#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gov-support-matching-skill / scripts/run.py  (manifest v0.4.0)

manifest.yaml의 io_contract를 구현하는 엔트리포인트.
입력: business_profile, target_period
출력: matched_programs, excluded_programs, draft_application, judge_review, quality_gate_result, lock_state, needs_confirmation

처리 순서 (manifest.model_routing.stages와 1:1 대응):
  1. collect_and_extract_announcements  - 공고문 수집 및 핵심기준 추출
  2. check_eligibility_and_disqualification - 신청자격 체크 및 지원제외·결격 위험 점검
  3. match_programs                     - 자격요건 매칭 (마감지남 자동제외, 필수서류 없으면 실패처리)
  4. draft_application                  - 신청서 초안 작성
  5. judge_mode_self_review             - 심사위원 모드 자기검수 (감점위험/과장/증빙부족 우선 탐색)
  quality_gate                          - confidence_threshold(0.85) + judge_review 둘 다 만족해야 READY_FOR_APPROVAL

v0.4.0 변경사항 (실제 공고문 PDF + 실제 사업자 프로필로 테스트하며 발견된 문제 중 3건 수정):
  - [예산 정합성] check_budget_compatibility() 추가: business_profile.budget_detail 총액이
    공고 budget_criteria.max_grant_krw를 초과하는지, budget_detail 항목의 category가
    budget_criteria.excluded_categories(집행 불가 항목)에 해당하는지 점검해 rejection_risks에 반영.
  - [심사배점 매칭] judge_mode_self_review의 rubric 커버리지 체크를 "항목명 첫 단어만 포함 검사"에서
    "토큰 분리 + 동의어 테이블(부분일치) + 나머지 토큰은 완전일치"로 개선 (_rubric_covered).
    '가점'류(서술로 커버 불가능한 항목)는 커버리지 체크 대상에서 제외.
    주의: 첫 시도에서는 "토큰 앞 2글자만 맞아도 매칭"이라는 fallback을 넣었다가 전 항목이 오탐(over-match)하는 걸 회귀 테스트로 발견 → 제거함. 현재는 동의어 테이블에 등록된 어근을 포함하는 토큰만 부분매칭 허용, 나머지는 전체 문자열 정확 일치 요구. 그래도 여전히 키워드 휴리스틱이지 의미 기반(NLP) 매칭은 아님 — 알려진 한계로 명시.
  - [자격요건 스키마] business_profile에 gender/career_interruption_status/
    career_interruption_reason 추가, 공고 eligibility에 required_gender/
    requires_career_interruption 추가. 값이 없으면(None) 기존 패턴대로 "확인 필요"로 처리.

v0.3.0 변경사항 (실제 사업자 데이터로 테스트하며 발견된 문제 수정):
  - business_description/team_experience/budget_detail/expected_outcomes가 이제
    문자열(v0.2.0 방식)뿐 아니라 중첩 객체(실제 예비창업패키지류 사업계획서에서 흔한
    구조)도 받아들인다. _format_business_description() 등 포맷터가 dict를 사람이
    읽을 수 있는 문자열로 변환한다. 값이 없으면 여전히 "[확인 필요]"로 표시.
  - documents_status가 이제 두 가지 형태를 모두 지원한다:
      (a) 기존 flat map {"문서명": true/false}
      (b) 신규 {"prepared_documents": [...], "not_prepared_or_needs_check": [...]}
          각 항목은 {"document_name":.., "status": "준비됨"|"파일 보유"|"확인 필요"|"미보유"}
    상태 문자열 매핑: "준비됨"/"파일 보유" -> prepared=true, "확인 필요"/"미보유" -> prepared=false.
  - 자격요건 체크에서 biz_type/industry_code 등이 profile에 아예 없는 경우(None) "불합격(False)"이
    아니라 "확인 필요(None/unresolved)"로 처리하도록 수정.
  - main()이 두 번째 CLI 인자로 announcements 파일 경로를 받을 수 있도록 확장
    (예: python3 run.py test/real_program_input.json scripts/real_announcements.json).

v0.5.0 변경사항 (판정로직 확장스펙: gov-support-skill/정부지원사업_판정로직_확장스펙.md 기반,
  4개 서브시스템을 judge_mode_self_review() 확장으로 추가. 기존 confidence 공식은 불변,
  아래 4개는 judge_pass_recommendation의 판정 근거를 "형식요건만" -> "형식+내용품질"로 넓히는
  질적 판정 레이어로만 추가됨):
  - [위험표현 사전] RISK_PHRASE_DICTIONARY(9종 고정세트) + scan_risk_phrases(): 과장/책임소재
    불명 표현을 스캔해 exaggeration_flags에 "원문 표현 + 대체문구 제안" 형태로 추가(append,
    기존 EXAGGERATION_WORDS 체크는 유지). 자동 치환 없음 — 제안만.
  - [PSST 자동검수] assess_psst(): Problem/Solution/Support/Traction 4구간을 draft 섹션과
    profile 데이터에서 pass/fail 판정. 판정만 하고 문장을 대신 써주지 않음 — "무엇이 없는지"만 지적.
    숫자+단위 정규식(_MEASURE_UNIT_RE)은 "300만 개"/"1.5억원"처럼 만/억 단위가 낀 한국식
    수량 표현도 인식하도록 만/억 옵션 그룹을 포함한다.
  - [8인 가상 심사위원] run_judge_panel(): 공고적합성/자격규정/문제정의/AI필요성/실행계획/
    예산증빙/성과확장/발표Q&A 8인이 각각 0~5점 + 즉시경고(warning) 판정. 공고의 실제
    scoring_rubric 항목에 키워드 기반으로 매핑. 8인 로직은 공고 불변, 매핑만 공고별 가변.
  - [감점 전파 모델] build_deduction_map(): 대표 이슈 5종(예산근거누락/자격증빙미확보/
    작업시간실측없음/AI필요성불명확/산출물미정의)이 다른 평가항목으로 번지는 연쇄 리스크를
    고정 계수(스펙 원문 표)로 설명. confidence 점수는 다시 깎지 않고 설명 문장으로만 추가.
  - overall_pass_recommendation 갱신: 기존(unconfirmed_sections==0 AND unprepared==0 AND
    하드실격없음 AND 페이지제한존재)에 "psst_review 전항목 pass" AND "judge_panel_review
    즉시경고 0건" 조건을 추가. 하나라도 fail/경고면 기존처럼 False + reasons에 구체 사유.
  - 이번 1차 구현 범위는 스펙 원문의 고정 표/계수로 시작 (공고별 가변 전파계수 등은 미포함 —
    스펙에 없는 것을 새로 만들지 않는다는 원칙).

v0.5.1 변경사항 (통합 진입점 추가 — 외부 시스템 연동 준비):
  - review_application(business_profile, announcement, ref_date=None) 신설. 기존
    check_eligibility_and_disqualification/_score_criteria/draft_application/
    judge_mode_self_review/apply_quality_gate를 전혀 재작성하지 않고 그대로 재사용하는
    "감싸기(wrapping)" 전용 진입점. collect_and_extract_announcements()/match_programs()의
    다건-공고 수집·매칭 파이프라인을 거치지 않고, 이미 확정된 announcement 1건 + business_profile
    1건에 대해 초안+심사위원 검수(4개 서브시스템 포함)만 실행하고 싶은 외부 호출측(예: AI직원
    플랫폼)을 위해 추가함.

v0.5.2 변경사항 (문서명 fuzzy 매칭):
  - [문서명 매칭] match_document_status() 신설: documents_status <-> 공고 required_documents
    매칭을 기존 "원문 완전일치"에서 "완전일치 -> 정규화(공백/괄호 제거) 후 완전일치 ->
    DOCUMENT_NAME_SYNONYM_GROUPS에 등록된 동의어 그룹 매칭" 3단계로 확장.
    RUBRIC_SYNONYMS/_rubric_covered와 동일 원칙(등록된 것끼리만 매칭, 짧은 어근 무분별
    부분매칭 금지)을 그대로 적용. 매칭 실패 시 이유를 document_match_notes에 기록해
    향후 동의어 테이블 보강에 쓸 수 있게 함. 동의어 그룹은 괄호 제거 정규화로 서로 다른
    문서가 붕괴 충돌할 위험이 없는 4개(사업자등록증류/법인등기부등본류/중소기업확인서류/
    부가가치과세표준증명류)만 안전하게 등록함(국세/지방세 납세증명서처럼 괄호 안 내용이
    문서를 구분하는 유일한 단서인 경우는 등록하지 않음 — 의미 추측 금지 원칙).

