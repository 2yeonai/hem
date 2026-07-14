#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kids-story-ost-factory / scripts/run.py  (manifest v2, schema: ai공장짓기/manifest.schema.v2.yaml)

"옛날옛적에" AI 키즈 동화·동요 공장의 실행 뼈대(skeleton). 방역/정부지원사업
run.py와 같은 성격의 mock 스텁 실행기 — 실제 AI 모델(동화 창작/작사/TTS)은
전혀 호출하지 않고, manifest.yaml의 stages/triggers/run_if를 그대로 읽어
"구조가 처음부터 끝까지 한 번 통과되는지"만 확인한다.

이 스캐폴드가 반영하는 결정 3건(ai공장짓기/decision-log_skill-factory-
architecture.md §9, 2026-07-14 혜미 회신):
  ① OST/노래 기능은 MVP에 포함 확정 — OST생성봇이 run_if로 켜고 끌 수는
     있게 자리를 두되 기본은 항상 실행.
  ② 입력은 "아이 자유입력"이 아니라 "보호자가 아이 발화를 대신 입력" —
     발화수집봇의 입력 필드명이 이를 반영. 최소 수준 안전필터(안전선별봇)는
     입력 주체와 무관하게 유지.
  ③ 실존 IP 캐릭터명은 테스트 단계라 허용 — 캐릭터_IP_점검봇은 지금
     차단하지 않고 배포 게이트용 플래그(deployment_gate_required)만 기록.

사용법:
  python3 run.py [입력 JSON 경로] [--manifest <manifest.yaml 경로>] [--trigger event]

기본 입력 JSON 경로는 test/sample_input.json.
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml이 필요합니다: pip install pyyaml --break-system-packages")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_MANIFEST = ROOT_DIR / "manifest.yaml"
DEFAULT_INPUT = ROOT_DIR / "test" / "sample_input.json"

# [§9 해소③ 반영] mock용 실존 IP 캐릭터 감지 사전 — 실제 서비스용 정식
# 목록이 아니라 "구조가 동작하는지" 확인용 예시일 뿐. 실제 배포 게이트
# 심사 시점에는 정식 목록/절차가 필요(manifest.yaml open_questions 참고).
KNOWN_IP_CHARACTERS_MOCK = ["뽀로로", "핑크퐁", "타요", "미키마우스", "엘사"]

# 최소 수준 부적절 표현 필터 mock 사전 [§9 해소② 반영]
FLAGGED_TERMS_MOCK = ["폭력", "무기", "욕설"]


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def build_graph(stages):
    by_id = {s["id"]: s for s in stages}
    successors = {s["id"]: [] for s in stages}
    for s in stages:
        for dep in s.get("depends_on", []) or []:
            successors.setdefault(dep, []).append(s["id"])
    return by_id, successors


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
    if condition == "OST_포함이_요청됨":
        sr = ctx.get("structured_request") or {}
        included = sr.get("ost_included", True)  # 기본값 true (§9 해소①)
        return bool(included), f"structured_request.ost_included={included}"
    return False, f"알 수 없는 run_if 조건 '{condition}' - 안전하게 기본값 False(건너뜀) 처리"


# ---------------------------------------------------------------------
# stage별 목업(mock) 실행 함수 - 전부 실제 모델 호출 없는 스텁
# ---------------------------------------------------------------------

def run_발화수집봇(ctx, stage):
    inp = ctx["_input"]
    ctx["request_meta"] = {
        "requested_at": inp.get("requested_at", _now_iso()),
        "input_channel": inp.get("input_channel", "manual"),
    }
    # [§9 해소② 반영] 이 값은 항상 "보호자가 아이 발화를 대신 입력한 원문"이다.
    ctx["child_utterance_raw"] = inp.get("child_utterance_raw", "")
    return f"child_utterance_raw={ctx['child_utterance_raw']!r} (보호자 입력, §9 해소② 반영)"


def run_입력정리봇(ctx, stage):
    inp = ctx["_input"]
    # mock: 실제 LLM 구조화 대신, 테스트 입력에 이미 옵션이 있으면 그대로 사용
    options = inp.get("requested_options", {})
    ctx["structured_request"] = {
        "requested_characters": options.get("requested_characters", []),
        "theme": options.get("theme", "미정"),
        "child_name": options.get("child_name", ""),
        "child_age": options.get("child_age"),
        "tone": options.get("tone", "따뜻한"),
        "ost_included": options.get("ost_included", True),  # 기본 true (§9 해소①)
    }
    return f"structured_request={ctx['structured_request']} (mock 구조화, 실제 LLM 호출 없음)"


def run_안전선별봇(ctx, stage):
    text = ctx.get("child_utterance_raw", "")
    flagged = [t for t in FLAGGED_TERMS_MOCK if t in text]
    ctx["safety_check_result"] = {
        "pass": len(flagged) == 0,
        "flagged_terms": flagged,
        "reason": "감지된 부적절 표현 없음" if not flagged else f"부적절 표현 감지: {flagged}",
    }
    return f"safety_check_result={ctx['safety_check_result']} (§9 해소②: 입력주체 무관 최소필터 유지)"


def run_캐릭터_IP_점검봇(ctx, stage):
    requested = (ctx.get("structured_request") or {}).get("requested_characters", [])
    detected = [c for c in requested if c in KNOWN_IP_CHARACTERS_MOCK]
    ctx["ip_flag"] = {
        "detected_characters": detected,
        "deployment_gate_required": len(detected) > 0,
    }
    note = "실존 IP 감지되었으나 테스트 단계라 통과(§9 해소③)" if detected else "실존 IP 미감지"
    return f"ip_flag={ctx['ip_flag']} ({note})"


