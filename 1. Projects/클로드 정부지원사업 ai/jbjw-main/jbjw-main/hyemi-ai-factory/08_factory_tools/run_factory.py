#!/usr/bin/env python3
"""공장 실행기 — 7단계 파이프라인 (notice→risk→ideas→lock→review→revision→handoff).

사용법:
    python 08_factory_tools/run_factory.py <프로젝트명> --step all
    python 08_factory_tools/run_factory.py <프로젝트명> --step review

원칙 (factory_runner_spec.md):
- 규칙으로 판정 가능한 것은 코드가, 판단이 필요한 것은 ai_prompt_*.md 생성으로, 확정은 사람이.
- 코드는 어떤 경로로도 LOCKED 상태를 쓰지 않는다.
- exit code: 0 정상 / 2 FATAL / 3 BLOCKED / 4 PENDING_APPROVAL
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STAGES = ["notice", "risk", "ideas", "lock", "review", "revision", "handoff"]

# danger_words.md 파싱 실패 시 대비 최소 내장 목록
FALLBACK_DANGER_TERMS = [
    "완벽히 해결", "100% 가능", "무조건 가능", "검증 완료", "실패하지 않음",
    "효과 보장", "독점", "최고 수준", "세계 최초", "자동으로 모두 처리",
    "AI가 판단", "자동 발송", "무인 운영",
]


# ---------- 공통 유틸 ----------

def missing(v) -> bool:
    return v in (None, "", "미확보", "미확인", [], {})


def fmt(v) -> str:
    if missing(v):
        return "**[확인 필요]**"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


class Ctx:
    def __init__(self, project: str):
        self.project = project
        self.input_path = BASE / "01_inputs" / project / "input.json"
        self.out_dir = BASE / "04_outputs" / project
        self.review_dir = BASE / "05_reviews" / project
        self.state_path = self.out_dir / "project.json"
        self.data = None
        self.state = None
        self.today = date.today().isoformat()

    def load(self):
        if not self.state_path.exists():
            raise SystemExit(fatal(f"project.json 없음 — 먼저 create_project.py {self.project} 실행"))
        if not self.input_path.exists():
            raise SystemExit(fatal(f"입력 없음: {self.input_path}"))
        try:
            self.data = json.loads(self.input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(fatal(f"input.json 파싱 실패: {e}"))
        for key in ("project_name", "notice", "applicant", "ideas"):
            if key not in self.data:
                raise SystemExit(fatal(f"input.json 필수 키 누락: {key}"))
        self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.review_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self):
        self.state["updated_at"] = self.today
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def set_stage(self, stage: str, status: str):
        # 안전장치: 코드는 LOCKED를 쓰지 않는다
        assert status != "LOCKED", "코드에 의한 LOCK 금지"
        self.state["stages"][stage] = status

    def note(self, msg: str):
        if msg not in self.state["needs_confirmation"]:
            self.state["needs_confirmation"].append(msg)

    def warn(self, msg: str):
        if msg not in self.state["warnings"]:
            self.state["warnings"].append(msg)

    def write(self, path: Path, text: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"  생성: {path.relative_to(BASE)}")


def fatal(msg: str) -> int:
    print(f"[FATAL] {msg}")
    return 2


def load_danger_terms() -> list:
    """00_rules/danger_words.md 의 표 1열에서 위험 표현을 추출."""
    path = BASE / "00_rules" / "danger_words.md"
    terms = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*([^|]+?)\s*\|", line)
            if not m:
                continue
            cell = m.group(1)
            if cell in ("표현", "---") or cell.startswith("-"):
                continue
            for t in cell.split("/"):
                t = re.sub(r"\(.*?\)", "", t).strip()
                if len(t) >= 2:
                    terms.append(t)
    return sorted(set(terms + FALLBACK_DANGER_TERMS), key=len, reverse=True)


# ---------- 단계 구현 ----------

def step_notice(ctx: Ctx) -> str:
    n = ctx.data["notice"]
    checks = []
    for key, label in [
        ("raw_text", "공고문 원문"), ("exclusions", "지원제외 조항"), ("eligibility", "신청자격"),
        ("scoring", "심사표·배점"), ("execution_period", "수행기간"),
    ]:
        if missing(n.get(key)):
            checks.append(label)
            ctx.note(f"공고: {label} 미확보")
    scoring_rows = "\n".join(
        f"| {s.get('item','?')} | {s.get('points','?')} | {s.get('note','')} |"
        for s in (n.get("scoring") or [])
    ) or "| [확인 필요 — 배점표 미입력, 내부 기준(evaluation_rubric.md)으로 대체] | - | |"
    b = n.get("budget", {}) or {}
    f = n.get("format", {}) or {}
    p = n.get("presentation", {}) or {}
    body = f"""# 공고 요약: {fmt(n.get('title'))}

