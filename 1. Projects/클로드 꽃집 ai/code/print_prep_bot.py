"""
print_prep_bot.py — 출력준비봇 (12봇_kind분류표.yaml의 print_prep_bot 실제 구현)

역할: 확정 주문(storage_bot이 저장한 order 레코드)에서 인쇄용 산출물 4종(주문서/리본/
배송메모/기사요약)을 만든다. 템플릿 채우기만 하고 판단은 하지 않는다 — 값이 없으면(None)
임의로 채우지 않고 "확인 필요"라고 그대로 표시한다(프로젝트 전체 원칙: 불확실한 값 임의
채우기 금지).

golden_set의 structured_extract 필드명이 항목마다 조금씩 다르다는 점(예: 001은
recipient_org/sender_title, 006은 recipient_title/recipient_region)을 그대로 반영해
여러 후보 필드명 중 처음 채워진 값을 쓰도록 만들었다 — 필드명을 하나로 강제 통일하지
않는다(golden_set.yaml schema_note: "나중에 매핑 예정"과 같은 맥락).

12봇_kind분류표.yaml 대응:
  io.reads:  order
  io.writes: order_print, ribbon_print, delivery_memo, driver_summary
"""

_UNKNOWN = "확인 필요"


def _field(confirmed_fields, *keys):
    """confirmed_fields에서 keys 중 처음 발견되는 non-None 값을 반환. 없으면 "확인 필요"."""
    for k in keys:
        v = (confirmed_fields or {}).get(k)
        if v is not None:
            return v
    return _UNKNOWN


def prepare_print(order):
    """
    공개 API. order = storage_bot.save_order()/get_order()가 반환하는 레코드 형태를
    기대한다(order_id, bundle_id, bundle_sequence, confirmed_fields, manual_edits 등).
    """
    confirmed = order.get("confirmed_fields") or {}
    order_id = order.get("order_id")

    recipient = _field(confirmed, "recipient_org", "recipient_title", "recipient_region")
    recipient_name = _field(confirmed, "recipient_name")
    sender = _field(confirmed, "sender_org", "sender_title")
    sender_name = _field(confirmed, "sender_name")
    product = _field(confirmed, "product", "product_name")
    amount = _field(confirmed, "amount_krw", "price")
    ribbon_raw = _field(confirmed, "ribbon_message_raw")
    ribbon_final = _field(confirmed, "ribbon_message_final")

    order_print = {
        "order_id": order_id,
        "bundle_id": order.get("bundle_id"),
        "bundle_sequence": order.get("bundle_sequence"),
        "recipient": recipient,
        "recipient_name": recipient_name,
        "sender": sender,
        "sender_name": sender_name,
        "product": product,
        "amount_krw": amount,
        "ribbon_message_final": ribbon_final,
        "확인_필요_필드": order.get("확인_필요_필드", []),
    }

    ribbon_print = {
        "order_id": order_id,
        "ribbon_message_raw": ribbon_raw,
        "ribbon_message_final": ribbon_final,
        "product": product,
    }

    delivery_memo = (
        "[배송메모] 주문 " + str(order_id) + " - 수령: " + str(recipient)
        + ("(" + str(recipient_name) + ")" if recipient_name != _UNKNOWN else "")
        + " / 상품: " + str(product) + " / 금액: " + str(amount)
    )

    driver_summary = (
        "수령지: " + str(recipient) + " | 상품: " + str(product) + " | 리본: " + str(ribbon_final)
    )

    return {
        "order_print": order_print,
        "ribbon_print": ribbon_print,
        "delivery_memo": delivery_memo,
        "driver_summary": driver_summary,
    }
