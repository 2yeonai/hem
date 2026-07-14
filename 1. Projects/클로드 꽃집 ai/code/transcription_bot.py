"""
transcription_bot.py — 받아쓰기봇 (12봇_kind분류표.yaml의 transcription_bot 실제 구현)

역할: raw_audio/raw_image를 텍스트로 바꾸고(STT/OCR), raw_text는 최소 정리만 해서
cleaned_text에 담는다. "판단"은 하지 않는다 — 의미 보정(구어체 교정 등)은 correction_bot
(말귀봇, kind: model) 몫이고 여기선 하지 않는다(shared_context.cleaned_text 설명 그대로).

알려진 한계(숨기지 않고 명시): 이 작업 환경에는 실제 STT/OCR API 키가 연결돼 있지 않다.
그래서 STT_ENGINE/OCR_ENGINE은 지금 "받은 값을 그대로 텍스트로 반환하는" 항등(identity)
목업이다 — 실제로 오디오 바이너리를 텍스트로 바꾸는 게 아니라, 이미 텍스트로 들어온
입력(golden_set의 raw_text_excerpt 등)을 그대로 통과시키는 자리표시자다. 나중에 실제
STT/OCR API 키가 생기면 STT_ENGINE/OCR_ENGINE 두 이름만 실제 호출 함수로 바꿔치면 된다
(order_classification_bot의 CLASSIFY_ENGINE과 같은 패턴).

kind_open_question(12봇_kind분류표.yaml 원문 인용): Fable 답변 내부에서도 "STT 호출
자체"(local)와 "STT 후처리"(model 가능성 암시)가 불일치한다는 미해결 질문이 있음 —
이 파일은 "STT 호출 자체" 관점(현재 표의 채택안)만 구현한다.

12봇_kind분류표.yaml 대응:
  io.reads:  raw_audio, raw_image, raw_text
  io.writes: stt_text, ocr_text, cleaned_text, engine_meta
"""

import re


def _identity_stt_engine(raw_audio):
    """목업 STT 엔진 — 실제 음성 인식 없음. 입력을 그대로 텍스트로 돌려준다."""
    return raw_audio


def _identity_ocr_engine(raw_image):
    """목업 OCR 엔진 — 실제 이미지 인식 없음. 입력을 그대로 텍스트로 돌려준다."""
    return raw_image


# 나중에 LLM/실제 STT·OCR API로 교체할 때 이 두 이름만 바꿔치면 된다
STT_ENGINE = _identity_stt_engine
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
    stt_text = STT_ENGINE(raw_audio) if raw_audio is not None else None
    ocr_text = OCR_ENGINE(raw_image) if raw_image is not None else None

    if stt_text is not None:
        source_for_cleanup = stt_text
    elif ocr_text is not None:
        source_for_cleanup = ocr_text
    else:
        source_for_cleanup = raw_text
    cleaned_text = _minimal_cleanup(source_for_cleanup)

    engine_meta = {
        "stt_engine": "mock_identity" if raw_audio is not None else None,
        "ocr_engine": "mock_identity" if raw_image is not None else None,
        "real_api_connected": False,
        "note": "실제 STT/OCR API 미연동 — 알려진 한계(known limitation)",
    }

    return {
        "stt_text": stt_text,
        "ocr_text": ocr_text,
        "cleaned_text": cleaned_text,
        "engine_meta": engine_meta,
    }
