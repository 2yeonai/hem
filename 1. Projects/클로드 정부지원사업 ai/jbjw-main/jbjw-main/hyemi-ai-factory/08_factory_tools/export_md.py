#!/usr/bin/env python3
"""export_md.py — 분석 결과를 파일 15종(Markdown/JSON/HANDOFF/다음 프롬프트)으로 내보내기."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

HEADER_NOTE = "⚠️ 규칙 기반 예비 판정 — AI 검수·사람 확정 전 참고용. 상태: DRAFT"


def _w(path: Path, text: str, made: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    made.append(str(path))


def export_all(project: str, data: dict, res: dict, base: Path) -> list:
    made = []
    today = date.today().isoformat()
    out = base / "04_outputs" / project
    rev = base / "05_reviews" / project
    n, r, d = res["notice"], res["risk"], res["danger"]
    ideas, bud, lock, judge = res["ideas"], res["budget"], res["lock"], res["judge"]

    # 1. 공고 요약
    rows = "\n".join(f"| {k} | {v} |" for k, v in n["fields"].items())
    sc = "\n".join(f"| {s.get('item')} | {s.get('points')} |" for s in n["scoring"]) or "| [확인 필요 — 배점표 미입력] | - |"
    _w(out / "notice_summary.md", f"""# 공고 요약: {project}

{HEADER_NOTE} / {today}

| 항목 | 내용 |
|---|---|
{rows}

## 심사표·배점 분석

| 평가항목 | 배점 |
|---|---:|
{sc}

- 배점 최고 항목: {n['top_item']['item'] + ' (' + str(n['top_item']['points']) + '점) — 분량·증빙 집중 대상' if n['top_item'] else '[확인 필요]'}
- 내부 기준 대체 여부: {'예 (실제 심사표 입수 시 재분석 필수)' if not n['scoring'] else '아니오'}

## 확인 필요

{chr(10).join('- ' + x for x in n['needs']) or '- 없음'}
""", made)

    # 1-b. 배점 전략
    st = res.get("strategy")
    if st:
        srows = "\n".join(f"| {x['item']} | {x['points']} | {x['share']}% | {x['hint']} |" for x in st["rows"])
        _w(out / "scoring_strategy.md", f"""# 배점 전략: {project}

{HEADER_NOTE} / {today}
{st['note']}

| 평가항목 | 배점 | 비중 | 공략 전략 |
|---|---:|---:|---|
{srows}

- 최고 배점 항목: **{st['top']['item'] + ' (' + str(st['top']['points']) + '점)' if st['top'] else '[확인 필요]'}** — 분량·증빙·도식을 여기에 집중
- 배점 낮은 항목은 짧고 명확하게 압축 (과분량 금지)
""", made)

    # 1-c. 신청자 입력 폼 (0단계 또는 신청자 정보 미비 시)
    if res.get("applicant_form_md") and (res.get("stage0") or not data.get("ideas")):
        _w(out / "applicant_input_form.md", res["applicant_form_md"], made)

    # 2. 자격 리스크
    rr = "\n".join(f"| {a} | {b} | {c} |" for a, b, c, _ in r["rows"])
    _w(out / "applicant_risk_check.md", f"""# 자격·지원제외 리스크: {project}

{HEADER_NOTE} / {today} / 최종 판정은 사람 확정 필수

| 항목 | 값 | 판정 |
|---|---|---|
{rr}

## 탈락급 (즉시 중단)

{chr(10).join('- **' + b + '**' for b in r['blockers']) or '- 없음'}

## 사람이 확인해야 할 것

{chr(10).join('- ' + x for x in r['needs']) or '- 없음'}
""", made)

    # 3. 아이디어 비교표
    axes = ["공고 적합성", "문제 명확성", "실행 가능성", "증빙 가능성", "예산 적합성", "발표 방어"]
    head = "| 후보 | " + " | ".join(axes) + " | 합계 | 판정 |"
    sep = "|---|" + "---:|" * (len(axes) + 1) + "---|"
    body = "\n".join(
        "| {} | {} | {}/{} | {} |".format(
            f"{it['id']} {it['name']}",
            " | ".join("?" if it["scores"][a] is None else str(it["scores"][a]) for a in axes),
            it["total"], it["max"], it["verdict"])
        for it in ideas["items"])
    reasons = "\n".join(f"- **{it['id']}**: " + " / ".join(it["reasons"]) for it in ideas["items"])
    _w(out / "idea_comparison_table.md", f"""# 아이디어 후보 비교: {project}

