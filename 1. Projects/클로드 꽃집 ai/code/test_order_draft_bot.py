"""
test_order_draft_bot.py - order_draft_bot.py를 golden_set으로 검증

order_draft_bot은 correction_bot이 만든 normalized_text 1건을 받는다는 전제로
설계됐다. 이 테스트는 두 층위로 나눠 검증한다:

  1. "입력이 이미 분리된 주문 1건일 때" - 001(SMS)과 005/006 세그먼트(call_007을
     '/' 기준으로 수동 분리한 것, 실제 order_split_bot이 언젠가 이렇게 분리해줄
     것을 가정한 시뮬레이션)에서 핵심 필드가 golden_set의 structured_extract와
     대체로 일치하는지 확인한다.
  2. "입력이 아직 분리되지 않았을 때"(call_007 원문 그대로) - 서로 다른 두
     주문의 직함/기관명이 recipient/sender 슬롯에 뒤섞일 수 있음을 보여주는
     알려진 한계 케이스(상류 order_split_bot의 한계가 전파된 것, 실패로 세지
     않음).

이름(recipient_name/sender_name)은 이 봇이 의도적으로 절대 채우지 않으므로
"필드가 없다"가 아니라 "항상 missing_fields에 있어야 정상"이 이 테스트의 기대값.

실행: python3 test_order_draft_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import correction_bot as cb
import order_draft_bot as odb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"


def _norm(s):
    return s.replace(" ", "") if isinstance(s, str) else s


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    text_001 = entries["001"]["raw_variants"][1]["text"]
    full_call = entries["005"]["raw_text_full_call"]
    seg_005, seg_006 = full_call.split("/")

    rows = []
    unexpected_failures = []

    # ---- case 1: 001 - 명확한 단일 주문 ----
    c1 = cb.correct_text(text_001)
    d1 = odb.build_draft(c1["normalized_text"])["order_draft"]
    checks_001 = {
        "recipient_org": _norm(d1["recipient_org"]) == _norm("창녕군청 재무과"),
        "sender_title": d1["sender_title"] == "부곡면장",
        "product": d1["product"] == "난",
        "amount_krw": d1["amount_krw"] == 100000,
        "ribbon_phrase_raw": d1["ribbon_phrase_raw"] == "승진축하",
        "recipient_name_is_None": d1["recipient_name"] is None,
        "sender_name_is_None": d1["sender_name"] is None,
    }
    ok1 = all(checks_001.values())
    rows.append({
        "id": "001", "label": "SMS 단일 주문(명확한 필드)",
        "expected": "recipient_org/sender_title/product/amount_krw/ribbon_phrase_raw 전부 golden_set과 일치, 이름은 None",
        "actual": str({k: v for k, v in checks_001.items() if not v}) if not ok1 else "전부 일치",
        "verdict": "일치" if ok1 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok1:
        unexpected_failures.append("001")

    # ---- case 2: 005 세그먼트(수동 분리) ----
    c2 = cb.correct_text(seg_005)
    d2 = odb.build_draft(c2["normalized_text"])["order_draft"]
    checks_005 = {
        "recipient_title": d2["recipient_title"] == "부곡면장",
        "recipient_org": d2["recipient_org"] == "부곡면",
        "sender_org": _norm(d2["sender_org"]) == _norm("대륙건설"),
        "event": d2["event"] == "승진",
        "recipient_name_is_None": d2["recipient_name"] is None,
    }
    ok2 = all(checks_005.values())
    rows.append({
        "id": "005", "label": "부곡면장 건 세그먼트(수동 분리)",
        "expected": "recipient_title=부곡면장, recipient_org=부곡면, sender_org~대륙건설, event=승진",
        "actual": str({k: v for k, v in checks_005.items() if not v}) if not ok2 else "전부 일치",
        "verdict": "일치" if ok2 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok2:
        unexpected_failures.append("005")

    # ---- case 3: 006 세그먼트(수동 분리) ----
    c3 = cb.correct_text(seg_006)
    d3 = odb.build_draft(c3["normalized_text"])["order_draft"]
    checks_006 = {
        "recipient_title": d3["recipient_title"] == "북면장",
        "sender_org": _norm(d3["sender_org"]) == _norm("부공면협의회"),
        "amount_krw": d3["amount_krw"] == 50000,
        "recipient_name_is_None": d3["recipient_name"] is None,
    }
    ok3 = all(checks_006.values())
    rows.append({
        "id": "006", "label": "북면장 건 세그먼트(수동 분리)",
        "expected": "recipient_title=북면장, sender_org~부공면협의회, amount_krw=50000",
        "actual": str({k: v for k, v in checks_006.items() if not v}) if not ok3 else "전부 일치",
        "verdict": "일치" if ok3 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok3:
        unexpected_failures.append("006")

    # ---- case 4: 알려진 한계 - call_007 원문 그대로(미분리) 입력 시 필드 혼선 ----
    c4 = cb.correct_text(full_call)
    d4 = odb.build_draft(c4["normalized_text"])["order_draft"]
    # 미분리 원문에서는 부곡면장(005건 정보)이 recipient로, 북면장 관련 정보(006건 sender_org)가
    # sender로 뒤섞여 나온다 - 이것이 실제 두 개의 독립 주문이라는 사실을 이 봇은 모른다.
    mixed = (d4["recipient_title"] == "부곡면장" and d4["sender_org"] is not None)
    rows.append({
        "id": "call_007-한계", "label": "미분리 원문(call_007 통째로) - 상류 한계 전파",
        "expected": "실제로는 독립된 두 주문이지만, 미분리 입력이라 한 주문인 것처럼 필드가 섞여 나오는 것이 예견된 한계",
        "actual": "recipient_title=" + str(d4["recipient_title"]) + ", sender_org=" + str(d4["sender_org"])
                  + (" (섞임 확인됨 - 예견된 한계 그대로)" if mixed else " (섞이지 않음 - 뜻밖)"),
        "verdict": "일치 (알려진 한계 그대로 재현됨)" if mixed else "불일치 (예상과 다름 - 확인 필요)",
    })

    # ---- 결과표 출력 ----
    print("id             | 사례                                | 기대")
    print("-" * 140)
    for r in rows:
        print("%-14s | %-35s | %s" % (r["id"], r["label"], r["expected"]))
        print("               실제: " + r["actual"])
        print("               verdict: " + r["verdict"])
    print("")

    ok_count = sum(1 for r in rows if r["verdict"].startswith("일치"))
    print(str(ok_count) + "/" + str(len(rows)) + " 통과, " + str(len(unexpected_failures)) + "개 예상 못한 실패")
    if unexpected_failures:
        print("예상 못한 실패 id: " + str(unexpected_failures))

    print("")
    print("알려진 한계(숨기지 않고 명시): 이 봇은 입력이 이미 '주문 1건' 단위로 분리됐다는")
    print("전제로 설계됐다. order_split_bot이 아직 실제 분리를 못 하면(known limitation),")
    print("서로 다른 주문의 필드가 recipient/sender 슬롯에 섞여 나올 수 있다 - 이 봇의")
    print("버그가 아니라 상류 stage의 한계가 전파된 것.")

    return len(unexpected_failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
