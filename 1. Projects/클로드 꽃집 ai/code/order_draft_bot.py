"""
order_draft_bot.py - 주문정리봇 (규칙기반 임시 버전)

역할: correction_bot이 만든 normalized_text에서 정형 필드(수령처/수령자/일시 등)를
구조화한다. 이미 말귀봇이 의미 해석을 끝낸 텍스트에서 사전 정의된 스키마로 필드를
채우는 작업이라 tier: haiku로 제안됨(12봇_kind분류표.yaml tier_rationale — 단,
실측 없는 제안이라는 open_question이 있음).

다른 model 스테이지와 같은 이유(API 키 없음)로 지금은 정규식+위치 휴리스틱
기반 규칙기반 버전을 만든다.

핵심 설계: 위치 휴리스틱
  화환주문 문자/통화는 관습적으로 "받는사람 정보가 먼저, 보내는사람 정보(금액/
  이벤트 뒤)가 나중"에 나온다(golden_set 001/005/006 전부 이 어순을 따름).
  pivot = 금액 또는 이벤트 키워드가 텍스트에서 처음 등장하는 위치로 잡고,
  그보다 앞에 나온 직함/기관명 매칭은 recipient, 뒤에 나온 매칭은 sender로
  배정한다. 이 관습을 따르지 않는 문자/통화는 오분류될 수 있다(알려진 한계).

이름(recipient_name/sender_name) — [2026-07-20 정책 변경, 혜미 승인]:
과거에는 레이블 없이 나열된 2~4음절 한글 이름은 수신/발신 순서를 안전하게
구분할 근거가 없다는 이유로(golden_set 001에서 스크린샷/타이핑 버전 사이에
이름이 실제로 뒤바뀐 실사고 참고) LLM 경로에서도 코드로 강제 null 처리했다.
2026-07-20 세션에서 혜미가 "이름도 자동 추출하되, 이미 있는 사람 승인 단계를
안전장치로 삼자"고 명시적으로 승인해, LLM 경로(_draft_llm)는 이제 다른 필드와
같은 위치 휴리스틱(pivot 앞=recipient, 뒤=sender)으로 이름도 추출을 "시도"한다.
단, 애매하면(후보 3개 이상, 순서 불명확 등) 여전히 null + missing_fields로
남기도록 프롬프트에 명시했고, field_confidence를 정직하게 낮게 매기게 해서
webapp 검수 화면에서 사람이 낮은 확신도를 보고 다시 확인할 수 있게 했다
(자세한 내용은 decision-log_12to14봇.md 해당 날짜 항목 참고).
규칙기반 폴백(_draft_rule_based)은 여전히 이름을 시도하지 않는다 — 정규식으로
한글 이름 후보를 안전하게 판별할 방법이 없어 그대로 두는 것이 알려진 한계다
(LLM 호출 실패 시에만 타는 경로라 실사용 빈도는 낮음).

알려진 한계 (숨기지 않고 명시):
  - 위치 휴리스틱은 golden_set의 관습적 어순을 가정한 것 — 그 가정이 깨지는
    입력(예: 보내는사람 정보가 먼저 나오는 문자)에서는 recipient/sender가
    뒤바뀔 수 있다.
  - 직함 패턴(2~4음절 한글 + 면장/동장/... )은 구어체 필러(예: "그래", "저기")가
    우연히 그 앞에 붙으면 오탐될 수 있다 — 최소한의 필러 차단 목록(_FILLER_PREFIXES)만
    두었을 뿐 완전한 필터는 아니다.
  - 직함(면장/동장/이장)에서 지역명을 유추할 때(예: "북면장" -> "북면") 그
    지역이 실제로 존재하는지는 검증하지 않는다 — golden_set 006의 "북면"처럼
    창녕군에 공식적으로 없는 지명일 수 있다(참고자료_행정구역_지명사전.yaml
    대조는 이 규칙기반 버전의 범위 밖).
  - 이 봇은 입력이 이미 "주문 1건" 단위로 분리된 세그먼트라는 전제로 설계됐다.
    order_split_bot이 아직 실제 분리를 못 해(known limitation) golden_set
    call_007처럼 여러 주문이 섞인 원문을 통째로 받으면, 서로 다른 주문의
    직함/기관명이 recipient/sender 두 슬롯에 뒤섞여 배정될 수 있다 — 이 봇의
    버그가 아니라 상류 stage(order_split_bot)의 알려진 한계가 전파된 것
    (test_order_draft_bot.py에 call_007 케이스로 명시).
  - ribbon_phrase_raw 후보가 2개 이상 발견되면(golden_set 005: "면접축하"와
    "승진축하" 둘 다 매칭) 어느 것이 최종 문구인지 규칙기반으로 확정하지
    않고 None으로 남긴다 — golden_set은 사람이 문맥("없잖아"라는 화자의 확인
    발언)으로 "승진 축하합니다"를 골랐지만, 그 수준의 추론은 이 규칙기반
    버전 범위 밖이다.

12봇_kind분류표.yaml 대응:
  io.reads:  normalized_text
  io.writes: order_draft, field_confidence, field_sources, missing_fields
"""

