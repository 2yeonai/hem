#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/collector/promote_candidates.py

raw 계층(announcements_raw_YYYY-MM-DD.json) -> candidate 계층
(candidates_YYYY-MM-DD.json) 승격기. 3계층 io_contract(T7 설계 §14 Q4, §15)의
가운데 단계다.

설계 근거 문서 (신규 판단 없음): 1. Projects/ai공장짓기/decision-log_skill-factory-architecture.md §14, §15
프로필 정본: scripts/business_profiles.yaml
candidate 스키마의 본문 필드 이름은 scripts/real_announcements.json(정본)과 동일하게 맞춤.

=== 이 스크립트가 하는 일 (그리고 하지 않는 일) ===
- raw 카드의 제목을 business_profiles.yaml의 3개 프로필 각각의
  scraping_keywords와 대조해 1개 이상 매칭되면 그 프로필 id를
  matched_profiles[]에 태그하고 candidate로 승격한다.
- excluded_types를 지킨다: 온천꽃식물원·대륙창업은 "기창업" 사업이므로
  창업 트랙 공고에는 절대 매칭시키지 않는다(§15 표 참고). 모온은 반대로
  예비창업 트랙이 최우선이라 창업 트랙 배제 대상이 아니다.
- eligibility/exclusion_conditions/required_documents/submission_format/
  budget_criteria/scoring_rubric 등 "본문(공고문/첨부 HWP)을 읽어야만 알 수
  있는 필드"는 **채우지 않는다.** null로 두고 unresolved[]에 필드명을
  명시한다 — 여기서 실제 LLM 추출을 하는 게 아니라 구조만 만드는 단계다
  (§14 Q4: "실제 LLM 추출은 후속 단계, 지금은 구조만").
- 마감 지난 공고는 collect_bizinfo.py에서 이미 걸러지는 게 정상 흐름이지만,
  이 스크립트는 raw 파일을 독립적으로도 받을 수 있으므로(재실행/과거 raw
  재처리 등) **여기서도 한 번 더 방어적으로 deadline을 재확인**한다 — 회사
  헌장의 "미승인 발송 차단을 발송 단계 자체에서 재확인" 패턴과 동일한 이유:
  파이프라인 순서만 믿지 않는다.

=== 창업 트랙 판별 (§16 판정1·판정2 반영, 2026-07-16) ===
어떤 공고 제목이 "창업 트랙"인지 판별하는 마커 목록은 이제
scripts/business_profiles.yaml의 최상위 `startup_track_markers:`가 정본이다
(run.py의 _classify_startup_track_announcement()도 같은 목록을 로드한다 —
§16 판정1: 두 곳에 따로 있던 목록을 합집합으로 단일 정본화). yaml에 이 키가
없거나 로드 실패 시에는 STARTUP_TRACK_MARKERS_FALLBACK(기존 하드코딩 값,
이 목록도 이제 promote_candidates.py 쪽 9개 + run.py 쪽 "창업" 포괄어까지
합친 합집합)으로 폴백한다 — 하위호환.

판별은 2단계다(§16 판정2: 자동 "제외"는 확실할 때만, 애매하면 candidate에
남기고 사람 검수로 넘긴다):
- "certain": 제목에 "창업"을 제외한 구체 마커(예비창업/창업패키지 등, 공식
  사업 트랙 명칭이라 오탐 위험이 낮음)가 하나라도 포함됨 -> excluded_types에
  창업 트랙 제외가 걸린 프로필은 이 매칭에서 확실히 제외한다.
- "ambiguous": 구체 마커는 없지만 포괄어 "창업"만 단독으로 포함됨(예:
  "경력단절여성 창업케어"처럼 창업 지원사업인지 확신할 수 없는 제목 —
  §16 판정2가 든 예시 "마커 부분 일치, 제목만으로 판단 불가"에 해당) ->
  자동 제외하지 않고 candidate에 남기되, unresolved에 "창업트랙 판별
  불확실 — 사람 검수 필요"를 추가해 사람 검수 게이트로 넘긴다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from typing import Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "[ERROR] PyYAML이 필요합니다. pip install --break-system-packages pyyaml",
        file=sys.stderr,
    )
    raise

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)  # .../scripts
INBOX_DIR = os.path.join(SCRIPTS_DIR, "inbox")
BUSINESS_PROFILES_PATH = os.path.join(SCRIPTS_DIR, "business_profiles.yaml")

# real_announcements.json 정본과 동일한 "본문 해석 필요" 필드 목록.
# candidate 카드에서는 전부 null로 두고 unresolved[]에 이름을 남긴다.
BODY_DERIVED_FIELDS = [
    "eligibility",
    "exclusion_conditions",
    "required_documents",
    "required_documents_note",
    "submission_format",
    "budget_criteria",
    "scoring_rubric",
    "scoring_rubric_note",
]