{HEADER_NOTE} / {today} / '?' = 판정 불가([확인 필요])

{head}
{sep}
{body}

## 후보별 감점 위험·근거

{reasons}

## 기계 추천

- {ideas['recommend']['id'] + ' ' + ideas['recommend']['name'] if ideas['recommend'] else '추천 가능 후보 없음'}
- {ideas['note']}
- **최종 선정은 사람 몫** — 앱 LOCK 화면에서 승인 기록
""", made)

    # 4. LOCK 판정 + 과제명·요약 후보
    _w(out / "selected_idea_lock.md", f"""# LOCK 판정: {project}

상태: **{lock['status']}** / {today} / LOCK 가능: {'예 — 사람이 LOCK_STATUS.md에 기재' if lock['can_lock'] else '아니오'}

## LOCK 불가 사유 ({len(lock['block_reasons'])}건)

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(lock['block_reasons'])) or '- 없음'}

## 대상 아이디어

- 사람 확정: {lock['selected']['id'] + ' ' + lock['selected']['name'] if lock['selected'] else '미확정'}
- 기계 추천: {lock['recommend']['id'] + ' ' + lock['recommend']['name'] if lock['recommend'] else '없음'}

## 과제명 후보 5 (규칙 생성 — AI·사람 다듬기 필요)

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(res['titles'])) or '- 후보 선정 후 생성됨'}

## 한 줄 요약 후보 5

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(res['summaries'])) or '- 후보 선정 후 생성됨'}

## 다음 단계 조건

{lock['next_conditions']}
""", made)

    # 5. 위험 표현
    dr = "\n".join(f"| {h['source']} | {h['term']} | {h['snippet']} | {h['replacement']} |" for h in d) or "| - | 검출 없음 | - | - |"
    _w(rev / "dangerous_expression_review.md", f"""# 위험 표현 검출: {project}

기준: 00_rules/danger_words.md / {today} / 검출 {len(d)}건

| 위치 | 표현 | 문맥 | 대체 제안 |
|---|---|---|---|
{dr}

{('**' + str(len(d)) + '건 수정 전 LOCK·제출 금지**') if d else '입력 텍스트 기준 0건 — 본문 작성 후 재스캔 필요'}
""", made)

    # 6. 예산 리스크
    br = "\n".join(
        f"| {x['item']} | {x['amount']} | {x['output']} | {'; '.join(x['flags']) or '-'} | {'필요' if x['quote_needed'] else '-'} |"
        for x in bud["rows"]) or "| (예산 계획 미입력) | - | - | 예산 판정 불가 | 필요 |"
    _w(rev / "budget_risk_review.md", f"""# 예산 리스크: {project}

{HEADER_NOTE} / {today}

| 항목 | 금액 | 산출물 연결 | 위험 | 견적서 |
|---|---|---|---|---|
{br}

## 확인 필요

{chr(10).join('- ' + x for x in bud['needs']) or '- 없음'}
""", made)

    # 7. 누락 증빙
    me = "\n".join(f"| {x['need']} | {x['why']} | {x['alt']} | {x['prio']} |" for x in res["missing_evidence"]) or "| - | - | - | - |"
    _w(rev / "missing_evidence_list.md", f"""# 누락 증빙 리스트: {project}

{today}

| 필요한 증빙 | 이유 | 대체 자료 | 우선순위 |
|---|---|---|---|
{me}
""", made)

    # 8. 심사위원 검수 + 예상 점수표
    jr = "\n".join(f"| {x['item']} | {x['points']} | {x['est']} | {x['why']} |" for x in judge["rows"])
    _w(rev / "score_estimation_table.md", f"""# 예상 점수표: {project}

{HEADER_NOTE} / {today} / {'내부 기준 대체 채점 [확인 필요]' if judge['internal_scoring_used'] else '입력된 심사표 기준'}

| 평가항목 | 배점 | 예상 | 감점 사유 |
|---|---:|---:|---|
{jr}
| **합계** | **{judge['max']}** | **{judge['total']}** ({judge['pct']}%) | |
""", made)
    _w(rev / "final_judge_review.md", f"""# 심사위원 검수(기계): {project}

{today} / 판정: **{judge['verdict']}**

## 감점·탈락 요인

{chr(10).join('- ' + x for x in judge['deductions']) or '- 없음'}

## 탈락급 리스크

{chr(10).join('- ' + b for b in r['blockers']) or '- 없음'}

## 한계 고지

