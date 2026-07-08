"""
test_storage_bot.py - storage_bot.py를 golden_set.yaml의 실제 사례로 검증

사용한 golden_set 항목: 001(문자, 단독 주문), 005/006(통화 1건에서 나온 주문 2건 -
같은 bundle_id를 가짐). 002~004는 order_status가 non_order라 애초에 저장 단계까지
오지 않는 케이스라 이 테스트에서는 제외.

실행: python3 test_storage_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import storage_bot

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"
TEST_DB_PATH = Path(__file__).parent / "test_flower_orders.json"

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

    e001 = entries["001"]
    saved_001 = storage_bot.save_order(
        confirmed_fields=e001["structured_extract"],
        manual_edits={},
        approval_action="주문확정",
        bundle_id="single_" + e001["id"],
        bundle_sequence={"index": 1, "total": 1},
        db_path=TEST_DB_PATH,
    )
    check("001 saved (order_id issued)", bool(saved_001 and saved_001.get("order_id")))

    missing_001 = set(saved_001["확인_필요_필드"])
    check(
        "001: recipient_name/sender_name are None so auto-flagged as needing confirmation",
        {"recipient_name", "sender_name"}.issubset(missing_001),
        "actual=" + str(sorted(missing_001)),
    )
    check(
        "001: recipient_org kept as-is (no data loss)",
        saved_001["confirmed_fields"]["recipient_org"] == "창녕군청 재무과",
    )
    status_001 = storage_bot.get_bundle_status("single_" + e001["id"], db_path=TEST_DB_PATH)
    check(
        "001: single-order bundle (total=1) is 완료 immediately after save",
        status_001["bundle_status"] == "완료",
        "actual=" + str(status_001),
    )

    e005, e006 = entries["005"], entries["006"]
    bundle_id = e005["source_call_id"]
    check("005/006 share the same source_call_id", bundle_id == e006["source_call_id"])

    saved_005 = storage_bot.save_order(
        confirmed_fields=e005["structured_extract"],
        manual_edits={},
        approval_action="주문확정",
        bundle_id=bundle_id,
        bundle_sequence={"index": 1, "total": 2},
        db_path=TEST_DB_PATH,
    )
    mid_status = storage_bot.get_bundle_status(bundle_id, db_path=TEST_DB_PATH)
    check(
        "after only 005 is saved, bundle is still 진행중 (waiting on 2nd)",
        mid_status["bundle_status"] == "진행중",
        "actual=" + str(mid_status),
    )

    saved_006 = storage_bot.save_order(
        confirmed_fields=e006["structured_extract"],
        manual_edits={},
        approval_action="주문확정",
        bundle_id=bundle_id,
        bundle_sequence={"index": 2, "total": 2},
        db_path=TEST_DB_PATH,
    )
    final_status = storage_bot.get_bundle_status(bundle_id, db_path=TEST_DB_PATH)
    check(
        "after both 005+006 saved, bundle flips to 완료",
        final_status["bundle_status"] == "완료",
        "actual=" + str(final_status),
    )

    missing_006 = set(saved_006["확인_필요_필드"])
    check(
        "006: recipient_region is None (북면 place-name ambiguity) so kept flagged",
        "recipient_region" in missing_006,
        "actual=" + str(sorted(missing_006)),
    )
    check(
        "006: amount_krw=50000 is a confirmed value, not in the flagged list",
        "amount_krw" not in missing_006,
    )

    listed = storage_bot.list_orders(bundle_id=bundle_id, db_path=TEST_DB_PATH)
    check(
        "listing by bundle_id returns 005,006 in order (index 1,2)",
        [o["bundle_sequence"]["index"] for o in listed] == [1, 2],
    )

    updated = storage_bot.update_order(
        saved_001["order_id"],
        confirmed_fields=dict(saved_001["confirmed_fields"], sender_name="백승흔"),
        db_path=TEST_DB_PATH,
    )
    check("update bumps version 1 -> 2", updated["version"] == 2, "actual version=" + str(updated["version"]))
    check(
        "after update, sender_name no longer in the flagged list",
        "sender_name" not in updated["확인_필요_필드"],
    )

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