주의(아직 해결 안 됨 — 알려진 한계):
  - PDF/HWP 공고문 자동 파싱 없음 — 공고는 사람이 직접 읽고 scripts/*.json으로 구조화해야 함.
  - documents_status 매칭은 v0.5.2에서 fuzzy(정규화+동의어 테이블) 매칭으로 개선됐지만, 등록된
    동의어 그룹에 없는 표현은 여전히 미준비로 집계된다 — 의미 기반(NLP) 매칭이 아니라 화이트리스트
    기반이므로, 실제 서류는 있는데 표현이 등록 안 된 경우는 여전히 놓칠 수 있음(known limitation).
  - 예비창업자(사업자등록 자체가 없는 상태)/해외법인 국적 요건/겸업 조합 조건 등은 여전히
    스키마로 표현되지 않음 (eligibility._unmapped_requirements에 텍스트로만 기록).
  - 심사배점 커버리지 체크는 여전히 키워드 기반 휴리스틱이다 (의미 이해 아님).
  - PSST/8인심사위원의 pass/fail·score 판정도 키워드·구조 존재여부 기반 휴리스틱이다
    (숫자+단위 정규식, budget_detail 존재여부, 문서 준비여부 등). 의미 기반 판단이 아니므로
    최종 판단은 사람이 해야 한다 (v0.5.0).

주의: collect_and_extract_announcements()는 기본적으로 scripts/sample_announcements.json(목업)을
     읽는다. 실제 공고를 테스트하려면 두 번째 CLI 인자로 별도 announcements JSON 경로를 지정한다.
"""

import json
import sys
import os
import re
import yaml
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
CONFIDENCE_THRESHOLD = 0.85  # manifest.yaml quality_gate.confidence_threshold와 동일해야 함
FAILURE_LOG_PATH = ROOT_DIR / "test" / "failure_log.jsonl"

EXAGGERATION_WORDS = [
    "최초", "유일", "국내 최고", "세계 최고", "압도적", "혁신적인", "완벽한",
    "타의 추종을 불허", "독보적", "100% 보장", "무조건", "최고 수준"
]

# v0.4.0: 심사배점 커버리지 체크에서 완전히 제외할 항목(서술형 초안으로는 애초에 채울 수 없는 항목)
RUBRIC_SKIP_ITEMS = ["가점", "가산점"]

# v0.4.0: 흔한 표현 차이를 흡수하기 위한 동의어 테이블.
# 토큰에 이 키(어근)가 "부분포함"되어 있으면, 동의어 중 하나라도 본문에 있는지 확인한다.
# (그 외 토큰은 완전일치만 인정 — 너무 짧은 어근의 부분매칭은 과도한 오탐을 만들어 제외했음)
RUBRIC_SYNONYMS = {
    "창업": ["창업", "사업"],
    "아이템": ["아이템", "아이디어", "서비스", "제품", "솔루션"],
    "사업화": ["사업화", "사업"],
}

RUBRIC_STOPWORDS = {"및", "등", "의", "그", "것", "수"}

# ---------------------------------------------------------------------------
# v0.5.0 확장 STEP 1: 위험표현 사전과 대체문구
#   출처: 정부지원사업_판정로직_확장스펙.md 1번 표. 원문 9개 고정 세트 그대로 이식.
#   비고(원문): "이 사전은 고정 파일이 아니라 룰 엔진의 일부로 취급...
#   이번 구현 범위는 위 9개 고정 세트로 시작." -> 스펙에 없는 표현은 추가하지 않음.
#   자동 치환은 하지 않는다 — "원문 표현 + 대체문구 제안"만 반환, 최종 수정은 사람.
# ---------------------------------------------------------------------------
RISK_PHRASE_DICTIONARY = [
    {"phrase": "완벽히 해결", "risk_type": "과장", "replacement": "위험을 줄임 / 오류를 완화함"},
    {"phrase": "100% 자동화", "risk_type": "과장·책임소재 불명", "replacement": "대표자 검수 기반 반자동화"},
    {"phrase": "AI가 판단한다", "risk_type": "책임위험", "replacement": "AI가 분류 초안을 제안하고 사람이 확정한다"},
    {"phrase": "자동 발송", "risk_type": "개인정보·운영사고", "replacement": "발송 대기열 생성 후 담당자 승인 발송"},
    {"phrase": "외주 개발만 하면 된다", "risk_type": "실행력 약화", "replacement": "내부 운영 프로세스에 맞춘 구축·검증"},
    {"phrase": "단순 구독", "risk_type": "구매성 위험", "replacement": "업무 자동화를 위한 API 연계 및 산출물 생성"},
    {"phrase": "장비 구매", "risk_type": "자산취득성 위험", "replacement": "현장 실증을 위한 단기 장비 활용 [확인 필요]"},
    {"phrase": "플랫폼으로 대박 확장", "risk_type": "범위 과다", "replacement": "협약기간 내 MVP 구축 및 도입 검증"},
    {"phrase": "기존 문제를 다 없앤다", "risk_type": "증빙 부재", "replacement": "특정 병목 1~2개를 우선 개선한다"},
]


def scan_risk_phrases(text):
    """서술형 텍스트에서 위험표현 사전(RISK_PHRASE_DICTIONARY) 매칭 항목을 그대로 반환.
    자동 치환 없음 — 호출측(judge_mode_self_review)에서 '원문 표현 + 대체문구 제안' 형태로만 노출."""
    text = text or ""
    return [entry for entry in RISK_PHRASE_DICTIONARY if entry["phrase"] in text]


def _risk_phrase_flag_text(entry):
    return (
        f"위험표현 발견: '{entry['phrase']}' (유형: {entry['risk_type']}) "
        f"-> 대체문구 제안: {entry['replacement']}"
    )


def today():
    override = os.environ.get("GOV_SKILL_TODAY")
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def log_failure(step, input_summary, error, confidence_at_failure=None):
    FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "input_summary": input_summary,
        "error": str(error),
        "confidence_at_failure": confidence_at_failure,
    }
    with open(FAILURE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# STEP 1: 공고문 수집 및 핵심 기준 추출
# ---------------------------------------------------------------------------
def collect_and_extract_announcements(target_period, announcements_path=None):
    path = announcements_path or (SCRIPT_DIR / "sample_announcements.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    extracted = []
    needs_confirmation = []
    for a in raw:
        missing_fields = []
        if not a.get("required_documents"):
            missing_fields.append("required_documents")
        if not a.get("scoring_rubric"):
            missing_fields.append("scoring_rubric")
        if a.get("submission_format", {}).get("page_limit") is None:
            missing_fields.append("page_limit")

        if a.get("source_note"):
            needs_confirmation.append(f"[{a['program_name']}] {a['source_note']}")

        elig = a.get("eligibility", {}) or {}
        if elig.get("_unmapped_requirements"):
            needs_confirmation.append(
                f"[{a['program_name']}] 현재 스키마로 표현 못하는 자격요건 있음: "
                + "; ".join(elig["_unmapped_requirements"])
            )

        extracted.append({**a, "_missing_fields": missing_fields})

    return extracted, needs_confirmation


# ---------------------------------------------------------------------------
# STEP 2: 신청자격 체크 및 지원제외·결격 위험 점검
# ---------------------------------------------------------------------------
def _years_since(d, ref):
    return (ref - d).days / 365.25


def check_eligibility_and_disqualification(
    profile, announcement, ref_date, founding_requirement_hint=None, industry_code_verified=True
):
    """
    founding_requirement_hint: v0.6.0(다중 사업 프로필) 전용 선택 인자. 기본값 None이면
    기존 동작(단일 business_profile 경로)과 완전히 동일 — 하위호환 보존.
    "pre_founding_required"가 전달되고 profile.founded_date가 없으면(개업 전), 업력 criterion을
    "확인 필요(None)"이 아니라 "적격(True)"으로 처리한다 — 예비창업 요건(개업 전 필수) 공고에는
    개업 전 상태 자체가 자격 충족이므로("모름"이 아니라 "충족"). match_programs()의
    apply_founding_classification=True 경로에서만 채워진다.

    industry_code_verified: v0.6.0(다중 사업 프로필) 전용 선택 인자. 기본값 True면 기존
    동작(단일 business_profile 경로)과 완전히 동일 — 하위호환 보존. False가 전달되면
    profile.industry_code가 표준산업분류 코드가 아니라 자유서술(business_profiles.yaml의
    industry 필드 등)이라는 뜻이므로, industry_codes 목록과 "불일치"(in 비교 False)로
    나온 결과를 "부적격(False)"이 아니라 "확인 필요(None)"로 처리한다(§16 판정3: "모름≠미달").
    일치(True)로 나온 경우는 그대로 True 유지 — 우연히 일치했어도 부정할 근거는 없다.
    """
    elig = announcement.get("eligibility", {})
    criteria = []

    # 값이 아예 없으면(None) "불합격"이 아니라 "확인 필요"로 처리
    biz_types = elig.get("biz_type")
    if biz_types and biz_types != "any":
        val = profile.get("biz_type")
        if val is None:
            criteria.append(("기업형태", None))
        else:
            criteria.append(("기업형태", val in biz_types))

    industry_codes = elig.get("industry_codes")
    if industry_codes and industry_codes != "any":
        val = profile.get("industry_code")
        if val is None:
            criteria.append(("업종코드", None))
        else:
            matched = val in industry_codes
            if not matched and not industry_code_verified:
                criteria.append((
                    "업종코드(자유서술이라 표준산업분류 코드와 대조 불가 — 확인 필요)",
                    None,
                ))
            else:
                criteria.append(("업종코드", matched))

    founded = parse_date(profile.get("founded_date"))
    min_y = elig.get("min_years_since_founding")
    max_y = elig.get("max_years_since_founding")
    if min_y is not None or max_y is not None:
        if founded is None:
            if founding_requirement_hint == "pre_founding_required":
                criteria.append(("업력(예비창업 요건 개업전 필수 -> 개업 전 상태로 적격)", True))
            else:
                criteria.append(("업력", None))
        else:
            years = _years_since(founded, ref_date)
            ok = True
            if min_y is not None:
                ok = ok and years >= min_y
            if max_y is not None:
                ok = ok and years <= max_y
            criteria.append((f"업력({years:.1f}년)", ok))

    region = elig.get("region")
    if region and region != "any":
        val = profile.get("region")
        if val is None:
            criteria.append(("지역", None))
        else:
            criteria.append(("지역", val in region))

    max_emp = elig.get("max_employees")
    min_emp = elig.get("min_employees")
    if max_emp is not None or min_emp is not None:
        emp = profile.get("employees")
        if emp is None:
            criteria.append(("상시근로자수", None))
        else:
            ok = True
            if max_emp is not None:
                ok = ok and emp <= max_emp
            if min_emp is not None:
                ok = ok and emp >= min_emp
            criteria.append(("상시근로자수", ok))

    max_rev = elig.get("max_annual_revenue_krw")
    if max_rev is not None:
        rev = profile.get("annual_revenue_krw")
        if rev is None:
            criteria.append(("매출액 기준", None))
        else:
            criteria.append(("매출액 기준", rev <= max_rev))

    ceo_age_max = elig.get("ceo_age_max")
    if ceo_age_max is not None:
        ceo_birth = parse_date(profile.get("ceo_birth_date"))
        if ceo_birth is None:
            criteria.append(("대표자연령", None))
        else:
            age = int(_years_since(ceo_birth, ref_date))
            criteria.append((f"대표자연령({age}세)", age <= ceo_age_max))

    # v0.4.0: 성별 요건
    required_gender = elig.get("required_gender")
    if required_gender and required_gender != "any":
        val = profile.get("gender")
        if val is None:
            criteria.append(("성별", None))
        else:
            criteria.append(("성별", val == required_gender))

    # v0.4.0: 경력단절 요건
    if elig.get("requires_career_interruption"):
        val = profile.get("career_interruption_status")
        if val is None:
            criteria.append(("경력단절 여부", None))
        else:
            criteria.append(("경력단절 여부", bool(val)))

    disqualification_risks = []
    flags = profile.get("disqualification_flags", []) or []
    exclusions = announcement.get("exclusion_conditions", []) or []
    for flag in flags:
        for exclusion in exclusions:
            if flag in exclusion or exclusion in flag:
                disqualification_risks.append(
                    f"자기신고 항목 '{flag}' 이(가) 지원제외 조건 '{exclusion}'에 해당할 위험"
                )

    unverifiable = [
        e for e in exclusions
        if any(k in e for k in ["체납", "중복", "휴업", "폐업", "수료"])
    ]

    return criteria, disqualification_risks, unverifiable


def _score_criteria(criteria):
    if not criteria:
        return 1.0, []
    total = 0.0
    unresolved = []
    for name, result in criteria:
        if result is True:
            total += 1.0
        elif result is False:
            total += 0.0
        else:
            total += 0.5
            unresolved.append(name)
    return total / len(criteria), unresolved


# ---------------------------------------------------------------------------
# STEP 3: 자격요건 매칭 (마감지남 자동제외, 필수서류 없으면 실패처리)
# ---------------------------------------------------------------------------
def match_programs(
    profile, announcements, target_period, ref_date,
    apply_founding_classification=False, industry_code_verified=True,
):
    """
    apply_founding_classification: v0.6.0(다중 사업 프로필) 전용 선택 인자. 기본값 False면
    기존 동작(단일 business_profile 경로)과 완전히 동일 — 하위호환 보존.
    True면 공고별로 _classify_founding_requirement()를 계산해
    check_eligibility_and_disqualification()에 founding_requirement_hint로 전달한다
    (예비창업 요건 공고에 대한 "적격" 판정용, run_for_profile()에서만 True로 호출됨).

    industry_code_verified: v0.6.0(다중 사업 프로필) 전용 선택 인자. 기본값 True면 기존
    동작과 완전히 동일 — 하위호환 보존. False면 check_eligibility_and_disqualification()에
    그대로 전달해 industry_codes 불일치를 부적격이 아닌 확인 필요로 처리한다(§16 판정3).
    """
    matched = []
    excluded = []
    needs_confirmation = []

    period_end = parse_date(target_period["end_date"])

    for a in announcements:
        name = a["program_name"]
        deadline = parse_date(a.get("deadline"))

        if deadline is None:
            excluded.append({"program_name": name, "exclusion_reason": "마감일 정보 없음 -> 확인 필요"})
            needs_confirmation.append(f"[{name}] 마감일 정보를 원문에서 확인하지 못함")
            continue
        if deadline < ref_date:
            excluded.append({"program_name": name, "exclusion_reason": f"마감일 경과 ({deadline.isoformat()})"})
            continue
        if deadline > period_end:
            excluded.append({
                "program_name": name,
                "exclusion_reason": f"마감일({deadline.isoformat()})이 조회기간 종료일({period_end.isoformat()}) 이후 -> 이번 조회 범위 밖"
            })
            continue

        if not a.get("required_documents"):
            excluded.append({
                "program_name": name,
                "exclusion_reason": "필수 제출서류 목록을 원문에서 확인하지 못함 -> 자동 실패 처리 (manifest self_check_rules 적용)"
            })
            continue

        founding_hint = _classify_founding_requirement(a) if apply_founding_classification else None
        criteria, disq_risks, unverifiable = check_eligibility_and_disqualification(
            profile, a, ref_date, founding_requirement_hint=founding_hint,
            industry_code_verified=industry_code_verified,
        )
        score, unresolved = _score_criteria(criteria)

        if disq_risks:
            excluded.append({
                "program_name": name,
                "exclusion_reason": "결격 위험 감지: " + "; ".join(disq_risks)
            })
            continue

        if unresolved:
            needs_confirmation.append(
                f"[{name}] 다음 자격기준을 profile 데이터만으로 판단 불가: {', '.join(unresolved)}"
            )
        if unverifiable:
            needs_confirmation.append(
                f"[{name}] 다음 지원제외 조건은 자기신고 데이터로 검증 불가(세금체납 등 공적 확인 필요): {', '.join(unverifiable)}"
            )

        if a.get("_missing_fields"):
            needs_confirmation.append(
                f"[{name}] 원문에서 다음 항목 미확인: {', '.join(a['_missing_fields'])}"
            )

        matched.append({
            "program_name": name,
            "eligibility_confidence": round(score, 2),
            "required_documents": a["required_documents"],
            "deadline": deadline.isoformat(),
            "disqualification_risks": disq_risks,
            "_raw": a,
            "_unresolved_criteria": unresolved,
        })

    matched.sort(key=lambda x: x["eligibility_confidence"], reverse=True)
    return matched, excluded, needs_confirmation


# ---------------------------------------------------------------------------
# STEP 4: 신청서 초안 작성
# ---------------------------------------------------------------------------
def _join(items, sep=", "):
    return sep.join(str(i) for i in items if i)


def _format_business_description(value):
    """string(v0.2.0) 또는 dict(v0.3.0, 예: 예비창업패키지 사업계획서 구조)를 문자열로 변환."""
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        brand = value.get("brand_name")
        meaning = value.get("brand_meaning")
        if brand:
            parts.append(f"브랜드명: {brand}" + (f" ({meaning})" if meaning else ""))
        item = value.get("business_item")
        if item:
            parts.append(f"사업 아이템: {item}")
        desc = value.get("description")
        if desc:
            parts.append(desc)
        target = value.get("target_customer")
        if target:
            parts.append(f"타겟 고객: {target}")
        problem = value.get("core_problem")
        if problem:
            parts.append(f"핵심 문제의식: {problem}")
        solution = value.get("solution_structure")
        if isinstance(solution, dict):
            steps = solution.get("program_steps") or []
            if steps:
                parts.append("프로그램 구성: " + " -> ".join(steps))
            measure = solution.get("measurement_items") or []
            if measure:
                parts.append("측정/관리 항목: " + _join(measure))
            diff = solution.get("differentiation") or []
            if diff:
                parts.append("차별점: " + _join(diff, "; "))
            boundary = solution.get("non_medical_boundary")
            if boundary:
                parts.append(boundary)
        channels = value.get("initial_channels") or []
        if channels:
            parts.append("초기 고객 확보 채널: " + _join(channels))
        return " ".join(parts)
    return str(value)


def _format_team_experience(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        founder = value.get("founder")
        if isinstance(founder, dict):
            role = founder.get("role")
            summary = founder.get("experience_summary")
            if role or summary:
                parts.append(f"대표자({role or '대표'}): {summary or ''}".strip())
            certs = founder.get("certifications_and_training") or []
            if certs:
                parts.append("보유 자격/교육: " + _join(certs, "; "))
            work = founder.get("work_experience") or []
            if work:
                parts.append("실무 경력: " + _join(work, "; "))
            strength = founder.get("execution_strength") or []
            if strength:
                parts.append("실행 역량: " + _join(strength, "; "))
        planned = value.get("planned_team") or []
        if planned:
            lines = [
                f"{p.get('role','')}({p.get('status','')}): {p.get('responsibility','')}"
                for p in planned
            ]
            parts.append("채용/확보 예정 인력: " + _join(lines, " / "))
        partners = value.get("partners_or_advisors") or []
        if partners:
            lines = [
                f"{p.get('role','')}({p.get('status','')}): {p.get('purpose','')}"
                for p in partners
            ]
            parts.append("파트너/자문: " + _join(lines, " / "))
        return " ".join(parts)
    return str(value)


def _format_budget_detail(value):
    """list(v0.2.0, [{item, amount_krw, note}]) 또는 dict(v0.3.0, phase_1/phase_2 구조)를 문자열로 변환."""
    if not value:
        return ""
    if isinstance(value, list):
        lines = []
        for b in value:
            item = b.get("item", "항목명 미상")
            amount = b.get("amount_krw")
            amount_str = f"{amount:,}원" if isinstance(amount, (int, float)) else "금액 미상"
            note = b.get("note")
            line = f"{item} {amount_str}"
            if note:
                line += f"({note})"
            lines.append(line)
        return _join(lines)
    if isinstance(value, dict):
        parts = []
        principle = value.get("budget_principle")
        if principle:
            parts.append(principle)
        for phase_key in sorted(k for k in value.keys() if k.startswith("phase_")):
            phase = value[phase_key]
            if not isinstance(phase, dict):
                continue
            title = phase.get("title", phase_key)
            items = phase.get("items", []) or []
            item_lines = []
            for it in items:
                cat = it.get("category", "")
                nm = it.get("item", "")
                amt = it.get("amount_krw")
                amt_str = f"{amt:,}원" if isinstance(amt, (int, float)) else "금액 미상"
                item_lines.append(f"{cat}-{nm} {amt_str}")
            subtotal = phase.get("subtotal_krw")
            subtotal_str = f" (소계 {subtotal:,}원)" if isinstance(subtotal, (int, float)) else ""
            parts.append(f"{title}{subtotal_str}: " + _join(item_lines, "; "))
        total = value.get("total_krw")
        if isinstance(total, (int, float)):
            parts.append(f"총 예산 {total:,}원")
        return " ".join(parts)
    return str(value)


def _format_expected_outcomes(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        outputs = value.get("business_outputs") or []
        if outputs:
            parts.append("산출물: " + _join(outputs))
        goals = value.get("market_validation_goals") or []
        if goals:
            parts.append("시장검증 목표: " + _join(goals))
        rev = value.get("revenue_goals")
        if isinstance(rev, dict):
            bits = []
            if rev.get("main_product"):
                bits.append(f"주력상품 {rev['main_product']}")
            if rev.get("package_price_krw"):
                bits.append(f"단가 {rev['package_price_krw']:,}원")
            if rev.get("initial_customer_goal"):
                bits.append(f"목표고객 {rev['initial_customer_goal']}")
            if rev.get("estimated_revenue_krw"):
                bits.append(f"예상매출 {rev['estimated_revenue_krw']}원")
            if rev.get("calculation"):
                bits.append(f"산출근거: {rev['calculation']}")
            if bits:
                parts.append("매출 목표: " + _join(bits))
        social = value.get("social_value") or []
        if social:
            parts.append("사회적 가치: " + _join(social, "; "))
        longterm = value.get("long_term_outcomes") or []
        if longterm:
            parts.append("장기 성과: " + _join(longterm))
        return " ".join(parts)
    return str(value)


def _status_to_bool(status, default):
    s = (status or "").strip()
    if any(kw in s for kw in ["준비됨", "파일 보유"]):
        return True
    if any(kw in s for kw in ["확인 필요", "미보유"]):
        return False
    return default


def _normalize_documents_status(value):
    """반환: {document_name: bool} flat map.
    구버전 flat dict({"문서명": true/false})와 신버전
    ({"prepared_documents":[...], "not_prepared_or_needs_check":[...]}) 둘 다 지원.
    """
    if not value or not isinstance(value, dict):
        return {}

    if "prepared_documents" in value or "not_prepared_or_needs_check" in value:
        flat = {}
        for entry in value.get("prepared_documents", []) or []:
            name = entry.get("document_name")
            if name:
                flat[name] = _status_to_bool(entry.get("status", ""), default=True)
        for entry in value.get("not_prepared_or_needs_check", []) or []:
            name = entry.get("document_name")
            if name:
                flat[name] = _status_to_bool(entry.get("status", ""), default=False)
        return flat

    flat = {}
    for k, v in value.items():
        if isinstance(v, bool):
            flat[k] = v
        elif isinstance(v, str):
            flat[k] = _status_to_bool(v, default=False)
        else:
            flat[k] = bool(v)
    return flat


# ---------------------------------------------------------------------------
# v0.5.2: 문서명 fuzzy 매칭 (documents_status <-> 공고 required_documents)
#   배경: documents_status의 document_name이 공고 required_documents 문자열과 정확히
#   일치해야만 매칭되던 known limitation(주석 79행 참고). RUBRIC_SYNONYMS/_rubric_covered와
#   동일한 원칙("동의어 테이블에 명시적으로 등록된 것끼리만 매칭, 짧은 어근의 무분별한
#   부분매칭 금지 — v0.4.0에서 겪은 "창업"/"사업" 과다매칭 실수를 반복하지 않는다")을 그대로
#   문서명 매칭에 적용한다.
#
#   매칭 순서:
#     1) 원문 그대로 완전일치 (기존 동작, 최우선 보존)
#     2) 정규화(공백/괄호 안 내용 제거) 후 완전일치 (예: "사업자 등록증"와 "사업자등록증"처럼
#        순수 표기 차이만 있는 경우 — 의미 추측이 아니라 서식상 흔한 변형이므로 안전)
#     3) DOCUMENT_NAME_SYNONYM_GROUPS에 등록된 동의어 그룹 매칭 (아래 그룹에 명시적으로
#        등록된 변형 쌍끼리만 허용 — 그룹에 없는 표현은 매칭하지 않는다)
#   매칭 실패 시 이유를 함께 남겨(향후 동의어 테이블 보강용) match_reason에 기록한다.
# ---------------------------------------------------------------------------
# 주의: 아래 그룹은 "정규화(공백+괄호 제거) 후 문자열"끼리 등록한다. 괄호 제거 정규화 특성상
# "납세증명(국세)"/"납세증명(지방세)"처럼 괄호 안 내용이 서로 다른 문서를 구분하는 유일한 단서인
# 경우 괄호를 지우면 둘 다 "납세증명"으로 붕괴해 서로 다른 문서가 같은 것으로 오매칭될 위험이
# 있다 — 이런 경우는 그룹에 등록하지 않는다(국세/지방세 납세증명서, "사업신청서"~"사업계획서"처럼
# 괄호 밖에서도 이미 이름이 다른 별개 문서로 볼 여지가 있는 쌍도 제외 — 의미 추측 금지 원칙).
# 여기 등록된 4개는 괄호를 지워도 동일 문서를 가리킨다는 점이 공고 원문 표기 자체로 명확한
# 경우만 남긴 것이다(예: 공고가 "중소기업확인서(소상공인확인서)"라고 병기해 이미 동일 취급).
DOCUMENT_NAME_SYNONYM_GROUPS = [
    {"사업자등록증", "사업자등록증사본", "사업자등록증명원", "사업자등록증명"},
    {"중소기업확인서", "소상공인확인서"},
    {"법인등기부등본", "법인등기사항전부증명서"},
    {"부가가치과세표준증명", "부가가치세과세표준증명"},
]


def _normalize_whitespace(name):
    """공백/줄바꿈만 제거. 괄호 안 내용은 건드리지 않는다 — 괄호가 문서를 구분하는
    유일한 단서인 경우(예: 납세증명(국세) vs 납세증명(지방세))가 있어, 이 단계에서
    괄호까지 지우면 서로 다른 문서가 같은 것으로 오매칭(충돌)될 위험이 있다. 순수
    서식(공백) 차이만 흡수하는 안전한 정규화만 여기서 수행한다."""
    if not name:
        return ""
    return re.sub(r"\s+", "", name)


def _normalize_doc_name_for_synonym(name):
    """동의어 그룹 조회 전용 정규화: 공백 제거 + 괄호(원문 안 내용) 제거.
    괄호 제거는 여기(동의어 그룹 조회)에만 적용한다 — DOCUMENT_NAME_SYNONYM_GROUPS에
    명시적으로 등록된 그룹 멤버십 조회에만 쓰이므로, 등록되지 않은 조합(예: 납세증명
    국세/지방세)은 괄호를 지운 뒤에도 어느 그룹에도 속하지 않아 매칭되지 않는다
    (화이트리스트로만 매칭한다는 원칙을 정규화 단계에서도 깨지 않기 위함)."""
    if not name:
        return ""
    s = re.sub(r"[\(（][^)）]*[\)）]", "", name)  # (...), （...） 안 내용 제거
    s = re.sub(r"[\[［][^\]］]*[\]］]", "", s)      # [...], ［...］ 안 내용 제거
    s = re.sub(r"\s+", "", s)                        # 공백/줄바꿈 전부 제거
    return s


def _doc_synonym_group_id(normalized_name):
    """normalized_name(괄호 제거 정규화된 이름)이 속한 DOCUMENT_NAME_SYNONYM_GROUPS의
    인덱스, 없으면 None."""
    for idx, group in enumerate(DOCUMENT_NAME_SYNONYM_GROUPS):
        if normalized_name in group:
            return idx
    return None


def match_document_status(required_name, documents_status):
    """
    required_name(공고 required_documents 문자열 1건)을 documents_status(사업자 쪽
    {document_name: bool} flat map)에서 찾는다.
    반환: (prepared: bool, match_type: str, matched_key: str|None, reason: str)
      match_type: "exact" | "normalized" | "synonym" | "unmatched"

    3단계 매칭이며, 괄호 제거는 3단계(synonym, 화이트리스트 그룹 조회)에만 적용한다.
    2단계(normalized)는 공백만 제거하는 안전한 정규화만 수행한다 — 괄호 안 내용이
    문서를 구분하는 유일한 단서인 경우(납세증명 국세/지방세 등)에 2단계에서 먼저
    충돌 매칭되는 것을 막기 위함(단위테스트로 발견한 버그 수정, v0.5.2 2차 수정).
    """
    if required_name in documents_status:
        return documents_status[required_name], "exact", required_name, "원문 완전일치"

    ws_required = _normalize_whitespace(required_name)
    for key, val in documents_status.items():
        if _normalize_whitespace(key) == ws_required:
            return val, "normalized", key, f"정규화(공백 제거) 후 완전일치: '{key}'"

    syn_required = _normalize_doc_name_for_synonym(required_name)
    required_group = _doc_synonym_group_id(syn_required)
    if required_group is not None:
        for key, val in documents_status.items():
            if _doc_synonym_group_id(_normalize_doc_name_for_synonym(key)) == required_group:
                return val, "synonym", key, f"동의어 테이블 매칭(그룹 {required_group}): '{key}'"

    return (
        False,
        "unmatched",
        None,
        "매칭 실패 — documents_status에 완전일치/정규화일치/등록된 동의어 후보가 없음 "
        "(동의어 테이블에 없는 표현일 가능성 -> 실제로 서류가 있다면 동의어 테이블 보강 검토)",
    )


# --- v0.4.0 / v0.5.3: 예산 정합성 체크 (정부지원분/자기부담분 구분) -----------
# v0.5.3: budget_detail 각 항목에 fund_source("government"|"self") 필드 추가.
# 사용자 결정(2026-07-09): fund_source가 없는 항목(기존 데이터 전부 해당)은
# "전부 정부지원분으로 간주"(A안)도 "전부 제외"(B안)도 하지 않는다. 대신:
#   - 자동 판정(quality_gate/8인심사위원/감점전파)에는 그 항목들을 아예 반영하지
#     않는다 — 즉 fund_source="government"로 "명시"된 항목의 합계만으로 한도초과
#     여부를 판단한다 (B안과 동일한 게이트 동작 — 오탐 방지가 최우선).
#   - 대신 미지정 항목이 있으면 그 사실 자체를 budget_breakdown.unresolved_note에
#     "확인 필요" 안내문으로 별도로 노출한다. 이 note는 rejection_risks/budget_risks
#     리스트에 넣지 않는다 — judge_panel "예산증빙" 심사위원과 deduction_map은
#     budget_risks가 비어있는지만 보므로, note를 risks에 안 넣어야 fund_source
#     미지정 상태 자체가 자동으로 감점 판정을 만들지 않는다(거짓 경고 방지).
#     즉 이 note는 사람이 judge_review를 읽을 때만 보이는 "참고 정보"이며,
#     자동 pass/fail 판정에는 전혀 영향을 주지 않는다 (deduction_map과 동일한
#     "설명 전용, 점수에는 반영 안 함" 원칙을 따름).
def _extract_budget_items(budget_detail):
    """budget_detail(list 또는 phase 구조 dict)에서
    {category, item, amount_krw, fund_source} 평면 리스트 추출.
    fund_source: "government"(정부지원분) | "self"(자기부담분) | None(미지정, 기존 데이터 호환)."""
    items = []
    if isinstance(budget_detail, list):
        for b in budget_detail:
            items.append({
                "category": b.get("category"),
                "item": b.get("item"),
                "amount_krw": b.get("amount_krw"),
                "fund_source": b.get("fund_source"),
            })
    elif isinstance(budget_detail, dict):
        for phase_key in sorted(k for k in budget_detail.keys() if k.startswith("phase_")):
            phase = budget_detail[phase_key]
            if not isinstance(phase, dict):
                continue
            for it in phase.get("items", []) or []:
                items.append({
                    "category": it.get("category"),
                    "item": it.get("item"),
                    "amount_krw": it.get("amount_krw"),
                    "fund_source": it.get("fund_source"),
                })
    return items


def _budget_total(budget_detail, items=None):
    if isinstance(budget_detail, dict) and isinstance(budget_detail.get("total_krw"), (int, float)):
        return budget_detail["total_krw"]
    items = items if items is not None else _extract_budget_items(budget_detail)
    amounts = [i["amount_krw"] for i in items if isinstance(i.get("amount_krw"), (int, float))]
    return sum(amounts) if amounts else None


def _budget_source_breakdown(items):
    """items(_extract_budget_items 결과)를 fund_source 기준으로 3분할해서 합계를 낸다.
    반환: {"confirmed_government_krw", "confirmed_self_krw", "unresolved_krw", "unresolved_count"}
    자동 판정에는 confirmed_government_krw만 쓴다 — unresolved는 게이트에 포함하지 않는다."""
    gov = 0
    self_amt = 0
    unresolved = 0
    unresolved_count = 0
    for it in items:
        amt = it.get("amount_krw")
        if not isinstance(amt, (int, float)):
            continue
        src = it.get("fund_source")
        if src == "government":
            gov += amt
        elif src == "self":
            self_amt += amt
        else:
            unresolved += amt
            unresolved_count += 1
    return {
        "confirmed_government_krw": gov,
        "confirmed_self_krw": self_amt,
        "unresolved_krw": unresolved,
        "unresolved_count": unresolved_count,
    }


def check_budget_compatibility(budget_detail, budget_criteria):
    """
    사업자의 budget_detail과 공고 budget_criteria 간 정합성 점검.
    1) fund_source="government"로 명시된 항목의 합계가 공고 지원한도(max_grant_krw)를
       초과하는지 (v0.5.3부터: 총사업비가 아니라 "명시적으로 정부지원분으로 표시된 금액"만
       비교 — fund_source 미지정 항목은 이 판정에서 제외, 대신 breakdown.unresolved_note로
       별도 안내만 함)
    2) 사업자 예산 항목의 category가 공고의 excluded_categories(집행 불가 항목)에 해당하는지
    반환: (risks: list[str], breakdown: dict|None) — breakdown은 judge_review에 총액/
    정부지원분(확인)/자기부담분(확인)/미확인 항목 수와 안내문을 노출해서 사람이 어느
    기준으로 판정됐는지, 그리고 무엇이 아직 확인 안 됐는지 볼 수 있게 함.
    """
    risks = []
    if not budget_detail or not budget_criteria:
        return risks, None

    items = _extract_budget_items(budget_detail)
    total = _budget_total(budget_detail, items)
    max_grant = budget_criteria.get("max_grant_krw")
    src = _budget_source_breakdown(items)

    breakdown = {
        "total_krw": total,
        "confirmed_government_krw": src["confirmed_government_krw"],
        "confirmed_self_krw": src["confirmed_self_krw"],
        "unresolved_krw": src["unresolved_krw"],
        "unresolved_count": src["unresolved_count"],
        "unresolved_note": None,
    }

    government_krw = src["confirmed_government_krw"]

    if isinstance(max_grant, (int, float)) and government_krw > max_grant:
        risks.append(
            f"사업자 예산계획에서 fund_source='government'(정부지원분)로 명시된 항목 합계"
            f"({government_krw:,}원)만으로도 이 공고의 지원한도({max_grant:,}원)를 초과함 "
            f"-> 총사업비(전체 {total:,}원)가 아니라 정부지원분 단독 금액 기준으로도 초과이므로 "
            "예산 재조정 또는 지원한도 재확인이 필요"
        )
    elif isinstance(max_grant, (int, float)) and src["unresolved_count"] > 0:
        breakdown["unresolved_note"] = (
            f"예산 항목 {src['unresolved_count']}건에 fund_source(정부지원분/자기부담분 구분)가 "
            f"지정되지 않아 정부지원분 합계를 정확히 계산하지 못함(미구분 금액 "
            f"{src['unresolved_krw']:,}원, 총사업비 {total:,}원 중 일부, 확인된 정부지원분 "
            f"{government_krw:,}원/자기부담분 {src['confirmed_self_krw']:,}원). 총사업비가 지원한도"
            f"({max_grant:,}원)를 넘더라도 자기부담분이 포함된 정상 구성일 수 있어 이 사실만으로 "
            "자동으로 위험 처리하지 않음 -> 정부지원분 단독 금액이 지원한도 이내인지 사람이 "
            "직접 확인 필요 (이 안내는 자동 판정(quality_gate/심사위원/감점전파)에 반영되지 않음, "
            "참고 정보 전용)"
        )

    excluded_categories = budget_criteria.get("excluded_categories") or []
    if excluded_categories:
        conflicting = [
            it for it in items
            if it.get("category") and any(ec in it["category"] for ec in excluded_categories)
        ]
        if conflicting:
            desc_parts = []
            for it in conflicting:
                amt = it.get("amount_krw")
                amt_str = f"{amt:,}원" if isinstance(amt, (int, float)) else "금액 미상"
                desc_parts.append(f"{it['category']}-{it.get('item','?')}({amt_str})")
            risks.append(
                "사업자 예산계획에 이 공고가 지원 제외한다고 명시한 항목 카테고리가 포함됨: "
                + "; ".join(desc_parts)
                + " -> 해당 항목은 이 공고 지원금으로 집행 불가하므로 신청서에서 제외하거나 "
                  "자기부담 재원으로 명시해야 함"
            )
    return risks, breakdown


def draft_application(profile, top_match):
    if not top_match:
        return None

    a = top_match["_raw"]
    name = a["program_name"]
    rubric = a.get("scoring_rubric", [])
    rubric_str = ", ".join(f"{r['item']}({r['weight']}점)" for r in rubric) if rubric else "확인 필요(심사표 미확보)"

    years = None
    founded = parse_date(profile.get("founded_date"))
    if founded:
        years = round(_years_since(founded, today()), 1)

    budget = a.get("budget_criteria", {}) or {}
    max_grant = budget.get("max_grant_krw")
    matching_ratio = budget.get("matching_fund_ratio")

    business_description = _format_business_description(profile.get("business_description"))
    team_experience = _format_team_experience(profile.get("team_experience"))
    budget_detail_str = _format_budget_detail(profile.get("budget_detail"))
    expected_outcomes = _format_expected_outcomes(profile.get("expected_outcomes"))

    # --- 2_신청동기_및_필요성 ---
    if business_description:
        section2 = business_description
    else:
        section2 = (
            "[확인 필요] 이 섹션은 실제 기술/사업 아이템에 대한 구체적 정보가 "
            "business_profile.business_description에 없어 채워지지 않았습니다. "
            "실제 신청 전 대표자가 구체적 기술 내용, 문제의식, 차별점을 입력해야 합니다."
        )

    # --- 3_사업화_계획: business_description(실행 맥락) + budget_detail(예산 기반 실행계획) 결합 ---
    if business_description or budget_detail_str:
        parts = []
        if max_grant:
            parts.append(f"예산 상한 {max_grant:,}원(자기부담률 {matching_ratio}) 기준 내에서 사업화를 추진합니다.")
        if business_description:
            parts.append(f"사업 아이템: {business_description}")
        if budget_detail_str:
            parts.append(f"예산 집행 계획: {budget_detail_str}")
        section3 = " ".join(parts)
    else:
        section3 = (
            "[확인 필요] business_profile.business_description과 budget_detail이 모두 없어 "
            "구체적 실행 계획(마일스톤, 일정, 담당인력)을 작성하지 못했습니다."
        )

    # --- 4_팀_역량 ---
    ceo_age_str = None
    if profile.get("ceo_birth_date"):
        ceo_age_str = "만 " + str(int(_years_since(parse_date(profile["ceo_birth_date"]), today()))) + "세"
    cert_list = profile.get("certifications", [])
    cert_str = _join(cert_list) if isinstance(cert_list, list) else str(cert_list or "")
    if team_experience:
        section4 = (
            f"대표자는 {ceo_age_str or '[확인 필요]'}이며, 보유 인증: "
            f"{cert_str or '없음'}. {team_experience}"
        )
    else:
        section4 = (
            f"대표자는 {ceo_age_str or '[확인 필요]'}이며, 보유 인증: "
            f"{cert_str or '없음'}. "
            "[확인 필요] business_profile.team_experience가 없어 팀원 이력/역할은 작성되지 않았습니다."
        )

    # --- 5_예산_계획 ---
    if budget_detail_str:
        section5 = f"세부 예산 항목: {budget_detail_str}."
    else:
        section5 = (
            "[확인 필요] business_profile.budget_detail이 없어 세부 예산 항목(인건비/재료비/외주비 등) "
            "배분을 작성하지 못했습니다."
        )

    # --- 6_기대효과 ---
    if expected_outcomes:
        section6 = expected_outcomes
    else:
        section6 = (
            "[확인 필요] business_profile.expected_outcomes가 없어 매출/고용 증대 등 "
            "정량적 기대효과와 산출 근거를 작성하지 못했습니다."
        )

    # --- required_documents_checklist: documents_status(신/구 형태 모두)를 정규화해서 반영 ---
    # v0.5.2: exact match뿐 아니라 정규화/동의어 테이블 기반 fuzzy match도 시도(match_document_status).
    documents_status = _normalize_documents_status(profile.get("documents_status"))
    required_documents_checklist = []
    document_match_notes = []
    for d in a.get("required_documents", []):
        prepared, match_type, matched_key, reason = match_document_status(d, documents_status)
        required_documents_checklist.append({
            "document": d,
            "prepared": bool(prepared),
            "match_type": match_type,
            "matched_against": matched_key,
        })
        if match_type == "unmatched":
            document_match_notes.append(f"'{d}': {reason}")
        elif match_type in ("normalized", "synonym"):
            document_match_notes.append(f"'{d}' -> '{matched_key}' ({reason})")

    draft = {
        "program_name": name,
        "sections": {
            "1_사업개요": (
                f"신청기업은 {profile.get('industry_code', '[업종 확인 필요]')} 분야에서 "
                f"{years if years is not None else '[확인 필요]'}년간 사업을 영위해온 "
                f"{profile.get('biz_type', '[기업형태 확인 필요]')}입니다. "
                f"소재지는 {profile.get('region', '[확인 필요]')}이며, 상시근로자 {profile.get('employees', '[확인 필요]')}명 규모입니다."
            ),
            "2_신청동기_및_필요성": section2,
            "3_사업화_계획": section3,
            "4_팀_역량": section4,
            "5_예산_계획": section5,
            "6_기대효과": section6,
        },
        "matched_scoring_rubric": rubric_str,
        "page_limit": a.get("submission_format", {}).get("page_limit"),
        "required_documents_checklist": required_documents_checklist,
        "document_match_notes": document_match_notes,
    }
    return draft


# ---------------------------------------------------------------------------
# v0.5.0 확장 STEP 2: PSST 자동검수 (Problem/Solution/Support/Traction)
#   출처: 정부지원사업_판정로직_확장스펙.md 2번 표.
#   핵심 원칙: PASS/FAIL만 내리지 않고, 어느 문장이 어떤 증빙부족 때문에 FAIL인지 기록.
#   판정만 하고 문장을 대신 써주지 않는다 — "무엇이 없는지"만 지적.
#   구현은 draft의 섹션 텍스트/구조 존재여부 기반 휴리스틱이다(의미 이해 아님, 알려진 한계).
# ---------------------------------------------------------------------------
_MEASURE_UNIT_RE = re.compile(
    r"\d[\d,\.]*\s*(만|억)?\s*(분|시간|일|주|개월|년|건|회|명|개|배|원|%|퍼센트)"
)


def _has_measured_value(text):
    return bool(_MEASURE_UNIT_RE.search(text or ""))


def assess_psst(profile, draft):
    """
    PSST(Problem/Solution/Support/Traction) 자동검수.
    draft가 없으면(매칭 프로그램 없음) 4구간 모두 검수 대상 아님(not_applicable)으로 처리.
    반환: {"problem":{"result":..,"reason":..}, "solution":.., "support":.., "traction":..}
    """
    if draft is None:
        na = {"result": "not_applicable", "reason": "매칭된 사업이 없어 신청서 초안 자체가 없음 -> PSST 검수 대상 아님"}
        return {"problem": na, "solution": na, "support": na, "traction": na}

    sections = draft["sections"]
    section2 = sections.get("2_신청동기_및_필요성", "")
    section3 = sections.get("3_사업화_계획", "")
    section6 = sections.get("6_기대효과", "")

    # --- Problem: 고객·현장 문제를 시간/비용/오류로 설명했는가 ---
    if "[확인 필요]" in section2:
        problem = {
            "result": "fail",
            "reason": "business_description이 없어 고객/현장 문제 서술 자체가 없음 (감성서사조차 없음)",
        }
    elif not _has_measured_value(section2):
        problem = {
            "result": "fail",
            "reason": "문제 서술은 있으나 시간/비용/오류 등 측정값(숫자+단위)이 발견되지 않음 "
                      "-> 감성서사만 있고 측정값이 없는 상태로 판단",
        }
    else:
        problem = {"result": "pass", "reason": "문제 서술에서 측정값(숫자+단위)을 확인함"}

    # --- Solution: 문제와 기능이 1:1 대응하는가 ---
    budget_detail_present = bool(profile.get("budget_detail"))
    if "[확인 필요]" in section3:
        solution = {
            "result": "fail",
            "reason": "business_description/budget_detail이 모두 없어 문제-기능 대응 관계를 "
                      "확인할 근거 자체가 없음",
        }
    elif not budget_detail_present:
        solution = {
            "result": "fail",
            "reason": "budget_detail(실행 계획/예산)이 없어 기능이 실제 실행 항목으로 연결되는지 "
                      "확인 불가 -> 기능 나열만 있고 문제 대응 맵이 없는 상태로 판단",
        }
    else:
        solution = {
            "result": "pass",
            "reason": "business_description과 budget_detail(실행 항목)이 함께 확인되어 "
                      "문제-실행 연결 근거가 있음",
        }

    # --- Support: 증빙·견적·현장자료가 연결되는가 ---
    checklist = draft.get("required_documents_checklist", [])
    prepared_count = sum(1 for d in checklist if d.get("prepared"))
    if not checklist:
        support = {
            "result": "fail",
            "reason": "required_documents_checklist 자체가 없어(공고 필수서류 미확보) 증빙 연결 여부를 "
                      "확인할 수 없음",
        }
    elif prepared_count == 0:
        support = {
            "result": "fail",
            "reason": f"필수서류 {len(checklist)}건 중 준비완료로 확인된 서류가 0건 -> 사진·견적·실측·"
                      "기존 데이터 등 증빙이 연결되지 않은 상태로 판단",
        }
    else:
        support = {
            "result": "pass",
            "reason": f"필수서류 {len(checklist)}건 중 {prepared_count}건이 준비완료로 확인되어 "
                      "증빙 연결 근거가 있음",
        }

    # --- Traction: 기간 내 성과 측정 계획이 있는가 ---
    if "[확인 필요]" in section6:
        traction = {
            "result": "fail",
            "reason": "expected_outcomes가 없어 기간 내 성과 측정 계획 자체가 없음",
        }
    elif not _has_measured_value(section6):
        traction = {
            "result": "fail",
            "reason": "기대효과 서술은 있으나 산출물/측정식/기준선을 나타내는 숫자+단위가 발견되지 않음",
        }
    else:
        traction = {
            "result": "pass",
            "reason": "기대효과 서술에서 측정 가능한 목표 수치를 확인함",
        }

    return {"problem": problem, "solution": solution, "support": support, "traction": traction}


# ---------------------------------------------------------------------------
# v0.5.0 확장 STEP 3: 8인 가상 심사위원
#   출처: 정부지원사업_판정로직_확장스펙.md 3번 표. 8인 로직 자체는 공고 불변,
#   공고별 scoring_rubric 매핑만 가변(키워드 기반 휴리스틱).
# ---------------------------------------------------------------------------
JUDGE_DEFINITIONS = [
    {
        "key": "공고적합성",
        "name": "공고적합성 심사위원",
        "key_question": "이 아이템이 공고 목적과 직접 맞는가",
        "rubric_keywords": ["적합", "목적", "부합"],
    },
    {
        "key": "자격규정",
        "name": "자격·규정 심사위원",
        "key_question": "자격·제외요건·중복수혜·체납·업종 배제가 해결됐는가",
        "rubric_keywords": ["자격", "규정", "요건"],
    },
    {
        "key": "문제정의",
        "name": "문제정의 심사위원",
        "key_question": "문제를 수치와 현장맥락으로 입증했는가",
        "rubric_keywords": ["필요성", "문제", "기술성"],
    },
    {
        "key": "AI필요성",
        "name": "AI 필요성 심사위원",
        "key_question": "왜 AI여야 하며 기존 수작업/일반툴과 무엇이 다른가",
        "rubric_keywords": ["AI", "기술", "차별성", "혁신"],
    },
    {
        "key": "실행계획",
        "name": "실행계획 심사위원",
        "key_question": "6개월 내 범위가 현실적인가",
        "rubric_keywords": ["실행", "계획", "사업화"],
    },
    {
        "key": "예산증빙",
        "name": "예산·증빙 심사위원",
        "key_question": "돈의 사용처와 산출물·견적이 연결되는가",
        # "사업비"는 v0.5.4에서 추가 — 3번째 실제 공고(생활문화 혁신지원)의 심사배점 항목
        # "사업비 비목별 집행계획"이 기존 "예산"/"자금" 키워드로는 매칭되지 않아 발견된
        # 과소매칭. 추가 전 전체 공고(real_announcements.json/sample_announcements.json)
        # scoring_rubric 텍스트를 스캔해 "사업비전"류 무관 단어에 우연히 포함되는 사례가
        # 없음을 확인한 뒤 추가함(v0.4.0의 짧은 키워드 과다매칭 재발 방지 원칙 준수).
        "rubric_keywords": ["예산", "자금", "사업비"],
    },
    {
        "key": "성과확장",
        "name": "성과·확장 심사위원",
        "key_question": "도입 성과를 측정할 수 있는가",
        # "기대효과"는 v0.5.4에서 추가 — 3번째 실제 공고의 심사배점 항목 "파급효과 - 사업수행
        # 기대효과"가 기존 "성과"/"확장"/"고용"/"사회적" 키워드로는 매칭되지 않아 발견된
        # 과소매칭(주의: "기대효과"는 "성과"를 부분포함하지 않는 별개 표현이라 "성과" 하나로는
        # 못 잡음). 전체 공고 scoring_rubric 텍스트 스캔 후 무관 단어와의 충돌 없음을 확인.
        "rubric_keywords": ["성과", "확장", "고용", "사회적", "기대효과"],
    },
    {
        "key": "발표QA",
        "name": "발표·Q&A 심사위원",
        "key_question": "왜 지금, 왜 너, 왜 이 방식인지 방어 가능한가",
        # 스펙 원문 표에도 이 심사위원의 rubric 매핑 예시가 없음(서류평가 rubric에는
        # 보통 발표/Q&A 항목이 없기 때문) -> rubric 매핑 대상에서 항상 제외.
        "rubric_keywords": [],
    },
]

_AI_EXAGGERATION_RISK_TYPES = {"과장", "과장·책임소재 불명", "책임위험"}


def run_judge_panel(draft, top_match, psst_review, risk_phrase_hits, budget_risks):
    """
    8인 가상 심사위원 평가. 각 심사위원은 이미 계산된 구조적 신호(자격 미확정/미준비서류/
    결격위험/예산리스크/위험표현/PSST 결과)를 근거로 0~5점 + 즉시경고(warning)를 매긴다.
    draft가 없으면(매칭 프로그램 없음) 패널 평가 대상 자체가 없음으로 처리.
    """
    if draft is None or top_match is None:
        return {
            "panel": [],
            "immediate_warnings": ["매칭된 사업이 없어 심사위원 패널 평가 대상 자체가 없음"],
            "warning_count": 0,
        }

    risk_types = {h["risk_type"] for h in risk_phrase_hits}
    unresolved = top_match.get("_unresolved_criteria", [])
    unprepared = [d["document"] for d in draft.get("required_documents_checklist", []) if not d["prepared"]]
    disqualification_risks = top_match.get("disqualification_risks", [])

    def pf(pass_ok, pass_reason, fail_reason):
        return (5, False, pass_reason) if pass_ok else (1, True, fail_reason)

    judge_scores = {}

    judge_scores["공고적합성"] = pf(
        "범위 과다" not in risk_types,
        "공고 목적과 무관한 과도한 확장 서술 없음",
        "위험표현 사전에서 '범위 과다'(예: 플랫폼으로 대박 확장) 유형 표현이 발견됨 "
        "-> 공고 목적과 무관한 확장 아이디어 혼입 위험",
    )

    judge_scores["자격규정"] = pf(
        not unresolved and not unprepared and not disqualification_risks,
        "자격기준 미확정 항목, 미준비 서류, 결격 위험 모두 없음",
        f"자격기준 미확정 {len(unresolved)}건 / 미준비서류 {len(unprepared)}건 / "
        f"결격위험 {len(disqualification_risks)}건 -> 서류 미확보 또는 확인 필요 방치 상태",
    )

    judge_scores["문제정의"] = pf(
        psst_review["problem"]["result"] == "pass",
        "문제정의(PSST-Problem) 검수 통과: 측정값 기반 문제 서술 확인",
        "문제정의(PSST-Problem) 검수 미통과: " + psst_review["problem"]["reason"],
    )

    judge_scores["AI필요성"] = pf(
        not (risk_types & _AI_EXAGGERATION_RISK_TYPES),
        "'AI가 다 해준다'류 과장 표현 없음",
        "위험표현 사전에서 과장/책임소재 불명 유형 표현이 발견됨 -> AI 필요성 서술이 과장으로 "
        "방어력 약화 위험",
    )

    judge_scores["실행계획"] = pf(
        psst_review["solution"]["result"] == "pass",
        "실행계획(PSST-Solution) 검수 통과: 실행 항목(budget_detail)과 연결 확인",
        "실행계획(PSST-Solution) 검수 미통과: " + psst_review["solution"]["reason"],
    )

    judge_scores["예산증빙"] = pf(
        not budget_risks and "자산취득성 위험" not in risk_types,
        "예산 정합성 문제 및 장비구매성 위험표현 없음",
        f"예산 정합성 위험 {len(budget_risks)}건 또는 '자산취득성 위험'(장비 구매) 표현 발견 "
        "-> 견적/집행근거 부족 위험",
    )

    judge_scores["성과확장"] = pf(
        psst_review["traction"]["result"] == "pass",
        "성과확장(PSST-Traction) 검수 통과: 측정 가능한 목표치 확인",
        "성과확장(PSST-Traction) 검수 미통과: " + psst_review["traction"]["reason"],
    )

    qa_fail = psst_review["problem"]["result"] != "pass" or psst_review["solution"]["result"] != "pass"
    judge_scores["발표QA"] = pf(
        not qa_fail,
        "문제정의·실행계획 근거가 모두 확인되어 핵심 WHY 방어 근거 있음",
        "문제정의 또는 실행계획(PSST) 근거 부족 -> 왜 지금/왜 이 방식인지 방어 불가 위험",
    )

    panel = []
    immediate_warnings = []
    for jd in JUDGE_DEFINITIONS:
        score, warning, reason = judge_scores[jd["key"]]
        mapped = []
        if jd["rubric_keywords"]:
            rubric = top_match["_raw"].get("scoring_rubric", [])
            for item in rubric:
                if any(kw in item["item"] for kw in jd["rubric_keywords"]):
                    mapped.append(f"{item['item']}({item['weight']}점)")
        panel.append({
            "judge": jd["name"],
            "key_question": jd["key_question"],
            "score": score,
            "warning": warning,
            "reason": reason,
            "mapped_rubric_items": mapped,
        })
        if warning:
            immediate_warnings.append(f"{jd['name']}: {reason}")

    return {
        "panel": panel,
        "immediate_warnings": immediate_warnings,
        "warning_count": len(immediate_warnings),
    }


# ---------------------------------------------------------------------------
# v0.5.0 확장 STEP 4: 감점 전파 모델
#   출처: 정부지원사업_판정로직_확장스펙.md 4번 표(대표 이슈 5종, 고정 계수).
#   confidence 점수는 다시 깎지 않는다 — judge_review 안에 설명 문장으로만 추가.
#   공고별 가변 전파계수는 이번 스코프에 포함하지 않음(스펙 원문 명시).
# ---------------------------------------------------------------------------
DEDUCTION_PROPAGATION_TABLE = {
    "예산 근거 누락": {
        "direct": {"criterion": "예산", "amount": -5},
        "propagated": [
            {"criterion": "실행", "amount": -3},
            {"criterion": "성과", "amount": -2},
            {"criterion": "발표", "amount": -2},
        ],
        "interpretation": "\"돈을 왜 쓰는지\"를 못 막으면 실현성·성과·발표가 동시 약화",
    },
    "자격 증빙 미확보": {
        "direct": {"criterion": "자격", "amount": "BLOCK"},
        "propagated": [
            {"criterion": "실행", "amount": -3},
            {"criterion": "발표", "amount": -3},
        ],
        "interpretation": "아예 제출금지 수준",
    },
    "작업시간 실측 없음": {
        "direct": {"criterion": "필요성", "amount": -4},
        "propagated": [
            {"criterion": "성과", "amount": -2},
            {"criterion": "발표", "amount": -1},
        ],
        "interpretation": "문제 크기와 개선폭을 둘 다 증명 못함",
    },
    "AI 필요성 불명확": {
        "direct": {"criterion": "AI활용", "amount": -4},
        "propagated": [
            {"criterion": "공고적합성", "amount": -2},
            {"criterion": "발표", "amount": -2},
        ],
        "interpretation": "왜 AI여야 하는지 방어 불가",
    },
    "산출물 미정의": {
        "direct": {"criterion": "실행", "amount": -4},
        "propagated": [
            {"criterion": "성과", "amount": -3},
            {"criterion": "예산", "amount": -2},
        ],
        "interpretation": "협약기간 안에 남는 것이 없음",
    },
}


def build_deduction_map(profile, draft, psst_review, judge_panel_review, budget_risks, unprepared_count):
    """
    대표 이슈 5종의 발생 여부를 기존 신호(budget_risks/unprepared/PSST/8인심사위원)로 판정하고,
    발생한 이슈만 스펙 원문의 고정 전파표를 그대로 붙여 반환한다.
    confidence는 건드리지 않음 — 설명 문장 용도.
    """
    if draft is None:
        return {
            "triggered_issues": [],
            "note": "매칭된 사업이 없어 감점 전파 분석 대상 자체가 없음",
        }

    triggered_names = []

    if not profile.get("budget_detail") or budget_risks:
        triggered_names.append("예산 근거 누락")

    if unprepared_count > 0:
        triggered_names.append("자격 증빙 미확보")

    if psst_review["problem"]["result"] == "fail":
        triggered_names.append("작업시간 실측 없음")

    ai_warning = any(
        p["judge"] == "AI 필요성 심사위원" and p["warning"]
        for p in judge_panel_review.get("panel", [])
    )
    if ai_warning:
        triggered_names.append("AI 필요성 불명확")

    if psst_review["traction"]["result"] == "fail":
        triggered_names.append("산출물 미정의")

    triggered_issues = []
    for name in triggered_names:
        entry = DEDUCTION_PROPAGATION_TABLE[name]
        triggered_issues.append({
            "issue": name,
            "direct_deduction": entry["direct"],
            "propagated_deductions": entry["propagated"],
            "interpretation": entry["interpretation"],
        })

    return {
        "triggered_issues": triggered_issues,
        "note": (
            "감점전파는 quality_gate_result.overall_confidence를 다시 깎지 않는다. "
            "이 이슈가 어느 항목까지 번지는지 설명하는 용도로만 사용한다."
            if triggered_issues else
            "감점전파 대상 이슈 없음 (예산/자격/문제정의/AI필요성/산출물 관련 트리거 모두 미해당)"
        ),
    }


# ---------------------------------------------------------------------------
# STEP 5: 심사위원 모드 자기검수 (Judge Mode Self-Review)
#   원칙: 무조건 긍정하지 않는다. "떨어질 이유"부터 찾는다.
# ---------------------------------------------------------------------------
def _rubric_covered(item_text, full_text):
    """
    v0.4.0: 심사배점 항목이 초안에서 다뤄졌는지 판단하는 개선된 휴리스틱.
    - '가점'류(서술로 커버 불가능한 항목)는 None(해당없음) 반환 -> 커버리지 체크 대상에서 제외.
    - 항목명을 토큰으로 분리(조사/일반어 제외)한 뒤:
        * 토큰이 동의어 테이블의 어근을 부분포함하면 -> 동의어 중 하나라도 본문에 있으면 커버.
        * 그 외 토큰은 -> 완전일치(해당 단어 그대로 본문에 있어야) 커버.
      토큰 중 하나라도 커버되면 항목 전체를 커버된 것으로 간주(OR 조건).
    - 짧은 어근의 무분별한 부분매칭(예: 아무 토큰의 앞 2글자)은 과도한 오탐(거의 모든 항목이
      '커버됨'으로 판정)을 만들어 제거했다 — 동의어 테이블에 명시적으로 등록된 어근에 한해서만
      부분매칭을 허용한다.
    """
    if any(skip in item_text for skip in RUBRIC_SKIP_ITEMS):
        return None

    tokens = [t for t in re.split(r"[\s·,()]+", item_text) if t and t not in RUBRIC_STOPWORDS]
    if not tokens:
        return True

    for t in tokens:
        synonym_hit = False
        for base, syns in RUBRIC_SYNONYMS.items():
            if base in t:
                synonym_hit = True
                variants = set(syns) | {base}
                if any(v in full_text for v in variants):
                    return True
        if not synonym_hit and t in full_text:
            return True
    return False


def judge_mode_self_review(draft, top_match, profile):
    rejection_risks = []
    exaggeration_flags = []
    unsupported_claims = []

    if draft is None:
        na_psst = {"result": "not_applicable", "reason": "매칭된 사업이 없어 신청서 초안 자체가 없음 -> 검수 대상 아님"}
        return {
            "rejection_risks": ["매칭된 사업이 없어 초안 자체가 존재하지 않음 -> 심사 대상 아님"],
            "exaggeration_flags": [],
            "unsupported_claims": [],
            "overall_pass_recommendation": False,
            "psst_review": {"problem": na_psst, "solution": na_psst, "support": na_psst, "traction": na_psst},
            "judge_panel_review": {
                "panel": [],
                "immediate_warnings": ["매칭된 사업이 없어 심사위원 패널 평가 대상 자체가 없음"],
                "warning_count": 0,
            },
            "deduction_map": {"triggered_issues": [], "note": "매칭된 사업이 없어 감점 전파 분석 대상 자체가 없음"},
            "budget_breakdown": None,
            "_unconfirmed_sections": [],
            "_unprepared_documents": [],
        }

    a = top_match["_raw"]
    full_text = " ".join(draft["sections"].values())

    for word in EXAGGERATION_WORDS:
        if word in full_text:
            exaggeration_flags.append(f"과장 표현 '{word}' 사용 -> 근거 데이터 없이 사용 시 심사위원 신뢰도 감점 위험")

    # v0.5.0: 위험표현 사전(스펙 1번) 스캔 결과를 추가(append)한다 — 기존 EXAGGERATION_WORDS
    # 체크를 대체하지 않음. "발견 시 exaggeration_flags에 추가"라는 지시를 그대로 따름.
    risk_phrase_hits = scan_risk_phrases(full_text)
    for hit in risk_phrase_hits:
        exaggeration_flags.append(_risk_phrase_flag_text(hit))

    if not exaggeration_flags:
        exaggeration_flags.append("검토 완료: 명백한 과장 표현 없음 (단, 실제 제출 전 재검수 권장)")

    unconfirmed_sections = [k for k, v in draft["sections"].items() if "[확인 필요]" in v]
    if unconfirmed_sections:
        unsupported_claims.append(
            f"다음 섹션은 구체적 근거 없이 템플릿으로만 채워짐 -> 제출 전 반드시 실제 데이터로 대체: {', '.join(unconfirmed_sections)}"
        )
    else:
        unsupported_claims.append("검토 완료: 템플릿 잔여 문구 없음 (모든 섹션이 실제 입력값으로 채워짐)")

    page_limit = draft.get("page_limit")
    if page_limit is None:
        rejection_risks.append("페이지 제한 정보가 없어 분량 초과 여부를 검증할 수 없음 -> 원문 재확인 필요")

    rubric = a.get("scoring_rubric", [])
    if rubric:
        for r in rubric:
            item = r["item"]
            covered = _rubric_covered(item, full_text)
            if covered is False:
                rejection_risks.append(
                    f"심사배점 항목 '{item}'({r['weight']}점)이 초안에서 명확히 다뤄지지 않음 -> 배점 손실 위험"
                )
            # covered is None(가점류) -> 서술 커버리지 체크 대상 아님, 조용히 건너뜀
    else:
        rejection_risks.append("심사표(배점기준)를 원문에서 확보하지 못해 배점 대응 여부를 검증할 수 없음")

    unresolved = top_match.get("_unresolved_criteria", [])
    if unresolved:
        rejection_risks.append(
            f"다음 자격기준이 미확정 상태로 접수 시 서류심사에서 부적격 판정 위험: {', '.join(unresolved)}"
        )

    unprepared = [d["document"] for d in draft.get("required_documents_checklist", []) if not d["prepared"]]
    if unprepared:
        rejection_risks.append(
            f"필수서류 {len(unprepared)}건이 아직 '준비완료'로 체크되지 않음: {', '.join(unprepared)}"
        )

    if top_match.get("disqualification_risks"):
        rejection_risks.append("결격 위험이 이미 감지되었음: " + "; ".join(top_match["disqualification_risks"]))

    # v0.4.0 / v0.5.3: 예산 정합성 체크 (정부지원분 vs 자기부담분 구분)
    budget_risks, budget_breakdown = check_budget_compatibility(
        profile.get("budget_detail"), a.get("budget_criteria", {}) or {}
    )
    rejection_risks.extend(budget_risks)

    # v0.5.0: PSST 자동검수 -> 8인 가상 심사위원 -> 감점 전파 모델 (이 순서로 서로 입력이 됨)
    psst_review = assess_psst(profile, draft)
    judge_panel_review = run_judge_panel(draft, top_match, psst_review, risk_phrase_hits, budget_risks)
    deduction_map = build_deduction_map(
        profile, draft, psst_review, judge_panel_review, budget_risks, len(unprepared)
    )

    if not rejection_risks:
        rejection_risks.append("검토 완료: 구조적/형식적 감점 요인 없음 (자격기준, 필수서류, 심사배점 커버리지, 페이지제한, 예산 정합성 모두 충족). "
                                "단, 이는 형식 요건 충족 여부만 확인한 것이며 내용의 설득력·기술적 타당성은 사람이 최종 검토해야 함")

    psst_all_pass = all(v["result"] == "pass" for v in psst_review.values())
    judge_panel_clean = judge_panel_review.get("warning_count", 0) == 0

    overall_pass_recommendation = (
        len(unprepared) == 0
        and len(unconfirmed_sections) == 0
        and not top_match.get("disqualification_risks")
        and page_limit is not None
        and psst_all_pass
        and judge_panel_clean
    )

    return {
        "rejection_risks": rejection_risks,
        "exaggeration_flags": exaggeration_flags,
        "unsupported_claims": unsupported_claims,
        "overall_pass_recommendation": overall_pass_recommendation,
        "psst_review": psst_review,
        "judge_panel_review": judge_panel_review,
        "deduction_map": deduction_map,
        "budget_breakdown": budget_breakdown,
        "_unconfirmed_sections": unconfirmed_sections,
        "_unprepared_documents": unprepared,
    }


# ---------------------------------------------------------------------------
# 통합 진입점 (v0.5.1) — 외부 시스템(AI직원 플랫폼 등) 연동용 단일 함수
#   기존 로직(check_eligibility_and_disqualification/_score_criteria/
#   draft_application/judge_mode_self_review/apply_quality_gate)은 전혀
#   재작성하지 않고 그대로 호출한다 — 이 함수는 순수하게 "감싸기"(wrapping)만 한다.
#   collect_and_extract_announcements()/match_programs()의 다건-공고 수집·매칭
#   파이프라인을 거치지 않고, 이미 확정된 announcement 1건에 대해 business_profile
#   1건의 초안+심사위원 검수(위험표현/PSST/8인심사위원/감점전파 전부 포함)만
#   실행하고 싶은 외부 호출측을 위한 진입점.
# ---------------------------------------------------------------------------
def review_application(business_profile, announcement, ref_date=None):
    """
    business_profile 1건 + announcement(raw dict) 1건을 받아
    "서류 초안 작성 + 심사위원 모드 자기검수(4개 서브시스템 포함)" 결과를
    하나의 dict로 반환하는 통합 진입점.

    내부적으로 기존 파이프라인 함수를 그대로 재사용한다:
      check_eligibility_and_disqualification() -> _score_criteria()
      -> draft_application() -> judge_mode_self_review() -> apply_quality_gate()

    반환값 구조는 run()의 최상위 출력과 동일한 하위 필드를 사용한다:
      { "draft_application": ..., "judge_review": ..., "quality_gate_result": ...,
        "lock_state": ... }
    judge_review 안에 psst_review/judge_panel_review/deduction_map이 모두 포함됨.
    """
    ref_date = ref_date or today()

    criteria, disq_risks, _unverifiable = check_eligibility_and_disqualification(
        business_profile, announcement, ref_date
    )
    score, unresolved = _score_criteria(criteria)

    top_match = {
        "program_name": announcement.get("program_name"),
        "eligibility_confidence": round(score, 2),
        "required_documents": announcement.get("required_documents", []),
        "deadline": announcement.get("deadline"),
        "disqualification_risks": disq_risks,
        "_raw": announcement,
        "_unresolved_criteria": unresolved,
    }

    draft = draft_application(business_profile, top_match)
    judge_review = judge_mode_self_review(draft, top_match, business_profile)
    quality_gate_result = apply_quality_gate([top_match], judge_review, draft)

    judge_review_public = {k: v for k, v in judge_review.items() if not k.startswith("_")}

    return {
        "draft_application": draft,
        "judge_review": judge_review_public,
        "quality_gate_result": quality_gate_result,
        "lock_state": quality_gate_result["lock_state"],
    }


# ---------------------------------------------------------------------------
# QUALITY GATE (숫자 기준 + 질적 기준 AND 결합)
# ---------------------------------------------------------------------------
def apply_quality_gate(matched_programs, judge_review, draft):
    if not matched_programs:
        return {
            "overall_confidence": 0.0,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "confidence_passed": False,
            "judge_pass_recommendation": False,
            "lock_state": "DRAFT",
            "routed_to": "human_review",
            "reasons": ["매칭된 지원사업 없음 -> quality_gate/심사위원 검수 대상 자체가 없음"],
        }

    top = matched_programs[0]
    base_confidence = top["eligibility_confidence"]

    real_risks = [r for r in judge_review["rejection_risks"] if not r.startswith("검토 완료:")]
    penalty = 0.05 * min(len(real_risks), 3)
    overall_confidence = max(0.0, round(base_confidence - penalty, 3))
    confidence_passed = overall_confidence >= CONFIDENCE_THRESHOLD
    judge_passed = judge_review["overall_pass_recommendation"]

    reasons = []

    if confidence_passed:
        reasons.append(
            f"[통과] quality_gate(숫자 기준): overall_confidence({overall_confidence}) "
            f">= confidence_threshold({CONFIDENCE_THRESHOLD}) (base={base_confidence}, 감점위험 {len(real_risks)}건 반영)"
        )
    else:
        reasons.append(
            f"[미통과] quality_gate(숫자 기준): overall_confidence({overall_confidence}) "
            f"< confidence_threshold({CONFIDENCE_THRESHOLD}) (base={base_confidence}, 감점위험 {len(real_risks)}건 반영)"
        )

    if judge_passed:
        reasons.append("[통과] 심사위원 모드(질적 기준): overall_pass_recommendation=true")
    else:
        detail = []
        unconfirmed = judge_review.get("_unconfirmed_sections", [])
        if unconfirmed:
            detail.append(f"'[확인 필요]' 표시가 남은 섹션 {len(unconfirmed)}개: {', '.join(unconfirmed)}")
        unprepared = judge_review.get("_unprepared_documents", [])
        if unprepared:
            detail.append(f"필수서류 미준비 {len(unprepared)}건: {', '.join(unprepared)}")
        if top.get("disqualification_risks"):
            detail.append("결격 위험 감지됨: " + "; ".join(top["disqualification_risks"]))
        other_risks = [
            r for r in real_risks
            if "'[확인 필요]'" not in r and "필수서류" not in r and "결격 위험" not in r
        ]
        if other_risks:
            detail.append(f"기타 감점 위험 {len(other_risks)}건: " + " | ".join(other_risks))
        # v0.5.0: PSST/8인심사위원 미통과 사유도 구체적으로 노출
        psst_review = judge_review.get("psst_review", {})
        psst_fails = [k for k, v in psst_review.items() if v.get("result") == "fail"]
        if psst_fails:
            detail.append(f"PSST 미통과 구간 {len(psst_fails)}개: {', '.join(psst_fails)}")
        judge_panel_review = judge_review.get("judge_panel_review", {})
        if judge_panel_review.get("warning_count", 0) > 0:
            detail.append(
                f"8인 심사위원 즉시경고 {judge_panel_review['warning_count']}건: "
                + " | ".join(judge_panel_review.get("immediate_warnings", []))
            )
        reasons.append(
            "[미통과] 심사위원 모드(질적 기준): overall_pass_recommendation=false - "
            + ("; ".join(detail) if detail else "구체 사유 확인 안됨(로직 점검 필요)")
        )

    lock_state = "READY_FOR_APPROVAL" if (confidence_passed and judge_passed) else "DRAFT"
    routed_to = "auto_complete" if lock_state == "READY_FOR_APPROVAL" else "human_review"

    if lock_state == "DRAFT":
        reasons.append(
            "최종 판정: quality_gate 통과 여부와 심사위원 overall_pass_recommendation을 "
            "모두 만족해야 READY_FOR_APPROVAL로 전환됨. 하나 이상 미충족이므로 DRAFT 유지, human_review로 라우팅."
        )
    else:
        reasons.append("최종 판정: 숫자 기준과 질적 기준을 모두 만족하여 READY_FOR_APPROVAL로 전환됨.")

    return {
        "overall_confidence": overall_confidence,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "confidence_passed": confidence_passed,
        "judge_pass_recommendation": judge_passed,
        "lock_state": lock_state,
        "routed_to": routed_to,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run(input_data, announcements_path=None):
    business_profile = input_data["business_profile"]
    target_period = input_data["target_period"]
    ref_date = today()

    needs_confirmation = []

    try:
        announcements, nc1 = collect_and_extract_announcements(target_period, announcements_path)
        needs_confirmation += nc1
    except Exception as e:
        log_failure("collect_and_extract_announcements", str(input_data)[:500], e)
        raise

    try:
        matched, excluded, nc2 = match_programs(business_profile, announcements, target_period, ref_date)
        needs_confirmation += nc2
    except Exception as e:
        log_failure("match_programs", str(input_data)[:500], e)
        raise

    top_match = matched[0] if matched else None

    try:
        draft = draft_application(business_profile, top_match)
    except Exception as e:
        log_failure("draft_application", str(top_match)[:500], e)
        raise

    try:
        judge_review = judge_mode_self_review(draft, top_match, business_profile)
    except Exception as e:
        log_failure("judge_mode_self_review", str(draft)[:500], e)
        raise

    quality_gate_result = apply_quality_gate(matched, judge_review, draft)
    if quality_gate_result["lock_state"] != "READY_FOR_APPROVAL":
        log_failure(
            "quality_gate",
            f"program={top_match['program_name'] if top_match else None}",
            f"lock_state=DRAFT (confidence_passed={quality_gate_result['confidence_passed']}, "
            f"judge_pass_recommendation={quality_gate_result['judge_pass_recommendation']})",
            quality_gate_result["overall_confidence"],
        )

    matched_public = [
        {k: v for k, v in m.items() if not k.startswith("_")} for m in matched
    ]
    judge_review_public = {k: v for k, v in judge_review.items() if not k.startswith("_")}

    output = {
        "matched_programs": matched_public,
        "excluded_programs": excluded,
        "draft_application": draft,
        "judge_review": judge_review_public,
        "quality_gate_result": quality_gate_result,
        "lock_state": quality_gate_result["lock_state"],
        "needs_confirmation": sorted(set(needs_confirmation)),
        "run_meta": {
            "ref_date": ref_date.isoformat(),
            "target_period": target_period,
        },
    }
    return output


# ---------------------------------------------------------------------------
# v0.6.0: 다중 사업 프로필 대응 (business_profiles.yaml 기반)
#   출처: decision-log_skill-factory-architecture.md §15 (Fable 5 설계, 2026-07-16).
#   기존 단일 business_profile JSON 입력 경로(run()/main())는 전혀 수정하지 않고 그대로
#   보존한다 — 이 섹션은 순수 추가(additive)이며, run()/match_programs()/
#   check_eligibility_and_disqualification()의 확장 인자는 전부 기본값이 기존 동작을
#   재현하도록 설계됨(하위호환).
# ---------------------------------------------------------------------------

def profile_to_business_profile(profile_entry):
    """
    business_profiles.yaml의 프로필 1건(matching_fields 포함)을 기존 엔진의
    business_profile 스키마(check_eligibility_and_disqualification/draft_application이
    참조하는 필드명)로 변환하는 어댑터.
    원칙: matching_fields 값이 null([확인 필요])이면 그대로 None으로 남긴다 — 추측해서
    채우지 않는다. None은 기존 엔진의 "확인 필요"(needs_confirmation) 흐름을 그대로 타므로
    "모름"으로 처리되지, "자격 미달"로 처리되지 않는다(기존 check_eligibility_and_disqualification의
    None 처리 원칙과 동일 — 이 어댑터는 그 원칙을 깨지 않는다).
    """
    mf = profile_entry.get("matching_fields", {}) or {}
    return {
        "biz_type": mf.get("biz_type"),
        # §16 판정3(해결됨, 2026-07-16): business_profiles.yaml의 industry는 "도소매업 —
        # 생화·조경수"처럼 자유서술이고, 기존 엔진/공고 스키마의 industry_codes는 표준산업분류
        # 코드 리스트라 대조 불가하다. 코드 매핑표를 새로 만드는 대신, run_for_profile()이
        # match_programs(industry_code_verified=False)로 호출해 industry_codes 불일치를
        # "불합격(False)"이 아니라 "확인 필요(None)"로 처리하도록 했다(check_eligibility_and_
        # disqualification의 industry_code_verified 인자 참고) — "모름≠미달" 원칙. 혜미가
        # 홈택스 등에서 실제 업종코드를 확인해 이 필드에 코드값을 채우면(및 호출측을
        # industry_code_verified=True로 전환하면) 정밀 대조로 격상 가능.
        "industry_code": mf.get("industry"),
        "founded_date": mf.get("founded_date"),
        "region": mf.get("region"),
        "annual_revenue_krw": mf.get("annual_revenue_krw"),
        "employees": mf.get("employees"),
        "ceo_birth_date": mf.get("ceo_birth_date"),
        "gender": mf.get("ceo_gender"),
        "certifications": mf.get("certifications", []) or [],
        "disqualification_flags": mf.get("disqualification_flags", []) or [],
        # career_interruption_status/reason: business_profiles.yaml에 해당 필드가 아예 없음
        # (추측 금지 원칙에 따라 신설하지 않음) -> None -> 기존 엔진이 "확인 필요"로 처리.
        "career_interruption_status": None,
        "career_interruption_reason": None,
    }


def _classify_founding_requirement(announcement):
    """
    공고가 "개업 전(예비창업)"을 요구하는지 "이미 개업(기창업)"을 요구하는지 판정하는
    보수적 휴리스틱.
    TODO(설계 질문): 공고 스키마(real_announcements.json 등)에 "예비창업자만 지원 가능" vs
    "기창업자만 지원 가능"을 명시하는 전용 필드가 없다 — 오히려 real_announcements.json의
    공고1(경력단절여성 창업케어) eligibility._unmapped_requirements 자체가 "예비창업자는
    min/max_years_since_founding으로 표현이 애매하다"고 명시하고 있어, 이 스키마의 알려진
    한계다. 아래는 program_name 키워드 + min_years_since_founding만으로 판단하는 최소
    휴리스틱이며, Fable 설계 확정 전까지 잠정치다. 확실하지 않으면(unclear) 기존 엔진의
    "확인 필요" 흐름에 맡기고 여기서 임의로 적격/부적격을 확정하지 않는다.
    반환: "pre_founding_required" | "post_founding_required" | "unclear"
    """
    name = announcement.get("program_name", "") or ""
    elig = announcement.get("eligibility", {}) or {}
    min_y = elig.get("min_years_since_founding")

    if "예비창업" in name:
        return "pre_founding_required"
    if "초기창업" in name or "기창업" in name:
        return "post_founding_required"
    if isinstance(min_y, (int, float)) and min_y > 0:
        return "post_founding_required"
    return "unclear"


# §16 판정1 폴백값: business_profiles.yaml의 startup_track_markers를 로드하지 못할 때만 쓴다.
# scripts/collector/promote_candidates.py의 옛 STARTUP_TRACK_MARKERS(9개)와 이 파일의 옛
# 키워드 목록(["창업","예비창업","초기창업"])의 합집합 — yaml이 정본이고 이 상수는 하위호환용.
STARTUP_TRACK_MARKERS_FALLBACK = [
    "예비창업",
    "초기창업",
    "청년창업",
    "창업패키지",
    "창업사업화",
    "창업기업",
    "창업지원",
    "창업경진대회",
    "창업오디션",
    "창업",
]

# §16 판정2: 구체 마커 목록에서 이 포괄어를 제외한 나머지만 "certain"(확실) 판정에 쓴다.
_GENERIC_STARTUP_MARKER = "창업"


def classify_startup_track(announcement, markers=None):
    """
    공고가 "창업 지원" 트랙인지 판정하는 3단계 분류 (§16 판정1·판정2 반영, 2026-07-16).
    markers: business_profiles.yaml의 startup_track_markers 목록. None이면
    STARTUP_TRACK_MARKERS_FALLBACK으로 폴백(하위호환).

    - "certain": program_name에 "창업"을 제외한 구체 마커(예비창업/창업패키지 등, 공식
      트랙 명칭이라 오탐 위험이 낮음)가 포함되거나, max_years_since_founding<=7(업력 상한이
      낮게 걸린 공고는 구조적으로 창업 초기 대상 — 텍스트가 아니라 수치 근거이므로 확실)인 경우.
    - "ambiguous": 구체 마커는 없지만 포괄어 "창업"만 단독으로 포함됨(예: "경력단절여성
      창업케어"처럼 창업 지원 트랙인지 제목만으로 확신할 수 없는 경우 — §16 판정2가 든 예시
      "마커 부분 일치, 제목만으로 판단 불가"에 해당).
    - "none": 위 신호가 전혀 없음.

    TODO(설계 질문, 여전히 미해결): 공고 스키마에 "트랙 유형"을 명시하는 전용 필드가 없어
    여전히 program_name 키워드 기반 휴리스틱이다 — Fable 설계 확정 전까지 잠정치.
    """
    name = announcement.get("program_name", "") or ""
    markers = markers or STARTUP_TRACK_MARKERS_FALLBACK
    specific_markers = [m for m in markers if m != _GENERIC_STARTUP_MARKER]
    if any(m in name for m in specific_markers):
        return "certain"
    elig = announcement.get("eligibility", {}) or {}
    max_y = elig.get("max_years_since_founding")
    if isinstance(max_y, (int, float)) and max_y <= 7:
        return "certain"
    if _GENERIC_STARTUP_MARKER in markers and _GENERIC_STARTUP_MARKER in name:
        return "ambiguous"
    return "none"


def apply_profile_exclusions(profile_entry, business_profile, announcements, startup_track_markers=None):
    """
    business_profiles.yaml의 excluded_types와 founded_date(null=개업 전) 상태를 반영해
    match_programs() 호출 전에 공고 목록을 걸러낸다. 제외된 항목은 excluded_programs와
    동일한 {"program_name", "exclusion_reason"} 형태로 반환해 결과에 제외 사유가 남도록 한다.
    §16 판정2: 창업 트랙 판정이 "certain"일 때만 자동 제외한다. "ambiguous"(포괄어 "창업"만
    단독 일치)면 제외하지 않고 그대로 통과시키되, needs_confirmation에 판별 불확실 사실을
    남겨 사람 검수로 넘긴다 — 거르는 건 사람 검수 게이트의 몫이라는 원칙.
    반환: (filtered_announcements, excluded_entries, needs_confirmation)
    """
    excluded_types = profile_entry.get("excluded_types", []) or []
    exclude_startup = any("창업" in et for et in excluded_types)
    founded_is_null = business_profile.get("founded_date") is None
    markers = startup_track_markers or STARTUP_TRACK_MARKERS_FALLBACK

    filtered = []
    excluded = []
    needs_confirmation = []
    for a in announcements:
        name = a.get("program_name")

        if exclude_startup:
            track_signal = classify_startup_track(a, markers)
            if track_signal == "certain":
                excluded.append({
                    "program_name": name,
                    "exclusion_reason": (
                        f"프로필 excluded_types 규칙에 의해 제외: '{profile_entry.get('display_name')}'는 "
                        "창업 지원 트랙 제외 대상(business_profiles.yaml excluded_types 참고) -> "
                        "이 공고는 창업 트랙으로 확실히 판정됨(classify_startup_track=certain)"
                    ),
                })
                continue
            if track_signal == "ambiguous":
                needs_confirmation.append(
                    f"[{name}] 창업트랙 판별 불확실 — 사람 검수 필요 (프로필 "
                    f"'{profile_entry.get('display_name')}'의 excluded_types 창업 지원 제외 규칙 "
                    "대상인지 제목만으로 확실하지 않음, classify_startup_track=ambiguous -> "
                    "자동 제외하지 않고 그대로 매칭 후보에 남김, §16 판정2)"
                )
                # 제외하지 않고 아래로 통과 -> founded_is_null 체크 및 filtered에 포함.

        if founded_is_null:
            classification = _classify_founding_requirement(a)
            if classification == "post_founding_required":
                excluded.append({
                    "program_name": name,
                    "exclusion_reason": (
                        "예비창업 상태(개업 전, founded_date=null)인 프로필 — 이 공고는 기창업(개업 후) "
                        "요건으로 판정됨(_classify_founding_requirement 휴리스틱, 설계 질문 참고) -> 부적격"
                    ),
                })
                continue
            # classification == "pre_founding_required" -> 제외하지 않고 그대로 통과시킨다.
            # match_programs(apply_founding_classification=True) 경로에서 같은 분류를 다시 계산해
            # check_eligibility_and_disqualification에 hint로 전달, 업력 criterion을 "적격"으로
            # 처리한다(추측 금지: "unclear"는 여기서도 배제하지 않고 기존 확인필요 흐름에 맡김).

        filtered.append(a)

    return filtered, excluded, needs_confirmation


def _load_business_profiles_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("profiles", []) or []


def _load_startup_track_markers(path):
    """§16 판정1: business_profiles.yaml 최상위 startup_track_markers를 로드. 키가 없거나
    로드 실패 시 STARTUP_TRACK_MARKERS_FALLBACK(하위호환)으로 폴백한다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        markers = data.get("startup_track_markers")
        if markers:
            return list(markers)
    except Exception:
        pass
    return list(STARTUP_TRACK_MARKERS_FALLBACK)


def run_for_profile(profile_entry, target_period, ref_date, announcements_path=None, startup_track_markers=None):
    """
    프로필 1건(business_profiles.yaml의 profiles[i])에 대해 기존 파이프라인
    (collect_and_extract_announcements -> apply_profile_exclusions(신규) -> match_programs
    -> draft_application -> judge_mode_self_review -> apply_quality_gate)을 실행한다.
    기존 run()의 단계 구성을 그대로 따르되, business_profile 대신 profile_entry를
    profile_to_business_profile()로 변환해 사용하고 apply_profile_exclusions()를
    match_programs() 앞에 추가로 끼워넣은 것이 유일한 차이다.

    startup_track_markers: §16 판정1 — business_profiles.yaml의 startup_track_markers
    목록(run_multi_profile()이 로드해 전달). None이면 STARTUP_TRACK_MARKERS_FALLBACK 사용.

    match_programs()는 industry_code_verified=False로 호출한다 — business_profiles.yaml의
    industry는 자유서술이라 표준산업분류 코드와 대조 불가하므로(§16 판정3), industry_codes
    불일치를 부적격이 아니라 확인 필요로 처리하기 위함(단일 business_profile 입력 경로인
    run()/match_programs() 기본값(True)에는 영향 없음 — 하위호환 보존).
    """
    business_profile = profile_to_business_profile(profile_entry)
    needs_confirmation = []

    try:
        announcements, nc1 = collect_and_extract_announcements(target_period, announcements_path)
        needs_confirmation += nc1
    except Exception as e:
        log_failure("collect_and_extract_announcements", str(profile_entry)[:500], e)
        raise

    filtered_announcements, profile_excluded, nc0 = apply_profile_exclusions(
        profile_entry, business_profile, announcements, startup_track_markers=startup_track_markers
    )
    needs_confirmation += nc0

    try:
        matched, excluded, nc2 = match_programs(
            business_profile, filtered_announcements, target_period, ref_date,
            apply_founding_classification=True, industry_code_verified=False,
        )
        needs_confirmation += nc2
    except Exception as e:
        log_failure("match_programs", str(profile_entry)[:500], e)
        raise

    excluded = profile_excluded + excluded

    top_match = matched[0] if matched else None

    try:
        draft = draft_application(business_profile, top_match)
    except Exception as e:
        log_failure("draft_application", str(top_match)[:500], e)
        raise

    try:
        judge_review = judge_mode_self_review(draft, top_match, business_profile)
    except Exception as e:
        log_failure("judge_mode_self_review", str(draft)[:500], e)
        raise

    quality_gate_result = apply_quality_gate(matched, judge_review, draft)
    if quality_gate_result["lock_state"] != "READY_FOR_APPROVAL":
        log_failure(
            "quality_gate",
            f"profile={profile_entry.get('id')} program={top_match['program_name'] if top_match else None}",
            f"lock_state=DRAFT (confidence_passed={quality_gate_result['confidence_passed']}, "
            f"judge_pass_recommendation={quality_gate_result['judge_pass_recommendation']})",
            quality_gate_result["overall_confidence"],
        )

    matched_public = [
        {k: v for k, v in m.items() if not k.startswith("_")} for m in matched
    ]
    judge_review_public = {k: v for k, v in judge_review.items() if not k.startswith("_")}

    return {
        "profile_id": profile_entry.get("id"),
        "display_name": profile_entry.get("display_name"),
        "matched_programs": matched_public,
        "excluded_programs": excluded,
        "draft_application": draft,
        "judge_review": judge_review_public,
        "quality_gate_result": quality_gate_result,
        "lock_state": quality_gate_result["lock_state"],
        "needs_confirmation": sorted(set(needs_confirmation)),
        "run_meta": {
            "ref_date": ref_date.isoformat(),
            "target_period": target_period,
        },
    }


def run_multi_profile(profiles_path, announcements_path=None, target_period=None, ref_date=None):
    """
    business_profiles.yaml의 모든 프로필을 순회하며 각각 run_for_profile()을 실행하고
    {profile_id: 결과} 형태로 묶어 반환한다.
    target_period 미지정 시 ref_date로부터 180일 구간을 기본값으로 사용한다(단일 입력
    경로의 target_period는 입력 JSON에서 명시적으로 받는 것과 달리, 다중 프로필 CLI
    실행은 입력 JSON이 없으므로 합리적 기본값이 필요 -> 이 기본값 자체는 새 설계 판단이라기보다
    실행 편의를 위한 값이라 TODO로 표시하지 않음. 다만 정확한 기본 구간 길이는 Fable 확인 대상일
    수 있어 최종 보고 "설계 질문"에 짧게 언급함).
    """
    ref_date = ref_date or today()
    if target_period is None:
        target_period = {
            "start_date": ref_date.isoformat(),
            "end_date": (ref_date + timedelta(days=180)).isoformat(),
        }

    profiles = _load_business_profiles_yaml(profiles_path)
    startup_track_markers = _load_startup_track_markers(profiles_path)
    results = {}
    for profile_entry in profiles:
        pid = profile_entry.get("id")
        results[pid] = run_for_profile(
            profile_entry, target_period, ref_date, announcements_path,
            startup_track_markers=startup_track_markers,
        )
    return results


# =============================================================================
# 뒷단(선정 후): PPT·발표대본·예상Q&A 자동화 (v0.6.1, 2026-07-16)
# 설계 근거: ai공장짓기/decision-log_skill-factory-architecture.md §17,
#            클로드 정부지원사업 ai/설계_뒷단자동화_PPT발표대본QNA.md (Fable 5, 2026-07-16)
# 8 stage: local 2(선정접수/발표패키지저장) / model 4(mock 규칙기반 —
#          발표요건추출/PPT초안생성/발표대본생성/예상QNA생성) / human 2(mock 자동승인 —
#          실제 승인 UI 없음, 방역/꽃집 human 게이트와 동일한 알려진 한계).
# 이 구간은 위 매칭~초안~심사위원 로직(run/run_for_profile 등)과 완전히 분리된
# 별도 진입점이다 — 기존 함수·회귀테스트는 전혀 건드리지 않는다.
# =============================================================================

MAX_PRESENTATION_APPROVAL_RETRIES = 3  # 방역 MAX_APPROVAL_RETRIES와 동일값(임의 — §17 "아직 반영 안 된 것" open question 승계)


def _new_presentation_approval_block(prev_doc=None):
    """방역 scripts/run.py의 _new_approval_block과 동일 패턴 —
    manifest.schema.v2.yaml#check_output_schema.approval_block 그대로 적용."""
    prev_approval = (prev_doc or {}).get("approval") or {}
    history = list(prev_approval.get("version_history") or [])
    if prev_approval.get("status") == "반려":
        history.append({
            "version": prev_approval.get("version"),
            "status": "반려",
            "rejection_reason": prev_approval.get("rejection_reason"),
            "rejection_target": prev_approval.get("rejection_target"),
        })
        new_version = (prev_approval.get("version") or 1) + 1
    else:
        new_version = prev_approval.get("version") or 1
    return {
        "status": "초안",
        "version": new_version,
        "approved_by": None,
        "approved_at": None,
        "rejection_reason": None,
        "rejection_target": None,
        "version_history": history,
    }


def stage_선정접수(selection_input):
    """kind: local. 선정 통보 원문 + 제출확정본 참조를 구조화해 받는다 — AI 판단 없음.
    §17 1절 전제: 콘텐츠 원천은 draft_application(초안)이 아니라 사람이 실제 제출한
    확정본(submitted_application_ref)이어야 함 — 없으면 추측하지 않고 즉시 중단."""
    notice = selection_input.get("selection_notice") or {}
    submitted_ref = selection_input.get("submitted_application_ref")
    if not submitted_ref:
        raise ValueError(
            "선정접수 실패: submitted_application_ref(사람이 지정하는 실제 제출확정본 경로)가 없음 — 추측으로 채우지 않음"
        )
    return {"selection_notice": notice, "submitted_application_ref": submitted_ref}


def stage_발표요건추출(ctx, announcement=None):
    """kind: model, tier: low_cost. 통보문+정본 공고에서 발표요건을 추출한다.
    원문에 없는 값은 [확인 필요]로 비워둔다 — 추측 금지 원칙 승계."""
    notice = ctx.get("selection_notice") or {}
    ann = announcement or {}
    return {
        "발표평가_존재": notice.get("has_presentation", "[확인 필요]"),
        "발표시간_분": notice.get("presentation_minutes") or ann.get("presentation_minutes") or "[확인 필요]",
        "슬라이드_제한": notice.get("slide_limit") or "[확인 필요]",
        "질의응답_시간_분": notice.get("qna_minutes") or "[확인 필요]",
        "발표평가_배점표": ann.get("scoring_rubric_note") or notice.get("scoring_rubric_note") or "[확인 필요]",
    }


def evaluate_presentation_run_if(requirements):
    """run_if: 발표평가_또는_발표자료가_요구됨.
    모름=발표없음으로 낙관 처리하지 않는다 — [확인 필요]뿐이면 스킵하지 않고 계속 진행,
    사람이 확인하게 한다(§17 "아직 반영 안 된 것" 원칙)."""
    val = requirements.get("발표평가_존재")
    if val == "[확인 필요]":
        return True, "발표평가 여부 불확실 — 모름=발표없음으로 임의 처리하지 않고 사람 확인 필요, stage 계속 진행"
    if val:
        return True, "발표평가 존재 확인됨"
    return False, "발표평가 없음(서류만으로 선정) — stage 3~8 스킵"


def stage_ppt초안생성(ctx):
    """kind: model, tier: mid. 제출확정본+발표 배점표 -> 슬라이드 아웃라인.
    known limitation: 실 LLM 미연동 — 규칙기반 목업(섹션 제목만 구조화, 본문은 자리표시)."""
    req = ctx.get("presentation_requirements") or {}
    outline = [
        {"slide": 1, "title": "사업 개요", "content": "[목업] submitted_application_ref 참조 요약 필요 — 실 LLM 미연동"},
        {"slide": 2, "title": "문제 정의 및 필요성", "content": "[목업]"},
        {"slide": 3, "title": "실행 계획", "content": "[목업]"},
        {"slide": 4, "title": "예산 계획", "content": "[목업]"},
        {"slide": 5, "title": "기대 효과", "content": "[목업]"},
    ]
    return {
        "outline": outline,
        "slide_limit_note": req.get("슬라이드_제한"),
        "approval_required": True,
        "approval": _new_presentation_approval_block(ctx.get("ppt_draft")),
        "locked": False,
    }


def stage_ppt승인(ctx, mock_decision="승인"):
    """kind: human. mock — 실제 승인 UI 없음(꽃집/방역과 동일 알려진 한계).
    mock_decision: "승인" 또는 "반려:<사유>" (테스트용 반려 시나리오 주입)."""
    doc = ctx.get("ppt_draft") or {}
    approval = doc.setdefault("approval", {})
    if mock_decision.startswith("반려"):
        reason = mock_decision.split(":", 1)[1] if ":" in mock_decision else "내용 오류"
        approval.update({
            "status": "반려", "rejection_reason": f"[테스트모드 mock] {reason}",
            "rejection_target": "PPT문제", "approved_by": None, "approved_at": None,
        })
        doc["locked"] = False
    else:
        approval.update({
            "status": "승인완료", "approved_by": "[테스트모드 mock] 대표자",
            "approved_at": ctx.get("_ref_datetime"), "rejection_reason": None, "rejection_target": None,
        })
        doc["locked"] = True
    return doc


def stage_발표대본생성(ctx):
    """kind: model, tier: mid. depends_on: PPT승인(초안생성이 아님) — §17 판정2.
    PPT가 승인·잠금되기 전에는 절대 실행하지 않는다(반려 전파 차단)."""
    ppt = ctx.get("ppt_draft") or {}
    if not ppt.get("locked"):
        raise RuntimeError("발표대본생성 실패: PPT가 아직 승인·잠금되지 않음 — depends_on 위반(§17 판정2)")
    req = ctx.get("presentation_requirements") or {}
    script_lines = [
        f"[{s['slide']}번 슬라이드: {s['title']}] [목업] 발표시간 {req.get('발표시간_분', '[확인 필요]')}분 배분 — 실 LLM 미연동"
        for s in ppt.get("outline", [])
    ]
    return {
        "script_lines": script_lines,
        "approval_required": True,
        "approval": _new_presentation_approval_block(ctx.get("presentation_script")),
        "locked": False,
    }


def stage_예상qna생성(ctx, judge_review=None):
    """kind: model, tier: high. 8인심사위원/감점전파/확인필요 목록을 질문 소재로
    재사용한다 — 새 판정 로직을 만들지 않는다(§17 판정4). 적대적 심사위원 시뮬레이션."""
    jr = judge_review or {}
    weak_points = []
    weak_points += (jr.get("judge_panel_review", {}) or {}).get("immediate_warnings", []) or []
    weak_points += jr.get("exaggeration_flags", []) or []
    weak_points += [f"{k} 확인 필요" for k in (ctx.get("needs_confirmation") or [])]
    if not weak_points:
        weak_points = ["[확인 필요 목록 없음 — 일반 질문만 생성]"]
    qna = [
        {"question": f"[목업] '{wp}'에 대해 어떻게 대응하시겠습니까?", "answer": "[목업] 실 LLM 미연동 — 답변 초안 생성 안 됨"}
        for wp in weak_points
    ]
    return {
        "qna": qna,
        "approval_required": True,
        "approval": _new_presentation_approval_block(ctx.get("expected_qna")),
        "locked": False,
    }


def stage_발표패키지승인(ctx, script_decision="승인", qna_decision="승인"):
    """kind: human. 대본+Q&A 일괄 게이트, 문서별 approval은 독립(부분 반려 가능) — §17 판정3."""
    results = {}
    for key, decision in (("presentation_script", script_decision), ("expected_qna", qna_decision)):
        doc = ctx.get(key) or {}
        approval = doc.setdefault("approval", {})
        if decision.startswith("반려"):
            reason = decision.split(":", 1)[1] if ":" in decision else "내용 오류"
            target = "대본문제" if key == "presentation_script" else "질문답변문제"
            approval.update({
                "status": "반려", "rejection_reason": f"[테스트모드 mock] {reason}",
                "rejection_target": target, "approved_by": None, "approved_at": None,
            })
            doc["locked"] = False
        else:
            approval.update({
                "status": "승인완료", "approved_by": "[테스트모드 mock] 대표자",
                "approved_at": ctx.get("_ref_datetime"), "rejection_reason": None, "rejection_target": None,
            })
            doc["locked"] = True
        results[key] = approval["status"]
    return results


def _pending_presentation_rejections(ctx):
    rej = {}
    for key in ("ppt_draft", "presentation_script", "expected_qna"):
        approval = (ctx.get(key) or {}).get("approval") or {}
        if approval.get("status") == "반려":
            rej[key] = approval.get("rejection_target")
    return rej


def stage_발표패키지저장(ctx):
    """kind: local. 저장 직전 3종 문서 전부 승인완료인지 강제 재검증 —
    방역 문자장부봇의 이중 검증 패턴 그대로(§17 판정1/헌장 적용). 아니면 절대 저장하지 않는다.
    이 파이프라인은 저장까지만 수행 — 실제 발표 현장 사용/제출은 반드시 사람(헌장 §3)."""
    docs = {
        "ppt_draft": ctx.get("ppt_draft") or {},
        "presentation_script": ctx.get("presentation_script") or {},
        "expected_qna": ctx.get("expected_qna") or {},
    }
    blocked = [k for k, d in docs.items() if d.get("approval_required") and (d.get("approval") or {}).get("status") != "승인완료"]
    if blocked:
        raise RuntimeError(f"[안전장치 발동 - 저장 차단] 승인완료 안 된 문서 저장 시도: {blocked}")
    return {
        "saved_at": ctx.get("_ref_datetime"),
        "versions": {k: (d.get("approval") or {}).get("version") for k, d in docs.items()},
        "note": "저장까지만 수행 — 실제 발표 현장 사용/제출은 반드시 사람(헌장 §3 절대 자동화 금지)",
    }


def run_presentation_backend(selection_input, announcement=None, judge_review=None,
                              mock_decisions=None, ref_datetime="2026-07-16T00:00:00"):
    """
    정부지원 뒷단(선정 후 PPT·발표대본·예상Q&A) 8 stage 오케스트레이터.
    mock — 실 LLM/승인 UI 미연동(known limitation, §17 참고). 기존 run()/run_for_profile()과
    완전히 분리된 별도 진입점 — 매칭~초안~심사위원 로직은 전혀 건드리지 않는다.

    mock_decisions: {"ppt": "승인"|"반려:사유", "script": ..., "qna": ...} — 테스트용 반려
    시나리오 주입. script/qna 반려는 첫 시도에서만 적용되고(mock 단순화), 재작업 후에는
    자동 승인된다 — 실제 운영에서는 매 시도마다 사람이 다시 판단한다.
    """
    mock_decisions = mock_decisions or {}
    ctx = {"_ref_datetime": ref_datetime}
    trace = []

    ctx.update(stage_선정접수(selection_input))
    trace.append("선정접수")

    ctx["presentation_requirements"] = stage_발표요건추출(ctx, announcement=announcement)
    trace.append("발표요건추출")

    should_run, reason = evaluate_presentation_run_if(ctx["presentation_requirements"])
    if not should_run:
        return {"skipped": True, "reason": reason, "trace": trace, "ctx": ctx}

    # --- 게이트① PPT ---
    for attempt in range(1, MAX_PRESENTATION_APPROVAL_RETRIES + 2):
        ctx["ppt_draft"] = stage_ppt초안생성(ctx)
        ctx["ppt_draft"] = stage_ppt승인(ctx, mock_decision=mock_decisions.get("ppt", "승인") if attempt == 1 else "승인")
        trace.append(f"PPT초안생성+PPT승인(attempt {attempt}) -> {ctx['ppt_draft']['approval']['status']}")
        if ctx["ppt_draft"]["approval"]["status"] == "승인완료":
            break
        if attempt > MAX_PRESENTATION_APPROVAL_RETRIES:
            return {"halted": True, "reason": "PPT 반려 재시도 한도 초과(mock 한계)", "trace": trace, "ctx": ctx}

    # --- 대본/Q&A 생성 + 게이트② (부분 반려 지원) ---
    ctx["presentation_script"] = stage_발표대본생성(ctx)
    ctx["expected_qna"] = stage_예상qna생성(ctx, judge_review=judge_review)
    trace.append("발표대본생성+예상QNA생성")

    for attempt in range(1, MAX_PRESENTATION_APPROVAL_RETRIES + 2):
        gate2 = stage_발표패키지승인(
            ctx,
            script_decision=mock_decisions.get("script", "승인") if attempt == 1 else "승인",
            qna_decision=mock_decisions.get("qna", "승인") if attempt == 1 else "승인",
        )
        trace.append(f"발표패키지승인(attempt {attempt}) -> {gate2}")
        rejections = _pending_presentation_rejections(ctx)
        if not rejections:
            break
        if attempt > MAX_PRESENTATION_APPROVAL_RETRIES:
            return {"halted": True, "reason": f"발표패키지 반려 재시도 한도 초과(mock 한계): {rejections}", "trace": trace, "ctx": ctx}
        if rejections.get("presentation_script") == "대본문제":
            ctx["presentation_script"] = stage_발표대본생성(ctx)
            trace.append(f"발표대본생성 재작업(attempt {attempt + 1})")
        if rejections.get("expected_qna") == "질문답변문제":
            ctx["expected_qna"] = stage_예상qna생성(ctx, judge_review=judge_review)
            trace.append(f"예상QNA생성 재작업(attempt {attempt + 1})")

    ctx["presentation_package_record"] = stage_발표패키지저장(ctx)
    trace.append("발표패키지저장")
    return {"halted": False, "trace": trace, "ctx": ctx}


def main():
    # 사용법(기존, 하위호환 그대로 보존): python3 run.py [input.json] [announcements.json]
    #   announcements.json 생략 시 scripts/sample_announcements.json(목업) 사용.
    # 사용법(v0.6.0 신규): python3 run.py --profiles <business_profiles.yaml> [announcements.json]
    #   3개 프로필을 순회 매칭하고 test/multi_profile_output_YYYY-MM-DD.json에 저장.
    if len(sys.argv) > 1 and sys.argv[1] == "--backend":
        # 사용법(v0.6.1 신규): python3 run.py --backend <selection_input.json> [mock_decisions.json]
        #   선정 후 뒷단(PPT·발표대본·예상Q&A) 8 stage 실행. test/backend_result_<timestamp>.json에 저장.
        if len(sys.argv) < 3:
            print("사용법: python3 run.py --backend <selection_input.json> [mock_decisions.json]", file=sys.stderr)
            sys.exit(1)
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            selection_input = json.load(f)
        mock_decisions = None
        if len(sys.argv) > 3:
            with open(sys.argv[3], "r", encoding="utf-8") as f:
                mock_decisions = json.load(f)
        result = run_presentation_backend(selection_input, mock_decisions=mock_decisions)
        out_path = ROOT_DIR / "test" / f"backend_result_{today().isoformat()}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n[저장됨] {out_path}", file=sys.stderr)
        return result

    if len(sys.argv) > 1 and sys.argv[1] == "--profiles":
        if len(sys.argv) < 3:
            print("사용법: python3 run.py --profiles <business_profiles.yaml> [announcements.json]", file=sys.stderr)
            sys.exit(1)
        profiles_path = Path(sys.argv[2])
        announcements_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

        ref_date = today()
        results = run_multi_profile(profiles_path, announcements_path=announcements_path, ref_date=ref_date)

        out_path = ROOT_DIR / "test" / f"multi_profile_output_{ref_date.isoformat()}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"\n[저장됨] {out_path}", file=sys.stderr)
        return results

    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = ROOT_DIR / "test" / "sample_input.json"

    announcements_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    result = run(input_data, announcements_path=announcements_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
