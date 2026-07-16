#!/usr/bin/env python3
"""present_engine.py — 발표 라인 (혜미 방식 14~16단계).

14단계 발표자료 제작   → slide_deck_engine (11장 기본 흐름, 배점 기준 재구성)
15단계 발표 대본 제작   → script_engine (풀버전·압축·쉬운말·슬라이드별 핵심·마무리)
16단계 발표연습기      → rehearsal_engine (타이머 배분·공격질문·방어답변·위험표현)

원칙:
- 발표자료는 제출본 요약이 아니다 — 심사표·예상질문·예산방어 중심으로 재구성.
- 한 슬라이드 = 하나의 핵심 주장. 발표자가 실제로 말할 수 있는 문장.
- 제출본과 충돌 금지: 초안과 같은 데이터(선정 아이디어)에서만 생성.
"""
from __future__ import annotations

import re

from engines import ATTACK_QUESTIONS, SAFE_ANSWER, fmt, is_missing
from draft_engine import _need, pick_idea, sanitize_text

# 쉬운 말 변환 (정책어 → 현장어)
EASY_WORDS = [
    ("수행기간", "사업 기간"), ("산출물", "결과물"), ("자부담", "제가 내는 돈"),
    ("실측", "직접 재본"), ("고도화", "더 좋게 만드는 것"), ("구축", "만들기"),
    ("도입", "들여오기"), ("검증", "확인"), ("협약", "계약"), ("역량", "할 수 있는 힘"),
    ("증빙", "증거 자료"), ("본 과제", "이 사업"), ("당사", "저희 가게"),
    ("프로세스", "일하는 순서"), ("반자동", "반은 자동, 반은 직접"),
]


def easy_speech(text: str) -> str:
    for hard, easy in EASY_WORDS:
        text = text.replace(hard, easy)
    return text


# ------------------------------------------------- 14단계: 발표자료

# (슬라이드 흐름, 시간 비중 %) — 공고 발표 기준 있으면 조정하라는 note 병기
SLIDE_FLOW = [
    ("과제명·한 줄 요약", 6), ("문제 (필요성)", 12), ("기존 방식의 한계", 8),
    ("핵심 해결방안", 14), ("실행계획 (기간 내)", 12), ("예산과 산출물", 12),
    ("성과목표", 10), ("고객·확산 계획", 8), ("신청자 역량", 8),
    ("리스크 관리", 5), ("마무리", 5),
]


