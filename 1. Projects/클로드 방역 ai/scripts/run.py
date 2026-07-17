#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pest-control-ai-ops / scripts/run.py  (manifest v2, schema: ai공장짓기/manifest.schema.v2.yaml)

방역&클린 AI 운영관리 스킬의 실행 뼈대(skeleton). 아직 실제 AI 모델을 호출하지
않고, manifest.yaml의 stages/triggers/run_if/entry_points를 그대로 읽어
"구조가 처음부터 끝까지 한 번 통과되는지"만 확인하는 목적의 스텁 실행기다.

[2026-07-07 (문서승인워크플로우, Fable 5 결정) 갱신] decision-log_skill-
factory-architecture.md 7절 반영:
  - 문서생성봇/문서승인 두 stage를 "반려-재작업 루프"로 묶어서 실행한다.
    depends_on 그래프에는 순환을 만들지 않는다(DAG 유지 - return_to는
    그래프 엣지가 아니라 메타데이터라는 스키마 원칙 그대로 따름) - 대신
    이 실행기가 명령형(imperative)으로 재시도 루프를 돈다.
  - 문자장부봇(발송)에 "승인완료 아닌 문서는 절대 발송 금지" 철칙을
    강제 구현 - 파이프라인 순서만 믿지 않고 발송 stage 자체에서 재검증.

사용법:
  python3 run.py [입력 JSON 경로] [--manifest <manifest.yaml 경로>] [--trigger event|schedule]
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import date, timedelta

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml이 필요합니다: pip install pyyaml --break-system-packages")
    sys.exit(1)

import llm_client  # 2026-07-17: 진짜 API 키 연결 후 신설 - 4개 model stage가 공용으로 사용

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_MANIFEST = ROOT_DIR / "manifest.yaml"
DEFAULT_MOCK_INPUT = ROOT_DIR / "test" / "temp_mock_input_임시.json"
DEFAULT_SCHEDULE_MOCK_INPUT = ROOT_DIR / "test" / "temp_schedule_mock_input_임시.json"

CYCLE_DAYS = {
    "월1회": 30,
    "격월": 60,
    "분기": 90,
    "반기": 180,
    "연1회": 365,
}
DEFAULT_CYCLE_DAYS = 90

MAX_APPROVAL_RETRIES = 3  # [신규] 반려-재작업 루프 최대 재시도 횟수(mock 한계 - open_questions 참고)

# [2026-07-07 신규] business_info 기본값 — 실제 운영에서는 대표자가 설정하는
# 값이어야 하지만, 이 mock 실행기에는 별도 설정 단계가 없어 상수로 둠.
# 테스트 입력(_input.business_info)으로 덮어쓸 수 있음.
DEFAULT_BUSINESS_INFO = {
    "상호명": "방역&클린",
    "대표자명": "[대표자명 미입력 - 확인 필요]",
    "사업자등록번호": "[사업자등록번호 미입력 - 확인 필요]",
}


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _today():
    override = os.environ.get("PEST_SKILL_TODAY")
    if override:
        return date.fromisoformat(override)
    return date.today()


def build_graph(stages, triggers=None):
    by_id = {s["id"]: s for s in stages}
    successors = {s["id"]: [] for s in stages}
    for s in stages:
        for dep in s.get("depends_on", []) or []:
            successors.setdefault(dep, []).append(s["id"])

    if triggers:
        trigger_entry_by_key = {}
        for t in triggers:
            ttype = t.get("type")
            ident = t.get("source") if ttype == "event" else t.get("interval") if ttype == "schedule" else None
            if ttype and ident:
                trigger_entry_by_key[f"{ttype}:{ident}"] = t.get("entry_stage")
        for s in stages:
            for ep in (s.get("entry_points") or []):
                origin = trigger_entry_by_key.get(ep)
                if not origin or origin == s["id"]:
                    continue
                successors.setdefault(origin, [])
                if s["id"] not in successors[origin]:
                    successors[origin].append(s["id"])

    return by_id, successors


def reachable_from(entry_id, successors):
    seen = set()
    queue = [entry_id]
    order = []
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        order.append(cur)
        for nxt in successors.get(cur, []):
            if nxt not in seen:
                queue.append(nxt)
    return order


