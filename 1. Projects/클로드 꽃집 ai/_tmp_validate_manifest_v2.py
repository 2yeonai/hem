#!/usr/bin/env python3
"""
validate_manifest.py — 스킬 팩토리 v2 manifest 검증 스크립트

배경: 이 스크립트는 이번(2026-07-07) 방역 스킬 작업 전까지 존재하지 않았음.
지금까지는 최종점검_리포트(꽃집)에서 "파이썬 스크립트로 전수 검사"했다고만
기록돼 있고 스크립트 자체는 남아있지 않아서, 이번에 처음으로 재사용 가능한
형태로 새로 작성함.

검사 항목:
  1. stage id 중복 여부
  2. depends_on이 참조하는 stage id가 실제로 존재하는지
  3. triggers[].entry_stage가 실제로 존재하는 stage id인지
  3b. stage.entry_points가 "type:식별자" 형식이고 triggers 섹션에 실제
      선언된 트리거를 가리키는지 (2026-07-07 추가)
  4. stage.io.reads / io.writes가 shared_context에 선언된 필드명인지
  5. shared_context 필드의 written_by / read_by가 실제 그 stage의
     io.writes / io.reads와 일치하는지 (양방향 교차검증)
  6. run_if가 있는 stage에 run_if_status(또는 근거 설명)가 같이 있는지
     (경고만, 실패 아님 — 문서화 관례 점검)
  7. check.schema_ref가 "파일경로#점표기경로" 형식이면, 그 파일을 찾아
     점표기경로가 실제로 존재하는 키 경로인지 best-effort로 확인
     (파일을 못 찾으면 경고만, 실패 아님)

사용법:
  python3 validate_manifest.py <manifest.yaml 경로> [--schema <manifest.schema.v2.yaml 경로>]

종료 코드: 0 = 실패(FAIL) 없음(경고는 있을 수 있음), 1 = 실패 1개 이상
"""
import sys
import os
import argparse
import yaml


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_schema_ref(ref, base_dir):
    """'상대경로/파일.yaml#a.b.c' 형태를 best-effort로 풀어서 (파일존재, 키경로존재) 반환"""
    if "#" not in ref:
        return None, None
    file_part, key_part = ref.split("#", 1)
    candidates = [
        file_part,
        os.path.join(base_dir, file_part),
        os.path.join(base_dir, os.path.basename(file_part)),
        os.path.join(os.path.dirname(base_dir), file_part),
    ]
    data = None
    found_path = None
    for c in candidates:
        if os.path.isfile(c):
            try:
                data = load_yaml(c)
                found_path = c
                break
            except Exception:
                continue
    if data is None:
        return False, None
    node = data
    for key in key_part.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return True, False
    return True, True


