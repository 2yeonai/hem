"""
test_delivery_photo_bot.py - delivery_photo_bot.py 검증

golden_set에는 실제 사진 데이터가 없으므로(알려진 한계), dispatch_record 형태만
최소한으로 만들어 사용한다 — 이 봇의 입력 계약(dispatch_record)만 확인하면 되고,
사진 촬영 자체는 이 코드 환경에서 재현할 수 없다.

실행: python3 test_delivery_photo_bot.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import delivery_photo_bot as dpb

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    extra = "  (" + detail + ")" if detail else ""
    print("[" + status + "] " + label + extra)


def main():
    dummy_dispatch_record = {"dispatch_id": "dispatch_test01", "order_id": "order_test01"}

    r1 = dpb.capture_delivery_photo(dummy_dispatch_record, photo_uri=None)
    check("photo_uri가 없으면 photo_status는 '대기'(임의로 완료 처리 안 함)", r1["photo_status"] == "대기")
    check("photo_uri가 없으면 delivery_photo도 None", r1["delivery_photo"] is None)

    r2 = dpb.capture_delivery_photo(dummy_dispatch_record, photo_uri="mock://photo/order_test01.jpg")
    check("photo_uri가 있으면 photo_status는 '완료'", r2["photo_status"] == "완료")
    check("photo_uri가 있으면 delivery_photo에 그대로 저장", r2["delivery_photo"] == "mock://photo/order_test01.jpg")

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    print("")
    print(str(passed) + "/" + str(total) + " checks passed")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
