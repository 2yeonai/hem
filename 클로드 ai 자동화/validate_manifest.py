#!/usr/bin/env python3
"""
manifest.yaml 검증 스크립트 (외부 라이브러리 최소화 버전)

비개발자용 사용법:
  python3 validate_manifest.py manifest.yaml

필요한 것: pyyaml 만 있으면 됨 (보통 기본 설치되어 있음).
설치 안 돼 있으면 Claude에게: "pip install pyyaml --break-system-packages 실행해줘"

이 스크립트는 아무것도 수정하지 않습니다. 읽기 전용 검사입니다.
"""

import sys
import json
import re
import os

try:
    import yaml
except ImportError:
    print("❌ pyyaml이 설치되어 있지 않습니다.")
    print("   Claude에게 이렇게 말하세요: 'pip install pyyaml --break-system-packages 실행해줘'")
    sys.exit(1)


ALLOWED_TIERS = {"low_cost", "mid", "high", "escalation"}
FORBIDDEN_MODEL_PATTERNS = [
    r"claude-fable", r"claude-sonnet", r"claude-opus", r"claude-haiku",
    r"gpt-\d", r"gemini-"
]


def err(problems, msg):
    problems.append(msg)


def check_top_level_required(m, problems):
    required = ["name", "version", "io_contract", "model_routing", "quality_gate", "invocation"]
    for key in required:
        if key not in m:
            err(problems, f"필수 항목 누락: '{key}'가 없습니다.")


def check_version(m, problems):
    v = m.get("version")
    if v and not re.match(r"^\d+\.\d+\.\d+$", str(v)):
        err(problems, f"version 형식이 잘못됨: '{v}' (예: 0.1.0 형식이어야 함)")


def check_io_contract(m, problems):
    io = m.get("io_contract")
    if io is None:
        return
    if "input_schema" not in io:
        err(problems, "io_contract.input_schema가 없습니다.")
    if "output_schema" not in io:
        err(problems, "io_contract.output_schema가 없습니다.")


def check_model_routing(m, problems):
    routing = m.get("model_routing")
    if routing is None:
        return
    stages = routing.get("stages")
    if not stages:
        err(problems, "model_routing.stages가 비어있거나 없습니다.")
        return
    for i, stage in enumerate(stages):
        tier = stage.get("tier")
        if tier not in ALLOWED_TIERS:
            err(problems, f"model_routing.stages[{i}].tier='{tier}'는 허용되지 않음. "
                           f"{sorted(ALLOWED_TIERS)} 중 하나여야 함.")
        step = stage.get("step")
        if not step:
            err(problems, f"model_routing.stages[{i}]에 'step' 설명이 없습니다.")

    # stop_rule #1: 실제 모델명 하드코딩 금지
    text = json.dumps(routing, ensure_ascii=False)
    for pat in FORBIDDEN_MODEL_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            err(problems, f"model_routing 안에 실제 모델명('{pat}' 패턴)이 하드코딩되어 있습니다. "
                           f"티어 이름만 쓰세요 (low_cost/mid/high/escalation).")


def check_quality_gate(m, problems):
    qg = m.get("quality_gate")
    if qg is None:
        err(problems, "quality_gate 섹션이 없습니다.")
        return
    if "confidence_threshold" not in qg:
        err(problems, "quality_gate.confidence_threshold가 없습니다 — 도메인별로 반드시 명시해야 합니다.")
    else:
        ct = qg["confidence_threshold"]
        if not (isinstance(ct, (int, float)) and 0 <= ct <= 1):
            err(problems, f"quality_gate.confidence_threshold는 0~1 사이 숫자여야 함 (현재: {ct})")
    on_fail = qg.get("on_fail")
    if on_fail is None:
        err(problems, "quality_gate.on_fail이 없습니다.")
    else:
        if "retry_count" not in on_fail:
            err(problems, "quality_gate.on_fail.retry_count가 없습니다.")
        target = on_fail.get("escalation_target")
        if target not in {"self_retry", "human_review", "escalation_tier"}:
            err(problems, f"quality_gate.on_fail.escalation_target='{target}'는 허용되지 않음.")


def check_invocation(m, problems):
    inv = m.get("invocation")
    if inv is None:
        return
    if "entrypoint" not in inv:
        err(problems, "invocation.entrypoint가 없습니다.")
    if not inv.get("callable_by"):
        err(problems, "invocation.callable_by가 비어있습니다.")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 validate_manifest.py <manifest.yaml 경로>")
        sys.exit(1)

    manifest_path = sys.argv[1]
    if not os.path.exists(manifest_path):
        print(f"❌ 파일을 찾을 수 없습니다: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    problems = []
    check_top_level_required(manifest, problems)
    check_version(manifest, problems)
    check_io_contract(manifest, problems)
    check_model_routing(manifest, problems)
    check_quality_gate(manifest, problems)
    check_invocation(manifest, problems)

    if problems:
        print(f"❌ 검증 실패 — {len(problems)}개 문제 발견\n")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        sys.exit(1)
    else:
        print("✅ 검증 통과 — 이 manifest는 표준 포맷을 따릅니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
