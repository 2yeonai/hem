#!/usr/bin/env python3
"""ai_engine.py — AI 4모드 라우터 (표준 라이브러리만 사용).

모드:
  local   규칙 엔진만 (비용 0원) — 기본값. 다른 모드 실패 시 최종 폴백.
  bridge  로그인된 ChatGPT/Claude/Gemini 웹 활용 (반자동): 프롬프트 생성·복사
          → 사용자가 웹에 붙여넣고 응답을 앱에 다시 붙여넣음. 개인용 실험 기능.
  api     사용자 API 키로 직접 호출 (urllib). 호출 전 예상 비용(원) 표시 + 확인 필수.
  hybrid  구조 분석은 local, 고급 판단(정밀 분석·초안 다듬기·검수)만 bridge/api + 캐시.

키 보안: 평문 저장 금지 — 사용자 비밀번호 기반 PBKDF2-HMAC 스트림 암호화(+무결성 MAC)로
00_local/ai_keys.enc에 저장 (00_local/은 gitignore). 키는 로그·화면·Export에 노출하지 않는다.
결제 기능 없음. 사용 가능 AI가 없으면 local로 동작한다.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCAL_DIR = BASE / "00_local"          # gitignore 대상 (키·캐시·설정)
KEYS_FILE = LOCAL_DIR / "ai_keys.enc"
SETTINGS_FILE = LOCAL_DIR / "ai_settings.json"
CACHE_DIR = LOCAL_DIR / "ai_cache"

PROVIDERS = ("openai", "claude", "gemini")

# 원화 비용표 (1K 토큰당, 대략치 — 설정에서 수정 가능). 환율 1,400원/$ 가정.
COST_KRW_PER_1K = {
    "openai": {"model": "gpt-4o-mini", "in": 0.21, "out": 0.84},
    "claude": {"model": "claude-haiku-4-5-20251001", "in": 1.4, "out": 7.0},
    "gemini": {"model": "gemini-2.0-flash", "in": 0.14, "out": 0.56},
}


# ------------------------------------------------------------- 설정

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"mode": "local", "enabled": [], "models": {}}  # enabled: 이번 달 사용 AI


def save_settings(s: dict):
    LOCAL_DIR.mkdir(exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------- 키 암호화

def _keystream(password: str, salt: bytes, n: int) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    out = b""
    c = 0
    while len(out) < n:
        out += hmac.new(key, c.to_bytes(8, "big"), hashlib.sha256).digest()
        c += 1
    return out[:n]


def _mac(password: str, salt: bytes, ct: bytes) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt + b"mac", 200_000)
    return hmac.new(key, ct, hashlib.sha256).digest()


def save_keys(keys: dict, password: str):
    """keys: {"openai": "sk-...", ...} → 암호화 저장. 평문은 어디에도 남지 않는다."""
    LOCAL_DIR.mkdir(exist_ok=True)
    data = json.dumps(keys).encode()
    salt = os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(data, _keystream(password, salt, len(data))))
    blob = {"salt": base64.b64encode(salt).decode(), "ct": base64.b64encode(ct).decode(),
            "mac": base64.b64encode(_mac(password, salt, ct)).decode()}
    KEYS_FILE.write_text(json.dumps(blob), encoding="utf-8")


def load_keys(password: str) -> dict | None:
    """비밀번호가 틀리면 None (비번 분실 시 delete_keys 후 재입력)."""
    if not KEYS_FILE.exists():
        return {}
    try:
        blob = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(blob["salt"])
        ct = base64.b64decode(blob["ct"])
        if not hmac.compare_digest(base64.b64decode(blob["mac"]), _mac(password, salt, ct)):
            return None
        return json.loads(bytes(a ^ b for a, b in zip(ct, _keystream(password, salt, len(ct)))))
    except Exception:
        return None


def delete_keys():
    KEYS_FILE.unlink(missing_ok=True)


def has_saved_keys() -> bool:
    return KEYS_FILE.exists()


def mask(key: str) -> str:
    return (key[:6] + "…" + key[-4:]) if len(key) > 12 else "(짧은 키)"


# ------------------------------------------------------------- 비용 추정

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)  # 한국어 대략치


def estimate_cost_krw(provider: str, prompt: str, expect_out_tokens=1500) -> dict:
    c = COST_KRW_PER_1K.get(provider, COST_KRW_PER_1K["openai"])
    tin = estimate_tokens(prompt)
    won = tin / 1000 * c["in"] + expect_out_tokens / 1000 * c["out"]
    return {"provider": provider, "model": c["model"], "in_tokens": tin,
            "out_tokens": expect_out_tokens, "krw": round(won, 1)}


# ------------------------------------------------------------- 캐시 (Hybrid)

def _cache_path(prompt: str, provider: str) -> Path:
    h = hashlib.sha256((provider + "\x00" + prompt).encode()).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def cache_get(prompt: str, provider: str):
    p = _cache_path(prompt, provider)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))["text"]
        except Exception:
            return None
    return None


def cache_put(prompt: str, provider: str, text: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(prompt, provider).write_text(
        json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------- API 호출 (urllib)

def _post(url: str, headers: dict, body: dict, timeout=90) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_api(provider: str, api_key: str, prompt: str, model: str = "") -> str:
    """단일 제공자 호출. 실패는 예외로 — 라우터가 폴백 처리."""
    model = model or COST_KRW_PER_1K[provider]["model"]
    if provider == "openai":
        r = _post("https://api.openai.com/v1/chat/completions",
                  {"Authorization": f"Bearer {api_key}"},
                  {"model": model, "messages": [{"role": "user", "content": prompt}]})
        return r["choices"][0]["message"]["content"]
    if provider == "claude":
        r = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                  {"model": model, "max_tokens": 4000,
                   "messages": [{"role": "user", "content": prompt}]})
        return "".join(b.get("text", "") for b in r["content"])
    if provider == "gemini":
        r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                  {}, {"contents": [{"parts": [{"text": prompt}]}]})
        return r["candidates"][0]["content"]["parts"][0]["text"]
    raise ValueError(f"미지원 제공자: {provider}")


def run_api_task(prompt: str, keys: dict, use_cache=True) -> dict:
    """설정된(이번 달 사용) AI 순서대로 시도, 실패 시 다음으로 폴백. 전부 실패 → local 안내."""
    s = load_settings()
    enabled = [p for p in s.get("enabled", []) if p in PROVIDERS and keys.get(p)]
    errors = []
    for p in enabled:
        if use_cache:
            hit = cache_get(prompt, p)
            if hit:
                return {"ok": True, "provider": p, "text": hit, "cached": True, "krw": 0}
        try:
            text = call_api(p, keys[p], prompt, s.get("models", {}).get(p, ""))
            cache_put(prompt, p, text)
            return {"ok": True, "provider": p, "text": text, "cached": False,
                    "krw": estimate_cost_krw(p, prompt)["krw"]}
        except urllib.error.HTTPError as e:
            errors.append(f"{p}: HTTP {e.code}")  # 응답 본문은 키 노출 위험 없게 코드만
        except Exception as e:
            errors.append(f"{p}: {type(e).__name__}")
    return {"ok": False, "errors": errors,
            "fallback": "사용 가능 AI 없음/전부 실패 — 로컬 규칙 결과로 진행 (이미 생성됨)"}


# ------------------------------------------------------------- 고급 작업 프롬프트 (bridge/api 공용)

TASKS = {
    "notice_deep": ("공고 정밀 분석",
        "너는 정부지원사업 심사위원이다. 아래 공고문을 분석해 1)사업의 진짜 목적 2)심사위원이 점수를 주는 기준(배점표 해석) "
        "3)본문에 되돌려줘야 할 공고 어휘 10개 4)감점·탈락 지뢰 5)이 공고에서 유리한 전략 3가지를 한국어로, 근거 원문을 인용하며 답하라.\n\n[공고문]\n{notice}"),
    "draft_polish": ("사업계획서 초안 다듬기",
        "너는 정부지원사업 전문 작성자다. 아래 초안을 심사표 기준으로 다듬어라. 과장 표현 금지(완벽/100%/보장 등), "
        "수치 없는 주장은 [확인 필요]로 표시, 배점 높은 항목을 두껍게. 섹션 구조는 유지하라.\n\n[심사표]\n{scoring}\n\n[초안]\n{draft}"),
    "judge_review": ("심사위원 모의 채점",
        "너는 깐깐한 심사위원이다. 아래 사업계획서 초안을 심사표로 항목별 채점(근거 포함)하고, "
        "탈락 사유 후보 3개와 보완 우선순위를 제시하라. 좋은 말만 하지 마라.\n\n[심사표]\n{scoring}\n\n[초안]\n{draft}"),
    "qna_attack": ("발표 Q&A 공격 생성",
        "너는 발표 심사장의 공격적인 심사위원이다. 아래 계획서에서 가장 아픈 질문 10개와, "
        "각 질문에 과장 없이 방어하는 모범 답변(3문장 이내)을 만들어라.\n\n[초안]\n{draft}"),
}


def build_prompt(task: str, **kw) -> str:
    label, tpl = TASKS[task]
    return tpl.format(**{k: (v or "[없음]")[:6000] for k, v in kw.items()})