def validate(manifest_path, schema_path=None):
    errors = []
    warnings = []

    manifest = load_yaml(manifest_path)
    base_dir = os.path.dirname(os.path.abspath(manifest_path))

    stages = manifest.get("stages", [])
    shared_context = manifest.get("shared_context", {})
    triggers = manifest.get("triggers", [])

    stage_ids = [s.get("id") for s in stages]

    # 1. stage id 중복
    seen = set()
    for sid in stage_ids:
        if sid in seen:
            errors.append(f"[FAIL] stage id 중복: {sid}")
        seen.add(sid)
    stage_id_set = set(stage_ids)

    # 2. depends_on 참조 무결성
    for s in stages:
        sid = s.get("id")
        for dep in s.get("depends_on", []) or []:
            if dep not in stage_id_set:
                errors.append(f"[FAIL] stage '{sid}'의 depends_on이 존재하지 않는 stage '{dep}'를 참조함")

    # 3. triggers.entry_stage 참조 무결성
    for t in triggers:
        entry = t.get("entry_stage")
        if entry and entry not in stage_id_set:
            errors.append(f"[FAIL] trigger(type={t.get('type')})의 entry_stage '{entry}'가 존재하지 않는 stage임")

    # 3b. stage.entry_points 형식 및 트리거 참조 무결성 (2026-07-07 추가)
    declared_trigger_keys = set()
    for t in triggers:
        ttype = t.get("type")
        ident = t.get("source") if ttype == "event" else t.get("interval") if ttype == "schedule" else None
        if ttype and ident:
            declared_trigger_keys.add(f"{ttype}:{ident}")
    for s in stages:
        sid = s.get("id")
        for ep in (s.get("entry_points") or []):
            if ":" not in ep:
                errors.append(f"[FAIL] stage '{sid}'의 entry_points 항목 '{ep}'가 'type:식별자' 형식이 아님")
                continue
            if ep not in declared_trigger_keys:
                errors.append(f"[FAIL] stage '{sid}'의 entry_points '{ep}'가 triggers 섹션에 선언되지 않은 트리거를 참조함")

    # 4. io.reads/writes가 shared_context 필드인지
    context_fields = set(shared_context.keys())
    for s in stages:
        sid = s.get("id")
        io = s.get("io", {}) or {}
        for field in (io.get("reads") or []):
            if field not in context_fields:
                errors.append(f"[FAIL] stage '{sid}'의 io.reads가 shared_context에 없는 필드 '{field}'를 참조함")
        for field in (io.get("writes") or []):
            if field not in context_fields:
                errors.append(f"[FAIL] stage '{sid}'의 io.writes가 shared_context에 없는 필드 '{field}'를 참조함")

    # 5. written_by/read_by ↔ stage io 교차검증
    stage_io = {s.get("id"): (s.get("io", {}) or {}) for s in stages}
    for field, spec in shared_context.items():
        if not isinstance(spec, dict):
            continue
        for writer in (spec.get("written_by") or []):
            if writer not in stage_id_set:
                errors.append(f"[FAIL] shared_context.{field}.written_by가 존재하지 않는 stage '{writer}'를 참조함")
            else:
                writes = stage_io.get(writer, {}).get("writes") or []
                if field not in writes:
                    warnings.append(f"[WARN] shared_context.{field}.written_by에 '{writer}'가 있지만, 그 stage의 io.writes엔 '{field}'가 없음")
        for reader in (spec.get("read_by") or []):
            if reader not in stage_id_set:
                errors.append(f"[FAIL] shared_context.{field}.read_by가 존재하지 않는 stage '{reader}'를 참조함")
            else:
                reads = stage_io.get(reader, {}).get("reads") or []
                if field not in reads:
                    warnings.append(f"[WARN] shared_context.{field}.read_by에 '{reader}'가 있지만, 그 stage의 io.reads엔 '{field}'가 없음")

    # 6. run_if 있는 stage에 run_if_status 동반 여부 (경고만)
    for s in stages:
        if "run_if" in s and "run_if_status" not in s:
            warnings.append(f"[WARN] stage '{s.get('id')}'에 run_if는 있지만 run_if_status(근거/확정여부 설명)가 없음")

    # 7. check.schema_ref best-effort 확인
    for s in stages:
        check = s.get("check")
        if check and "schema_ref" in check:
            ref = check["schema_ref"]
            file_found, key_found = resolve_schema_ref(ref, base_dir)
            if file_found is False:
                warnings.append(f"[WARN] stage '{s.get('id')}'의 check.schema_ref '{ref}' — 참조 파일을 못 찾음(경로 확인 필요)")
            elif file_found and key_found is False:
                errors.append(f"[FAIL] stage '{s.get('id')}'의 check.schema_ref '{ref}' — 파일은 찾았으나 키 경로가 없음")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument("--schema", dest="schema_path", default=None)
    args = parser.parse_args()

    errors, warnings = validate(args.manifest_path, args.schema_path)

    print(f"검증 대상: {args.manifest_path}")
    print(f"오류(FAIL): {len(errors)}건 / 경고(WARN): {len(warnings)}건\n")

    for e in errors:
        print(e)
    for w in warnings:
        print(w)

    if not errors and not warnings:
        print("문제 없음 — 모든 검사 통과")

    print()
    if errors:
        print("결과: FAIL")
        sys.exit(1)
    else:
        print("결과: PASS (경고는 참고만, 통과 처리)")
        sys.exit(0)


if __name__ == "__main__":
    main()
