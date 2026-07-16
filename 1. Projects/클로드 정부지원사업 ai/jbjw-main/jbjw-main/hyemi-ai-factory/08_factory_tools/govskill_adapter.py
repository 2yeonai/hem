#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""govskill_adapter.py — hyemi-ai-factory ↔ gov-support-matching-skill 번역기(어댑터).

이 파일 하나만 새로 추가됨. engines.py / draft_engine.py / present_engine.py /
app.py / run_factory.py 등 기존 판정 로직·화면·파이프라인은 전혀 수정하지 않는다.
(요청 원문: "판정 로직이나 화면은 건드리지 말고, 데이터 형태만 바꿔주는 별도 파일
하나만 새로 만들면 돼")

무엇을 하는가
------------
hyemi-ai-factory의 input.json 구조(notice/applicant/ideas[]/budget_plan[]/
selected_idea_id/approvals)를 gov-support-matching-skill의
review_application(business_profile, announcement, ref_date) 이 요구하는
business_profile / announcement 스키마로 "형태만" 바꾼 뒤 그대로 호출한다.
gov-support-skill 쪽 판정 로직(위험표현/PSST/8인심사위원/감점전파/quality_gate)은
단 한 줄도 재작성하지 않고 그대로 재사용한다.

"최종 선정된 아이디어" 판정 기준 (input_schema.json에 이미 문서화된 공식 필드)
--------------------------------------------------------------------------
- data["selected_idea_id"]        : 사람이 최종 확정한 아이디어 id (string|null)
- data["approvals"]["idea_selected"] : 그 확정을 사람이 승인했다는 boolean 플래그
둘 다 있어야("id 존재" AND "idea_selected is True") 확정으로 인정한다.
이는 engines.lock_engine()/draft_engine.pick_idea()가 이미 쓰고 있는 것과
동일한 기준이며, human_approval_points.md / README_CLI.md / input_schema.json에
공식적으로 문서화되어 있다 — 이 어댑터가 새로 지어낸 규칙이 아니다.
확정되지 않았으면(둘 중 하나라도 아니면) 이 어댑터는 아무것도 호출하지 않고
PENDING_APPROVAL로 멈춘다 (앱의 error_handling_rules.md와 동일한 상태명 사용).

gov-support-skill 저장소 위치 찾기
----------------------------------
두 저장소(hyemi-ai-factory / gov-support-matching-skill)는 별도 git 저장소라
상대경로가 배포 환경마다 달라질 수 있다. 다음 순서로 찾는다:
  1) 환경변수 GOVSKILL_SCRIPTS_DIR (review_application이 들어있는 run.py의 폴더)
  2) 이미 sys.path에 run.py가 잡혀 있으면(같은 파이썬 프로세스에 이미 임포트된 경우) 그대로 사용
  3) 이 파일 기준 상위 폴더들을 최대 6단계까지 훑어 "scripts/run.py" +
     그 안에 review_application 함수가 있는지 확인 (형제 저장소가 근처에 있는
     일반적인 배치를 가정한 보수적 탐색 — 그 이상은 추측하지 않고 에러로 보고)
  4) 못 찾으면 무엇을 해야 하는지 알려주는 명확한 에러 메시지와 함께 실패한다
     (조용히 넘어가거나 임의 경로를 지어내지 않는다).

알려진 번역 손실 (숨기지 않고 아래에 명시 + translation_notes로도 매 호출마다 반환)
--------------------------------------------------------------------------------
1. [완화됨 — 아래 "자격요건 안전장치" 참고] hyemi-ai-factory의 notice.eligibility/
   exclusions는 자유서술 텍스트다. gov-support-skill의 announcement.eligibility는
   구조화된 필드(biz_type/industry_codes/min_years_since_founding/...)를 기대한다.
   자유서술을 그 구조로 "이해"해서 채우는 것은 새로운 판정 로직(자연어 해석)이
   되므로 여전히 하지 않는다 — eligibility 정량 필드는 여전히 빈 채로 전달된다.
   대신 eligibility_keyword_safety_check()로 "핵심 키워드가 원문에 최소한
   언급은 됐는지"만 확인해서, 언급 안 된 게 있으면 그 사실을 명시적으로 경고한다
   (완벽한 파싱이 아니라 "모르면 낙관적으로 처리하지 않는다"는 안전장치).
