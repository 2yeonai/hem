#!/usr/bin/env python3
"""Hyemi Grant Factory — 로컬 웹앱 (Python 표준 라이브러리만 사용).

실행:  python3 08_factory_tools/app.py   →  http://127.0.0.1:8787

설계 원칙:
- 감점 위험이 먼저 보인다 (위험 배너 → 판정 → 상세 순서)
- 코드가 LOCKED를 만들지 않는다. 공고 원문 없으면 LOCK 불가.
- 저장은 전부 기존 공장 폴더(01_inputs/04_outputs/05_reviews/10_handoff)의 파일로.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import email
import ai_engine
import engines
from doc_extract import extract_text
from export_md import export_all
from notice_parser import parse_notice

BASE = engines.BASE
PORT = 8787


# ------------------------------------------------------------ data helpers

def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9가-힣-]+", "-", (name or "").strip().lower()).strip("-")


def list_projects() -> list:
    out = []
    inp = BASE / "01_inputs"
    if inp.exists():
        for p in sorted(inp.iterdir()):
            if (p / "input.json").exists():
                res_path = BASE / "04_outputs" / p.name / "results.json"
                summary = None
                if res_path.exists():
                    try:
                        r = json.loads(res_path.read_text(encoding="utf-8"))
                        summary = {"lock": r["lock"]["status"], "verdict": r["judge"]["verdict"],
                                   "danger": len(r["danger"]), "blockers": len(r["risk"]["blockers"]),
                                   "stage0": bool(r.get("stage0"))}
                    except Exception:
                        pass
                out.append({"name": p.name, "summary": summary})
    return out


def load_input(project: str) -> dict:
    return json.loads((BASE / "01_inputs" / project / "input.json").read_text(encoding="utf-8"))


def save_input(project: str, data: dict):
    p = BASE / "01_inputs" / project / "input.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_results(project: str):
    p = BASE / "04_outputs" / project / "results.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def rerun(project: str):
    data = load_input(project)
    res = engines.analyze_all(data)
    export_all(project, data, res, BASE)


# ------------------------------------------------------------ form parsing

def _lines(v: str) -> list:
    return [x.strip() for x in (v or "").splitlines() if x.strip()]


def _csv(v: str) -> list:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def form_to_input(f: dict) -> dict:
    def g(k, default=""):
        return (f.get(k, [default]) or [default])[0].strip()

    scoring = []
    for ln in _lines(g("scoring")):
        m = re.match(r"(.+?)[:|]\s*(\d+)", ln)
        if m:
            scoring.append({"item": m.group(1).strip(), "points": int(m.group(2))})
    budget = []
    for ln in _lines(g("budget_plan")):
        parts = [x.strip() for x in ln.split("|")]
        budget.append({"item": parts[0] if parts else "",
                       "amount": parts[1] if len(parts) > 1 and parts[1] else "미확보",
                       "purpose": parts[2] if len(parts) > 2 else "",
                       "output": parts[3] if len(parts) > 3 else ""})
    ideas = []
    for i in (1, 2, 3):
        if not g(f"idea{i}_name"):
            continue
        ideas.append({
            "id": f"idea{i}", "name": g(f"idea{i}_name"), "problem": g(f"idea{i}_problem"),
            "target": g(f"idea{i}_target") or "미확보",
            "outputs": _csv(g(f"idea{i}_outputs")),
            "budget_estimate": g(f"idea{i}_budget") or "미확보",
            "evidence_owned": _csv(g(f"idea{i}_ev_owned")),
            "evidence_planned": _csv(g(f"idea{i}_ev_planned")),
            "risks": _csv(g(f"idea{i}_risks")),
        })
    return {
        "project_name": slugify(g("project_name")),
        "created_at": date.today().isoformat(),
        "notice": {
            "title": g("notice_title") or "미확보", "agency": g("agency") or "미확보",
            "purpose": g("purpose") or "미확보",
            "raw_text": g("raw_text") or "미확보",
            "apply_deadline": g("deadline") or "미확보",
            "execution_period": g("period") or "미확보",
            "eligibility": g("eligibility") or "미확보", "exclusions": g("exclusions") or "미확보",
            "budget": {"max_amount": g("budget_max") or "미확보",
                       "self_pay_ratio": g("self_ratio") or "미확보",
                       "allowed_items": [], "excluded_items": []},
            "format": {"form_type": g("form_type") or "미확보",
                       "page_limit": g("page_limit") or "미확보", "char_limit": "미확보"},
            "scoring": scoring,
            "presentation": {"required": g("presentation") or "미확보",
                             "present_minutes": "미확보", "qna_minutes": "미확보"},
            "bonus_items": [],
        },
        "applicant": {
            "name": g("app_name") or "미확보", "biz_type": g("biz_type") or "미확보",
            "biz_years": g("biz_years") or "미확보", "industry": g("industry") or "미확보",
            "industry_code": g("industry_code") or "미확보",
            "channels": _csv(g("channels")),
            "duplicate_grant_history": g("duplicate") or "미확인",
            "tax_arrears": g("arrears") or "미확인",
            "closed_biz_history": g("closed") or "미확인", "notes": g("notes"),
        },
        "ideas": ideas,
        "evidence": {"owned": _csv(g("ev_owned")), "planned": _csv(g("ev_planned"))},
        "budget_plan": budget,
        "selected_idea_id": None,
        "approvals": {"eligibility_confirmed": False, "idea_selected": False,
                      "budget_confirmed": False, "final_submission_approved": False},
    }


# ------------------------------------------------------------------- HTML

CSS = """
body{font-family:system-ui,'Apple SD Gothic Neo',sans-serif;margin:0;background:#f5f5f2;color:#222}
header{background:#1a1a2e;color:#fff;padding:10px 20px;display:flex;gap:16px;align-items:baseline}
header a{color:#ffd166;text-decoration:none;font-weight:600} header small{color:#aaa}
main{max-width:1080px;margin:16px auto;padding:0 16px}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 18px;margin-bottom:14px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
th,td{border:1px solid #ccc;padding:5px 8px;text-align:left;vertical-align:top}
th{background:#eee}
.b-red{background:#c0392b;color:#fff;padding:10px 14px;border-radius:6px;margin-bottom:10px;font-weight:600}
.b-yel{background:#f39c12;color:#fff;padding:10px 14px;border-radius:6px;margin-bottom:10px}
.b-grn{background:#27ae60;color:#fff;padding:10px 14px;border-radius:6px;margin-bottom:10px}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;color:#fff}
.t-red{background:#c0392b}.t-yel{background:#e67e22}.t-grn{background:#27ae60}.t-gry{background:#7f8c8d}
nav.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
nav.tabs a{padding:6px 12px;background:#ddd;border-radius:6px;text-decoration:none;color:#222;font-size:14px}
nav.tabs a.on{background:#1a1a2e;color:#fff}
input[type=text],textarea,select{width:100%;box-sizing:border-box;padding:6px;border:1px solid #bbb;border-radius:4px;font-size:14px}
textarea{font-family:inherit} label{font-weight:600;font-size:13px;display:block;margin-top:10px}
button,.btn{background:#1a1a2e;color:#fff;border:0;padding:9px 18px;border-radius:6px;font-size:15px;cursor:pointer;text-decoration:none;display:inline-block;margin-top:10px}
button.warn{background:#c0392b} .grid{display:grid;grid-template-columns:1fr 1fr;gap:0 20px}
.hint{color:#777;font-size:12px} pre{background:#f0f0ee;padding:10px;overflow-x:auto;border-radius:6px;font-size:13px}
h2{margin:6px 0 10px} h3{margin:14px 0 6px}
.st{display:inline-block;min-width:20px;text-align:center;padding:2px 4px;margin:1px;border-radius:4px;font-size:12px;font-weight:700;color:#fff;cursor:default}
.s-done{background:#27ae60}.s-part{background:#e67e22}.s-todo{background:#95a5a6}
.s-blk{background:#c0392b}.s-hum{background:#2980b9}
.timer{font-size:40px;font-weight:800;font-variant-numeric:tabular-nums}
.danger-hit{background:#ffd5d5;border-bottom:2px solid #c0392b}
.slidebox{border:2px solid #1a1a2e;border-radius:8px;padding:16px;min-height:120px;margin:8px 0}
"""


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{esc(title)} — Hyemi Grant Factory</title><style>{CSS}</style></head>
<body><header><a href="/">🏭 Hyemi Grant Factory</a>
<a href="/upload" style="font-size:14px">📄 공고 업로드</a>
<a href="/ai" style="font-size:14px">🤖 AI 설정</a>
<small>규칙 기반 예비 판정 — 확정은 사람이 한다 / LOCKED는 앱이 만들지 않는다</small></header>
<main>{body}</main></body></html>""".encode("utf-8")


def verdict_tag(v: str) -> str:
    cls = "t-red" if ("불가" in v or "탈락" in v) else "t-yel" if "보완" in v or "보류" in v else "t-grn"
    return f'<span class="tag {cls}">{esc(v)}</span>'


# ------------------------------------------------------------- screen parts

def parse_multipart(ctype: str, body: bytes) -> tuple:
    """multipart/form-data → (fields dict, files [(name, filename, bytes)])."""
    msg = email.message_from_bytes(b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
    fields, files = {}, []
    if msg.is_multipart():
        for part in msg.get_payload():
            name = part.get_param("name", header="content-disposition")
            fname = part.get_param("filename", header="content-disposition")
            payload = part.get_payload(decode=True) or b""
            if fname:
                files.append((name, fname, payload))
            elif name:
                fields[name] = payload.decode("utf-8", "ignore").strip()
    return fields, files


def notice_from_parsed(text: str, parsed: dict, title_hint: str) -> dict:
    """추출 텍스트 + 구조 분석 → input_schema의 notice dict (없으면 미확보 유지)."""
    fmt = {"form_type": "미확보", "page_limit": parsed.get("page_limit", "미확보"), "char_limit": "미확보"}
    return {
        "title": parsed.get("title") or title_hint or "미확보",
        "agency": "미확보",
        "purpose": parsed.get("purpose", "미확보"),
        "raw_text": text or "미확보",
        "apply_deadline": parsed.get("apply_deadline", "미확보"),
        "execution_period": parsed.get("execution_period", "미확보"),
        "eligibility": parsed.get("eligibility", "미확보"),
        "exclusions": parsed.get("exclusions", "미확보"),
        "budget": {"max_amount": parsed.get("max_amount", "미확보"),
                   "self_pay_ratio": parsed.get("self_pay", "미확보"),
                   "allowed_items": [], "excluded_items": []},
        "format": fmt,
        "scoring": parsed.get("scoring", []),
        "presentation": {"required": parsed.get("presentation_required", "미확보"),
                         "present_minutes": "미확보", "qna_minutes": "미확보"},
        "bonus_items": [],
        "documents": parsed.get("documents", []),
        "schedule": parsed.get("schedule", []),
        "parse_notes": parsed.get("parse_notes", []),
    }


def screen_upload() -> str:
    return """<div class=card><h2>📄 공고 파일 업로드 → 0단계 자동 시작</h2>
<p class=hint>PDF·HWP·HWPX·DOCX·TXT 지원. 업로드하면 텍스트 추출 → 구조 분석(배점표·마감·자격·제출서류)
→ 성격 분석(목적·심사 의도) → 0단계 분석 전부가 자동 실행된다. 이미지·스캔 PDF는 AI 모드 또는 텍스트 붙여넣기 사용.</p>
<form method=post action="/upload" enctype="multipart/form-data">
<label>프로젝트명 (영문·숫자·하이픈)</label><input type=text name=project_name required>
<label>공고 파일</label><input type=file name=file>
<label>또는 공고 원문 텍스트 붙여넣기 (파일보다 우선)</label><textarea name=raw rows=8></textarea>
<button>업로드 + 자동 분석 →</button>
<p class=hint>PDF 추출에 오류가 나면 1회 설치: <code>pip install pypdf</code> · 구형 HWP: <code>pip install olefile</code></p>
</form></div>"""


def screen_dashboard() -> str:
    rows = []
    for p in list_projects():
        s = p["summary"]
        if s:
            stage = '<span class="tag t-yel">0단계: 신청자 입력 대기</span> · ' if s.get("stage0") else ""
            info = (f'{stage}LOCK {esc(s["lock"])} · {verdict_tag(s["verdict"])} · '
                    f'위험표현 {s["danger"]}건 · 탈락급 {s["blockers"]}건')
        else:
            info = '<span class="tag t-gry">미분석</span>'
        rows.append(f'<tr><td><a href="/project/{esc(p["name"])}">{esc(p["name"])}</a></td><td>{info}</td></tr>')
    table = ("<table><tr><th>프로젝트</th><th>상태 (위험 먼저)</th></tr>" + "".join(rows) + "</table>") if rows else "<p>프로젝트가 없습니다.</p>"
    return f"""<div class=card><h2>대시보드</h2>{table}
<a class=btn href="/upload">📄 공고 파일 업로드 (자동 분석)</a>
<a class=btn href="/new">+ 새 프로젝트 (직접 입력)</a>
<form method=post action="/run_sample" style="display:inline"><button>▶ 샘플 프로젝트 실행 (API 키 불필요)</button></form>
<p class=hint>샘플은 가상 공고 데이터다. 실제 공고 결과로 재사용 금지 (D-006).</p></div>"""


def _idea_block(i: int, idea: dict = None) -> str:
    v = idea or {}

    def tx(k):
        x = v.get(k)
        return esc("" if x in (None, "미확보") else x)

    def cs(k):
        return esc(", ".join(v.get(k) or []))

    return f"""<fieldset style="margin-top:12px;border:1px solid #ccc;border-radius:6px">
<legend>아이디어 후보 {i} (선택 — 없으면 0단계로 저장되고 신청자 폼이 생성됨)</legend>
<div class=grid>
<div><label>이름</label><input type=text name=idea{i}_name value="{tx('name')}"></div>
<div><label>대상 고객·수혜자</label><input type=text name=idea{i}_target value="{tx('target')}"></div>
</div>
<label>해결하는 문제 <span class=hint>시간·비용·오류 수치로 쓸수록 점수 판정이 정확해짐</span></label>
<textarea name=idea{i}_problem rows=2>{tx('problem')}</textarea>
<div class=grid>
<div><label>산출물 (쉼표 구분)</label><input type=text name=idea{i}_outputs value="{cs('outputs')}"></div>
<div><label>예산 규모</label><input type=text name=idea{i}_budget value="{tx('budget_estimate')}" placeholder="예: 1500만원 / 미확보"></div>
<div><label>확보 증빙 (쉼표)</label><input type=text name=idea{i}_ev_owned value="{cs('evidence_owned')}"></div>
<div><label>예정 증빙 (쉼표)</label><input type=text name=idea{i}_ev_planned value="{cs('evidence_planned')}"></div>
</div>
<label>알고 있는 리스크 (쉼표)</label><input type=text name=idea{i}_risks value="{cs('risks')}">
</fieldset>"""


def _sel(name: str, current, opts=("미확인", "없음", "있음")) -> str:
    o = "".join(f'<option value="{x}" {"selected" if str(current) == x else ""}>{x}</option>' for x in opts)
    return f"<select name={name}>{o}</select>"


def screen_new() -> str:
    return f"""<div class=card><h2>새 프로젝트</h2>
<form method=post action="/create">
<label>프로젝트명 (필수, 영문·숫자·하이픈)</label><input type=text name=project_name required>

<h3>1. 공고문</h3>
<div class=grid>
<div><label>공고명</label><input type=text name=notice_title></div>
<div><label>주관기관</label><input type=text name=agency></div>
<div><label>공고 목적</label><input type=text name=purpose></div>
<div><label>수행기간</label><input type=text name=period></div>
<div><label>접수 마감</label><input type=text name=deadline></div>
<div><label>발표 여부</label><input type=text name=presentation placeholder="있음/없음/미확보"></div>
<div><label>지원 한도</label><input type=text name=budget_max></div>
<div><label>자부담 비율</label><input type=text name=self_ratio></div>
<div><label>양식</label><input type=text name=form_type placeholder="PSST/자유양식"></div>
<div><label>페이지 제한</label><input type=text name=page_limit></div>
</div>
<label>공고문 원문 전체 <span class=hint>비우면 [확인 필요] 모드 — 모든 실전 판정·LOCK이 막힌다</span></label>
<textarea name=raw_text rows=8></textarea>
<div class=grid>
<div><label>신청자격 (원문)</label><textarea name=eligibility rows=2></textarea></div>
<div><label>지원제외 조항 (원문·가장 중요)</label><textarea name=exclusions rows=2></textarea></div>
</div>
<label>심사표·배점 <span class=hint>한 줄에 하나: 항목: 배점 (예: 실행계획: 30)</span></label>
<textarea name=scoring rows=4></textarea>

<h3>2. 신청자</h3>
<div class=grid>
<div><label>이름/상호</label><input type=text name=app_name></div>
<div><label>사업자 형태</label><input type=text name=biz_type placeholder="예비창업/개인/법인"></div>
<div><label>업력(년)</label><input type=text name=biz_years></div>
<div><label>업종</label><input type=text name=industry></div>
<div><label>업종코드</label><input type=text name=industry_code></div>
<div><label>판매·운영 채널 (쉼표)</label><input type=text name=channels></div>
<div><label>동일사업 중복수혜</label><select name=duplicate><option value="미확인">미확인</option><option value="없음">없음</option><option value="있음">있음</option></select></div>
<div><label>세금 체납</label><select name=arrears><option value="미확인">미확인</option><option value="없음">없음</option><option value="있음">있음</option></select></div>
<div><label>폐업 이력</label><select name=closed><option value="미확인">미확인</option><option value="없음">없음</option><option value="있음">있음</option></select></div>
</div>
<label>비고</label><input type=text name=notes>

<h3>3. 아이디어 후보 (1~3개)</h3>
{_idea_block(1)}{_idea_block(2)}{_idea_block(3)}

<h3>4. 증빙·예산</h3>
<div class=grid>
<div><label>보유 증빙 전체 (쉼표)</label><input type=text name=ev_owned></div>
<div><label>예정 증빙 (쉼표)</label><input type=text name=ev_planned></div>
</div>
<label>예산 계획 <span class=hint>한 줄에 하나: 항목|금액|용도|산출물 — 모르면 항목만이라도</span></label>
<textarea name=budget_plan rows=4></textarea>

<button>분석 실행 →</button>
<p class=hint>모르는 값은 비워둬라 — 지어내지 말고. 공장이 [확인 필요]로 추적한다.</p>
</form></div>"""


def screen_edit(project: str) -> str:
    data = load_input(project)
    a = data.get("applicant", {}) or {}
    ideas = data.get("ideas", []) or []
    ev = data.get("evidence", {}) or {}

    def tx(k):
        x = a.get(k)
        return esc("" if x in (None, "미확보") else x)

    bud = "\n".join(f"{b.get('item', '')}|{'' if b.get('amount') == '미확보' else b.get('amount', '')}|{b.get('purpose', '')}|{b.get('output', '')}"
                    for b in (data.get("budget_plan") or []))
    blocks = "".join(_idea_block(i + 1, ideas[i] if i < len(ideas) else None) for i in range(3))
    return f"""<div class=card><h2>{esc(project)} — 신청자·아이디어 입력</h2>
<p class=hint>공고 분석은 그대로 유지된다. 여기서 신청자 정보와 아이디어 후보를 채우면 0단계를 벗어난다.
참고 질문지: 04_outputs/{esc(project)}/applicant_input_form.md (Export 탭)</p>
<form method=post action="/update/{esc(project)}">
<h3>신청자</h3>
<div class=grid>
<div><label>이름/상호</label><input type=text name=app_name value="{tx('name')}"></div>
<div><label>사업자 형태</label><input type=text name=biz_type value="{tx('biz_type')}"></div>
<div><label>업력(년)</label><input type=text name=biz_years value="{tx('biz_years')}"></div>
<div><label>업종</label><input type=text name=industry value="{tx('industry')}"></div>
<div><label>업종코드</label><input type=text name=industry_code value="{tx('industry_code')}"></div>
<div><label>판매·운영 채널 (쉼표)</label><input type=text name=channels value="{esc(', '.join(a.get('channels') or []))}"></div>
<div><label>동일사업 중복수혜</label>{_sel('duplicate', a.get('duplicate_grant_history', '미확인'))}</div>
<div><label>세금 체납</label>{_sel('arrears', a.get('tax_arrears', '미확인'))}</div>
<div><label>폐업 이력</label>{_sel('closed', a.get('closed_biz_history', '미확인'))}</div>
</div>
<label>비고</label><input type=text name=notes value="{tx('notes')}">
<h3>아이디어 후보</h3>
{blocks}
<h3>증빙·예산</h3>
<div class=grid>
<div><label>보유 증빙 전체 (쉼표)</label><input type=text name=ev_owned value="{esc(', '.join(ev.get('owned') or []))}"></div>
<div><label>예정 증빙 (쉼표)</label><input type=text name=ev_planned value="{esc(', '.join(ev.get('planned') or []))}"></div>
</div>
<label>예산 계획 <span class=hint>한 줄에 하나: 항목|금액|용도|산출물</span></label>
<textarea name=budget_plan rows=4>{esc(bud)}</textarea>
<button>저장 + 재분석 →</button>
</form></div>"""


TABS = [("notice", "① 공고 분석"), ("risk", "② 자격 리스크"), ("ideas", "③ 아이디어 비교"),
        ("lock", "④ LOCK 판정"), ("judge", "⑤ 심사위원 검수"), ("revision", "⑥ 재작업 지시서"),
        ("qna", "⑦ 발표 Q&A"), ("draft", "⑧ 서류 초안"), ("present", "⑨ 발표자료"),
        ("rehearse", "⑩ 발표연습기"), ("export", "⑪ Export / HANDOFF")]

STAGE_CLS = {"done": "s-done", "partial": "s-part", "todo": "s-todo",
             "blocked": "s-blk", "human": "s-hum"}


def pipeline_strip(res) -> str:
    """17단계 파이프라인 진행 표시 (모든 탭 상단)."""
    pl = res.get("pipeline")
    if not pl:
        return ""
    cells = "".join(
        f'<span class="st {STAGE_CLS.get(p["status"], "s-todo")}" title="{esc(p["no"])}. {esc(p["name"])} — {esc(p["note"])}">{p["no"]}</span>'
        for p in pl)
    legend = ('<span class="st s-done">완료</span><span class="st s-part">진행</span>'
              '<span class="st s-todo">대기</span><span class="st s-blk">잠김</span>'
              '<span class="st s-hum">사람</span>')
    return (f'<div class=card style="padding:8px 14px"><b style="font-size:13px">공정 0~16</b> {cells}'
            f'<span style="float:right;font-size:11px">{legend}</span>'
            f'<div class=hint>번호에 마우스를 올리면 단계명·상태가 보인다 (혜미 방식 17단계)</div></div>')


def screen_project(project: str, tab: str) -> str:
    res = load_results(project)
    if res is None:
        return f'<div class=card><h2>{esc(project)}</h2><p>결과 없음.</p><form method=post action="/rerun/{esc(project)}"><button>분석 실행</button></form></div>'
    n, r, d = res["notice"], res["risk"], res["danger"]
    lock, judge, rv = res["lock"], res["judge"], res["revision"]
    banners = ""
    if res.get("stage0"):
        banners += (f'<div class=b-yel>📝 0단계: 신청자·아이디어 미입력 — LOCK·제출 판정이 잠겨 있다. '
                    f'<a style="color:#fff;text-decoration:underline" href="/edit/{esc(project)}">신청자·아이디어 입력 →</a></div>')
    if r["blockers"]:
        banners += f'<div class=b-red>⛔ 탈락급 리스크 {len(r["blockers"])}건: ' + " · ".join(esc(b) for b in r["blockers"]) + "</div>"
    if not n["raw_ok"]:
        banners += '<div class=b-red>⚠️ 공고문 원문 없음 — 모든 판정은 [확인 필요], LOCK 불가</div>'
    if d:
        banners += f'<div class=b-yel>위험 표현 {len(d)}건 검출 — ⑤/⑥ 탭에서 확인</div>'
    if res.get("engine_errors"):
        banners += ('<div class=b-yel>⚠ 일부 엔진 오류 (앱은 계속 동작): '
                    + esc("; ".join(res["engine_errors"][:3])) + "</div>")
    if not banners:
        banners = '<div class=b-grn>탈락급 리스크·위험 표현 미검출 (규칙 기준) — 사람 확인은 여전히 필요</div>'
    tabs = "".join(f'<a class="{ "on" if t == tab else "" }" href="/project/{esc(project)}?tab={t}">{lbl}</a>' for t, lbl in TABS)
    body = {"notice": _tab_notice, "risk": _tab_risk, "ideas": _tab_ideas, "lock": _tab_lock,
            "judge": _tab_judge, "revision": _tab_revision, "qna": _tab_qna,
            "draft": _tab_draft, "present": _tab_present, "rehearse": _tab_rehearse,
            "export": _tab_export}[tab](project, res)
    return (f"<h2>{esc(project)} {verdict_tag(judge['verdict'])} <span class='tag t-gry'>LOCK: {esc(lock['status'])}</span></h2>"
            f"{banners}{pipeline_strip(res)}<nav class=tabs>{tabs}</nav><div class=card>{body}</div>"
            f'<a class=btn href="/edit/{esc(project)}">신청자·아이디어 입력/수정</a> '
            f'<form method=post action="/rerun/{esc(project)}" style="display:inline"><button>재분석</button></form>')


def _tab_notice(project, res):
    n = res["notice"]
    rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in n["fields"].items())
    sc = "".join(f"<tr><td>{esc(s.get('item'))}</td><td>{esc(s.get('points'))}</td></tr>" for s in n["scoring"]) or "<tr><td colspan=2>[확인 필요] 배점표 미입력 — 내부 기준 대체</td></tr>"
    needs = "".join(f"<li>{esc(x)}</li>" for x in n["needs"]) or "<li>없음</li>"
    top = f"{esc(n['top_item']['item'])} ({esc(n['top_item']['points'])}점)" if n["top_item"] else "[확인 필요]"
    st = res.get("strategy")
    strat = ""
    if st:
        srows = "".join(f"<tr><td>{esc(x['item'])}</td><td>{x['points']}</td><td>{x['share']}%</td><td>{esc(x['hint'])}</td></tr>"
                        for x in st["rows"])
        strat = (f"<h3>배점 전략 (공략법)</h3><p class=hint>{esc(st['note'])}</p>"
                 f"<table><tr><th>평가항목</th><th>배점</th><th>비중</th><th>공략 전략</th></tr>{srows}</table>")
    ch = res.get("character") or {}
    chs = ""
    if ch:
        intents = "".join(f"<li>{esc(x)}</li>" for x in ch.get("review_intent", []))
        risky = "".join(f"<li>{esc(x)}</li>" for x in ch.get("risky_moves", []))
        terms = ", ".join(ch.get("preferred_terms", [])[:12]) or "-"
        chs = (f"<h3>공고 성격 분석 (로컬 규칙)</h3>"
               f"<p>사업 성격: <b>{esc(' / '.join(ch.get('purpose_type', [])) or '?')}</b></p>"
               f"<b>심사 의도 (배점 상위 해석)</b><ul>{intents}</ul>"
               f"<b>본문에 되돌려줄 공고 어휘</b><p>{esc(terms)}</p>"
               f"<b>위험 전략 (공고 명시 근거)</b><ul>{risky}</ul>"
               f"<p class=hint>{esc(ch.get('note', ''))} · 정밀 분석: 상단 🤖 AI 설정 → '공고 정밀 분석'</p>")
    return f"""<h3>공고 요약</h3><table>{rows}</table>
<h3>심사표·배점</h3><table><tr><th>평가항목</th><th>배점</th></tr>{sc}</table>
<p>배점 최고 항목(분량·증빙 집중 대상): <b>{top}</b></p>
{strat}{chs}
<h3>[확인 필요] 항목</h3><ul>{needs}</ul>"""


def _tab_risk(project, res):
    r = res["risk"]
    cls = {"high": "t-red", "warn": "t-yel", "ok": "t-grn"}
    rows = "".join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td><span class="tag {cls[l]}">{esc(c)}</span></td></tr>'
                   for a, b, c, l in r["rows"])
    needs = "".join(f"<li>{esc(x)}</li>" for x in r["needs"]) or "<li>없음</li>"
    return f"""<h3>신청자격·지원제외 리스크</h3>
<table><tr><th>항목</th><th>값</th><th>판정</th></tr>{rows}</table>
<h3>사람이 서류로 확인해야 할 것</h3><ul>{needs}</ul>
<p class=hint>확인 완료 후 ④ LOCK 탭에서 승인을 기록해라. 서류 없이 승인하지 마라.</p>"""


def _tab_ideas(project, res):
    ideas = res["ideas"]
    axes = ["공고 적합성", "문제 명확성", "실행 가능성", "증빙 가능성", "예산 적합성", "발표 방어"]
    head = "".join(f"<th>{a}</th>" for a in axes)
    rows = ""
    for it in ideas["items"]:
        cells = "".join(f"<td>{'?' if it['scores'][a] is None else it['scores'][a]}</td>" for a in axes)
        vt = verdict_tag(it["verdict"])
        rows += f"<tr><td>{esc(it['id'])} {esc(it['name'])}</td>{cells}<td>{it['total']}/{it['max']}</td><td>{vt}</td></tr>"
        rows += f"<tr><td colspan={len(axes)+3} class=hint>{esc(' / '.join(it['reasons']))}</td></tr>"
    rec = f"{esc(ideas['recommend']['id'])} {esc(ideas['recommend']['name'])}" if ideas["recommend"] else "없음"
    return f"""<h3>아이디어 후보 비교 <span class=hint>? = 판정 불가([확인 필요])</span></h3>
<table><tr><th>후보</th>{head}<th>합계</th><th>판정</th></tr>{rows}</table>
<p>기계 추천: <b>{rec}</b> — {esc(ideas['note'])}. 최종 선정은 ④ LOCK 탭에서 사람이 기록.</p>"""


def _tab_lock(project, res):
    lock = res["lock"]
    data = load_input(project)
    reasons = "".join(f"<li>{esc(x)}</li>" for x in lock["block_reasons"]) or "<li>없음 — LOCK 가능 (사람이 06_locks/LOCK_STATUS.md에 기재)</li>"
    opts = "".join(f'<option value="{esc(i.get("id"))}" {"selected" if data.get("selected_idea_id") == i.get("id") else ""}>{esc(i.get("id"))} {esc(i.get("name"))}</option>'
                   for i in data.get("ideas", []))
    ap = data.get("approvals") or {}
    def chk(k):
        return "checked" if ap.get(k) is True else ""
    titles = "".join(f"<li>{esc(t)}</li>" for t in res["titles"]) or "<li>후보 확정 후 생성</li>"
    sums = "".join(f"<li>{esc(t)}</li>" for t in res["summaries"]) or "<li>후보 확정 후 생성</li>"
    return f"""<h3>LOCK 판정: <b>{esc(lock['status'])}</b></h3>
<h3>LOCK 불가 사유</h3><ol>{reasons}</ol>
<h3>사람 승인 기록 <span class=hint>서류·견적으로 확인한 것만 체크해라 — 체크가 곧 책임 기록이다</span></h3>
<form method=post action="/approve/{esc(project)}">
<label>최종 아이디어</label><select name=selected_idea_id><option value="">(미확정)</option>{opts}</select>
<p><label><input type=checkbox name=idea_selected {chk('idea_selected')}> 최종 아이디어를 내가 확정한다</label>
<label><input type=checkbox name=eligibility_confirmed {chk('eligibility_confirmed')}> 자격 3종(중복수혜·체납·업종코드)을 서류로 확인했다</label>
<label><input type=checkbox name=budget_confirmed {chk('budget_confirmed')}> 예산을 견적 기반으로 확인했다</label></p>
<button>승인 기록 + 재분석</button></form>
<h3>과제명 후보 (규칙 생성 초안)</h3><ol>{titles}</ol>
<h3>한 줄 요약 후보</h3><ol>{sums}</ol>
<p class=hint>{esc(lock['next_conditions'])}</p>"""


def _tab_judge(project, res):
    judge, d, bud, me = res["judge"], res["danger"], res["budget"], res["missing_evidence"]
    rows = "".join(f"<tr><td>{esc(x['item'])}</td><td>{x['points']}</td><td>{x['est']}</td><td>{esc(x['why'])}</td></tr>" for x in judge["rows"])
    drows = "".join(f"<tr><td>{esc(h['source'])}</td><td><b>{esc(h['term'])}</b></td><td>{esc(h['replacement'])}</td></tr>" for h in d) or "<tr><td colspan=3>검출 없음 (입력 텍스트 기준)</td></tr>"
    brows = "".join(f"<tr><td>{esc(x['item'])}</td><td>{esc(x['amount'])}</td><td>{esc('; '.join(x['flags']) or '-')}</td><td>{'필요' if x['quote_needed'] else '-'}</td></tr>" for x in bud["rows"]) or "<tr><td colspan=4>예산 계획 미입력 — 판정 불가</td></tr>"
    mrows = "".join(f"<tr><td>{esc(x['need'])}</td><td>{esc(x['why'])}</td><td>{x['prio']}</td></tr>" for x in me) or "<tr><td colspan=3>-</td></tr>"
    ded = "".join(f"<li>{esc(x)}</li>" for x in judge["deductions"]) or "<li>없음</li>"
    return f"""<h3>판정: {verdict_tag(judge['verdict'])} — 예상 {judge['total']}/{judge['max']}점 ({judge['pct']}%)</h3>
<p class=hint>{'내부 기준 대체 채점 [확인 필요]' if judge['internal_scoring_used'] else '입력된 심사표 기준'} · 규칙 기반 상한 90% — 나머지는 증빙과 사람 몫 · 80점 미만 제출 금지</p>
<table><tr><th>평가항목</th><th>배점</th><th>예상</th><th>감점 사유</th></tr>{rows}</table>
<h3>감점·탈락 요인</h3><ul>{ded}</ul>
<h3>위험 표현 ({len(d)}건)</h3><table><tr><th>위치</th><th>표현</th><th>대체 제안</th></tr>{drows}</table>
<h3>예산 리스크</h3><table><tr><th>항목</th><th>금액</th><th>위험</th><th>견적서</th></tr>{brows}</table>
<h3>누락 증빙</h3><table><tr><th>필요</th><th>이유</th><th>우선순위</th></tr>{mrows}</table>"""


def _tab_revision(project, res):
    rv = res["revision"]
    def ol(items):
        return "".join(f"<li>{esc(x)}</li>" for x in items) or "<li>없음</li>"
    return f"""<h3>재작업 지시서 (기계 감지분)</h3>
<h3 style="color:#c0392b">1순위 — 탈락 위험 (해소 전 제출·LOCK 금지)</h3><ol>{ol(rv['p1'])}</ol>
<h3 style="color:#e67e22">2순위 — 점수 상승</h3><ol>{ol(rv['p2'])}</ol>
<h3>3순위 — 보완</h3><ol>{ol(rv['p3'])}</ol>
<h3>본문 혼입 금지 (확장 아이디어로 분리)</h3><ul>{ol(rv['quarantine'])}</ul>"""


def _tab_qna(project, res):
    cls = {"발화 가능": "t-grn", "증빙 필요": "t-yel", "발화 금지": "t-red"}
    rows = "".join(f'<tr><td>{esc(q["question"])}</td><td><span class="tag {cls[q["status"]]}">{esc(q["status"])}</span></td><td>{esc(q["note"] or "-")}</td></tr>' for q in res["qna"])
    return f"""<h3>발표 공격 질문 점검</h3>
<table><tr><th>질문</th><th>상태</th><th>발화 조건</th></tr>{rows}</table>
<h3>모르는 질문 안전 문장</h3><pre>{esc(engines.SAFE_ANSWER)}</pre>"""


def _tab_draft(project, res):
    doc = res.get("document")
    if not doc:
        return "<p>재분석이 필요하다 (하단 재분석 버튼).</p>"
    ws = doc["writing_strategy"]
    wrows = "".join(f"<tr><td>{esc(x['item'])}</td><td>{x['points']}</td><td>{x['share']}%</td>"
                    f"<td>{esc(x['judge_eye'])}</td><td>{esc(x['tactic'])}</td><td>{esc(x['evidence'])}</td></tr>"
                    for x in ws["rows"])
    out = [f"""<h3>작성전략표 (7단계) — 페이지 제한: {esc(ws['page_limit'])}</h3>
<p class=hint>{esc(ws['rule'])}</p>
<table><tr><th>평가항목</th><th>배점</th><th>분량</th><th>심사위원이 보는 것</th><th>작성전략</th><th>증빙</th></tr>{wrows}</table>"""]
    draft = doc["draft"]
    if not draft.get("ready"):
        out.append(f'<div class=b-yel>본문 초안 미생성 — {esc(draft.get("reason", ""))}</div>')
    else:
        out.append(f"<h3>본문 초안 (8단계) — {esc(draft['status'])}</h3>"
                   f"<p><b>과제명(초안)</b>: {esc(draft['title'])}<br><b>한 줄 요약</b>: {esc(draft['summary'])}</p>")
        for s in draft["sections"]:
            tbl = ""
            if s.get("table"):
                t = s["table"]
                tbl = ("<table><tr>" + "".join(f"<th>{esc(h)}</th>" for h in t["head"]) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in t["rows"])
                       + "</table>")
            out.append(f"<h3>{esc(s['no'])}. {esc(s['title'])}</h3><p>{esc(s['body'])}</p>{tbl}"
                       f"<p class=hint>가이드: {esc(' / '.join(s['guide']))}</p>")
        if draft["sanitized"]:
            reps = "".join(f"<li>'{esc(x['term'])}' → '{esc(x['to'])}'</li>" for x in draft["sanitized"])
            out.append(f"<h3>위험 표현 자동 치환 (12단계)</h3><ul>{reps}</ul>")
        if draft["todos"]:
            out.append("<h3>초안 완성 전 할 일</h3><ol>"
                       + "".join(f"<li>{esc(t)}</li>" for t in draft["todos"]) + "</ol>")
    ev = doc["evidence_link"]
    erows = "".join(f"<tr><td>{esc(x['claim'])}</td><td>{esc(x['status'])}</td><td>{esc(x['use'])}</td></tr>" for x in ev["rows"])
    out.append(f"<h3>증빙 연결표 (9단계)</h3><table><tr><th>본문 주장</th><th>상태</th><th>사용 방법</th></tr>{erows}</table>")
    bt = doc["budget_table"]
    if bt.get("ready"):
        brows = "".join(f"<tr><td>{esc(x['item'])}</td><td>{esc(x['amount'])}</td><td>{esc(x['output'])}</td>"
                        f"<td>{esc(x['basis'])}</td><td>{esc(x['linked_item'])}</td><td>{esc(x['expected'])}</td></tr>"
                        for x in bt["rows"])
        out.append(f"<h3>연결형 예산표 (10단계)</h3><p class=hint>{esc(bt['flow'])}</p>"
                   f"<table><tr><th>항목</th><th>금액</th><th>산출물</th><th>산정 근거</th><th>연결 평가항목</th><th>기대성과</th></tr>{brows}</table>")
    else:
        out.append(f'<div class=b-yel>예산표 미생성 — {esc(bt.get("reason", ""))}</div>')
    fc = doc["final_check"]
    frows = "".join(f"<tr><td>{esc(x['q'])}</td><td>{esc(x['status'])}</td><td>{esc(x['note'])}</td></tr>" for x in fc["rows"])
    out.append(f"<h3>최종 점검 (13단계) — {esc(fc['verdict'])}</h3>"
               f"<table><tr><th>점검 질문</th><th>상태</th><th>비고</th></tr>{frows}</table>"
               f"<p class=hint>{esc(fc['note'])} · 전체 파일: 04_outputs/{esc(project)}/application_draft.md 등 (⑪ Export 탭)</p>")
    return "".join(out)


def _tab_present(project, res):
    pres = res.get("presentation")
    if not pres:
        return "<p>재분석이 필요하다 (하단 재분석 버튼).</p>"
    deck = pres["deck"]
    if not deck.get("ready"):
        return f'<div class=b-yel>발표자료 미생성 — {esc(deck.get("reason", ""))}</div>'
    srows = "".join(f"<tr><td>{s['no']}</td><td>{esc(s['title'])}</td><td><b>{esc(s['key_message'])}</b></td>"
                    f"<td>{'<br>'.join(esc(b) for b in s['bullets'])}</td><td>{esc(s['evidence'] or '-')}</td><td>{s['seconds']}초</td></tr>"
                    for s in deck["slides"])
    script = pres["script"]
    sc = ""
    if script.get("ready"):
        body = "".join(f"<h3 style='margin-top:10px'>{s['no']}. {esc(s['title'])} ({s['seconds']}초)</h3>"
                       f"<p>{esc(s['text'])}</p><p class=hint>반드시 말할 것: {esc(s['must_say'])}</p>"
                       for s in script["slides"])
        comp = "".join(f"<li>{esc(c['text'])}</li>" for c in script["compressed"])
        sc = (f"<h3>발표 대본 (15단계)</h3><p><b>시작:</b> {esc(script['opening'])}</p>{body}"
              f"<p><b>마무리:</b> {esc(script['closing'])}</p>"
              f"<h3>압축 대본 (슬라이드당 1문장)</h3><ol>{comp}</ol>"
              f"<p class=hint>쉬운 말 버전: presentation_script.md 참조 · {esc(script['todo'])}</p>")
    return f"""<h3>발표자료 구성 (14단계) — 총 {deck['total_seconds'] // 60}분 / 발표 여부: {esc(deck['presentation_required'])}</h3>
<p class=hint>{esc(deck['note'])}<br>원칙: {esc(' / '.join(deck['rules']))}</p>
<a class=btn href="/file/04_outputs/{esc(project)}/slides.pptx">⬇ PPTX 다운로드 (PowerPoint에서 열기)</a>
<table><tr><th>#</th><th>슬라이드</th><th>핵심 주장</th><th>불릿</th><th>증빙</th><th>시간</th></tr>{srows}</table>
{sc}"""


def _tab_rehearse(project, res):
    pres = res.get("presentation")
    reh = (pres or {}).get("rehearsal")
    deck = (pres or {}).get("deck", {})
    if not reh or not deck.get("ready"):
        return f'<div class=b-yel>발표연습기는 발표자료 생성 후 사용 가능 — {esc(deck.get("reason", "아이디어 선정 필요"))}</div>'
    slides_js = json.dumps([{"no": s["no"], "title": s["title"], "sec": s["seconds"],
                             "must": s["must_say"], "qs": s["questions"]}
                            for s in reh["per_slide"]], ensure_ascii=False)
    attacks = [x["q"] for x in reh["attack_questions"]]
    attacks_js = json.dumps(attacks, ensure_ascii=False)
    danger_js = json.dumps(engines.load_danger_terms(), ensure_ascii=False)
    w3 = "".join(f"<p><b>{esc(x['q'])}</b> <span class=hint>({esc(x['how'])})</span><br>→ {esc(x['answer'])}</p>" for x in reh["why3"])
    bd = "".join(f"<p><b>{esc(x['item'])}</b><br>→ {esc(x['answer'])}</p>" for x in reh["budget_defense"]) or "<p class=hint>예산 계획 입력 후 생성</p>"
    aq_rows = "".join(f"<tr><td>{esc(x['q'])}</td><td>{esc(x['status'])}</td><td>{esc(x['note'] or '-')}</td></tr>" for x in reh["attack_questions"])
    return f"""<h3>발표연습기 (16단계) — 총 {reh['total_seconds'] // 60}분</h3>
<p class=hint>모드: {esc(' / '.join(reh['modes']))} · 목적은 암기가 아니라 과장 없이 방어할 수 있게 만드는 것</p>

<h3>⏱ 시간 측정 발표 모드</h3>
<div class=slidebox>
  <div class=timer id=clock>00:00</div>
  <div id=slideinfo style="font-size:18px;margin:8px 0">시작 버튼을 누르면 슬라이드 1부터 진행</div>
  <div id=slidemust class=hint></div>
  <button type=button onclick="startRun()">▶ 발표 시작</button>
  <button type=button onclick="nextSlide()">다음 슬라이드 →</button>
  <button type=button class=warn onclick="stopRun()">■ 종료·리포트</button>
  <div id=report></div>
</div>

<h3>🗡 심사위원 공격 모드 + 위험 표현 감지</h3>
<div class=slidebox>
  <div id=attackq style="font-size:17px;font-weight:700">버튼을 누르면 공격 질문이 나온다</div>
  <button type=button onclick="drawQ()">공격 질문 뽑기</button>
  <label>내 답변을 소리 내 말한 뒤, 요지를 적어보기 (위험 표현 실시간 감지)</label>
  <textarea id=ans rows=3 oninput="scanDanger()"></textarea>
  <div id=dangerout class=hint>위험 표현 0건</div>
  <p class=hint>피드백 기준: {esc(' / '.join(reh['feedback_criteria']))}</p>
</div>

<h3>WHY 3종 방어 (모범 구조)</h3>{w3}
<h3>예산 방어</h3>{bd}
<h3>공격 질문 10 — 발화 상태</h3>
<table><tr><th>질문</th><th>상태</th><th>조건</th></tr>{aq_rows}</table>
<h3>모르는 질문 안전 문장</h3><pre>{esc(reh['unknown_answer'])}</pre>

<script>
const SLIDES={slides_js}, ATTACKS={attacks_js}, DANGER={danger_js};
let t0=null, idx=-1, laps=[], tick=null;
function fmtT(s){{return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}}
function startRun(){{t0=Date.now(); idx=-1; laps=[]; nextSlide();
  if(tick)clearInterval(tick);
  tick=setInterval(()=>{{const el=Math.floor((Date.now()-t0)/1000);
    document.getElementById('clock').textContent=fmtT(el);
    const s=SLIDES[idx]; if(!s)return;
    const spent=Math.floor((Date.now()-laps[idx].start)/1000);
    document.getElementById('clock').style.color=spent>s.sec?'#c0392b':'#1a1a2e';}},250);}}
function nextSlide(){{if(t0===null)return startRun();
  if(idx>=0)laps[idx].end=Date.now();
  idx++;
  if(idx>=SLIDES.length)return stopRun();
  laps.push({{start:Date.now(),end:null}});
  const s=SLIDES[idx];
  document.getElementById('slideinfo').textContent=s.no+'. '+s.title+' — 권장 '+s.sec+'초';
  document.getElementById('slidemust').textContent='반드시 말할 것: '+s.must+(s.qs.length?' · 예상 질문: '+s.qs.join(' / '):'');}}
function stopRun(){{if(tick)clearInterval(tick);
  if(idx>=0&&laps[idx]&&!laps[idx].end)laps[idx].end=Date.now();
  let rows='', over=[];
  laps.forEach((l,i)=>{{const s=SLIDES[i], sp=Math.round((l.end-l.start)/1000);
    const flag=sp>s.sec?' ⚠ 초과 '+(sp-s.sec)+'초':(sp<s.sec*0.4?' (너무 빨리 지나감)':'');
    if(sp>s.sec)over.push(s.title);
    rows+='<tr><td>'+s.no+'. '+s.title+'</td><td>'+s.sec+'초</td><td>'+sp+'초'+flag+'</td></tr>';}});
  document.getElementById('report').innerHTML='<h3>시간 리포트</h3><table><tr><th>슬라이드</th><th>권장</th><th>실제</th></tr>'+rows+'</table>'+
    (over.length?'<p><b>줄여야 할 슬라이드:</b> '+over.join(', ')+'</p>':'<p>시간 배분 양호 — 시간이 남으면 배점 높은 슬라이드를 보강하라</p>');
  t0=null;}}
function drawQ(){{const q=ATTACKS[Math.floor(Math.random()*ATTACKS.length)];
  document.getElementById('attackq').textContent='Q. '+q;}}
function scanDanger(){{const v=document.getElementById('ans').value; const hits=[];
  DANGER.forEach(t=>{{if(v.includes(t))hits.push(t);}});
  const o=document.getElementById('dangerout');
  if(hits.length){{o.innerHTML='<span style="color:#c0392b;font-weight:700">위험 표현 '+hits.length+'건: '+hits.join(', ')+'</span> — 대체: 위험을 줄임 / 단계적으로 확대 / 검토 후 진행';}}
  else{{o.textContent='위험 표현 0건';}}}}
</script>"""


def _tab_export(project, res):
    out = BASE / "04_outputs" / project
    rev = BASE / "05_reviews" / project
    files = [f"04_outputs/{project}/{p.name}" for p in sorted(out.glob("*")) if p.is_file()]
    files += [f"05_reviews/{project}/{p.name}" for p in sorted(rev.glob("*")) if p.is_file()]
    files += [f"10_handoff/HANDOFF_{project}.md"]
    links = "".join(f'<li><a href="/file/{esc(f)}">{esc(f)}</a></li>' for f in files)
    prompt = (out / "next_step_prompt.md")
    ptext = prompt.read_text(encoding="utf-8") if prompt.exists() else ""
    return f"""<h3>Export / HANDOFF</h3>
<p>모든 결과는 이미 저장소 파일로 저장돼 있다. 링크는 원문 보기·복사용.</p>
<ul>{links}</ul>
<h3>다음 실행 프롬프트 (AI 세션에 붙여넣기)</h3><pre>{esc(ptext)}</pre>"""


# ----------------------------------------------------------------- AI 화면

def screen_ai(msg: str = "") -> str:
    s = ai_engine.load_settings()
    mode = s.get("mode", "local")
    enabled = s.get("enabled", [])
    projects = "".join(f'<option value="{esc(p["name"])}">{esc(p["name"])}</option>' for p in list_projects())
    tasks = "".join(f'<option value="{k}">{esc(v[0])}</option>' for k, v in ai_engine.TASKS.items())
    costs = "".join(
        f"<tr><td>{p}</td><td>{c['model']}</td><td>약 {ai_engine.estimate_cost_krw(p, 'x' * 18000)['krw']}원</td></tr>"
        for p, c in ai_engine.COST_KRW_PER_1K.items())

    def rd(v, label, desc):
        return (f'<label style="font-weight:400"><input type=radio name=mode value="{v}" '
                f'{"checked" if mode == v else ""}> <b>{label}</b> — {desc}</label>')

    def cb(p):
        return (f'<label style="display:inline;font-weight:400;margin-right:14px">'
                f'<input type=checkbox name=en_{p} {"checked" if p in enabled else ""}> {p}</label>')

    saved = "저장된 키 있음 (암호화됨)" if ai_engine.has_saved_keys() else "저장된 키 없음"
    return f"""<div class=card><h2>🤖 AI 엔진 설정</h2>
{f'<div class=b-grn>{esc(msg)}</div>' if msg else ''}
<form method=post action="/ai_settings">
<h3>모드</h3>
{rd('local', '로컬', '규칙 엔진만 · 비용 0원 · 항상 동작 (기본)')}<br>
{rd('bridge', '브라우저 브리지', '로그인된 ChatGPT/Claude/Gemini 웹 활용 — 프롬프트 복사 → 응답 붙여넣기 (개인용 실험 기능)')}<br>
{rd('api', 'API', '내 API 키로 직접 호출 · 호출 전 예상 비용(원) 확인 필수')}<br>
{rd('hybrid', 'Hybrid', '구조 분석은 로컬, 고급 판단만 브리지/API + 캐시로 중복 호출 방지 (권장)')}
<h3>이번 달 사용 가능 AI (선택된 것만 라우팅, 실패 시 다음으로 폴백, 없으면 로컬)</h3>
{cb('openai')}{cb('claude')}{cb('gemini')}
<br><button>설정 저장</button></form>

<h3>예상 비용 (공고 1건 정밀 분석 기준, 원화)</h3>
<table><tr><th>제공자</th><th>모델</th><th>1회 예상</th></tr>{costs}</table>
<p class=hint>결제 기능 없음 — 비용은 각 AI 계정에서 직접 결제된다. 호출 전 항상 예상 비용을 표시하고 동의를 받는다.</p>

<h3>API 키 ({saved})</h3>
<form method=post action="/ai_keys">
<div class=grid>
<div><label>OpenAI 키</label><input type=password name=k_openai placeholder="sk-…"></div>
<div><label>Claude 키</label><input type=password name=k_claude placeholder="sk-ant-…"></div>
<div><label>Gemini 키</label><input type=password name=k_gemini placeholder="AIza…"></div>
<div><label>암호화 비밀번호 (저장 시 필수)</label><input type=password name=pw></div>
</div>
<button name=act value=save>암호화 저장</button>
<button name=act value=delete class=warn onclick="return confirm('저장된 키를 삭제할까요? (비밀번호 분실 시 이 방법뿐)')">저장 키 삭제</button>
<p class=hint>평문 저장 금지 — 비밀번호 기반 암호화(00_local/, git 제외). 키는 화면·로그·Export에 노출되지 않는다.
비밀번호를 잊으면 삭제 후 재입력.</p></form>
</div>

<div class=card><h2>고급 작업 실행 (브리지 / API)</h2>
<form method=get action="/ai_run">
<div class=grid>
<div><label>프로젝트</label><select name=p>{projects}</select></div>
<div><label>작업</label><select name=task>{tasks}</select></div>
</div>
<button>프롬프트 생성 →</button>
</form>
<p class=hint>브리지: 생성된 프롬프트를 복사해 ChatGPT/Claude/Gemini 웹에 붙여넣고, 응답을 다시 붙여넣으면
05_reviews/에 저장된다. API: 예상 비용 확인 후 호출.</p></div>"""


def screen_ai_run(project: str, task: str) -> str:
    data = load_input(project)
    res = load_results(project) or {}
    scoring = "\n".join(f"{s.get('item')}: {s.get('points')}점" for s in (res.get("notice", {}).get("scoring") or []))
    draft_md = ""
    doc = res.get("document", {})
    if doc.get("draft", {}).get("ready"):
        draft_md = "\n\n".join(f"## {s['title']}\n{s['body']}" for s in doc["draft"]["sections"])
    prompt = ai_engine.build_prompt(task, notice=(data.get("notice", {}).get("raw_text") or ""),
                                    scoring=scoring, draft=draft_md)
    s = ai_engine.load_settings()
    enabled = [p for p in s.get("enabled", []) if p in ai_engine.PROVIDERS]
    costs = "".join(f"<li>{p}: 약 {ai_engine.estimate_cost_krw(p, prompt)['krw']}원</li>" for p in enabled) or "<li>선택된 AI 없음 — 설정에서 체크</li>"
    return f"""<div class=card><h2>{esc(ai_engine.TASKS[task][0])} — {esc(project)}</h2>
<h3>① 브리지 (비용 0원 — 내 구독 웹 AI 이용)</h3>
<p class=hint>아래 프롬프트를 복사해 ChatGPT/Claude/Gemini 웹에 붙여넣어라.</p>
<textarea rows=10 onclick="this.select()">{esc(prompt)}</textarea>
<form method=post action="/ai_bridge/{esc(project)}/{esc(task)}">
<label>② 웹 AI의 응답 붙여넣기 → 저장</label>
<textarea name=answer rows=8 placeholder="AI 응답 전체를 붙여넣기"></textarea>
<button>응답 저장 (05_reviews)</button></form>
<h3>③ 또는 API 직접 호출 — 예상 비용</h3><ul>{costs}</ul>
<form method=post action="/ai_api/{esc(project)}/{esc(task)}">
<label>키 비밀번호 (저장된 키 복호화)</label><input type=password name=pw>
<p><label style="font-weight:400"><input type=checkbox name=agree required> 위 예상 비용(원)을 확인했고 API 호출에 동의한다</label></p>
<button>API 호출 실행</button></form>
<p class=hint>실패 시 선택된 다음 AI로 자동 폴백, 전부 실패하면 로컬 결과로 진행. 캐시 적중 시 0원.</p></div>"""


def _save_ai_review(project: str, task: str, provider: str, text: str) -> str:
    rev = BASE / "05_reviews" / project
    rev.mkdir(parents=True, exist_ok=True)
    p = rev / f"ai_{task}.md"
    label = ai_engine.TASKS[task][0]
    p.write_text(f"# AI {label}: {project}\n\n출처: {provider} / {date.today().isoformat()} / "
                 f"상태: DRAFT — 사람 검수 전 확정 금지\n\n{text}\n", encoding="utf-8")
    return f"05_reviews/{project}/{p.name}"


# --------------------------------------------------------------- sample data

def sample_input() -> dict:
    p = BASE / "07_samples" / "sample_app_input.json"
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ server

class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, code=200, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, loc: str):
        self.send_response(303)
        self.send_header("Location", loc)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # 조용히

    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        try:
            if not parts:
                return self._send(page("대시보드", screen_dashboard()))
            if parts[0] == "new":
                return self._send(page("새 프로젝트", screen_new()))
            if parts[0] == "upload":
                return self._send(page("공고 업로드", screen_upload()))
            if parts[0] == "ai":
                return self._send(page("AI 설정", screen_ai(parse_qs(u.query).get("msg", [""])[0])))
            if parts[0] == "ai_run":
                q = parse_qs(u.query)
                return self._send(page("AI 작업", screen_ai_run(q.get("p", [""])[0], q.get("task", ["notice_deep"])[0])))
            if parts[0] == "edit" and len(parts) == 2:
                return self._send(page(f"{parts[1]} 입력", screen_edit(parts[1])))
            if parts[0] == "project" and len(parts) == 2:
                tab = (parse_qs(u.query).get("tab", ["notice"]))[0]
                if tab not in dict(TABS):
                    tab = "notice"
                return self._send(page(parts[1], screen_project(parts[1], tab)))
            if parts[0] == "file":
                rel = "/".join(parts[1:])
                target = (BASE / rel).resolve()
                if not str(target).startswith(str(BASE)) or not target.is_file():
                    return self._send(page("404", "<div class=card>파일 없음</div>"), 404)
                ctype = {"json": "application/json; charset=utf-8",
                         "html": "text/html; charset=utf-8",
                         "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         "pdf": "application/pdf",
                         "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                         }.get(target.suffix.lstrip("."), "text/plain; charset=utf-8")
                return self._send(target.read_bytes(), 200, ctype)
            return self._send(page("404", "<div class=card>없는 화면</div>"), 404)
        except Exception as e:  # 오류는 화면에 정직하게
            return self._send(page("오류", f"<div class=card><div class=b-red>오류: {esc(e)}</div>"
                                           f"<p>입력 파일과 08_factory_tools/error_handling_rules.md를 확인해라.</p></div>"), 500)

    def do_POST(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" in ctype:
            form = {}
        else:
            form = parse_qs(raw_body.decode("utf-8")) if raw_body else {}
        try:
            if parts and parts[0] == "upload":
                fields, files = parse_multipart(ctype, raw_body)
                project = slugify(fields.get("project_name", ""))
                if not project:
                    return self._send(page("오류", "<div class=card><div class=b-red>프로젝트명이 필요하다</div></div>"), 400)
                if (BASE / "01_inputs" / project / "input.json").exists():
                    return self._send(page("오류", f"<div class=card><div class=b-red>'{esc(project)}' 이미 존재</div></div>"), 400)
                warnings, text, fname = [], fields.get("raw", ""), ""
                if not text and files:
                    _, fname, blob = files[0]
                    ext = extract_text(fname, blob)
                    text, warnings = ext["text"], ext["warnings"]
                    (BASE / "01_inputs" / project).mkdir(parents=True, exist_ok=True)
                    (BASE / "01_inputs" / project / f"원본_{Path(fname).name}").write_bytes(blob)
                parsed = parse_notice(text)
                parsed.setdefault("parse_notes", []).extend(warnings)
                data = {"project_name": project, "created_at": date.today().isoformat(),
                        "notice": notice_from_parsed(text, parsed, Path(fname).stem if fname else ""),
                        "applicant": {"name": "미확보", "duplicate_grant_history": "미확인",
                                      "tax_arrears": "미확인", "closed_biz_history": "미확인"},
                        "ideas": [], "evidence": {"owned": [], "planned": []}, "budget_plan": [],
                        "selected_idea_id": None,
                        "approvals": {"eligibility_confirmed": False, "idea_selected": False,
                                      "budget_confirmed": False, "final_submission_approved": False}}
                save_input(project, data)
                rerun(project)
                return self._redirect(f"/project/{project}")
            if parts and parts[0] == "ai_settings":
                s = ai_engine.load_settings()
                s["mode"] = (form.get("mode", ["local"]))[0]
                s["enabled"] = [p for p in ai_engine.PROVIDERS if f"en_{p}" in form]
                ai_engine.save_settings(s)
                return self._redirect("/ai?msg=설정 저장됨")
            if parts and parts[0] == "ai_keys":
                act = (form.get("act", ["save"]))[0]
                if act == "delete":
                    ai_engine.delete_keys()
                    return self._redirect("/ai?msg=저장 키 삭제됨 — 재입력 가능")
                pw = (form.get("pw", [""]))[0]
                if not pw:
                    return self._redirect("/ai?msg=암호화 비밀번호가 필요하다")
                keys = {p: (form.get(f"k_{p}", [""]))[0].strip() for p in ai_engine.PROVIDERS}
                keys = {k: v for k, v in keys.items() if v}
                if not keys:
                    return self._redirect("/ai?msg=입력된 키 없음")
                old = ai_engine.load_keys(pw) if ai_engine.has_saved_keys() else {}
                ai_engine.save_keys({**(old or {}), **keys}, pw)
                return self._redirect("/ai?msg=키 암호화 저장됨 (" + ", ".join(keys) + ")")
            if parts and parts[0] == "ai_bridge" and len(parts) == 3:
                ans = (form.get("answer", [""]))[0].strip()
                if not ans:
                    return self._redirect(f"/ai_run?p={parts[1]}&task={parts[2]}")
                rel = _save_ai_review(parts[1], parts[2], "브라우저 브리지(웹 AI)", ans)
                return self._send(page("저장됨", f'<div class=card><div class=b-grn>저장됨: {esc(rel)}</div>'
                                                f'<a class=btn href="/file/{esc(rel)}">열기</a> '
                                                f'<a class=btn href="/project/{esc(parts[1])}">프로젝트로</a></div>'))
            if parts and parts[0] == "ai_api" and len(parts) == 3:
                pw = (form.get("pw", [""]))[0]
                keys = ai_engine.load_keys(pw)
                if keys is None:
                    return self._send(page("오류", '<div class=card><div class=b-red>비밀번호가 틀렸다 — 분실 시 /ai에서 키 삭제 후 재입력</div></div>'), 403)
                if not keys:
                    return self._send(page("오류", '<div class=card><div class=b-red>저장된 키 없음 — /ai에서 먼저 저장</div></div>'), 400)
                data = load_input(parts[1])
                res = load_results(parts[1]) or {}
                scoring = "\n".join(f"{s.get('item')}: {s.get('points')}점" for s in (res.get("notice", {}).get("scoring") or []))
                doc = res.get("document", {})
                draft_md = "\n\n".join(f"## {s['title']}\n{s['body']}" for s in doc.get("draft", {}).get("sections", [])) if doc.get("draft", {}).get("ready") else ""
                prompt = ai_engine.build_prompt(parts[2], notice=(data.get("notice", {}).get("raw_text") or ""), scoring=scoring, draft=draft_md)
                r = ai_engine.run_api_task(prompt, keys)
                if not r["ok"]:
                    return self._send(page("실패", f'<div class=card><div class=b-yel>전 제공자 실패: {esc("; ".join(r["errors"]))}<br>{esc(r["fallback"])}</div></div>'))
                rel = _save_ai_review(parts[1], parts[2], f"{r['provider']} API" + (" (캐시)" if r.get("cached") else ""), r["text"])
                cost_txt = "캐시 적중 (0원)" if r.get("cached") else f"약 {r.get('krw', 0)}원"
                return self._send(page("완료", f'<div class=card><div class=b-grn>완료 — {esc(r["provider"])} '
                                              f'{cost_txt} → {esc(rel)}</div>'
                                              f'<a class=btn href="/file/{esc(rel)}">결과 열기</a></div>'))
            if parts and parts[0] == "create":
                data = form_to_input(form)
                project = data["project_name"]
                if not project:
                    return self._send(page("오류", "<div class=card><div class=b-red>프로젝트명이 필요하다</div></div>"), 400)
                # 아이디어 0개 허용 — 0단계(공고 분석·신청자 폼 생성) 모드로 저장된다
                if (BASE / "01_inputs" / project / "input.json").exists():
                    return self._send(page("오류", f"<div class=card><div class=b-red>'{esc(project)}' 이미 존재 — 기존 프로젝트는 덮어쓰지 않는다</div></div>"), 400)
                save_input(project, data)
                rerun(project)
                return self._redirect(f"/project/{project}")
            if parts and parts[0] == "run_sample":
                data = sample_input()
                project = data["project_name"]
                save_input(project, data)
                rerun(project)
                return self._redirect(f"/project/{project}")
            if parts and parts[0] == "rerun" and len(parts) == 2:
                rerun(parts[1])
                return self._redirect(f"/project/{parts[1]}")
            if parts and parts[0] == "update" and len(parts) == 2:
                data = load_input(parts[1])
                new = form_to_input(form)
                for k in ("applicant", "ideas", "evidence", "budget_plan"):
                    data[k] = new[k]
                if data.get("selected_idea_id") not in [i.get("id") for i in data["ideas"]]:
                    data["selected_idea_id"] = None
                    data.setdefault("approvals", {})["idea_selected"] = False
                save_input(parts[1], data)
                rerun(parts[1])
                return self._redirect(f"/project/{parts[1]}?tab=ideas")
            if parts and parts[0] == "approve" and len(parts) == 2:
                data = load_input(parts[1])
                sel = (form.get("selected_idea_id", [""]))[0]
                data["selected_idea_id"] = sel or None
                ap = data.setdefault("approvals", {})
                for k in ("idea_selected", "eligibility_confirmed", "budget_confirmed"):
                    ap[k] = k in form
                save_input(parts[1], data)
                rerun(parts[1])
                return self._redirect(f"/project/{parts[1]}?tab=lock")
            return self._send(page("404", "<div class=card>없는 동작</div>"), 404)
        except Exception as e:
            return self._send(page("오류", f"<div class=card><div class=b-red>오류: {esc(e)}</div></div>"), 500)


def _lan_ip() -> str | None:
    """휴대폰 접속용 이 PC의 LAN IP 추정 (실제 패킷 전송 없이 라우팅 정보만 조회)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def main():
    # 0.0.0.0 바인딩: 같은 와이파이의 휴대폰·다른 기기에서 접속 가능 (인터넷 공개 아님 — 공유기 밖에서는 접속 불가)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ip = _lan_ip()
    print(f"Hyemi Grant Factory 실행 중")
    print(f"  이 PC:        http://127.0.0.1:{PORT}")
    if ip:
        print(f"  휴대폰(같은 와이파이): http://{ip}:{PORT}")
    else:
        print(f"  휴대폰 접속: http://<이 PC의 IP>:{PORT}  (IP 확인: Windows=ipconfig, Mac/Linux=ifconfig)")
    print(f"  (중지: Ctrl+C · 방화벽 확인 창이 뜨면 '허용' 클릭)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
