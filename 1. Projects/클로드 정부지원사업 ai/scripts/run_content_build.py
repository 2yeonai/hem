# -*- coding: utf-8 -*-
"""
run_content_build.py — 내용 생성 구간 실행기 (2026-07-20 2차, [gombeck1])

manifest v0.7.0의 local stage들을 실제로 자동 실행한다 (복붙 없음):
  prepare : 입력표 YAML 자동 로드 → 입력 충분성 진단 → 시나리오 검사 → 미달 시 차단(exit 2)
  gate    : workdir/sections/{A|B}_{problem|solution|scaleup|team}.md 자동 병합 →
            산술·복사본·고객군·증빙 게이트 일괄 실행 → FAIL 시 차단(exit 1)
  finalize: 게이트 통과본을 제출용/내부검토본으로 자동 분리 저장
  all     : prepare → gate → finalize

사용:
  python3 scripts/run_content_build.py --input 입력표_템플릿.yaml \
      --workdir mo,on_예비창업패키지/공장실행_2026-07-20 all
"""
import argparse, io, json, os, sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content_gate as cg

SECTIONS = [("problem", "1. 문제인식 (Problem)"),
            ("solution", "2. 실현가능성 (Solution)"),
            ("scaleup", "3. 성장전략 (Scale-up)"),
            ("team", "4. 팀 구성 (Team)")]
DOCS = {"A": "예비창업패키지", "B": "초기창업패키지(가상 시나리오)"}


def load_input(path):
    return yaml.safe_load(io.open(path, encoding="utf-8"))


def build_ledger(inp):
    """입력표를 증빙 원장으로 변환 — 잠금값 수치가 본문에서 '출처 없는 수치'로 오탐되지 않게 등록."""
    ledger = []
    def add(claim, status, ev=None):
        ledger.append({"claim": claim, "status": status, "evidence_type": ev,
                       "usable_in_submission": status not in cg.NEVER_IN_SUBMISSION})
    for item in inp.get("founder_capability", []):
        add(str(item.get("value")), item.get("status", "needs_evidence"), item.get("evidence"))
    add("전국 출장형 업체 300~500개소, 단일 5만원 기준 연 1.8~3억원, 구간제 9.9만~19.9만 기준 연 3.6억~11.9억원", "ai_suggestion")
    add("서비스 1회 단가 10~15만원(업계 공개요금)", "user_confirmed", "업계 공개요금")
    add("가격 구간 9.9만/19.9만/39.9만, 검증 5만·10만·20만", inp.get("pricing", {}).get("status", "ai_suggestion"))
    add("예창패 1단계 2,000만원(400/900/250/300/150), 협약 8개월", "verified_fact", "공고 원문")
    add("초창패 정부지원 1억 + 자기부담 3,334(현금 1,334+현물 2,000), 총사업비 13,334", "verified_fact", "공고 붙임6")
    cp = inp.get("current_performance_초창패가상") or {}
    if cp:
        add("가상 현재실적: 시범 3곳·사용자 10명·기록 150건·유료 1곳·월 20만원·확인시간 15분→5분",
            "simulation_assumption")
    for k in ("customer_validation", "deal_evidence", "usage_performance", "revenue"):
        for name, e in (inp.get(k) or {}).items():
            add("%s=%s" % (name, e.get("value")), e.get("status", "needs_evidence"))
    return ledger


def cmd_prepare(inp, workdir):
    os.makedirs(os.path.join(workdir, "sections"), exist_ok=True)
    flat = {
        "program_type": inp.get("program_type"), "reference_date": inp.get("reference_date"),
        "business_status": (inp.get("business_status") or {}).get("value"),
        "product_stage": (inp.get("product_stage") or {}).get("value"),
        "customer_validation": inp.get("customer_validation"), "deal_evidence": inp.get("deal_evidence"),
        "usage_performance": inp.get("usage_performance"), "revenue": inp.get("revenue"),
        "founder_capability": inp.get("founder_capability"), "team": inp.get("team"),
        "pricing": inp.get("pricing"), "primary_market": (inp.get("primary_market") or {}).get("value"),
        "evidence_status": inp.get("evidence_status"), "prohibitions": inp.get("prohibitions"),
    }
    diag = cg.diagnose_input_sufficiency(flat)
    print("[prepare] 입력 충분성: %d%% — %s" % (diag["level_pct"], diag["verdict"]))
    for m in diag["missing"]:
        print("   부족:", m)
    scen_b = {"program_type": "초기창업패키지", "simulation_mode": True,
              "current_performance": inp.get("current_performance_초창패가상") or {}}
    errs = cg.check_scenario(scen_b)
    for e in errs:
        print("   [시나리오B 오류]", e)
    io.open(os.path.join(workdir, "prepare_report.json"), "w", encoding="utf-8").write(
        json.dumps({"diagnosis": diag, "scenario_b_errors": errs}, ensure_ascii=False, indent=1))
    if diag["level_pct"] < 60 or errs:
        print("[prepare] 차단 — 입력 보강 후 재실행")
        return 2
    print("[prepare] 통과 — 섹션 작성 가능 (sections/{A|B}_{problem|solution|scaleup|team}.md)")
    return 0