import re

import llm_client

_SYSTEM_PROMPT = """당신은 꽃집(온천꽃식물원) 주문 문자/통화의 정규화된 텍스트에서
정형 필드를 뽑는 담당자입니다. 아래 필드를 채우세요:
recipient_org, recipient_name, recipient_title, sender_org, sender_name, sender_title,
event, amount_krw(정수, 원 단위), product, ribbon_phrase_raw.

가장 중요한 원칙 (반드시 지킬 것):
- recipient_name/sender_name도 이제 채워보세요 — 다른 필드와 같은 위치 관례를
  적용합니다: pivot(금액/이벤트 키워드) 앞에 나온 레이블 없는 한글 이름은
  recipient_name, pivot 뒤에 나온 이름은 sender_name일 가능성이 높습니다.
  단, 아래 경우엔 절대 채우지 말고 missing_fields에 넣으세요:
  (a) 레이블 없는 한글 이름 후보가 3개 이상이라 역할 배정이 애매할 때,
  (b) pivot 앞뒤 위치만으로 판단하기 어렵거나 문맥이 이 관례를 안 따를 때,
  (c) 조금이라도 확신이 없을 때 — 절대 무리해서 채우지 마세요.
  과거(golden_set 001)에 이름 순서를 잘못 판단해 이름이 실제로 뒤바뀐 사고가
  있었으니, 채우더라도 field_confidence를 정직하게 낮게 매기고 field_sources에
  왜 이 순서로 배정했는지 근거를 구체적으로 남기세요 — 이 값은 사람이 승인
  화면에서 반드시 확인 후 승인하니(자동 발송 아님), 확신이 낮아도 후보를
  제시하는 것 자체는 도움이 됩니다.
- ribbon_phrase_raw 후보가 2개 이상이면(예: "면접축하"와 "승진축하" 둘 다 등장)
  어느 것이 맞는지 확정하지 말고 null로 남기세요.
- 그 외 필드도 확신이 없으면 null + missing_fields로 남기고 지어내지 마세요.
- 각 필드마다 field_confidence(0.0~1.0)와 field_sources(왜 그렇게 판단했는지 또는
  왜 못 채웠는지 한 문장)를 반드시 채우세요.

반드시 아래 JSON 형식으로만 답하세요:
{
  "order_draft": {"recipient_org": null|"...", "recipient_name": null|"...", "recipient_title": null|"...",
                   "sender_org": null|"...", "sender_name": null|"...", "sender_title": null|"...",
                   "event": null|"...", "amount_krw": null|<정수>, "product": null|"...",
                   "ribbon_phrase_raw": null|"..."},
  "field_confidence": {"<필드명>": <0.0~1.0>, ...},
  "field_sources": {"<필드명>": "<판단 근거 또는 못 채운 이유>", ...},
  "missing_fields": ["<채우지 못한 필드명>", ...]
}
"""

