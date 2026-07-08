#!/usr/bin/env python3
"""notice_parser.py — 공고문 텍스트 → 구조(배점·일정·서류·자격) + 성격(목적·심사의도·전략) 분석.

단순 추출이 아니라 혜미 방식 0단계·4단계를 자동화한다:
- parse_notice(): input_schema의 notice dict 필드를 채운다 (없으면 '미확보' 유지)
- notice_character(): 사업 목적 분류, 심사 의도, 선호 표현, 위험 전략 도출 (규칙 기반 = 로컬 모드)
모든 결과는 [확인 필요] 태그와 근거 줄을 함께 남긴다 — 지어내지 않는다.
"""
from __future__ import annotations

import re

DATE_PAT = re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})[일.]?")
SCORE_ROW = re.compile(r"([가-힣A-Za-z·\s()]{2,30}?)\s*[\(:]?\s*(\d{1,3})\s*점\s*[\)]?")
PAGE_LIMIT = re.compile(r"(\d{1,3})\s*(?:페이지|쪽|매)\s*(?:이내|이하|내외)")


def _section(text: str, heads: list, stop_heads: list, max_lines=15) -> str:
    """제목 키워드가 있는 줄부터 다음 섹션 제목 전까지 수집."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if len(s) < 40 and any(h in s for h in heads):
            out = []
            for j in range(i + 1, min(i + 1 + max_lines, len(lines))):
                t = lines[j].strip()
                # 다음 섹션 제목: 짧은 줄 + 머리말 키워드가 줄 앞부분(번호 뒤)에 있을 때만
                if (t and len(t) < 40 and not any(h in t for h in heads)
                        and any(0 <= t.find(h) <= 4 for h in stop_heads)):
                    break
                if t:
                    out.append(t)
            if out:
                return "\n".join(out)[:800]
    return ""


ALL_HEADS = ["목적", "개요", "신청자격", "지원대상", "지원내용", "지원규모", "지원제외", "제외대상",
             "신청방법", "접수", "제출서류", "평가", "심사", "선정", "일정", "문의", "유의사항", "협약"]


def parse_notice(text: str) -> dict:
    """텍스트 → notice dict 부분 필드 + 근거. 못 찾으면 키를 만들지 않는다."""
    out: dict = {"parse_notes": []}
    if not text or len(text) < 100:
        out["parse_notes"].append("텍스트 부족 — 구조 분석 불가")
        return out

    # 제목: 첫 줄들 중 '공고'가 든 가장 긴 줄
    for ln in text.splitlines()[:15]:
        s = ln.strip()
        if "공고" in s and 8 < len(s) < 80:
            out["title"] = re.sub(r"^\S*공고\S*\s*", "", s) or s
            out["title"] = s
            break

    # 마감·일정: 날짜 패턴 + 주변 맥락
    dates = []
    for m in DATE_PAT.finditer(text):
        ctx = text[max(0, m.start() - 25):m.end() + 15].replace("\n", " ")
        dates.append({"date": f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", "context": ctx.strip()})
    if dates:
        out["schedule"] = dates[:12]
        # 마감일: '마감·까지' 문맥 우선, 없으면 '접수' 문맥 — 기간 표기(A ~ B)는 늦은 날짜가 마감
        for keys in (("마감", "까지"), ("접수",)):
            cand = [d for d in dates if any(k in d["context"] for k in keys)]
            if cand:
                out["apply_deadline"] = max(c["date"] for c in cand)
                break

    # 수행기간
    m = re.search(r"(?:협약|수행|사업)\s*기간[^\n]{0,40}", text)
    if m:
        out["execution_period"] = m.group(0).strip()[:100]

    # 배점표: 'XX점' 패턴 (합계 60~120이면 신뢰)
    scoring, seen = [], set()
    for m in SCORE_ROW.finditer(text):
        # 개행을 넘어 붙은 앞 줄 제목 제거 (같은 줄의 항목명만)
        item = m.group(1).split("\n")[-1].strip(" -·|\t")
        pts = int(m.group(2))
        if 3 <= pts <= 60 and 2 <= len(item) <= 30 and item not in seen and not item.isdigit():
            if any(k in item for k in ("배점", "합계", "총점", "만점")):
                continue
            scoring.append({"item": item, "points": pts})
            seen.add(item)
    total = sum(s["points"] for s in scoring)
    if 60 <= total <= 120 and len(scoring) >= 3:
        out["scoring"] = scoring
        out["parse_notes"].append(f"배점표 자동 추출 {len(scoring)}개 항목 합계 {total}점 — 원문 대조 필요")
    elif scoring:
        out["parse_notes"].append(f"배점 후보 {len(scoring)}개 발견했으나 합계 {total}점이라 확정 안 함 [확인 필요]")

    # 섹션들
    for key, heads in [("purpose", ["목적", "개요", "취지"]), ("eligibility", ["신청자격", "지원대상", "신청 자격"]),
                       ("exclusions", ["지원제외", "제외대상", "신청제외", "참여제한"])]:
        sec = _section(text, heads, ALL_HEADS)
        if sec:
            out[key] = sec

    # 제출서류: 목록형 줄
    docs = []
    sec = _section(text, ["제출서류", "신청서류", "제출 서류"], ALL_HEADS, 20)
    for ln in sec.splitlines():
        s = ln.strip(" -·○•▷□①②③④⑤⑥⑦⑧⑨1234567890.)")
        if 3 < len(s) < 60:
            docs.append(s)
    if docs:
        out["documents"] = docs[:15]

    # 지원금·자부담·페이지 제한·발표
    m = re.search(r"(?:최대|한도)[^\n]{0,15}?([\d,]+)\s*(만\s*원|백만\s*원|억\s*원)", text)
    if m:
        out["max_amount"] = m.group(0).strip()
    m = re.search(r"자\s*부담[^\n]{0,40}", text)
    if m:
        out["self_pay"] = m.group(0).strip()[:80]
    m = PAGE_LIMIT.search(text)
    if m:
        out["page_limit"] = m.group(0)
    if re.search(r"발표\s*(평가|심사)|대면\s*평가|PT\s*심사|피칭", text):
        out["presentation_required"] = "있음(공고 감지)"
    return out


# ------------------------------------------------ 공고 성격 분석 (로컬 규칙)

PURPOSE_TYPES = [
    ("디지털 전환·AI", ["디지털", "AI", "인공지능", "스마트", "자동화", "온라인 전환"]),
    ("창업·초기기업", ["창업", "예비창업", "초기", "스타트업"]),
    ("소상공인 경영개선", ["소상공인", "자영업", "경영개선", "골목"]),
    ("수출·판로", ["수출", "해외", "판로", "글로벌", "바이어"]),
    ("R&D·기술개발", ["R&D", "기술개발", "연구", "시제품", "특허"]),
    ("고용·인력", ["고용", "채용", "인력", "일자리"]),
    ("지역·전통시장", ["지역", "전통시장", "상권", "로컬"]),
]

INTENT_BY_AXIS = [
    ("성장", "돈을 준 뒤 '사업이 커졌다'는 성과를 보고하고 싶어한다 — 매출·고용·매출구조 변화로 답하라"),
    ("적합", "아무에게나 주는 돈이 아니라는 걸 확인하고 싶어한다 — 공고 목적 문구를 본문에 되돌려줘라"),
    ("실행", "돈이 집행 불능으로 남는 걸 두려워한다 — 기간 내 좁은 범위 + 월 단위 일정"),
    ("역량", "받고 못 하는 신청자를 거르고 싶어한다 — 직접 실행·검수 구조와 경험 증빙"),
    ("예산", "감사 지적을 두려워한다 — 항목→산출물→성과 연결과 산정 근거"),
]


def notice_character(text: str, scoring: list) -> dict:
    """사업 목적 분류 + 심사 의도 + 선호 표현 + 위험 전략 (규칙 기반 — AI 모드로 정밀화 가능)."""
    res = {"purpose_type": [], "review_intent": [], "preferred_terms": [],
           "risky_moves": [], "note": "규칙 기반 1차 분석 — AI 검수 탭에서 정밀 분석 가능 [확인 필요]"}
    if not text:
        res["note"] = "공고 텍스트 없음 — 성격 분석 불가"
        return res
    # 1. 목적 분류 (키워드 빈도)
    scores = []
    for name, kws in PURPOSE_TYPES:
        c = sum(text.count(k) for k in kws)
        if c >= 2:
            scores.append((c, name))
    res["purpose_type"] = [n for _, n in sorted(scores, reverse=True)[:2]] or ["일반 지원사업 [확인 필요]"]

    # 2. 심사 의도 (배점 상위 축 → 의도 해석)
    for s in sorted(scoring or [], key=lambda x: -x.get("points", 0))[:3]:
        item = s.get("item", "")
        intent = next((i for k, i in INTENT_BY_AXIS if k in item), None)
        res["review_intent"].append(f"{item}({s.get('points')}점): " + (intent or "이 항목에 근거·수치를 직접 배치하라"))
    if not res["review_intent"]:
        res["review_intent"].append("배점표 미확보 — 심사 의도 추정 불가, 원문 확보가 최우선 [확인 필요]")

    # 3. 선호 표현: 공고 빈출 정책어 (본문에 되돌려줄 어휘)
    words = re.findall(r"[가-힣]{2,8}", text)
    freq: dict = {}
    stop = set("지원 사업 신청 대상 경우 관련 위한 통해 또는 등의 해당 이내 이상 별도 기준 방법 제출 접수 안내 기관 진행".split())
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    res["preferred_terms"] = [w for w, c in sorted(freq.items(), key=lambda kv: -kv[1])[:12] if c >= 3]

    # 4. 위험 전략 (공고 명시 감점·제외에서 도출)
    risk_pats = [
        (r"단순[^\n]{0,30}(구매|구입|구독)", "단순 구매·구독형 계획"),
        (r"(외주|위탁)[^\n]{0,20}(불가|제외|지양)", "외주 의존형 계획"),
        (r"중복\s*(수혜|지원|참여)[^\n]{0,20}", "중복수혜 미확인 상태 신청"),
        (r"(허위|과장)[^\n]{0,20}", "과장·허위 기재"),
        (r"기\s*(개발|출시|수행)[^\n]{0,20}(제외|불가)", "이미 한 일을 새 과제처럼 쓰기"),
    ]
    for pat, label in risk_pats:
        m = re.search(pat, text)
        if m:
            res["risky_moves"].append(f"{label} — 공고 근거: \"{m.group(0)[:50]}\"")
    if not res["risky_moves"]:
        res["risky_moves"].append("공고에서 명시 감점 문구 미발견 — 내부 기준(danger_words)만 적용 중")
    return res
