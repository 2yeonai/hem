#!/usr/bin/env python3
"""Hyemi Grant Factory — 규칙 기반 분석 엔진 (AI API 불필요).

모든 엔진은 테스트 가능한 순수 함수: dict 입력 → dict 결과.
사용처: app.py(웹 UI), test_engines.py(테스트).

원칙:
- 판정 근거가 없으면 점수를 지어내지 않고 None + [확인 필요]로 남긴다.
- 어떤 엔진도 LOCKED 상태를 만들지 않는다 (LOCKED 기재는 사람 몫).
- 공고문 원문(raw_text)이 없으면 모든 실전 판정을 "확인 필요" 모드로 제한한다.

후속 확장(adapter): ai_adapter.generate(prompt) 형태의 함수를 주입하면
규칙 판정 옆에 AI 판정을 병기할 수 있게 각 엔진 결과에 ai_prompt 필드를 남긴다.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

MISSING = ("", None, "미확보", "미확인", [], {})


def is_missing(v) -> bool:
    return v in MISSING


def fmt(v) -> str:
    if is_missing(v):
        return "[확인 필요]"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


# ---------------------------------------------------------------- danger scan

FALLBACK_DANGER_TERMS = [
    "완벽히 해결", "완벽한", "100% 가능", "100%", "무조건 가능", "무조건",
    "검증 완료", "실패하지 않", "효과 보장", "독점", "최고 수준", "세계 최초",
    "국내 최초", "자동으로 모두 처리", "AI가 판단", "자동 발송", "무인 운영",
    "판매 확정", "제휴 확정", "대규모 확장", "폭발적 성장", "수익 보장", "원금 보장",
]

DANGER_REPLACEMENTS = [
    ("완벽", "위험을 줄임 / 오류를 완화함"),
    ("100%", "가능성을 높임 / 수행기간 내 가능한 범위"),
    ("무조건", "단계적으로 검증하며 진행"),
    ("자동으로 모두", "자동 생성 후 검수하여 처리"),
    ("검증 완료", "시범운영을 통해 검증 예정"),
    ("독점", "초기 진입 우위 확보"),
    ("최고 수준", "목표 품질 기준 설정 후 관리"),
    ("최초", "기존 방식과의 차별점을 구체 항목으로 제시"),
    ("실패하지 않", "위험 발생 시 보완계획 보유"),
    ("보장", "초기 반응 확보 후 단계적 확대"),
    ("AI가 판단", "AI가 초안을 생성하고 신청자가 검수·확정"),
    ("자동 발송", "발송 목록 자동 생성 후 확인하여 발송"),
    ("무인", "운영 시간을 단축하는 반자동 운영"),
    ("확정", "협의 중 / 증빙 확보 후 추진"),
    ("확장", "단계적 확대"),
]


def load_danger_terms() -> list:
    """00_rules/danger_words.md 표 1열 파싱. 실패 시 내장 목록."""
    path = BASE / "00_rules" / "danger_words.md"
    terms = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*([^|]+?)\s*\|", line)
            if not m:
                continue
            cell = m.group(1)
            if cell in ("표현", "위험 표현") or cell.startswith("-"):
                continue
            for t in cell.split("/"):
                t = re.sub(r"\(.*?\)", "", t).strip()
                if len(t) >= 2:
                    terms.append(t)
    return sorted(set(terms) | set(FALLBACK_DANGER_TERMS), key=len, reverse=True)


def _collect_texts(data: dict) -> dict:
    out = {}
    n = data.get("notice", {}) or {}
    if not is_missing(n.get("purpose")):
        out["공고목적(입력)"] = n["purpose"]
    for i in data.get("ideas", []) or []:
        pid = i.get("id", "?")
        for k, label in (("name", "후보명"), ("problem", "문제"), ("target", "대상")):
            if not is_missing(i.get(k)):
                out[f"{pid}.{label}"] = str(i[k])
        if i.get("outputs"):
            out[f"{pid}.산출물"] = " ".join(i["outputs"])
    for b in data.get("budget_plan", []) or []:
        if not is_missing(b.get("purpose")):
            out[f"예산.{b.get('item', '?')}"] = str(b["purpose"])
    return out


def dangerous_expression_scanner(data: dict) -> list:
    """입력 텍스트에서 위험 표현 검출 + 대체 표현 제안."""
    terms = load_danger_terms()
    hits = []
    for src, text in _collect_texts(data).items():
        found_spans = []
        for t in terms:
            pos = text.find(t)
            if pos < 0:
                continue
            # 더 긴 표현이 이미 잡은 구간과 겹치면 생략 (완벽히 해결 > 완벽)
            if any(s <= pos < e for s, e in found_spans):
                continue
            found_spans.append((pos, pos + len(t)))
            rep = next((r for k, r in DANGER_REPLACEMENTS if k in t), "replacement_words.md 참조")
            hits.append({"source": src, "term": t, "snippet": text[:90], "replacement": rep})
    return hits


# ------------------------------------------------------------- notice analyze

SECTION_HINTS = {
    "purpose": ["목적", "취지"],
    "eligibility": ["신청자격", "지원대상", "신청 자격"],
    "exclusions": ["지원제외", "제외대상", "신청제외", "지원 제외", "참여제한"],
    "documents": ["제출서류", "제출 서류", "필수서류", "신청서류"],
    "budget": ["지원금", "지원금액", "지원규모", "사업비"],
    "scoring": ["평가항목", "심사기준", "배점", "평가기준"],
}


def notice_analyzer(notice: dict) -> dict:
    raw = notice.get("raw_text") or ""
    raw_ok = not is_missing(notice.get("raw_text"))
    needs, fields, guessed = [], {}, {}

    def find_lines(hints, limit=3):
        if not raw_ok:
            return []
        out = []
        for ln in raw.splitlines():
            s = ln.strip()
            # 키워드가 있어도 '미확보·유실·없음'을 말하는 줄은 정보가 아니다
            if any(bad in s for bad in ("미확보", "유실", "해당 없음", "추후 공지")):
                continue
            if any(h in s for h in hints) and len(s) > 3:
                out.append(s[:140])
                if len(out) >= limit:
                    break
        return out

    for key, label in [
        ("purpose", "공고 목적"), ("eligibility", "신청자격"), ("exclusions", "지원제외"),
        ("execution_period", "수행기간"), ("apply_deadline", "접수 마감"),
    ]:
        v = notice.get(key)
        if not is_missing(v):
            fields[label] = str(v)
        else:
            g = find_lines(SECTION_HINTS.get(key, [label]))
            if g:
                fields[label] = "(원문 추정) " + " / ".join(g)
                guessed[label] = g
            else:
                fields[label] = "[확인 필요]"
                needs.append(f"공고: {label} 미확보")

    docs = find_lines(SECTION_HINTS["documents"])
    fields["제출서류"] = ("(원문 추정) " + " / ".join(docs)) if docs else "[확인 필요]"
    if not docs:
        needs.append("공고: 제출서류 미확인")

    scoring = notice.get("scoring") or []
    if not scoring:
        needs.append("공고: 심사표·배점 미확보 — 내부 기준(evaluation_rubric.md)으로 대체")
    top = max(scoring, key=lambda s: s.get("points", 0)) if scoring else None
    if not raw_ok:
        needs.insert(0, "공고문 원문 없음 — 전 판정 [확인 필요] 모드, LOCK 금지")
    return {"raw_ok": raw_ok, "fields": fields, "guessed": guessed,
            "scoring": scoring, "top_item": top, "needs": needs}


# ---------------------------------------------------------------- risk check

def applicant_risk_checker(applicant: dict) -> dict:
    rows, blockers, needs = [], [], []

    def truthy(v):
        return v is True or v in ("있음", "true", "True", "yes", "y")

    def falsy(v):
        return v is False or v in ("없음", "false", "False", "no", "n")

    for key, label, stop_msg in [
        ("tax_arrears", "세금 체납", "체납 — 접수 요건 미달 가능"),
        ("duplicate_grant_history", "중복수혜", "동일사업 중복수혜"),
    ]:
        v = applicant.get(key)
        if truthy(v):
            blockers.append(stop_msg)
            rows.append((label, fmt(v), "BLOCKED — 탈락급", "high"))
        elif falsy(v):
            rows.append((label, "없음(신고)", "이상 없음 — 서류로 재확인 권장", "ok"))
        else:
            rows.append((label, fmt(v), "[확인 필요] — 서류 확인 전 확정 금지", "warn"))
            needs.append(f"자격: {label} 미확인")

    for key, label, hint in [
        ("industry_code", "업종코드", "공고 제외 업종과 대조"),
        ("biz_years", "업력", "공고 자격 기준과 대조"),
        ("biz_type", "사업자 형태", "지원대상 정의와 대조"),
        ("closed_biz_history", "폐업 이력", "재창업 요건 확인"),
    ]:
        v = applicant.get(key)
        if is_missing(v):
            rows.append((label, "[확인 필요]", hint, "warn"))
            needs.append(f"자격: {label} 미확보")
        else:
            rows.append((label, fmt(v), f"입력됨 — {hint} (사람 대조)", "ok"))

    return {"rows": rows, "blockers": blockers, "needs": needs}


# -------------------------------------------------------------- idea evaluate

MEASURABLE_PAT = re.compile(r"\d|시간|주당|월 |건수|비용|원가|오류|불량|반품|재작업|%")
STOPWORDS = set("및 등 있는 하는 위한 대한 통해 통한 기반 관련 지원 사업 시스템 서비스".split())


def idea_evaluator(data: dict, notice_res: dict) -> dict:
    notice = data.get("notice", {}) or {}
    corpus = (notice.get("raw_text") or "") + " " + (notice.get("purpose") or "")
    corpus_ok = notice_res["raw_ok"] or not is_missing(notice.get("purpose"))
    items = []
    for i in data.get("ideas", []) or []:
        scores, reasons = {}, []
        text = f"{i.get('name', '')} {i.get('problem', '')} {i.get('target', '')}"

        # 1. 공고 적합성 — 어휘 겹침 (원문 없으면 판정하지 않음)
        if corpus_ok:
            toks = {t for t in re.split(r"[\s,.·/()\[\]~·]+", text) if len(t) >= 2 and t not in STOPWORDS}
            overlap = sum(1 for t in toks if t in corpus)
            scores["공고 적합성"] = 5 if overlap >= 6 else 4 if overlap >= 4 else 3 if overlap >= 2 else 2
            reasons.append(f"공고문 어휘 겹침 {overlap}개 (기계 추정 — AI·사람 재확인)")
        else:
            scores["공고 적합성"] = None
            reasons.append("공고 원문 없음 → 적합성 판정 불가 [확인 필요]")

        # 2. 문제 명확성 — 측정 표현 유무
        m = len(set(MEASURABLE_PAT.findall(i.get("problem") or "")))
        scores["문제 명확성"] = 5 if m >= 3 else 4 if m == 2 else 3 if m == 1 else 2
        if m == 0:
            reasons.append("문제에 수치·측정 표현 없음 — 시간/비용/오류로 구체화 필요")

        # 3. 실행 가능성 — 산출물·리스크 인식
        outs = i.get("outputs") or []
        scores["실행 가능성"] = min(5, 2 + len(outs) + (1 if i.get("risks") else 0))
        if not outs:
            reasons.append("산출물 미정의 — 수행기간 내 남는 것이 없어 보임")

        # 4. 증빙 가능성
        eo = len(i.get("evidence_owned") or [])
        scores["증빙 가능성"] = 5 if eo >= 3 else 4 if eo == 2 else 3 if eo == 1 else 1
        if eo == 0:
            reasons.append("확보 증빙 0건 — 관련 주장 전부 단정 금지")

        # 5. 예산 적합성
        scores["예산 적합성"] = 3 if not is_missing(i.get("budget_estimate")) else 2
        if is_missing(i.get("budget_estimate")):
            reasons.append("예산 규모 미기재")

        # 6. 발표 방어
        d = (0 if is_missing(i.get("target")) else 1) + (1 if m >= 1 else 0) + (1 if eo >= 1 else 0)
        scores["발표 방어"] = 2 + d
        if is_missing(i.get("target")):
            reasons.append("고객·수혜자 불명확 — WHY 3종 방어 취약")

        vals = [v for v in scores.values() if v is not None]
        total, mx = sum(vals), len(vals) * 5
        fatal = scores["공고 적합성"] is not None and scores["공고 적합성"] <= 2
        ratio = total / mx if mx else 0
        if fatal or ratio < 0.45:
            verdict = "탈락 후보"
        elif ratio >= 0.68 and eo >= 1:
            verdict = "추천 후보"
        else:
            verdict = "보류"
        items.append({"id": i.get("id"), "name": i.get("name") or "(이름 없음)",
                      "scores": scores, "total": total, "max": mx,
                      "verdict": verdict, "reasons": reasons})

    pool = [r for r in items if r["verdict"] == "추천 후보"] or [r for r in items if r["verdict"] == "보류"]
    rec = max(pool, key=lambda r: r["total"]) if pool else None
    return {"items": items, "recommend": rec,
            "note": "규칙 기반 예비 채점 — AI 10축 채점과 사람 확정 전 참고용"}


# ----------------------------------------------------------------- budget

BUDGET_FLAGS = [
    ("외주", "외주 의존으로 보일 위험 — 신청자 직접 수행 범위 병기"),
    ("구독", "구독료 — 공고 허용 여부 확인 필요"),
    ("장비", "단순 구매성 위험 — 산출물 연결 필수"),
    ("구매", "단순 구매성 위험 — 산출물 연결 필수"),
    ("인건비", "기존 인건비는 지원제외인 공고가 많음 [확인 필요]"),
    ("임차", "임차료는 지원제외인 공고가 많음 [확인 필요]"),
]


def budget_risk_checker(data: dict) -> dict:
    plan = data.get("budget_plan") or []
    rows, needs = [], []
    if not plan:
        needs.append("예산 계획 미입력 — 예산 적정성 판정 불가, 예산표 작성 전 견적 확보 필요")
    for b in plan:
        item = b.get("item") or "(항목 없음)"
        blob = f"{item} {b.get('purpose') or ''}"
        flags = [msg for kw, msg in BUDGET_FLAGS if kw in blob]
        if is_missing(b.get("output")):
            flags.append("산출물 연결 없음 — '이 돈을 쓰면 뭐가 남는가' 불명")
        quote_needed = is_missing(b.get("amount")) or any(k in item for k in ("개발", "구축", "제작", "도입"))
        if quote_needed:
            needs.append(f"예산 '{item}': 견적서(또는 산정 근거) 필요")
        rows.append({"item": item, "amount": fmt(b.get("amount")), "purpose": fmt(b.get("purpose")),
                     "output": fmt(b.get("output")), "flags": flags, "quote_needed": quote_needed})
    return {"rows": rows, "needs": needs}


# ------------------------------------------------------------------- lock

def lock_engine(data, notice_res, risk_res, idea_res, budget_res, danger_hits) -> dict:
    ap = data.get("approvals") or {}
    reasons = []
    if not notice_res["raw_ok"]:
        reasons.append("공고문 원문 없음 — 실전 판정 근거 부재")
    if not (data.get("ideas") or []):
        reasons.append("아이디어 후보 미입력 (0단계) — applicant_input_form 작성 필요")
    reasons += [f"탈락급 리스크: {b}" for b in risk_res["blockers"]]
    if ap.get("eligibility_confirmed") is not True:
        reasons.append("자격 3종(중복수혜·체납·업종코드) 사람 확인 기록 없음")
    sel = data.get("selected_idea_id")
    if not sel or ap.get("idea_selected") is not True:
        reasons.append("최종 아이디어 사람 미확정 (selected_idea_id + approvals.idea_selected)")
    if ap.get("budget_confirmed") is not True:
        reasons.append("예산 미확정 (견적 기반 사람 확인 필요)")
    if danger_hits:
        reasons.append(f"위험 표현 {len(danger_hits)}건 미해소")
    sel_input = next((i for i in data.get("ideas", []) if i.get("id") == sel), None)
    if sel and sel_input is not None and not (sel_input.get("evidence_owned") or []):
        reasons.append("선정 아이디어의 확보 증빙 0건")
    sel_item = next((r for r in idea_res["items"] if r["id"] == sel), None) if sel else None
    status = "REVIEWED" if not reasons else "DRAFT"
    return {"status": status, "can_lock": not reasons, "block_reasons": reasons,
            "selected": sel_item, "recommend": idea_res["recommend"],
            "next_conditions": "위 불가 사유 전부 해소 → 사람이 06_locks/LOCK_STATUS.md에 LOCKED 기재"}


# ---------------------------------------------------- title / summary 후보

def title_generator(idea: dict, applicant: dict) -> list:
    tgt = idea.get("target") or applicant.get("industry") or "현장"
    prob = re.sub(r"[.。]$", "", (idea.get("problem") or "반복 수작업 부담"))[:24]
    name = idea.get("name") or "자동화 도구"
    out = (idea.get("outputs") or ["결과물"])[0]
    return [
        f"{tgt}의 {prob} 문제를 줄이는 {name} 구축",
        f"{tgt}을 위한 {name} 구축 및 시범운영",
        f"{prob} 완화를 위한 {name} 기반 {out} 구축",
        f"{tgt}의 업무 부담을 줄이는 {name} 도입·검증 과제",
        f"{name} 구축으로 {tgt}의 {prob}을 개선하는 디지털 전환 과제",
    ]


def summary_generator(idea: dict) -> list:
    name = idea.get("name") or "자동화 도구"
    tgt = idea.get("target") or "현장"
    outs = ", ".join((idea.get("outputs") or ["산출물"])[:2])
    return [
        f"{tgt}의 반복 업무를 {name}(으)로 반자동화해 처리 시간을 [실측치] 대비 단계적으로 줄이는 과제",
        f"입력자료를 넣으면 {outs}이(가) 생성되고 신청자가 검수 후 확정하는 반자동 시스템 구축",
        f"{tgt}의 수작업 오류 위험을 낮추고 처리 흐름을 표준화하는 {name} 구축·검증",
        f"수행기간 내 {outs}을(를) 완성하고 도입 전후 효과를 실측으로 비교하는 과제",
        f"{name}을(를) 구축해 [실측치] 기준 개선 목표를 검증하는 디지털 전환 시범 과제",
    ]


# --------------------------------------------------------- scoring strategy

STRATEGY_HINTS = [
    ("성장", "효율화에서 멈추지 말고 '사업모델이 어떻게 커지는가'(신상품·재구매·매출 구조 변화)로 연결하라"),
    ("시장", "고객이 누구고 경쟁 대비 무엇이 다르며 왜 지속되는지 — 매출 추세 증빙과 함께"),
    ("적합", "적용 지점을 운영 프로세스 단계로 특정하고, 도입 필요성은 실측 수치로 증명하라"),
    ("필요", "문제를 시간·비용·오류의 실측 수치로 구체화하라 (감성 서사 금지)"),
    ("역량", "대표자 검수형 실행 구조 + 관련 경험·기존 자원을 증빙과 연결하라"),
    ("실행", "기간 내 범위를 좁게 한정하고 월 단위 일정·단계별 산출물·검증 방법을 제시하라"),
    ("계획", "월 단위 일정표 + 단계별 산출물 + 위험 시 보완계획"),
    ("예산", "항목→목적→산출물→성과 연결표와 산정 근거(견적) 없이는 쓰지 마라"),
    ("효과", "성과목표는 측정 방법과 함께 — 기준치 실측 없는 목표 수치는 위험"),
]


def scoring_strategy_engine(notice_res: dict) -> dict:
    """배점표 → 배점군 분석 + 항목별 공략 전략 (규칙 기반)."""
    scoring = notice_res["scoring"] or INTERNAL_SCORING
    internal = not notice_res["scoring"]
    groups = {}
    for s in scoring:
        name = s.get("item") or "?"
        # "성장가능성 — 사업모델 개선" 처럼 구분자가 있으면 앞부분(평가군)으로 묶는다
        group = re.split(r"\s*[—–:]\s*|\s+-\s+", name)[0].strip() or name
        groups[group] = groups.get(group, 0) + int(s.get("points", 0) or 0)
    total = sum(groups.values())
    rows = []
    for name, pts in sorted(groups.items(), key=lambda kv: -kv[1]):
        share = round(pts / total * 100) if total else 0
        hint = next((h for k, h in STRATEGY_HINTS if k in name),
                    "심사위원이 점수 줄 근거(수치·증빙)를 이 항목에 직접 배치하라")
        rows.append({"item": name, "points": pts, "share": share, "hint": hint})
    top = rows[0] if rows else None
    return {"rows": rows, "top": top, "total": total, "internal": internal,
            "note": "배점 비중대로 분량·증빙을 배치하라. 최고 배점 항목이 본문의 중심 서사다."
                    + (" [확인 필요 — 실제 심사표 미입력, 내부 기준 대체]" if internal else "")}


# ------------------------------------------------- applicant form generator

EXCLUSION_CHECKS = [
    "국세 체납 (규제 중)", "지방세 체납 (규제 중)",
    "금융기관 채무불이행·부도·법정관리 등", "정부지원사업 참여 제한·제재 조치 중",
    "사업자등록 휴·폐업 상태", "체불사업주 명단 포함", "비영리 사업자·단체·조합 해당",
    "정책자금·공고상 지원제외 업종 해당 가능성",
]


def applicant_form_generator(data: dict, notice_res: dict, strategy: dict) -> str:
    """공고 기준으로 신청자가 채울 질문지 Markdown 생성 (0단계용)."""
    n = data.get("notice", {}) or {}
    deadline = n.get("apply_deadline")
    top = strategy["top"]
    growth_q = ""
    if top:
        growth_q = (f"| 성장 연결: 이게 되면 사업이 어떻게 커지는가 — 최고 배점 "
                    f"'{top['item']}'({top['points']}점) 대응 | |\n")
    excl = "\n".join(f"| {i+1} | {c} | 없음 / 있음 / 미확인 | |" for i, c in enumerate(EXCLUSION_CHECKS))
    idea_block = ("| 질문 | 답변 |\n|---|---|\n"
                  "| 이름 (한 줄) | |\n"
                  "| 문제점: 어떤 업무가 왜 힘든가 (시간·오류·기회손실, 아는 만큼 수치로) | |\n"
                  "| 해결책: AI·도구가 내 운영 프로세스의 어느 단계에 어떻게 들어가는가 | |\n"
                  "| 산출물: 사업이 끝났을 때 손에 남는 것 | |\n"
                  + growth_q +
                  "| 대표자 검수 지점: 결과물을 내가 어디서 확인·확정하는가 | |")
    self_pay = (n.get("budget", {}) or {}).get("self_pay_ratio")
    return f"""# applicant_input_form.md — 신청자 입력 폼 ({data.get('project_name', '')})