def slide_deck_engine(data: dict, res: dict, doc: dict) -> dict:
    n = data.get("notice", {}) or {}
    pres = n.get("presentation", {}) or {}
    required = pres.get("required")
    idea_row, idea_src = pick_idea(data, res["ideas"])
    if not idea_src:
        return {"ready": False, "reason": "아이디어 미선정 — 발표자료는 선정·초안 이후에 만든다 (충돌 방지)"}
    draft = doc["draft"]
    minutes = pres.get("present_minutes")
    total_sec = int(re.sub(r"\D", "", str(minutes)) or 10) * 60 if not is_missing(minutes) else 600
    top = (res["strategy"].get("top") or {})
    sec_by_no = {s["no"]: s for s in draft.get("sections", [])} if draft.get("ready") else {}
    name = idea_src.get("name") or "?"
    target = idea_src.get("target") or _need("고객")
    outputs = ", ".join(idea_src.get("outputs") or []) or _need("산출물")
    ev = ", ".join((idea_src.get("evidence_owned") or [])[:2]) or _need("증빙")
    b_rows = doc["budget_table"].get("rows", []) if doc["budget_table"].get("ready") else []
    budget_line = " / ".join(f"{r['item']} {r['amount']}" for r in b_rows[:3]) or _need("예산 항목")
    risks = ", ".join(idea_src.get("risks") or []) or _need("리스크 인식")

    content = {
        "과제명·한 줄 요약": {"key": draft.get("title", name),
                        "bullets": [draft.get("summary", "")], "ev": ""},
        "문제 (필요성)": {"key": f"{target}의 반복 손실이 실재한다",
                     "bullets": [(idea_src.get("problem") or _need("문제"))[:80],
                                 "근거: " + ev], "ev": ev},
        "기존 방식의 한계": {"key": "쓰던 이유는 있었지만 한계가 남는다",
                      "bullets": [_need("기존 방식 vs 한계 1줄"), f"본 과제가 해결하는 지점: {name}"], "ev": ""},
        "핵심 해결방안": {"key": f"{name} — 대표자 검수형 반자동 구조",
                    "bullets": [f"산출물: {outputs}", "AI 초안 생성 → 대표자 검수·확정"], "ev": ""},
        "실행계획 (기간 내)": {"key": f"수행기간 {fmt(n.get('execution_period'))} 안에 끝나는 범위",
                        "bullets": ["준비(기준치 실측) → 구축 → 검증(전후 비교)"], "ev": ""},
        "예산과 산출물": {"key": "돈을 쓰면 남는 것이 명확하다",
                    "bullets": [budget_line, "항목→목적→산출물→성과 연결표 제시"], "ev": "견적서"},
        "성과목표": {"key": "측정 방법이 있는 목표만 말한다",
                 "bullets": [_need("기준치(실측) → 목표치 · 측정 방법")], "ev": "실측 기록"},
        "고객·확산 계획": {"key": f"최고 배점 '{top.get('item', '성장가능성')}' 대응",
                     "bullets": [(sec_by_no.get("5", {}).get("body", ""))[:80] or _need("성장 연결")], "ev": ""},
        "신청자 역량": {"key": "내가 직접 실행하고 검수한다",
                   "bullets": [(sec_by_no.get("6", {}).get("body", ""))[:80]], "ev": "사업자등록증 등"},
        "리스크 관리": {"key": "위험을 알고 있고 보완계획이 있다",
                   "bullets": [f"인식한 리스크: {risks}", "발생 시 범위 축소·대체 수단으로 보완"], "ev": ""},
        "마무리": {"key": "공고 목적과 맞는, 기간 내 검증 가능한 과제",
                "bullets": ["약속은 좁게, 검증은 확실하게"], "ev": ""},
    }
    slides = []
    for i, (title, share) in enumerate(SLIDE_FLOW, 1):
        c = content[title]
        bullets = [sanitize_text(b)[0] for b in c["bullets"] if b]
        slides.append({"no": i, "title": title, "key_message": sanitize_text(c["key"])[0],
                       "bullets": bullets, "evidence": c["ev"],
                       "seconds": round(total_sec * share / 100),
                       "must_say": bullets[0] if bullets else c["key"]})
    return {"ready": True, "slides": slides, "total_seconds": total_sec,
            "presentation_required": fmt(required),
            "note": ("발표 여부 미확보 — 공고 원문 확인 필요. " if is_missing(required) else "")
                    + "이 흐름은 기본값이다. 공고의 발표 기준·심사표에 맞춰 조정하라.",
            "rules": ["한 슬라이드 = 하나의 핵심 주장", "글자는 짧게, 이미지는 증빙 역할",
                      "제출본과 충돌 금지", "배점 높은 항목을 핵심 슬라이드에"]}


# ------------------------------------------------- 15단계: 발표 대본

def script_engine(deck: dict, data: dict) -> dict:
    if not deck.get("ready"):
        return {"ready": False, "reason": deck.get("reason", "발표자료 없음")}
    full, compressed, easy = [], [], []
    for s in deck["slides"]:
        lines = [f"{s['key_message']}."] + [f"{b}." for b in s["bullets"]]
        spoken = " ".join(lines).replace("..", ".")
        full.append({"no": s["no"], "title": s["title"], "seconds": s["seconds"],
                     "text": spoken, "must_say": s["must_say"]})
        compressed.append({"no": s["no"], "text": f"{s['key_message']}."})
        easy.append({"no": s["no"], "text": easy_speech(spoken)})
    opening = ("안녕하십니까. " + (full[0]["text"] if full else "") +
               " 지금부터 왜 이 사업이 필요한지, 무엇을 만들고, 돈을 어디에 쓰는지 순서로 말씀드리겠습니다.")
    closing = ("정리하겠습니다. 문제는 실재하고, 해결 범위는 수행기간 안으로 한정했으며, "
               "예산은 산출물과 연결했습니다. 결과물은 제가 직접 검수하며 실행하겠습니다. 감사합니다.")
    return {"ready": True, "opening": sanitize_text(opening)[0],
            "slides": full, "compressed": compressed, "easy": easy,
            "closing": sanitize_text(closing)[0],
            "rules": ["서류 문장을 그대로 읽지 않는다 — 말로 바꾼다", "한 문장을 짧게",
                      "외운 티보다 직접 설명하는 느낌", "신청자의 실제 경험이 드러나게"],
            "todo": "발표자 말투 맞춤·시간 압축은 실제 발표자가 소리 내 읽으며 조정 (16단계 연습기)"}


