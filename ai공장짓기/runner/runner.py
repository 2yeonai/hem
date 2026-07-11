#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runner.py — 범용 러너 MVP (④ AI회사 플랫폼의 실행 엔진)

근거 설계: ai공장짓기/설계노트/1_플랫폼_공통_스펙_(모든_공장이_따르는_것).md
  - 1-5 "범용 러너 MVP 범위" (2026-07-08 Fable 확정) 를 그대로 구현
  - 1-4 "공통규칙 3가지"(재실행게이트 / 반려루프 라우팅 / 검수원등급) 반영
결정사항(2026-07-10 세션로그): 러너 몸통 = 코드 + Sonnet 구현. Fable 교체 금지.

MVP 범위 (구현함):
  1. manifest.yaml 로드 + 정적 검증(문법/의존관계/순환없음/io-필드 존재/티어 검사)
  2. pipeline-type 골격만 지원 (resident는 명확한 에러로 거부)
  3. kind: local / model / human 실행
     - model: 핸들러가 있으면 핸들러(현재는 전부 mock), 없으면 MockModelProvider
       (실제 API 프로바이더는 ModelProvider 서브클래스로 교체하는 자리만 있음)
     - human: "큐에 내보내고 대기" 인터페이스 — 실제 큐 없음, 입력 JSON의
       human_decisions 또는 자동승인 스텁으로 대체
  4. 모든 stage 경계에서 io.writes 산출 검증 — 불일치시 자동수정 금지, 명확한 에러로 정지
  5. 실패 행동: "정지"와 "N회 재시도"(exec_params.retry_count) 두 가지만
  6. stage별 실행 로그(입력해시/소요시간/성공실패) → runner/logs/*.json

공통규칙 3가지 (1-4):
  ① rerun_gate — manifest가 hash_inputs 선언, 러너가 해시 비교→skip/run.
     필드 없으면 enabled: false (하위호환). 상태 저장: runner/state/
  ② on_reject — human stage의 반려 라우팅(default/by_reason/max_loops/on_exhaust).
     기존 방역 방식(on_fail.human_reject.return_to 매핑)도 하위호환으로 지원.
     명령형 루프로 처리 — depends_on 그래프에 순환을 만들지 않음(스키마 원칙).
     ※ MVP 제외 항목 유지: 실제 집행 "큐"는 없음(로그로 대체).
  3. review.risk_tier — 스키마 골격 파싱 + 로그만. 실제 T1/T2/T3 집행은 안 함
     (설계노트: "값 배정은 지금 안 함").

핸들러 모듈 계약 (공장이 제공, --handlers 로 지정):
  STAGE_FUNCS: dict[stage_id -> fn(ctx, stage) -> str]   # 필수(없는 stage는 model만 mock 대체)
  evaluate_run_if(condition, ctx) -> (bool, str)          # 선택
  pending_rejections(ctx, stage_id) -> dict[key->사유코드] # 선택(반려루프 감지용)
  should_stop(ctx, stage) -> (bool, str)                  # 선택(stop_condition 판정)
  batch_items(ctx, entry_stage) -> list[dict] | None      # 선택(묶음 순차 처리 정책)

사용법:
  python3 runner.py <manifest.yaml> [--input in.json] [--trigger event|schedule]
                    [--handlers handlers.py] [--validate-only] [--log-dir DIR]

오류가 나면: ai공장짓기/failure_log.md 형식대로 기록할 것 (하위 모델 수리용).
"""
import sys
import os
import json
import time
import hashlib
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml이 필요합니다: pip install pyyaml --break-system-packages")
    sys.exit(1)

RUNNER_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = RUNNER_DIR / "logs"
DEFAULT_STATE_DIR = RUNNER_DIR / "state"

# 티어 규범: 설계노트 1-2 — "모델명 아닌 티어명만(low_cost/mid/high), Fable 배정 절대 금지"
CANONICAL_TIERS = {"low_cost", "mid", "high"}
TIER_ALIASES = {"haiku": "low_cost", "sonnet": "mid", "opus": "high"}
FORBIDDEN_TIERS = {"fable", "fable5", "fable-5", "claude-fable-5", "mythos"}

# 플랫폼 공통 반려 사유코드 enum (1-4 ②) + 공장별 확장 허용
COMMON_REJECT_REASONS = {"형식", "내용", "예산", "제약위반"}

DEFAULT_MAX_REJECT_LOOPS = 3

# shared_context 타입 선언 ↔ 파이썬 타입 (경계 검증용, None은 항상 허용)
TYPE_MAP = {
    "string": str,
    "object": dict,
    "array": list,
    "boolean": bool,
    "number": (int, float),
    "integer": int,
}


class RunnerError(Exception):
    """러너가 던지는 모든 '명확한 에러로 정지' — 자동수정 금지 원칙."""


# ----------------------------------------------------------------------
# 로드/유틸
# ----------------------------------------------------------------------

def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def stable_hash(obj):
    """입력해시 — json 직렬화 기반, dict 키 정렬로 안정화."""
    try:
        blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        blob = repr(obj)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_handlers(path):
    """핸들러 모듈을 파일 경로로 로드 (한글/공백 경로 지원)."""
    if not path:
        return None
    p = Path(path).resolve()
    if not p.is_file():
        raise RunnerError(f"핸들러 모듈 파일을 찾을 수 없음: {p}")
    spec = importlib.util.spec_from_file_location("factory_handlers_" + stable_hash(str(p)), str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------------------
# 1. 정적 검증 (MVP 항목 1)
# ----------------------------------------------------------------------

def normalize_tier(tier):
    """티어명 정규화. (canonical, warning|None, error|None) 반환."""
    if tier is None:
        return None, None, "model stage에 tier가 없음 (low_cost/mid/high 중 하나 필요)"
    t = str(tier).strip().lower()
    if t in FORBIDDEN_TIERS:
        return None, None, f"tier '{tier}' — Fable(최상위 모델) 배정은 절대 금지 (설계노트 1-2, 2026-07-10 결정)"
    if t in CANONICAL_TIERS:
        return t, None, None
    if t in TIER_ALIASES:
        return TIER_ALIASES[t], (
            f"tier '{tier}'는 모델명 — 티어명({TIER_ALIASES[t]})으로 표기 권장(설계노트 1-2). "
            f"이번 실행에서는 {TIER_ALIASES[t]}로 해석함(manifest 자동수정은 안 함)"
        ), None
    return None, None, f"알 수 없는 tier '{tier}' (허용: low_cost/mid/high)"


def static_validate(manifest, manifest_path="<memory>"):
    """정적 검증: 문법은 load_yaml 시점에 확인됨. 여기서는 구조를 검사.
    반환: (errors, warnings). errors가 있으면 실행 금지."""
    errors, warnings = [], []

    if not isinstance(manifest, dict):
        return [f"manifest 루트가 dict가 아님: {type(manifest)}"], []

    execution = manifest.get("execution", "pipeline-type")
    if execution not in (None, "pipeline-type"):
        errors.append(f"execution '{execution}'은 MVP 범위 밖 (pipeline-type만 지원, resident는 1-5에서 명시적으로 제외)")

    stages = manifest.get("stages") or []
    shared_context = manifest.get("shared_context") or {}
    triggers = manifest.get("triggers") or []

    if not stages:
        errors.append("stages가 비어 있음")
        return errors, warnings

    # id 중복 / 존재
    stage_ids = [s.get("id") for s in stages]
    seen = set()
    for sid in stage_ids:
        if not sid:
            errors.append("id 없는 stage 존재")
        elif sid in seen:
            errors.append(f"stage id 중복: {sid}")
        seen.add(sid)
    stage_id_set = set(stage_ids)

    # kind 검사 + 티어 검사
    for s in stages:
        sid = s.get("id")
        kind = s.get("kind")
        if kind not in ("local", "model", "human", "tool", "adapter"):
            errors.append(f"stage '{sid}' kind '{kind}' 불명 (local/model/human/tool/adapter)")
        if kind == "model":
            _, warn, err = normalize_tier(s.get("tier"))
            if err:
                errors.append(f"stage '{sid}': {err}")
            if warn:
                warnings.append(f"stage '{sid}': {warn}")

    # depends_on / triggers.entry_stage / entry_points 참조 무결성
    for s in stages:
        for dep in s.get("depends_on") or []:
            if dep not in stage_id_set:
                errors.append(f"stage '{s.get('id')}' depends_on '{dep}' — 존재하지 않는 stage")
    declared_trigger_keys = {}
    for t in triggers:
        ttype = t.get("type")
        ident = t.get("source") if ttype == "event" else t.get("interval") if ttype == "schedule" else None
        if ttype and ident:
            declared_trigger_keys[f"{ttype}:{ident}"] = t.get("entry_stage")
        entry = t.get("entry_stage")
        if entry and entry not in stage_id_set:
            errors.append(f"trigger(type={ttype}) entry_stage '{entry}' — 존재하지 않는 stage")
    for s in stages:
        for ep in s.get("entry_points") or []:
            if ":" not in str(ep):
                errors.append(f"stage '{s.get('id')}' entry_points '{ep}' — 'type:식별자' 형식 아님")
            elif ep not in declared_trigger_keys:
                errors.append(f"stage '{s.get('id')}' entry_points '{ep}' — triggers에 선언 안 된 트리거")

    # io 필드가 shared_context에 존재하는지
    ctx_fields = set(shared_context.keys())
    for s in stages:
        io = s.get("io") or {}
        for field in io.get("reads") or []:
            if field not in ctx_fields:
                errors.append(f"stage '{s.get('id')}' io.reads '{field}' — shared_context에 없음")
        for field in io.get("writes") or []:
            if field not in ctx_fields:
                errors.append(f"stage '{s.get('id')}' io.writes '{field}' — shared_context에 없음")

    # 순환 없음 (전체 그래프 위상정렬)
    try:
        by_id, successors = build_graph(stages, triggers)
        topo_order(list(stage_id_set), by_id, successors)
    except RunnerError as e:
        errors.append(str(e))

    # 인접 stage 스키마 호환(약식): 각 read 필드에 대해, 조상 중 그 필드를 쓰는
    # stage가 하나라도 있는지 확인. 없으면 경고(트리거 입력으로 채워질 수 있어 FAIL 아님).
    writers_of = {}
    for s in stages:
        for field in (s.get("io") or {}).get("writes") or []:
            writers_of.setdefault(field, set()).add(s.get("id"))
    ancestors = compute_ancestors(stages)
    for s in stages:
        sid = s.get("id")
        for field in (s.get("io") or {}).get("reads") or []:
            ws = writers_of.get(field, set())
            if ws and not (ws & ancestors.get(sid, set())):
                warnings.append(f"stage '{sid}'가 읽는 '{field}'를 조상 stage가 쓰지 않음(다른 경로/트리거 입력 가능성 — 확인 필요)")

    # rerun_gate 골격 검사 (①)
    rg = manifest.get("rerun_gate")
    if rg is not None:
        if not isinstance(rg, dict):
            errors.append("rerun_gate는 object여야 함")
        else:
            if rg.get("enabled") and not rg.get("hash_inputs"):
                errors.append("rerun_gate.enabled=true인데 hash_inputs 선언이 없음(무엇을 해시할지는 공장이 선언)")
            if rg.get("scope") not in (None, "full", "from_stage"):
                errors.append(f"rerun_gate.scope '{rg.get('scope')}' 불명 (full|from_stage)")

    # on_reject / review 골격 검사 (② ③)
    for s in stages:
        orj = s.get("on_reject")
        if orj is not None:
            if s.get("kind") != "human":
                warnings.append(f"stage '{s.get('id')}'에 on_reject가 있으나 kind가 human이 아님")
            for dest in list((orj.get("by_reason") or {}).values()) + ([orj.get("default")] if orj.get("default") else []):
                if dest and dest not in stage_id_set:
                    errors.append(f"stage '{s.get('id')}' on_reject 목적지 '{dest}' — 존재하지 않는 stage")
            for reason in (orj.get("by_reason") or {}):
                if reason not in COMMON_REJECT_REASONS:
                    warnings.append(f"stage '{s.get('id')}' on_reject 사유 '{reason}' — 공통 enum(형식/내용/예산/제약위반) 밖(공장별 확장으로 간주)")
            if orj.get("on_exhaust") not in (None, "escalate_human", "fail_with_report"):
                errors.append(f"stage '{s.get('id')}' on_exhaust '{orj.get('on_exhaust')}' 불명")
        # 하위호환: on_fail.human_reject.return_to 매핑의 목적지 검사
        rt = ((s.get("on_fail") or {}).get("human_reject") or {}).get("return_to")
        if isinstance(rt, dict):
            for dest in rt.values():
                if dest and dest not in stage_id_set:
                    errors.append(f"stage '{s.get('id')}' return_to 목적지 '{dest}' — 존재하지 않는 stage")
        rv = s.get("review")
        if rv is not None:
            if rv.get("risk_tier") not in (None, "T1", "T2", "T3"):
                errors.append(f"stage '{s.get('id')}' review.risk_tier '{rv.get('risk_tier')}' 불명 (T1|T2|T3)")
            if rv.get("reviewer_grade") not in (None, "senior", "standard", "any"):
                errors.append(f"stage '{s.get('id')}' review.reviewer_grade '{rv.get('reviewer_grade')}' 불명")

    return errors, warnings


# ----------------------------------------------------------------------
# 그래프 (방역 run.py의 검증된 로직을 범용화 — entry_points 반영)
# ----------------------------------------------------------------------

def build_graph(stages, triggers=None):
    by_id = {s["id"]: s for s in stages}
    successors = {s["id"]: [] for s in stages}
    for s in stages:
        for dep in s.get("depends_on") or []:
            successors.setdefault(dep, []).append(s["id"])
    if triggers:
        trigger_entry_by_key = {}
        for t in triggers:
            ttype = t.get("type")
            ident = t.get("source") if ttype == "event" else t.get("interval") if ttype == "schedule" else None
            if ttype and ident:
                trigger_entry_by_key[f"{ttype}:{ident}"] = t.get("entry_stage")
        for s in stages:
            for ep in s.get("entry_points") or []:
                origin = trigger_entry_by_key.get(ep)
                if not origin or origin == s["id"]:
                    continue
                successors.setdefault(origin, [])
                if s["id"] not in successors[origin]:
                    successors[origin].append(s["id"])
    return by_id, successors


def compute_ancestors(stages):
    """depends_on 기준 조상 집합(간접 포함)."""
    parents = {s["id"]: list(s.get("depends_on") or []) for s in stages}
    ancestors = {}

    def walk(sid, seen):
        for p in parents.get(sid, []):
            if p not in seen:
                seen.add(p)
                walk(p, seen)
        return seen

    for sid in parents:
        ancestors[sid] = walk(sid, set())
    return ancestors


def reachable_from(entry_id, successors):
    seen, queue, order = set(), [entry_id], []
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
    queue = sorted([sid for sid in stage_ids if indeg[sid] == 0])
    order = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in edges[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(stage_ids):
        raise RunnerError(f"위상정렬 실패 — 순환 의존성 의심: {stage_id_set - set(order)}")
    return order


# ----------------------------------------------------------------------
# 3. kind별 실행 (MVP 항목 3)
# ----------------------------------------------------------------------

class ModelProvider:
    """model stage 호출 인터페이스. 실제 API 연동 시 이 클래스를 상속해 교체.
    MVP: MockModelProvider만 존재 (볼트 원칙: 아직 어떤 스킬도 실제 LLM 호출 안 함)."""

    def call(self, stage, tier, ctx, shared_context):
        raise NotImplementedError


class MockModelProvider(ModelProvider):
    """io.writes에 선언된 필드를 shared_context 타입에 맞는 mock 값으로 채움."""

    MOCK_BY_TYPE = {"string": "[mock:{tier}] {sid} 출력", "object": {}, "array": [],
                    "boolean": False, "number": 0, "integer": 0}

    def call(self, stage, tier, ctx, shared_context):
        sid = stage["id"]
        for field in (stage.get("io") or {}).get("writes") or []:
            ftype = (shared_context.get(field) or {}).get("type", "string")
            template = self.MOCK_BY_TYPE.get(ftype, None)
            if isinstance(template, str):
                ctx[field] = template.format(tier=tier, sid=sid)
            elif template is not None:
                ctx[field] = type(template)()  # 새 빈 객체
            else:
                ctx[field] = None
        return f"[MockModelProvider] tier={tier} — 실제 API 호출 없음, writes {len((stage.get('io') or {}).get('writes') or [])}개 필드 mock 생성"


def default_human_stub(ctx, stage, input_data):
    """human stage 스텁 (MVP 항목: '큐에 내보내고 대기' 인터페이스만).
    입력 JSON의 human_decisions[stage_id]가 있으면 그 값 사용, 없으면 자동승인.
    값 형식: "승인" | "반려:<사유코드>" | 리스트(재시도마다 순차 소비)"""
    sid = stage["id"]
    decisions = (input_data or {}).get("human_decisions") or {}
    raw = decisions.get(sid, "승인")
    key = f"_human_call_count_{sid}"
    idx = ctx.get(key, 0)
    ctx[key] = idx + 1
    if isinstance(raw, list):
        raw = raw[min(idx, len(raw) - 1)] if raw else "승인"
    ctx[f"_human_decision_{sid}"] = raw
    return f"[HUMAN-QUEUE 스텁] '{sid}' 검수 요청을 큐에 내보냄 → 결정: {raw} (실제 큐 없음, 수동승인 스텁)"


# ----------------------------------------------------------------------
# 4. 경계 검증 (MVP 항목 4) — 자동수정 금지, 명확한 에러로 정지
# ----------------------------------------------------------------------

def boundary_check(stage, ctx, shared_context):
    sid = stage["id"]
    problems = []
    for field in (stage.get("io") or {}).get("writes") or []:
        if field not in ctx:
            problems.append(f"선언한 io.writes '{field}'가 실행 후 shared_context에 없음")
            continue
        val = ctx[field]
        if val is None:
            continue  # None(아직 값 없음)은 허용 — 방역 mock 관례
        declared = (shared_context.get(field) or {}).get("type")
        pytype = TYPE_MAP.get(declared)
        if pytype and not isinstance(val, pytype):
            problems.append(
                f"'{field}' 타입 불일치: 선언={declared}, 실제={type(val).__name__} (자동수정 금지 — 공장 쪽 수정 필요)")
    if problems:
        raise RunnerError(f"[경계검증 실패] stage '{sid}': " + " / ".join(problems))


# ----------------------------------------------------------------------
# 공통규칙 ① 재실행 게이트
# ----------------------------------------------------------------------

def rerun_gate_check(manifest, input_data, ctx, state_dir, skill_name):
    """반환: (skip 여부, 사유, 새 해시). 러너가 해시 비교, 무엇을 해시할지는 공장이 선언."""
    rg = manifest.get("rerun_gate") or {}
    if not rg.get("enabled"):
        return False, "rerun_gate 없음/비활성 — 항상 실행(하위호환)", None
    material = {}
    for key in rg.get("hash_inputs") or []:
        if key == "user_input":
            material[key] = input_data
        else:
            material[key] = ctx.get(key, input_data.get(key) if isinstance(input_data, dict) else None)
    new_hash = stable_hash(material)
    state_file = Path(state_dir) / f"rerun_gate_{skill_name}.json"
    old_hash = None
    if state_file.is_file():
        try:
            old_hash = load_json(state_file).get("hash")
        except (json.JSONDecodeError, OSError):
            old_hash = None
    if old_hash == new_hash:
        return True, f"입력 해시 동일({new_hash}) — scope={rg.get('scope', 'full')} 스킵", new_hash
    return False, f"입력 해시 변경({old_hash} → {new_hash}) — 실행", new_hash


def rerun_gate_save(state_dir, skill_name, new_hash):
    if new_hash is None:
        return
    state_file = Path(state_dir) / f"rerun_gate_{skill_name}.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"hash": new_hash, "saved_at": datetime.now().isoformat()}, f, ensure_ascii=False)


# ----------------------------------------------------------------------
# 러너 본체
# ----------------------------------------------------------------------

class Runner:
    def __init__(self, manifest, handlers=None, model_provider=None,
                 log_dir=DEFAULT_LOG_DIR, state_dir=DEFAULT_STATE_DIR):
        self.manifest = manifest
        self.handlers = handlers
        self.provider = model_provider or MockModelProvider()
        self.log_dir = Path(log_dir)
        self.state_dir = Path(state_dir)
        self.shared_context_spec = manifest.get("shared_context") or {}
        self.stages = manifest.get("stages") or []
        self.triggers = manifest.get("triggers") or []
        self.by_id, self.successors = build_graph(self.stages, self.triggers)
        self.ancestors = compute_ancestors(self.stages)
        self.log_entries = []
        self.skill_name = manifest.get("skill_name") or manifest.get("domain") or "unknown_skill"

    # --- 핸들러 훅 ---
    def _hook(self, name):
        return getattr(self.handlers, name, None) if self.handlers else None

    def _eval_run_if(self, condition, ctx):
        fn = self._hook("evaluate_run_if")
        if fn:
            return fn(condition, ctx)
        if condition is None:
            return True, "run_if 없음 — 항상 실행"
        return False, f"run_if '{condition}' 판정 핸들러 없음 — 안전하게 건너뜀(기본 False)"

    def _pending_rejections(self, ctx, sid):
        fn = self._hook("pending_rejections")
        if fn:
            return fn(ctx, sid) or {}
        # 기본: human 스텁 결정이 "반려:사유" 형식이면 감지
        raw = ctx.get(f"_human_decision_{sid}")
        if isinstance(raw, str) and raw.startswith("반려"):
            reason = raw.split(":", 1)[1] if ":" in raw else "내용"
            return {sid: reason}
        return {}

    def _should_stop(self, ctx, stage):
        fn = self._hook("should_stop")
        if fn:
            return fn(ctx, stage)
        return False, ""

    # --- stage 1개 실행 (재시도 포함, MVP 항목 5·6) ---
    def run_stage(self, sid, ctx, input_data):
        stage = self.by_id[sid]
        should_run, reason = self._eval_run_if(stage.get("run_if"), ctx)
        if not should_run:
            self._log(sid, stage, ran=False, status="SKIP", detail=reason, input_hash=None, dur_ms=0)
            print(f"[SKIP] {sid} — {reason}")
            return "SKIP"

        # 검수원등급(③) — 파싱+로그만, 집행 없음
        rv = stage.get("review")
        if rv:
            print(f"[REVIEW-META] {sid}: risk_tier={rv.get('risk_tier')} grade={rv.get('reviewer_grade')} "
                  f"sla={rv.get('sla_hours')}h priority={rv.get('queue_priority')} (MVP: 로그만, 집행 안 함)")

        reads = (stage.get("io") or {}).get("reads") or []
        input_hash = stable_hash({k: ctx.get(k) for k in reads} if reads else input_data)
        retries = int((stage.get("exec_params") or {}).get("retry_count") or 0)

        attempt = 0
        while True:
            attempt += 1
            t0 = time.monotonic()
            try:
                detail = self._dispatch(sid, stage, ctx, input_data)
                boundary_check(stage, ctx, self.shared_context_spec)
                dur = int((time.monotonic() - t0) * 1000)
                self._log(sid, stage, ran=True, status="OK", detail=detail, input_hash=input_hash, dur_ms=dur, attempt=attempt)
                print(f"[RUN]  {sid} — {detail}")
                break
            except RunnerError:
                raise  # 경계검증 실패는 재시도 대상 아님 — 즉시 정지(자동수정 금지)
            except Exception as e:  # 핸들러 내부 오류 → N회 재시도 후 정지
                dur = int((time.monotonic() - t0) * 1000)
                self._log(sid, stage, ran=True, status="FAIL", detail=f"{type(e).__name__}: {e}", input_hash=input_hash, dur_ms=dur, attempt=attempt)
                if attempt > retries:
                    raise RunnerError(f"[정지] stage '{sid}' 실패 {attempt}회(재시도 한도 {retries}) — {type(e).__name__}: {e}") from e
                print(f"[RETRY] {sid} — {attempt}/{retries + 1}회 실패, 재시도: {e}")

        stop, stop_reason = self._should_stop(ctx, stage)
        if stop:
            print(f"[STOP] {sid} — {stop_reason}")
            self._log(sid, stage, ran=False, status="STOP", detail=stop_reason, input_hash=None, dur_ms=0)
            return "STOP"
        return "OK"

    def _dispatch(self, sid, stage, ctx, input_data):
        kind = stage.get("kind")
        funcs = getattr(self.handlers, "STAGE_FUNCS", {}) if self.handlers else {}
        fn = funcs.get(sid)
        if kind in ("local", "tool", "adapter"):
            if fn is None:
                raise RunnerError(f"kind={kind} stage '{sid}'의 핸들러(STAGE_FUNCS)가 없음 — local은 결정적 코드가 반드시 필요")
            return fn(ctx, stage)
        if kind == "model":
            tier, _, err = normalize_tier(stage.get("tier"))
            if err:
                raise RunnerError(f"stage '{sid}': {err}")
            if fn is not None:
                return fn(ctx, stage)  # 현재는 전부 mock 핸들러
            return self.provider.call(stage, tier, ctx, self.shared_context_spec)
        if kind == "human":
            if fn is not None:
                return fn(ctx, stage)
            return default_human_stub(ctx, stage, input_data)
        raise RunnerError(f"stage '{sid}' kind '{kind}' 실행 불가")

    # --- 공통규칙 ② 반려루프 (명령형, DAG에 순환 없음) ---
    def _reject_config(self, stage):
        orj = stage.get("on_reject")
        if orj:
            return {
                "default": orj.get("default"),
                "by_reason": orj.get("by_reason") or {},
                "max_loops": int(orj.get("max_loops") or DEFAULT_MAX_REJECT_LOOPS),
                "on_exhaust": orj.get("on_exhaust") or "escalate_human",
            }
        rt = ((stage.get("on_fail") or {}).get("human_reject") or {}).get("return_to")
        if rt:
            if isinstance(rt, dict):
                return {"default": None, "by_reason": rt, "max_loops": DEFAULT_MAX_REJECT_LOOPS, "on_exhaust": "escalate_human"}
            return {"default": rt, "by_reason": {}, "max_loops": DEFAULT_MAX_REJECT_LOOPS, "on_exhaust": "escalate_human"}
        return None

    def _rework_path(self, dest, human_sid, order):
        """dest부터 human stage까지, human의 조상인 stage만 골라 재실행 경로 구성."""
        if dest not in order:
            return [dest]
        anc = self.ancestors.get(human_sid, set())
        i, j = order.index(dest), order.index(human_sid)
        return [sid for sid in order[i:j] if sid == dest or sid in anc]

    def run_human_with_reject_loop(self, human_sid, ctx, input_data, order):
        stage = self.by_id[human_sid]
        cfg = self._reject_config(stage)
        result = self.run_stage(human_sid, ctx, input_data)
        if result in ("SKIP", "STOP") or cfg is None:
            return result
        loops = 0
        while True:
            rejections = self._pending_rejections(ctx, human_sid)
            if not rejections:
                return "OK"
            loops += 1
            if loops > cfg["max_loops"]:
                msg = (f"반려 루프 {cfg['max_loops']}회 소진 — on_exhaust={cfg['on_exhaust']}")
                if cfg["on_exhaust"] == "fail_with_report":
                    raise RunnerError(f"[정지] stage '{human_sid}': {msg}")
                print(f"[ESCALATE] {human_sid} — {msg}: 사람 개입 필요 상태로 종료(실제 에스컬레이션 큐는 MVP 제외)")
                self._log(human_sid, stage, ran=False, status="ESCALATED", detail=msg, input_hash=None, dur_ms=0)
                return "ESCALATED"
            dests_run = set()
            for key, reason in rejections.items():
                dest = cfg["by_reason"].get(reason) or cfg["default"]
                print(f"[반려-재작업 {loops}/{cfg['max_loops']}] {key}: 사유='{reason}' → {dest}")
                if not dest:
                    raise RunnerError(f"[정지] stage '{human_sid}': 사유 '{reason}'의 라우팅 목적지 없음(on_reject.default도 없음)")
                for sid in self._rework_path(dest, human_sid, order):
                    if sid not in dests_run:
                        self.run_stage(sid, ctx, input_data)
                        dests_run.add(sid)
            self.run_stage(human_sid, ctx, input_data)

    # --- 파이프라인 실행 ---
    def run(self, input_data, trigger_type="event"):
        trigger = next((t for t in self.triggers if t.get("type") == trigger_type), None)
        if trigger is None:
            raise RunnerError(f"manifest에 type={trigger_type} 트리거가 없음")
        entry_stage = trigger["entry_stage"]
        order = topo_order(reachable_from(entry_stage, self.successors), self.by_id, self.successors)

        ctx = {"_input": input_data}
        skip, reason, new_hash = rerun_gate_check(self.manifest, input_data, ctx, self.state_dir, self.skill_name)
        print(f"[재실행게이트] {reason}")
        if skip:
            self._log("__rerun_gate__", {"id": "__rerun_gate__"}, ran=False, status="SKIP_ALL", detail=reason, input_hash=new_hash, dur_ms=0)
            self._flush_log(trigger_type)
            return ctx, self.log_entries

        print(f"=== 범용 러너 실행: skill={self.skill_name} trigger={trigger_type} entry={entry_stage} ===")
        print(f"실행 순서: {' -> '.join(order)}\n")

        batch_fn = self._hook("batch_items")
        entry_idx = order.index(entry_stage)

        # 진입 stage까지 실행
        head, tail = order[:entry_idx + 1], order[entry_idx + 1:]
        stopped = self._run_sequence(head, ctx, input_data, order)

        if not stopped and tail:
            items = batch_fn(ctx, entry_stage) if batch_fn else None
            if items is None:
                self._run_sequence(tail, ctx, input_data, order)
            else:
                # 묶음 순차 처리 정책(schema v2 §5 재사용): 1건씩 끝까지
                print(f"\n[묶음 순차 처리] {len(items)}건 — 1건씩 끝까지 처리\n")
                for i, item in enumerate(items, 1):
                    print(f"--- [{i}/{len(items)}] 처리 시작 ---")
                    ctx.update(item)
                    self._run_sequence(tail, ctx, input_data, order)
                    print()

        rerun_gate_save(self.state_dir, self.skill_name, new_hash)
        self._flush_log(trigger_type)
        return ctx, self.log_entries

    def _run_sequence(self, seq, ctx, input_data, order):
        for sid in seq:
            stage = self.by_id[sid]
            if stage.get("kind") == "human" and self._reject_config(stage):
                result = self.run_human_with_reject_loop(sid, ctx, input_data, order)
            else:
                result = self.run_stage(sid, ctx, input_data)
            if result in ("STOP", "ESCALATED"):
                # ESCALATED: 반려 루프 소진 — 사람 개입 전까지 후속 stage 진행 금지
                return True
        return False

    # --- 로그 (MVP 항목 6: 입력해시/소요시간/성공실패) ---
    def _log(self, sid, stage, ran, status, detail, input_hash, dur_ms, attempt=1):
        self.log_entries.append({
            "stage": sid, "kind": stage.get("kind"), "ran": ran, "status": status,
            "attempt": attempt, "input_hash": input_hash, "duration_ms": dur_ms,
            "detail": str(detail)[:500], "at": datetime.now().isoformat(),
        })

    def _flush_log(self, trigger_type):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        fname = self.log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.skill_name}_{trigger_type}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({"skill": self.skill_name, "trigger": trigger_type,
                       "entries": self.log_entries}, f, ensure_ascii=False, indent=1)
        print(f"\n[로그 저장] {fname}")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="범용 러너 MVP")
    parser.add_argument("manifest_path")
    parser.add_argument("--input", dest="input_path", default=None)
    parser.add_argument("--trigger", default="event", choices=["event", "schedule"])
    parser.add_argument("--handlers", default=None, help="핸들러 모듈(.py) 경로")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    args = parser.parse_args()

    manifest = load_yaml(args.manifest_path)
    errors, warnings = static_validate(manifest, args.manifest_path)
    print(f"[정적검증] FAIL {len(errors)}건 / WARN {len(warnings)}건")
    for w in warnings:
        print("  [WARN]", w)
    for e in errors:
        print("  [FAIL]", e)
    if errors:
        print("결과: FAIL — 실행하지 않음(자동수정 금지 원칙)")
        sys.exit(1)
    if args.validate_only:
        print("결과: PASS (--validate-only)")
        sys.exit(0)

    handlers = load_handlers(args.handlers) if args.handlers else None
    input_data = load_json(args.input_path) if args.input_path else {}

    runner = Runner(manifest, handlers=handlers, log_dir=args.log_dir, state_dir=args.state_dir)
    try:
        ctx, entries = runner.run(input_data, trigger_type=args.trigger)
    except RunnerError as e:
        print(f"\n[러너 정지] {e}")
        runner._flush_log(args.trigger)
        sys.exit(2)

    ran = [e["stage"] for e in entries if e.get("ran") and e.get("status") == "OK"]
    print(f"\n=== 요약 === 실행 OK stage 수: {len(ran)}\n{ran}")


if __name__ == "__main__":
    main()