작성 규칙: 모르는 값은 지어내지 말고 `미확인`이라고 써라. 공장이 [확인 필요]로 추적한다.
이 폼이 채워지기 전에는 아이디어 LOCK·제출 판정을 하지 않는다.

## 0. 접수 상태{f' (마감: {deadline})' if not is_missing(deadline) else ' [마감일 확인 필요]'}

- [ ] 이미 접수함 (접수번호: ) / [ ] 접수 예정 / [ ] 마감 경과 → 차기 공고 대비로 전환

## 1. 기본 정보

| 질문 | 답변 |
|---|---|
| 상호 / 대표자명 | |
| 사업자 형태 (개인/법인, 공동대표 여부) | |
| 개업일(사업자등록증 기준) / 업력 | |
| 업종명 / 업종코드 | |
| 주 사업 내용 (2~3문장) | |
| 판매·운영 채널 | |
| 상시근로자 수 | |

## 2. 결격 사유 체크 (하나라도 '있음'이면 즉시 STOP 보고)

| # | 항목 | 해당 여부 | 확인 서류 |
|---|---|---|---|
{excl}

### 2-9. 동시수행·중복수혜 — 현재 수행 중인 정부지원사업 전부 (없으면 "없음")

- 사업명 / 주관기관 / 협약기간:

