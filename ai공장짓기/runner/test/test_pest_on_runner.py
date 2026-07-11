#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pest_on_runner.py — 방역 스킬(18 stage)을 범용 러너 위에서 실행하는 연결 테스트

비교 기준: 기존 방역 전용 실행기(클로드 방역 ai/scripts/run.py)의 검증된 동작.
  P1  event 경로 완주 — 만족도수집봇까지 도달, 문서 승인상태=승인완료
  P2  schedule 경로 — 리마인더봇 날짜계산 → 도래 고객만 묶음 순차 처리
  P3  반려 시나리오 — 표현오류 반려→문서생성봇 재실행(version 2)→재승인
  P4  데이터오류 반려 — 현장완료입력봇 복귀 경유 재작업
  P5  발송 차단 안전장치 — 지속 반려→루프 소진→문자장부봇 미실행(미승인 문서 발송 없음)
  P6  stop_condition — 일반문의는 문의판정봇에서 조기 종료

실행: python3 test/test_pest_on_runner.py
"""
import sys
import copy
import tempfile
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER_DIR = HERE.parent
VAULT_ROOT = RUNNER_DIR.parents[1]
PEST_DIR = VAULT_ROOT / "클로드 방역 ai"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = load_module("runner_mod", RUNNER_DIR / "runner.py")
A = load_module("pest_adapter", RUNNER_DIR / "adapters" / "pest_adapter.py")

MANIFEST = R.load_yaml(PEST_DIR / "manifest.yaml")
EVENT_INPUT = R.load_json(PEST_DIR / "test" / "temp_mock_input_임시.json")
SCHEDULE_INPUT = R.load_json(PEST_DIR / "test" / "temp_schedule_mock_input_임시.json")

RESULTS = []


def check(name, cond, note=""):
    RESULTS.append((name, bool(cond), note))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {note}")


def run(input_data, trigger):
    with tempfile.TemporaryDirectory() as tmp:
        runner = R.Runner(copy.deepcopy(MANIFEST), handlers=A,
                          log_dir=Path(tmp) / "logs", state_dir=Path(tmp) / "state")
        return runner.run(copy.deepcopy(input_data), trigger)


def ok_stages(entries):
    return [e["stage"] for e in entries if e.get("status") == "OK"]


def main():
    errors, warnings = R.static_validate(MANIFEST)
    print(f"[정적검증] FAIL {len(errors)} / WARN {len(warnings)}")
    for e in errors:
        print("  ", e)
    check("P0 방역 manifest 정적검증(러너 기준)", not errors, f"WARN {len(warnings)}건(내용은 로그 참고)")

    # P1 event 완주
    ctx, entries = run(EVENT_INPUT, "event")
    ran = ok_stages(entries)
    dd = ctx.get("document_draft") or {}
    approved = all(((dd.get(k) or {}).get("approval") or {}).get("status") == "승인완료"
                   for k in ("report", "certificate") if dd.get(k))
    check("P1 event 경로 완주(만족도수집봇 도달)", "만족도수집봇" in ran, f"OK stage {len(ran)}개")
    check("P1b 승인필수 문서 전부 승인완료", approved)

    # P2 schedule 경로 — 3명 중 도래/임박 2명만 처리 (기존 실행기와 동일 데이터)
    import os
    os.environ.setdefault("PEST_SKILL_TODAY", "2026-07-07")  # 기존 테스트와 동일 기준일
    ctx, entries = run(SCHEDULE_INPUT, "schedule")
    due = ctx.get("reminder_due_list") or []
    n_notice = sum(1 for e in entries if e["stage"] == "방문알림봇" and e["status"] == "OK")
    check("P2 리마인더 날짜계산 실행", len(due) >= 1, f"due_list={len(due)}건")
    check("P2b 도래 고객 수만큼 묶음 순차 처리", n_notice == len(due), f"방문알림봇 실행 {n_notice}회 = due {len(due)}건")

    # P3 표현오류 반려 → 문서생성봇만 재실행 → 재승인
    inp = copy.deepcopy(EVENT_INPUT)
    inp["문서승인_시뮬레이션"] = ["반려:표현오류", "승인완료"]
    ctx, entries = run(inp, "event")
    n_gen = sum(1 for e in entries if e["stage"] == "문서생성봇" and e["status"] == "OK")
    n_field = sum(1 for e in entries if e["stage"] == "현장완료입력봇" and e["status"] == "OK")
    dd = ctx.get("document_draft") or {}
    ver = ((dd.get("report") or dd.get("certificate") or {}).get("approval") or {}).get("version")
    check("P3 표현오류 반려→문서생성봇 재실행→version 2", n_gen == 2 and ver == 2, f"문서생성봇 {n_gen}회, v{ver}")
    check("P3b 현장완료입력봇은 재실행 안 됨(표현오류)", n_field == 1, f"{n_field}회")

    # P4 데이터오류 반려 → 현장완료입력봇 복귀 경유
    inp = copy.deepcopy(EVENT_INPUT)
    inp["문서승인_시뮬레이션"] = ["반려:데이터오류", "승인완료"]
    ctx, entries = run(inp, "event")
    n_field = sum(1 for e in entries if e["stage"] == "현장완료입력봇" and e["status"] == "OK")
    check("P4 데이터오류 반려→현장완료입력봇 재실행", n_field == 2, f"현장완료입력봇 {n_field}회")

    # P5 지속 반려 → 루프 소진 → 발송(문자장부봇) 미실행 = 미승인 문서 발송 차단
    inp = copy.deepcopy(EVENT_INPUT)
    inp["문서승인_시뮬레이션"] = "반려:표현오류"   # 항상 반려
    ctx, entries = run(inp, "event")
    ran = ok_stages(entries)
    escalated = any(e["status"] == "ESCALATED" for e in entries)
    check("P5 지속 반려→ESCALATED, 문자장부봇(발송) 미실행", escalated and "문자장부봇" not in ran,
          f"escalated={escalated}, 발송={'문자장부봇' in ran}")

    # P6 일반문의 조기 종료
    inp = copy.deepcopy(EVENT_INPUT)
    inp["text"] = "안녕하세요 그냥 인사드려요"
    ctx, entries = run(inp, "event")
    ran = ok_stages(entries)
    check("P6 일반문의 stop_condition 조기 종료", "대표자검수" not in ran and "만족도수집봇" not in ran,
          f"실행됨: {ran}")

    print()
    failed = [r for r in RESULTS if not r[1]]
    print(f"=== 방역×러너 연결 테스트: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS ===")
    if failed:
        print("실패 항목:", [(r[0], r[2]) for r in failed])
        sys.exit(1)
    print("[전체 결과] PASS")


if __name__ == "__main__":
    main()
