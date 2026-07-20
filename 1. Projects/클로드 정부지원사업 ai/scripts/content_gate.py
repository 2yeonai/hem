# -*- coding: utf-8 -*-
"""
content_gate.py — 정부지원 공장 '내용 품질 게이트' (2026-07-20 신설, [gombeck1])

배경: 외부감사(초창패_예창패_초안 평가_2026-07-19.md)가 지적한 부실 초안의
구조적 원인 4가지를 결정론적 코드로 막는다. LLM 호출 없음(비용 0).
  ① 시장규모 10배 계산 오류 → verify_arithmetic()
  ② 예창패·초창패 복사본 생성 → check_scenario_separation()
  ③ 사실/가정/목표 혼용, 증빙 없는 수치 → check_evidence_ledger(), find_unlabeled_numbers()
  ④ 내부 메모가 제출본에 노출 → split_outputs()
  ⑤ 입력 부족한 채 초안 생성 → diagnose_input_sufficiency()

run.py를 건드리지 않는 독립 모듈(대형 파일 편집 잘림 버그 회피).
사용: python3 scripts/content_gate.py --self-test
"""

import re
import difflib

# ---------------------------------------------------------------------------
# 상태값 어휘 (외부감사 지시 3번)
# ---------------------------------------------------------------------------
CLAIM_STATUSES = (
    "verified_fact",          # 증빙 가능한 실제 사실 → 현재 실적으로 작성 가능
    "user_confirmed",         # 사용자가 확인한 사실 → 사실로 작성 + 증빙 필요 표시
    "simulation_assumption",  # 가상 지원용 설정 → 가상 시나리오에서만 현재 실적으로
    "planned_target",         # 협약기간 목표 → 미래형으로만 작성
    "ai_suggestion",          # AI 제안 수치 → 사용자 승인 전 본문 금지
    "needs_evidence",         # 근거 부족 → [근거 필요] 표시
    "prohibited",             # 본문 사용 금지
)

FACT_LIKE = {"verified_fact", "user_confirmed"}
NEVER_IN_SUBMISSION = {"ai_suggestion", "needs_evidence", "prohibited"}

# ---------------------------------------------------------------------------
# ① 산술 검증 — "N(~M)개(소) × K만원 (× 12개월) = X억(~Y억)원" 재계산
# ---------------------------------------------------------------------------
_NUM = r"([\d,.]+)"

def _to_won(num_str, unit):
    v = float(num_str.replace(",", ""))
    return v * {"만원": 1e4, "억원": 1e8, "억": 1e8, "천만원": 1e7, "원": 1}[unit]

def _fmt_won(v):
    if v >= 1e8:
        s = v / 1e8
        return ("%.1f" % s).rstrip("0").rstrip(".") + "억원"
    return ("%.0f" % (v / 1e4)) + "만원"

def verify_arithmetic(text):
    """시장규모/매출 산식 패턴을 찾아 재계산. 불일치 목록 반환(비면 통과).

    잡아야 하는 실제 사례(2026-07 초안):
      '300~500개 × 월 구독료 5만원 = 연간 SAM 18억~30억원'  → 실제 1.8억~3억원
    """
    problems = []
    pat = re.compile(
        _NUM + r"\s*(?:~\s*" + _NUM + r")?\s*(?:개소|개|곳|명|업체)\s*[×xX*]\s*(?:월\s*)?(?:구독료\s*)?"
        + _NUM + r"\s*(만원|천만원|억원)"
        + r"(?:\s*[×xX*]\s*12\s*개월)?"
        + r"[^0-9]{0,40}?" + _NUM + r"\s*(?:~\s*" + _NUM + r"\s*)?억원?"
    )
    for m in pat.finditer(text):
        lo, hi, price, unit, r_lo, r_hi = m.groups()
        months = 12 if ("12개월" in m.group(0) or "연" in text[max(0, m.start() - 15): m.end() + 5]) else 1
        p = _to_won(price, unit)
        calc_lo = float(lo.replace(",", "")) * p * months
        calc_hi = float((hi or lo).replace(",", "")) * p * months
        stated_lo = float(r_lo.replace(",", "")) * 1e8
        stated_hi = float((r_hi or r_lo).replace(",", "")) * 1e8
        ok_lo = abs(calc_lo - stated_lo) / max(calc_lo, 1) < 0.15
        ok_hi = abs(calc_hi - stated_hi) / max(calc_hi, 1) < 0.15
        if not (ok_lo and ok_hi):
            problems.append({
                "type": "arithmetic_error",
                "expr": m.group(0)[:120],
                "stated": "%s~%s" % (_fmt_won(stated_lo), _fmt_won(stated_hi)),
                "recalculated": "%s~%s" % (_fmt_won(calc_lo), _fmt_won(calc_hi)),
                "action": "문서 생성 중단 — 수치를 재계산 값으로 수정하거나 산식을 고칠 것",
            })
    return problems