2. applicant.biz_years(연차, 숫자)만 있고 founded_date(개업일)가 없어
   founded_date를 오늘 날짜에서 biz_years년을 빼 근사 계산한다 — 일/월 단위
   오차가 있을 수 있다. (심각도 낮음 — 사용자 확인, 보완 보류)
3. budget_plan 항목에 category가 없어(item/purpose 텍스트만 있음)
   budget_criteria.excluded_categories 매칭이 동작하지 않는다(항상 통과).
   단, 이 위험 자체는 engines.budget_risk_checker가 이미 별도로 키워드
   매칭(인건비/임차 등)으로 잡고 있으므로 완전히 놓치는 것은 아니다.
   (심각도 낮음 — 사용자 확인, 보완 보류)
4. [확인함] hyemi-ai-factory 스키마 전체(input_schema.json)를 다시 훑었지만
   "서류 준비 상태"를 나타내는 필드는 uploads/attachments/documents_status
   등 어떤 이름으로도 존재하지 않는다. 가장 가까운 것은 evidence.owned/planned인데,
   이는 "증빙 자료가 실물로 있는지"를 나타내는 범용 리스트이지 공고별
   required_documents 항목 이름과 1:1로 대응하는 체크리스트가 아니다(예:
   "사업자등록증"은 들어있지만 "국세 납세증명서" 같은 공고 고유 서류명과
   정확히 대응한다는 보장이 없다 — 억지로 매칭하면 이름 유사도 추측이 되어
   새로운 판정 로직을 만드는 셈이 된다). 그래서 required_documents는 여전히
   빈 리스트로 두고, PSST-Support/서류체크리스트가 "항상 0건 준비"로 나온다는
   사실을 translation_notes에 명확히 남긴다 — 사람이 직접 확인해야 한다.
5. notice.apply_deadline이 "2026-07-03(금) 16:00 (소상공인24)"처럼 자유
   서술이라 앞부분 YYYY-MM-DD만 정규식으로 추출한다. 못 찾으면 None.
6. exclusion_conditions는 notice.exclusions 원문 한 덩어리를 리스트 1건으로
   감싸 전달한다(문장 단위 분리 안 함) — disqualification_flags와의 부분
   문자열 매칭 정밀도가 떨어질 수 있다.

자격요건 안전장치 (eligibility_keyword_safety_check)
-----------------------------------------------------
eligibility 정량 필드가 비어 있으면 gov-support-skill 쪽 criteria가 빈 리스트가
되어 _score_criteria([])가 항상 1.0(만점)을 반환한다 — "확인해서 통과"가 아니라
"검사 자체가 없어서 만점"인데 겉보기엔 구분이 안 된다. 이를 완화하기 위해
notice.eligibility + notice.exclusions + notice.raw_text를 합친 텍스트에서
핵심 키워드 4종("업력", "매출", "지역", "체납")이 최소 한 번이라도 언급됐는지만
본다(자연어 이해 아님 — 단순 부분 문자열 포함 여부). 하나라도 언급 안 됐으면
"확인 필요"로 명시적으로 낮춰 표시한다. 언급됐다고 해서 그 요건이 실제로
충족됐다는 뜻은 아니다 — 여전히 "이 주제가 원문에 등장은 한다"는 것만 확인하는
것이며, 최종 판단은 사람 몫이다.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# 1. gov-support-skill 위치 탐색 + review_application 로드
# --------------------------------------------------------------------------
_govskill_run_module = None


