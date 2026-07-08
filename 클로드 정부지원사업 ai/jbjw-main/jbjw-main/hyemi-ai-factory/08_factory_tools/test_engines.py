#!/usr/bin/env python3
"""test_engines.py — 엔진 단위 테스트 (stdlib assert 기반, pytest 불필요).

실행: python3 08_factory_tools/test_engines.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

BASE = engines.BASE
PASS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    PASS.append(cond)
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))


def sample():
    return json.loads((BASE / "07_samples" / "sample_app_input.json").read_text(encoding="utf-8"))


# 1. notice_analyzer
d = sample()
n = engines.notice_analyzer(d["notice"])
check("notice: raw_text 있으면 raw_ok", n["raw_ok"])
check("notice: 배점 최고 항목 식별", n["top_item"]["item"] == "실행계획·실현 가능성")
check("notice: 제출서류 미확인 → 확인 필요", any("제출서류" in x for x in n["needs"]))

d2 = sample()
d2["notice"]["raw_text"] = "미확보"
n2 = engines.notice_analyzer(d2["notice"])
check("notice: 원문 없으면 LOCK 금지 경고", any("LOCK 금지" in x for x in n2["needs"]))

# 2. applicant_risk_checker
r = engines.applicant_risk_checker(d["applicant"])
check("risk: 중복수혜 미확인 → 확인 필요", any("중복수혜" in x for x in r["needs"]))
check("risk: 체납 없음 → 차단 아님", not r["blockers"])
d3 = sample()
d3["applicant"]["tax_arrears"] = "있음"
r3 = engines.applicant_risk_checker(d3["applicant"])
check("risk: 체납 있음 → BLOCKED", len(r3["blockers"]) == 1)

# 3. dangerous_expression_scanner
hits = engines.dangerous_expression_scanner(d)
terms = {h["term"] for h in hits}
check("danger: '완벽히 해결' 검출 (idea3)", any("완벽" in t for t in terms), str(terms))
check("danger: 대체 표현 제안 포함", all(h["replacement"] for h in hits))

# 4. idea_evaluator
ie = engines.idea_evaluator(d, n)
by = {i["id"]: i for i in ie["items"]}
check("ideas: idea1 추천 후보", by["idea1"]["verdict"] == "추천 후보", by["idea1"]["verdict"])
check("ideas: idea3 탈락 후보 (적합성 낮음+증빙 0)", by["idea3"]["verdict"] == "탈락 후보", by["idea3"]["verdict"])
check("ideas: 추천 = idea1", ie["recommend"]["id"] == "idea1")
ie2 = engines.idea_evaluator(d2, n2)
check("ideas: 원문+목적 없으면 적합성 None", ie2["items"][0]["scores"]["공고 적합성"] is None
      if engines.is_missing(d2["notice"].get("purpose")) else True)

# 5. budget_risk_checker
b = engines.budget_risk_checker(d)
check("budget: 장비 구매 → 단순 구매성 플래그", any("단순 구매" in f for row in b["rows"] for f in row["flags"]))
check("budget: 개발비 금액 미확보 → 견적 필요", any(row["quote_needed"] for row in b["rows"]))
b0 = engines.budget_risk_checker({"budget_plan": []})
check("budget: 계획 없음 → 판정 불가 경고", any("판정 불가" in x for x in b0["needs"]))

# 6. lock_engine — 미승인 상태
lk = engines.lock_engine(d, n, r, ie, b, hits)
check("lock: 미승인 → DRAFT + 불가 사유 존재", lk["status"] == "DRAFT" and len(lk["block_reasons"]) >= 3)
# 승인해도 위험표현·견적 문제가 남으면 LOCK 불가
d4 = sample()
d4["selected_idea_id"] = "idea1"
d4["approvals"].update(eligibility_confirmed=True, idea_selected=True, budget_confirmed=True)
lk4 = engines.lock_engine(d4, n, engines.applicant_risk_checker(d4["applicant"]),
                          engines.idea_evaluator(d4, n), engines.budget_risk_checker(d4),
                          engines.dangerous_expression_scanner(d4))
check("lock: 승인해도 위험 표현 있으면 불가", not lk4["can_lock"])
# 원문 없으면 절대 불가
lk5 = engines.lock_engine(d4, n2, r, ie, b, [])
check("lock: 공고 원문 없으면 절대 불가", not lk5["can_lock"]
      and any("원문" in x for x in lk5["block_reasons"]))

# 7. judge_review_engine
j = engines.judge_review_engine(d, n, r, ie, b, hits)
check("judge: 배점 합계 100", j["max"] == 100)
check("judge: 예산 근거 부족 감점 반영", any("예산 근거 부족" in x["why"] for x in j["rows"]))
check("judge: 판정은 보완/불가 (완벽 아님)", "가능" not in j["verdict"] or "보완" in j["verdict"], j["verdict"])
j2 = engines.judge_review_engine(d2, n2, r, engines.idea_evaluator(d2, n2), b, [])
check("judge: 원문 없으면 제출 불가 고정", "제출 불가" in j2["verdict"], j2["verdict"])

# 8. qna / titles / export
q = engines.qna_generator(d, n, ie, b)
check("qna: 10문항", len(q) == 10)
check("qna: 예산 질문 발화 금지 (견적 없음)", any(x["status"] == "발화 금지" for x in q if "예산" in x["question"]))
t = engines.title_generator(d["ideas"][0], d["applicant"])
check("titles: 과제명 후보 5개", len(t) == 5)

res = engines.analyze_all(d)
check("analyze_all: 15종 키 존재", all(k in res for k in
      ("notice", "risk", "danger", "ideas", "budget", "lock", "judge", "qna",
       "revision", "titles", "summaries", "missing_evidence")))
check("revision: 1순위에 위험 표현 포함", any("위험 표현" in x for x in res["revision"]["p1"]))
check("revision: idea3 본문 혼입 금지", any("idea3" in x for x in res["revision"]["quarantine"]))

# 9. 0단계 (신청자·아이디어 미입력) — 실전 초기 상태
d0 = sample()
d0["ideas"] = []
d0["applicant"] = {"name": "미확보", "duplicate_grant_history": "미확인", "tax_arrears": "미확인"}
r0 = engines.analyze_all(d0)
check("stage0: 플래그 켜짐", r0["stage0"] is True)
check("stage0: 심사 판정 불가 고정", "판정 불가" in r0["judge"]["verdict"], r0["judge"]["verdict"])
check("stage0: LOCK 불가 사유에 아이디어 미입력", any("아이디어 후보 미입력" in x for x in r0["lock"]["block_reasons"]))
check("stage0: 재작업 1순위 첫 항목 = 신청자 입력", "신청자·아이디어" in r0["revision"]["p1"][0])
check("stage0: 신청자 폼 생성 (결격 체크 포함)", "결격 사유 체크" in r0["applicant_form_md"])
check("strategy: 배점군 최고 식별", r0["strategy"]["top"]["item"] == "실행계획·실현 가능성"
      if r0["strategy"]["internal"] else r0["strategy"]["top"]["points"] >= 20)

# 10. 서류 라인 (7~13단계)
import re as _re
import draft_engine
res_full = engines.analyze_all(sample())
doc = res_full["document"]
check("draft: 초안 생성됨 (추천 후보 기반)", doc["draft"]["ready"] is True)
check("draft: 본문 6절", len(doc["draft"]["sections"]) == 6)
check("draft: 작성전략표 배점군별 행", len(doc["writing_strategy"]["rows"]) >= 3)
check("draft: 연결형 예산표 생성", doc["budget_table"]["ready"] is True)
check("draft: 예산 행마다 연결 평가항목 존재", all(r["linked_item"] for r in doc["budget_table"]["rows"]))
san, reps = draft_engine.sanitize_text("이 문제를 완벽히 해결하고 100% 가능하다")
check("sanitize: 위험 표현 치환", "완벽히 해결" not in san and "100%" not in san, san)
check("sanitize: 치환 기록 남김", len(reps) >= 2)
check("final_check: 점검 질문 9종", len(doc["final_check"]["rows"]) == 9)

# 11. 발표 라인 (14~16단계)
pres = res_full["presentation"]
check("deck: 슬라이드 11장", len(pres["deck"]["slides"]) == 11)
check("deck: 슬라이드별 권장 시간 배분", all(s["seconds"] > 0 for s in pres["deck"]["slides"]))
check("script: 대본 3종 (풀·압축·쉬운말)", pres["script"]["ready"]
      and len(pres["script"]["compressed"]) == 11 and len(pres["script"]["easy"]) == 11)
check("rehearsal: WHY 3종 방어 답변", len(pres["rehearsal"]["why3"]) == 3
      and all(x["answer"] for x in pres["rehearsal"]["why3"]))
check("rehearsal: 예산 방어 항목별 생성", len(pres["rehearsal"]["budget_defense"]) >= 1)
check("rehearsal: 공격 질문 10종 상태 포함", len(pres["rehearsal"]["attack_questions"]) == 10)

# 12. 파이프라인 17단계
pl = res_full["pipeline"]
check("pipeline: 0~16단계 17개", len(pl) == 17 and pl[0]["no"] == 0 and pl[-1]["no"] == 16)
check("pipeline: 8단계(본문) 완료 표시", next(p for p in pl if p["no"] == 8)["status"] == "done")
# stage0에서는 서류·발표 라인이 잠긴다
r0b = engines.analyze_all(d0)
check("stage0: 초안 미생성 (섞임 방지)", r0b["document"]["draft"]["ready"] is False)
check("stage0: 발표자료 미생성", r0b["presentation"]["deck"]["ready"] is False)
check("stage0: 파이프라인 3단계 대기", next(p for p in r0b["pipeline"] if p["no"] == 3)["status"] == "todo")

# 13. PPTX 생성 (표준 라이브러리 zip)
import tempfile
import xml.dom.minidom
import zipfile
from pptx_writer import write_pptx
with tempfile.TemporaryDirectory() as td:
    p = write_pptx(Path(td) / "t.pptx", "test", pres["deck"]["slides"])
    z = zipfile.ZipFile(p)
    check("pptx: zip 손상 없음", z.testzip() is None)
    check("pptx: 슬라이드 11장 포함", sum(1 for n in z.namelist() if _re.match(r"ppt/slides/slide\d+\.xml$", n)) == 11)
    ok = True
    for name in z.namelist():
        try:
            xml.dom.minidom.parseString(z.read(name))
        except Exception:
            ok = False
    check("pptx: 전체 XML 유효", ok)

# 14. 문서 추출 (doc_extract)
import zipfile as _zf
from io import BytesIO
from doc_extract import extract_text
_buf = BytesIO()
with _zf.ZipFile(_buf, "w") as z:
    z.writestr("word/document.xml",
               "<w:document><w:body><w:p><w:r><w:t>2026년 지원사업 공고</w:t></w:r></w:p>"
               "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>성장가능성</w:t></w:r></w:p></w:tc>"
               "<w:tc><w:p><w:r><w:t>40점</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>")
r_dx = extract_text("a.docx", _buf.getvalue())
check("extract: DOCX 텍스트+표 추출", "지원사업 공고" in r_dx["text"] and "성장가능성" in r_dx["text"])
r_bad = extract_text("x.pdf", b"broken")
check("extract: 손상 파일도 예외 없이 경고 반환", isinstance(r_bad["warnings"], list) and len(r_bad["warnings"]) >= 1)
check("extract: 이미지 → OCR 안내", "OCR" in " ".join(extract_text("a.png", b"x")["warnings"]))

# 15. 공고 파서 (notice_parser)
from notice_parser import notice_character, parse_notice
SAMPLE = """2026년 소상공인 디지털 전환 지원사업 공고
1. 사업목적
소상공인의 디지털 기술 도입을 지원하여 경영 효율화와 매출 성장을 도모
2. 신청자격
공고일 기준 사업자등록을 보유한 소상공인
3. 지원제외
국세 체납자, 단순 물품 구매 목적 신청은 제외
4. 접수기간
2026. 8. 1. ~ 2026. 8. 29. 18:00까지 마감
5. 평가기준
성장가능성 (40점) / 디지털 적합성 (30점) / 수행 역량 (30점)
6. 제출서류
- 사업계획서 1부
- 사업자등록증명
발표평가: 대면 평가 실시 (사업계획서 15페이지 이내)
"""
pn = parse_notice(SAMPLE)
check("parser: 배점표 자동 추출 (합계 100)", sum(s["points"] for s in pn.get("scoring", [])) == 100, str(pn.get("scoring")))
check("parser: 마감일 감지", pn.get("apply_deadline") == "2026-08-29", pn.get("apply_deadline"))
check("parser: 제출서류·페이지 제한", len(pn.get("documents", [])) >= 2 and "15" in pn.get("page_limit", ""))
check("parser: 자격·제외 섹션", "사업자등록" in pn.get("eligibility", "") and "체납" in pn.get("exclusions", ""))
ch = notice_character(SAMPLE, pn.get("scoring", []))
check("character: 사업 성격 분류", any("디지털" in t or "소상공인" in t for t in ch["purpose_type"]), str(ch["purpose_type"]))
check("character: 심사 의도 = 배점 상위 해석", any("성장" in x for x in ch["review_intent"]))
check("character: 위험 전략 (공고 근거)", any("구매" in x for x in ch["risky_moves"]), str(ch["risky_moves"]))

# 16. AI 엔진 — 키 암호화·비용·설정 (네트워크 호출 없음)
import ai_engine
import tempfile as _tmp
from pathlib import Path as _P
with _tmp.TemporaryDirectory() as td:
    ai_engine.LOCAL_DIR = _P(td)
    ai_engine.KEYS_FILE = _P(td) / "k.enc"
    ai_engine.SETTINGS_FILE = _P(td) / "s.json"
    ai_engine.CACHE_DIR = _P(td) / "c"
    ai_engine.save_keys({"openai": "sk-test-1234567890abcd"}, "pw1")
    check("ai: 키 암호화 저장 → 평문 미노출", "sk-test" not in ai_engine.KEYS_FILE.read_text())
    check("ai: 올바른 비번 복호화", ai_engine.load_keys("pw1")["openai"].endswith("abcd"))
    check("ai: 틀린 비번 → None (무결성)", ai_engine.load_keys("wrong") is None)
    est = ai_engine.estimate_cost_krw("claude", "가" * 3000)
    check("ai: 원화 비용 추정", est["krw"] > 0 and est["in_tokens"] == 1000)
    ai_engine.cache_put("p1", "openai", "답")
    check("ai: Hybrid 캐시 적중", ai_engine.cache_get("p1", "openai") == "답")
    ai_engine.save_settings({"mode": "hybrid", "enabled": []})
    r = ai_engine.run_api_task("질문", {})
    check("ai: 사용 가능 AI 없음 → 로컬 폴백 안내", r["ok"] is False and "로컬" in r["fallback"])

# 17. 실패 격리 — 깨진 입력에도 analyze_all이 결과를 낸다
broken = {"notice": {"raw_text": 12345, "scoring": "이상한값"}, "ideas": [{"id": None}], "budget_plan": "x"}
rb = engines.analyze_all(broken)
check("isolation: 깨진 입력에도 결과 반환", "pipeline" in rb and "judge" in rb)
check("isolation: 오류 목록 기록", isinstance(rb.get("engine_errors"), list))

# 18. DOCX Export
from docx_writer import write_docx
import xml.dom.minidom as _dom
with _tmp.TemporaryDirectory() as td:
    p = write_docx(_P(td) / "t.docx", "테스트", [("h1", "절1"), ("p", "본문"),
                                                ("table", {"head": ["a"], "rows": [["b"]]})])
    z = _zf.ZipFile(p)
    check("docx: zip 유효", z.testzip() is None)
    _dom.parseString(z.read("word/document.xml"))
    check("docx: XML 유효 + 내용 포함", "절1" in z.read("word/document.xml").decode())

print(f"\n결과: {sum(PASS)}/{len(PASS)} 통과")
sys.exit(0 if all(PASS) else 1)
