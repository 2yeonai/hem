#!/usr/bin/env python3
"""draft_engine.py — 서류 라인 (혜미 방식 7~13단계).

7단계  작성전략 수립      → writing_strategy_engine
8단계  본문 구조 작성      → document_draft_engine (문제→대안한계→해결→실행→성장→역량)
9단계  증빙자료 연결      → evidence_link_engine
10단계 예산표 작성        → budget_table_engine (항목→목적→산출물→근거→평가항목→성과)
11단계 페이지·글자수 조정  → length_check_engine
12단계 위험 표현 제거      → sanitize_draft (자동 치환 + 치환 기록)
13단계 최종 제출본 정리    → final_check_engine (최종 점검 질문 9종)

원칙:
- 초안은 항상 DRAFT. 모르는 값은 지어내지 않고 [확인 필요: ...]로 남긴다.
- 아이디어가 선정(또는 추천)되지 않으면 초안을 만들지 않는다 (섞임 방지).
- 생성 문장은 만들자마자 위험 표현 치환기를 통과시킨다 (12단계 내장).
"""
from __future__ import annotations

import re

from engines import (DANGER_REPLACEMENTS, MEASURABLE_PAT, fmt, is_missing,
                     load_danger_terms)


def _need(what: str) -> str:
    return f"[확인 필요: {what}]"


def pick_idea(data: dict, idea_res: dict):
    """선정 아이디어(사람 확정) 우선, 없으면 기계 추천. 없으면 None."""
    sel = data.get("selected_idea_id")
    row = (next((r for r in idea_res["items"] if r["id"] == sel), None)
           or idea_res.get("recommend"))
    if not row:
        return None, None
    src = next((i for i in data.get("ideas", []) if i.get("id") == row["id"]), None)
    return row, src


# ------------------------------------------------- 12단계: 위험 표현 치환

def sanitize_text(text: str) -> tuple:
    """위험 표현을 안전 표현으로 치환. 반환: (치환된 텍스트, 치환 기록 리스트)."""
    replaced = []
    for term in load_danger_terms():
        if term not in text:
            continue
        rep = next((r.split(" / ")[0] for k, r in DANGER_REPLACEMENTS if k in term), None)
        if rep:
            text = text.replace(term, rep)
            replaced.append({"term": term, "to": rep})
    return text, replaced


# ------------------------------------------------- 7단계: 작성전략 수립

JUDGE_EYES = [
    ("성장", "이 돈을 쓰면 사업이 실제로 커지는가 — 매출 구조 변화·재구매·신상품"),
    ("시장", "고객이 실재하고 계속 사는가 — 매출 추세·경쟁 대비 차별점"),
    ("적합", "적용 지점이 운영 프로세스의 어느 단계인지 특정되는가"),
    ("필요", "문제가 시간·비용·오류의 수치로 증명되는가"),
    ("역량", "신청자가 직접 실행·검수할 수 있어 보이는가"),
    ("실행", "수행기간 안에 끝나는 좁고 검증된 범위인가"),
    ("계획", "월 단위 일정과 단계별 산출물이 있는가"),
    ("예산", "항목마다 산출물·성과와 연결되고 산정 근거가 있는가"),
    ("효과", "성과목표가 측정 가능하고 기준치(실측)가 있는가"),
]


def writing_strategy_engine(strategy: dict, notice_res: dict, data: dict,
                            idea_src: dict | None) -> dict:
    """배점표 → 항목별 작성전략표 (7단계). 분량 비중 = 배점 비중."""
    n = data.get("notice", {}) or {}
    page_limit = (n.get("format", {}) or {}).get("page_limit")
    ev_owned = set((data.get("evidence", {}) or {}).get("owned") or [])
    if idea_src:
        ev_owned |= set(idea_src.get("evidence_owned") or [])
    rows = []
    for s in strategy["rows"]:
        eye = next((e for k, e in JUDGE_EYES if k in s["item"]),
                   "이 항목에서 점수 줄 근거가 본문에 직접 보이는가")
        ev = ", ".join(sorted(ev_owned)[:3]) if ev_owned else _need("이 항목에 붙일 증빙")
        rows.append({"item": s["item"], "points": s["points"], "share": s["share"],
                     "judge_eye": eye, "tactic": s["hint"], "evidence": ev})
    return {"rows": rows, "page_limit": fmt(page_limit),
            "rule": "배점 비중 = 분량 비중. 최고 배점 항목이 본문의 중심 서사다. "
                    "배점 낮은 항목은 짧고 명확하게 압축한다."}