_TITLE_PATTERN = re.compile(r"([가-힣]{1,4})\s*(면장|동장|이장|사장|대표|원장|과장|팀장|부장)")
_ORG_PATTERN = re.compile(r"([가-힣]{2,10})\s*(군청|시청|구청|주민센터|면사무소|동사무소|협의회|건설|병원|학교|회사)")
_DEPT_SUFFIX_PATTERN = re.compile(r"^\s*([가-힣]{2,6}과)")
_DIGIT_AMOUNT_PATTERN = re.compile(r"(\d+)\s*(만\s*원|마넌|원)")
_KOREAN_DIGIT_MAP = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9, "십": 10}
_KOREAN_AMOUNT_PATTERN = re.compile(r"([일이삼사오육칠팔구]|십)\s*만\s*원")
_PRODUCT_PATTERN = re.compile(r"화환|근조|조화|난초|리본|화분|(?<![가-힣])난(?=으로|을|를|이|은|만|다|,|\.|\s|$)")
_RIBBON_PHRASE_PATTERN = re.compile(r"([가-힣]{2,6})\s*축하")
_EVENT_KEYWORDS = ["승진", "취임", "합격", "개업", "입학", "졸업", "결혼", "출산", "부장"]
_TITLE_TO_REGION_SUFFIX = {"면장": "면", "동장": "동", "이장": "리"}
# 구어체 필러(간투사)가 직함 패턴 앞에 우연히 붙어 오탐되는 것을 막는 최소 차단 목록
# (예: "그래 면장" -> "그래"+"면장"으로 잘못 매칭). 완전한 필터는 아니다(알려진 한계).
_FILLER_PREFIXES = {"그래", "그거", "저기", "어디", "아니", "그냥", "이제", "알겠"}

FIELDS = [
    "recipient_org", "recipient_name", "recipient_title",
    "sender_org", "sender_name", "sender_title",
    "event", "amount_krw", "product", "ribbon_phrase_raw",
]


def _find_pivot(text: str):
    positions = []
    m = _DIGIT_AMOUNT_PATTERN.search(text)
    if m:
        positions.append(m.start())
    m2 = _KOREAN_AMOUNT_PATTERN.search(text)
    if m2:
        positions.append(m2.start())
    for kw in _EVENT_KEYWORDS:
        idx = text.find(kw)
        if idx != -1:
            positions.append(idx)
    return min(positions) if positions else None


def _parse_amount(text: str):
    m = _DIGIT_AMOUNT_PATTERN.search(text)
    if m:
        unit = re.sub(r"\s", "", m.group(2))
        num = int(m.group(1))
        if unit in ("만원", "마넌"):
            return num * 10000
        if unit == "원":
            return num
    m2 = _KOREAN_AMOUNT_PATTERN.search(text)
    if m2:
        digit = _KOREAN_DIGIT_MAP.get(m2.group(1))
        if digit:
            return digit * 10000
    return None


def _pick_role_matches(text: str, pattern, pivot, exclude_prefixes=None):
    """pattern의 findall 매치들을 pivot 기준으로 recipient/sender 첫 매치씩 배정한다.
    exclude_prefixes에 있는 접두어(간투사 등)로 시작하는 매치는 건너뛴다(완전한
    필터는 아니고 최소한의 오탐 방지 - 알려진 한계)."""
    recipient_match = None
    sender_match = None
    for m in pattern.finditer(text):
        if exclude_prefixes and m.group(1) in exclude_prefixes:
            continue
        role = "recipient" if (pivot is None or m.start() < pivot) else "sender"
        if role == "recipient" and recipient_match is None:
            recipient_match = m
        elif role == "sender" and sender_match is None:
            sender_match = m
    return recipient_match, sender_match