# §16 판정1 폴백값: business_profiles.yaml의 startup_track_markers를 로드하지 못할 때만 쓴다.
# run.py 쪽 옛 목록("창업" 포괄어 포함)과의 합집합 — yaml이 정본이고 이 상수는 하위호환용.
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
# "창업"이 단독으로 일치하면 "ambiguous"(애매) — 자동 제외하지 않고 사람 검수로 넘긴다.
_GENERIC_STARTUP_MARKER = "창업"


# --------------------------------------------------------------------------
# 프로필 로딩
# --------------------------------------------------------------------------


def load_profiles(path: str = BUSINESS_PROFILES_PATH) -> tuple:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    profiles = data.get("profiles", [])
    rules = data.get("collector_rules", {})
    markers = data.get("startup_track_markers") or list(STARTUP_TRACK_MARKERS_FALLBACK)
    return profiles, rules, markers


def _keyword_core(keyword: str) -> str:
    """'농업 (화훼 생산·유통 연계)' -> '농업' 처럼 괄호 주석 제거한 핵심 토큰."""
    core = re.split(r"[（(]", keyword, maxsplit=1)[0].strip()
    return core


def classify_startup_track(title: str, markers: list) -> str:
    """
    §16 판정2: 창업 트랙 판별을 "certain"/"ambiguous"/"none" 3단계로 분류.
    - certain: 포괄어 "창업"을 뺀 구체 마커(예비창업/창업패키지 등)가 제목에 포함됨.
    - ambiguous: 구체 마커는 없지만 포괄어 "창업"만 단독으로 제목에 포함됨(마커 부분
      일치/제목만으로 판단 불가 사례 — 예: "경력단절여성 창업케어").
    - none: "창업" 관련 신호 자체가 없음.
    """
    text = title or ""
    markers = markers or STARTUP_TRACK_MARKERS_FALLBACK
    specific_markers = [m for m in markers if m != _GENERIC_STARTUP_MARKER]
    if any(m in text for m in specific_markers):
        return "certain"
    if _GENERIC_STARTUP_MARKER in markers and _GENERIC_STARTUP_MARKER in text:
        return "ambiguous"
    return "none"


def profile_excludes_startup(profile: dict) -> bool:
    excluded_types = profile.get("excluded_types") or []
    return any("창업" in str(x) for x in excluded_types)


def match_profiles_for_card(title: str, profiles: list, min_keyword_match: int, markers: list = None) -> tuple:
    """
    반환: (matched_profile_ids, match_detail, track_ambiguous)
    match_detail: {profile_id: [매칭된 키워드 리스트]} — 디버깅/검수용.
    track_ambiguous: bool — §16 판정2에 따라, 창업트랙 제외 대상 프로필에서 "ambiguous"
    판정 때문에 자동 제외하지 않고 그대로 매칭시킨 경우 True(호출측이 unresolved에 반영).
    """
    text = title or ""
    track_signal = classify_startup_track(text, markers)
    matched = []
    detail = {}
    track_ambiguous = False

    for profile in profiles:
        pid = profile.get("id")
        if not pid:
            continue

        excludes_startup = profile_excludes_startup(profile)
        if excludes_startup and track_signal == "certain":
            # 확실한 창업 트랙 판정 + excluded_types 강제 — 키워드가 우연히 걸려도 승격시키지 않는다.
            continue

        keywords = profile.get("scraping_keywords") or []
        hits = []
        for kw in keywords:
            core = _keyword_core(kw)
            if core and core in text:
                hits.append(kw)
        if len(hits) >= min_keyword_match:
            matched.append(pid)
            detail[pid] = hits
            if excludes_startup and track_signal == "ambiguous":
                # 판정2: 애매하면 제외 금지 — 매칭은 유지하되 사람 검수가 필요함을 표시.
                track_ambiguous = True

    return matched, detail, track_ambiguous


# --------------------------------------------------------------------------
# raw -> candidate 변환
# --------------------------------------------------------------------------


def _is_deadline_passed(deadline: Optional[str], today: date) -> bool:
    if not deadline:
        return False  # 마감일 미상은 보수적으로 살려둔다 (버리지 않음)
    try:
        return date.fromisoformat(deadline) < today
    except ValueError:
        return False