def _load_module_from_path(run_py_path: Path):
    spec = importlib.util.spec_from_file_location("govskill_run", run_py_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _search_upward_for_scripts_dir(start: Path, max_levels: int = 6):
    cur = start
    for _ in range(max_levels):
        cand = cur / "scripts" / "run.py"
        if cand.exists():
            return cand.parent
        # 형제 폴더들도 한 단계만 훑는다(예: ..의 다른 하위폴더에 gov-support-skill이 있는 경우)
        if cur.parent != cur:
            for sib in cur.parent.iterdir():
                sib_cand = sib / "scripts" / "run.py"
                if sib.is_dir() and sib_cand.exists():
                    return sib_cand.parent
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _find_govskill_run_py() -> Path:
    env = os.environ.get("GOVSKILL_SCRIPTS_DIR")
    if env:
        p = Path(env) / "run.py"
        if p.exists():
            return p
        raise RuntimeError(
            f"환경변수 GOVSKILL_SCRIPTS_DIR='{env}'가 설정돼 있지만 그 안에 run.py가 없습니다."
        )
    found_dir = _search_upward_for_scripts_dir(_THIS_DIR)
    if found_dir:
        return found_dir / "run.py"
    raise RuntimeError(
        "gov-support-matching-skill의 scripts/run.py를 찾지 못했습니다. "
        "환경변수 GOVSKILL_SCRIPTS_DIR에 그 폴더 경로(run.py가 들어있는 scripts 폴더)를 "
        "지정해주세요. 예: export GOVSKILL_SCRIPTS_DIR=/path/to/gov-support-matching-skill/scripts"
    )


def _get_govskill_module():
    global _govskill_run_module
    if _govskill_run_module is not None:
        return _govskill_run_module
    run_py = _find_govskill_run_py()
    mod = _load_module_from_path(run_py)
    if not hasattr(mod, "review_application"):
        raise RuntimeError(
            f"{run_py}를 찾았지만 review_application() 함수가 없습니다. "
            "gov-support-skill 버전이 v0.5.1 미만일 수 있습니다."
        )
    _govskill_run_module = mod
    return mod


# --------------------------------------------------------------------------
# 2. "최종 확정 아이디어" 판정 (input_schema.json에 이미 문서화된 공식 기준)
# --------------------------------------------------------------------------
def get_confirmed_idea(data: dict):
    """
    반환: (idea_dict|None, confirmed: bool, reason: str)
    확정 기준: data['selected_idea_id']가 ideas[] 안에 실제로 존재하고,
              data['approvals']['idea_selected'] is True.
    (engines.lock_engine / draft_engine.pick_idea와 동일 기준 — 새 기준 아님)
    """
    sel_id = data.get("selected_idea_id")
    approved = (data.get("approvals") or {}).get("idea_selected") is True
    ideas = data.get("ideas") or []
    idea = next((i for i in ideas if i.get("id") == sel_id), None) if sel_id else None

    if not sel_id or not approved:
        return None, False, (
            "PENDING_APPROVAL: 최종 아이디어가 사람에 의해 확정되지 않음 "
            "(selected_idea_id + approvals.idea_selected==true 필요)"
        )
    if idea is None:
        return None, False, f"selected_idea_id '{sel_id}'가 ideas[] 안에 존재하지 않음 — 입력 오류"
    return idea, True, "확정된 아이디어 확인됨"


# --------------------------------------------------------------------------
# 2-b. 자격요건 안전장치 — "모르면 낙관적으로 처리하지 않는다"
# --------------------------------------------------------------------------
CORE_ELIGIBILITY_KEYWORDS = ["업력", "매출", "지역", "체납"]


def eligibility_keyword_safety_check(notice: dict) -> dict:
    """
    eligibility/exclusions/raw_text를 합친 텍스트에 핵심 키워드 4종이
    언급됐는지만 확인하는 단순 안전장치 (완전한 파싱/이해가 아님).
    목적: eligibility 정량 필드를 못 채워 criteria=[] -> _score_criteria가
    무조건 1.0을 반환하는 상황에서, 그 1.0을 "확인된 만점"으로 오인하지
    않도록 눈에 띄게 경고하는 것.
    """
    combined = " ".join(
        str(notice.get(k) or "") for k in ("eligibility", "exclusions", "raw_text")
    )
    found = [k for k in CORE_ELIGIBILITY_KEYWORDS if k in combined]
    missing = [k for k in CORE_ELIGIBILITY_KEYWORDS if k not in combined]
    all_found = not missing
    return {
        "checked_keywords": CORE_ELIGIBILITY_KEYWORDS,
        "found": found,
        "missing": missing,
        "all_found": all_found,
        "confidence_display_recommendation": (
            "핵심 키워드는 원문에 전부 언급됨 — 단, 이는 '언급 여부'만 확인한 것이지 "
            "요건 충족 여부를 판정한 것은 아님. eligibility_confidence(base)는 여전히 "
            "정량 기준이 구조화되지 않아 1.0으로 계산됨을 감안해서 볼 것."
            if all_found else
            "확인 필요 — eligibility_confidence(base)가 1.0으로 나와도 그대로 신뢰하지 말 것. "
            f"공고 원문(eligibility/exclusions/raw_text)에 다음 핵심 자격요건 키워드가 "
            f"전혀 언급되지 않음: {', '.join(missing)} (언급이 없다고 해서 요건이 없다는 "
            "뜻은 아니며, 원문을 사람이 직접 확인해야 한다는 뜻)"
        ),
    }


# --------------------------------------------------------------------------
# 3. 데이터 형태 변환 헬퍼 (판정 없음 — 순수 형식 변환)
# --------------------------------------------------------------------------
_KRW_UNIT_RE = re.compile(r"([\d,\.]+)\s*(억|천만|백만|만)?\s*원")
_PERCENT_RE = re.compile(r"([\d,\.]+)\s*%")
_DATE_RE = re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})")


