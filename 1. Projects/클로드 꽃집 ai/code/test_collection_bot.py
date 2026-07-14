"""
test_collection_bot.py - collection_bot.py를 golden_set.yaml 채널 기준으로 검증

실행: python3 test_collection_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collection_bot as cb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    extra = "  (" + detail + ")" if detail else ""
    print("[" + status + "] " + label + extra)


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    # ---- case 1: sms 채널(001), raw_text만 있음 ----
    text_001 = entries["001"]["raw_variants"][0]["text"]
    r1 = cb.collect(source_type="sms", raw_text=text_001)
    check("001 sms: raw_text가 원문 그대로 보존됨", r1["raw_text"] == text_001)
    check("001 sms: source_type 그대로 기록", r1["source_type"] == "sms")
    check("001 sms: raw_image/raw_audio는 None(둘 다 없었으니까)", r1["raw_image"] is None and r1["raw_audio"] is None)
    check("001 sms: created_at 자동 채워짐", bool(r1["created_at"]))

    # ---- case 2: call 채널(002), raw_text_excerpt를 raw_text로 ----
    r2 = cb.collect(source_type="call", raw_text=entries["002"]["raw_text_excerpt"])
    check("002 call: raw_text 보존", r2["raw_text"] == entries["002"]["raw_text_excerpt"])

    # ---- case 3: 정의되지 않은 source_type은 거부 ----
    try:
        cb.collect(source_type="fax", raw_text="아무거나")
        bad_source_rejected = False
    except ValueError:
        bad_source_rejected = True
    check("정의되지 않은 source_type(fax)은 ValueError로 거부", bad_source_rejected)

    # ---- case 4: raw_* 전부 없으면 원본 소실 금지 규칙으로 거부 ----
    try:
        cb.collect(source_type="manual")
        empty_rejected = False
    except ValueError:
        empty_rejected = True
    check("raw_text/raw_image/raw_audio 전부 없으면 ValueError로 거부(원본 소실 금지)", empty_rejected)

    # ---- case 5: created_at을 명시적으로 주면 그 값을 그대로 씀 ----
    r5 = cb.collect(source_type="manual", raw_text="수기 입력", created_at="2026-01-01T00:00:00+00:00")
    check("created_at을 명시하면 자동생성 안 하고 그 값 그대로 사용", r5["created_at"] == "2026-01-01T00:00:00+00:00")

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    print("")
    print(str(passed) + "/" + str(total) + " checks passed")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
