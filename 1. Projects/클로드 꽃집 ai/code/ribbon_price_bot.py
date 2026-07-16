"""
ribbon_price_bot.py - 리본상품금액봇 (규칙기반 임시 버전)

역할: order_draft_bot이 만든 order_draft(및 normalized_text)에서 리본 문구를
정중한 최종 문구로 다듬고(ribbon_message_final), 상품명/금액/수량을 정형화한다.
작업 C 지시문에 tier: haiku로 명시된 stage — "정규화/템플릿 적용" 성격이 강해
order_draft_bot보다도 판단이 단순하다고 이미 합의됨(12봇_kind분류표.yaml
tier_rationale 참고).

다른 model 스테이지와 같은 이유(API 키 없음)로 지금은 사전+템플릿 기반
규칙기반 버전을 만든다.

로직:
  1. ribbon_message_raw: order_draft.ribbon_phrase_raw를 그대로 가져온다.
     order_draft_bot이 이미 "후보가 여러 개라 확정 못 함"으로 None을 남겼다면,
     여기서도 임의로 하나를 고르지 않고 None 그대로 둔다(프로젝트 원칙: 값을
     임의로 채우지 않는다).
  2. ribbon_message_final: raw 문구에서 "축하" 앞의 어근(예: "승진")을 뽑아
     "{어근}{을/를} 축하드립니다." 템플릿을 적용한다. 받침 유무는 유니코드
     종성 계산으로 판단한다(_has_batchim). raw가 None이면 final도 None.
  3. product_name: order_draft.product를 그대로 정식 상품명으로 채택한다
     (사전 정규화/동의어 통합은 아직 없음 — 알려진 한계).
  4. price: order_draft.amount_krw를 그대로 채택한다(수량 나눗셈/할증 등
     계산 없음).
  5. quantity: normalized_text에서 "숫자+개" 패턴이 명시적으로 있을 때만
     채우고, 명시가 없으면 "1개로 가정"하지 않고 None + 확인 필요로 남긴다
     (프로젝트 원칙 — golden_set 001/005/006 전부 수량이 명시돼 있지 않아
     이 케이스가 실제로 흔함).

알려진 한계 (숨기지 않고 명시):
  - ribbon_message_final 템플릿은 "{어근}을/를 축하드립니다." 딱 한 가지
    패턴만 지원한다. 근조/결혼/개업 등 다른 경조사 문구 톤(예: "삼가 고인의
    명복을 빕니다")은 이 버전에 없다 — 지금 golden_set에 승진 축하 사례만
    있어서 그것만 커버함. 실제 서비스에는 문구 유형별 템플릿이 더 필요하다.
  - product_name/price 값을 order_draft가 이미 뽑아놓은 값을 그대로
    신뢰한다 — 이 stage 자체가 원문을 다시 읽어 교차검증하지는 않는다.
  - quantity는 "숫자+개"류 명시적 패턴만 인식한다. "두 개", "세 개" 같은
    한글 수사는 인식하지 못한다(order_draft_bot의 금액 파서만 한글 수사를
    처리함 — 수량까지 확장하지 않음, 확인 필요).
  - order_draft가 order_split_bot의 known limitation(미분리 원문)을 그대로
    물려받았다면(golden_set call_007처럼), 이 봇도 그 오염된 값을 그대로
    정규화할 뿐 교정하지 않는다 — 상류 한계의 전파.

12봇_kind분류표.yaml 대응:
  io.reads:  order_draft, normalized_text
  io.writes: ribbon_message_raw, ribbon_message_final, product_name, price, quantity
"""

import re

_QUANTITY_PATTERN = re.compile(r"(\d+)\s*개")


def _has_batchim(ch: str) -> bool:
    """마지막 글자에 받침이 있는지 유니코드 종성 계산으로 판단한다."""
    code = ord(ch) - 0xAC00
    if 0 <= code <= 11171:
        return (code % 28) != 0
    return False  # 한글 완성형 음절이 아니면 판단 불가 - 받침 없다고 가정(알려진 한계)


def _build_ribbon_final(raw):
    if not raw or not raw.endswith("축하"):
        return None
    stem = raw[: -len("축하")]
    if not stem:
        return None
    particle = "을" if _has_batchim(stem[-1]) else "를"
    return stem + particle + " 축하드립니다."


def _process_rule_based(order_draft: dict, normalized_text: str) -> dict:
    """
    규칙기반(사전+템플릿) 리본/상품/금액 정규화 로직.

    나중에 LLM으로 교체할 때: 이 함수와 같은 시그니처(order_draft, normalized_text)
    -> dict를 만들어서 PROCESS_ENGINE에 대입하면 된다(process_ribbon_and_price()
    쪽은 안 바꿔도 됨).
    """
    order_draft = order_draft or {}
    normalized_text = normalized_text or ""

    ribbon_raw = order_draft.get("ribbon_phrase_raw")
    ribbon_final = _build_ribbon_final(ribbon_raw) if ribbon_raw else None

    product_name = order_draft.get("product")
    price = order_draft.get("amount_krw")

    qty_match = _QUANTITY_PATTERN.search(normalized_text)
    quantity = int(qty_match.group(1)) if qty_match else None

    notes = []
    if ribbon_raw is None:
        notes.append("ribbon_message_raw 없음(order_draft_bot 단계에서 후보 다수/미검출) - 확정하지 않음")
    if product_name is None:
        notes.append("product_name 없음 - order_draft에 product 정보 없음")
    if price is None:
        notes.append("price 없음 - order_draft에 amount_krw 정보 없음")
    if quantity is None:
        notes.append("quantity 명시 없음 - 기본값(1개) 가정하지 않고 확인 필요로 남김")

    confidence = 0.8 if (ribbon_final and product_name and price is not None) else 0.5

    return {
        "ribbon_message_raw": ribbon_raw,
        "ribbon_message_final": ribbon_final,
        "product_name": product_name,
        "price": price,
        "quantity": quantity,
        "confidence": confidence,
        "reason": "; ".join(notes) if notes else "order_draft 값 전부 채워져 있어 정규화 성공",
    }


# 실제로 쓰이는 정규화 엔진. 지금은 규칙기반. 나중에 LLM 버전을 만들면
# ribbon_price_bot.PROCESS_ENGINE = process_llm 처럼 이 이름만 바꿔치기하면
# process_ribbon_and_price()를 포함해 이 파일을 쓰는 다른 코드는 손댈 필요가 없다.
PROCESS_ENGINE = _process_rule_based


def process_ribbon_and_price(order_draft: dict, normalized_text: str = "") -> dict:
    """
    공개 API. order_draft_bot 결과(order_draft dict)와 normalized_text를 받아
    ribbon_message_raw/final, product_name, price, quantity를 만든다.
    반환: {"ribbon_message_raw", "ribbon_message_final", "product_name", "price",
           "quantity", "confidence", "reason"}
    """
    return PROCESS_ENGINE(order_draft, normalized_text)
