"""
order_classification_bot.py - 주문판정봇 (규칙기반 임시 버전)

역할: 통화/문자 원문 1건을 6종으로 분류한다
  주문전화 | 주문가능성있음 | 단순문의 | 일반통화 | 스팸무관 | 확인필요

지금은 Claude API 키가 이 작업 환경에 연결돼 있지 않아서, 원래 설계(kind: model,
tier: sonnet — 문맥을 보고 판단)를 지금 당장 구현/테스트할 수 없다. 그래서 우선
키워드/패턴 매칭 규칙기반 버전을 만들고, 나중에 API 키가 생기면 CLASSIFY_ENGINE
자리에 LLM 호출 함수만 갈아끼우면 되도록 구조를 분리해뒀다.

알려진 한계 (숨기지 않고 명시): golden_set 003번("꽃 심으로 가야 되는데...")처럼
도메인 키워드("꽃")는 있지만 실제 주문 신호(가격/배송동사/축하문구)가 없는 케이스는
이 규칙기반 버전으로는 구분하지 못한다 — 문맥을 못 읽기 때문에 생기는, 애초에
이 봇을 model(sonnet)으로 설계한 이유 그 자체인 케이스다. 실제 LLM을 붙이기 전까지의
알려진 한계로 남겨둔다(test_order_classification_bot.py 결과표에 명시적으로 표시).

12봇_kind분류표.yaml 대응:
  io.reads:  stt_text, ocr_text, raw_text
  io.writes: order_classification
"""

import re

ORDER_CLASSIFICATIONS = ["주문전화", "주문가능성있음", "단순문의", "일반통화", "스팸무관", "확인필요"]

# confidence가 이 값보다 낮으면 분류값과 무관하게 강제로 "확인필요"로 덮어쓴다
# (설계문서 규칙: "애매하면 무조건 확인 필요로 남겨")
FORCE_UNCERTAIN_BELOW = 0.5

_PRICE_PATTERN = re.compile(r"\d+\s*(만\s*원|원|마넌)")
_PRODUCT_PATTERN = re.compile(r"화환|근조|조화|난초|\b난\b|리본")
_SEND_VERB_PATTERN = re.compile(r"보내(주세요|줘|고\s*싶은데|고싶은데)|배달|배송")
_CELEBRATION_PATTERN = re.compile(r"축하합니다|축하해|근조|삼가")
_WEAK_DOMAIN_PATTERN = re.compile(r"꽃")

_GREETING_PATTERN = re.compile(r"잘\s*지내|건강하|밥\s*먹었|어떻게\s*지내")
_SCHEDULE_QUESTION_PATTERN = re.compile(r"언제\s*(하는데|해|야)|몇\s*시")


def _classify_rule_based(text: str) -> dict:
    """
    규칙기반(키워드/패턴 매칭) 판정 로직.

    나중에 LLM으로 교체할 때: 이 함수와 시그니처(text: str) -> dict가 같은 함수를
    만들어서 아래 CLASSIFY_ENGINE에 대입만 하면 된다 (classify_order() 쪽은 안 바꿔도 됨).
    아직 실제 LLM 호출 코드는 만들지 않았다(API 키 없음 — 사용자 확인 사항).
    """
    strong_signals = 0
    if _PRICE_PATTERN.search(text):
        strong_signals += 1
    if _PRODUCT_PATTERN.search(text):
        strong_signals += 1
    if _SEND_VERB_PATTERN.search(text):
        strong_signals += 1
    if _CELEBRATION_PATTERN.search(text):
        strong_signals += 1

    if strong_signals >= 2:
        return {
            "order_classification": "주문전화",
            "confidence": 0.85,
            "reason": "강한 주문 신호 " + str(strong_signals) + "개 매칭(가격/상품/배송동사/축하문구 조합)",
        }

    if strong_signals == 1:
        return {
            "order_classification": "주문가능성있음",
            "confidence": 0.65,
            "reason": "주문 신호 1개만 매칭 — 확신 부족",
        }

    if _WEAK_DOMAIN_PATTERN.search(text):
        return {
            "order_classification": "주문가능성있음",
            "confidence": 0.55,
            "reason": "도메인 키워드('꽃')만 매칭, 강한 주문 신호 없음 — 규칙기반 한계 구간(golden_set 003 참고)",
        }

    if _GREETING_PATTERN.search(text) or _SCHEDULE_QUESTION_PATTERN.search(text):
        return {
            "order_classification": "일반통화",
            "confidence": 0.8,
            "reason": "안부/일정 문의 패턴 매칭, 주문 신호 없음",
        }

    return {
        "order_classification": "확인필요",
        "confidence": 0.3,
        "reason": "어떤 규칙에도 뚜렷하게 걸리지 않음",
    }


# 실제로 쓰이는 판정 엔진. 지금은 규칙기반. 나중에 LLM 버전을 만들면
# order_classification_bot.CLASSIFY_ENGINE = classify_order_llm 처럼 이 이름만 바꿔치기하면
# classify_order()를 포함해 이 파일을 쓰는 다른 코드는 손댈 필요가 없다.
CLASSIFY_ENGINE = _classify_rule_based


def classify_order(text: str) -> dict:
    """
    공개 API. CLASSIFY_ENGINE을 호출하고, confidence가 낮으면 분류값과 무관하게
    강제로 "확인필요"로 덮어쓴다.
    반환: {"order_classification": ..., "confidence": ..., "reason": ...}
    """
    result = CLASSIFY_ENGINE(text)
    if result["confidence"] < FORCE_UNCERTAIN_BELOW and result["order_classification"] != "확인필요":
        result = dict(result)
        result["order_classification"] = "확인필요"
        result["reason"] = result["reason"] + " (confidence 낮아 강제 확인필요로 전환)"
    return result
