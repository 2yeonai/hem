#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pest_adapter.py — 방역 스킬을 범용 러너에 연결하는 어댑터

원칙: '클로드 방역 ai' 폴더는 한 글자도 수정하지 않는다.
기존 scripts/run.py의 검증된 mock 함수(STAGE_FUNCS)와 판정 로직을
그대로 import해서 러너의 핸들러 계약으로 노출만 한다.

러너 핸들러 계약 구현:
  STAGE_FUNCS          — 방역 run.py의 것을 그대로 재사용
  evaluate_run_if      — 방역 run.py의 것을 그대로 재사용
  pending_rejections   — 방역 run.py의 _pending_rejections 래핑 (문서승인 전용)
  should_stop          — 방역 run.py의 stop_condition 로직과 동일하게 재현
  batch_items          — 리마인더봇 이후 "묶음 순차 처리 정책"(schema v2 §5) 재현
"""
import importlib.util
from pathlib import Path

# 방역 run.py 위치 — 볼트 루트 기준 상대 경로 (러너: ai공장짓기/runner/adapters/)
VAULT_ROOT = Path(__file__).resolve().parents[3]
PEST_RUN_PY = VAULT_ROOT / "클로드 방역 ai" / "scripts" / "run.py"


def _load_pest_module():
    if not PEST_RUN_PY.is_file():
        raise FileNotFoundError(f"방역 run.py를 찾을 수 없음: {PEST_RUN_PY}")
    spec = importlib.util.spec_from_file_location("pest_run_module", str(PEST_RUN_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PEST = _load_pest_module()

# 1) stage 함수·run_if 판정 — 방역 것 그대로
STAGE_FUNCS = dict(_PEST.STAGE_FUNCS)
evaluate_run_if = _PEST.evaluate_run_if


# [발견사항 2026-07-12 / failure_log err-2026-07-12-01] 방역 manifest는
# visit_notice를 type: object로 선언했는데, 기존 mock(run_방문알림봇)은 문자열을
# 씀 — 기존 방역 전용 실행기는 경계검증이 없어 그동안 안 잡혔고, 범용 러너의
# 경계검증이 처음 잡아냄. 방역 폴더는 수정하지 않는다는 원칙에 따라(자동수정
# 금지), 어댑터에서 manifest 계약(object)대로 감싸서 반환. 근본 수정(방역
# run.py 또는 manifest 중 한쪽 통일)은 방역 폴더 다음 작업 때 할 것.
def _run_방문알림봇_계약보정(ctx, stage):
    detail = _PEST.STAGE_FUNCS["방문알림봇"](ctx, stage)
    if isinstance(ctx.get("visit_notice"), str):
        cr = ctx.get("customer_record") or {}
        ctx["visit_notice"] = {
            "message": ctx["visit_notice"],
            "customer_name": cr.get("customer_name"),
            "visit_date": cr.get("visit_requested_date"),
        }
    return detail + " (어댑터: manifest 계약대로 object 변환)"


STAGE_FUNCS["방문알림봇"] = _run_방문알림봇_계약보정


# 2) 반려 감지 — 문서승인 stage에서만 의미 있음
def pending_rejections(ctx, stage_id):
    if stage_id != "문서승인":
        return {}
    return _PEST._pending_rejections(ctx)


# 3) stop_condition — 방역 run.py의 _run_one_stage 안 로직과 동일
def should_stop(ctx, stage):
    if stage.get("stop_condition") and ctx.get("inquiry_classification") in ("일반문의", "스팸무관", "확인필요"):
        return True, (f"stop_condition: inquiry_classification={ctx.get('inquiry_classification')} — 조기 종료"
                      f" (방역 run.py와 동일 판정)")
    return False, ""


# 4) 묶음 순차 처리 — schedule 트리거에서 리마인더봇이 만든 due_list를 1건씩
def batch_items(ctx, entry_stage):
    if entry_stage != "리마인더봇":
        return None  # event 경로: 묶음 처리 없음
    due_list = ctx.get("reminder_due_list") or []
    return [{"customer_record": dict(due)} for due in due_list]