# ------------------------------------------------- 16단계: 발표연습기 데이터

WHY3 = [
    ("왜 이 아이템인가?", "문제와 기존 한계로 답한다",
     lambda i, a: f"{i.get('target') or '현장'}에서 {(i.get('problem') or '[확인 필요: 문제]')[:50]} 문제가 반복되고, 기존 방식으로는 해결이 안 되기 때문입니다."),
    ("왜 지금인가?", "공고 취지·환경 변화·필요성으로 답한다",
     lambda i, a: "지금 개선하지 않으면 손실이 계속 쌓이고, 이번 공고의 지원 범위가 정확히 이 문제에 해당하기 때문입니다."),
    ("왜 신청자가 해야 하는가?", "경험·자원·실행역량으로 답한다",
     lambda i, a: f"제가 {fmt(a.get('industry'))} 현장을 직접 운영하며 이 문제를 매일 겪고 있고, 결과물을 직접 검수할 수 있기 때문입니다."),
]


def rehearsal_engine(data: dict, res: dict, doc: dict, deck: dict, script: dict) -> dict:
    idea_row, idea_src = pick_idea(data, res["ideas"])
    a = data.get("applicant", {}) or {}
    i = idea_src or {}

    why3 = [{"q": q, "how": how, "answer": sanitize_text(gen(i, a))[0]} for q, how, gen in WHY3]

    budget_defense = []
    for r in (doc["budget_table"].get("rows") or []):
        ans = (f"{r['item']}은(는) {r['purpose']}에 필요하고, 결과물로 {r['output']}이(가) 남습니다. "
               f"금액 산정 근거는 {r['basis']}입니다. 줄여야 한다면 범위를 좁혀 핵심 산출물부터 확보하겠습니다.")
        budget_defense.append({"item": r["item"], "answer": sanitize_text(ans)[0],
                               "structure": "항목 → 목적 → 산출물 → 성과 → 평가항목 연결"})

    # 슬라이드별 예상 질문
    slide_qs = {
        "문제": ["그 수치는 어떻게 측정했습니까?", "문제가 그렇게 크다면 왜 여태 해결 안 했습니까?"],
        "해결": ["기존 방식과 무엇이 다릅니까?", "단순 구매·외주 아닙니까?"],
        "실행": ["수행기간 안에 정말 가능합니까?", "업체가 중간에 이탈하면요?"],
        "예산": ["이 금액 산정 근거는요?", "예산을 30% 줄이면 무엇을 뺄 겁니까?"],
        "성과": ["목표치가 근거가 있습니까?", "실패하면 어떻게 보완합니까?"],
        "역량": ["대표자가 직접 할 수 있습니까?", "기술을 모르는데 어떻게 검수합니까?"],
        "확산": ["그 확장 계획의 근거는요?"],
    }
    per_slide = []
    for s in (deck.get("slides") or []):
        qs = [q for k, lst in slide_qs.items() if k in s["title"] for q in lst]
        per_slide.append({"no": s["no"], "title": s["title"], "seconds": s["seconds"],
                          "must_say": s["must_say"], "questions": qs})

    qna_status = {q["question"]: q for q in res["qna"]}
    return {"why3": why3, "budget_defense": budget_defense, "per_slide": per_slide,
            "attack_questions": [{"q": q, "status": qna_status.get(q, {}).get("status", "발화 가능"),
                                  "note": qna_status.get(q, {}).get("note", "")}
                                 for q in ATTACK_QUESTIONS],
            "unknown_answer": SAFE_ANSWER,
            "total_seconds": deck.get("total_seconds", 600),
            "feedback_criteria": ["질문에 직접 답했는가", "답변이 장황하지 않은가", "과장 표현이 없는가",
                                  "증빙을 언급했는가", "예산과 산출물을 연결했는가", "실제로 말할 수 있는 문장인가"],
            "modes": ["시간 측정", "슬라이드별 연습", "심사위원 공격", "예산 방어",
                      "WHY 3종", "위험 표현 감지", "최종 리허설"]}


# ------------------------------------------------- 발표 라인 오케스트레이터

def build_presentation_line(data: dict, res: dict, doc: dict) -> dict:
    deck = slide_deck_engine(data, res, doc)
    script = script_engine(deck, data)
    rehearsal = rehearsal_engine(data, res, doc, deck, script)
    return {"deck": deck, "script": script, "rehearsal": rehearsal}
