"""
test_dispatch_bot.py - dispatch_bot.py를 golden_set(001) 기반 저장 레코드로 검증

실행: python3 test_dispatch_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import storage_bot
import print_prep_bot as ppb
import dispatch_bot as db

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"
TEST_DB_PATH = Path(__file__).parent / "test_dispatch.json"

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

    saved = storage_bot.save_order(
        confirmed_fields=e001["structured_extract"], manual_edits={}, approval_action="주문확정",
        bundle_id="single_001", bundle_sequence={"index": 1, "total": 1}, db_path=TEST_DB_PATH,
    )
    printed = ppb.prepare_print(saved)

    r1 = db.dispatch(saved, printed["driver_summary"], printed["delivery_memo"])
    rec = r1["dispatch_record"]
    check("dispatch_record에 order_id가 그대로 연결됨", rec["order_id"] == saved["order_id"])
    check("dispatch_record에 bundle_id가 pass-through됨", rec["bundle_id"] == "single_001")
    check("driver_id를 안 주면 '미배정'으로 남김(임의 배정 금지)", rec["driver_id"] == "미배정")
    check("status는 배송중으로 초기화됨", rec["status"] == "배송중")
    check("dispatch_id가 발급됨", bool(rec["dispatch_id"]))

    r2 = db.dispatch(saved, printed["driver_summary"], printed["delivery_memo"], driver_id="기사001")
    check("driver_id를 명시하면 그 값 사용", r2["dispatch_record"]["driver_id"] == "기사001")

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