작성일: {ctx.today} / 상태: DRAFT / 생성: run_factory.py (notice)

## 1. 기본 정보

| 항목 | 내용 |
|---|---|
| 공고명 | {fmt(n.get('title'))} |
| 주관기관 | {fmt(n.get('agency'))} |
| 공고 목적 | {fmt(n.get('purpose'))} |
| 접수 마감 | {fmt(n.get('apply_deadline'))} |
| 수행기간 | {fmt(n.get('execution_period'))} |
| 지원 한도 / 자부담 | {fmt(b.get('max_amount'))} / {fmt(b.get('self_pay_ratio'))} |

## 2. 자격·제외

| 항목 | 내용 |
|---|---|
| 신청자격 | {fmt(n.get('eligibility'))} |
| 지원제외 | {fmt(n.get('exclusions'))} |
| 가점 항목 | {fmt(n.get('bonus_items'))} |

## 3. 제출·평가

| 항목 | 내용 |
|---|---|
| 양식 / 페이지 제한 | {fmt(f.get('form_type'))} / {fmt(f.get('page_limit'))} |
| 발표 | 필요: {fmt(p.get('required'))}, 발표 {fmt(p.get('present_minutes'))}분 + Q&A {fmt(p.get('qna_minutes'))}분 |

### 심사표·배점

| 평가항목 | 배점 | 비고 |
|---|---:|---|
{scoring_rows}

## 4. 예산 기준

- 허용: {fmt(b.get('allowed_items'))}
- 제외: {fmt(b.get('excluded_items'))}

## 5. 확인 필요 목록

{chr(10).join('- ' + c for c in checks) if checks else '- 없음'}
"""
    ctx.write(ctx.out_dir / "notice_summary.md", body)
    ctx.set_stage("notice", "DRAFT")
    return "OK"


def step_risk(ctx: Ctx) -> str:
    a = ctx.data["applicant"]
    blockers, rows = [], []

    def row(item, value, judge):
        rows.append(f"| {item} | {fmt(value)} | {judge} |")

    if a.get("tax_arrears") is True:
        blockers.append("체납(tax_arrears=true) — 접수 요건 미달 가능")
        row("세금 체납", a.get("tax_arrears"), "**BLOCKED — 탈락급**")
    elif missing(a.get("tax_arrears")):
        row("세금 체납", a.get("tax_arrears"), "[확인 필요 — 납세증명서]")
        ctx.note("자격: 체납 여부 미확인")
    else:
        row("세금 체납", a.get("tax_arrears"), "이상 없음(신고 기준)")

    if a.get("duplicate_grant_history") is True:
        blockers.append("동일사업 중복수혜(duplicate_grant_history=true)")
        row("중복수혜", a.get("duplicate_grant_history"), "**BLOCKED — 탈락급**")
    elif missing(a.get("duplicate_grant_history")):
        row("중복수혜", a.get("duplicate_grant_history"), "[확인 필요 — 수혜 이력 조회]")
        ctx.note("자격: 중복수혜 여부 미확인")
    else:
        row("중복수혜", a.get("duplicate_grant_history"), "이상 없음(신고 기준)")

    for key, label, need in [
        ("industry_code", "업종코드", "공고 제외 업종과 대조 필요"),
        ("biz_years", "업력", "공고 자격 기준과 대조 필요"),
        ("biz_type", "사업자 형태", "지원대상 정의와 대조 필요"),
    ]:
        if missing(a.get(key)):
            row(label, a.get(key), f"[확인 필요 — {need}]")
            ctx.note(f"자격: {label} 미확보")
        else:
            row(label, a.get(key), f"입력됨 — {need} (사람 대조)")

    approved = (ctx.data.get("approvals") or {}).get("eligibility_confirmed") is True
    body = f"""# 자격·리스크 점검: {ctx.project}

