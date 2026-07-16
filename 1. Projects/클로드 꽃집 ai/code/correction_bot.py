"""
correction_bot.py - 말귀봇 (규칙기반 임시 버전)

역할: order_split_bot이 넘긴 세그먼트 1건(segment_text)을 받아 구어체/STT 오인식을
문맥으로 보정한 normalized_text를 만든다. golden_set 005의 "보호구 매장"이 뭘
뜻하는지, "면접 축하한다고"가 "승진 축하한다고"의 오인식인지 등은 실제 의미
추론이 필요한 문제라 kind: model, tier: sonnet으로 설계됐다(12봇_kind분류표.yaml
tier_rationale 참고).

다른 model 스테이지(order_classification_bot, order_split_bot)와 같은 이유로
(이 작업 환경에 Claude API 키가 연결돼 있지 않음) 지금은 사전+정규식 규칙기반
버전을 만든다. 나중에 API 키가 생기면 CORRECTION_ENGINE 자리에 LLM 호출 함수만
갈아끼우면 되도록 구조를 분리해뒀다(다른 규칙기반 model 봇과 동일한 패턴).

이 규칙기반 버전이 실제로 하는 일 (4가지, 전부 "안전한 것만" 자동 반영):
  1. "숫자+마넌" 류 명백한 단위 오인식만 정규화(예: "10마넌" -> "10만원") —
     의미가 안 바뀌는 표기 정규화이므로 normalized_text에 바로 반영하고
     correction_log에 남긴다.
  2. 발음이 비슷한 고유명사 오인식 후보(예: "부공면"↔"부곡면")는 사전에 있는
     것만 candidates에 후보로 남기고, normalized_text/원문은 절대 덮어쓰지
     않는다(프로젝트 원칙: "값을 임의로 채우지 않는다" — 원문 보존).
  3. 화자 스스로 불확실함을 드러내는 표현("몰라", "글쎄", "아마", "모르겠")을
     감지해 그 주변 구간을 candidates로 남긴다(golden_set 006 "몰라 뭐 저 어디
     부장됐다던가" 참고 — 화자 본인도 불확실한 것을 확정된 사실처럼 다루면 안 됨).
  4. 서로 다른 이벤트류 키워드(승진/면접/취임 등)가 함께 나오면 문맥 불일치
     가능성으로 candidates에 남긴다(golden_set 005: "승진"과 "면접"이 동시 등장 —
     화자가 실수로 뱉은 말인지 실제로 다른 사유인지 규칙기반으로는 판단 못함).

알려진 한계 (숨기지 않고 명시):
  - golden_set 005의 "보호구 매장"처럼 사전에 없는 낯선 오인식 패턴은 전혀
    잡지 못한다 — "처음 보는 단어가 오인식인지 원래 그런 뜻인지"는 문맥을
    실제로 이해해야 구별 가능한데, 정규식/사전 매칭으로는 안 된다. 이건 바로
    이 봇을 model(sonnet)으로 설계한 이유 그 자체인 케이스라, 실제 LLM을
    붙이기 전까지의 알려진 한계로 남겨둔다(test_correction_bot.py에 명시).
  - 이 봇은 입력이 이미 "주문 1건" 단위로 분리된 세그먼트라는 전제(io_note,
    order_split_bot.fan_out_resolution 참고)로 설계됐다. order_split_bot이
    아직 실제 분리를 못 해(known limitation) golden_set call_007처럼 여러
    주문이 섞인 원문을 그대로 받으면, 서로 다른 주문의 이벤트/오인식 신호가
    한 세그먼트 안에서 뒤섞여 candidates가 뒤죽박죽 나올 수 있다 — 이 봇의
    버그가 아니라 상류 stage(order_split_bot)의 알려진 한계가 전파된 것.

12봇_kind분류표.yaml 대응:
  io.reads:  order_segments, stt_text, ocr_text
  io.writes: normalized_text, correction_log, candidates
io_note 대응: 이 함수는 세그먼트 1건(segment_text: str)을 입력으로 받는다 —
  bundle_id/bundle_sequence는 이 stage를 그냥 통과한다(읽지도 쓰지도 않음,
  실행기가 pass-through로 전달).
"""

import re

