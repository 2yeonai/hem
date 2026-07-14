"""
dispatch_bot.py — 배송전달봇 (12봇_kind분류표.yaml의 dispatch_bot 실제 구현)

역할: 기사 화면에 필요한 최소 정보(배송지/연락처/상품/리본/사진버튼)만 라우팅한다.
판단 없음 — 이미 만들어진 driver_summary/delivery_memo/order를 기사에게 전달하는
기록(dispatch_record)만 만든다.

12봇_kind분류표.yaml 대응:
  io.reads:  driver_summary, delivery_memo, order
  io.writes: dispatch_record
"""

import uuid
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def dispatch(order, driver_summary, delivery_memo, driver_id=None):
    """
    공개 API. driver_id를 안 주면 "미배정"으로 남긴다(임의로 기사를 배정하지 않음).
    """
    return {
        "dispatch_record": {
            "dispatch_id": "dispatch_" + str(uuid.uuid4())[:8],
            "order_id": order.get("order_id"),
            "bundle_id": order.get("bundle_id"),
            "driver_id": driver_id or "미배정",
            "driver_summary": driver_summary,
            "delivery_memo": delivery_memo,
            "status": "배송중",
            "dispatched_at": _now(),
        }
    }
