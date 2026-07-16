#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/collector/collect_bizinfo.py

기업마당(bizinfo.go.kr) 공고 수집기 — 3계층 io_contract(T7 설계 §14 Q4)의
"raw 계층"만 담당한다. 여기서 만드는 파일은 real_announcements.json(정본)을
절대 직접 건드리지 않는다 — 사람이 아직 안 읽은, "기계적으로 확실한 필드만"
있는 1차 수집 결과다.

설계 근거 문서 (신규 판단 없음, 전부 이 문서 그대로 구현):
  1. Projects/ai공장짓기/decision-log_skill-factory-architecture.md §14, §15

=== ① bizinfo Open API 확인 결과 (2026-07-16, Sonnet 구현 세션) ===
공공데이터포털(data.go.kr)에 등록된 "중소벤처기업부_중소기업지원사업목록"
  https://www.data.go.kr/data/3034791/fileData.do
의 메타 설명에 실제 데이터 출처가 기업마당 자체라고 명시되어 있고, 기업마당은
별도로 Open API를 직접 제공한다:
  - API 소개/신청 페이지: https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi
  - API 엔드포인트: https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do (GET, JSON/XML)
  - 인증키(crtfcKey) 발급: 기업마당 사이트에서 "IP 등록" 또는 "URL 등록" 중 하나를
    선택해 발급 신청 → 담당자 승인 후 이메일로 키 통보 (사람이 할 일 — 최종 보고
    ④ 참고, 이 스크립트는 발급된 키를 "받아서 쓰는" 역할만 한다)
  - data.go.kr 메타 설명에 명시된 구성요소: 분야/사업명/신청시작일자/신청종료일자/
    소관기관/수행기관/접수기관/등록일자/상세URL

**주의 (TODO — 운영 투입 전 필수 확인)**: 샌드박스 환경의 아웃바운드 HTTPS가
막혀 있어(프록시 403) 이 세션에서는 실제 crtfcKey로 라이브 호출을 해보지
못했다. 아래 FIELD_MAP의 키 이름(pblancId/pblancNm/jrsdInsttNm/reqstBeginEndDe 등)은
  - 기업마당 상세페이지 URL 패턴 확인분: https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/view.do?pblancId=PBLN_000000000097212
  - data.go.kr 메타 설명의 "구성요소" 목록
  - 공개된 기업마당 API 연동 예시(제3자 MCP 서버 구현체)에서 pblancId/pblancNm/
    jrsdInsttNm/reqstBeginEndDe/hashtags/jsonArray/pageUnit/pageIndex 필드명 확인
을 근거로 역산/교차확인한 것이라 신뢰도가 높지만, **실물 API 응답 1건을 받아
FIELD_MAP을 재검증하기 전까지는 100% 확정이 아니다.** API 자체가 없는 게
아니라 "있는 걸 확인했지만 스키마 실물 검증을 못 한" 상태이므로, 지시("API가
없거나 확인 불가면 파싱")의 "확인 불가" 케이스에 해당한다고 보고 아래에
파싱 폴백(scrape_list_page_fallback)도 함께 구현해 두었다. 폴백도 마찬가지로
실제 목록 페이지 HTML을 이 세션에서 받아보지 못해 CSS 선택자/정규식은
추정치다 — 운영 투입 전 사람이 한 번 실행해서 확인 필요.

=== ② 파이프라인 순서 ===
  1. fetch (API 우선, 실패/미확정 시 폴백 파싱) → 원본 레코드 리스트
  2. 원본 레코드 → RAW_SCHEMA로 정규화 (title/agency/url/pblancId/
     announcement_date/deadline/attachment_links)
  3. 마감 지난 공고 필터링 (deadline < 오늘)
  4. pblancId 중복 필터링 (scripts/inbox/의 기존 announcements_raw_*.json에서
     이미 수집된 pblancId는 재수집하지 않음)
  5. 체크섬 게이트: 살아남은 레코드 집합의 해시를 .last_checksum과 비교.
     동일하면 출력 파일은 쓰되(감사 목적) exit code 10으로 "후속 단계
     (promote_candidates.py) 스킵" 신호를 보낸다. — 실제 스킵 배선(예: run.py나
     스케줄러가 이 exit code를 보고 promote_candidates.py 호출을 건너뛰는 것)은
     TODO: 이 수집기 단독으로는 자기 자신을 스킵할 뿐, 상위 오케스트레이터가
     아직 없음 (§14 "다음 액션"에 명시된 별도 항목).