작성일: {ctx.today} / 상태: DRAFT / 생성: run_factory.py (risk)
최종 판정: **사람 확정 필수** (approvals.eligibility_confirmed = {str(approved).lower()})

| 점검 항목 | 신고·입력값 | 판정 |
|---|---|---|
{chr(10).join(rows)}

## 구조 리스크 (모든 프로젝트 공통 점검 — AI 검수 단계에서 재평가)

- 단순 구매성으로 보일 위험 / 외주 의존으로 보일 위험 / 개인정보 처리 / 수행기간 내 실현 가능성

## 판정

{'**BLOCKED**: ' + ' · '.join(blockers) if blockers else ('자격 승인 완료 (사람 확인 기록됨)' if approved else '조건부 진행 — 자격 3종은 서류 확인 전까지 확정 금지. 확인 후 approvals.eligibility_confirmed=true 기록')}
"""
    ctx.write(ctx.out_dir / "applicant_risk_check.md", body)
    if blockers:
        ctx.state["blockers"] = blockers
        ctx.set_stage("risk", "BLOCKED")
        return "BLOCKED"
    if not approved:
        ctx.warn("자격 3종 미승인 상태로 진행 중 (revision 1순위 기재)")
    ctx.set_stage("risk", "DRAFT")
    return "OK"


def step_ideas(ctx: Ctx) -> str:
    ideas = ctx.data["ideas"]
    rows = []
    for i in ideas:
        rows.append(
            f"| {i.get('id')} | {fmt(i.get('name'))} | {fmt(i.get('problem'))} | {fmt(i.get('target'))} | "
            f"{len(i.get('evidence_owned') or [])}건 확보 / {len(i.get('evidence_planned') or [])}건 예정 | "
            f"{fmt(i.get('risks'))} |"
        )
        if not (i.get("evidence_owned") or []):
            ctx.warn(f"{i.get('id')}: 확보 증빙 0건")
    body = f"""# 아이디어 후보표: {ctx.project}

작성일: {ctx.today} / 상태: DRAFT / 생성: run_factory.py (ideas)
⚠️ 10축 채점은 AI 판단 단계 — ai_prompt_ideas.md 를 Claude 세션에 붙여넣어 채점 후 이 파일에 반영하라.

| id | 후보명 | 해결 문제 | 대상 | 증빙 | 리스크 |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## AI 채점 반영 후 형식 (evaluation_rubric.md 10축, 5점 척도)

| 후보 | 공고 적합성 | 배점 적합성 | 문제 명확성 | 고객 명확성 | 증빙 가능성 | 실현 가능성 | 차별성 | 예산 타당성 | 발표 방어 | 리스크 | 합계 | 종합 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| (AI 채점 대기) | | | | | | | | | | | | |
"""
    ctx.write(ctx.out_dir / "idea_comparison_table.md", body)
    prompt = f"""# ai_prompt_ideas.md — Claude 세션에 그대로 붙여넣기

hyemi-ai-factory의 CLAUDE.md와 00_rules/evaluation_rubric.md, 00_rules/danger_words.md를 읽고 적용해라.

