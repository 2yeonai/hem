"""
test_sms_ledger_bot.py - sms_ledger_bot.py를 golden_set(005/006, 같은 bundle) 기반으로 검증

005만 저장된 상태에서 발송하면 bundle_status는 아직 진행중이어야 하고, 006까지
저장된 뒤 발송하면 완료로 바뀌어야 한다 — storage_bot의 get_bundle_status 카운트
비교 로직을 sms_ledger_bot이 그대로 재사용하는지 확인한다(test_storage_bot.py의
005/006 시나리오와 동일한 데이터를 사용).

실행: python3 test_sms_ledger_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import storage_bot
import delivery_photo_bot as dpb
import sms_ledger_bot as slb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"
TEST_DB_PATH = Path(__file__).parent / "test_sms_ledger.json"

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    extra = "  (" + detail + ")" if detail else ""
    print("[" + status + "] " + label + extra)


def reset_db():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except PermissionError:
            storage_bot._save(TEST_DB_PATH, {"orders": {}, "workflow_events": []})


def main():
    reset_db()
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}
    e005, e006 = entries["005"], entries["006"]
    bundle_id = e005["source_call_id"]

    saved_005 = storage_bot.save_order(
        confirmed_fields=e005["structured_extract"], manual_edits={}, approval_action="주문확정",
        bundle_id=bundle_id, bundle_sequence={"index": 1, "total": 2}, db_path=TEST_DB_PATH,
    )
    photo_005 = dpb.capture_delivery_photo({"dispatch_id": "d1"}, photo_uri=None)
    ledger_005 = slb.send_and_ledger(
        order=saved_005, delivery_photo=photo_005["delivery_photo"], photo_status=photo_005["photo_status"],
        bundle_id=bundle_id, bundle_sequence={"index": 1, "total": 2}, db_path=TEST_DB_PATH,
    )
    check("005 발송 후 message_result 상태는 발송완료(목업)", ledger_005["message_result"]["status"] == "발송완료")
    check(
        "005만 저장된 시점엔 bundle_status가 아직 진행중",
        ledger_005["bundle_status"] == "진행중",
        "actual=" + ledger_005["bundle_status"],
    )

    saved_006 = storage_bot.save_order(
        confirmed_fields=e006["structured_extract"], manual_edits={}, approval_action="주문확정",
        bundle_id=bundle_id, bundle_sequence={"index": 2, "total": 2}, db_path=TEST_DB_PATH,
    )
    photo_006 = dpb.capture_delivery_photo({"dispatch_id": "d2"}, photo_uri="mock://photo/006.jpg")
    ledger_006 = slb.send_and_ledger(
        order=saved_006, delivery_photo=photo_006["delivery_photo"], photo_status=photo_006["photo_status"],
        bundle_id=bundle_id, bundle_sequence={"index": 2, "total": 2}, db_path=TEST_DB_PATH,
    )
    check(
        "006까지 저장 후 발송하면 bundle_status가 완료로 바뀜",
        ledger_006["bundle_status"] == "완료",
        "actual=" + ledger_006["bundle_status"],
    )
    check("006 message_job에 bundle_id가 pass-through됨", ledger_006["message_job"]["bundle_id"] == bundle_id)
    check("006 history_log에 event_type=sms_sent 기록", ledger_006["history_log"]["event_type"] == "sms_sent")

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    print("")
    print(str(passed) + "/" + str(total) + " checks passed")

    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except PermissionError:
            pass
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