def verify_budget_total(items, stated_total_manwon):
    """예산 항목 합계 검증. items: [(비목, 금액_만원)], stated_total_manwon: 명시된 합계."""
    total = sum(a for _, a in items)
    if abs(total - stated_total_manwon) > 0.5:
        return [{
            "type": "budget_sum_error",
            "sum_of_items": total, "stated_total": stated_total_manwon,
            "action": "항목 합계와 명시 총액 불일치 — 초안 생성 중단",
        }]
    return []

# ---------------------------------------------------------------------------
# ② 예창패·초창패 시나리오 분리 (외부감사 지시 2·9·11번)
# ---------------------------------------------------------------------------
CHOCHANG_REQUIRED_CURRENT = (
    "business_reg_date",   # 사업자등록일
    "product_stage",       # MVP/상용화 등 (아이디어/목업이면 부적합)
    "pilot_companies",     # 시범업체 수 (>0)
    "active_users",        # 사용자 수 (>0)
    "usage_records",       # 누적 기록 건수 (>0)
    "paying_customers",    # 유료 고객 수 (>0)
    "monthly_revenue",     # 월 반복매출 (>0)
)

def check_scenario(scenario):
    """application_scenario 최소 요건 검사(작성 시작 전 게이트)."""
    errs = []
    ptype = scenario.get("program_type")
    if ptype not in ("예비창업패키지", "초기창업패키지"):
        errs.append("program_type이 예비창업패키지/초기창업패키지 중 하나가 아님")
        return errs
    if ptype == "초기창업패키지":
        cur = scenario.get("current_performance") or {}
        for k in CHOCHANG_REQUIRED_CURRENT:
            v = cur.get(k)
            if v in (None, "", 0):
                errs.append(
                    "초창패 시나리오에 현재 성과 '%s'가 없음 — 이 상태로 쓰면 예창패 복사본이 됨. "
                    "가상 지원이면 simulation_assumption으로라도 값을 정할 것" % k)
        if scenario.get("simulation_mode") is None:
            errs.append("simulation_mode(실제/가상 여부) 미지정")
        if str(cur.get("product_stage", "")) in ("아이디어", "목업"):
            errs.append("초창패인데 제품 단계가 '%s' — 초기창업기업 성과로 인정 불가" % cur.get("product_stage"))
    return errs

def check_scenario_separation(draft_a, draft_b, threshold=0.80):
    """예창패/초창패 두 초안이 사실상 같은 문서인지 검사(외부감사: '예산만 키운 복사본')."""
    ratio = difflib.SequenceMatcher(None, draft_a, draft_b).ratio()
    if ratio >= threshold:
        return [{
            "type": "program_clone_error",
            "similarity": round(ratio, 3),
            "action": "두 프로그램 초안 유사도 %.0f%% — 현재실적·협약목표·예산 논리를 단계별로 다르게 재생성할 것" % (ratio * 100),
        }]
    return []

# ---------------------------------------------------------------------------
# ③ 증빙 원장 + 출처 없는 수치 차단 (외부감사 지시 3·4번)
# ---------------------------------------------------------------------------
def check_evidence_ledger(ledger):
    """evidence_ledger 항목 검사. 항목: {claim, status, evidence_type, source_file, usable_in_submission}"""
    errs = []
    for i, e in enumerate(ledger):
        st = e.get("status")
        if st not in CLAIM_STATUSES:
            errs.append("원장 #%d: status '%s'는 허용 어휘가 아님 %s" % (i, st, list(CLAIM_STATUSES)))
            continue
        if st in NEVER_IN_SUBMISSION and e.get("usable_in_submission"):
            errs.append("원장 #%d (%s): status=%s는 제출본 사용 불가인데 usable_in_submission=true" % (i, e.get("claim", "")[:30], st))
        if st in FACT_LIKE and not (e.get("source_file") or e.get("evidence_type")):
            errs.append("원장 #%d (%s): 사실(status=%s)로 표시했으나 출처/증빙 종류가 없음" % (i, e.get("claim", "")[:30], st))
    return errs

_FUTURE_MARKERS = ("목표", "예정", "계획", "검증", "가설", "확보함", "추진함")

