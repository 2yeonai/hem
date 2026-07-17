"""
review_manager_bot.py - 검수매니저 (규칙기반 임시 버전)

역할: 여러 상류 stage(order_draft_bot, correction_bot, ribbon_price_bot,
order_split_bot)의 confidence/후보값/missing_fields를 종합해, 사람 검수자
(human_reviewer)에게 무엇을 확인시켜야 하는지 체크리스트(review_checklist)와
우선순위 색상(review_priority), 편집 가능 필드 목록(editable_fields)을 만든다.

kind_rationale(12봇_kind분류표.yaml): "quality_gate의 특수화 — '통과/사람
에스컬레이션' 분기를 출력하는 model stage(사람 자체는 아님)". 다만 이 파이프
라인에서 human_reviewer는 depends_on 그래프상 항상 실행되는 stage라(주문
분류 게이트처럼 조건부로 건너뛸 수 있는 stop_condition이 없음), 이 봇의
"에스컬레이션" 의미는 "사람 검수를 건너뛴다"가 아니라 "그 검수를 얼마나
급하게/꼼꼼히 봐야 하는지" 우선순위를 매기는 것으로 해석했다 — 이 해석 자체가
확정된 사양이 아니라 이 구현에서 채택한 작업 가정이라는 점을 명시해둔다.

다른 model 스테이지와 같은 이유(API 키 없음)로 지금은 규칙기반 버전을 만든다.

review_priority 색상 규칙 (2026-07-14, 이 구현에서 제안 — 12봇_kind분류표.yaml
open_questions에 "review_manager_bot.check의 confidence 매핑: ... 미정"으로
명시된 항목이라 실측 없이 제안하는 것임, 확인 필요):
  - 빨강: split_status == "확인필요"(다중주문 가능성) 이거나 product_name/price
    같은 핵심(배송·정산에 필요한) 필드가 없을 때.
  - 노랑: candidates(correction_bot이 감지한 불확실 phrase)가 있거나
    missing_fields가 3개를 초과할 때.
  - 파랑: missing_fields가 일부 있지만(주로 이름류) 핵심 필드는 다 채워져
    급하지 않은 경우.
  - 초록: missing_fields/candidates가 전혀 없고 split_status도 완료일 때.

알려진 한계 (숨기지 않고 명시):
  - 위 색상 규칙 자체가 실측 없이 제안된 것 — 실제 운영 데이터로 임계값을
    재조정해야 할 수 있다(yaml open_questions와 동일한 사항).
  - recipient_name/sender_name은 order_draft_bot이 애초에 추출을 시도하지
    않으므로 거의 항상 missing_fields에 잡힌다 — 이 자체는 매 주문마다
    "이름 확인 필요"를 반복 표시하게 만드는데, 실제 서비스에서는 노이즈가
    될 수 있다(단, "값을 임의로 채우지 않는다" 원칙상 지금은 그대로 둠).
  - correction_bot/order_draft_bot이 상류(order_split_bot)의 known
    limitation을 물려받았다면(golden_set call_007처럼 미분리 원문), 이
    봇은 그 오염된 값을 바탕으로 체크리스트를 만들 뿐 원인을 스스로
    진단하지 못한다 — 다만 split_status=확인필요 신호 자체는 그대로
    전달되므로 빨강으로 잡히기는 한다.

12봇_kind분류표.yaml 대응:
  io.reads:  order_draft, field_confidence, field_sources, missing_fields,
             candidates, ribbon_message_raw, ribbon_message_final, product_name,
             price, quantity, correction_log, split_status
  io.writes: review_checklist, review_priority, editable_fields
"""

import llm_client

_CRITICAL_FIELD_NAMES = ["product_name", "price"]
_NAME_FIELDS = {"recipient_name", "sender_name"}

_SYSTEM_PROMPT = """당신은 꽃집(온천꽃식물원) 주문 파이프라인의 검수 매니저입니다.
여러 상류 단계의 결과(order_draft, missing_fields, candidates, split_status,
product_name, price, quantity 등)를 받아서, 사람 검수자에게 무엇을 확인시켜야 하는지
review_checklist(문장 목록)와 review_priority(빨강/노랑/파랑/초록 중 하나)를 만드세요.

우선순위 판단 기준:
- 빨강: split_status가 확인필요이거나, product_name/price처럼 배송·정산에 꼭 필요한
  핵심 필드가 없을 때
- 노랑: candidates(불확실 후보)가 있거나 missing_fields가 3개 초과일 때
- 파랑: missing_fields가 일부(주로 이름류) 있지만 핵심 필드는 다 채워져 급하지 않을 때
- 초록: missing_fields/candidates가 전혀 없고 split_status도 완료일 때

절대 원칙: recipient_name/sender_name이 없는 것은 이 스킬의 의도된 설계입니다
(이름을 함부로 추측하면 실사고로 이어진 이력이 있음) - 이것 때문에 priority를
필요 이상으로 높이지 말고, 체크리스트에는 "사람이 직접 채워야 함"으로만 표시하세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "review_checklist": ["<확인 항목 문장>", ...],
  "review_priority": "빨강"|"노랑"|"파랑"|"초록",
  "editable_fields": ["<필드명>", ...],
  "reason": "<한 문장 이유>"
}
"""