def run_동화생성봇(ctx, stage):
    sr = ctx.get("structured_request") or {}
    characters = sr.get("requested_characters") or ["이름 없는 주인공"]
    theme = sr.get("theme", "미정")
    title = f"{'/'.join(characters)}의 {theme} 이야기 (mock 제목)"
    body = (
        f"[mock 동화 본문 - 실제 LLM 미호출] 옛날 옛적에 {', '.join(characters)}가(이) "
        f"'{theme}'에 관한 이야기를 시작했습니다... (여기에 실제 생성 본문이 들어갈 자리)"
    )
    ctx["story_draft"] = {"title": title, "body": body, "characters_used": characters}
    return f"story_draft.title={title!r} (mock, 실제 창작 없음)"


def run_OST생성봇(ctx, stage):
    story = ctx.get("story_draft") or {}
    ctx["ost_draft"] = {
        "lyrics": f"[mock 가사 - 실제 작곡/LLM 미호출] {story.get('title', '')}를 위한 노래 가사 자리",
        "style_note": "잔잔하고 따뜻한 동요풍 (mock 스타일노트)",
    }
    return f"ost_draft 생성됨 (mock, run_if 조건 통과 - §9 해소①: OST 기본 포함)"


def run_보호자검수(ctx, stage):
    # mock: 테스트 입력에 review_decision이 있으면 그걸 쓰고, 없으면 자동 승인
    inp = ctx["_input"]
    decision = inp.get("review_decision", {"pass": True, "reviewer": "mock-보호자", "reason": "mock 자동승인"})
    ctx["review_result"] = decision
    return f"review_result={decision} (mock — 실제 서비스에서는 사람이 직접 승인/반려)"


def run_산출물포맷봇(ctx, stage):
    ctx["final_package"] = {
        "story": ctx.get("story_draft"),
        "ost": ctx.get("ost_draft"),
        "deployment_gate_required": (ctx.get("ip_flag") or {}).get("deployment_gate_required", False),
        "generated_at": _now_iso(),
    }
    return "final_package 조립 완료"


STAGE_FUNCS = {
    "발화수집봇": run_발화수집봇,
    "입력정리봇": run_입력정리봇,
    "안전선별봇": run_안전선별봇,
    "캐릭터_IP_점검봇": run_캐릭터_IP_점검봇,
    "동화생성봇": run_동화생성봇,
    "OST생성봇": run_OST생성봇,
    "보호자검수": run_보호자검수,
    "산출물포맷봇": run_산출물포맷봇,
}


def _run_one_stage(sid, by_id, ctx, trace):
    stage = by_id[sid]
    run_if = stage.get("run_if")
    ok, reason = evaluate_run_if(run_if, ctx)
    if not ok:
        print(f"[SKIP] {sid} - run_if 조건 불충족: {reason}")
        trace.append({"stage": sid, "ran": False, "reason": reason})
        return None

    func = STAGE_FUNCS.get(sid)
    if func is None:
        print(f"[경고] {sid} - mock 실행 함수가 정의되지 않음(스킵)")
        trace.append({"stage": sid, "ran": False, "reason": "mock 함수 없음"})
        return None

    result = func(ctx, stage)
    print(f"[RUN]  {sid} ({stage.get('kind')}) -> {result}")
    trace.append({"stage": sid, "ran": True, "result": result})

    if stage.get("kind") == "human":
        review = ctx.get("review_result") or {}
        if review.get("pass") is False:
            return_to = ((stage.get("on_fail") or {}).get("human_reject") or {}).get("return_to")
            print(f"[REJECT] {sid} - 반려됨 (사유: {review.get('reason')}) -> 복귀: {return_to}")
    return None


def run_pipeline(manifest, input_data, trigger_type="event"):
    stages = manifest["stages"]
    triggers = manifest.get("triggers", [])
    by_id, successors = build_graph(stages)

    trigger = next((t for t in triggers if t["type"] == trigger_type), None)
    if trigger is None:
        raise RuntimeError(f"manifest에 type={trigger_type} 트리거가 없음")

    all_ids = [s["id"] for s in stages]
    order = topo_order(all_ids, by_id, successors)

    ctx = {"_input": input_data}
    trace = []

    print(f"=== 옛날옛적에 파이프라인 실행 (trigger={trigger_type}, entry_stage={trigger['entry_stage']}) ===")
    print(f"실행 순서: {' -> '.join(order)}\n")

    for sid in order:
        _run_one_stage(sid, by_id, ctx, trace)

    print("\n=== 최종 shared_context 상태 ===")
    printable = {k: v for k, v in ctx.items() if not k.startswith("_")}
    print(json.dumps(printable, ensure_ascii=False, indent=2))

    return ctx, trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", nargs="?", default=None)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--trigger", default="event", choices=["event"])
    args = parser.parse_args()

    input_path = args.input_path or str(DEFAULT_INPUT)

    manifest = load_yaml(args.manifest)
    input_data = load_json(input_path)

    if os.path.abspath(input_path) == os.path.abspath(str(DEFAULT_INPUT)):
        print("[알림] 실제 사용 데이터가 아니라 구조 확인용 샘플 입력으로 실행합니다.\n")

    ctx, trace = run_pipeline(manifest, input_data, trigger_type=args.trigger)

    ran_stages = [t["stage"] for t in trace if t.get("ran")]
    print(f"\n=== 요약 ===\n실행된 stage 수: {len(ran_stages)}\n실행된 stage: {ran_stages}")

    if "산출물포맷봇" in ran_stages:
        print("\nPASS: 파이프라인이 처음부터 끝까지(산출물포맷봇까지) 통과했습니다.")
    else:
        print("\n주의: 파이프라인이 산출물포맷봇까지 도달하지 못했습니다(조기 종료 또는 오류 가능).")


if __name__ == "__main__":
    main()