def parse_krw(text) -> int | None:
    """'80만원', '2,000만원', '4,000만원 범위 내' 등 -> 정수 원화. 실패 시 None."""
    if isinstance(text, (int, float)):
        return int(text)
    if not text or not isinstance(text, str):
        return None
    m = _KRW_UNIT_RE.search(text)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    unit = m.group(2)
    mult = {"억": 1_0000_0000, "천만": 1000_0000, "백만": 100_0000, "만": 1_0000}.get(unit, 1)
    return int(num * mult)


def parse_ratio(text) -> float | None:
    """'20%', '20% 이상' 등 -> 0.2. 실패 시 None."""
    if isinstance(text, (int, float)):
        return float(text)
    if not text or not isinstance(text, str):
        return None
    m = _PERCENT_RE.search(text)
    if not m:
        return None
    return round(float(m.group(1).replace(",", "")) / 100, 4)


def parse_iso_date(text) -> str | None:
    """'2026-07-03(금) 16:00 (소상공인24)' 등에서 앞의 YYYY-MM-DD만 추출."""
    if not text or not isinstance(text, str):
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _approx_founded_date(biz_years) -> str | None:
    """biz_years(숫자 연차)로부터 founded_date 근사 계산 (일/월 단위 오차 있음)."""
    try:
        years = float(biz_years)
    except (TypeError, ValueError):
        return None
    approx = date.today() - timedelta(days=round(years * 365.25))
    return approx.isoformat()


def _disqualification_flags_from_applicant(applicant: dict) -> list:
    """tax_arrears/duplicate_grant_history/closed_biz_history(이미 engines.applicant_risk_checker가
    쓰는 것과 동일한 필드)를 gov-support-skill의 disqualification_flags(문자열 리스트) 형태로 변환."""
    def truthy(v):
        return v is True or v in ("있음", "true", "True", "yes", "y")

    flags = []
    if truthy(applicant.get("tax_arrears")):
        flags.append("체납")
    if truthy(applicant.get("duplicate_grant_history")):
        flags.append("중복수혜")
    if truthy(applicant.get("closed_biz_history")):
        flags.append("폐업")
    return flags


