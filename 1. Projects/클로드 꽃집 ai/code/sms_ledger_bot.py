"""
sms_ledger_bot.py — 문자장부봇 (12봇_kind분류표.yaml의 sms_ledger_bot 실제 구현)

역할: 배송 완료 문자(mock/real)를 보내고 즉시 장부화한다. 문자 발송을 마치면 같은
bundle_id로 이미 storage_bot에 저장된 주문 수를 세어 bundle_sequence.total과 비교해서
bundle_status(진행중/완료)를 갱신한다 — 개수 비교는 판단이 필요 없는 카운트 작업이라
kind: local 그대로 유지한다(shared_context.bundle_status io_note 참고). 실제 카운트
로직은 storage_bot.get_bundle_status()를 그대로 재사용한다(중복 구현 금지).

알려진 한계(숨기지 않고 명시): 실제 문자 발송 게이트웨이(알리고 등)는 이 작업 환경에
연동돼 있지 않다 — 아래 SEND_ENGINE은 항상 성공을 반환하는 목업이다. 실제 게이트웨이가
생기면 이 이름만 바꿔치면 된다(다른 봇들의 *_ENGINE 패턴과 동일).

12봇_kind분류표.yaml 대응:
  io.reads:  order, delivery_photo, photo_status, bundle_id, bundle_sequence
  io.writes: message_job, message_result, history_log, bundle_status
"""

import uuid
from datetime import datetime, timezone

import storage_bot

DEFAULT_DB_PATH = storage_bot.DB_PATH


def _now():
    return datetime.now(timezone.utc).isoformat()


def _mock_send_engine(to, content):
    """목업 문자 발송 엔진 — 실제 게이트웨이 미연동, 항상 성공 처리."""
    return {"status": "발송완료", "provider": "mock", "sent_at": _now()}


SEND_ENGINE = _mock_send_engine


def send_and_ledger(order, delivery_photo, photo_status, bundle_id, bundle_sequence,
                     to=None, db_path=DEFAULT_DB_PATH):
    """
    공개 API. order/delivery_photo/photo_status로 문자 내용을 만들어 (mock) 발송하고,
    발송 결과를 message_result에, 발송 이력을 history_log에 남긴 뒤, bundle_id 기준
    저장 완료 개수를 세어 bundle_status를 계산한다. bundle_sequence 자체는 여기서
    직접 쓰이지 않는다 — 실제 개수 비교는 DB에 이미 저장된 bundle_sequence.total 값
    (storage_bot.get_bundle_status)을 기준으로 하기 때문에, 인자로는 io 계약(reads)을
    맞추기 위해 받아두기만 한다.
    """
    job_id = "msg_" + str(uuid.uuid4())[:8]
    confirmed = order.get("confirmed_fields") or {}
    product = confirmed.get("product") or confirmed.get("product_name") or "확인 필요"

    content = (
        "[온천꽃식물원] 주문 " + str(order.get("order_id")) + " 배송이 완료되었습니다. "
        "상품: " + str(product) + ". "
        + ("사진 확인: " + delivery_photo if photo_status == "완료" and delivery_photo else "배송사진 대기중")
    )

    message_job = {
        "job_id": job_id,
        "order_id": order.get("order_id"),
        "bundle_id": bundle_id,
        "channel": "sms",
        "to": to or "확인 필요",
        "content": content,
    }

    send_result = SEND_ENGINE(message_job["to"], content)
    message_result = dict(send_result)
    message_result["job_id"] = job_id

    history_log = {
        "order_id": order.get("order_id"),
        "bundle_id": bundle_id,
        "event_type": "sms_sent",
        "detail": {"job_id": job_id, "status": send_result["status"]},
        "created_at": _now(),
    }

    bundle_info = storage_bot.get_bundle_status(bundle_id, db_path=db_path) if bundle_id else None
    bundle_status = bundle_info["bundle_status"] if bundle_info else "확인 필요"

    return {
        "message_job": message_job,
        "message_result": message_result,
        "history_log": history_log,
        "bundle_status": bundle_status,
    }