# ------------------------------------------------- 8단계: 본문 구조 작성

def document_draft_engine(data: dict, idea_row: dict | None, idea_src: dict | None,
                          strategy: dict, titles: list, summaries: list) -> dict:
    """본문 초안 6절 생성. 아이디어 없으면 생성하지 않음."""
    if not idea_src:
        return {"ready": False,
                "reason": "아이디어 미선정 — 5단계(아이디어 평가·선정) 전에는 초안을 만들지 않는다 (섞임 방지)"}
    a = data.get("applicant", {}) or {}
    n = data.get("notice", {}) or {}
    problem = idea_src.get("problem") or _need("문제 서술")
    target = idea_src.get("target") or _need("고객·수혜자")
    name = idea_src.get("name") or _need("아이디어명")
    outputs = idea_src.get("outputs") or []
    period = n.get("execution_period")
    measured = bool(MEASURABLE_PAT.search(idea_src.get("problem") or ""))

    sections = []

    # 8-1. 문제정의
    body = (f"{target}은(는) 현재 {problem} 이 문제는 "
            + ("입력된 수치 기준으로 반복 손실을 만들고 있다."
               if measured else
               f"{_need('시간·비용·오류 실측 수치 — 감성 서사 금지, 최소 1주 기록')} 규모의 손실을 만들고 있다.")
            + f" 기존 방식으로는 해결되지 않아 지금 개선이 필요하다.")
    sections.append({
        "no": "1", "title": "문제정의 (필요성)", "body": body,
        "guide": ["누가 불편한가 / 어떤 문제가 반복되는가 / 어떤 손실이 생기는가 / 왜 지금인가",
                  "시간·비용·오류·품질 편차·운영 부담으로 구체화 — 감성 서사 금지"],
        "todo": [] if measured else ["문제 실측 수치 확보 (작업일지·주문 기록 등)"]})

    # 8-2. 기존 대안의 한계
    sections.append({
        "no": "2", "title": "기존 대안의 한계", "body":
            f"현재는 수작업 또는 범용 도구로 대응하고 있다. 기존 방식을 쓰는 이유가 있었음을 인정하되, "
            f"{_need('기존 방식 2~3개와 각각의 한계')} 를 비교표로 제시하고 본 과제가 해결하는 지점을 특정한다.",
        "table": {"head": ["기존 방식", "사용 이유", "한계", "본 과제의 해결 방향"],
                  "rows": [[_need("기존 방식 1"), "", "", name],
                           [_need("기존 방식 2"), "", "", ""]]},
        "guide": ["기존 대안을 무조건 비난하지 않는다 — 쓰던 이유 인정 후 남는 한계를 보여준다"],
        "todo": ["기존 방식·한계 비교표 채우기"]})

    # 8-3. 해결방안
    sol_rows = [[problem[:40], name, o, _need("기간 내 구현 범위")] for o in (outputs or [_need("산출물")])]
    sections.append({
        "no": "3", "title": "해결방안", "body":
            f"{name}을(를) {target}의 운영 프로세스에 적용한다. "
            f"결과물은 신청자(대표자)가 직접 검수·확정하는 반자동 구조로 운영해 품질과 책임을 유지한다.",
        "table": {"head": ["문제", "해결방안", "산출물", "수행기간 내 구현 범위"], "rows": sol_rows},
        "guide": ["기능·절차·산출물·운영방식으로 나눠 쓴다 — 추상어 금지",
                  "'AI가 다 한다'가 아니라 'AI 초안 생성 → 대표자 검수·확정' 구조로 쓴다"],
        "todo": [] if outputs else ["산출물 정의 — 사업이 끝났을 때 손에 남는 것"]})

    # 8-4. 실행계획
    months = _need("수행기간(개월)") if is_missing(period) else str(period)
    sections.append({
        "no": "4", "title": "실행계획", "body":
            f"수행기간({months}) 안에서 실행 범위를 한정한다. 월 단위 일정·단계별 산출물·검증 방법을 제시하고, "
            f"위험 발생 시 보완계획을 병기한다.",
        "table": {"head": ["단계", "기간", "내용", "산출물", "검증 방법"],
                  "rows": [["준비", "1개월차", "요구 정리·업체 선정·기준치 실측", "요구정의서, 실측 기록", "실측 데이터 확인"],
                           ["구축", _need("기간"), f"{name} 구축·적용", ", ".join(outputs[:2]) or _need("산출물"), "동작 확인"],
                           ["검증", "마지막 1개월", "도입 전후 비교 측정·보완", "전후 비교 리포트", "실측 비교"]]},
        "guide": ["기간 내 가능한 범위로 좁게 — 넓은 약속이 감점 1순위"],
        "todo": ["월 단위 일정 확정 (수행기간 공고 원문 대조)"]})

    # 8-5. 성장 전략 (최고 배점 항목 대응)
    top = strategy.get("top") or {}
    growth = idea_src.get("growth") or ""
    sections.append({
        "no": "5", "title": f"성장·확산 전략 (최고 배점 '{top.get('item', '성장가능성')}' 대응)",
        "body": (growth if growth else
                 f"{_need('이게 되면 사업이 어떻게 커지는가 — 신상품·재구매·매출 구조 변화')} "
                 f"현재 단계와 장기 확장을 분리해 쓴다. 이번 수행범위에서는 검증까지, "
                 f"다음 단계에서 단계적으로 확대한다."),
        "guide": ["'시간 절감'에서 멈추면 최고 배점을 못 받는다 — 사업모델 변화로 연결하라",
                  "과도한 확장 서사 금지 — 현 단계와 장기를 분리"],
        "todo": [] if growth else ["성장 연결 서사 작성 (배점 최고 항목)"]})

    # 8-6. 신청자 역량
    yrs = a.get("biz_years")
    chan = ", ".join(a.get("channels") or [])
    cap = (f"{fmt(a.get('name'))}은(는) {fmt(a.get('industry'))} 분야에서 "
           + (f"{yrs}년간 운영해 왔으며 " if not is_missing(yrs) else _need("업력") + " ")
           + (f"{chan} 채널을 직접 운영한다. " if chan else "")
           + "본 과제의 결과물은 대표자가 직접 검수·확정하는 구조로 실행하며, "
           + f"부족한 기술 역량은 {_need('외부 협력·교육 계획')}으로 보완한다.")
    sections.append({
        "no": "6", "title": "신청자 역량", "body": cap,
        "guide": ["경험·기존 자원·현장 이해도·고객 접점을 증빙과 연결", "부족한 역량은 숨기지 말고 보완 방식을 쓴다"],
        "todo": []})

    title = titles[0] if titles else _need("과제명")
    summary = summaries[0] if summaries else _need("한 줄 요약")

    # 12단계: 생성 문장 위험 표현 자동 치환
    replaced_total = []
    for s in sections:
        s["body"], rep = sanitize_text(s["body"])
        replaced_total += rep
    todos = [t for s in sections for t in s["todo"]]
    return {"ready": True, "idea_id": idea_row["id"], "title": title, "summary": summary,
            "sections": sections, "sanitized": replaced_total, "todos": todos,
            "flow": "문제 → 해결방안 → 실행계획 → 예산 → 산출물 → 성과 → 역량 → 증빙",
            "status": "DRAFT — 대괄호 [확인 필요] 전부 해소 + 사람 검수 전 제출 금지"}


