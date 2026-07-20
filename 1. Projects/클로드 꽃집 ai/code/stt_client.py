"""
stt_client.py - 통화 녹음 파일(오디오)을 텍스트로 바꾸는 OpenAI Whisper API 호출 도우미.

2026-07-20 신설: 혜미가 "통화녹음도 가능해야지, API도 넣었으니까"라고 요청. 확인 결과
Anthropic Claude API는 아직 오디오 입력을 지원하지 않아(2026-07 기준 공식 확인 -
Messages API는 텍스트/이미지만 받고 raw audio는 못 받음) 이미 있는 ANTHROPIC_API_KEY로는
음성인식이 안 된다. 그래서 별도 서비스(OpenAI Whisper API)를 새로 붙인다 - 혜미가
직접 OpenAI 계정을 만들고 API 키를 발급받아야 하는 부분(계정 생성은 AI가 대신 못 함).

비용(2026-07 기준, OpenAI 공식 가격표 https://openai.com/business/pricing/ - 변동 가능,
정확한 최신 금액은 그 페이지에서 재확인 권장): whisper-1 모델 기준 분당 0.006달러
(약 8원, 1350원/달러 환산). 통화 10분이면 약 80원. 이 스킬의 통화량 기준으로는
한 달에 몇 천 원 수준일 것으로 예상됨(정확한 예상치는 실제 통화 건수·평균 길이에
따라 다름 - HANDOFF.md/decision-log 참고).

.env 위치: code/.env에 OPENAI_API_KEY=... 한 줄 추가(로컬 테스트용). Render는 이것과
별개로 Settings > Environment Variables에 OPENAI_API_KEY를 새로 추가해야 한다
(ANTHROPIC_API_KEY와는 다른 서비스 키라 따로 등록 필요).

설계 원칙(llm_client.py와 동일한 안전망 패턴 승계):
  - 키가 없거나 호출이 실패하면 STTUnavailableError를 던진다 - 호출부(transcription_bot의
    _stt_auto)가 이걸 잡아서 "실제 음성인식 실패" 상태로 안내하고, 파이프라인 전체를
    깨뜨리지 않는다.
"""

import io
import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def _load_env_file(path: Path) -> None:
    """llm_client.py의 로더와 동일한 구현(중복이지만, 각 client 파일이 서로 독립적으로
    동작하는 기존 패턴을 그대로 따름 - 하나가 고장나도 다른 하나는 영향받지 않게)."""
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

_client = None

# 실제 사용 모델. whisper-1은 OpenAI의 가장 오래되고 안정적인 STT 모델이라 우선
# 채택(2026-07). gpt-4o-mini-transcribe가 분당 가격은 더 싸지만(약 0.003달러/분),
# 신모델이라 안정성 검증 전이라 일단 보수적으로 whisper-1로 시작 - 나중에 비용
# 최적화하려면 이 상수만 바꾸면 됨.
_STT_MODEL = "whisper-1"


class STTUnavailableError(Exception):
    """API 키가 없거나, 호출/응답이 실패했을 때 - 호출부가 "음성인식 실패" 처리하도록 신호."""


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not os.environ.get("OPENAI_API_KEY"):
        raise STTUnavailableError("OPENAI_API_KEY가 없음 (code/.env 또는 Render Environment 확인 필요)")
    import openai  # 지연 import - 키 없는 환경(예: 테스트)에서도 이 파일 자체는 import 가능하게

    _client = openai.OpenAI()
    return _client


def transcribe_audio(audio_bytes: bytes, filename: str = "recording.m4a") -> str:
    """
    오디오 바이트를 받아 OpenAI Whisper API로 한국어 텍스트로 바꾼다.
    실패(키 없음/네트워크 오류/입력이 오디오가 아님 등)하면 STTUnavailableError를 던진다.
    """
    if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
        raise STTUnavailableError(f"오디오 바이트가 아니거나 비어있음: {type(audio_bytes)!r}")

    try:
        client = _get_client()
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename  # OpenAI SDK가 파일명 확장자로 오디오 포맷을 추론함
        response = client.audio.transcriptions.create(
            model=_STT_MODEL,
            file=file_obj,
            language="ko",
        )
    except STTUnavailableError:
        raise
    except Exception as e:  # 네트워크/인증/포맷 오류 등 전부 "음성인식 실패" 신호로 통일
        raise STTUnavailableError(f"OpenAI STT 호출 실패: {e}") from e

    text = getattr(response, "text", None)
    if not text:
        raise STTUnavailableError(f"STT 응답에 text가 없음: {response!r}")
    return text