프로젝트 {ctx.project}의 아이디어 후보를 채점해라.
입력: 01_inputs/{ctx.project}/input.json (ideas 배열), 04_outputs/{ctx.project}/notice_summary.md

작업:
1. 각 후보를 10축 5점 척도로 채점하고 근거를 써라 (무조건 긍정 금지, 감점 위험 먼저).
2. 후보별 감점 위험과 심사위원 예상 공격을 표로 써라.
3. 심사표 배점 기준으로 1개를 추천하고, 탈락 후보의 보존 방법(확장/증빙/타 공고)을 지정해라.
4. 결과를 04_outputs/{ctx.project}/idea_comparison_table.md 의 "AI 채점 반영 후 형식" 표에 채워 넣어라.
5. 최종 선정은 사람 몫 — input.json의 selected_idea_id와 approvals.idea_selected는 건드리지 마라.
"""
    ctx.write(ctx.out_dir / "ai_prompt_ideas.md", prompt)
    ctx.set_stage("ideas", "DRAFT")
    return "OK"


def step_lock(ctx: Ctx) -> str:
    sel = ctx.data.get("selected_idea_id")
    approved = (ctx.data.get("approvals") or {}).get("idea_selected") is True
    if not sel or not approved:
        ctx.set_stage("lock", "PENDING_APPROVAL")
        print("  [PENDING_APPROVAL] 최종 아이디어가 사람 확정되지 않았습니다.")
        print(f"    해제: 01_inputs/{ctx.project}/input.json 에 selected_idea_id 지정 +")
        print('          "approvals": {"idea_selected": true} 기록 후 재실행')
        return "PENDING_APPROVAL"
    idea = next((i for i in ctx.data["ideas"] if i.get("id") == sel), None)
    if idea is None:
        ctx.set_stage("lock", "BLOCKED")
        ctx.state["blockers"].append(f"selected_idea_id '{sel}' 가 ideas에 없음")
        return "BLOCKED"
    body = f"""# 최종 아이디어 LOCK: {ctx.project}

작성일: {ctx.today} / 상태: DRAFT (사람 승인 기록됨 — 검수 후 LOCK_STATUS.md에 수동 기재)
생성: run_factory.py (lock)

| 항목 | 내용 |
|---|---|
| 최종 아이디어 | {fmt(idea.get('name'))} ({sel}) |
| 핵심 문제 | {fmt(idea.get('problem'))} |
| 첫 고객·수혜자 | {fmt(idea.get('target'))} |
| 주요 산출물 | {fmt(idea.get('outputs'))} |
| 확보 증빙 | {fmt(idea.get('evidence_owned'))} |
| 예정 증빙 | {fmt(idea.get('evidence_planned'))} |
| 조심할 리스크 | {fmt(idea.get('risks'))} |
| 과제명 후보 | (AI 생성 대기 — ai_prompt_lock.md 실행) |
| 한 줄 요약 후보 | (AI 생성 대기) |
| 핵심 성과목표 | [확인 필요 — 실측 기준치 확보 후 작성] |

## LOCK 이후 규칙

탈락 후보는 본문 혼입 금지 — expansion_ideas.md 또는 후속 계획으로 분리 (lock_rules.md).
"""
    ctx.write(ctx.out_dir / "selected_idea_lock.md", body)
    prompt = f"""# ai_prompt_lock.md — Claude 세션에 그대로 붙여넣기

hyemi-ai-factory의 CLAUDE.md와 00_rules/를 적용해라.