def to_business_profile(applicant: dict, idea: dict, notes: list) -> dict:
    """applicant + 확정된 idea 1건 -> gov-support-skill business_profile."""
    founded_date = _approx_founded_date(applicant.get("biz_years"))
    if founded_date and applicant.get("biz_years") not in (None, "", "미확보", "미확인"):
        notes.append(
            f"founded_date는 biz_years({applicant.get('biz_years')})로부터 근사 계산됨 "
            f"({founded_date}) — 일/월 단위 오차 가능"
        )

    problem = idea.get("problem") or ""
    target = idea.get("target") or ""
    name = idea.get("name") or ""
    business_description = " ".join(
        p for p in [
            f"사업 아이템: {name}." if name else "",
            f"해결 대상 문제: {problem}" if problem else "",
            f"고객/수혜자: {target}" if target else "",
        ] if p
    ).strip() or None

    outputs = idea.get("outputs") or []
    expected_outcomes = ("산출물: " + ", ".join(outputs)) if outputs else None

    budget_detail = []
    for b in applicant.get("_budget_plan", []) or []:
        amt = parse_krw(b.get("amount"))
        if b.get("amount") not in (None, "", "미확보") and amt is None:
            notes.append(f"budget_plan 항목 '{b.get('item')}'의 금액 '{b.get('amount')}' 파싱 실패 -> amount_krw=None")
        budget_detail.append({
            "item": b.get("item"),
            "category": None,  # hyemi-ai-factory 스키마에 category가 없음 (알려진 한계 3)
            "amount_krw": amt,
            "note": (b.get("purpose") or "") + ((" / 산출물: " + b["output"]) if b.get("output") else ""),
        })
    if applicant.get("_budget_plan"):
        notes.append(
            "budget_detail의 category가 전부 None임 — excluded_categories(집행 불가 항목) 자동 매칭이 "
            "동작하지 않음 (알려진 한계 3). 예산 키워드 위험은 hyemi-ai-factory의 "
            "engines.budget_risk_checker가 별도로 이미 검출함."
        )

    return {
        "biz_type": applicant.get("biz_type") if applicant.get("biz_type") not in ("", "미확보") else None,
        "industry_code": applicant.get("industry_code") if applicant.get("industry_code") not in ("", "미확보") else None,
        "founded_date": founded_date,
        "region": None,  # hyemi-ai-factory applicant 스키마에 필드 자체가 없음
        "annual_revenue_krw": None,
        "employees": None,
        "ceo_birth_date": None,
        "gender": None,
        "career_interruption_status": None,
        "career_interruption_reason": None,
        "disqualification_flags": _disqualification_flags_from_applicant(applicant),
        "business_description": business_description,
        "team_experience": (applicant.get("notes") or None),
        "budget_detail": budget_detail,
        "expected_outcomes": expected_outcomes,
        "documents_status": {},  # 아래 announcement 쪽 참고
    }


