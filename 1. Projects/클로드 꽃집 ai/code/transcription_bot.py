"""
transcription_bot.py — 받아쓰기봇 (12봇_kind분류표.yaml의 transcription_bot 실제 구현)

역할: raw_audio/raw_image를 텍스트로 바꾸고(STT/OCR), raw_text는 최소 정리만 해서
cleaned_text에 담는다. "판단"은 하지 않는다 — 의미 보정(구어체 교정 등)은 correction_bot
(말귀봇, kind: model) 몫이고 여기선 하지 않는다(shared_context.cleaned_text 설명 그대로).

STT — [2026-07-20 갱신] 혜미 요청으로 실 API(OpenAI Whisper, stt_client.py) 연동
완료. STT_ENGINE은 이제 실제 오디오 바이트를 받아 한국어 텍스트로 바꾸려고 "시도"하고,
키가 없거나 호출이 실패하면(예: OPENAI_API_KEY 미등록, 네트워크 오류) 조용히 항등
목업으로 대체한다(다른 model stage들의 LLM 우선+규칙기반 폴백과 같은 안전망 패턴).
engine_meta.real_api_connected로 실제 어느 쪽이 쓰였는지 투명하게 남긴다.

OCR — 여전히 미연동, 항등(identity) 목업이다(알려진 한계, 숨기지 않고 명시). 사진으로
들어온 주문은 여전히 사람이 옮겨 적어야 한다.

kind_open_question(12봇_kind분류표.yaml 원문 인용): Fable 답변 내부에서도 "STT 호출
자체"(local)와 "STT 후처리"(model 가능성 암시)가 불일치한다는 미해결 질문이 있음 —
이 파일은 "STT 호출 자체" 관점(현재 표의 채택안)만 구현한다.

12봇_kind분류표.yaml 대응:
  io.reads:  raw_audio, raw_image, raw_text
  io.writes: stt_text, ocr_text, cleaned_text, engine_meta
"""

import re

import stt_client


def _identity_stt_engine(raw_audio):
    """목업 STT 엔진 — 실제 음성 인식 없음. 입력을 그대로 텍스트로 돌려준다.
    (테스트/golden_set 시뮬레이션에서 raw_audio 자리에 텍스트를 직접 넣는 경우와,
    실 STT 호출이 실패했을 때의 폴백 경로 둘 다에 쓰인다.)"""
    return raw_audio


def _identity_ocr_engine(raw_image):
    """목업 OCR 엔진 — 실제 이미지 인식 없음. 입력을 그대로 텍스트로 돌려준다."""
    return raw_image


def _real_stt_engine(raw_audio):
    """실제 OpenAI Whisper API 호출(2026-07-20 신설). raw_audio는 실제 오디오
    바이트여야 한다 - 문자열이 오면 stt_client가 STTUnavailableError를 던진다."""
    return stt_client.transcribe_audio(raw_audio)


def _auto_stt_engine(raw_audio):
    """실 STT 우선 시도, 실패하면(키 없음/네트워크 오류/오디오가 아닌 입력 등)
    항등 목업으로 자동 대체. 반환값은 (text, real_api_connected) 튜플.

    주의: raw_audio가 진짜 오디오 바이트(bytes/bytearray)인데 실 STT가 실패하면,
    바이트를 그대로 "텍스트"인 척 반환하면 안 된다(다운스트림 정리 로직이 깨짐 -
    2026-07-20에 실제로 발견된 버그). 항등 폴백은 raw_audio가 원래 문자열일
    때(테스트/golden_set 시뮬레이션)만 의미가 있고, 진짜 바이트면 None을 반환해
    "음성인식 실패"를 정직하게 알린다."""
    try:
        return _real_stt_engine(raw_audio), True
    except stt_client.STTUnavailableError:
        if isinstance(raw_audio, (bytes, bytearray)):
            return None, False
        return _identity_stt_engine(raw_audio), False


# 2026-07-20부터 STT는 실 API(Whisper) 우선, 실패 시 항등 목업 자동 대체.
# OCR은 여전히 항등 목업만(알려진 한계) - 나중에 실제 OCR API가 생기면 이 이름만 바꿔치면 됨.
STT_ENGINE = _auto_stt_engine
OCR_ENGINE = _identity_ocr_engine


def _minimal_cleanup(text):
    """말귀봇(의미 보정)이 아니라 받아쓰기봇 몫의 최소 정리 — 연속 공백만 정리한다."""
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip()


def transcribe(raw_audio=None, raw_image=None, raw_text=None):
    """
    공개 API. raw_audio/raw_image/raw_text 중 있는 것만 처리한다.
    cleaned_text는 stt_text > ocr_text > raw_text 우선순위로 있는 것 하나를 최소 정리해서 채운다.
    """
    stt_real_used = False
    if raw_audio is not None:
        stt_text, stt_real_used = STT_ENGINE(raw_audio)
    else:
        stt_text = None
    ocr_text = OCR_ENGINE(raw_image) if raw_image is not None else None

    if stt_text is not None:
        source_for_cleanup = stt_text
    elif ocr_text is not None:
        source_for_cleanup = ocr_text
    else:
        source_for_cleanup = raw_text
    cleaned_text = _minimal_cleanup(source_for_cleanup)

    engine_meta = {
        "stt_engine": ("whisper-1" if stt_real_used else "mock_identity") if raw_audio is not None else None,
        "ocr_engine": "mock_identity" if raw_image is not None else None,
        # [2026-07-20 갱신] STT는 이제 실 API 연동됨(성공 시 True) - OCR은 여전히 미연동.
        "real_api_connected": bool(stt_real_used),
        "note": "STT는 실 API 연동(2026-07-20, 실패 시 자동 폴백) - OCR은 여전히 미연동, 알려진 한계",
    }

    return {
        "stt_text": stt_text,
        "ocr_text": ocr_text,
        "cleaned_text": cleaned_text,
        "engine_meta": engine_meta,
    }
