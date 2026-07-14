#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_content_on_runner.py — 콘텐츠 공장을 범용 러너 위에서 실행하는 테스트

  C1  정적검증 PASS (공통규칙 3가지 포함 manifest)
  C2  완주: 주제→…→게시(mock)→기록, 두 채널 모두 승인완료 후 게시
  C3  채널 선택: threads만 선택하면 블로그작성봇 SKIP + 게시도 threads만
  C4  반려(내용)→분석카드봇부터 재파생(카드 v2, 초안 v2)→재승인→게시
  C5  지속 반려→루프 소진→ESCALATED, 게시봇 미실행(미승인 게시 차단)
  C6  rerun_gate: 같은 주제 2회차는 전체 스킵

실행: python3 test/test_content_on_runner.py
"""
import sys
import copy
import tempfile
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTORY_DIR = HERE.parent
VAULT_ROOT = FACTORY_DIR.parent
RUNNER_DIR = VAULT_ROOT / "ai공장짓기" / "runner"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = load_module("runner_mod", RUNNER_DIR / "runner.py")
H = load_module("content_handlers", FACTORY_DIR / "scripts" / "handlers.py")

MANIFEST = R.load_yaml(FACTORY_DIR / "manifest.yaml")
BASE_INPUT = R.load_json(HERE / "sample_input.json")

RESULTS = []


def check(name, cond, note=""):
    RESULTS.append((name, bool(cond), note))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {note}")


def run(input_data, state_dir=None):
    tmp_ctx = tempfile.TemporaryDirectory()
    sd = state_dir or (Path(tmp_ctx.name) / "state")
    runner = R.Runner(copy.deepcopy(MANIFEST), handlers=H,
                      log_dir=Path(tmp_ctx.name) / "logs", state_dir=sd)
    ctx, entries = runner.run(copy.deepcopy(input_data), "event")
    return ctx, entries


def ok_stages(entries):
    return [e["stage"] for e in entries if e.get("status") == "OK"]


def main():
    errors, warnings = R.static_validate(MANIFEST)
    for e in errors:
        print("  [FAIL]", e)
    check("C1 콘텐츠 manifest 정적검증", not errors, f"FAIL {len(errors)} / WARN {len(warnings)}")

    # C2 완주
    ctx, entries = run(BASE_INPUT)
    ran = ok_stages(entries)
    pub = (ctx.get("publish_result") or {}).get("published") or {}
    check("C2 완주(주제→게시→기록)", "기록봇" in ran, f"OK {len(ran)}개: {ran}")
    check("C2b 두 채널 모두 게시(mock)", set(pub) == {"blog", "threads"}, str(list(pub)))
    check("C2c 발행 장부 기록", len((ctx.get("publish_log") or {}).get("entries", [])) == 2)

    # C3 채널 선택 (threads만)
    inp = dict(BASE_INPUT, channels=["threads"], topic="채널선택 테스트")
    ctx, entries = run(inp)
    ran = ok_stages(entries)
    skipped = [e["stage"] for e in entries if e["status"] == "SKIP"]
    pub = (ctx.get("publish_result") or {}).get("published") or {}
    check("C3 blog 미선택시 블로그작성봇 SKIP", "블로그작성봇" in skipped and "블로그작성봇" not in ran, f"skip={skipped}")
    check("C3b threads만 게시", set(pub) == {"threads"}, str(list(pub)))

    # C4 반려(내용) → 분석카드봇부터 재파생
    inp = dict(BASE_INPUT, topic="반려 테스트")
    inp["승인_시뮬레이션"] = ["반려:내용", "승인"]
    ctx, entries = run(inp)
    card_rev = (ctx.get("content_card") or {}).get("revision")
    blog_v = ((ctx.get("blog_draft") or {}).get("approval") or {}).get("version")
    pub = (ctx.get("publish_result") or {}).get("published") or {}
    check("C4 내용반려→카드 v2→초안 v2→재승인→게시", card_rev == 2 and blog_v == 2 and pub,
          f"card v{card_rev}, blog v{blog_v}, 게시={list(pub)}")

    # C5 지속 반려 → ESCALATED, 게시 차단
    inp = dict(BASE_INPUT, topic="소진 테스트")
    inp["승인_시뮬레이션"] = "반려:내용"
    ctx, entries = run(inp)
    ran = ok_stages(entries)
    escalated = any(e["status"] == "ESCALATED" for e in entries)
    check("C5 루프 소진→ESCALATED, 게시봇 미실행", escalated and "게시봇" not in ran,
          f"escalated={escalated}")

    # C6 rerun_gate
    with tempfile.TemporaryDirectory() as tmp:
        sd = Path(tmp) / "state"
        run(dict(BASE_INPUT, topic="게이트 테스트"), state_dir=sd)
        ctx, entries = run(dict(BASE_INPUT, topic="게이트 테스트"), state_dir=sd)
        check("C6 같은 주제 2회차 전체 스킵(rerun_gate)", entries and entries[0]["status"] == "SKIP_ALL",
              entries[0]["status"] if entries else "no log")

    print()
    failed = [r for r in RESULTS if not r[1]]
    print(f"=== 콘텐츠 공장×러너 테스트: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS ===")
    if failed:
        print("실패 항목:", [(r[0], r[2]) for r in failed])
        sys.exit(1)
    print("[전체 결과] PASS")


if __name__ == "__main__":
    main()