이 검수는 규칙 기반 기계 검수다. 정성 검수(스토리 일관성, 차별성 실질 평가)는
AI 심사위원 모드(ai_prompt) 또는 사람이 수행해야 한다. 80점 미만 제출 금지 원칙 적용.
""", made)

    # 9. 발표 Q&A
    qq = "\n".join(f"| {q['question']} | {q['status']} | {q['note'] or '-'} |" for q in res["qna"])
    _w(rev / "presentation_attack_qna.md", f"""# 발표 공격 질문 점검: {project}

{today} / 상태: 발화 가능 / 증빙 필요(확보 후 발화) / 발화 금지(근거 확보 전 금지)

| 질문 | 상태 | 조건 |
|---|---|---|
{qq}

## 모르는 질문 안전 문장

{res['qna'][0]['fallback'] if res['qna'] else ''}
""", made)

    # 10. 재작업 지시서
    rv = res["revision"]
    _w(rev / "revision_order.md", f"""# 재작업 지시서: {project}

{today} / 기계 감지분 — AI·사람 검수 결과와 합산할 것

## 1순위 — 탈락 위험 (해소 전 제출·LOCK 금지)

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(rv['p1'])) or '- 없음'}

## 2순위 — 점수 상승

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(rv['p2'])) or '- 없음'}

## 3순위 — 보완

{chr(10).join(f'{i+1}. {x}' for i, x in enumerate(rv['p3'])) or '- 없음'}

## 본문 혼입 금지 (확장 아이디어로 분리)

{chr(10).join('- ' + x for x in rv['quarantine']) or '- 없음'}
""", made)

    # 11. 다음 실행 프롬프트
    _w(out / "next_step_prompt.md", f"""# 다음 실행 프롬프트: {project}

```text
hyemi-ai-factory의 CLAUDE.md와 00_rules/ 전체를 적용해라.
프로젝트 {project}의 규칙 기반 결과(04_outputs/{project}/, 05_reviews/{project}/)를 읽고:
1. revision_order.md 1순위부터 반영 상태를 점검해라.
2. 아이디어 10축 정밀 채점과 심사위원 모드 8종 정성 검수를 수행해라.
3. 과제명·한줄요약 후보를 다듬고, 위험 표현 재스캔 후 결과를 갱신해라.
4. LOCK 조건 충족 시에만 사람 확정을 요청해라. 완료 후 HANDOFF 갱신.
```
""", made)

    # 12. HANDOFF
    _w(base / "10_handoff" / f"HANDOFF_{project}.md", f"""# HANDOFF_{project}.md

갱신: {today} / 생성: Hyemi Grant Factory 앱

- LOCK 상태: {lock['status']} (가능: {'예' if lock['can_lock'] else '아니오'})
- 심사 판정: {judge['verdict']} (예상 {judge['total']}/{judge['max']})
- 위험 표현: {len(d)}건 / 탈락급: {len(r['blockers'])}건 / 확인 필요(공고): {len(n['needs'])}건
- 1순위 재작업: {len(rv['p1'])}건 → 05_reviews/{project}/revision_order.md
- 다음 명령: 앱 재실행(입력 보완 후) 또는 04_outputs/{project}/next_step_prompt.md
""", made)

    # 14. 서류 라인 (7~13단계)
    doc = res.get("document")
    if doc:
        _export_document_line(project, doc, out, today, made)

    # 15. 발표 라인 (14~16단계)
    pres = res.get("presentation")
    if pres and pres["deck"].get("ready"):
        _export_presentation_line(project, pres, out, today, made)

    # 16. DOCX + 인쇄용 HTML (M5) — 실패해도 전체 export는 계속
    try:
        from docx_writer import draft_to_docx
        p = draft_to_docx(project, res, out)
        if p:
            made.append(str(p))
            _w(out / "print_draft.html", _print_html(project, res), made)
    except Exception:
        pass

    # 13. 통합 JSON
    _w(out / "results.json", json.dumps(res, ensure_ascii=False, indent=2, default=str), made)
    return made


def _print_html(project: str, res: dict) -> str:
    """브라우저에서 열어 인쇄 → 'PDF로 저장' (한글 폰트 문제 없는 PDF 경로)."""
    draft = res["document"]["draft"]
    secs = ""
    for s in draft["sections"]:
        tbl = ""
        if s.get("table"):
            t = s["table"]
            tbl = ("<table border=1 cellspacing=0 cellpadding=6><tr>"
                   + "".join(f"<th>{h}</th>" for h in t["head"]) + "</tr>"
                   + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in t["rows"])
                   + "</table>")
        secs += f"<h2>{s['no']}. {s['title']}</h2><p>{s['body']}</p>{tbl}"
    return f"""<!doctype html><html lang=ko><head><meta charset=utf-8><title>{project} 초안 인쇄</title>
