"""
order_split_bot.py - 주문분리봇 (규칙기반 임시 버전)

역할: order_classification_bot이 "주문전화/주문가능성있음"으로 판정한 원문 1건
안에 독립된 주문이 여러 건 섞여 있는지 판단해서 분리한다.

주문판정봇과 같은 이유로(API 키 없음) 지금은 규칙기반 버전을 만든다. 다만 이 봇은
판정봇보다 한 단계 더 어렵다 — "이게 주문인가"는 키워드로 어느 정도 근사할 수
있지만, "경계를 어디서 끊어야 하는가"는 화제 전환/수신자 전환을 실제로 이해해야
하는 문제라 정규식으로는 안전하게 할 수 없다.

그래서 이 규칙기반 버전의 역할을 의도적으로 좁혔다: 실제로 텍스트를 자르지 않고,
"여러 주문이 섞였을 가능성이 있는지"만 감지한다. 신호가 잡히면 임의로 나누지 않고
split_status를 "확인필요"로 남겨 사람에게 넘긴다(설계문서 원칙 그대로). 즉 이 버전은
golden_set 005/006 같은 실제 2건짜리 통화를 "정확히 2개로 자동 분리"하지는 못하고,
대신 "이거 안에 여러 건 있는 것 같다"까지만 감지한다 — 이것도 알려진 한계로 남겨둠
(test_order_split_bot.py에서 명시적으로 표시, 숨기지 않음).

나중에 LLM으로 교체할 때: SPLIT_ENGINE 자리에 실제 분리(경계 포함)까지 하는 함수를
넣으면 된다.

12봇_kind분류표.yaml 대응:
  io.reads:  stt_text, ocr_text, raw_text, order_classification
  io.writes: order_segments, split_status, bundle_id, bundle_sequence
"""

import re
import uuid

import llm_client

_TITLE_PATTERN = re.compile(r"([가-힣]{2,4})(면장|동장|이장|사장|대표|원장|과장|팀장)")
_PRICE_PATTERN = re.compile(r"\d+\s*(만\s*원|원|마넌)")
_CELEBRATION_PATTERN = re.compile(r"축하합니다|축하해|근조|삼가")

_SYSTEM_PROMPT = """당신은 꽃집(온천꽃식물원) 주문 접수 원문에서 "독립된 주문이 여러 건 섞여
있는지"를 판단하고, 확신이 있을 때만 실제로 경계를 나누는 담당자입니다.

원칙(반드시 지킬 것):
- 경계(어디서 잘라야 하는지)가 조금이라도 애매하면 절대 임의로 나누지 마세요.
  이 경우 전체 원문을 세그먼트 1개로 두고 split_status를 "확인필요"로 남기세요.
- 서로 다른 수신자(직함/기관)나 서로 다른 금액이 명확히 분리된 문맥으로 여러 번
  나오고, 그 경계가 문장 구조상 확실할 때만 실제로 여러 세그먼트로 나누고
  split_status를 "완료"로 표시하세요.
- 절대 존재하지 않는 정보를 지어내지 마세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "order_segments": [{"segment_text": "<이 세그먼트에 해당하는 원문 부분>", "split_confidence": <0.0~1.0>}, ...],
  "split_status": "완료" 또는 "확인필요",
  "confidence": <0.0~1.0>,
  "reason": "<한 문장 이유>"
}
"""


def _split_rule_based(text: str) -> dict:
    """
    규칙기반 분리 로직 — 실제 경계는 긋지 않고 "여러 건일 가능성"만 감지한다.
    가능성 신호가 하나라도 잡히면 split_status를 확인필요로 강제한다
    (설계문서 규칙: "분리 기준이 애매하면 임의로 나누지 않는다").
    """
    titles = _TITLE_PATTERN.findall(text)
    distinct_titles = {t[0] + t[1] for t in titles}  # 예: {"부곡면장", "북면장"}
    price_count = len(_PRICE_PATTERN.findall(text))
    celebration_count = len(_CELEBRATION_PATTERN.findall(text))

    multi_signals = []
    if len(distinct_titles) >= 2:
        multi_signals.append("서로 다른 수신자 직함 " + str(sorted(distinct_titles)))
    if price_count >= 2:
        multi_signals.append("가격 언급 " + str(price_count) + "회")
    if celebration_count >= 2:
        multi_signals.append("축하/근조 문구 " + str(celebration_count) + "회")

    if multi_signals:
        return {
            "order_segments": [{"segment_text": text, "split_confidence": 0.4}],
            "split_status": "확인필요",
            "confidence": 0.4,
            "reason": "여러 주문 가능성 신호 감지(" + "; ".join(multi_signals)
                      + ") — 규칙기반은 경계를 안전하게 못 그어 분리하지 않고 사람 확인으로 넘김",
        }

    return {
        "order_segments": [{"segment_text": text, "split_confidence": 0.9}],
        "split_status": "완료",
        "confidence": 0.9,
        "reason": "여러 주문 신호 없음 — 단일 주문으로 판단",
    }


def _split_llm(text: str) -> dict:
    """2026-07-17 신설: 실제 Claude 호출 버전. manifest.yaml의 tier: mid 사용."""
    result = llm_client.call_llm_json(
        tier="mid",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=f"원문:\n{text}",
    )
    segments = result.get("order_segments")
    if not isinstance(segments, list) or not segments:
        raise llm_client.LLMUnavailableError(f"order_segments가 비어있거나 형식이 이상함: {segments!r}")
    if result.get("split_status") not in ("완료", "확인필요"):
        raise llm_client.LLMUnavailableError(f"split_status 값이 이상함: {result.get('split_status')!r}")
    return result


def _split_auto(text: str) -> dict:
    """LLM 우선, 실패 시 규칙기반 자동 대체(다른 5개 model 봇과 동일한 안전망 패턴)."""
    try:
        return _split_llm(text)
    except llm_client.LLMUnavailableError as e:
        result = dict(_split_rule_based(text))
        result["reason"] = result["reason"] + f" [LLM 호출 실패로 규칙기반 대체: {e}]"
        return result


# 2026-07-17부터 LLM(Claude) 우선, 실패 시 규칙기반 자동 대체.
SPLIT_ENGINE = _split_auto


def split_order(text: str, bundle_id: str = None) -> dict:
    """
    공개 API. bundle_id를 안 주면 새로 발급한다. order_segments의 각 원소에
    bundle_id/bundle_sequence(index/total)를 실어 보낸다 — 분리와 동시에 부여한다는
    설계 그대로(io_note 참고).
    """
    result = SPLIT_ENGINE(text)
    bundle_id = bundle_id or ("bundle_" + str(uuid.uuid4())[:8])
    segments = result["order_segments"]
    total = len(segments)

    enriched_segments = []
    for i, seg in enumerate(segments, start=1):
        enriched = dict(seg)
        enriched["bundle_id"] = bundle_id
        enriched["bundle_sequence"] = {"index": i, "total": total}
        enriched_segments.append(enriched)

    return {
        "order_segments": enriched_segments,
        "split_status": result["split_status"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "bundle_id": bundle_id,
    }