# ---- 1. 명백한 단위 오인식(의미 안 바뀜) — normalized_text에 바로 반영 ----
_UNIT_MISHEARD_PATTERN = re.compile(r"(\d+)\s*마넌")

# ---- 2. 발음 비슷한 고유명사 오인식 후보 사전 (자동 반영 안 함, candidates만) ----
_TYPO_CANDIDATE_DICT = {
    "부공면": "부곡면",
}

# ---- 3. 화자 스스로 불확실함을 드러내는 표현 ----
_SELF_UNCERTAIN_PATTERN = re.compile(r"몰라|글쎄|아마|모르겠")

# ---- 4. 서로 다른 이벤트 키워드 동시 등장 감지 ----
_EVENT_KEYWORDS = ["승진", "면접", "취임", "합격", "개업", "입학", "졸업", "결혼", "출산", "부장"]


def _normalize_units(text: str, log: list) -> str:
    def _sub(m):
        original = m.group(0)
        corrected = m.group(1) + "만원"
        log.append({
            "original": original,
            "corrected": corrected,
            "type": "단위_오인식_정규화",
            "note": "숫자+마넌 -> 숫자+만원 (의미 안 바뀌는 표기 정규화, 안전하게 자동 반영)",
        })
        return corrected
    return _UNIT_MISHEARD_PATTERN.sub(_sub, text)


def _find_typo_candidates(text: str) -> list:
    found = []
    for typo, guess in _TYPO_CANDIDATE_DICT.items():
        if typo in text:
            found.append({
                "phrase": typo,
                "candidates": [guess + "(오인식 추정)"],
                "note": "발음 유사 오인식 후보 — 원문 그대로 보존, 자동 반영하지 않음(확인 필요)",
            })
    return found


def _find_self_uncertain_spans(text: str) -> list:
    found = []
    for m in _SELF_UNCERTAIN_PATTERN.finditer(text):
        start = max(0, m.start() - 10)
        end = min(len(text), m.end() + 10)
        found.append({
            "phrase": text[start:end].strip(),
            "candidates": [],
            "note": "화자 스스로 불확실함을 드러내는 표현 감지 — 확정된 사실처럼 다루면 안 됨(확인 필요)",
        })
    return found


def _find_event_conflicts(text: str) -> list:
    matched = sorted({kw for kw in _EVENT_KEYWORDS if kw in text})
    if len(matched) >= 2:
        return [{
            "phrase": ", ".join(matched),
            "candidates": [],
            "note": "서로 다른 이벤트류 키워드가 동시에 등장 — 실제 사유가 무엇인지 불일치 가능성(확인 필요)",
        }]
    return []


def _correct_rule_based(text: str) -> dict:
    """
    규칙기반(사전+정규식) 보정 로직.

    나중에 LLM으로 교체할 때: 이 함수와 같은 시그니처(text: str) -> dict를
    만들어서 CORRECTION_ENGINE에 대입하면 된다(correct_text() 쪽은 안 바꿔도 됨).
    """
    correction_log = []
    normalized = _normalize_units(text, correction_log)

    candidates = []
    candidates.extend(_find_typo_candidates(normalized))
    candidates.extend(_find_self_uncertain_spans(normalized))
    candidates.extend(_find_event_conflicts(normalized))

    confidence = 0.9 if not candidates else 0.5

    return {
        "normalized_text": normalized,
        "correction_log": correction_log,
        "candidates": candidates,
        "confidence": confidence,
        "reason": (
            "단위 표기 정규화 " + str(len(correction_log)) + "건, 불확실 후보 "
            + str(len(candidates)) + "건 감지"
        ),
    }


# 실제로 쓰이는 보정 엔진. 지금은 규칙기반. 나중에 LLM 버전을 만들면
# correction_bot.CORRECTION_ENGINE = correct_text_llm 처럼 이 이름만 바꿔치기하면
# correct_text()를 포함해 이 파일을 쓰는 다른 코드는 손댈 필요가 없다.
CORRECTION_ENGINE = _correct_rule_based


def correct_text(segment_text: str) -> dict:
    """
    공개 API. order_split_bot이 만든 order_segments의 원소 1개(segment_text)를 받는다.
    반환: {"normalized_text", "correction_log", "candidates", "confidence", "reason"}
    """
    return CORRECTION_ENGINE(segment_text or "")
