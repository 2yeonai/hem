"""
test_order_classification_bot.py - order_classification_bot.py를 golden_set으로 검증

golden_set.yaml에서 실제로 서로 다른 원문(raw text)인 것만 뽑아 테스트한다:
  001 (SMS 주문), 002/003/004 (비주문 통화 발췌), call_007 (005/006이 같은 원문에서
  나온 것이므로 원문 기준으로는 1건 — 분리 전 전체 통화를 판정하는 게 이 봇의 역할이라
  005/006을 따로 두 번 테스트하지 않는다).

golden_set 003번("꽃 심으로 가야 되는데...")은 규칙기반 버전으로는 못 거를 것으로
"미리 알고" 테스트한다 — 실패해도 놀랄 일이 아니라 설계상 예견된 한계다(주석 참고).
이 케이스만 "알려진 한계"로 별도 표시하고, 나머지가 전부 맞아야 통과로 본다.

실행: python3 test_order_classification_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import order_classification_bot as ocb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"

KNOWN_LIMITATIONS = {"003"}  # 규칙기반이라 못 거를 걸로 미리 알고 있는 케이스 id


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    # (id, 표시용 라벨, 판정에 넣을 원문, golden_set에 기록된 기대값)
    cases = [
        ("001", "SMS 주문(백승흔/박혜미 난 10만원)", entries["001"]["raw_variants"][0]["text"], entries["001"]["order_classification"]),
        ("002", "안부 전화", entries["002"]["raw_text_excerpt"], entries["002"]["order_classification"]),
        ("003", "꽃 심으러 감(키워드 함정)", entries["003"]["raw_text_excerpt"], entries["003"]["order_classification"]),
        ("004", "행사 일정 문의", entries["004"]["raw_text_excerpt"], entries["004"]["order_classification"]),
        ("call_007", "부곡면장/북면장 승진축하 통화(분리 전 전체)", entries["005"]["raw_text_full_call"], entries["005"]["order_classification"]),
    ]

    rows = []
    unexpected_failures = []

    for case_id, label, text, expected in cases:
        result = ocb.classify_order(text)
        actual = result["order_classification"]
        match = (actual == expected)

        if match:
            verdict = "일치"
        elif case_id in KNOWN_LIMITATIONS:
            verdict = "불일치 (알려진 한계 — 규칙기반은 문맥 못 읽음, LLM 붙이기 전까지 예상된 실패)"
        else:
            verdict = "불일치 (예상 못한 실패 — 확인 필요)"
            unexpected_failures.append(case_id)

        rows.append({
            "id": case_id, "label": label, "expected": expected, "actual": actual,
            "confidence": result["confidence"], "reason": result["reason"], "verdict": verdict,
        })

    # ---- 결과표 출력 ----
    print("id       | 사례                                        | 기대값        | 실제값        | conf | 판정")
    print("-" * 130)
    for r in rows:
        print("%-8s | %-42s | %-12s | %-12s | %.2f | %s" % (
            r["id"], r["label"], r["expected"], r["actual"], r["confidence"], r["verdict"]
        ))
    print("")
    for r in rows:
        print("[" + r["id"] + "] reason: " + r["reason"])

    print("")
    ok_count = sum(1 for r in rows if r["verdict"] == "일치")
    known_limitation_count = sum(1 for r in rows if "알려진 한계" in r["verdict"])
    print(str(ok_count) + "/" + str(len(rows)) + " 일치, " + str(known_limitation_count) + "개는 알려진 한계로 실패, " + str(len(unexpected_failures)) + "개는 예상 못한 실패")

    if unexpected_failures:
        print("예상 못한 실패 id: " + str(unexpected_failures))

    # 알려진 한계(003)를 뺀 나머지가 전부 맞아야 이 테스트는 "통과"로 본다
    return len(unexpected_failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