def find_unlabeled_numbers(text, ledger):
    """본문 속 정량 주장 문장 중 원장에 없는 것을 찾는다(사실형 서술 차단용).

    간이 규칙: 숫자+단위(분/시간/%/건/곳/명/원)를 포함한 문장이
      - 원장의 claim 키워드와도 매칭되지 않고
      - 미래형 표지(목표/예정/계획/검증)도 없으면 → 근거 없는 사실형 수치로 플래그.
    """
    flags = []
    claims = [c.get("claim", "") for c in ledger]
    for sent in re.split(r"(?<=[.함음됨임])\s+|\n", text):
        if not re.search(r"\d[\d,.]*\s*(분|시간|%|건|곳|명|만원|억|회)", sent):
            continue
        if any(m in sent for m in _FUTURE_MARKERS):
            continue
        matched = any(_claim_overlap(c, sent) for c in claims if c)
        if not matched:
            flags.append({"type": "unlabeled_number", "sentence": sent.strip()[:100],
                          "action": "원장에 등록하고 상태값을 부여하거나, 목표/예정형으로 고칠 것"})
    return flags

def _claim_overlap(claim, sent):
    nums_c = set(re.findall(r"\d[\d,.]*", claim))
    nums_s = set(re.findall(r"\d[\d,.]*", sent))
    return bool(nums_c & nums_s)

# ---------------------------------------------------------------------------
# ④ 내부본/제출본 분리 (외부감사 지시 13번 + 최종 지시)
# ---------------------------------------------------------------------------
INTERNAL_MARKERS = (
    "⚠", "※", "[확인 필요]", "[근거 필요]", "외부감사", "외부 검토", "탈락", "재사용하지 않았음",
    "JSON", "json", "계산 오류", "미반영", "판단 보류", "가상 시나리오", "simulation", "내부 검토",
    "AI가", "자동화가", "초안임",
)

def split_outputs(text):
    """문단 단위로 내부 마커 포함 문단을 내부검토본으로 이동. (제출용, 내부검토본) 반환."""
    submission, internal = [], []
    for para in text.split("\n"):
        if any(m in para for m in INTERNAL_MARKERS):
            internal.append(para)
        else:
            submission.append(para)
    return "\n".join(submission).strip(), "\n".join(internal).strip()

# ---------------------------------------------------------------------------
# ⑤ 입력 충분성 진단 (외부감사 지시 5번 + '앞으로 입력해야 할 최소 정보' 표)
# ---------------------------------------------------------------------------
REQUIRED_INPUTS = (
    ("program_type",       "지원사업 (예창패/초창패)"),
    ("reference_date",     "가상 기준일"),
    ("business_status",    "사업자 상태 (미등록/등록일)"),
    ("product_stage",      "제품 상태 (아이디어/목업/MVP/상용화)"),
    ("customer_validation","고객검증 실제 조사 수 (산모·관리사·업체)"),
    ("deal_evidence",      "거래성과 (의향서·MOU·계약·유료고객)"),
    ("usage_performance",  "사용성과 (업체 수·사용자 수·기록 건수)"),
    ("revenue",            "매출성과 (누적·월·구독)"),
    ("founder_capability", "대표자 역량 (판매·마케팅·자격·현장경험)"),
    ("team",               "팀 (인력·외주·자문·채용계획)"),
    ("pricing",            "가격 (검증 가격·목표 가격)"),
    ("primary_market",     "1차 시장 (지불고객 정확히 한 종류)"),
    ("evidence_status",    "증빙상태 (완료/진행/목표/가정)"),
    ("prohibitions",       "금지사항 (의료표현·과장·미확인 수치)"),
)

def diagnose_input_sufficiency(inputs):
    """작성 전 필수 진단. 반환: {level_pct, ready, missing, verdict}"""
    filled, missing = [], []
    for key, label in REQUIRED_INPUTS:
        v = inputs.get(key)
        (filled if v not in (None, "", [], {}) else missing).append(label)
    pct = round(100.0 * len(filled) / len(REQUIRED_INPUTS))
    return {
        "level_pct": pct,
        "ready": filled,
        "missing": missing,
        "verdict": ("작성 가능" if pct == 100 else
                    "부족 항목을 가정값 후보로 제안 후, 가정임을 표시하고 진행" if pct >= 60 else
                    "작성 중단 — 입력 보강 필요"),
    }

# ---------------------------------------------------------------------------
# ⑥ 고객군·범위 일관성 (외부감사 지시 8·9번)
# ---------------------------------------------------------------------------
CUSTOMER_TERMS = ("산후도우미 업체", "산후조리원", "출장 산후마사지", "피부미용업",
                  "에이전시", "방문형 산후케어 업체", "산후 홈케어 업체", "육아돌봄")

def check_customer_consistency(paying_customer_text):
    hits = [t for t in CUSTOMER_TERMS if t in paying_customer_text]
    errs = []
    if len(hits) > 1:
        errs.append({"type": "customer_mix", "found": hits,
                     "action": "지불고객은 정확히 한 종류로 고정하고 나머지는 확장시장/연계정보로 분리"})
    if "피부미용업" in paying_customer_text:
        errs.append({"type": "scope_risk", "found": "피부미용업",
                     "action": "B2B SaaS 계획서에 피부미용업 신고 문구 금지 — 소프트웨어 개발·공급업으로"})
    return errs