# ------------------------------------------------- 9단계: 증빙자료 연결

CLAIM_EVIDENCE = [
    ("문제가 반복된다", ["작업시간 실측 기록", "주문서·장부 샘플", "작업 과정 사진"]),
    ("고객이 실재한다", ["매출·판매 내역", "고객 후기", "판매 채널 화면"]),
    ("신청자가 실행할 수 있다", ["사업자등록증", "포트폴리오", "교육 수료자료", "자격증"]),
    ("예산이 적정하다", ["견적서", "예산 산출근거", "시장 단가 자료"]),
    ("기존에 시도해 봤다", ["시제품·목업", "랜딩페이지", "상세페이지"]),
]


def evidence_link_engine(data: dict, idea_src: dict | None) -> dict:
    owned = set((data.get("evidence", {}) or {}).get("owned") or [])
    planned = set((data.get("evidence", {}) or {}).get("planned") or [])
    if idea_src:
        owned |= set(idea_src.get("evidence_owned") or [])
        planned |= set(idea_src.get("evidence_planned") or [])
    rows, gaps = [], []
    for claim, evs in CLAIM_EVIDENCE:
        have = [e for e in evs if any(e[:3] in o or o[:3] in e for o in owned)]
        plan = [e for e in evs if any(e[:3] in p or p[:3] in e for p in planned)]
        if have:
            status, use = "확보", ", ".join(have)
        elif plan:
            status, use = "예정", ", ".join(plan) + " — 본문에는 '확보 후 추진'으로만"
        else:
            status, use = "없음", "이 주장 단정 금지 — 보완계획으로 대체"
            gaps.append(f"'{claim}' 증빙 없음: {' / '.join(evs[:2])} 중 확보 필요")
        rows.append({"claim": claim, "candidates": ", ".join(evs), "status": status, "use": use})
    return {"rows": rows, "gaps": gaps, "owned": sorted(owned), "planned": sorted(planned),
            "rule": "이미지·도식에는 200~300자 설명문 — 심사위원이 해석하게 두지 않는다"}


