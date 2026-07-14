"""
test_manifest.py - manifest.yaml regression test (structural, no runner exists yet)

There is no run_pipeline.py to execute end-to-end yet, so "regression test" here
means: verify manifest.yaml's pipeline.stages graph is internally consistent, and
stays in sync with 12bot_kind_bunryupyo.yaml (the detailed-rationale companion
file). This is exactly the kind of thing that silently breaks when someone edits
one file and forgets the other.

Checks:
  1. manifest.yaml passes the platform validator (validate_manifest.py)
  2. Every stage id in manifest.yaml's pipeline.stages also exists in
     12bot_kind_bunryupyo.yaml's stages, with the same kind
  3. Every depends_on target is a real stage id (no dangling references)
  4. The dependency graph has no cycles
  5. Every io.reads / io.writes field name used in manifest.yaml is declared
     in 12bot_kind_bunryupyo.yaml's shared_context (no undeclared fields)
  6. model_routing.stages covers exactly the stages with kind: model (no
     missing tier assignment, no orphaned tier assignment for a non-model stage)
  7. on_reject is only present on kind: human stages

Run: python3 test_manifest.py
"""

import sys
import subprocess
import yaml
from pathlib import Path

FOLDER = Path(__file__).parent.parent
MANIFEST_PATH = FOLDER / "manifest.yaml"
KIND_TABLE_PATH = FOLDER / "12봇_kind분류표.yaml"
VALIDATOR_PATH = FOLDER.parent / "클로드 ai 자동화" / "validate_manifest.py"

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    extra = "  (" + detail + ")" if detail else ""
    print("[" + status + "] " + label + extra)


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    with open(KIND_TABLE_PATH, encoding="utf-8") as f:
        kind_table = yaml.safe_load(f)

    # 1. platform validator
    r = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), str(MANIFEST_PATH)],
        capture_output=True, text=True
    )
    check("manifest.yaml passes validate_manifest.py", r.returncode == 0, r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[:200])

    m_stages = {s["id"]: s for s in manifest["pipeline"]["stages"]}
    k_stages = {s["id"]: s for s in kind_table["stages"]}

    # 2. stage id + kind match between the two files
    check(
        "manifest.yaml has exactly the same 14 stage ids as 12봇_kind분류표.yaml",
        set(m_stages.keys()) == set(k_stages.keys()),
        "manifest only=" + str(set(m_stages) - set(k_stages)) + " table only=" + str(set(k_stages) - set(m_stages)),
    )
    kind_mismatches = [sid for sid in m_stages if sid in k_stages and m_stages[sid]["kind"] != k_stages[sid]["kind"]]
    check("no kind mismatches between manifest.yaml and 12봇_kind분류표.yaml", kind_mismatches == [], str(kind_mismatches))

    # 3. depends_on targets exist
    bad_deps = []
    for sid, s in m_stages.items():
        for dep in s.get("depends_on", []):
            if dep not in m_stages:
                bad_deps.append((sid, dep))
    check("every depends_on target is a real stage id", bad_deps == [], str(bad_deps))

    # 4. no cycles (simple DFS)
    def has_cycle():
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {sid: WHITE for sid in m_stages}

        def visit(sid):
            color[sid] = GRAY
            for dep in m_stages[sid].get("depends_on", []):
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    return True
                if color[dep] == WHITE and visit(dep):
                    return True
            color[sid] = BLACK
            return False

        return any(color[sid] == WHITE and visit(sid) for sid in m_stages)

    check("dependency graph has no cycles", not has_cycle())

    # 5. io fields declared in shared_context
    shared_fields = set(kind_table["shared_context"].keys())
    undeclared = []
    for sid, s in m_stages.items():
        io = s.get("io", {})
        for field in (io.get("reads") or []) + (io.get("writes") or []):
            if field not in shared_fields:
                undeclared.append((sid, field))
    check("every io.reads/writes field is declared in shared_context", undeclared == [], str(undeclared))

    # 6. model_routing covers exactly the model-kind stages
    model_stage_ids = {sid for sid, s in m_stages.items() if s["kind"] == "model"}
    routed_ids = {s["step"] for s in manifest["model_routing"]["stages"]}
    check(
        "model_routing.stages covers exactly the kind:model stages, no more/less",
        model_stage_ids == routed_ids,
        "model_stages=" + str(model_stage_ids) + " routed=" + str(routed_ids),
    )

    # 7. on_reject only on kind: human stages
    bad_on_reject = [sid for sid, s in m_stages.items() if "on_reject" in s and s["kind"] != "human"]
    check("on_reject only appears on kind: human stages", bad_on_reject == [], str(bad_on_reject))

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    print("")
    print(str(passed) + "/" + str(total) + " checks passed")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