def topo_order(stage_ids, by_id, successors):
    stage_id_set = set(stage_ids)
    indeg = {sid: 0 for sid in stage_ids}
    edges = {sid: [] for sid in stage_ids}
    for sid in stage_ids:
        for nxt in successors.get(sid, []):
            if nxt in stage_id_set:
                edges[sid].append(nxt)
                indeg[nxt] += 1
    queue = [sid for sid in stage_ids if indeg[sid] == 0]
    order = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in edges[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(stage_ids):
        missing = stage_id_set - set(order)
        raise RuntimeError(f"위상정렬 실패 - 순환 의존성 의심: {missing}")
    return order


def evaluate_run_if(condition, ctx):
    if condition is None:
        return True, "run_if 없음 - 항상 실행"
    if condition == "미정_골든셋수집후결정":
        return False, "미정 상태 - 골든셋 확보 전까지 기본 꺼짐(사용자 지시, 2026-07-07)"
    if condition == "완료보고서_또는_소독증명서를_요청함":
        cr = ctx.get("customer_record") or {}
        wants_report = bool(cr.get("report_requested") if "report_requested" in cr else ctx.get("report_requested"))
        wants_cert = bool(cr.get("certificate_requested") if "certificate_requested" in cr else ctx.get("certificate_requested"))
        return (wants_report or wants_cert), f"report_requested={wants_report}, certificate_requested={wants_cert}"
    if condition == "승인필수_문서가_존재함":
        dd = ctx.get("document_draft") or {}
        needed = any((dd.get(k) or {}).get("approval_required") for k in ("report", "certificate"))
        return needed, f"approval_required=true 문서 존재={needed}"
    if condition == "고객이_문서를_요청함":
        cr = ctx.get("customer_record") or {}
        wants_doc = bool(cr.get("document_requested") or ctx.get("document_requested"))
        return wants_doc, f"[구버전 조건] document_requested={wants_doc}"
    return False, f"알 수 없는 run_if 조건 '{condition}' - 안전하게 기본값 False(건너뜀) 처리"


# ---------------------------------------------------------------------
# stage별 목업(mock) 실행 함수 - 전부 실제 모델 호출 없는 스텁
# ---------------------------------------------------------------------

def run_수집봇(ctx, stage):
    inp = ctx["_input"]
    ctx["raw_text"] = inp.get("text", "")
    ctx["raw_audio"] = inp.get("audio_url", "")
    ctx["source_type"] = inp.get("source_type", "manual")
    ctx["created_at"] = inp.get("created_at", "2026-07-07T00:00:00")
    return f"raw_text={ctx['raw_text']!r} source_type={ctx['source_type']}"


def run_전사봇(ctx, stage):
    ctx["stt_text"] = ctx.get("raw_text", "")
    ctx["cleaned_text"] = ctx.get("raw_text", "").strip()
    return "stt_text = raw_text (mock, 실제 STT 호출 없음)"


_INQUIRY_CLASSIFICATIONS = ["방역요청", "견적문의", "일반문의", "스팸무관", "확인필요"]

_INQUIRY_SYSTEM_PROMPT = """당신은 경남 진주 지역 방역업체(방역&클린)의 문의 판정 담당자입니다.
전화/문자 원문 1건을 보고 아래 5개 분류 중 정확히 하나로 판정하세요.

- 방역요청: 실제로 방역/소독 방문을 원하는 의도가 명확함(바퀴벌레·해충·쥐·곰팡이 등 구체적 문제 + 방문 요청)
- 견적문의: 방문 확정은 아니지만 가격/견적을 물어봄
- 일반문의: 방역과 무관한 일반 문의(영업시간, 위치 등)
- 스팸무관: 스팸이거나 방역과 완전히 무관함
- 확인필요: 위 어디에도 자신 있게 넣기 애매함 - 확신이 없으면 반드시 이 값을 고르세요

반드시 아래 JSON 형식으로만 답하세요:
{"inquiry_classification": "<5개 중 하나>", "confidence": <0.0~1.0>, "reason": "<한 문장 이유>"}
"""


def _classify_inquiry_rule_based(text: str) -> str:
    keywords_pest = ["방역", "소독", "바퀴", "해충", "쥐", "곰팡이"]
    return "방역요청" if any(k in text for k in keywords_pest) else "일반문의"


def run_문의판정봇(ctx, stage):
    """2026-07-17: 진짜 Claude 호출로 교체(manifest.yaml tier: sonnet). 실패 시 기존
    키워드 매칭 mock으로 자동 대체 - 꽃집 스킬과 동일한 안전망 패턴."""
    text = ctx.get("stt_text", "") or ctx.get("raw_text", "")
    try:
        result = llm_client.call_llm_json(
            tier="sonnet", system_prompt=_INQUIRY_SYSTEM_PROMPT, user_prompt=f"원문:\n{text}"
        )
        classification = result.get("inquiry_classification")
        if classification not in _INQUIRY_CLASSIFICATIONS:
            raise llm_client.LLMUnavailableError(f"허용된 5개 분류 밖의 값: {classification!r}")
        ctx["inquiry_classification"] = classification
        return f"inquiry_classification={classification} (Claude 호출, confidence={result.get('confidence')}) - {result.get('reason')}"
    except llm_client.LLMUnavailableError as e:
        ctx["inquiry_classification"] = _classify_inquiry_rule_based(text)
        return f"inquiry_classification={ctx['inquiry_classification']} (LLM 호출 실패로 키워드 매칭 mock 대체: {e})"


def run_현장분리봇(ctx, stage):
    ctx["site_segments"] = []
    ctx["split_status"] = "완료"
    return "mock: 분리 없음(단일 현장으로 취급)"


_CORRECTION_SYSTEM_PROMPT = """당신은 경남 진주 지역 방역업체(방역&클린)의 문의 원문 보정 담당자입니다.
STT(음성인식) 오인식이나 진주 지역 사투리·구어체를 문맥으로 보정한 normalized_text를 만드세요.

절대 원칙:
- 의미가 바뀌지 않는 명백한 오류/사투리 표기만 반영하세요(예: 사투리 어미를 표준어로,
  명백한 오인식을 문맥상 뜻이 분명한 단어로).
- 조금이라도 확신이 안 서는 보정은 원문을 바꾸지 말고 그대로 두세요.
- 원문에 없는 내용을 지어내지 마세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "normalized_text": "<보정된 텍스트>",
  "correction_log": [{"original": "...", "corrected": "...", "note": "..."}],
  "reason": "<한 문장 이유>"
}
"""


def run_보정봇(ctx, stage):
    """2026-07-17: 진짜 Claude 호출로 교체(manifest.yaml tier: sonnet). 실패 시 기존
    항등(identity) mock으로 자동 대체."""
    text = ctx.get("stt_text") or ctx.get("raw_text", "")
    try:
        result = llm_client.call_llm_json(
            tier="sonnet", system_prompt=_CORRECTION_SYSTEM_PROMPT, user_prompt=f"원문:\n{text}"
        )
        normalized = result.get("normalized_text")
        if not isinstance(normalized, str):
            raise llm_client.LLMUnavailableError(f"normalized_text 형식이 이상함: {normalized!r}")
        ctx["normalized_text"] = normalized
        ctx["correction_log"] = result.get("correction_log") or []
        return f"normalized_text 보정 완료(Claude 호출, 보정 {len(ctx['correction_log'])}건) - {result.get('reason')}"
    except llm_client.LLMUnavailableError as e:
        ctx["normalized_text"] = text
        ctx["correction_log"] = []
        return f"normalized_text = stt_text 그대로 (LLM 호출 실패로 mock 대체: {e})"


_INQUIRY_ORGANIZE_SYSTEM_PROMPT = """당신은 방역업체(방역&클린) 문의 정리 담당자입니다.
정규화된 문의 원문에서 아래 필드를 채우세요:
space_type(공간 유형, 예: 사무실/가정집/카페), visit_requested_date(방문 희망일,
원문에 명시된 경우만, ISO 날짜 형식이 아니어도 원문 표현 그대로 가능),
report_requested(방역 보고서 요청 여부, true/false),
certificate_requested(소독증명서 요청 여부, true/false),
followup_needed(후속 연락 필요 여부, true/false).

절대 원칙: 원문에 명시되지 않은 값은 절대 채우지 마세요(null로 남기고
missing_fields에 넣으세요). 특히 고객 이름(customer_name)은 이 stage가
채우지 않습니다 - 전화/문자 발신자 정보로 별도 확보하는 값이라 원문 텍스트만으로
추측하면 안 됩니다. 확신 없는 값을 지어내지 마세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "space_type": null|"...",
  "visit_requested_date": null|"...",
  "report_requested": true|false,
  "certificate_requested": true|false,
  "followup_needed": true|false,
  "field_confidence": {"<필드명>": <0.0~1.0>, ...},
  "field_sources": {"<필드명>": "<근거 또는 못 채운 이유>", ...},
  "missing_fields": ["<필드명>", ...]
}
"""


def run_문의정리봇(ctx, stage):
    """2026-07-17: 진짜 Claude 호출로 교체(manifest.yaml tier: haiku). customer_name은
    이 stage가 원래부터 채우지 않는 설계라(전화/문자 발신자 정보로 별도 확보) 그대로
    _input에서 pass-through. 실패 시 기존 mock(테스트용 _input 직접 복사)으로 대체."""
    text = ctx.get("normalized_text", "")
    inp = ctx["_input"]
    ctx["customer_name"] = inp.get("customer_name", "확인필요")
    ctx["request_note"] = text
    try:
        result = llm_client.call_llm_json(
            tier="haiku", system_prompt=_INQUIRY_ORGANIZE_SYSTEM_PROMPT, user_prompt=f"정규화된 문의 원문:\n{text}"
        )
        ctx["space_type"] = result.get("space_type") or inp.get("space_type", "확인필요")
        ctx["visit_requested_date"] = result.get("visit_requested_date") or inp.get("visit_requested_date", "확인필요")
        ctx["report_requested"] = bool(result.get("report_requested"))
        ctx["certificate_requested"] = bool(result.get("certificate_requested"))
        ctx["followup_needed"] = bool(result.get("followup_needed"))
        ctx["field_confidence"] = result.get("field_confidence") or {}
        ctx["field_sources"] = result.get("field_sources") or {}
        ctx["missing_fields"] = result.get("missing_fields") or []
        return (
            f"report_requested={ctx['report_requested']} certificate_requested={ctx['certificate_requested']} "
            f"(Claude 호출)"
        )
    except llm_client.LLMUnavailableError as e:
        ctx["space_type"] = inp.get("space_type", "확인필요")
        ctx["visit_requested_date"] = inp.get("visit_requested_date", "확인필요")
        report_wanted = ("보고서" in text) or bool(inp.get("report_requested"))
        cert_wanted = ("증명서" in text) or bool(inp.get("certificate_requested"))
        if not report_wanted and not cert_wanted and inp.get("document_requested"):
            report_wanted = True
        ctx["report_requested"] = report_wanted
        ctx["certificate_requested"] = cert_wanted
        ctx["followup_needed"] = bool(inp.get("followup_needed", False))
        ctx["field_confidence"] = {"overall": 0.7}
        ctx["field_sources"] = {}
        ctx["missing_fields"] = []
        return f"report_requested={report_wanted} certificate_requested={cert_wanted} (LLM 호출 실패로 mock 대체: {e})"


def run_견적금액산정봇(ctx, stage):
    ctx["estimated_price"] = None
    return "mock: 미실행 상태 (run_if로 꺼져 있음)"


_REVIEW_SYSTEM_PROMPT = """당신은 방역업체(방역&클린) 파이프라인의 검수 매니저입니다.
여러 상류 단계의 결과(고객명/공간유형/방문희망일/요청사항/문서요청여부/후속연락여부/
missing_fields/estimated_price 등)를 받아서, 대표자가 확인해야 할 항목
(review_checklist)과 우선순위(review_priority: 빨강/노랑/파랑/초록 중 하나)를 만드세요.

우선순위 판단 기준:
- 빨강: 방문희망일처럼 예약에 꼭 필요한 핵심 필드가 없거나 확인이 시급할 때
- 노랑: missing_fields가 여러 개 있거나 애매한 부분이 있을 때
- 파랑: missing_fields가 일부 있지만 핵심 필드는 채워져 급하지 않을 때
- 초록: missing_fields가 전혀 없고 핵심 정보가 다 확인됐을 때

절대 원칙: 고객 이름(customer_name)은 이 스킬에서 원래 전화/문자 발신자 정보로
별도 확보하는 값이라 이것 때문에 priority를 필요 이상으로 높이지 마세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "review_checklist": ["<확인 항목>", ...],
  "review_priority": "빨강"|"노랑"|"파랑"|"초록",
  "editable_fields": ["<필드명>", ...],
  "reason": "<한 문장 이유>"
}
"""


def run_검수매니저(ctx, stage):
    """2026-07-17: 진짜 Claude 호출로 교체(manifest.yaml tier: sonnet). 실패 시 기존
    고정값 mock으로 자동 대체."""
    user_prompt = (
        f"customer_name: {ctx.get('customer_name')}\nspace_type: {ctx.get('space_type')}\n"
        f"visit_requested_date: {ctx.get('visit_requested_date')}\nrequest_note: {ctx.get('request_note')}\n"
        f"report_requested: {ctx.get('report_requested')}\ncertificate_requested: {ctx.get('certificate_requested')}\n"
        f"followup_needed: {ctx.get('followup_needed')}\nmissing_fields: {ctx.get('missing_fields')}\n"
        f"correction_log: {ctx.get('correction_log')}\nsplit_status: {ctx.get('split_status')}\n"
        f"estimated_price: {ctx.get('estimated_price')}"
    )
    try:
        result = llm_client.call_llm_json(tier="sonnet", system_prompt=_REVIEW_SYSTEM_PROMPT, user_prompt=user_prompt)
        if result.get("review_priority") not in ("빨강", "노랑", "파랑", "초록"):
            raise llm_client.LLMUnavailableError(f"review_priority 값이 이상함: {result.get('review_priority')!r}")
        ctx["review_checklist"] = result.get("review_checklist") or []
        ctx["review_priority"] = result["review_priority"]
        ctx["editable_fields"] = result.get("editable_fields") or ["customer_name", "visit_requested_date"]
        return f"review_priority={ctx['review_priority']} (Claude 호출) - {result.get('reason')}"
    except llm_client.LLMUnavailableError as e:
        ctx["review_checklist"] = ["고객명 확인", "방문희망일 확인"]
        ctx["review_priority"] = "초록"
        ctx["editable_fields"] = ["customer_name", "visit_requested_date"]
        return f"review_priority=초록 (LLM 호출 실패로 mock 대체: {e})"


def run_대표자검수(ctx, stage):
    ctx["confirmed_fields"] = {
        "customer_name": ctx.get("customer_name"),
        "space_type": ctx.get("space_type"),
        "visit_requested_date": ctx.get("visit_requested_date"),
        "request_note": ctx.get("request_note"),
        "report_requested": ctx.get("report_requested"),
        "certificate_requested": ctx.get("certificate_requested"),
        "followup_needed": ctx.get("followup_needed"),
    }
    ctx["manual_edits"] = {}
    ctx["approval_action"] = "방문확정"
    ctx["rejection_reason"] = None
    return ("[테스트모드 자동승인] 실제로는 대표자가 화면에서 검수해야 함(kind: human). "
            "이 게이트는 고객 문의/방문확정 승인이며, 문서 자체 승인(아래 문서승인 stage)과는 별개")


def run_고객DB저장봇(ctx, stage):
    ctx["customer_record"] = dict(ctx.get("confirmed_fields") or {})
    ctx["visit_cycle"] = ctx["_input"].get("visit_cycle")
    ctx["last_visit_date"] = ctx["_input"].get("last_visit_date")
    ctx["workflow_event"] = {"event": "저장완료"}
    ctx["version"] = 1
    cr = ctx["customer_record"]
    return (f"customer_record 저장 완료 "
            f"(report_requested={cr.get('report_requested')}, certificate_requested={cr.get('certificate_requested')})")


def run_방문알림봇(ctx, stage):
    cr = ctx.get("customer_record") or {}
    ctx["visit_notice"] = f"{cr.get('customer_name')} / {cr.get('visit_requested_date')} 방문 예정"
    return ctx["visit_notice"]


def run_현장완료입력봇(ctx, stage):
    ctx["site_completion_note"] = "[테스트모드 mock] 현장 방역 완료 처리됨"
    inp = ctx["_input"]
    ctx["used_chemicals"] = inp.get("used_chemicals", "[mock] 약품명 미입력")
    # [2026-07-07 신규] business_info(상호명/대표자명/사업자등록번호) — 테스트
    # 입력으로 덮어쓸 수 있고, 없으면 기본값을 그대로 저장·전달함(실제로
    # ctx에 저장되고 문서생성봇이 읽어가는지 검증 가능하도록).
    business_info = dict(DEFAULT_BUSINESS_INFO)
    business_info.update(inp.get("business_info") or {})
    ctx["business_info"] = business_info
    return (f"{ctx['site_completion_note']} / used_chemicals={ctx['used_chemicals']!r} "
            f"/ business_info={business_info!r}")


def run_현장사진봇(ctx, stage):
    ctx["site_photo"] = []
    return "mock: 미실행 상태(site_photo는 배열 타입, 현재는 빈 배열)"


def _new_approval_block(prev_doc):
    prev_approval = (prev_doc or {}).get("approval") or {}
    history = list(prev_approval.get("version_history") or [])
    if prev_approval.get("status") == "반려":
        history.append({
            "version": prev_approval.get("version"),
            "status": "반려",
            "rejection_reason": prev_approval.get("rejection_reason"),
            "rejection_target": prev_approval.get("rejection_target"),
        })
        new_version = (prev_approval.get("version") or 1) + 1
    else:
        new_version = prev_approval.get("version") or 1
    return {
        "status": "초안",
        "version": new_version,
        "approved_by": None,
        "approved_at": None,
        "rejection_reason": None,
        "rejection_target": None,
        "version_history": history,
    }


def run_문서생성봇(ctx, stage):
    cr = ctx.get("customer_record") or {}
    wants_report = bool(cr.get("report_requested"))
    wants_cert = bool(cr.get("certificate_requested"))
    created_date = (ctx["_input"].get("created_at") or "")[:10] or cr.get("visit_requested_date")
    prev_dd = ctx.get("document_draft") or {}

    # [2026-07-07 신규] business_info는 현장완료입력봇이 저장해둔 값을 그대로
    # 읽어옴 — 없으면(예: business_info 이전 버전 테스트 데이터) 기본값 사용.
    business_info = ctx.get("business_info") or dict(DEFAULT_BUSINESS_INFO)

    report = None
    if wants_report:
        report = {
            "작업일": created_date,
            "작업구역": cr.get("space_type"),
            "처리내용": ctx.get("site_completion_note"),
            "사용약품": ctx.get("used_chemicals"),
            "business_info": business_info,
            "approval_required": True,
            "approval": _new_approval_block(prev_dd.get("report")),
            "locked": False,
        }

    certificate = None
    if wants_cert:
        certificate = {
            "상호": business_info.get("상호명"),  # business_info.상호명과 자동 동기화(중복 입력 방지)
            "실시면적": "[mock] 면적 미입력",
            "소재지": cr.get("space_type"),
            "관리자확인": "[mock] 미확인",
            "소독기간": cr.get("visit_requested_date"),
            "소독내용종류": "[mock] 종류 미입력",
            "약품사용내용": ctx.get("used_chemicals"),
            "발급일": created_date,
            "소독실시자": "[mock] 담당자 미입력",
            "business_info": business_info,
            "approval_required": True,
            "approval": _new_approval_block(prev_dd.get("certificate")),
            "locked": False,
        }

    ctx["document_draft"] = {
        "report": report,
        "certificate": certificate,
        "storage_location": None,
        "retention_period": "2년(잠정, 법령 미확인)" if certificate else None,
        "note": "[mock 초안 - 법정 서식 미확정]",
    }
    ver_info = []
    if report:
        ver_info.append(f"report v{report['approval']['version']}")
    if certificate:
        ver_info.append(f"certificate v{certificate['approval']['version']}")
    return (f"document_draft 생성됨 - report={'있음' if report else '없음'}, "
            f"certificate={'있음' if certificate else '없음'} ({', '.join(ver_info)}) (mock)")


def run_문서승인(ctx, stage):
    attempt_idx = ctx.get("_문서승인_호출횟수", 0)
    ctx["_문서승인_호출횟수"] = attempt_idx + 1

    sim = ctx["_input"].get("문서승인_시뮬레이션", "승인완료")
    if isinstance(sim, list):
        sim = sim[min(attempt_idx, len(sim) - 1)] if sim else "승인완료"
    if isinstance(sim, str):
        sim = {"report": sim, "certificate": sim}
    dd = ctx.get("document_draft") or {}
    summary = []
    for doc_key in ("report", "certificate"):
        doc = dd.get(doc_key)
        if not doc or not doc.get("approval_required"):
            continue
        decision = sim.get(doc_key, "승인완료")
        approval = doc.setdefault("approval", {})
        if decision.startswith("반려"):
            target = decision.split(":", 1)[1] if ":" in decision else "표현오류"
            approval["status"] = "반려"
            approval["rejection_reason"] = f"[테스트모드 mock] {target} 사유로 반려"
            approval["rejection_target"] = target
            approval["approved_by"] = None
            approval["approved_at"] = None
            doc["locked"] = False
        else:
            approval["status"] = "승인완료"
            approval["approved_by"] = "[테스트모드 mock] 대표자"
            approval["approved_at"] = ctx["_input"].get("created_at", "2026-07-07T00:00:00")
            approval["rejection_reason"] = None
            approval["rejection_target"] = None
            doc["locked"] = True
        summary.append(f"{doc_key}={approval['status']}")
    return f"문서승인 결과: {', '.join(summary) if summary else '(승인대상 문서 없음)'}"


def run_문자장부봇(ctx, stage):
    dd = ctx.get("document_draft") or {}
    blocked = []
    approved = []
    for doc_key in ("report", "certificate"):
        doc = dd.get(doc_key)
        if not doc:
            continue
        status = (doc.get("approval") or {}).get("status")
        if doc.get("approval_required") and status != "승인완료":
            blocked.append((doc_key, status))
        elif doc.get("approval_required"):
            approved.append(doc_key)
    if blocked:
        raise RuntimeError(f"[안전장치 발동 - 발송 차단] 승인완료 안 된 문서 발송 시도: {blocked}")

    ctx["message_job"] = {"to": "고객"}
    ctx["message_result"] = {"status": "발송완료(mock)"}
    ctx["history_log"] = {"logged": True}
    return f"완료 안내 문자 발송(mock) - 승인완료돼 첨부된 문서: {approved if approved else '없음'}"


def run_만족도수집봇(ctx, stage):
    ctx["satisfaction_response"] = None
    return "mock: 아직 수집 안 함"


def run_리마인더봇(ctx, stage):
    customers = ctx["_input"].get("customers", [])
    today = _today()
    due_list = []
    for c in customers:
        last_visit_str = c.get("last_visit_date")
        if not last_visit_str:
            continue
        try:
            last_visit = date.fromisoformat(last_visit_str)
        except ValueError:
            continue
        cycle = c.get("visit_cycle")
        cycle_days = CYCLE_DAYS.get(cycle, DEFAULT_CYCLE_DAYS)
        due_date = last_visit + timedelta(days=cycle_days)
        days_until_due = (due_date - today).days
        if days_until_due <= 7:
            due_list.append({
                "customer_name": c.get("customer_name"),
                "space_type": c.get("space_type"),
                "visit_cycle": cycle,
                "last_visit_date": last_visit_str,
                "due_date": due_date.isoformat(),
                "days_until_due": days_until_due,
                "is_overdue": days_until_due < 0,
                "visit_requested_date": due_date.isoformat(),
                "report_requested": bool(c.get("report_requested", False)),
                "certificate_requested": bool(c.get("certificate_requested", False)),
            })
    ctx["reminder_due_list"] = due_list
    overdue_n = sum(1 for d in due_list if d["is_overdue"])
    return (f"reminder_due_list={len(due_list)}건(지연 {overdue_n}건) "
            f"- 오늘={today.isoformat()} 기준 실제 날짜비교")


STAGE_FUNCS = {
    "수집봇": run_수집봇,
    "전사봇": run_전사봇,
    "문의판정봇": run_문의판정봇,
    "현장분리봇": run_현장분리봇,
    "보정봇": run_보정봇,
    "문의정리봇": run_문의정리봇,
    "견적금액산정봇": run_견적금액산정봇,
    "검수매니저": run_검수매니저,
    "대표자검수": run_대표자검수,
    "고객DB저장봇": run_고객DB저장봇,
    "방문알림봇": run_방문알림봇,
    "현장완료입력봇": run_현장완료입력봇,
    "현장사진봇": run_현장사진봇,
    "문서생성봇": run_문서생성봇,
    "문서승인": run_문서승인,
    "문자장부봇": run_문자장부봇,
    "만족도수집봇": run_만족도수집봇,
    "리마인더봇": run_리마인더봇,
}


def _run_one_stage(sid, by_id, ctx, trace):
    stage = by_id[sid]
    run_if = stage.get("run_if")
    should_run, reason = evaluate_run_if(run_if, ctx)
    if not should_run:
        print(f"[SKIP] {sid} - {reason}")
        trace.append({"stage": sid, "ran": False, "reason": reason})
        return None

    func = STAGE_FUNCS.get(sid)
    if func is None:
        print(f"[SKIP] {sid} - 알 수 없는 stage(스텁 함수 없음)")
        trace.append({"stage": sid, "ran": False, "reason": "스텁 함수 없음"})
        return None

    result = func(ctx, stage)
    print(f"[RUN]  {sid} - {result}")
    trace.append({"stage": sid, "ran": True, "detail": result})

    stop_condition = stage.get("stop_condition")
    if stop_condition and ctx.get("inquiry_classification") in ("일반문의", "스팸무관", "확인필요"):
        print(f"[STOP] {sid}의 stop_condition에 따라 조기 종료 "
              f"(inquiry_classification={ctx.get('inquiry_classification')})")
        trace.append({"stage": "__stop__", "ran": False, "reason": "stop_condition"})
        return "STOP"
    return None


def _pending_rejections(ctx):
    dd = ctx.get("document_draft") or {}
    out = {}
    for k in ("report", "certificate"):
        doc = dd.get(k)
        if doc and doc.get("approval_required") and (doc.get("approval") or {}).get("status") == "반려":
            out[k] = doc["approval"].get("rejection_target")
    return out


def _run_document_approval_cycle(by_id, ctx, trace):
    approval_stage = by_id.get("문서승인")
    return_to_map = None
    if approval_stage:
        return_to_map = (approval_stage.get("on_fail") or {}).get("human_reject", {}).get("return_to")

    for attempt in range(1, MAX_APPROVAL_RETRIES + 2):
        _run_one_stage("문서생성봇", by_id, ctx, trace)

        if not approval_stage:
            return
        should_run, reason = evaluate_run_if(approval_stage.get("run_if"), ctx)
        if not should_run:
            print(f"[SKIP] 문서승인 - {reason}")
            trace.append({"stage": "문서승인", "ran": False, "reason": reason})
            return
        _run_one_stage("문서승인", by_id, ctx, trace)

        rejections = _pending_rejections(ctx)
        if not rejections:
            return

        if attempt > MAX_APPROVAL_RETRIES:
            print(f"[경고] 문서승인 반려 재시도 {MAX_APPROVAL_RETRIES}회 초과 - "
                  f"중단(mock 한계, 실제로는 대표자가 계속 처리해야 함 - open_questions 참고)")
            return

        dests_run = set()
        for doc_key, target in rejections.items():
            dest = return_to_map.get(target) if isinstance(return_to_map, dict) else return_to_map
            print(f"[반려-재작업 {attempt}/{MAX_APPROVAL_RETRIES}] {doc_key} "
                  f"rejection_target={target} -> {dest}")
            if dest and dest != "문서생성봇" and dest not in dests_run:
                _run_one_stage(dest, by_id, ctx, trace)
                dests_run.add(dest)


def _run_sequence(seq, by_id, ctx, trace):
    i = 0
    while i < len(seq):
        sid = seq[i]
        if sid == "문서생성봇" and i + 1 < len(seq) and seq[i + 1] == "문서승인":
            _run_document_approval_cycle(by_id, ctx, trace)
            i += 2
            continue
        if _run_one_stage(sid, by_id, ctx, trace) == "STOP":
            break
        i += 1


def run_pipeline(manifest, input_data, trigger_type="event"):
    stages = manifest["stages"]
    triggers = manifest.get("triggers", [])
    by_id, successors = build_graph(stages, triggers)

    trigger = next((t for t in triggers if t["type"] == trigger_type), None)
    if trigger is None:
        raise RuntimeError(f"manifest에 type={trigger_type} 트리거가 없음")
    entry_stage = trigger["entry_stage"]

    reachable_ids = reachable_from(entry_stage, successors)
    order = topo_order(reachable_ids, by_id, successors)

    ctx = {"_input": input_data}
    trace = []

    print(f"=== 방역 파이프라인 실행 (trigger={trigger_type}, entry_stage={entry_stage}) ===")
    print(f"실행 순서: {' -> '.join(order)}\n")

    if trigger_type != "schedule":
        _run_sequence(order, by_id, ctx, trace)
    else:
        reminder_idx = order.index(entry_stage)
        _run_sequence(order[:reminder_idx + 1], by_id, ctx, trace)

        remaining = order[reminder_idx + 1:]
        due_list = ctx.get("reminder_due_list") or []
        print(f"\n[스케줄 경로] 방문주기 도래/임박 고객 {len(due_list)}건 - 1건씩 순차 처리\n")

        if not remaining:
            print("[알림] entry_points로 연결된 후속 stage가 없음 - 리마인더봇에서 종료")
        elif not due_list:
            print("[알림] 방문주기가 도래/임박한 고객이 없어 후속 stage는 실행하지 않음")
        else:
            for i, due in enumerate(due_list, 1):
                print(f"--- [{i}/{len(due_list)}] {due.get('customer_name')} "
                      f"(days_until_due={due.get('days_until_due')}, overdue={due.get('is_overdue')}) 처리 시작 ---")
                ctx["customer_record"] = dict(due)
                _run_sequence(remaining, by_id, ctx, trace)
                print()

    print("=== 최종 shared_context 상태 ===")
    printable = {k: v for k, v in ctx.items() if not k.startswith("_")}
    print(json.dumps(printable, ensure_ascii=False, indent=2))

    return ctx, trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", nargs="?", default=None)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--trigger", default="event", choices=["event", "schedule"])
    args = parser.parse_args()

    default_input = DEFAULT_MOCK_INPUT if args.trigger == "event" else DEFAULT_SCHEDULE_MOCK_INPUT
    input_path = args.input_path or str(default_input)

    manifest = load_yaml(args.manifest)
    input_data = load_json(input_path)

    known_defaults = (os.path.abspath(str(DEFAULT_MOCK_INPUT)), os.path.abspath(str(DEFAULT_SCHEDULE_MOCK_INPUT)))
    if os.path.abspath(input_path) in known_defaults:
        print("[알림] 실제 골든셋이 아니라 구조 확인용 임시 가짜 데이터로 실행합니다.\n")

    ctx, trace = run_pipeline(manifest, input_data, trigger_type=args.trigger)

    ran_stages = [t["stage"] for t in trace if t.get("ran")]
    print(f"\n=== 요약 ===\n실행된 stage 수: {len(ran_stages)}\n실행된 stage: {ran_stages}")

    if "만족도수집봇" in ran_stages:
        print("\nPASS: 파이프라인이 처음부터 끝까지(만족도수집봇까지) 통과했습니다.")
    elif args.trigger == "schedule":
        print("\n참고: schedule 트리거는 방문주기가 도래한 고객이 없으면 만족도수집봇까지 "
              "안 갈 수 있음(정상) - 위 로그의 due_list 건수를 확인할 것.")
    else:
        print("\n주의: 파이프라인이 만족도수집봇까지 도달하지 못했습니다(조기 종료 또는 오류 가능).")


if __name__ == "__main__":
    main()