def _build_checklist(order_draft, missing_fields, candidates, split_status,
                      product_name, price, quantity):
    checklist = []

    if split_status == "확인필요":
        checklist.append(
            "split_status=확인필요 - 통화/문자 1건 안에 주문이 여러 건 섞여 있을 "
            "가능성 있음, 분리 여부부터 확인 필요"
        )

    for c in candidates or []:
        phrase = c.get("phrase", "")
        note = c.get("note", "")
        checklist.append("correction_bot 감지 불확실 phrase: '" + str(phrase) + "' - " + str(note))

    if product_name is None:
        checklist.append("product_name 없음 - 배송에 필요한 핵심 값, 확인 필요")
    if price is None:
        checklist.append("price 없음 - 정산에 필요한 핵심 값, 확인 필요")

    non_name_missing = [f for f in (missing_fields or []) if f not in _NAME_FIELDS]
    for f in non_name_missing:
        checklist.append(f + " 없음(order_draft 단계에서 추출 못함) - 확인 필요")

    if _NAME_FIELDS.intersection(missing_fields or []):
        checklist.append(
            "recipient_name/sender_name - 이 규칙기반 버전은 이름을 아예 추출하지 "
            "않음(설계상 의도) - 사람이 직접 채워야 함"
        )

    if quantity is None:
        checklist.append("quantity 없음 - 기본값 가정 안 함, 수량 확인 필요")

    return checklist


def _decide_priority(missing_fields, candidates, split_status, product_name, price):
    missing_fields = missing_fields or []
    candidates = candidates or []

    has_critical_missing = product_name is None or price is None

    if split_status == "확인필요" or has_critical_missing:
        return "빨강"
    if candidates or len(missing_fields) > 3:
        return "노랑"
    if missing_fields:
        return "파랑"
    return "초록"


def _review_rule_based(order_draft, field_confidence, field_sources, missing_fields,
                        candidates, ribbon_message_raw, ribbon_message_final,
                        product_name, price, quantity, correction_log, split_status) -> dict:
    """
    규칙기반 검수 우선순위/체크리스트 산정 로직.

    나중에 LLM으로 교체할 때: 이 함수와 같은 시그니처를 만들어서 REVIEW_ENGINE에
    대입하면 된다(build_review() 쪽은 안 바꿔도 됨).
    """
    order_draft = order_draft or {}

    checklist = _build_checklist(
        order_draft, missing_fields, candidates, split_status, product_name, price, quantity
    )
    priority = _decide_priority(missing_fields, candidates, split_status, product_name, price)

    editable_fields = sorted(set(
        list(order_draft.keys())
        + ["ribbon_message_raw", "ribbon_message_final", "product_name", "price", "quantity"]
    ))

    return {
        "review_checklist": checklist,
        "review_priority": priority,
        "editable_fields": editable_fields,
        "reason": (
            str(len(checklist)) + "개 확인 항목 생성, split_status=" + str(split_status)
            + ", priority=" + priority
        ),
    }


def _review_llm(order_draft, field_confidence, field_sources, missing_fields,
                 candidates, ribbon_message_raw, ribbon_message_final,
                 product_name, price, quantity, correction_log, split_status) -> dict:
    """2026-07-17 신설: 실제 Claude 호출 버전. manifest.yaml의 tier: mid 사용."""
    user_prompt = (
        f"order_draft: {order_draft}\nmissing_fields: {missing_fields}\n"
        f"candidates: {candidates}\nsplit_status: {split_status}\n"
        f"product_name: {product_name}\nprice: {price}\nquantity: {quantity}\n"
        f"correction_log: {correction_log}"
    )
    result = llm_client.call_llm_json(tier="mid", system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt)
    if result.get("review_priority") not in ("빨강", "노랑", "파랑", "초록"):
        raise llm_client.LLMUnavailableError(f"review_priority 값이 이상함: {result.get('review_priority')!r}")
    if not isinstance(result.get("review_checklist"), list):
        raise llm_client.LLMUnavailableError("review_checklist가 리스트가 아님")
    result.setdefault("editable_fields", sorted(set(
        list((order_draft or {}).keys())
        + ["ribbon_message_raw", "ribbon_message_final", "product_name", "price", "quantity"]
    )))
    return result


def _review_auto(order_draft, field_confidence, field_sources, missing_fields,
                  candidates, ribbon_message_raw, ribbon_message_final,
                  product_name, price, quantity, correction_log, split_status) -> dict:
    """LLM 우선, 실패 시 규칙기반 자동 대체."""
    try:
        return _review_llm(
            order_draft, field_confidence, field_sources, missing_fields, candidates,
            ribbon_message_raw, ribbon_message_final, product_name, price, quantity,
            correction_log, split_status,
        )
    except llm_client.LLMUnavailableError as e:
        result = dict(_review_rule_based(
            order_draft, field_confidence, field_sources, missing_fields, candidates,
            ribbon_message_raw, ribbon_message_final, product_name, price, quantity,
            correction_log, split_status,
        ))
        result["reason"] = result["reason"] + f" [LLM 호출 실패로 규칙기반 대체: {e}]"
        return result


# 2026-07-17부터 LLM(Claude) 우선, 실패 시 규칙기반 자동 대체.
REVIEW_ENGINE = _review_auto


def build_review(order_draft=None, field_confidence=None, field_sources=None,
                  missing_fields=None, candidates=None, ribbon_message_raw=None,
                  ribbon_message_final=None, product_name=None, price=None,
                  quantity=None, correction_log=None, split_status=None) -> dict:
    """
    공개 API. 상류 stage들의 출력을 받아 review_checklist/review_priority/
    editable_fields를 만든다.
    반환: {"review_checklist", "review_priority", "editable_fields", "reason"}
    """
    return REVIEW_ENGINE(
        order_draft, field_confidence, field_sources, missing_fields, candidates,
        ribbon_message_raw, ribbon_message_final, product_name, price, quantity,
        correction_log, split_status,
    )