=== ③ 재시도 정책 (§14 Q3 그대로) ===
  - 일시 장애(네트워크 예외/타임아웃/HTTP 5xx): 당일 3회 재시도
    (5분→15분→45분 백오프). 그래도 실패하면 그날은 포기 (exit code 1).
    테스트 시 COLLECTOR_TEST_FAST_RETRY=1 환경변수를 주면 백오프 단위가
    분 대신 초로 축소된다(5→15→45 "초").
  - 구조 변경 의심(응답은 정상 200인데 파싱 결과 0건): 재시도 무의미하므로
    즉시 종료 (exit code 2). TODO: 사람 알림 채널 배선 — 기존 HANDOFF.md/
    일일 세션로그 체계에 맞춰 추후 연결 (notify_human_structure_change() 참고).
  - 3일 연속 일시장애 실패 시에만 사람 알림 — TODO: 이 스크립트는 단발 실행
    기준이라 "N일 연속" 상태를 알려면 실행 이력을 어딘가 누적해야 한다.
    exit code 1이 3일 연속 발생했는지는 상위 스케줄러/run.py가 판단해야 하며,
    이 스크립트는 오늘 실행 결과(성공/일시실패/구조의심)만 정직하게 반환한다.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Optional

# --------------------------------------------------------------------------
# 상수 / 설정
# --------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)          # .../scripts
INBOX_DIR = os.path.join(SCRIPTS_DIR, "inbox")
CHECKSUM_FILE = os.path.join(INBOX_DIR, ".last_checksum")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.yaml")  # 선택적, 사람이 만들 파일

API_ENDPOINT = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
API_KEY_ENV = "BIZINFO_API_KEY"

# TODO(검증필요): 실제 상세페이지 URL 패턴. data.go.kr 메타설명 + 검색으로 확인된
# 목록/상세 경로. pblancId 포맷 예시: PBLN_000000000097212
DETAIL_URL_TEMPLATE = (
    "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/view.do?pblancId={pblancId}"
)
LIST_PAGE_URL = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

# TODO(검증필요): 실물 API 응답을 받기 전까지 확정 아님. 여러 후보 키 이름을
# 순서대로 시도해서, 있는 것을 채택한다(방어적 파싱). 첫 실물 응답 확보 후
# 이 리스트를 정리(불필요 후보 제거)할 것.
FIELD_MAP = {
    "title": ["pblancNm", "bsnsSumryNm", "title"],
    "agency": ["jrsdInsttNm", "excInsttNm", "reqstInsttNm", "agency"],
    "pblancId": ["pblancId", "pblancld", "id"],
    "url": ["pblancUrl", "detailUrl", "url"],
    # 신청시작~종료일자가 하나의 문자열("YYYYMMDD ~ YYYYMMDD")로 오는 경우와
    # 분리된 필드로 오는 경우 둘 다 방어적으로 처리한다.
    "reqst_period_combined": ["reqstBeginEndDe"],
    "reqst_begin": ["reqstBeginDe", "pblancBeginDe"],
    "reqst_end": ["reqstEndDe", "pblancEndDe", "reqstCloseDe"],
    "announcement_date": ["creatPnttm", "regDt", "pblancRegDt"],
    # 첨부파일은 배열/단일필드 등 형태가 불확실 — 여러 후보를 다 모은다.
    "attachment_links": ["flpthNm", "printFlpthNm", "atchFileUrl", "fileList"],
}

RAW_SCHEMA_FIELDS = [
    "title",
    "agency",
    "url",
    "pblancId",
    "announcement_date",
    "deadline",
    "attachment_links",
]