def build_candidate_card(raw_card: dict, matched_profile_ids: list, match_detail: dict, track_ambiguous: bool = False) -> dict:
    now_iso = datetime.now().isoformat(timespec="seconds")
    card = {
        "program_name": raw_card.get("title"),
        "agency": raw_card.get("agency"),
        "source_url": raw_card.get("url"),
        "source_note": (
            "[자동수집-미검수] bizinfo.go.kr에서 기계 수집된 raw 필드만으로 구성된 "
            "candidate 카드. 본문(공고문/첨부 HWP)을 읽지 않았으므로 eligibility 등은 "
            "전부 null. 사람 검수 후 real_announcements.json으로 병합되기 전까지는 "
            "정본으로 취급하지 말 것."
        ),
        "announcement_date": raw_card.get("announcement_date"),
        "deadline": raw_card.get("deadline"),
        "pblancId": raw_card.get("pblancId"),
        "attachment_links": raw_card.get("attachment_links") or [],
        "matched_profiles": matched_profile_ids,
        "match_detail": match_detail,  # 프로필별 매칭 키워드 — 검수 편의용 부가정보
        "collected_at": raw_card.get("collected_at") or now_iso,
        "promoted_at": now_iso,
        # 실제 LLM 추출 전이라 신뢰도 산정 불가 — TODO: 후속 단계(Haiku/Sonnet
        # 본문 추출) 구현 시 실제 점수로 대체.
        "extraction_confidence": None,
        # §18 판정1(decision-log_skill-factory-architecture.md, 2026-07-16): 사람 검수 게이트
        # 표시 필드. run.py의 collect_and_extract_announcements()는 reviewed가 정확히 True인
        # 카드만 읽는다 — 기본값 False로 생성해, 검수 전에는 절대 매칭 파이프라인에 들어가지
        # 않는다(검수 UI는 범위 밖, 사람이 이 파일을 직접 편집해 true로 바꾸는 최소 구현).
        "reviewed": False,
        "reviewed_by": None,
        "reviewed_at": None,
    }
    for field in BODY_DERIVED_FIELDS:
        card[field] = None
    unresolved = list(BODY_DERIVED_FIELDS) + ["extraction_confidence"]
    if track_ambiguous:
        # §16 판정2: 자동 제외하지 않고 candidate에 남긴 대신, 사람 검수가 필요함을 명시.
        unresolved.append("창업트랙 판별 불확실 — 사람 검수 필요")
    card["unresolved"] = unresolved
    return card


def promote(raw_cards: list, profiles: list, rules: dict, today: date, markers: list = None, log=print) -> tuple:
    min_keyword_match = rules.get("min_keyword_match", 1)
    candidates = []
    skipped_expired = 0
    skipped_no_match = 0
    per_profile_counts = {p.get("id"): 0 for p in profiles if p.get("id")}

    for raw_card in raw_cards:
        deadline = raw_card.get("deadline")
        if rules.get("deadline_filter", True) is not False and _is_deadline_passed(deadline, today):
            skipped_expired += 1
            continue

        matched_ids, detail, track_ambiguous = match_profiles_for_card(
            raw_card.get("title", ""), profiles, min_keyword_match, markers
        )
        if not matched_ids:
            skipped_no_match += 1
            continue

        candidate = build_candidate_card(raw_card, matched_ids, detail, track_ambiguous)
        candidates.append(candidate)
        for pid in matched_ids:
            per_profile_counts[pid] = per_profile_counts.get(pid, 0) + 1

    log(
        f"[INFO] raw {len(raw_cards)}건 -> candidate {len(candidates)}건 "
        f"(마감지남 제외 {skipped_expired}건, 매칭없음 제외 {skipped_no_match}건)"
    )
    for pid, cnt in per_profile_counts.items():
        log(f"[INFO]   - {pid}: {cnt}건")

    return candidates, per_profile_counts


# --------------------------------------------------------------------------
# 입출력
# --------------------------------------------------------------------------


def load_raw_file(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("announcements", [])
    if isinstance(data, list):
        return data
    raise ValueError(f"알 수 없는 raw 파일 형식: {path}")


def write_candidates_file(candidates: list, date_str: str, inbox_dir: str, per_profile_counts: dict) -> str:
    os.makedirs(inbox_dir, exist_ok=True)
    out_path = os.path.join(inbox_dir, f"candidates_{date_str}.json")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "schema_note": (
            "candidate 계층 — real_announcements.json과 동일한 필드명 사용, "
            "본문 해석 필드는 전부 null(unresolved[] 참고). 사람 검수 게이트를 "
            "통과해야 정본(real_announcements.json)으로 병합됨(§14 Q4)."
        ),
        "count": len(candidates),
        "per_profile_counts": per_profile_counts,
        "candidates": candidates,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def run(raw_path: str, date_str: Optional[str] = None, inbox_dir: str = INBOX_DIR, log=print) -> int:
    today = date.today() if not date_str else date.fromisoformat(date_str)
    date_str = today.isoformat()

    raw_cards = load_raw_file(raw_path)
    profiles, rules, markers = load_profiles()

    candidates, per_profile_counts = promote(raw_cards, profiles, rules, today, markers=markers, log=log)

    out_path = write_candidates_file(candidates, date_str, inbox_dir, per_profile_counts)
    log(f"[INFO] candidate 출력 작성: {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="raw -> candidate 승격기")
    parser.add_argument("raw_path", help="announcements_raw_YYYY-MM-DD.json 경로")
    parser.add_argument(
        "--date", dest="date_str", default=None, help="출력 파일명에 쓸 날짜 (기본값=오늘)"
    )
    parser.add_argument(
        "--inbox-dir", dest="inbox_dir", default=INBOX_DIR, help="출력 폴더 (기본값=scripts/inbox)"
    )
    args = parser.parse_args()
    return run(args.raw_path, date_str=args.date_str, inbox_dir=args.inbox_dir)


if __name__ == "__main__":
    sys.exit(main())