프로젝트 {ctx.project}의 확정 아이디어({sel})에 대해:
1. 과제명 후보 5개 — [고객·현장]+[문제]+[해결수단]+[결과물] 구조, 3~5초 내 이해 가능.
2. 한 줄 요약 후보 5개 — 수치는 실측된 것만, 없으면 자리표시 [실측치].
3. danger_words.md 스캔 후 위험 표현 0건 확인.
4. 04_outputs/{ctx.project}/selected_idea_lock.md 의 대기 항목을 채워라. 상태는 DRAFT 유지.
"""
    ctx.write(ctx.out_dir / "ai_prompt_lock.md", prompt)
    ctx.set_stage("lock", "DRAFT")
    return "OK"


def step_review(ctx: Ctx) -> str:
    terms = load_danger_terms()
    hits = []
    for md in sorted(ctx.out_dir.glob("*.md")):
        if md.name.startswith("ai_prompt"):
            continue
        for ln, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for t in terms:
                if t in line:
                    hits.append((md.name, ln, t, line.strip()[:80]))
    hit_rows = "\n".join(
        f"| {f} | {ln} | {t} | {snippet} |" for f, ln, t, snippet in hits
    ) or "| - | - | 검출 없음 | - |"
    body = f"""# review_scan_report.md — 자동 검수 리포트: {ctx.project}

작성일: {ctx.today} / 생성: run_factory.py (review)
⚠️ 이것은 기계 검수(위험 표현·누락 집계)다. 심사위원 모드 정성 검수는 ai_prompt_judge.md 로 실행하라.

## 1. 위험 표현 스캔 (00_rules/danger_words.md, {len(terms)}개 항목 대조)

| 파일 | 행 | 검출 표현 | 문맥 |
|---|---|---|---|
{hit_rows}

{'**→ ' + str(len(hits)) + '건 검출 — replacement_words.md로 대체 후 재스캔**' if hits else '검출 0건'}

## 2. 확인 필요 누적 목록

{chr(10).join('- ' + c for c in ctx.state['needs_confirmation']) if ctx.state['needs_confirmation'] else '- 없음'}

## 3. 경고 누적 목록

{chr(10).join('- ' + w for w in ctx.state['warnings']) if ctx.state['warnings'] else '- 없음'}
"""
    ctx.write(ctx.review_dir / "review_scan_report.md", body)
    prompt = f"""# ai_prompt_judge.md — Claude 세션에 그대로 붙여넣기 (심사위원 모드)

hyemi-ai-factory의 CLAUDE.md, AGENTS.md(#5 심사위원), 00_rules/ 전체를 적용해라.
너는 지금부터 이 프로젝트를 떨어뜨릴 이유를 찾는 심사위원이다.

검수 대상: 04_outputs/{ctx.project}/ 전체 + 05_reviews/{ctx.project}/review_scan_report.md

8종 검수(공고 적합성/심사표·배점/아이디어 선정/실행 가능성/예산/증빙/위험 표현/발표 방어)를 실행하고
05_reviews/{ctx.project}/ 에 다음을 생성해라:
final_judge_review.md, score_estimation_table.md, risk_register.md, missing_evidence_list.md,
budget_risk_review.md, dangerous_expression_review.md, presentation_attack_qna.md, revision_order.md

템플릿: 03_templates/final_judge_review_template.md, revision_order_template.md
기준: 내부 채점 80점 미만 또는 탈락급 리스크 1건 이상이면 "제출 불가" 판정.
"""
    ctx.write(ctx.review_dir / "ai_prompt_judge.md", prompt)
    if hits:
        ctx.warn(f"위험 표현 {len(hits)}건 검출 (review_scan_report.md)")
    ctx.set_stage("review", "DRAFT")
    return "OK"


def step_revision(ctx: Ctx) -> str:
    p1, p2 = [], []
    if ctx.state["blockers"]:
        p1 += [f"[BLOCKED 해제] {b}" for b in ctx.state["blockers"]]
    p1 += [f"[확인 필요] {c}" for c in ctx.state["needs_confirmation"]]
    p2 += [f"[경고] {w}" for w in ctx.state["warnings"]]
    if ctx.state["stages"].get("lock") == "PENDING_APPROVAL":
        p1.append("[승인 대기] selected_idea_id 지정 + approvals.idea_selected=true 기록")
    body = f"""# revision_order_auto.md — 자동 재작업 지시서: {ctx.project}

작성일: {ctx.today} / 생성: run_factory.py (revision)
⚠️ 기계 감지분만 포함. 심사위원 정성 검수 결과(revision_order.md)와 합쳐서 볼 것.

## 1순위 — 진행을 막는 것 (탈락 위험·승인 대기)

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(p1)) if p1 else '- 없음'}

