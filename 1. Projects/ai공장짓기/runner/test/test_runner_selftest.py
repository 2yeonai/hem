#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_runner_selftest.py — 범용 러너 자체 테스트 (데모 공장 사용)

검증 항목 (설계노트 1-4·1-5의 요구를 하나씩 대응):
  T1  정상 완주: local/model(mock provider)/human(자동승인) 전 kind 통과
  T2  공통규칙① 재실행게이트: 같은 입력 2회차는 전체 스킵
  T3  공통규칙② 반려루프: 반려(형식)→s3_draft 재작업→재승인 (draft v2 확인)
  T4  공통규칙② 반려루프 소진: max_loops=2 초과시 ESCALATED + 후속 stage 미실행
  T5  경계검증: 선언한 io.writes를 안 쓰면 명확한 에러로 정지(자동수정 없음)
  T6  N회 재시도: 1회 실패 후 재시도로 성공, 로그에 FAIL+OK 둘 다 기록
  T7  정적검증: fable 티어 배정 → FAIL / 순환 의존성 → FAIL / resident → FAIL

실행: python3 test/test_runner_selftest.py   (runner/ 폴더 기준 아무 데서나 가능)
"""
import sys
import copy
import tempfile
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER_DIR = HERE.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = load_module("runner_mod", RUNNER_DIR / "runner.py")
H = load_module("demo_handlers", HERE / "demo_handlers.py")

MANIFEST = R.load_yaml(HERE / "demo_manifest.yaml")

RESULTS = []


def check(name, cond, note=""):
    RESULTS.append((name, bool(cond), note))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {note}")


def new_runner(tmp):
    return R.Runner(copy.deepcopy(MANIFEST), handlers=H,
                    log_dir=Path(tmp) / "logs", state_dir=Path(tmp) / "state")


def main():
    errors, warnings = R.static_validate(MANIFEST)
    check("T0 데모 manifest 정적검증", not errors, f"FAIL {len(errors)} / WARN {len(warnings)}")

    # T1 정상 완주
    with tempfile.TemporaryDirectory() as tmp:
        ctx, entries = new_runner(tmp).run({"text": "안녕"}, "event")
        ok = [e["stage"] for e in entries if e["status"] == "OK"]
        check("T1 정상 완주(전 kind)", ok == ["s1_intake", "s2_summarize", "s3_draft", "s4_review", "s5_archive"], str(ok))
        check("T1b mock provider가 summary 생성", isinstance(ctx.get("summary"), str) and "mock" in ctx["summary"], repr(ctx.get("summary"))[:60])
        check("T1c 로그에 입력해시·소요시간 기록", all(("input_hash" in e and "duration_ms" in e) for e in entries))

    # T2 재실행게이트
    with tempfile.TemporaryDirectory() as tmp:
        r1 = new_runner(tmp)
        r1.run({"text": "같은입력"}, "event")
        r2 = R.Runner(copy.deepcopy(MANIFEST), handlers=H, log_dir=Path(tmp) / "logs", state_dir=Path(tmp) / "state")
        ctx2, entries2 = r2.run({"text": "같은입력"}, "event")
        check("T2 재실행게이트 2회차 전체 스킵", entries2 and entries2[0]["status"] == "SKIP_ALL", entries2[0]["status"] if entries2 else "no log")
        r3 = R.Runner(copy.deepcopy(MANIFEST), handlers=H, log_dir=Path(tmp) / "logs", state_dir=Path(tmp) / "state")
        ctx3, entries3 = r3.run({"text": "다른입력"}, "event")
        check("T2b 입력 바뀌면 다시 실행", any(e["status"] == "OK" for e in entries3))

    # T3 반려루프: 형식 반려 1회 → s3_draft 재작업 → 승인
    with tempfile.TemporaryDirectory() as tmp:
        ctx, entries = new_runner(tmp).run(
            {"text": "반려테스트", "human_decisions": {"s4_review": ["반려:형식", "승인"]}}, "event")
        check("T3 반려→재작업→재승인", ctx.get("draft", {}).get("version") == 2 and ctx.get("archive_note"),
              f"draft v{ctx.get('draft', {}).get('version')}, archive={ctx.get('archive_note')!r}")

    # T4 반려루프 소진 → ESCALATED, 후속 미실행
    with tempfile.TemporaryDirectory() as tmp:
        ctx, entries = new_runner(tmp).run(
            {"text": "소진테스트", "human_decisions": {"s4_review": ["반려:형식", "반려:형식", "반려:형식", "반려:형식"]}}, "event")
        escalated = any(e["status"] == "ESCALATED" for e in entries)
        archived = ctx.get("archive_note") is not None
        check("T4 루프 소진→ESCALATED+후속 정지", escalated and not archived, f"escalated={escalated}, archive 실행됨={archived}")

    # T5 경계검증 실패 → RunnerError 정지
    with tempfile.TemporaryDirectory() as tmp:
        try:
            new_runner(tmp).run({"forget_write": True}, "event")
            check("T5 경계검증 위반시 정지", False, "에러가 안 남")
        except R.RunnerError as e:
            check("T5 경계검증 위반시 정지", "경계검증 실패" in str(e), str(e)[:80])

    # T6 재시도
    with tempfile.TemporaryDirectory() as tmp:
        ctx, entries = new_runner(tmp).run({"text": "재시도", "fail_once": True}, "event")
        s1 = [e for e in entries if e["stage"] == "s1_intake"]
        check("T6 1회 실패 후 재시도 성공", [e["status"] for e in s1] == ["FAIL", "OK"], str([e["status"] for e in s1]))

    # T7 정적검증 거부 케이스들
    bad = copy.deepcopy(MANIFEST)
    bad["stages"][1]["tier"] = "fable"
    errs, _ = R.static_validate(bad)
    check("T7a fable 티어 배정 금지", any("Fable" in e for e in errs), (errs or ["-"])[0][:80])

    bad = copy.deepcopy(MANIFEST)
    bad["stages"][0]["depends_on"] = ["s5_archive"]   # 순환
    errs, _ = R.static_validate(bad)
    check("T7b 순환 의존성 거부", any("순환" in e for e in errs))

    bad = copy.deepcopy(MANIFEST)
    bad["execution"] = "resident"
    errs, _ = R.static_validate(bad)
    check("T7c resident 골격 거부(MVP 범위 밖)", any("resident" in e for e in errs))

    bad = copy.deepcopy(MANIFEST)
    bad["stages"][2]["io"]["writes"] = ["없는필드"]
    errs, _ = R.static_validate(bad)
    check("T7d shared_context에 없는 필드 거부", any("없는필드" in e for e in errs))

    print()
    failed = [r for r in RESULTS if not r[1]]
    print(f"=== 자체 테스트 결과: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS ===")
    if failed:
        print("실패 항목:", [r[0] for r in failed])
        sys.exit(1)
    print("[전체 결과] PASS")


if __name__ == "__main__":
    main()
