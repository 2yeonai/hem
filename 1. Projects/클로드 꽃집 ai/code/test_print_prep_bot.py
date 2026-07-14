"""
test_print_prep_bot.py - print_prep_bot.py를 golden_set(001/006) 기반 저장 레코드로 검증

storage_bot.save_order()로 실제 저장 레코드를 만든 뒤, 그 레코드를 print_prep_bot에
넣어 인쇄용 산출물 4종이 값 손실 없이(None은 "확인 필요"로 표시) 만들어지는지 검증한다.

실행: python3 test_print_prep_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import storage_bot
import print_prep_bot as ppb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"
TEST_DB_PATH = Path(__file__).parent / "test_print_prep.json"

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
        confirmed_fields=e001["structured_extract"], manual_edits={}, approval_action="주문확정",
        bundle_id="single_001", bundle_sequence={"index": 1, "total": 1}, db_path=TEST_DB_PATH,
    )
    printed_001 = ppb.prepare_print(saved_001)

    check("001: order_print에 order_id 포함", printed_001["order_print"]["order_id"] == saved_001["order_id"])
    check("001: recipient는 recipient_org(창녕군청 재무과)로 채워짐", printed_001["order_print"]["recipient"] == "창녕군청 재무과")
    check("001: recipient_name은 None이라 '확인 필요'로 표시(임의로 안 채움)", printed_001["order_print"]["recipient_name"] == "확인 필요")
    check("001: ribbon_print에 ribbon_message_final 포함", printed_001["ribbon_print"]["ribbon_message_final"] == "승진을 축하드립니다.")
    check("001: delivery_memo가 문자열로 생성됨", isinstance(printed_001["delivery_memo"], str) and len(printed_001["delivery_memo"]) > 0)
    check("001: driver_summary가 문자열로 생성됨", isinstance(printed_001["driver_summary"], str) and len(printed_001["driver_summary"]) > 0)

    e006 = entries["006"]
    saved_006 = storage_bot.save_order(
        confirmed_fields=e006["structured_extract"], manual_edits={}, approval_action="주문확정",
        bundle_id="call_007_2026-07-07", bundle_sequence={"index": 2, "total": 2}, db_path=TEST_DB_PATH,
    )
    printed_006 = ppb.prepare_print(saved_006)
    check("006: recipient_title(북면장)로 recipient가 채워짐(recipient_org 없어도 fallback)", printed_006["order_print"]["recipient"] == "북면장")
    check("006: product가 None이라 '확인 필요'로 표시", printed_006["order_print"]["product"] == "확인 필요")
    check("006: amount_krw=50000은 실제 값 그대로 표시(확인 필요 아님)", printed_006["order_print"]["amount_krw"] == 50000)

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