def to_announcement(notice: dict, notes: list) -> dict:
    """notice(자유서술 대부분) -> gov-support-skill announcement(구조화 기대)."""
    budget = notice.get("budget", {}) or {}
    scoring = notice.get("scoring") or []
    scoring_rubric = [
        {"item": s.get("item"), "weight": s.get("points")}
        for s in scoring if s.get("item") is not None
    ]

    deadline = parse_iso_date(notice.get("apply_deadline"))
    if notice.get("apply_deadline") and notice.get("apply_deadline") != "미확보" and deadline is None:
        notes.append(f"apply_deadline '{notice.get('apply_deadline')}'에서 날짜를 추출하지 못함 -> deadline=None")

    max_grant = parse_krw(budget.get("max_amount"))
    matching_ratio = parse_ratio(budget.get("self_pay_ratio"))

    eligibility_raw = notice.get("eligibility")
    exclusions_raw = notice.get("exclusions")
    safety = eligibility_keyword_safety_check(notice)
    notes.append(
        "announcement.eligibility는 빈 구조로 전달됨(정량 자격기준 필드 없음) — "
        "criteria가 비어 eligibility_confidence(base)가 기계적으로 1.0이 됨. "
        + safety["confidence_display_recommendation"]
        + " 원문은 eligibility._raw_text에 그대로 보존됨."
    )

    notes.append(
        "이 필드(required_documents 구조화 목록)가 hyemi-ai-factory 스키마에 없어 "
        "서류 준비 여부를 항상 '미확인(0건 준비)'으로 처리함 — gov-support-skill의 "
        "PSST-Support 판정과 required_documents_checklist가 항상 fail/0건으로 나오는 "
        "것은 실제 미준비를 뜻하는 게 아니라 이 데이터가 없다는 뜻이다. evidence.owned/"
        "planned에 유사 항목이 있을 수 있으나 공고별 서류명과 이름이 정확히 대응한다는 "
        "보장이 없어(억지 매칭 시 이름 유사도 추측이 됨) 매핑하지 않았다 — 사람이 직접 "
        "서류 준비 상태를 확인해야 한다."
    )

    return {
        "program_name": notice.get("title"),
        "deadline": deadline,
        "required_documents": [],  # 알려진 한계: 구조화된 서류 목록 없음(위 note)
        "scoring_rubric": scoring_rubric,
        "budget_criteria": {
            "max_grant_krw": max_grant,
            "matching_fund_ratio": matching_ratio,
            "excluded_categories": budget.get("excluded_items") or [],
        },
        "exclusion_conditions": [exclusions_raw] if exclusions_raw and exclusions_raw != "미확보" else [],
        "eligibility": {"_raw_text": eligibility_raw} if eligibility_raw and eligibility_raw != "미확보" else {},
        "submission_format": {"page_limit": (notice.get("format", {}) or {}).get("page_limit")},
        "_eligibility_keyword_safety": safety,  # 어댑터 전용 메타데이터 — run_govskill_review에서 분리해 상위로 노출
    }


# --------------------------------------------------------------------------
# 4. 통합 진입점
# --------------------------------------------------------------------------
def run_govskill_review(data: dict, ref_date=None) -> dict:
    """
    hyemi-ai-factory data(input.json 전체) -> gov-support-skill review_application() 결과.

    반환 형태:
      {"available": False, "reason": "..."}                       # 확정 아이디어 없음
      {"available": True, "govskill_result": {...}, "translation_notes": [...],
       "eligibility_safety_check": {...}}                          # 성공
      {"available": False, "error": "..."}                         # gov-support-skill 로드 실패 등
    이 함수는 기존 hyemi-ai-factory 파일 어디에서도 아직 호출되지 않는다 —
    필요할 때 이 함수를 import해서 쓰면 된다 (연결 지점은 이 파일 자체).
    """
    idea, confirmed, reason = get_confirmed_idea(data)
    if not confirmed:
        return {"available": False, "reason": reason}

    try:
        mod = _get_govskill_module()
    except RuntimeError as e:
        return {"available": False, "error": str(e)}

    notes: list = []
    applicant = dict(data.get("applicant") or {})
    applicant["_budget_plan"] = data.get("budget_plan") or []  # to_business_profile 내부 전달용
    business_profile = to_business_profile(applicant, idea, notes)
    announcement = to_announcement(data.get("notice") or {}, notes)
    eligibility_safety_check = announcement.pop("_eligibility_keyword_safety")  # gov-support-skill에는 전달 안 함(어댑터 전용 메타데이터)

    govskill_result = mod.review_application(business_profile, announcement, ref_date=ref_date)

    return {
        "available": True,
        "confirmed_idea_id": idea.get("id"),
        "govskill_result": govskill_result,
        "translation_notes": notes,
        "eligibility_safety_check": eligibility_safety_check,
        "_business_profile_used": business_profile,
        "_announcement_used": announcement,
    }


if __name__ == "__main__":
    import json

    sample_path = _THIS_DIR.parent / "01_inputs" / "sample-demo" / "input.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    result = run_govskill_review(sample_data)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