<style>body{{font-family:'Malgun Gothic',sans-serif;max-width:800px;margin:24px auto;line-height:1.7}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th{{background:#eee}}
@media print{{button{{display:none}}}}</style></head><body>
<button onclick="window.print()">🖨 인쇄 / PDF로 저장</button>
<h1>사업계획서 초안 — {project}</h1>
<p><b>과제명:</b> {draft['title']}<br><b>한 줄 요약:</b> {draft['summary']}</p>
<p style="color:#a00">상태: DRAFT — [확인 필요] 해소 전 제출 금지</p>
{secs}</body></html>"""


def _export_document_line(project: str, doc: dict, out: Path, today: str, made: list):
    ws = doc["writing_strategy"]
    wrows = "\n".join(f"| {x['item']} | {x['points']} | {x['share']}% | {x['judge_eye']} | {x['tactic']} | {x['evidence']} |"
                      for x in ws["rows"])
    _w(out / "writing_strategy.md", f"""# 작성전략표 (7단계): {project}

{HEADER_NOTE} / {today} / 페이지 제한: {ws['page_limit']}
{ws['rule']}

| 평가항목 | 배점 | 분량 비중 | 심사위원이 보는 것 | 작성전략 | 필요한 증빙 |
|---|---:|---:|---|---|---|
{wrows}
""", made)

    draft = doc["draft"]
    if draft.get("ready"):
        parts = []
        for s in draft["sections"]:
            parts.append(f"## {s['no']}. {s['title']}\n\n{s['body']}\n")
            if s.get("table"):
                t = s["table"]
                parts.append("| " + " | ".join(t["head"]) + " |")
                parts.append("|" + "---|" * len(t["head"]))
                parts += ["| " + " | ".join(str(c) for c in r) + " |" for r in t["rows"]]
                parts.append("")
            parts.append("> 작성 가이드: " + " / ".join(s["guide"]) + "\n")
        san = "\n".join(f"- '{x['term']}' → '{x['to']}'" for x in draft["sanitized"]) or "- 없음"
        todos = "\n".join(f"- [ ] {t}" for t in draft["todos"]) or "- 없음"
        _w(out / "application_draft.md", f"""# 사업계획서 초안 (8단계): {project}

{draft['status']} / {today}

**과제명(초안)**: {draft['title']}
**한 줄 요약**: {draft['summary']}
**본문 흐름**: {draft['flow']}

{chr(10).join(parts)}
---

## 위험 표현 자동 치환 기록 (12단계)

{san}

## 초안 완성 전 할 일

{todos}
""", made)

    ev = doc["evidence_link"]
    erows = "\n".join(f"| {x['claim']} | {x['candidates']} | {x['status']} | {x['use']} |" for x in ev["rows"])
    _w(out / "evidence_link_table.md", f"""# 증빙 연결표 (9단계): {project}

{HEADER_NOTE} / {today}
{ev['rule']}

| 본문 주장 | 증빙 후보 | 상태 | 사용 방법 |
|---|---|---|---|
{erows}

## 증빙 공백 (확보 전 해당 주장 단정 금지)

{chr(10).join('- ' + g for g in ev['gaps']) or '- 없음'}

- 확보: {', '.join(ev['owned']) or '없음'}
- 예정: {', '.join(ev['planned']) or '없음'}
""", made)

    bt = doc["budget_table"]
    if bt.get("ready"):
        brows = "\n".join(f"| {x['item']} | {x['amount']} | {x['purpose']} | {x['output']} | {x['basis']} | {x['linked_item']} | {x['expected']} |"
                          for x in bt["rows"])
        flags = "\n".join(f"- **{x['item']}**: {f}" for x in bt["rows"] for f in x["flags"]) or "- 없음"
        _w(out / "budget_table.md", f"""# 연결형 예산표 (10단계): {project}

{HEADER_NOTE} / {today}
흐름: {bt['flow']} / {bt['rule']}

| 예산 항목 | 금액 | 사용 목적 | 산출물 | 산정 근거 | 연결 평가항목 | 기대성과 |
|---|---|---|---|---|---|---|
{brows}

## 예산 위험 플래그

{flags}
""", made)

    fc = doc["final_check"]
    frows = "\n".join(f"| {x['q']} | {x['status']} | {x['note']} |" for x in fc["rows"])
    lc = doc["length"]
    lrows = "\n".join(f"| {x['section']} | {x['chars']}자 | {x['share']}% | {x['note'] or '-'} |" for x in lc["rows"]) or "| (초안 없음) | - | - | - |"
    _w(out / "final_check.md", f"""# 분량 점검(11단계) + 최종 점검(13단계): {project}

{today} / 판정: **{fc['verdict']}**

## 분량 점검 — 페이지 제한: {lc['page_limit']}

{('⚠️ ' + lc['warn']) if lc['warn'] else ''}

| 절 | 분량 | 비중 | 경고 |
|---|---:|---:|---|
{lrows}

압축 원칙: {' / '.join(lc['checks'])}

## 최종 점검 질문 9종

| 점검 질문 | 상태 | 비고 |
|---|---|---|
{frows}

{fc['note']}
""", made)


def _export_presentation_line(project: str, pres: dict, out: Path, today: str, made: list):
    deck, script, reh = pres["deck"], pres["script"], pres["rehearsal"]
    srows = "\n".join(
        f"| {s['no']} | {s['title']} | {s['key_message']} | {'<br>'.join(s['bullets'])} | {s['evidence'] or '-'} | {s['seconds']}초 |"
        for s in deck["slides"])
    _w(out / "slides_outline.md", f"""# 발표자료 구성 (14단계): {project}

{HEADER_NOTE} / {today} / 발표 여부: {deck['presentation_required']} / 총 {deck['total_seconds'] // 60}분
{deck['note']}
원칙: {' / '.join(deck['rules'])}

| # | 슬라이드 | 핵심 주장 (1개) | 불릿 | 증빙 | 권장 시간 |
|---|---|---|---|---|---:|
{srows}

PPTX 파일: 04_outputs/{project}/slides.pptx (앱 ⑩ 발표자료 탭에서 다운로드)
""", made)

    if script.get("ready"):
        full = "\n\n".join(f"### {s['no']}. {s['title']} ({s['seconds']}초)\n\n{s['text']}\n\n- 반드시 말할 것: {s['must_say']}"
                           for s in script["slides"])
        comp = "\n".join(f"{c['no']}. {c['text']}" for c in script["compressed"])
        easy = "\n\n".join(f"**{e['no']}.** {e['text']}" for e in script["easy"])
        _w(out / "presentation_script.md", f"""# 발표 대본 (15단계): {project}

{HEADER_NOTE} / {today}
원칙: {' / '.join(script['rules'])}

## 시작 멘트

{script['opening']}

## 전체 대본 (슬라이드별)

{full}

## 마무리 멘트

{script['closing']}

---

## 압축 대본 (시간 부족 시 — 슬라이드당 1문장)

{comp}

## 쉬운 말 버전 (정책어 → 현장어)

{easy}

> {script['todo']}
""", made)

    w3 = "\n\n".join(f"**{x['q']}** ({x['how']})\n> {x['answer']}" for x in reh["why3"])
    bd = "\n\n".join(f"**{x['item']}** ({x['structure']})\n> {x['answer']}" for x in reh["budget_defense"]) or "예산 계획 입력 후 생성"
    ps = "\n".join(f"| {x['no']} | {x['title']} | {x['seconds']}초 | {x['must_say']} | {'<br>'.join(x['questions']) or '-'} |"
                   for x in reh["per_slide"])
    aq = "\n".join(f"| {x['q']} | {x['status']} | {x['note'] or '-'} |" for x in reh["attack_questions"])
    _w(out / "qna_defense.md", f"""# 발표 Q&A 방어 (16단계): {project}

{HEADER_NOTE} / {today}
피드백 기준: {' / '.join(reh['feedback_criteria'])}

## WHY 3종 방어

{w3}

## 예산 방어 (항목별)

{bd}

## 슬라이드별 예상 질문

| # | 슬라이드 | 시간 | 반드시 말할 것 | 예상 질문 |
|---|---|---:|---|---|
{ps}

## 심사위원 공격 질문 10 (발화 상태)

| 질문 | 상태 | 조건 |
|---|---|---|
{aq}

## 모르는 질문 안전 문장

{reh['unknown_answer']}

> 연습 모드: {' / '.join(reh['modes'])} — 앱 ⑪ 발표연습기 탭
""", made)

    # PPTX 파일
    from pptx_writer import write_pptx
    p = write_pptx(out / "slides.pptx", project, deck["slides"])
    made.append(str(p))
