#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_handlers.py — 데모 공장 핸들러 (러너 자체 테스트용 mock)"""


def run_s1_intake(ctx, stage):
    inp = ctx["_input"]
    # 재시도 검증: fail_once=true면 1회차에 일부러 실패
    n = ctx.get("_s1_calls", 0)
    ctx["_s1_calls"] = n + 1
    if inp.get("fail_once") and n == 0:
        raise ValueError("[의도된 실패] 재시도 검증용 1회차 오류")
    # 경계검증 검증: forget_write=true면 선언한 io.writes를 일부러 안 씀
    if not inp.get("forget_write"):
        ctx["raw_input"] = inp.get("text", "데모 입력")
    return f"raw_input 수집 (호출 {n + 1}회차)"


def run_s3_draft(ctx, stage):
    n = ctx.get("_s3_calls", 0)
    ctx["_s3_calls"] = n + 1
    ctx["draft"] = {"version": n + 1, "base": ctx.get("summary")}
    return f"draft v{n + 1} 생성"


def run_s5_archive(ctx, stage):
    ctx["archive_note"] = f"보관됨: draft v{(ctx.get('draft') or {}).get('version')}"
    return ctx["archive_note"]


STAGE_FUNCS = {
    "s1_intake": run_s1_intake,
    "s3_draft": run_s3_draft,
    "s5_archive": run_s5_archive,
    # s2_summarize: 핸들러 없음 → MockModelProvider 경로 검증
    # s4_review: 핸들러 없음 → default_human_stub 경로 검증
}
