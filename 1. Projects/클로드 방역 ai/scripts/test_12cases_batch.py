#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_12cases_batch.py

새 문서("방역&클린 모바일 AI 운영관리 MVP 계획안.md")의 합성 테스트 12건을
run.py의 run_pipeline()을 그대로 불러와(재작성 없이) 실행해보는 배치 테스트.

[2026-07-07 (문서승인워크플로우, Fable 5 결정) 갱신] card-A(승인상태 4종)를
manifest.yaml + run.py에 실제로 반영했으므로, 이 배치 테스트도 예전
approval_action(고객 문의 승인 게이트) 대신 document_draft.report/
certificate.approval.status(문서 자체 승인 게이트)를 검증하도록 갱신.
추가로 반려-재작업 루프(표현오류/데이터오류)와 "승인완료 안 된 문서는
발송 못 함" 안전장치도 별도 시나리오로 검증한다.

실행:
  python3 test_12cases_batch.py
"""
import sys
import json
from pathlib import Path
from datetime import date, timedelta

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
import run as run_mod  # run.py 재사용 - 로직 재작성 안 함

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml 필요: pip install pyyaml --break-system-packages")
    sys.exit(1)

GOLDEN_12 = ROOT_DIR / "test" / "새문서_합성테스트_12건.yaml"
MANIFEST = ROOT_DIR / "manifest.yaml"


def load_cases():
    with open(GOLDEN_12, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["cases"]


def case_to_input(case, 문서승인_시뮬레이션=None):
    """golden set 12건의 한 항목 -> run.py 수집봇이 기대하는 입력 JSON 형태로 변환"""
    doc_types = case["문서요청"]
    text_parts = [f"{case['현장명']}에서 {case['사용약품']} 사용해 방역 작업을 진행함."]
    if "완료보고서" in doc_types:
        text_parts.append("완료보고서 요청.")
    if "소독증명서" in doc_types:
        text_parts.append("소독증명서 요청.")
    inp = {
        "text": " ".join(text_parts),
        "source_type": "manual",
        "created_at": case["방문일"] + "T09:00:00",
        "customer_name": case["고객명"],
        "space_type": case["현장명"],
        "visit_requested_date": case["방문일"],
        "used_chemicals": case["사용약품"],
        "followup_needed": False,
        "visit_cycle": None,
        "last_visit_date": None,
        "_문서요청_원본": doc_types,
        "_승인상태_원본": case["승인상태"],
        "_D_day_원본": case["D_day"],
    }
    if 문서승인_시뮬레이션 is not None:
        inp["문서승인_시뮬레이션"] = 문서승인_시뮬레이션
    return inp


def approval_statuses(doc_draft):
    out = {}
    for k in ("report", "certificate"):
        doc = (doc_draft or {}).get(k)
        if doc:
            out[k] = (doc.get("approval") or {}).get("status")
    return out


def main():
    manifest = run_mod.load_yaml(str(MANIFEST))
    cases = load_cases()

    print(f"=== 새 문서 합성 테스트 {len(cases)}건 배치 실행 (event 트리거, 기본 자동승인) ===\n")

    rows = []
    for case in cases:
        input_data = case_to_input(case)
        ctx, trace = run_mod.run_pipeline(manifest, input_data, trigger_type="event")
        ran_stages = [t["stage"] for t in trace if t.get("ran")]
        reached_end = "만족도수집봇" in ran_stages
        doc_draft = ctx.get("document_draft") or {}
        statuses = approval_statuses(doc_draft)
        rows.append({
            "번호": case["번호"],
            "고객명": case["고객명"],
            "요청문서_원본": case["문서요청"],
            "document_draft_report_있음": doc_draft.get("report") is not None,
            "document_draft_certificate_있음": doc_draft.get("certificate") is not None,
            "승인상태_원본": case["승인상태"],
            "approval_statuses_결과": statuses,
            "D_day_원본": case["D_day"],
            "끝까지_도달": reached_end,
        })
        print(f"--- case {case['번호']} ({case['고객명']}) 요약 ---")
        print(f"  요청문서 원본={case['문서요청']} -> report={doc_draft.get('report') is not None}, "
              f"certificate={doc_draft.get('certificate') is not None}")
        print(f"  문서 승인상태(신규) = {statuses}")
        print(f"  끝까지 도달(만족도수집봇, 발송 성공 포함)={reached_end}")
        print()

    # ---- schedule 트리거 경로 시도 (리마인더봇, entry_points 실제 연결 검증) ----
    print("=== schedule 트리거(리마인더봇 entry_stage) 시도 ===")
    CYCLE_DAYS_FOR_TEST = 90  # "분기"
    customers = []
    for c in cases:
        visit_dt = date.fromisoformat(c["방문일"])
        last_visit_dt = visit_dt - timedelta(days=CYCLE_DAYS_FOR_TEST)
        customers.append({
            "customer_name": c["고객명"],
            "space_type": c["현장명"],
            "visit_cycle": "분기",
            "last_visit_date": last_visit_dt.isoformat(),
            "report_requested": "완료보고서" in c["문서요청"],
            "certificate_requested": "소독증명서" in c["문서요청"],
        })
    dummy_input = {"customers": customers}
    ctx2, trace2 = run_mod.run_pipeline(manifest, dummy_input, trigger_type="schedule")
    ran2 = [t["stage"] for t in trace2 if t.get("ran")]
    unique_ran2 = sorted(set(ran2))
    due_n = len(ctx2.get("reminder_due_list") or [])
    print(f"schedule 트리거로 실행된 stage(중복 포함, 고객 수만큼 반복): {len(ran2)}회")
    print(f"schedule 트리거로 실행된 고유 stage 종류: {unique_ran2}")
    print(f"방문주기 도래/임박으로 판정된 고객 수: {due_n}\n")

    # ---- 추가 시나리오: 반려-재작업 루프 (표현오류/데이터오류) ----
    print("=== 추가 시나리오 A: 표현오류 반려 1회 -> 문서생성봇 재실행 -> 재승인 ===")
    case1 = cases[2]  # 소독증명서만 요청하는 케이스
    input_a = case_to_input(case1, 문서승인_시뮬레이션=["반려:표현오류", "승인완료"])
    ctx_a, trace_a = run_mod.run_pipeline(manifest, input_a, trigger_type="event")
    ran_a = [t["stage"] for t in trace_a if t.get("ran")]
    doc_gen_count_a = ran_a.count("문서생성봇")
    cert_version_a = ((ctx_a.get("document_draft") or {}).get("certificate") or {}).get("approval", {}).get("version")
    cert_status_a = ((ctx_a.get("document_draft") or {}).get("certificate") or {}).get("approval", {}).get("status")
    print(f"  문서생성봇 실행 횟수={doc_gen_count_a}(반려 1회면 2여야 함), "
          f"최종 version={cert_version_a}(2여야 함), 최종 status={cert_status_a}(승인완료여야 함)")
    scenario_a_ok = (doc_gen_count_a == 2 and cert_version_a == 2 and cert_status_a == "승인완료"
                      and "만족도수집봇" in ran_a)
    print(f"  -> {'PASS' if scenario_a_ok else 'FAIL'}")

    print()
    print("=== 추가 시나리오 B: 데이터오류 반려 1회 -> 현장완료입력봇 복귀 -> 문서생성봇 재실행 -> 재승인 ===")
    input_b = case_to_input(case1, 문서승인_시뮬레이션=["반려:데이터오류", "승인완료"])
    ctx_b, trace_b = run_mod.run_pipeline(manifest, input_b, trigger_type="event")
    ran_b = [t["stage"] for t in trace_b if t.get("ran")]
    site_completion_count_b = ran_b.count("현장완료입력봇")
    cert_version_b = ((ctx_b.get("document_draft") or {}).get("certificate") or {}).get("approval", {}).get("version")
    scenario_b_ok = (site_completion_count_b == 2 and cert_version_b == 2 and "만족도수집봇" in ran_b)
    print(f"  현장완료입력봇 실행 횟수={site_completion_count_b}(데이터오류 반려로 되돌아가면 2여야 함), "
          f"최종 version={cert_version_b}(2여야 함)")
    print(f"  -> {'PASS' if scenario_b_ok else 'FAIL'}")

    print()
    print("=== 추가 시나리오 C(가장 중요): 계속 반려 -> 재시도 소진 -> 발송 시도 시 안전장치 발동 확인 ===")
    input_c = case_to_input(case1, 문서승인_시뮬레이션="반려:데이터오류")
    guard_fired = False
    try:
        run_mod.run_pipeline(manifest, input_c, trigger_type="event")
        print("  -> 예외가 발생하지 않음(안전장치 미작동 - 문제!)")
    except RuntimeError as e:
        guard_fired = "안전장치 발동" in str(e)
        print(f"  -> RuntimeError 발생(의도된 동작): {e}")
    print(f"  -> {'PASS(안전장치 정상 작동)' if guard_fired else 'FAIL(안전장치 작동 안 함)'}")

    # ---- 결과 요약 / 갭 판정 ----
    print()
    print("=" * 70)
    print("[검증 1] 문서요청 종류(완료보고서/소독증명서/둘다) 분기가 구분되는가?")
    combo_results = set()
    for r in rows:
        combo_results.add((r["document_draft_report_있음"], r["document_draft_certificate_있음"]))
    all_correct = all(
        (r["document_draft_report_있음"] == ("완료보고서" in r["요청문서_원본"])) and
        (r["document_draft_certificate_있음"] == ("소독증명서" in r["요청문서_원본"]))
        for r in rows
    )
    print(f"  -> document_draft의 report/certificate 유무 조합 종류 수: {len(combo_results)} {sorted(combo_results)}")
    print("  -> 결과:", "[해결됨] card-06 해결 확인" if (all_correct and len(combo_results) > 1) else "[갭 남음]")

    print()
    print("[검증 2] 승인상태 4종(승인완료/반려/승인대기/초안)이 반영되는가? — card-A(Fable 5 결정) 반영 확인")
    all_approved_default = all(
        all(v == "승인완료" for v in r["approval_statuses_결과"].values())
        for r in rows
    )
    print(f"  -> 기본(자동승인) 12건 전부 문서 승인상태=승인완료로 도달: {all_approved_default}")
    print(f"  -> 추가 시나리오 A(표현오류 반려->재승인): {'PASS' if scenario_a_ok else 'FAIL'}")
    print(f"  -> 추가 시나리오 B(데이터오류 반려->재승인): {'PASS' if scenario_b_ok else 'FAIL'}")
    print(f"  -> 추가 시나리오 C(미승인 발송 차단 안전장치): {'PASS' if guard_fired else 'FAIL'}")
    card_a_resolved = all_approved_default and scenario_a_ok and scenario_b_ok and guard_fired
    print(f"  -> 결과: {'[해결됨] card-A 해결 확인 — 초안/승인대기/승인완료/반려 상태가 문서별로 표현되고, 반려 2갈래 복귀와 발송 차단 안전장치가 모두 실제로 동작함' if card_a_resolved else '[갭 남음 — 재확인 필요]'}")

    print()
    print("[검증 3] D-day/지연 상태가 리마인더봇에서 표시되고, 후속 stage로 이어지는가?")
    print(f"  -> schedule 트리거 실행된 고유 stage: {unique_ran2}")
    print(f"  -> 방문주기 도래/임박 고객 수: {due_n}, 총 실행 횟수: {len(ran2)}회")
    gap3_ok = len(unique_ran2) > 1 and due_n > 0
    print("  -> 결과:", "[해결됨] card-08/card-09 해결 확인" if gap3_ok else "[갭 남음]")

    print()
    print("[요약] 실행된 케이스 수:", len(rows), "/ 끝까지 도달(만족도수집봇):",
          sum(1 for r in rows if r["끝까지_도달"]))
    print("[전체 결과]", "PASS - 모든 갭 해결 확인" if (all_correct and card_a_resolved and gap3_ok) else "일부 FAIL - 재확인 필요")


if __name__ == "__main__":
    main()
