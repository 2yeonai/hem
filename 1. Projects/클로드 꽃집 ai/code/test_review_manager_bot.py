"""
test_review_manager_bot.py - review_manager_bot.py를 golden_set으로 검증

review_manager_bot은 파이프라인의 마지막 model 스테이지로, 상류 전부
(correction_bot -> order_draft_bot -> ribbon_price_bot 및 order_split_bot의
split_status)를 종합해 review_checklist/review_priority/editable_fields를
만든다. 이 테스트는 전체 체인을 실제로 이어 붙여 golden_set 001/005/006에
대해 합리적인 우선순위가 나오는지 확인한다.

주의: review_priority 색상 규칙(초록/노랑/빨강/파랑) 자체가 12봇_kind분류표.yaml
open_questions에 "확인 필요"로 명시된 미확정 항목이라, 이 테스트는 review_manager_bot.py
docstring에 적어둔 이 구현의 제안 규칙을 기준으로 검증한다(실측/확정 규칙이
아님 - review_manager_bot.py 상단 docstring 참고).

실행: python3 test_review_manager_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import correction_bot as cb
import order_draft_bot as odb
import ribbon_price_bot as rpb
import review_manager_bot as rmb
import order_split_bot as osb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"


def _pipeline(text):
    split = osb.split_order(text)
    seg = split["order_segments"][0]
    c = cb.correct_text(seg["segment_text"])
    d = odb.build_draft(c["normalized_text"])
    r = rpb.process_ribbon_and_price(d["order_draft"], c["normalized_text"])
    rev = rmb.build_review(
        order_draft=d["order_draft"],
        field_confidence=d["field_confidence"],
        field_sources=d["field_sources"],
        missing_fields=d["missing_fields"],
        candidates=c["candidates"],
        ribbon_message_raw=r["ribbon_message_raw"],
        ribbon_message_final=r["ribbon_message_final"],
        product_name=r["product_name"],
        price=r["price"],
        quantity=r["quantity"],
        correction_log=c["correction_log"],
        split_status=split["split_status"],
    )
    return split, c, d, r, rev


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    text_001 = entries["001"]["raw_variants"][1]["text"]
    full_call = entries["005"]["raw_text_full_call"]

    rows = []
    unexpected_failures = []

    # ---- case 1: 001 - 핵심 필드(product/price)는 있으나 이름류 다수 missing -> 노랑 기대 ----
    split1, c1, d1, r1, rev1 = _pipeline(text_001)
    ok1 = (
        rev1["review_priority"] in ("노랑", "초록")  # 완전히 깨끗하면 초록, 이름 missing이면 노랑 - 둘 다 "너무 급하지 않음" 범주
        and "review_checklist" in rev1 and isinstance(rev1["review_checklist"], list)
        and set(rev1["editable_fields"]) >= {"product_name", "price"}
    )
    rows.append({
        "id": "001", "label": "SMS 단일 주문 - 핵심 필드 확보, 이름류만 미확정",
        "expected": "review_priority in {노랑, 초록} (급한 이슈 없음), editable_fields에 product_name/price 포함",
        "actual": "priority=" + rev1["review_priority"] + ", checklist 건수=" + str(len(rev1["review_checklist"])),
        "verdict": "일치" if ok1 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok1:
        unexpected_failures.append("001")

    # ---- case 2: call_007(005/006 원문 그대로, 실제 order_split_bot 입력) - split_status=확인필요 -> 빨강 기대 ----
    split2, c2, d2, r2, rev2 = _pipeline(full_call)
    ok2 = (rev2["review_priority"] == "빨강" and split2["split_status"] == "확인필요")
    split_checklist_found = any("split_status" in item for item in rev2["review_checklist"])
    rows.append({
        "id": "call_007", "label": "부곡면장/북면장 통화(미분리) - 다중주문 가능성 감지됨",
        "expected": "split_status=확인필요 -> review_priority=빨강, checklist에 split_status 관련 항목 포함",
        "actual": "split_status=" + split2["split_status"] + ", priority=" + rev2["review_priority"]
                  + (", checklist에 포함됨" if split_checklist_found else ", checklist에 없음(뜻밖)"),
        "verdict": "일치" if (ok2 and split_checklist_found) else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not (ok2 and split_checklist_found):
        unexpected_failures.append("call_007")

    # ---- case 3: 이름 필드는 항상 "사람이 채워야 함" 안내 문구가 checklist에 있어야 함(001 기준) ----
    name_notice_found = any("이름을 아예 추출하지 않음" in item for item in rev1["review_checklist"])
    rows.append({
        "id": "구조확인", "label": "이름 미추출 안내 문구가 checklist에 포함되는지",
        "expected": "recipient_name/sender_name 관련 안내 문구 포함",
        "actual": "포함됨" if name_notice_found else "누락됨",
        "verdict": "일치" if name_notice_found else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not name_notice_found:
        unexpected_failures.append("구조확인")

    # ---- 결과표 출력 ----
    print("id         | 사례                                              | 기대")
    print("-" * 140)
    for r in rows:
        print("%-10s | %-50s | %s" % (r["id"], r["label"], r["expected"]))
        print("             실제: " + r["actual"])
        print("             verdict: " + r["verdict"])
    print("")

    ok_count = sum(1 for r in rows if r["verdict"].startswith("일치"))
    print(str(ok_count) + "/" + str(len(rows)) + " 통과, " + str(len(unexpected_failures)) + "개 예상 못한 실패")
    if unexpected_failures:
        print("예상 못한 실패 id: " + str(unexpected_failures))

    print("")
    print("알려진 한계(숨기지 않고 명시): review_priority 색상 규칙(초록/노랑/빨강/파랑) 자체가")
    print("12봇_kind분류표.yaml open_questions에 '확인 필요'로 남겨진 미확정 항목이다 - 이 테스트는")
    print("review_manager_bot.py에 적어둔 이 구현의 제안 규칙 기준으로만 검증한다.")

    return len(unexpected_failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
