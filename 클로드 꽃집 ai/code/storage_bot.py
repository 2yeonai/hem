"""
storage_bot.py — 저장봇 (12봇_kind분류표.yaml의 storage_bot 실제 구현)

역할: 사람 검수(human_reviewer)를 통과한 주문 정보를 실제로 저장한다.
저장소: JSON 파일 1개(flower_orders.json, 이 파일과 같은 폴더에 자동 생성) —
        "간단한 데이터베이스"를 별도 서버 설치 없이 파일 하나로 구현한 것.
        (처음엔 SQLite로 만들었으나, 이 폴더가 클라우드 동기화 마운트 폴더라
        SQLite가 필요로 하는 파일 잠금(lock)이 제대로 안 돼 "disk I/O error"가
        발생함을 테스트 중 확인 — 그래서 매번 파일 전체를 읽고 고쳐 다시 쓰는
        JSON 방식으로 바꿈. 사람이 파일을 직접 열어봐도 내용을 알아볼 수 있다는
        장점도 있음.)

반드시 지키는 규칙 (프로젝트 전체 원칙 그대로 코드에 반영):
  1. 확실하지 않은 값(None/null)은 절대 임의로 채우지 않는다. None은 그대로
     저장하고, 저장 시점에 자동으로 "확인_필요_필드" 목록에 담아 남긴다.
  2. 같은 통화/문자 묶음(bundle_id)에서 나온 주문이 여러 건이면, 묶음 안에서
     몇 번째인지(bundle_sequence: index/total)를 함께 저장한다. 묶음의 total개가
     모두 저장되면 조회 시 bundle_status가 "완료"로 계산된다(실제 최종 갱신은
     설계상 sms_ledger_bot 몫이지만, 저장 단계에서도 확인할 수 있게 조회 함수를 둠).
  3. 기존 주문을 고치면(update_order) version을 1 올리고, 무엇이 바뀌었는지
     workflow_events에 기록을 남긴다(예전 값을 덮어써서 잃어버리지 않음).

12봇_kind분류표.yaml 대응:
  io.reads:  confirmed_fields, manual_edits, approval_action, bundle_id, bundle_sequence
  io.writes: order, workflow_event, version
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "flower_orders.json"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _find_missing_fields(confirmed_fields):
    return [k for k, v in (confirmed_fields or {}).items() if v is None]


def _load(db_path):
    if not Path(db_path).exists():
        return {"orders": {}, "workflow_events": []}
    with open(db_path, encoding="utf-8") as f:
        return json.load(f)


def _save(db_path, data):
    db_path = Path(db_path)
    tmp_path = db_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(db_path)


def init_db(db_path=DB_PATH):
    if not Path(db_path).exists():
        _save(db_path, {"orders": {}, "workflow_events": []})


def save_order(confirmed_fields, manual_edits=None, approval_action="주문확정",
               bundle_id=None, bundle_sequence=None, db_path=DB_PATH):
    data = _load(db_path)
    order_id = str(uuid.uuid4())[:8]
    missing = _find_missing_fields(confirmed_fields)
    now = _now()

    record = {
        "order_id": order_id,
        "bundle_id": bundle_id,
        "bundle_sequence": dict(bundle_sequence) if bundle_sequence else None,
        "approval_action": approval_action,
        "confirmed_fields": confirmed_fields,
        "manual_edits": manual_edits or {},
        "확인_필요_필드": missing,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    data["orders"][order_id] = record
    data["workflow_events"].append({
        "order_id": order_id,
        "event_type": "created",
        "detail": {"approval_action": approval_action, "확인_필요_필드": missing},
        "created_at": now,
    })
    _save(db_path, data)
    return dict(record)


def update_order(order_id, confirmed_fields=None, manual_edits=None,
                  approval_action=None, db_path=DB_PATH):
    data = _load(db_path)
    existing = data["orders"].get(order_id)
    if existing is None:
        raise ValueError("order_id=" + order_id + " 저장된 적 없음 — 수정 불가(먼저 save_order 필요)")

    new_confirmed = confirmed_fields if confirmed_fields is not None else existing["confirmed_fields"]
    new_manual = manual_edits if manual_edits is not None else existing["manual_edits"]
    new_approval = approval_action if approval_action is not None else existing["approval_action"]
    missing = _find_missing_fields(new_confirmed)
    now = _now()

    existing["confirmed_fields"] = new_confirmed
    existing["manual_edits"] = new_manual
    existing["approval_action"] = new_approval
    existing["확인_필요_필드"] = missing
    existing["version"] = existing["version"] + 1
    existing["updated_at"] = now

    data["workflow_events"].append({
        "order_id": order_id,
        "event_type": "updated",
        "detail": {"approval_action": new_approval, "확인_필요_필드": missing},
        "created_at": now,
    })
    _save(db_path, data)
    return dict(existing)


def get_order(order_id, db_path=DB_PATH):
    data = _load(db_path)
    record = data["orders"].get(order_id)
    return dict(record) if record else None


def list_orders(bundle_id=None, db_path=DB_PATH):
    data = _load(db_path)
    records = list(data["orders"].values())
    records.sort(key=lambda r: r["created_at"])
    if bundle_id:
        records = [r for r in records if r["bundle_id"] == bundle_id]
    return [dict(r) for r in records]


def get_bundle_status(bundle_id, db_path=DB_PATH):
    orders = list_orders(bundle_id=bundle_id, db_path=db_path)
    if not orders:
        return {"bundle_id": bundle_id, "saved_count": 0, "total": None, "bundle_status": "확인 필요"}
    total = orders[0]["bundle_sequence"]["total"] if orders[0]["bundle_sequence"] else None
    saved_count = len(orders)
    if total is None:
        status = "확인 필요"
    elif saved_count >= total:
        status = "완료"
    else:
        status = "진행중"
    return {"bundle_id": bundle_id, "saved_count": saved_count, "total": total, "bundle_status": status}