공고상 지원제외 조항 원문: {fmt(n.get('exclusions'))}

## 3. 아이디어 후보 (1~3개)

### 후보 1

{idea_block}

### 후보 2 (선택 — 후보 1과 동일 질문)

### 후보 3 (선택)

## 4. 현장 적용·실측 데이터

| 질문 | 답변 |
|---|---|
| 내 운영 프로세스를 단계로 쓰면 (예: 주문 확인→제작→포장→발송→안내) | |
| 가장 시간이 드는 단계와 실측/추정 시간 (실측이면 기록 방법) | |
| 반복 오류가 나는 단계와 최근 사례 | |
| 실측 기록 보유 여부 (없으면 이번 주부터 기록 시작 가능한가) | |
| 고객 개인정보를 다루는 단계 (보안성 답변 재료) | |

## 5. 예산·자부담 확보 계획{f' (자부담 {self_pay} 이상)' if not is_missing(self_pay) else ''}

| 질문 | 답변 |
|---|---|
| 희망 총사업비 규모 | |
| 자부담을 현금으로 부담 가능한가 (금액) | |
| 쓰고 싶은 예산 항목 (공고 허용 항목 기준) | |
| 견적을 받을 수 있는 업체·전문가 | |
| 친족·본인 현/전 재직 기업과 거래 계획 (있으면 집행 불가) | |