# 재시도 백오프 (초 단위). 기본 5/15/45분. 테스트 시 COLLECTOR_TEST_FAST_RETRY=1
# 이면 5/15/45 "초"로 축소.
_FAST_RETRY = os.environ.get("COLLECTOR_TEST_FAST_RETRY") == "1"
RETRY_BACKOFF_SECONDS = [5, 15, 45] if _FAST_RETRY else [5 * 60, 15 * 60, 45 * 60]

# --------------------------------------------------------------------------
# 예외 클래스 — 일시 장애 vs 구조 변경 의심을 코드 레벨에서 구분
# --------------------------------------------------------------------------


class TransientCollectorError(Exception):
    """네트워크/타임아웃/5xx — 재시도 대상."""


class StructureChangeSuspected(Exception):
    """응답은 정상인데 파싱 결과 0건 — 재시도 무의미, 즉시 사람 알림 대상."""


class ApiKeyMissing(Exception):
    """crtfcKey 미설정 — 사람이 발급/설정해야 함."""


# --------------------------------------------------------------------------
# API 키 로딩
# --------------------------------------------------------------------------


def load_api_key() -> str:
    """
    crtfcKey 로딩 우선순위:
      1. 환경변수 BIZINFO_API_KEY
      2. scripts/collector/config.yaml (bizinfo_api_key: "...") — 있으면 로드,
         없으면 스킵(선택적 파일)

    ※ 키 발급은 사람 몫이다. 발급 절차:
      1) https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi 접속
      2) "인증키 신청" — IP 등록 방식(고정 IP 있는 서버/PC) 또는 URL 등록 방식
         (배포 도메인 있는 경우) 중 선택해 신청서 제출
      3) 담당자 승인 후 이메일로 crtfcKey 통보 (승인까지 수 영업일 소요 가능 —
         정확한 소요 기간은 이 세션에서 확인 못함, 신청 시 안내 문구 확인)
      4) 발급된 키를 환경변수 BIZINFO_API_KEY로 설정하거나
         scripts/collector/config.yaml에 `bizinfo_api_key: "발급받은키"` 로 저장
         (이 파일은 git에 커밋하지 말 것 — .gitignore 등록 권장, TODO: 아직 미확인)
    """
    key = os.environ.get(API_KEY_ENV)
    if key:
        return key

    if os.path.exists(CONFIG_FILE):
        try:
            import yaml  # 표준 라이브러리 아님 — 이미 다른 스크립트(business_profiles.yaml
            # 로더)가 의존하고 있어 이 볼트 환경에는 설치되어 있다고 가정. 없으면
            # ImportError 메시지로 사람에게 안내.
        except ImportError:
            raise ApiKeyMissing(
                "config.yaml을 읽으려면 PyYAML이 필요합니다. "
                "pip install --break-system-packages pyyaml 로 설치하거나, "
                f"환경변수 {API_KEY_ENV}를 직접 설정하세요."
            )
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        key = cfg.get("bizinfo_api_key")
        if key:
            return key

    raise ApiKeyMissing(
        f"기업마당 API 키가 설정되어 있지 않습니다. 환경변수 {API_KEY_ENV}를 "
        f"설정하거나 {CONFIG_FILE}에 bizinfo_api_key를 넣어주세요. "
        "발급 절차는 load_api_key() 함수 docstring 참고."
    )


# --------------------------------------------------------------------------
# HTTP 호출 + 재시도
# --------------------------------------------------------------------------


def _classify_http_error(exc: Exception) -> bool:
    """True면 일시 장애(재시도 대상), False면 그 외(즉시 실패로 취급)."""
    if isinstance(exc, urllib.error.HTTPError):
        return 500 <= exc.code < 600
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return True
    return False


def _http_get_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "hem-gov-support-collector/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        if _classify_http_error(exc):
            raise TransientCollectorError(str(exc)) from exc
        raise
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # 응답은 왔는데 JSON이 아님 — 구조 변경 의심 후보. 상위에서 판단하도록
        # 원문 일부와 함께 예외를 던진다.
        raise StructureChangeSuspected(
            f"JSON 파싱 실패 (응답 앞부분: {raw_bytes[:200]!r})"
        ) from exc


