"""
collection_bot.py — 수집봇 (12봇_kind분류표.yaml의 collection_bot 실제 구현)

역할: 카카오톡/문자/사진/녹음파일/수기입력 등 어떤 채널로 들어오든 원본을 그대로
shared_context 필드로 옮겨 담는다. 판단은 하지 않는다 — 원본 소실 금지가 유일한 규칙.

12봇_kind분류표.yaml 대응:
  io.reads:  []
  io.writes: raw_text, raw_image, raw_audio, source_type, created_at
"""

from datetime import datetime, timezone

VALID_SOURCE_TYPES = {"call", "kakao", "sms", "photo", "manual"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def collect(source_type, raw_text=None, raw_image=None, raw_audio=None, created_at=None):
    """
    공개 API. source_type은 반드시 설계보고서에 정의된 5종 중 하나여야 한다.
    raw_text/raw_image/raw_audio 중 최소 1개는 있어야 한다(원본 소실 금지 규칙) —
    아무것도 없으면 조용히 빈 레코드를 만들지 않고 ValueError를 던진다.
    created_at을 안 주면 지금 시각(UTC ISO)을 채운다.
    """
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            "source_type must be one of " + str(sorted(VALID_SOURCE_TYPES)) + ", got: " + str(source_type)
        )
    if raw_text is None and raw_image is None and raw_audio is None:
        raise ValueError(
            "collection_bot: raw_text/raw_image/raw_audio 중 최소 1개는 있어야 함 (원본 소실 금지 규칙)"
        )

    return {
        "raw_text": raw_text,
        "raw_image": raw_image,
        "raw_audio": raw_audio,
        "source_type": source_type,
        "created_at": created_at or _now(),
    }
