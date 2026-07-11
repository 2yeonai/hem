"""
test_order_split_bot.py - order_split_bot.py를 golden_set으로 검증

이 봇은 order_classification_bot이 "주문전화/주문가능성있음"으로 판정한 것만
받는다는 전제라, 그 조건에 해당하는 golden_set 항목만 테스트한다: 001(단일 주문),
call_007(=005/006의 원본, 실제로 2건 섞인 통화).

기대하는 동작이 다르다는 점에 주의:
  - 001: 실제로 단일 주문이니 split_status가 "완료"로 나와야 정상.
  - call_007: 실제로는 2건이지만, 이 규칙기반 버전은 "안전하게 자르지 못하면
    확인필요로 넘긴다"는 원칙으로 설계했기 때문에 "정확히 2개로 분리"는 못 한다.
    대신 "여러 건일 가능성이 있다"를 감지해 split_status="확인필요"로 사람에게
    넘기는 것까지가 이 버전의 목표 — 이게 나오면 "성공"이다(틀린 게 아니라
    설계대로 안전하게 동작한 것). "정확한 2분리"는 실제 LLM을 붙이기 전까지 알려진
    한계로 명시한다.

실행: python3 test_order_split_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import order_split_bot as osb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    rows = []
    unexpected_failures = []

    # ---- case 1: 001, 실제 단일 주문 -> split_status는 완료가 나와야 정상 ----
    text_001 = entries["001"]["raw_variants"][0]["text"]
    r1 = osb.split_order(text_001)
    ok1 = (r1["split_status"] == "완료" and len(r1["order_segments"]) == 1)
    rows.append({
        "id": "001", "label": "단일 주문(SMS)", "expected": "split_status=완료, segment 1개",
        "actual": "split_status=" + r1["split_status"] + ", segment " + str(len(r1["order_segments"])) + "개",
        "verdict": "일치" if ok1 else "불일치 (예상 못한 실패 — 확인 필요)",
        "reason": r1["reason"],
    })
    if not ok1:
        unexpected_failures.append("001")

    # ---- case 2: call_007, 실제로는 2건이지만 규칙기반은 "확인필요"로 감지만 하면 성공 ----
    text_007 = entries["005"]["raw_text_full_call"]
    r2 = osb.split_order(text_007)
    ok2 = (r2["split_status"] == "확인필요")  # "정확히 2분리"가 아니라 "위험 감지"가 성공 기준
    actually_split_into_2 = len(r2["order_segments"]) == 2
    rows.append({
        "id": "call_007", "label": "부곡면장/북면장 통화(실제 2건)",
        "expected": "split_status=확인필요 (안전 감지 성공 기준 — '정확한 2분리'는 별개, 아래 참고)",
        "actual": "split_status=" + r2["split_status"] + ", segment " + str(len(r2["order_segments"])) + "개"
                  + (" [참고: 실제 2개로는 못 나눔 — 알려진 한계, LLM 붙이기 전까지]" if not actually_split_into_2 else ""),
        "verdict": "일치 (안전하게 확인필요로 넘김 — 설계대로)" if ok2 else "불일치 (예상 못한 실패 — 확인 필요)",
        "reason": r2["reason"],
    })
    if not ok2:
        unexpected_failures.append("call_007")

    # ---- case 3: bundle_id/bundle_sequence가 실제로 채워지는지 ----
    seg = r1["order_segments"][0]
    ok3 = ("bundle_id" in seg and seg.get("bundle_sequence") == {"index": 1, "total": 1})
    rows.append({
        "id": "구조확인", "label": "bundle_id/bundle_sequence 부여 여부",
        "expected": "각 segment에 bundle_id + bundle_sequence(index/total) 포함",
        "actual": "포함됨" if ok3 else "누락됨",
        "verdict": "일치" if ok3 else "불일치 (예상 못한 실패 — 확인 필요)",
        "reason": "-",
    })
    if not ok3:
        unexpected_failures.append("구조확인")

    # ---- 결과표 출력 ----
    print("id        | 사례                              | 기대                                                    | 실제")
    print("-" * 140)
    for r in rows:
        print("%-9s | %-33s | %-55s | %s" % (r["id"], r["label"], r["expected"], r["actual"]))
    print("")
    for r in rows:
        print("[" + r["id"] + "] verdict: " + r["verdict"])
        print("        reason: " + r["reason"])

    print("")
    ok_count = sum(1 for r in rows if r["verdict"].startswith("일치"))
    print(str(ok_count) + "/" + str(len(rows)) + " 통과, " + str(len(unexpected_failures)) + "개 예상 못한 실패")
    print("")
    print("알려진 한계(숨기지 않고 명시): call_007을 실제 부곡면장/북면장 2건으로 정확히")
    print("자동 분리하는 것은 이 규칙기반 버전으로는 못 함 — '여러 건일 가능성'만 감지해서")
    print("사람에게 넘기는 것까지가 이 버전의 목표. 실제 자동 분리는 LLM(sonnet) 붙인 뒤 재검증 필요.")

    if unexpected_failures:
        print("예상 못한 실패 id: " + str(unexpected_failures))

    return len(unexpected_failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
