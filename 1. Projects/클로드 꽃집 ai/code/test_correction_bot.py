"""
test_correction_bot.py - correction_bot.py를 golden_set으로 검증

correction_bot은 order_split_bot이 만든 세그먼트 1건(segment_text)을 입력으로
받는다는 전제로 설계됐다(io_note 참고). golden_set 005/006은 같은 통화
(call_007)의 두 세그먼트('/' 기준으로 사람이 표시한 경계)이므로, 이 테스트는
'/'로 수동 분리한 두 세그먼트를 각각 넣어 "입력이 이미 분리돼 있을 때" 이 봇이
의도대로 동작하는지 확인한다(실제 order_split_bot은 아직 이 분리를 자동으로
못 한다는 것 자체가 그 봇의 알려진 한계 — test_order_split_bot.py 참고).

001은 SMS 원문(타이핑 버전, "10마넌" 표기 포함)으로 단위 오인식 정규화를 검증한다.

알려진 한계 케이스: golden_set 005의 "보호구 매장"은 사전에 없는 낯선 오인식이라
이 규칙기반 버전이 전혀 잡지 못한다 — 실패가 아니라 예견된 한계로 표시한다
(correction_bot.py 모듈 docstring 참고).

실행: python3 test_correction_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import correction_bot as cb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    text_001 = entries["001"]["raw_variants"][1]["text"]  # 타이핑 버전 - "10마넌" 포함
    full_call = entries["005"]["raw_text_full_call"]
    seg_005, seg_006 = full_call.split("/")

    rows = []
    unexpected_failures = []

    # ---- case 1: 001 - "10마넌" -> "10만원" 단위 정규화 ----
    r1 = cb.correct_text(text_001)
    ok1 = ("10마넌" not in r1["normalized_text"]) and ("10만원" in r1["normalized_text"]) and len(r1["correction_log"]) >= 1
    rows.append({
        "id": "001", "label": "SMS 타이핑본(10마넌 단위 오인식)",
        "expected": "normalized_text에 '10만원' 포함, correction_log 1건 이상",
        "actual": "normalized_text=" + r1["normalized_text"][:40] + "... / log 건수=" + str(len(r1["correction_log"])),
        "verdict": "일치" if ok1 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok1:
        unexpected_failures.append("001")

    # ---- case 2: 005 세그먼트(수동 분리) - "승진"/"면접" 이벤트 충돌 감지 ----
    r2 = cb.correct_text(seg_005)
    event_conflict_found = any("이벤트류 키워드" in c["note"] for c in r2["candidates"])
    rows.append({
        "id": "005", "label": "부곡면장 건 세그먼트(수동 분리) - 이벤트 키워드 충돌",
        "expected": "candidates에 '승진/면접 동시 등장' 후보 포함",
        "actual": "candidates 건수=" + str(len(r2["candidates"])) + (" (이벤트 충돌 감지됨)" if event_conflict_found else " (이벤트 충돌 미감지)"),
        "verdict": "일치" if event_conflict_found else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not event_conflict_found:
        unexpected_failures.append("005")

    # ---- case 3: 006 세그먼트(수동 분리) - "부공면" 오타 후보 + "몰라" 자기불확실 감지 ----
    r3 = cb.correct_text(seg_006)
    typo_found = any(c["phrase"] == "부공면" for c in r3["candidates"])
    uncertain_found = any("몰라" in c["phrase"] for c in r3["candidates"])
    ok3 = typo_found and uncertain_found
    rows.append({
        "id": "006", "label": "북면장 건 세그먼트(수동 분리) - 오타 후보 + 자기불확실 표현",
        "expected": "candidates에 '부공면' 오타 후보 + '몰라' 자기불확실 표현 둘 다 포함",
        "actual": "오타 후보=" + str(typo_found) + ", 자기불확실=" + str(uncertain_found),
        "verdict": "일치" if ok3 else "불일치 (예상 못한 실패 - 확인 필요)",
    })
    if not ok3:
        unexpected_failures.append("006")

    # ---- case 4: 알려진 한계 - "보호구 매장"은 이 규칙기반 버전이 못 잡는다 ----
    unclear_phrase_caught = any("보호구" in str(c.get("phrase", "")) for c in r2["candidates"])
    rows.append({
        "id": "005-한계", "label": "'보호구 매장' 낯선 오인식 - 사전에 없어 못 잡음",
        "expected": "이 규칙기반 버전은 못 잡는 것이 예견된 한계(candidates에 없어야 '정상')",
        "actual": "감지됨(뜻밖)" if unclear_phrase_caught else "감지 안 됨(예견된 한계 그대로)",
        "verdict": "일치 (알려진 한계 그대로 재현됨)" if not unclear_phrase_caught else "불일치 (예상보다 똑똑하게 감지함 - 재확인 필요)",
    })

    # ---- 결과표 출력 ----
    print("id        | 사례                                          | 기대                                                    | 실제")
    print("-" * 150)
    for r in rows:
        print("%-9s | %-45s | %-55s | %s" % (r["id"], r["label"], r["expected"], r["actual"]))
    print("")
    for r in rows:
        print("[" + r["id"] + "] verdict: " + r["verdict"])

    print("")
    ok_count = sum(1 for r in rows if r["verdict"].startswith("일치"))
    print(str(ok_count) + "/" + str(len(rows)) + " 통과, " + str(len(unexpected_failures)) + "개 예상 못한 실패")

    if unexpected_failures:
        print("예상 못한 실패 id: " + str(unexpected_failures))

    print("")
    print("알려진 한계(숨기지 않고 명시): golden_set 005의 '보호구 매장'처럼 사전에 없는")
    print("낯선 오인식은 이 규칙기반 버전으로는 전혀 못 잡는다 - 문맥을 실제로 이해해야")
    print("가능한 일이라 LLM(sonnet) 붙인 뒤 재검증 필요.")

    return len(unexpected_failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