## 2순위 — 진행은 되지만 점수를 깎는 것

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(p2)) if p2 else '- 없음'}

## 처리 방법

- 입력 보완: 01_inputs/{ctx.project}/input.json 수정 → run_factory.py {ctx.project} --step all 재실행
- AI 판단 단계: 04_outputs/{ctx.project}/ai_prompt_*.md, 05_reviews/{ctx.project}/ai_prompt_judge.md 를 Claude에 붙여넣기
"""
    ctx.write(ctx.review_dir / "revision_order_auto.md", body)
    ctx.set_stage("revision", "DRAFT")
    return "OK"


def step_handoff(ctx: Ctx) -> str:
    stages = ctx.state["stages"]
    rows = "\n".join(f"| {s} | {stages[s]} |" for s in STAGES)
    body = f"""# HANDOFF_{ctx.project}.md — 프로젝트 인계문

갱신일: {ctx.today} / 생성: run_factory.py (handoff)

## 단계 상태

| 단계 | 상태 |
|---|---|
{rows}

## 남은 확인 필요 ({len(ctx.state['needs_confirmation'])}건)

{chr(10).join('- ' + c for c in ctx.state['needs_confirmation']) if ctx.state['needs_confirmation'] else '- 없음'}

## 차단 사유

{chr(10).join('- ' + b for b in ctx.state['blockers']) if ctx.state['blockers'] else '- 없음'}

## 다음 명령

```text
python 08_factory_tools/run_factory.py {ctx.project} --step all
```

AI 판단 단계가 대기 중이면 04_outputs/{ctx.project}/ai_prompt_*.md 를 Claude 세션에 붙여넣어라.
LOCK 기록은 검수 통과 후 사람이 06_locks/LOCK_STATUS.md 에 수동 기재한다.
"""
    ctx.write(BASE / "10_handoff" / f"HANDOFF_{ctx.project}.md", body)
    ctx.set_stage("handoff", "DRAFT")
    return "OK"


STEP_FUNCS = {
    "notice": step_notice, "risk": step_risk, "ideas": step_ideas, "lock": step_lock,
    "review": step_review, "revision": step_revision, "handoff": step_handoff,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="혜미식 AI 공장 실행기")
    ap.add_argument("project")
    ap.add_argument("--step", default="all", choices=["all"] + STAGES)
    ap.add_argument("--force", action="store_true", help="REVIEWED 이상 단계도 덮어쓰기")
    args = ap.parse_args()

    ctx = Ctx(args.project)
    try:
        ctx.load()
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    todo = STAGES if args.step == "all" else [args.step]
    exit_code = 0
    for s in todo:
        cur = ctx.state["stages"].get(s, "PENDING")
        if cur in ("REVIEWED",) and not args.force:
            print(f"[SKIP] {s}: 상태 {cur} — 덮어쓰려면 --force")
            continue
        print(f"[단계] {s}")
        result = STEP_FUNCS[s](ctx)
        if result == "BLOCKED":
            print(f"[BLOCKED] {s} 단계에서 정지. 사유는 project.json > blockers 와 산출물 참조.")
            exit_code = 3
            break
        if result == "PENDING_APPROVAL":
            exit_code = 4
            break
    # 정지되더라도 재작업 지시서·인계문은 남긴다 (error_handling_rules.md: 조용히 넘어가지 않는다)
    if exit_code in (3, 4) and args.step == "all":
        print("[단계] revision (정지 보고)")
        step_revision(ctx)
        print("[단계] handoff (정지 보고)")
        step_handoff(ctx)
    ctx.save_state()
    print(f"[상태 저장] {ctx.state_path.relative_to(BASE)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