def retry_call(fetch_fn, context_label: str, log=print):
    """
    §14 Q3 재시도 정책의 공용 구현. fetch_fn은 인자 없는 콜러블이어야 하고,
    TransientCollectorError만 재시도 대상이다(StructureChangeSuspected 등
    다른 예외는 즉시 위로 전파 — 재시도해도 의미 없는 실패이므로).
    3회 모두 실패하면 마지막 TransientCollectorError를 그대로 재발생시켜
    run()에서 exit code 1로 종료하게 한다. API 호출/폴백 스크레이핑 둘 다
    이 함수를 통해서만 네트워크에 접근한다 — 재시도 정책이 한 곳에만 있으면
    두 경로 중 하나가 정책을 빠뜨리는 실수를 막을 수 있다.
    """
    last_exc: Optional[Exception] = None
    attempts = len(RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(1, attempts + 1):
        try:
            return fetch_fn()
        except TransientCollectorError as exc:
            last_exc = exc
            log(f"[WARN] {context_label} 일시 장애 (시도 {attempt}/{attempts}): {exc}")
            if attempt <= len(RETRY_BACKOFF_SECONDS):
                wait_s = RETRY_BACKOFF_SECONDS[attempt - 1]
                log(f"[INFO] {wait_s}초 대기 후 재시도...")
                time.sleep(wait_s)
    assert last_exc is not None
    raise last_exc


def fetch_with_retry(url: str, context_label: str, log=print) -> dict:
    return retry_call(lambda: _http_get_json(url), context_label, log=log)


# --------------------------------------------------------------------------
# API 방식 수집
# --------------------------------------------------------------------------


def build_api_url(api_key: str, page_index: int = 1, page_unit: int = 100) -> str:
    params = {
        "crtfcKey": api_key,
        "dataType": "json",
        "pageUnit": str(page_unit),
        "pageIndex": str(page_index),
    }
    return f"{API_ENDPOINT}?{urllib.parse.urlencode(params)}"


def _first_present(record: dict, candidate_keys: list) -> Optional[str]:
    for k in candidate_keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return None


def normalize_api_record(record: dict, warnings: list) -> Optional[dict]:
    """기업마당 API 원본 레코드 1건 -> RAW_SCHEMA 1건. 확실하지 않은 필드는
    None + warnings에 어떤 필드가 못 찾아졌는지 남긴다(추측 금지)."""
    title = _first_present(record, FIELD_MAP["title"])
    pblanc_id = _first_present(record, FIELD_MAP["pblancId"])
    if not title or not pblanc_id:
        # 제목/pblancId는 필수 식별 정보 — 없으면 이 레코드는 신뢰할 수 없음
        warnings.append(f"title 또는 pblancId 누락된 레코드 스킵: {record!r}")
        return None

    agency = _first_present(record, FIELD_MAP["agency"])
    url = _first_present(record, FIELD_MAP["url"])
    if not url:
        url = DETAIL_URL_TEMPLATE.format(pblancId=pblanc_id)

    announcement_date = _first_present(record, FIELD_MAP["announcement_date"])

    deadline = None
    combined = _first_present(record, FIELD_MAP["reqst_period_combined"])
    if combined:
        # 예상 포맷 "20260601 ~ 20260630" 또는 "2026-06-01 ~ 2026-06-30" — 둘 다 시도
        m = re.search(r"(\d{4}-?\d{2}-?\d{2})\s*~\s*(\d{4}-?\d{2}-?\d{2})", combined)
        if m:
            deadline = _normalize_date_str(m.group(2))
    if not deadline:
        end_raw = _first_present(record, FIELD_MAP["reqst_end"])
        if end_raw:
            deadline = _normalize_date_str(str(end_raw))
    if not deadline:
        warnings.append(f"deadline 파싱 실패 (pblancId={pblanc_id}) — 마감일 미상으로 처리")

    attachments_raw = _first_present(record, FIELD_MAP["attachment_links"])
    if attachments_raw is None:
        attachment_links = []
    elif isinstance(attachments_raw, list):
        attachment_links = attachments_raw
    else:
        attachment_links = [attachments_raw]

    return {
        "title": title,
        "agency": agency,
        "url": url,
        "pblancId": pblanc_id,
        "announcement_date": _normalize_date_str(str(announcement_date)) if announcement_date else None,
        "deadline": deadline,
        "attachment_links": attachment_links,
    }


def _normalize_date_str(s: str) -> Optional[str]:
    """'20260630' / '2026-06-30' / '2026.06.30' -> 'YYYY-MM-DD'. 실패하면 None."""
    s = s.strip()
    m = re.match(r"^(\d{4})[.\-]?(\d{2})[.\-]?(\d{2})", s)
    if not m:
        return None
    y, mo, d = m.groups()
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def fetch_via_api(api_key: str, log=print) -> tuple:
    """전체 페이지 순회하며 raw 카드 리스트 반환. (cards, warnings) 튜플."""
    all_cards = []
    warnings: list = []
    page_index = 1
    page_unit = 100
    max_pages = 50  # 안전장치(무한루프 방지) — TODO: 실제 totalCount 필드로 대체

    while page_index <= max_pages:
        url = build_api_url(api_key, page_index=page_index, page_unit=page_unit)
        payload = fetch_with_retry(url, context_label=f"bizinfo API page {page_index}", log=log)

        # TODO(검증필요): 실제 응답 최상위 키가 jsonArray인지 확인 안 됨 —
        # 여러 후보를 방어적으로 시도.
        records = None
        for key in ("jsonArray", "items", "list", "data"):
            if isinstance(payload, dict) and key in payload:
                records = payload[key]
                break
        if records is None and isinstance(payload, list):
            records = payload
        if records is None:
            raise StructureChangeSuspected(
                f"API 응답에서 레코드 배열을 찾을 수 없음 (최상위 키: "
                f"{list(payload.keys()) if isinstance(payload, dict) else type(payload)})"
            )

        if not records:
            break  # 이 페이지가 마지막 페이지 (정상 종료)

        for rec in records:
            normalized = normalize_api_record(rec, warnings)
            if normalized:
                all_cards.append(normalized)

        if len(records) < page_unit:
            break
        page_index += 1

    return all_cards, warnings


# --------------------------------------------------------------------------
# 폴백: 목록 페이지 파싱 (API 스키마 미검증/장애 시)
# --------------------------------------------------------------------------


def scrape_list_page_fallback(log=print) -> tuple:
    """
    TODO(검증필요/미실행): 이 함수는 이 세션에서 실제 목록 페이지 HTML을 받아보지
    못한 채(샌드박스 네트워크 차단) 작성됐다. 정규식은 "상세페이지 링크에
    pblancId 쿼리파라미터가 노출되는 <a> 태그" 가정 하나에만 의존하는 최소
    구현이다. 운영 투입 전 반드시 사람이 한 번 실행해서 실물 HTML 구조와
    대조 검증할 것 — 지금은 "API 응답 스키마를 확정 못했을 때의 안전망이
    코드로 존재한다"는 것만 보장한다.
    """
    warnings: list = []

    def _fetch_list_page() -> bytes:
        req = urllib.request.Request(
            LIST_PAGE_URL, headers={"User-Agent": "hem-gov-support-collector/0.1"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if _classify_http_error(exc):
                raise TransientCollectorError(str(exc)) from exc
            raise

    # API 경로(fetch_with_retry)와 동일한 재시도 정책(§14 Q3)을 적용한다 —
    # 폴백이라고 재시도 없이 한 번만 시도하고 포기하지 않는다.
    html_bytes = retry_call(_fetch_list_page, context_label="bizinfo 목록페이지 폴백", log=log)

    page = html_bytes.decode("utf-8", errors="replace")

    # pblancId=PBLN_숫자 패턴이 들어간 링크를 전부 찾고, 그 주변의 텍스트를
    # 제목 후보로 잡는 매우 단순한 정규식 파싱 (TODO: html.parser 기반으로
    # 교체하고 agency/날짜도 추출하도록 보강 — 지금은 구조만 존재).
    pattern = re.compile(
        r'href="([^"]*pblancId=(PBLN_\d+)[^"]*)"[^>]*>([^<]{5,120})<', re.IGNORECASE
    )
    cards = []
    seen_ids = set()
    for m in pattern.finditer(page):
        href, pblanc_id, title_raw = m.groups()
        if pblanc_id in seen_ids:
            continue
        seen_ids.add(pblanc_id)
        title = html.unescape(title_raw).strip()
        url = href if href.startswith("http") else f"https://www.bizinfo.go.kr{href}"
        cards.append(
            {
                "title": title,
                "agency": None,  # 목록 페이지 파싱만으로는 확보 불가 — TODO
                "url": url,
                "pblancId": pblanc_id,
                "announcement_date": None,  # TODO
                "deadline": None,  # TODO — 목록 페이지에 표시되면 추가 파싱 필요
                "attachment_links": [],
            }
        )

    if not cards:
        warnings.append("폴백 파싱 결과 0건 — 목록 페이지 구조가 예상과 다를 수 있음")

    return cards, warnings


# --------------------------------------------------------------------------
# 필터링: 마감 지남 / 중복(pblancId)
# --------------------------------------------------------------------------


def filter_deadline_passed(cards: list, today: date, log=print) -> list:
    kept = []
    dropped = 0
    for c in cards:
        deadline = c.get("deadline")
        if deadline:
            try:
                d = date.fromisoformat(deadline)
                if d < today:
                    dropped += 1
                    continue
            except ValueError:
                pass  # 파싱 안 되면 일단 보수적으로 살려둠 (버리지 않음)
        kept.append(c)
    if dropped:
        log(f"[INFO] 마감 지난 공고 {dropped}건 필터링됨")
    return kept


def load_seen_pblanc_ids(inbox_dir: str, exclude_path: Optional[str] = None) -> set:
    """이미 raw로 수집된 적 있는 pblancId 집합. inbox의 기존
    announcements_raw_*.json 전부를 스캔한다(오늘자 파일 제외)."""
    seen = set()
    pattern = os.path.join(inbox_dir, "announcements_raw_*.json")
    for path in glob.glob(pattern):
        if exclude_path and os.path.abspath(path) == os.path.abspath(exclude_path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("announcements", data if isinstance(data, list) else []):
                pid = c.get("pblancId")
                if pid:
                    seen.add(pid)
        except (json.JSONDecodeError, OSError):
            continue  # 손상된 과거 파일은 조용히 스킵 (수집 자체를 막지 않음)
    return seen


def filter_duplicates(cards: list, seen_ids: set, log=print) -> list:
    kept = [c for c in cards if c.get("pblancId") not in seen_ids]
    dropped = len(cards) - len(kept)
    if dropped:
        log(f"[INFO] 기수집분(pblancId 중복) {dropped}건 필터링됨")
    return kept


# --------------------------------------------------------------------------
# 체크섬 게이트
# --------------------------------------------------------------------------


def compute_checksum(cards: list) -> str:
    ids = sorted(c.get("pblancId", "") for c in cards)
    payload = "|".join(ids).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_last_checksum(checksum_file: str) -> Optional[str]:
    if not os.path.exists(checksum_file):
        return None
    with open(checksum_file, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def write_checksum(checksum_file: str, checksum: str) -> None:
    os.makedirs(os.path.dirname(checksum_file), exist_ok=True)
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(checksum + "\n")


# --------------------------------------------------------------------------
# 사람 알림 (TODO — 배선만)
# --------------------------------------------------------------------------


def notify_human_structure_change(detail: str, log=print) -> None:
    # TODO: 실제 알림 채널 연결 (HANDOFF.md / 일일 세션로그 / Slack 등).
    # §14 Q3: "알림 채널은 기존 HANDOFF/일일 로그 체계에 맞춰 Sonnet 구현 시 결정"
    # — 이번 세션에서는 채널을 확정하지 않았으므로(설계 질문, 최종 보고 참고)
    # 우선 표준출력/stderr로만 남긴다.
    log(f"[ALERT][구조변경의심] {detail}", file=sys.stderr)


def notify_human_transient_failure(detail: str, log=print) -> None:
    # TODO: "3일 연속 실패 시에만 알림" 로직은 상위 스케줄러가 실행 이력을
    # 누적해서 판단해야 함(§14 Q3). 이 스크립트는 오늘 실패했다는 사실만 기록.
    log(f"[FAIL][일시장애-당일포기] {detail}", file=sys.stderr)


# --------------------------------------------------------------------------
# 출력
# --------------------------------------------------------------------------


def write_raw_output(cards: list, date_str: str, inbox_dir: str, warnings: list) -> str:
    os.makedirs(inbox_dir, exist_ok=True)
    out_path = os.path.join(inbox_dir, f"announcements_raw_{date_str}.json")
    payload = {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "source": "bizinfo.go.kr",
        "schema_note": "raw 계층 — 기계적으로 확실한 필드만. eligibility 등 본문 해석 "
        "필드는 없음(candidate 계층에서도 null, real_announcements.json 병합 전 사람 검수 필수).",
        "field_mapping_warnings": warnings,
        "count": len(cards),
        "announcements": cards,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def run(date_str: Optional[str] = None, inbox_dir: str = INBOX_DIR, log=print) -> int:
    today = date.today() if not date_str else date.fromisoformat(date_str)
    date_str = today.isoformat()

    warnings: list = []
    try:
        api_key = load_api_key()
    except ApiKeyMissing as exc:
        log(f"[INFO] {exc}")
        log("[INFO] API 키 없음 — 목록 페이지 파싱 폴백으로 진행합니다.")
        try:
            cards, fetch_warnings = scrape_list_page_fallback(log=log)
        except TransientCollectorError as exc2:
            notify_human_transient_failure(str(exc2), log=log)
            return 1
        warnings.extend(fetch_warnings)
    else:
        try:
            cards, fetch_warnings = fetch_via_api(api_key, log=log)
        except TransientCollectorError as exc:
            notify_human_transient_failure(str(exc), log=log)
            return 1
        except StructureChangeSuspected as exc:
            notify_human_structure_change(str(exc), log=log)
            return 2
        warnings.extend(fetch_warnings)

    if not cards:
        notify_human_structure_change(
            "API/폴백 호출은 성공했으나 파싱된 공고가 0건입니다. "
            "사이트 구조 변경 가능성 — 재시도하지 않고 즉시 종료합니다.",
            log=log,
        )
        return 2

    cards = filter_deadline_passed(cards, today, log=log)

    checksum_file = os.path.join(inbox_dir, ".last_checksum")
    out_path_placeholder = os.path.join(inbox_dir, f"announcements_raw_{date_str}.json")
    seen_ids = load_seen_pblanc_ids(inbox_dir, exclude_path=out_path_placeholder)
    cards = filter_duplicates(cards, seen_ids, log=log)

    checksum = compute_checksum(cards)
    last_checksum = read_last_checksum(checksum_file)

    out_path = write_raw_output(cards, date_str, inbox_dir, warnings)
    log(f"[INFO] raw 출력 작성: {out_path} ({len(cards)}건)")

    if checksum == last_checksum and last_checksum is not None:
        log("[INFO] 체크섬 동일 — 전일 대비 신규 공고 없음. 후속 단계(candidate 승격) 스킵 권고.")
        # 체크섬 파일은 갱신하지 않는다(변화 없음을 그대로 유지) — 갱신해도 무해하지만
        # "동일했다"는 사실 자체가 유의미한 로그이므로 파일을 다시 쓰지 않고 넘어감.
        return 10

    write_checksum(checksum_file, checksum)
    log(f"[INFO] 체크섬 갱신됨: {checksum[:12]}...")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="기업마당 공고 수집기 (raw 계층)")
    parser.add_argument(
        "--date", dest="date_str", default=None, help="YYYY-MM-DD (테스트용, 기본값=오늘)"
    )
    parser.add_argument(
        "--inbox-dir", dest="inbox_dir", default=INBOX_DIR, help="출력 폴더 (기본값=scripts/inbox)"
    )
    args = parser.parse_args()
    return run(date_str=args.date_str, inbox_dir=args.inbox_dir)


if __name__ == "__main__":
    sys.exit(main())
