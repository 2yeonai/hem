"""
llm_client.py - 방역 스킬의 kind:model stage들이 공통으로 쓰는 Claude API 호출 도우미.

꽃집 스킬(`1. Projects/클로드 꽃집 ai/code/llm_client.py`)과 같은 목적, 같은 설계
원칙(값을 임의로 채우지 않는다 / API 실패 시 기존 mock으로 자동 대체 / 모델명은
이 파일에만)을 그대로 따른다. 방역 manifest.yaml은 tier를 low_cost/mid/high가
아니라 haiku/sonnet/opus로 직접 표기하므로, 매핑 테이블만 그 이름에 맞춘다.

.env 파일 위치: 이 파일과 같은 폴더의 .env (scripts/.env) - 볼트 루트 .gitignore의
".env" 규칙이 파일명만 보고 어디에 있든 막아주므로 안전하다.
"""

import json
import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def _load_env_file(path: Path) -> None:
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

# manifest.yaml이 그대로 쓰는 티어명(haiku/sonnet/opus) -> 실제 모델 ID.
TIER_MODEL_MAP = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-4-8",  # 방역 스킬의 4개 model stage 중 실제로 쓰는 곳은 없음
}

_client = None


class LLMUnavailableError(Exception):
    """API 키가 없거나 호출/파싱 실패 - 호출부가 기존 mock으로 대체하도록 신호."""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMUnavailableError("ANTHROPIC_API_KEY가 없음 (scripts/.env 확인 필요)")
    import anthropic

    _client = anthropic.Anthropic()
    return _client


def call_llm_json(tier: str, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict:
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
    except Exception as e:
        raise LLMUnavailableError(f"Claude API 호출 실패: {e}") from e

    text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    raw_text = "".join(text_parts).strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise LLMUnavailableError(f"모델 응답이 JSON이 아님: {e} (원문 앞부분: {raw_text[:200]!r})") from e