# ---------------------------------------------------------------------------
# self test
# ---------------------------------------------------------------------------
def _self_test():
    fails = []

    # T1. 시장규모 10배 오류 → 탐지돼야 함
    bad = "업체 300~500개 × 월 구독료 5만원 × 12개월 = 연간 SAM 18~30억원 규모"
    good = "업체 300~500개 × 월 구독료 5만원 × 12개월 = 연간 SAM 1.8~3억원 규모"
    if not verify_arithmetic(bad): fails.append("T1a: 10배 오류 미탐지")
    if verify_arithmetic(good): fails.append("T1b: 정상 계산을 오탐")

    # T2. 예산 합계
    items = [("개발", 4500), ("마케팅", 1500), ("자문", 1000), ("조사", 1000), ("기타", 1000), ("확장", 1000)]
    if verify_budget_total(items, 10000): fails.append("T2a: 정상 합계 오탐")
    if not verify_budget_total(items, 9000): fails.append("T2b: 합계 오류 미탐지")

    # T3. 초창패 시나리오 — 현재 성과 없으면 차단
    empty = {"program_type": "초기창업패키지", "simulation_mode": True, "current_performance": {}}
    full = {"program_type": "초기창업패키지", "simulation_mode": True, "current_performance": {
        "business_reg_date": "2025-09-01", "product_stage": "MVP", "pilot_companies": 3,
        "active_users": 10, "usage_records": 150, "paying_customers": 1, "monthly_revenue": 200000}}
    if not check_scenario(empty): fails.append("T3a: 빈 초창패 시나리오 통과됨")
    if check_scenario(full): fails.append("T3b: 정상 초창패 시나리오 차단됨")

    # T4. 복사본 감지
    a = "문제인식 A. 솔루션 B. 시장 C. 팀 D. " * 30
    if not check_scenario_separation(a, a): fails.append("T4a: 동일 문서 미탐지")
    b = "초기창업기업 현재 실적: MVP 운영, 유료 1곳, 기록 150건. 협약목표: 유료 10곳, 고도화. " * 30
    if check_scenario_separation(a, b): fails.append("T4b: 다른 문서를 복사본으로 오탐")

    # T5. 증빙 원장
    ledger = [
        {"claim": "인수인계 15분 소요", "status": "needs_evidence", "usable_in_submission": True},
        {"claim": "제품 3종 100만개 판매", "status": "user_confirmed", "evidence_type": "판매기록"},
    ]
    errs = check_evidence_ledger(ledger)
    if not errs: fails.append("T5a: needs_evidence의 제출 사용을 차단 못함")
    if len(errs) != 1: fails.append("T5b: 정상 항목까지 차단")

    # T6. 출처 없는 수치 사실형 서술
    text = "업체당 인수인계에 평균 15분이 소요됨. 확인시간 50% 단축을 목표로 검증할 계획임."
    flags = find_unlabeled_numbers(text, [])
    if len(flags) != 1: fails.append("T6: 사실형 1건만 잡아야 하는데 %d건" % len(flags))

    # T7. 내부본/제출본 분리
    doc = "○ 고객 문제 : 기록 분산.\n⚠ [확인 필요] 지원금 상한 미확인\n○ 해결 : 회차 데이터 표준화.\n※ 외부감사 반영 메모"
    sub, internal = split_outputs(doc)
    if "⚠" in sub or "외부감사" in sub: fails.append("T7a: 제출본에 내부 마커 잔존")
    if "고객 문제" not in sub or "해결" not in sub: fails.append("T7b: 본문이 유실됨")

    # T8. 입력 충분성
    d = diagnose_input_sufficiency({"program_type": "예비창업패키지", "primary_market": "방문형 산후케어 업체"})
    if d["level_pct"] >= 60: fails.append("T8: 빈약한 입력이 60%% 이상으로 나옴 (%d)" % d["level_pct"])

    # T9. 고객군 혼합
    mix = check_customer_consistency("출장 산후관리 에이전시, 산후조리원, 피부미용업 등")
    if len(mix) < 2: fails.append("T9: 고객군 혼합+피부미용업 위험 미탐지")
    if check_customer_consistency("소속 관리사 3~20명 규모 지역 중소 방문형 산후케어 업체"): fails.append("T9b: 단일 고객 오탐")

    print("[content_gate self-test] %d개 검사" % 9)
    if fails:
        for f in fails: print("  [FAIL]", f)
        raise SystemExit(1)
    print("  [PASS] 전부 통과")

if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
