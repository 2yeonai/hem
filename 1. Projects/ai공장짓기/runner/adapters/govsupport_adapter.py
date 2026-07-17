#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
govsupport_adapter.py — 정부지원사업 스킬(매칭~심사 + 발표뒷단)을 범용 러너에 연결하는 어댑터

원칙: '클로드 정부지원사업 ai' 폴더는 한 글자도 수정하지 않는다(방역 어댑터와 동일 원칙).
scripts/run.py의 검증된 함수들을 그대로 import해서 러너의 핸들러 계약(STAGE_FUNCS 등)으로
노출만 한다.

러너 핸들러 계약 구현:
  STAGE_FUNCS          — 정부지원 run.py의 함수들을 stage id -> fn(ctx, stage) 형태로 감싸서 매핑
  evaluate_run_if      — 발표뒷단의 run_if 조건 하나("발표평가_또는_발표자료가_요구됨")를
                          run.py의 evaluate_presentation_run_if()로 그대로 위임
  pending_rejections   — run.py의 _pending_presentation_rejections() 래핑 (PPT승인/발표패키지승인 전용)
  should_stop          — 정부지원 manifest에는 stop_condition이 없음 -> 항상 (False, "")
  batch_items          — 정부지원 manifest에는 schedule 트리거/묶음 처리 정책이 없음 -> 항상 None

────────────────────────────────────────────────────────────────────────────
[발견사항 2026-07-17 ①] manifest.yaml이 두 개 공존한다.
  이 폴더 루트의 manifest.yaml(v0.5.4)은 io_contract/model_routing/quality_gate 방식의
  구식(v1 이전) 스키마다 — stages/shared_context/triggers 키가 아예 없다. 러너
  (runner.py)의 static_validate()는 manifest.get("stages")가 비어 있으면 "stages가
  비어 있음"으로 즉시 FAIL하므로, 이 manifest.yaml은 애초에 러너로 실행이 불가능하다.
  실제로 stages/shared_context/triggers를 갖춘 것은 같은 폴더의
  정부지원_manifest_v2.yaml(schema_version: v2) 하나뿐이다 — 이 어댑터는 그 파일을
  전제로 만들어졌다. runner.py 호출 시 반드시 정부지원_manifest_v2.yaml을 넘겨야 한다.

[발견사항 2026-07-17 ②] 정부지원_manifest_v2.yaml 안에는 서로 완전히 독립된 두 DAG가
  들어있다: (a) 매칭~심사 5-stage(collect_announcements → eligibility_screen →
  program_matching → draft_application_stage → judge_self_review), (b) 발표뒷단
  8-stage(선정접수 → … → 발표패키지저장). triggers 섹션에는 (b)의 진입점(선정접수)
  하나만 선언돼 있고 (a)를 시작시키는 트리거가 없다. 즉 지금 이 manifest로
  `runner.py --trigger event`를 돌리면 (b)만 실제로 실행되고, (a)는 정적검증 그래프
  에는 포함되지만 시작할 방법이 없다(트리거 추가는 정부지원_manifest_v2.yaml 수정이라
  이 작업 범위 밖 — 그 파일도 '클로드 정부지원사업 ai' 폴더 안이라 손대지 않음).
  STAGE_FUNCS에는 (a) 5-stage도 전부 매핑해뒀다(정적검증 통과 + 향후 트리거가 추가되면
  바로 쓸 수 있도록) — 다만 "지금 CLI로 실제 도달 가능한 건 (b)뿐"이라는 점은 기록해둔다.

[발견사항 2026-07-17 ③] eligibility_screen(io.writes: eligibility_check_result)에 대응하는
  독립 함수가 run.py에 없다. check_eligibility_and_disqualification()은 match_programs()
  내부 루프에서 공고 1건씩 호출되는 헬퍼일 뿐이고, match_programs()는 사전 계산된
  eligibility_check_result를 인자로 받지 않는다 — 자기 안에서 매번 다시 계산한다.
  이 어댑터의 eligibility_screen 핸들러는 원본 함수를 그대로(수정 없이) 재사용해 공고별
  결과를 모아 eligibility_check_result에 채워 manifest 계약(io.writes)은 만족시키지만,
  이 값은 program_matching의 실제 판정에는 소비되지 않는 "참고용 스냅샷"이다 — 이건
  어댑터의 임의 변환이 아니라 원본 run.py가 애초에 이 경계로 안 나뉘어 있었다는 사실을
  그대로 노출한 것이다.