## 6. 확보 가능한 증빙자료

- [ ] 사업자등록증 / [ ] 납세증명(국세·지방세) / [ ] 매출·판매 내역
- [ ] 작업 과정 사진 / [ ] 주문서·장부 샘플 / [ ] 고객 후기
- [ ] 작업시간 실측 기록 / [ ] 견적서 / [ ] 기타:

---
작성 후: 앱의 "신청자·아이디어 입력" 화면에 옮겨 적거나, 이 파일을 채워 다음 AI 세션에 전달.
"""


# ------------------------------------------------------------- judge review

INTERNAL_SCORING = [
    {"item": "문제 인식·필요성", "points": 20}, {"item": "해결방안·차별성", "points": 20},
    {"item": "실행계획·실현 가능성", "points": 25}, {"item": "예산 적정성", "points": 15},
    {"item": "신청자 역량·증빙", "points": 20},
]
AXIS_MAP = [
    ("필요", "문제 명확성"), ("이해", "문제 명확성"), ("문제", "문제 명확성"),
    ("실행", "실행 가능성"), ("실현", "실행 가능성"), ("계획", "실행 가능성"), ("해결", "실행 가능성"),
    ("성과", "문제 명확성"), ("효과", "문제 명확성"),
    ("예산", "예산 적합성"), ("사업비", "예산 적합성"),
    ("역량", "증빙 가능성"), ("증빙", "증빙 가능성"),
    ("차별", "발표 방어"), ("적합", "공고 적합성"), ("목적", "공고 적합성"),
]


def judge_review_engine(data, notice_res, risk_res, idea_res, budget_res, danger_hits) -> dict:
    scoring = notice_res["scoring"] or INTERNAL_SCORING
    internal_used = not notice_res["scoring"]
    sel_id = data.get("selected_idea_id")
    target = (next((r for r in idea_res["items"] if r["id"] == sel_id), None)
              or idea_res["recommend"])
    rows, total, maxp, deductions = [], 0, 0, []
    for s in scoring:
        pts = int(s.get("points", 0) or 0)
        maxp += pts
        axis = next((a for k, a in AXIS_MAP if k in (s.get("item") or "")), None)
        if target is None:
            est, why = 0, ["평가할 후보 없음"]
        else:
            axis_score = target["scores"].get(axis) if axis else None
            ratio = (axis_score / 5) if axis_score else 0.5
            est = round(pts * min(ratio, 0.9))  # 규칙 기반 상한 90% — 나머지는 증빙·사람 몫
            why = [] if axis_score else ["대응 축 판정 불가 → 중간값 가정 [확인 필요]"]
        if "예산" in (s.get("item") or "") and budget_res["needs"]:
            pen = round(pts * 0.35)
            est = max(0, est - pen)
            why.append(f"예산 근거 부족 -{pen}")
        if not notice_res["raw_ok"]:
            pen = round(pts * 0.2)
            est = max(0, est - pen)
            why.append(f"공고 원문 없음 -{pen}")
        rows.append({"item": s.get("item"), "points": pts, "est": est,
                     "why": "; ".join(why) if why else "-"})
        total += est
        deductions += why
    if danger_hits:
        deductions.append(f"위험 표현 {len(danger_hits)}건 (감점·신뢰 하락 요인)")
    pct = round(total / maxp * 100) if maxp else 0
    if not idea_res["items"]:
        verdict = "판정 불가 — 0단계: 신청자·아이디어 미입력 [확인 필요]"
    elif risk_res["blockers"]:
        verdict = "제출 불가 — 탈락급 리스크 해소 전"
    elif not notice_res["raw_ok"]:
        verdict = "제출 불가 — 공고 원문 확인 전 실전 판정 금지 [확인 필요]"
    elif pct >= 80 and not danger_hits and not budget_res["needs"]:
        verdict = "제출 가능 — 단, 사람 최종 확인 후"
    else:
        verdict = "보완 후 가능"
    return {"rows": rows, "total": total, "max": maxp, "pct": pct,
            "verdict": verdict, "deductions": sorted(set(deductions)),
            "internal_scoring_used": internal_used, "target": target}


# -------------------------------------------------------------------- Q&A

ATTACK_QUESTIONS = [
    "왜 이 아이템인가?", "왜 지금 필요한가?", "왜 신청자가 해야 하는가?",
    "기존 방식과 무엇이 다른가?", "수행기간 안에 가능한가?", "예산이 왜 필요한가?",
    "단순 구매나 외주 의존 아닌가?", "고객 또는 수혜자는 어떻게 확보할 것인가?",
    "실패하면 어떻게 보완할 것인가?", "공고 목적과 어떻게 맞는가?",
]

SAFE_ANSWER = ("현재 단계에서는 제출한 수행범위 안에서 먼저 검증하고, "
               "결과를 바탕으로 다음 단계에서 보완하겠습니다.")


def qna_generator(data, notice_res, idea_res, budget_res) -> list:
    sel = (next((r for r in idea_res["items"] if r["id"] == data.get("selected_idea_id")), None)
           or idea_res["recommend"])
    src = None
    if sel:
        src = next((i for i in data.get("ideas", []) if i.get("id") == sel["id"]), None)
    eo = len((src or {}).get("evidence_owned") or [])
    m = len(MEASURABLE_PAT.findall((src or {}).get("problem") or ""))
    out = []
    for q in ATTACK_QUESTIONS:
        status, note = "발화 가능", ""
        if "예산" in q or "구매" in q:
            if budget_res["needs"]:
                status, note = "발화 금지", "견적서·산정 근거 확보 전 답변 금지"
        elif "다른가" in q:
            status, note = "증빙 필요", "기존 대안 비교표 작성 후 발화"
        elif "아이템" in q or "지금" in q:
            if m == 0:
                status, note = "증빙 필요", "문제 수치(실측) 확보 후 발화"
        elif "공고 목적" in q and not notice_res["raw_ok"]:
            status, note = "발화 금지", "공고 원문 확인 전 답변 불가"
        if sel is None:
            status, note = "발화 금지", "선정 후보 없음"
        if eo == 0 and status == "발화 가능":
            status, note = "증빙 필요", "확보 증빙 0건 — 증빙 언급 답변 불가"
        out.append({"question": q, "status": status, "note": note,
                    "fallback": SAFE_ANSWER})
    return out


# ------------------------------------------------------------- revision plan

def revision_planner(notice_res, risk_res, idea_res, lock_res, budget_res, danger_hits) -> dict:
    p1, p2, p3, quarantine = [], [], [], []
    if not notice_res["raw_ok"]:
        p1.append("공고문 원문 확보 — 모든 판정의 전제 (대체 불가)")
    p1 += [f"탈락급 해소: {b}" for b in risk_res["blockers"]]
    p1 += [n for n in risk_res["needs"] if "중복수혜" in n or "체납" in n]
    for h in danger_hits:
        p1.append(f"위험 표현 수정: '{h['term']}' ({h['source']}) → {h['replacement']}")
    p1 += [n for n in budget_res["needs"] if "견적" in n]
    for it in idea_res["items"]:
        if it["verdict"] != "탈락 후보":
            for r in it["reasons"]:
                if "증빙 0건" in r or "수치" in r:
                    p2.append(f"{it['id']}({it['name']}): {r}")
    p2 += [n for n in notice_res["needs"] if "심사표" in n]
    p3 += [n for n in risk_res["needs"] if n not in p1]
    for it in idea_res["items"]:
        if it["verdict"] == "탈락 후보":
            quarantine.append(f"{it['id']}({it['name']}) — 본문 혼입 금지, expansion_ideas 또는 타 공고 후보로 보존")
    return {"p1": p1, "p2": p2, "p3": p3, "quarantine": quarantine}


# --------------------------------------------- 17단계 파이프라인 상태 추적

PIPELINE_STAGES = [
    (0, "기준자료 확인"), (1, "프로젝트 분리"), (2, "자격·리스크 검토"),
    (3, "아이디어 후보 정리"), (4, "심사표·배점 분석"), (5, "아이디어 평가·선정"),
    (6, "핵심 프레임 LOCK"), (7, "작성전략 수립"), (8, "본문 구조 작성"),
    (9, "증빙자료 연결"), (10, "예산표 작성"), (11, "페이지·글자수 조정"),
    (12, "위험 표현 제거"), (13, "최종 제출본 정리"), (14, "발표자료 제작"),
    (15, "발표 대본 제작"), (16, "발표연습기 적용"),
]


def pipeline_tracker(data: dict, res: dict) -> list:
    """각 단계 상태: done(완료) / partial(진행 중) / todo(대기) / blocked(잠김) / human(사람 몫)."""
    ap = data.get("approvals") or {}
    ideas = data.get("ideas") or []
    doc = res.get("document", {})
    pres = res.get("presentation", {})
    draft_ok = doc.get("draft", {}).get("ready", False)
    deck_ok = pres.get("deck", {}).get("ready", False)
    n = res["notice"]
    st = {}
    st[0] = ("done", "공고 원문 확보") if n["raw_ok"] else ("partial", "공고 원문 미확보 — 판정 제한 모드")
    st[1] = ("done", "프로젝트 폴더 분리됨")
    if res["risk"]["blockers"]:
        st[2] = ("blocked", f"탈락급 {len(res['risk']['blockers'])}건")
    elif ap.get("eligibility_confirmed") is True:
        st[2] = ("done", "자격 서류 확인 완료 (사람 승인)")
    else:
        st[2] = ("partial", "리스크 검토됨 — 서류 확인·승인 대기")
    st[3] = ("done", f"후보 {len(ideas)}개") if ideas else ("todo", "0단계 — 신청자·아이디어 입력 대기")
    st[4] = ("done", "공고 심사표 기준") if n["scoring"] else ("partial", "심사표 미입력 — 내부 기준 대체")
    if data.get("selected_idea_id") and ap.get("idea_selected") is True:
        st[5] = ("done", f"선정: {data['selected_idea_id']} (사람 확정)")
    elif res["ideas"].get("recommend"):
        st[5] = ("partial", f"기계 추천: {res['ideas']['recommend']['id']} — 사람 확정 대기")
    else:
        st[5] = ("todo", "평가할 후보 없음")
    st[6] = ("done", "LOCK 조건 충족 (REVIEWED)") if res["lock"]["can_lock"] else \
            ("blocked", f"불가 사유 {len(res['lock']['block_reasons'])}건")
    st[7] = ("done", "작성전략표 생성됨") if doc.get("writing_strategy") else ("todo", "")
    st[8] = ("done", "본문 초안 6절 생성 (DRAFT)") if draft_ok else \
            ("todo", doc.get("draft", {}).get("reason", "아이디어 선정 후 생성"))
    gaps = len(doc.get("evidence_link", {}).get("gaps", []))
    st[9] = ("done", "주장-증빙 연결 완료") if draft_ok and gaps == 0 else \
            ("partial", f"증빙 공백 {gaps}건") if draft_ok else ("todo", "초안 이후")
    st[10] = ("done", "연결형 예산표 생성") if doc.get("budget_table", {}).get("ready") else \
             ("todo", "예산 계획 입력 필요")
    st[11] = ("human", "제출양식 대조·압축은 사람 몫 (분량 점검표 제공)") if draft_ok else ("todo", "초안 이후")
    sanitized = len(doc.get("draft", {}).get("sanitized", []))
    st[12] = (("done", "위험 표현 0건") if not res["danger"] and sanitized == 0 else
              ("partial", f"입력 잔존 {len(res['danger'])}건 · 초안 자동치환 {sanitized}건")) if draft_ok \
             else ("todo", "초안 이후")
    fc = doc.get("final_check", {})
    st[13] = ("human", fc.get("verdict", "")) if draft_ok else ("todo", "초안 이후")
    st[14] = ("done", "슬라이드 11장 + PPTX 생성") if deck_ok else \
             ("todo", pres.get("deck", {}).get("reason", "선정 이후"))
    st[15] = ("done", "대본 3종 생성 (풀·압축·쉬운말)") if pres.get("script", {}).get("ready") else ("todo", "")
    st[16] = ("partial", "연습기 사용 가능 — 훈련은 발표자 몫") if deck_ok else ("todo", "발표자료 이후")
    return [{"no": no, "name": name, "status": st.get(no, ("todo", ""))[0],
             "note": st.get(no, ("todo", ""))[1]} for no, name in PIPELINE_STAGES]


# ------------------------------------------------------------ orchestrator

def _safe(errors: list, name: str, fn, default):
    """엔진 1개가 죽어도 전체 분석은 계속된다 (M6: 실패 격리)."""
    try:
        return fn()
    except Exception as e:
        errors.append(f"{name}: {type(e).__name__}: {e}")
        return default


def analyze_all(data: dict) -> dict:
    errors: list = []
    notice_res = _safe(errors, "notice", lambda: notice_analyzer(data.get("notice", {}) or {}),
                       {"raw_ok": False, "fields": {}, "guessed": {}, "scoring": [], "top_item": None,
                        "needs": ["공고 분석 엔진 오류 — 입력 확인"]})
    risk_res = _safe(errors, "risk", lambda: applicant_risk_checker(data.get("applicant", {}) or {}),
                     {"rows": [], "blockers": [], "needs": []})
    danger_hits = _safe(errors, "danger", lambda: dangerous_expression_scanner(data), [])
    idea_res = _safe(errors, "ideas", lambda: idea_evaluator(data, notice_res),
                     {"items": [], "recommend": None, "note": "아이디어 평가 엔진 오류"})
    budget_res = _safe(errors, "budget", lambda: budget_risk_checker(data), {"rows": [], "needs": []})
    lock_res = _safe(errors, "lock",
                     lambda: lock_engine(data, notice_res, risk_res, idea_res, budget_res, danger_hits),
                     {"status": "DRAFT", "can_lock": False, "block_reasons": ["LOCK 엔진 오류"],
                      "selected": None, "recommend": None, "next_conditions": ""})
    judge_res = _safe(errors, "judge",
                      lambda: judge_review_engine(data, notice_res, risk_res, idea_res, budget_res, danger_hits),
                      {"rows": [], "total": 0, "max": 100, "pct": 0, "verdict": "판정 불가 — 엔진 오류",
                       "deductions": [], "internal_scoring_used": True, "target": None})
    qna = _safe(errors, "qna", lambda: qna_generator(data, notice_res, idea_res, budget_res), [])
    revision = _safe(errors, "revision",
                     lambda: revision_planner(notice_res, risk_res, idea_res, lock_res, budget_res, danger_hits),
                     {"p1": [], "p2": [], "p3": [], "quarantine": []})
    strategy = _safe(errors, "strategy", lambda: scoring_strategy_engine(notice_res),
                     {"rows": [], "top": None, "total": 0, "internal": True, "note": "전략 엔진 오류"})
    # 공고 성격 분석 (목적·심사의도·선호표현·위험전략) — 로컬 규칙, AI 모드로 정밀화 가능
    from notice_parser import notice_character
    character = _safe(errors, "character",
                      lambda: notice_character((data.get("notice", {}) or {}).get("raw_text") or "",
                                               notice_res["scoring"]),
                      {"purpose_type": [], "review_intent": [], "preferred_terms": [],
                       "risky_moves": [], "note": "성격 분석 엔진 오류"})
    stage0 = not (data.get("ideas") or [])
    if stage0:
        revision["p1"].insert(0, "신청자·아이디어 정보 입력 — applicant_input_form.md 작성 (0단계)")
    pick = lock_res["selected"] or lock_res["recommend"]
    src_idea = next((i for i in data.get("ideas", []) if pick and i.get("id") == pick["id"]), None)
    titles = title_generator(src_idea, data.get("applicant", {})) if src_idea else []
    summaries = summary_generator(src_idea) if src_idea else []
    missing_evidence = _missing_evidence(data, src_idea, budget_res, notice_res)
    res = {"generated_at": date.today().isoformat(), "stage0": stage0,
           "notice": notice_res, "risk": risk_res, "danger": danger_hits,
           "ideas": idea_res, "budget": budget_res, "lock": lock_res,
           "judge": judge_res, "qna": qna, "revision": revision,
           "strategy": strategy, "character": character,
           "titles": titles, "summaries": summaries,
           "missing_evidence": missing_evidence}
    res["applicant_form_md"] = _safe(errors, "form",
                                     lambda: applicant_form_generator(data, notice_res, strategy), "")
    # 서류 라인(7~13단계) + 발표 라인(14~16단계) — 지연 임포트 (엔진 단독 테스트 가능)
    from draft_engine import build_document_line
    from present_engine import build_presentation_line
    res["document"] = _safe(errors, "document", lambda: build_document_line(data, res),
                            {"writing_strategy": {"rows": [], "page_limit": "?", "rule": ""},
                             "draft": {"ready": False, "reason": "서류 라인 엔진 오류"},
                             "evidence_link": {"rows": [], "gaps": [], "owned": [], "planned": [], "rule": ""},
                             "budget_table": {"ready": False, "reason": "오류"},
                             "length": {"page_limit": "?", "rows": [], "checks": [], "warn": None},
                             "final_check": {"rows": [], "verdict": "판정 불가 — 엔진 오류", "note": ""}})
    res["presentation"] = _safe(errors, "presentation",
                                lambda: build_presentation_line(data, res, res["document"]),
                                {"deck": {"ready": False, "reason": "발표 라인 엔진 오류"},
                                 "script": {"ready": False}, "rehearsal": None})
    res["pipeline"] = _safe(errors, "pipeline", lambda: pipeline_tracker(data, res), [])
    res["engine_errors"] = errors
    return res


def _missing_evidence(data, src_idea, budget_res, notice_res) -> list:
    rows = []
    if not notice_res["raw_ok"]:
        rows.append({"need": "공고문 원문", "why": "모든 판정의 전제", "alt": "없음 (대체 불가)", "prio": 1})
    if src_idea:
        if not (src_idea.get("evidence_owned") or []):
            rows.append({"need": "선정 아이디어 기본 증빙(사진·판매내역 등)", "why": "주장 단정 금지 해제", "alt": "-", "prio": 1})
        prob = src_idea.get("problem") or ""
        if not MEASURABLE_PAT.search(prob):
            rows.append({"need": "문제 실측 기록(작업일지 등)", "why": "필요성·성과 기준치", "alt": "최소 1주치 기록", "prio": 1})
        for ev in (src_idea.get("evidence_planned") or []):
            rows.append({"need": ev, "why": "본인 신고 예정 증빙", "alt": "-", "prio": 2})
    for n in budget_res["needs"]:
        if "견적" in n:
            rows.append({"need": n.replace("예산 ", "").split(":")[0] + " 견적서", "why": "예산 산정 근거", "alt": "시장 단가 자료(약함)", "prio": 1})
    return rows


def run_project(project: str, base: Path = BASE) -> list:
    """input.json 읽기 → 전체 분석 → 파일 15종 내보내기. 반환: 생성 파일 목록."""
    input_path = base / "01_inputs" / project / "input.json"
    data = json.loads(input_path.read_text(encoding="utf-8"))
    res = analyze_all(data)
    from export_md import export_all  # 지연 임포트 (엔진 단독 테스트 가능하게)
    return export_all(project, data, res, base)