def _draft_rule_based(text: str) -> dict:
    """
    규칙기반(정규식+위치휴리스틱) 필드 구조화 로직.

    나중에 LLM으로 교체할 때: 이 함수와 같은 시그니처(text: str) -> dict를
    만들어서 DRAFT_ENGINE에 대입하면 된다(build_draft() 쪽은 안 바꿔도 됨).
    """
    field_confidence = {f: 0.0 for f in FIELDS}
    field_sources = {f: "매칭 안 됨" for f in FIELDS}
    draft = {f: None for f in FIELDS}

    pivot = _find_pivot(text)

    # ---- 직함(수신/발신 역할은 pivot 기준 위치로 배정) ----
    recipient_title_m, sender_title_m = _pick_role_matches(
        text, _TITLE_PATTERN, pivot, exclude_prefixes=_FILLER_PREFIXES
    )
    if recipient_title_m:
        prefix, suffix = recipient_title_m.group(1), recipient_title_m.group(2)
        draft["recipient_title"] = prefix + suffix
        field_confidence["recipient_title"] = 0.8
        field_sources["recipient_title"] = "직함 패턴 매칭: '" + recipient_title_m.group(0) + "'"
        if suffix in _TITLE_TO_REGION_SUFFIX:
            draft["recipient_org"] = prefix + _TITLE_TO_REGION_SUFFIX[suffix]
            field_confidence["recipient_org"] = 0.6
            field_sources["recipient_org"] = (
                "직함에서 유추한 지역명(직함 패턴 '" + recipient_title_m.group(0)
                + "' 기반) - 행정구역 실재 여부 미검증, 확인 필요"
            )
    if sender_title_m:
        prefix, suffix = sender_title_m.group(1), sender_title_m.group(2)
        draft["sender_title"] = prefix + suffix
        field_confidence["sender_title"] = 0.8
        field_sources["sender_title"] = "직함 패턴 매칭: '" + sender_title_m.group(0) + "'"

    # ---- 기관명(군청/건설/협의회 등) - 뒤에 바로 "OO과" 부서명이 붙어있으면 함께 묶는다 ----
    recipient_org_m, sender_org_m = _pick_role_matches(text, _ORG_PATTERN, pivot)
    if recipient_org_m and draft["recipient_org"] is None:
        org_text = recipient_org_m.group(0).strip()
        dept_m = _DEPT_SUFFIX_PATTERN.match(text[recipient_org_m.end():])
        if dept_m:
            org_text = org_text + " " + dept_m.group(1)
        draft["recipient_org"] = org_text
        field_confidence["recipient_org"] = 0.85
        field_sources["recipient_org"] = "기관명 패턴 매칭: '" + org_text + "'"
    if sender_org_m:
        org_text = sender_org_m.group(0).strip()
        dept_m = _DEPT_SUFFIX_PATTERN.match(text[sender_org_m.end():])
        if dept_m:
            org_text = org_text + " " + dept_m.group(1)
        draft["sender_org"] = org_text
        field_confidence["sender_org"] = 0.85
        field_sources["sender_org"] = "기관명 패턴 매칭: '" + org_text + "'"

    # ---- 이벤트 ----
    event_positions = [(kw, text.find(kw)) for kw in _EVENT_KEYWORDS if kw in text]
    if event_positions:
        event_positions.sort(key=lambda x: x[1])
        primary_kw = event_positions[0][0]
        draft["event"] = primary_kw
        distinct_kw = {kw for kw, _ in event_positions}
        if len(distinct_kw) >= 2:
            field_confidence["event"] = 0.5
            field_sources["event"] = (
                "이벤트 키워드 매칭: '" + primary_kw + "' (그 외 감지: "
                + str(sorted(distinct_kw - {primary_kw})) + " - 복수 후보, 실제 사유 불일치 가능성 확인 필요)"
            )
        else:
            field_confidence["event"] = 0.8
            field_sources["event"] = "이벤트 키워드 매칭: '" + primary_kw + "'"

    # ---- 금액 ----
    amount = _parse_amount(text)
    if amount is not None:
        draft["amount_krw"] = amount
        field_confidence["amount_krw"] = 0.85
        field_sources["amount_krw"] = "금액 패턴 매칭"

    # ---- 상품 ----
    pm = _PRODUCT_PATTERN.search(text)
    if pm:
        draft["product"] = pm.group(0)
        field_confidence["product"] = 0.8
        field_sources["product"] = "상품 키워드 매칭: '" + pm.group(0) + "'"

    # ---- 리본 문구 후보(정확히 1개 매치일 때만 채택, 2개 이상이면 확정 안 함) ----
    ribbon_matches = [m.group(1) + "축하" for m in _RIBBON_PHRASE_PATTERN.finditer(text)]
    if len(ribbon_matches) == 1:
        draft["ribbon_phrase_raw"] = ribbon_matches[0]
        field_confidence["ribbon_phrase_raw"] = 0.8
        field_sources["ribbon_phrase_raw"] = "'축하' 인접 문구 매칭(단일 후보): '" + ribbon_matches[0] + "'"
    elif len(ribbon_matches) >= 2:
        field_sources["ribbon_phrase_raw"] = (
            "여러 후보 문구 발견 " + str(ribbon_matches) + " - 어느 것이 최종 문구인지 규칙기반으로 확정 불가, 확인 필요"
        )

    # ---- 이름(recipient_name/sender_name) - 의도적으로 시도하지 않음 ----
    field_sources["recipient_name"] = "이름 추출 시도 안 함(레이블 없는 한글 이름은 순서 신뢰 불가 - 확인 필요, 의도적 설계)"
    field_sources["sender_name"] = "이름 추출 시도 안 함(레이블 없는 한글 이름은 순서 신뢰 불가 - 확인 필요, 의도적 설계)"

    missing_fields = [f for f in FIELDS if draft.get(f) is None]

    return {
        "order_draft": draft,
        "field_confidence": field_confidence,
        "field_sources": field_sources,
        "missing_fields": missing_fields,
    }