[발견사항 2026-07-17 ④] needs_confirmation 필드는 manifest상 judge_self_review 단독
  writer로 선언돼 있지만, 실제로는 collect_and_extract_announcements()와
  match_programs() 둘 다 각자의 needs_confirmation 리스트를 반환한다(원본 run()이 이
  셋을 합쳐 정렬·중복제거 후 최종 출력한다 — run.py 2286행 근처
  `sorted(set(needs_confirmation))`). 이 어댑터는 collect_announcements/
  program_matching 단계에서 그 결과를 ctx의 비공개 키(_nc_collect/_nc_match — manifest에
  선언 안 된 필드라 러너의 경계검증 대상이 아님)에 잠시 담아뒀다가, judge_self_review
  단계에서 원본 run()과 동일한 방식(합치기 + sorted(set(...)))으로 합쳐
  needs_confirmation에 최종 기록한다.
────────────────────────────────────────────────────────────────────────────
"""
import importlib.util
from pathlib import Path

# 정부지원 run.py 위치 — 볼트 루트 기준 상대 경로(러너: ai공장짓기/runner/adapters/).
# parents[3]은 실제로는 "1. Projects" 폴더를 가리킴(pest_adapter.py와 동일한 변수명 관례 — 재사용).
VAULT_ROOT = Path(__file__).resolve().parents[3]
GOVSUPPORT_RUN_PY = VAULT_ROOT / "클로드 정부지원사업 ai" / "scripts" / "run.py"


def _load_govsupport_module():
    if not GOVSUPPORT_RUN_PY.is_file():
        raise FileNotFoundError(f"정부지원 run.py를 찾을 수 없음: {GOVSUPPORT_RUN_PY}")
    spec = importlib.util.spec_from_file_location("govsupport_run_module", str(GOVSUPPORT_RUN_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_GOV = _load_govsupport_module()


# ----------------------------------------------------------------------
# (a) 매칭~심사 5-stage — collect_and_extract_announcements / match_programs /
#     draft_application / judge_mode_self_review / apply_quality_gate를
#     원본 그대로 호출하고, 결과를 shared_context 필드에 옮겨 담기만 한다.
#     ([발견사항 ②] 참고 — 현재 manifest 트리거로는 이 5-stage에 도달할 방법이 없지만,
#     정적검증 완전성과 향후 트리거 추가에 대비해 매핑은 채워둔다.)
# ----------------------------------------------------------------------

def _run_collect_announcements(ctx, stage):
    """kind: model(tier: haiku). 원본 run()의 STEP 1과 동일.
    business_profile/target_period는 이 manifest의 shared_context에서 written_by: []
    (외부 호출자가 주입)로 선언돼 있음 — 이 stage가 파이프라인의 진입점(depends_on: [])이라
    ctx["_input"](러너가 항상 채워주는 원본 입력)에서 꺼내 shared_context에 등록해준다
    (방역 run_수집봇과 동일한 관례: 진입 stage가 _input을 읽어 공유 필드로 승격)."""
    inp = ctx.get("_input") or {}
    business_profile = inp.get("business_profile") or {}
    target_period = inp.get("target_period") or {}
    ctx["business_profile"] = business_profile
    ctx["target_period"] = target_period

    # 테스트/회귀용 선택 필드 — 실제 CLI(main())의 두 번째 인자(announcements_path)에 대응.
    announcements_path = inp.get("_announcements_path")
    raw_announcements, needs_confirmation = _GOV.collect_and_extract_announcements(
        target_period, announcements_path
    )
    ctx["raw_announcements"] = raw_announcements
    ctx["_nc_collect"] = needs_confirmation  # [발견사항 ④] 비공개 키, judge_self_review에서 합침
    return f"raw_announcements {len(raw_announcements)}건 수집 (needs_confirmation 잠정 {len(needs_confirmation)}건)"


def _run_eligibility_screen(ctx, stage):
    """kind: model(tier: sonnet). [발견사항 ③] 참고 — check_eligibility_and_disqualification()을
    공고별로 직접 호출해 참고용 스냅샷을 만든다. program_matching의 실제 판정에는 쓰이지 않는다
    (원본 run.py 구조가 그렇다 — 어댑터가 임의로 그렇게 만든 게 아님)."""
    profile = ctx.get("business_profile") or {}
    announcements = ctx.get("raw_announcements") or []
    ref_date = _GOV.today()
    result = {}
    for a in announcements:
        name = a.get("program_name", "(이름 없음)")
        criteria, disq_risks, unverifiable = _GOV.check_eligibility_and_disqualification(
            profile, a, ref_date
        )
        result[name] = {
            "criteria": [{"name": n, "result": r} for n, r in criteria],
            "disqualification_risks": disq_risks,
            "unverifiable_exclusions": unverifiable,
        }
    ctx["eligibility_check_result"] = result
    return (f"eligibility_check_result {len(result)}건 계산(참고용 스냅샷 — "
            f"program_matching은 자체 재계산함, [발견사항 ③])")


def _run_program_matching(ctx, stage):
    """kind: model(tier: sonnet). 원본 run()의 STEP 3과 동일(match_programs)."""
    profile = ctx.get("business_profile") or {}
    announcements = ctx.get("raw_announcements") or []
    target_period = ctx.get("target_period") or {}
    ref_date = _GOV.today()
    matched, excluded, needs_confirmation = _GOV.match_programs(
        profile, announcements, target_period, ref_date
    )
    ctx["matched_programs"] = matched
    ctx["excluded_programs"] = excluded
    ctx["_nc_match"] = needs_confirmation  # [발견사항 ④] 비공개 키, judge_self_review에서 합침
    return f"matched {len(matched)}건 / excluded {len(excluded)}건"


def _run_draft_application_stage(ctx, stage):
    """kind: model(tier: sonnet). 원본 run()의 STEP 4와 동일(draft_application).
    top_match 없으면 draft_application()이 None을 반환 — 러너 경계검증은 None을 허용함."""
    profile = ctx.get("business_profile") or {}
    matched = ctx.get("matched_programs") or []
    top_match = matched[0] if matched else None
    ctx["draft_application"] = _GOV.draft_application(profile, top_match)
    return "draft_application 생성" if ctx["draft_application"] else "draft_application 없음(매칭된 공고 없음)"


def _run_judge_self_review(ctx, stage):
    """kind: model(tier: opus). 원본 run()의 STEP 5(judge_mode_self_review) + quality_gate와 동일.
    [발견사항 ④]에 따라 needs_confirmation을 collect/match 단계 결과와 합쳐 최종 기록한다."""
    profile = ctx.get("business_profile") or {}
    matched = ctx.get("matched_programs") or []
    draft = ctx.get("draft_application")
    top_match = matched[0] if matched else None

    judge_review = _GOV.judge_mode_self_review(draft, top_match, profile)
    quality_gate_result = _GOV.apply_quality_gate(matched, judge_review, draft)

    nc = list(ctx.get("_nc_collect") or []) + list(ctx.get("_nc_match") or [])
    ctx["needs_confirmation"] = sorted(set(nc))  # 원본 run() 2286행 근처와 동일 방식
    ctx["judge_review"] = {k: v for k, v in judge_review.items() if not k.startswith("_")}
    ctx["quality_gate_result"] = quality_gate_result
    return f"lock_state={quality_gate_result.get('lock_state')} overall_confidence={quality_gate_result.get('overall_confidence')}"


# ----------------------------------------------------------------------
# (b) 발표뒷단 8-stage — run.py의 stage_* 함수들을 그대로 호출.
#     이 8개는 이미 (ctx, ...) 형태의 stage 함수로 짜여 있어 방역 패턴과 가장 가깝다.
# ----------------------------------------------------------------------

def _run_선정접수(ctx, stage):
    """kind: local. submitted_application_ref 없으면 stage_선정접수가 ValueError를 던진다 —
    삼키지 않고 그대로 올려 러너가 [정지]로 처리하게 둔다(추측 금지 원칙 승계)."""
    inp = ctx.get("_input") or {}
    result = _GOV.stage_선정접수(inp)
    ctx["selection_notice"] = result["selection_notice"]
    ctx["submitted_application_ref"] = result["submitted_application_ref"]
    return f"submitted_application_ref={result['submitted_application_ref']}"


def _run_발표요건추출(ctx, stage):
    """kind: model(tier: low_cost)."""
    inp = ctx.get("_input") or {}
    announcement = inp.get("announcement")
    ctx["presentation_requirements"] = _GOV.stage_발표요건추출(ctx, announcement=announcement)
    return f"발표평가_존재={ctx['presentation_requirements'].get('발표평가_존재')}"


def _run_PPT초안생성(ctx, stage):
    """kind: model(tier: mid)."""
    ctx["ppt_draft"] = _GOV.stage_ppt초안생성(ctx)
    d = ctx["ppt_draft"]
    return f"extraction_method={d.get('extraction_method')} render_error={d.get('render_error')}"


def _pick_human_decision(ctx, decisions, lookup_key, track_key=None):
    """decisions[lookup_key]가 리스트면(재시도 시나리오 테스트용) 호출 횟수만큼 순차 소비, 아니면
    그대로 반환. track_key는 ctx에 호출횟수를 저장할 때 쓰는 키(생략하면 lookup_key와 동일) —
    발표패키지승인처럼 decisions의 실제 키("script"/"qna")와 ctx 추적 네임스페이스를 분리해야
    할 때만 다르게 넘긴다([버그 발견 2026-07-17] 처음엔 이 둘을 같은 값으로 취급했다가
    발표패키지승인에서 decisions.get("발표패키지승인_script")가 항상 미스(실제 키는 "script")
    -> 매번 기본값 "승인"으로만 떨어지는 버그가 검증 중 재현됨 — lookup_key/track_key를 분리해
    수정)."""
    track_key = track_key or lookup_key
    call_key = f"_human_call_count_{track_key}"
    idx = ctx.get(call_key, 0)
    ctx[call_key] = idx + 1
    raw = decisions.get(lookup_key, "승인")
    if isinstance(raw, list):
        raw = raw[min(idx, len(raw) - 1)] if raw else "승인"
    return raw


def _run_PPT승인(ctx, stage):
    """kind: human. mock — 실제 승인 UI 없음(방역/꽃집과 동일 알려진 한계).
    입력 JSON의 human_decisions.PPT승인 값을 사용, 없으면 자동승인(default_human_stub과 동일 관례)."""
    inp = ctx.get("_input") or {}
    decisions = inp.get("human_decisions") or {}
    raw = _pick_human_decision(ctx, decisions, "PPT승인")
    ctx["ppt_draft"] = _GOV.stage_ppt승인(ctx, mock_decision=raw)
    return f"[HUMAN-QUEUE 스텁] 결정={raw} -> status={ctx['ppt_draft']['approval']['status']}"


def _run_발표대본생성(ctx, stage):
    """kind: model(tier: mid). depends_on: PPT승인 — ppt_draft.locked=False면 stage_발표대본생성이
    RuntimeError를 던진다(§17 판정2, depends_on 강제 재검증). 삼키지 않고 그대로 올린다."""
    ctx["presentation_script"] = _GOV.stage_발표대본생성(ctx)
    return f"script_lines {len(ctx['presentation_script'].get('script_lines', []))}줄"


def _run_예상QNA생성(ctx, stage):
    """kind: model(tier: high). judge_review는 매칭~심사 파이프라인이 실행됐을 때만 ctx에 있음 —
    없어도([발견사항 ②] 트리거 미도달 등) stage_예상qna생성이 judge_review=None을 안전하게 처리함."""
    ctx["expected_qna"] = _GOV.stage_예상qna생성(ctx, judge_review=ctx.get("judge_review"))
    return f"qna_templates {len(ctx['expected_qna'].get('qna_templates', []))}개"


def _run_발표패키지승인(ctx, stage):
    """kind: human. 대본+Q&A 일괄 게이트(부분 반려 가능, §17 판정3).
    human_decisions.발표패키지승인 = {"script": "...", "qna": "..."} 형식(없으면 각각 자동승인)."""
    inp = ctx.get("_input") or {}
    decisions = (inp.get("human_decisions") or {}).get("발표패키지승인") or {}
    script_decision = _pick_human_decision(ctx, decisions, "script", track_key="발표패키지승인_script")
    qna_decision = _pick_human_decision(ctx, decisions, "qna", track_key="발표패키지승인_qna")
    result = _GOV.stage_발표패키지승인(ctx, script_decision=script_decision, qna_decision=qna_decision)
    return f"[HUMAN-QUEUE 스텁] script={script_decision} qna={qna_decision} -> {result}"


def _run_발표패키지저장(ctx, stage):
    """kind: local. 저장 직전 3종 문서 전부 승인완료인지 재검증(방역 문자장부봇과 동일 안전장치) —
    아니면 stage_발표패키지저장이 RuntimeError를 던진다. 삼키지 않고 그대로 올린다."""
    ctx["presentation_package_record"] = _GOV.stage_발표패키지저장(ctx)
    return f"versions={ctx['presentation_package_record'].get('versions')}"


# ----------------------------------------------------------------------
# 1) STAGE_FUNCS — manifest 정부지원_manifest_v2.yaml의 stage id -> 위 함수 매핑
# ----------------------------------------------------------------------
STAGE_FUNCS = {
    # (a) 매칭~심사 5-stage — [발견사항 ②] 현재 트리거로는 도달 불가, 정적검증/향후용으로 매핑
    "collect_announcements": _run_collect_announcements,
    "eligibility_screen": _run_eligibility_screen,
    "program_matching": _run_program_matching,
    "draft_application_stage": _run_draft_application_stage,
    "judge_self_review": _run_judge_self_review,
    # (b) 발표뒷단 8-stage — 실제 트리거(type: event, source: selection_notice)로 도달 가능
    "선정접수": _run_선정접수,
    "발표요건추출": _run_발표요건추출,
    "PPT초안생성": _run_PPT초안생성,
    "PPT승인": _run_PPT승인,
    "발표대본생성": _run_발표대본생성,
    "예상QNA생성": _run_예상QNA생성,
    "발표패키지승인": _run_발표패키지승인,
    "발표패키지저장": _run_발표패키지저장,
}


# ----------------------------------------------------------------------
# 2) run_if 판정 — 정부지원_manifest_v2.yaml에 등장하는 조건은 이 하나뿐
#    ("발표평가_또는_발표자료가_요구됨", PPT초안생성/PPT승인/발표대본생성/예상QNA생성/
#    발표패키지승인/발표패키지저장 6개 stage가 공유).
# ----------------------------------------------------------------------
def evaluate_run_if(condition, ctx):
    # [버그 발견 2026-07-17, 검증 중 실제로 재현됨] 러너(runner.py)는 핸들러가 evaluate_run_if를
    # 제공하기만 하면, run_if가 아예 선언되지 않은 stage(condition=None)에 대해서도 무조건 이
    # 함수로 위임한다(Runner._eval_run_if — fn이 있으면 condition이 None이든 아니든 그냥 fn(condition, ctx)
    # 호출) — "run_if 없으면 항상 실행"이라는 기본 동작은 핸들러가 없을 때만 러너가 대신 해준다.
    # 방역 run.py의 evaluate_run_if도 동일하게 condition is None을 맨 앞에서 처리한다 — 그 관례를
    # 그대로 따른다. 이걸 빠뜨리면 run_if가 없는 stage(선정접수/발표요건추출 등)까지 전부
    # "알 수 없는 조건"으로 스킵돼버린다(실제로 처음 실행에서 이 증상으로 재현·확인함).
    if condition is None:
        return True, "run_if 없음 — 항상 실행"
    if condition == "발표평가_또는_발표자료가_요구됨":
        requirements = ctx.get("presentation_requirements") or {}
        return _GOV.evaluate_presentation_run_if(requirements)
    return False, f"알 수 없는 run_if 조건 '{condition}' — 안전하게 기본값 False(건너뜀) 처리(정부지원 어댑터에 매핑 없음)"


# ----------------------------------------------------------------------
# 3) 반려 감지 — PPT승인(단일 문서)과 발표패키지승인(대본+QNA 두 문서, 부분 반려 가능)에서만 의미 있음
# ----------------------------------------------------------------------
def pending_rejections(ctx, stage_id):
    if stage_id not in ("PPT승인", "발표패키지승인"):
        return {}
    all_rej = _GOV._pending_presentation_rejections(ctx)  # {"ppt_draft"/"presentation_script"/"expected_qna": rejection_target}
    if stage_id == "PPT승인":
        # on_reject가 return_to: PPT초안생성(단일 목적지)이라 reason 값 자체는 라우팅에 안 쓰이지만,
        # "반려됨"이라는 사실은 rejections dict가 비어있지 않은 것으로 러너가 판정한다.
        return {"PPT승인": all_rej["ppt_draft"]} if "ppt_draft" in all_rej else {}
    # 발표패키지승인: 문서별 독립 반려(§17 판정3) — by_reason 매핑("대본문제"/"질문답변문제")과
    # stage_발표패키지승인의 rejection_target 값이 정확히 일치해야 한다(run.py 3065행 참고).
    result = {}
    if "presentation_script" in all_rej:
        result["presentation_script"] = all_rej["presentation_script"]
    if "expected_qna" in all_rej:
        result["expected_qna"] = all_rej["expected_qna"]
    return result


# ----------------------------------------------------------------------
# 4) stop_condition — 정부지원_manifest_v2.yaml에는 어떤 stage에도 stop_condition이 없음
# ----------------------------------------------------------------------
def should_stop(ctx, stage):
    return False, ""


# ----------------------------------------------------------------------
# 5) 묶음 순차 처리 — 정부지원_manifest_v2.yaml에는 schedule 트리거/묶음 처리 정책이 없음
#    (트리거가 selection_notice event 단 하나뿐) — 항상 None(묶음 처리 없음)
# ----------------------------------------------------------------------
def batch_items(ctx, entry_stage):
    return None