def merge(workdir, doc):
    parts, missing = [], []
    for key, title in SECTIONS:
        fp = os.path.join(workdir, "sections", "%s_%s.md" % (doc, key))
        if not os.path.exists(fp):
            missing.append(fp); continue
        parts.append(io.open(fp, encoding="utf-8").read().strip())
    return "\n\n".join(parts), missing


def cmd_gate(inp, workdir):
    ledger = build_ledger(inp)
    report = {"fail": [], "warn": []}
    merged = {}
    for doc in DOCS:
        text, missing = merge(workdir, doc)
        if missing:
            report["fail"].append({"type": "missing_section", "doc": doc, "files": missing})
            continue
        merged[doc] = text
        io.open(os.path.join(workdir, "merged_%s.md" % doc), "w", encoding="utf-8").write(text)
        for pr in cg.verify_arithmetic(text):
            report["fail"].append(dict(pr, doc=doc))
        for pr in cg.check_customer_consistency(text):
            (report["fail"] if pr["type"] == "customer_mix" else report["warn"]).append(dict(pr, doc=doc))
        for fl in cg.find_unlabeled_numbers(text, ledger):
            report["warn"].append(dict(fl, doc=doc))
    if "A" in merged and "B" in merged:
        for pr in cg.check_scenario_separation(merged["A"], merged["B"]):
            report["fail"].append(pr)
    for e in cg.check_evidence_ledger(ledger):
        report["warn"].append({"type": "ledger", "detail": e})
    io.open(os.path.join(workdir, "gate_report.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print("[gate] FAIL %d건 / WARN %d건 — 상세: gate_report.json" % (len(report["fail"]), len(report["warn"])))
    for f in report["fail"]:
        print("   [FAIL]", f.get("type"), str(f)[:160])
    return 1 if report["fail"] else 0


def cmd_finalize(inp, workdir, outdir):
    ledger = build_ledger(inp)
    os.makedirs(outdir, exist_ok=True)
    made = []
    for doc, label in DOCS.items():
        mp = os.path.join(workdir, "merged_%s.md" % doc)
        if not os.path.exists(mp):
            continue
        text = io.open(mp, encoding="utf-8").read()
        sub, internal = cg.split_outputs(text)
        sub_path = os.path.join(outdir, "제출용_%s_2026-07-20.md" % label.split("(")[0])
        int_path = os.path.join(outdir, "내부검토본_%s_2026-07-20.md" % label.split("(")[0])
        io.open(sub_path, "w", encoding="utf-8").write(sub + "\n\n<!-- ok -->\n")
        internal_full = ("# 내부검토본 — %s\n\n## 본문에서 분리된 내부 문단\n\n%s\n\n"
                         "## 증빙 원장 (사실·가정·목표 구분표)\n\n" % (label, internal or "(없음)"))
        for e in ledger:
            internal_full += "- [%s] %s%s\n" % (e["status"], e["claim"],
                              "" if e.get("usable_in_submission") else " ← 제출본 사용 금지")
        internal_full += "\n<!-- ok -->\n"
        io.open(int_path, "w", encoding="utf-8").write(internal_full)
        made += [sub_path, int_path]
    print("[finalize] 저장:", *made, sep="\n   ")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("cmd", choices=["prepare", "gate", "finalize", "all"])
    a = ap.parse_args()
    inp = load_input(a.input)
    outdir = a.outdir or a.workdir
    if a.cmd in ("prepare", "all"):
        rc = cmd_prepare(inp, a.workdir)
        if rc: sys.exit(rc)
        if a.cmd == "prepare": sys.exit(0)
    if a.cmd in ("gate", "all"):
        rc = cmd_gate(inp, a.workdir)
        if rc: sys.exit(rc)
        if a.cmd == "gate": sys.exit(0)
    if a.cmd in ("finalize", "all"):
        sys.exit(cmd_finalize(inp, a.workdir, outdir))


if __name__ == "__main__":
    main()