# ------------------------------------------------- 10단계: 예산표 작성

def budget_table_engine(data: dict, strategy: dict, budget_res: dict) -> dict:
    """연결형 예산표: 항목 → 목적 → 산출물 → 근거 → 평가항목 → 기대성과."""
    plan = data.get("budget_plan") or []
    if not plan:
        return {"ready": False, "reason": "예산 계획 미입력 — 견적 확보 후 작성 (10단계)"}
    strat_items = [r["item"] for r in strategy.get("rows", [])]
    budget_axis = next((s for s in strat_items if "예산" in s), None)
    rows = []
    for b in plan:
        item = b.get("item") or "(항목 없음)"
        linked = budget_axis or (strat_items[0] if strat_items else "[확인 필요]")
        flags = next((r["flags"] for r in budget_res["rows"] if r["item"] == item), [])
        rows.append({
            "item": item, "amount": fmt(b.get("amount")), "purpose": fmt(b.get("purpose")),
            "output": fmt(b.get("output")),
            "basis": _need("견적서·산정 근거") if is_missing(b.get("amount")) or "개발" in item or "구축" in item
                     else "입력 금액 (견적 대조 필요)",
            "linked_item": linked,
            "expected": b.get("expected") or _need("이 돈을 쓰면 남는 성과"),
            "flags": flags})
    return {"ready": True, "rows": rows,
            "flow": "예산 항목 → 사용 목적 → 산출물 → 성과목표 → 평가항목 연결",
            "rule": "심사위원이 봤을 때 '이 돈을 쓰면 이 결과물이 나오겠다'가 보여야 한다"}


# ------------------------------------------------- 11단계: 분량 조정

