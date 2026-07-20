"""
llm_client.py - 6개 model stage(kind: model)가 공통으로 쓰는 Claude API 호출 도우미.

2026-07-17: 진짜 Anthropic API 키가 발급되면서 신설. 그동안 각 봇 파일(*_bot.py)의
docstring에 "API 키가 없어서 규칙기반 버전을 만든다"고 반복 기록돼 있던 그 제약이
해소돼, 이 파일이 실제 LLM 호출부를 한 곳에 모아 6개 봇이 재사용한다.

설계 원칙(회사 헌장/이 스킬의 반복된 원칙 그대로 승계):
  - "값을 임의로 채우지 않는다" - 모델이 확신 없는 값을 지어내면 안 된다. 각 봇의
    프롬프트에 이 원칙을 명시적으로 박아둔다(특히 order_draft_bot의 이름 필드 등).
  - API 호출이 실패(네트워크 오류, 키 문제, 응답 파싱 실패 등)하면 전체 파이프라인을
    깨뜨리지 않고, 각 봇 파일에 이미 있던 규칙기반 버전으로 자동 대체(fallback)한다.
    이건 새로운 설계 판단이 아니라 "안전망 없이 무너지면 안 된다"는 이 볼트의
    기존 원칙(quality_gate/on_fail/human_review 게이트) 적용일 뿐이다.
  - tier 이름(low_cost/mid/high)은 manifest.yaml의 규칙 그대로 사용하고, 실제
    모델명은 여기 한 곳에만 있다(모델명 하드코딩 금지 원칙 - 티어명만 stage에 노출).

.env 파일 위치: 이 파일과 같은 폴더의 .env (code/.env) - .gitignore가 이미 이
이름의 파일을 깃허브에 올라가지 않게 막고 있다(볼트 루트 .gitignore의 ".env" 규칙).
"""

import json
import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def _load_env_file(path: Path) -> None:
    """python-dotenv 의존성 없이 KEY=VALUE 줄만 읽어 os.environ에 채워 넣는다.
    이미 환경변수에 같은 이름이 있으면 덮어쓰지 않는다(명시적 환경변수 우선)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(_ENV_PATH)

# manifest.yaml model_routing이 쓰는 티어명 -> 실제 모델 ID. 이 파일 밖으로는
# 절대 모델명을 노출하지 않는다(모델명 하드코딩 금지 원칙, model_routing 주석 참고).
TIER_MODEL_MAP = {
    # [2026-07-20 수정] "claude-haiku-4-5"는 날짜 접미사가 빠진 잘못된 모델 ID였음
    # (정확한 문자열은 "claude-haiku-4-5-20251001") - 이 오타 때문에 low_cost
    # tier를 쓰는 모든 봇(order_draft_bot 포함)의 API 호출이 매번 실패해 규칙기반
    # 폴백으로 조용히 넘어가고 있었다. 혜미가 API 키를 등록했는데도 이름 자동추출이
    # 반영 안 되는 것처럼 보인 원인이 이것으로 추정됨 - 실사용 재확인 필요.
    "low_cost": "claude-haiku-4-5-20251001",
    "mid": "claude-sonnet-5",
    "high": "claude-opus-4-8",  # 이 스킬의 6개 model stage 중 실제로 high를 쓰는 곳은 없음
}

_client = None


class LLMUnavailableError(Exception):
    """API 키가 없거나, 호출/파싱이 실패했을 때 - 호출부가 규칙기반으로 대체(fallback)하도록 신호."""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMUnavailableError("ANTHROPIC_API_KEY가 없음 (code/.env 확인 필요)")
    import anthropic  # 지연 import - 키가 없는 환경(예: 테스트)에서도 이 파일 자체는 import 가능하게

    _client = anthropic.Anthropic()
    return _client


def call_llm_json(tier: str, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict:
    """
    지정한 tier의 모델을 호출해 JSON 하나를 돌려받는다. system_prompt는 반드시
    "JSON만 반환하라"는 지시를 포함해야 한다(각 봇 파일에서 작성).
    실패(키 없음/네트워크 오류/JSON 파싱 실패)하면 LLMUnavailableError를 던진다 -
    호출부(각 봇의 *_auto 함수)가 이걸 잡아서 규칙기반 버전으로 대체한다.
    """
    model = TIER_MODEL_MAP.get(tier)
    if model is None:
        raise LLMUnavailableError(f"알 수 없는 tier '{tier}'")

    try:
        client = _get_client()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except LLMUnavailableError:
        raise
    except Exception as e:  # 네트워크/인증/기타 API 오류 - 전부 fallback 신호로 통일
        raise LLMUnavailableError(f"Claude API 호출 실패: {e}") from e

    text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    raw_text = "".join(text_parts).strip()

    # 모델이 코드블록(```json ... ```)으로 감싸는 경우가 있어 벗겨낸다
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise LLMUnavailableError(f"모델 응답이 JSON이 아님: {e} (원문 앞부분: {raw_text[:200]!r})") from e