def _draft_llm(text: str) -> dict:
    """2026-07-17 신설: 실제 Claude 호출 버전. manifest.yaml의 tier: low_cost 사용."""
    result = llm_client.call_llm_json(
        tier="low_cost",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=f"정규화된 텍스트:\n{text}",
    )
    draft = result.get("order_draft")
    if not isinstance(draft, dict):
        raise llm_client.LLMUnavailableError(f"order_draft 형식이 이상함: {draft!r}")
    result.setdefault("field_confidence", {})
    result.setdefault("field_sources", {})
    # [2026-07-20 정책 변경] 예전엔 모델이 이름을 채우면 코드로 강제 null 처리했다.
    # 이제는 모델의 판단을 신뢰하되(혜미 승인, 사람 승인 단계가 안전장치), 안전을
    # 위해 이름 필드에 confidence가 안 왔으면(모델이 깜빡함) 임의로 안전한 값을
    # 지어내지 않도록 보수적으로 낮은 값(0.4)을 매겨 webapp 검수 화면에서 "확인
    # 필요" 표시가 뜨게 한다 — field_sources도 마찬가지로 기본값을 채운다.
    for name_field in ("recipient_name", "sender_name"):
        if draft.get(name_field) is not None:
            result["field_confidence"].setdefault(name_field, 0.4)
            result["field_sources"].setdefault(
                name_field,
                "위치 관례(pivot 앞/뒤)로 추정한 값 - 이름은 특히 뒤바뀔 수 있으니 꼭 확인",
            )
    missing = [f for f in FIELDS if draft.get(f) is None]
    result["missing_fields"] = missing
    result["order_draft"] = draft
    return result


def _draft_auto(text: str) -> dict:
    """LLM 우선, 실패 시 규칙기반 자동 대체."""
    try:
        return _draft_llm(text)
    except llm_client.LLMUnavailableError as e:
        result = dict(_draft_rule_based(text))
        result["field_sources"] = dict(result.get("field_sources") or {})
        result["field_sources"]["_engine_note"] = f"LLM 호출 실패로 규칙기반 대체: {e}"
        return result


# 2026-07-17부터 LLM(Claude) 우선, 실패 시 규칙기반 자동 대체.
DRAFT_ENGINE = _draft_auto


def build_draft(normalized_text: str) -> dict:
    """
    공개 API. correction_bot이 만든 normalized_text 1건을 받는다.
    반환: {"order_draft", "field_confidence", "field_sources", "missing_fields"}
    """
    return DRAFT_ENGINE(normalized_text or "")