def length_check_engine(draft: dict, data: dict, strategy: dict) -> dict:
    n = data.get("notice", {}) or {}
    page_limit = (n.get("format", {}) or {}).get("page_limit")
    checks = [
        "핵심 주장이 각 절의 첫 문장에 있는가",
        "중복 문장이 없는가", "감성 표현보다 근거가 남아 있는가",
        "표는 정리용으로만, 도식은 복잡한 구조 설명에만 쓰였는가",
        "배점 낮은 항목이 과하게 길지 않은가",
    ]
    rows = []
    if draft.get("ready"):
        total_chars = sum(len(s["body"]) for s in draft["sections"])
        shares = {r["item"]: r["share"] for r in strategy.get("rows", [])}
        for s in draft["sections"]:
            share = len(s["body"]) / total_chars * 100 if total_chars else 0
            rows.append({"section": s["title"], "chars": len(s["body"]),
                         "share": round(share), "note": ""})
        # 최고 배점 항목(성장) 절이 너무 짧으면 경고
        top = strategy.get("top")
        if top:
            growth_sec = next((r for r in rows if top["item"][:2] in r["section"]), None)
            if growth_sec and growth_sec["share"] < top["share"] * 0.5:
                growth_sec["note"] = f"최고 배점({top['points']}점) 항목인데 분량 부족 — 확대 필요"
    return {"page_limit": fmt(page_limit), "rows": rows, "checks": checks,
            "warn": None if not is_missing(page_limit) else
            "페이지 제한 미확보 — 제출양식 원문 확인 전 분량 확정 금지"}


# ------------------------------------------------- 13단계: 최종 점검

FINAL_QUESTIONS = [
    "과제명이 본문 전체와 일치하는가", "문제와 해결방안이 연결되는가",
    "예산과 산출물이 연결되는가", "성과목표가 측정 가능한가",
    "신청자가 실제로 할 수 있어 보이는가", "증빙이 본문 주장과 연결되는가",
    "과장 표현이 없는가", "공고 목적과 맞는가",
    "심사표 배점 높은 항목이 충분히 드러나는가",
]


def final_check_engine(draft: dict, judge_res: dict, danger_hits: list,
                       ev_link: dict, budget_table: dict) -> dict:
    rows = []
    auto = {
        "과장 표현이 없는가": ("통과", "위험 표현 0건") if not danger_hits and not draft.get("sanitized")
               else ("자동 치환됨" if draft.get("sanitized") else "실패",
                     f"입력 텍스트 위험 표현 {len(danger_hits)}건 잔존" if danger_hits
                     else f"초안 생성 중 {len(draft.get('sanitized', []))}건 치환 — 문맥 확인 필요"),
        "예산과 산출물이 연결되는가": ("통과", "연결형 예산표 생성됨") if budget_table.get("ready")
               else ("실패", budget_table.get("reason", "")),
        "증빙이 본문 주장과 연결되는가": ("통과", "주장-증빙 전부 연결") if not ev_link["gaps"]
               else ("보완", f"증빙 공백 {len(ev_link['gaps'])}건"),
    }
    for q in FINAL_QUESTIONS:
        if q in auto:
            status, note = auto[q]
        else:
            status, note = "사람 확인", "기계 판정 불가 — 제출 전 직접 점검"
        rows.append({"q": q, "status": status, "note": note})
    submit_ok = (draft.get("ready") and judge_res["pct"] >= 80
                 and not danger_hits and budget_table.get("ready"))
    return {"rows": rows,
            "verdict": ("최종본 후보 — 사람 확인 항목 점검 후 제출 판단" if submit_ok else
                        "제출 불가 — 예상 점수 80% 미만이거나 필수 요소 미충족"),
            "note": "이 판정은 규칙 기반이다. 최종 제출 승인(approvals.final_submission_approved)은 사람이 한다."}


# ------------------------------------------------- 서류 라인 오케스트레이터

def build_document_line(data: dict, res: dict) -> dict:
    """분석 결과(res)를 받아 7~13단계 산출물 생성."""
    idea_row, idea_src = pick_idea(data, res["ideas"])
    ws = writing_strategy_engine(res["strategy"], res["notice"], data, idea_src)
    draft = document_draft_engine(data, idea_row, idea_src, res["strategy"],
                                  res["titles"], res["summaries"])
    ev_link = evidence_link_engine(data, idea_src)
    btable = budget_table_engine(data, res["strategy"], res["budget"])
    length = length_check_engine(draft, data, res["strategy"])
    final = final_check_engine(draft, res["judge"], res["danger"], ev_link, btable)
    return {"writing_strategy": ws, "draft": draft, "evidence_link": ev_link,
            "budget_table": btable, "length": length, "final_check": final}
