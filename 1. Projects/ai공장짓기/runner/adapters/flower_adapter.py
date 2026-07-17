#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flower_adapter.py — 꽃집(온천꽃식물원) 스킬을 범용 러너에 연결하는 어댑터

원칙: '1. Projects/클로드 꽃집 ai' 폴더는 한 글자도 수정하지 않는다.
code/ 밑 14개 봇 모듈의 실제 함수(collect/transcribe/classify_order/... 규칙기반
구현 그대로)를 무수정 import해서, 러너의 핸들러 계약(STAGE_FUNCS 등 5개)으로
얇게 감싸서 노출만 한다. 값을 새로 지어내거나 봇 로직을 다시 구현하지 않는다.

pest_adapter.py(방역)와의 구조적 차이 (반드시 먼저 읽을 것 — 미리 베끼지 않은 이유):
  - 방역은 scripts/run.py 하나에 STAGE_FUNCS 딕셔너리가 이미 완성돼 있어서
    importlib로 그 파일 하나만 로드하면 끝났다.
  - 꽃집은 그런 단일 STAGE_FUNCS가 없다. code/ 밑에 14개 봇이 각자 파일로 쪼개져
    있고, run_pipeline.py는 이들을 "위상정렬된 순서대로 직접 함수 호출"하는
    스크립트일 뿐, stage_id -> 함수 매핑 딕셔너리를 만들어 노출하지 않는다.
    또한 각 봇 함수의 시그니처가 fn(ctx, stage)가 아니라 봇마다 제각각이다
    (예: collection_bot.collect(source_type=..., raw_text=..., ...),
    storage_bot.save_order(confirmed_fields=..., ..., db_path=...)).
    그래서 이 어댑터가 직접 STAGE_FUNCS를 새로 만들고, 각 stage마다
    "ctx에서 읽어서 봇 함수 인자로 넘기고, 봇 함수 반환값을 ctx에 다시 쓰는"
    fn(ctx, stage) 래퍼 14개를 작성한다.
  - run_pipeline.py는 code/ 모듈들을 `sys.path.insert(0, code_dir)` 뒤
    `import collection_bot` 식의 평범한 top-level import로 부른다(다른 봇
    모듈끼리도 서로 그렇게 import함 — 예: sms_ledger_bot.py 안에 `import
    storage_bot`). 이 상호 import 때문에 pest_adapter처럼 importlib.util로
    파일 하나씩 개별 로드하면 storage_bot이 매번 다른 모듈 객체로 중복 로드돼
    깨진다. 그래서 이 어댑터도 run_pipeline.py와 동일하게 code/ 를 sys.path에
    추가한 뒤 평범한 import 문을 쓴다(무수정 원칙 위반 아님 — 그 폴더의 파일은
    하나도 안 고침, import 방식만 run_pipeline.py 그대로 재사용).

러너 핸들러 계약 구현 (5개):
  STAGE_FUNCS          — 14개 stage_id -> fn(ctx, stage) 래퍼(직접 작성, 아래 참고)
  evaluate_run_if      — 미노출(꽃집 manifest.yaml에 run_if 쓰는 stage가 하나도 없음
                          — 러너 기본값이 이미 "condition None → 항상 실행"이라 그대로 충분)
  pending_rejections   — 항상 {} 반환(아래 [발견사항 4] 참고)
  should_stop          — order_classification_bot의 STOP_CLASSIFICATIONS 재현(아래 [발견사항 2])
  batch_items          — 항상 None 반환(아래 [발견사항 3] — 러너 구조상 표현 불가능한
                          부분 fan-out이라 정직하게 미지원으로 남김)

[발견사항 2026-07-17] manifest.yaml과 실제 구현/러너 계약 사이에서 발견한 불일치들
(감추지 않고 여기 기록 — manifest.yaml 폴더 자체는 고치지 않음):

1. [RESOLVED 2026-07-17 — 볼트 쪽 manifest.yaml 직접 수정으로 해결됨. 아래는 당시
   기록 그대로 보존] manifest.yaml에 triggers: 섹션이 아예 없었다.
   방역 manifest.yaml에는 triggers(type: event/schedule, entry_stage)가 있는데
   꽃집 manifest.yaml에는 그 섹션 자체가 없었다(grep 확인 — "^triggers:" 0건).
   러너(runner.py) Runner.run()은 `trigger = next(t for t in self.triggers if
   t.get("type")==trigger_type)`에서 못 찾으면 즉시 RunnerError로 정지한다.
   즉 이 manifest.yaml로는 --validate-only(정적검증)는 통과할 수 있어도,
   실제 실행(python3 runner.py ... --trigger event)은 트리거 자체가 없어서
   무조건 실패했다. 당시엔 이 어댑터가 고칠 수 있는 범위 밖이었다(manifest.yaml
   수정 금지 원칙) — 2026-07-17 세션에서 꽃집 폴더 쪽에 triggers: 블록
   (type: event, entry_stage: collection_bot 하나만 — schedule 트리거를 쓰는
   리마인더봇 성격의 stage가 이 14개 안에 없어서 event 하나만 선언)을 추가해
   해결. 재검증: `runner.py "manifest.yaml" --handlers flower_adapter.py
   --input <sample.json> --trigger event` 실제 실행 → 14개 stage 전부 OK로
   완주 확인(golden_set.yaml entry 001 문자 원문으로 스모크 테스트, 테스트로
   생성된 flower_orders.json/logs/state는 실데이터 아니므로 실행 후 정리함).

1b. [RESOLVED 2026-07-17 — 볼트 쪽 manifest.yaml 직접 수정으로 해결됨. 아래는 당시
   기록 그대로 보존] 정적검증(runner.py --validate-only)이 FAIL 6건으로 막혔었다.
   원인: manifest.yaml은 tier를 각 model stage 항목 안에
   직접 쓰지 않고, 별도 최상위 블록 `model_routing.stages`(step/tier 쌍의
   리스트)에 따로 선언한다(파일 상단 주석: "tier is declared ONLY here (not
   duplicated on stages), to avoid drift" — 의도적 설계였음). 반면 러너의
   static_validate()는 `s.get("tier")`로 각 stage 딕셔너리 자체에서 직접
   tier를 찾는다(model_routing이라는 블록 존재 자체를 모름) — 그래서 6개
   model stage(order_classification_bot/order_split_bot/correction_bot/
   order_draft_bot/ribbon_price_bot/review_manager_bot) 전부 "tier가 없음"
   FAIL로 잡힌다. 대조: 방역 manifest.yaml은 tier를 stage 안에 직접 쓰기
   때문에(`kind: model` 바로 아래 `tier: sonnet` 식) 같은 검증에서 FAIL 0건
   /WARN 11건(티어명 별칭 경고만)으로 통과한다 — 실제로 두 manifest를 같은
   러너로 돌려 대조 확인함.
   당시엔 이 어댑터(핸들러 모듈)가 고칠 수 있는 지점이 아니었다 — static_validate()는
   runner.py의 main()이 handlers 모듈을 로드하기도 전에, manifest.yaml만 보고
   먼저 실행되기 때문(핸들러 훅 5개 중 어느 것도 여기 개입하지 않음). 근본 해결
   옵션 ①(manifest.yaml의 각 stage에 tier를 직접 추가, model_routing과 중복되더라도
   러너 호환 목적)을 2026-07-17 세션에서 실행 — 6개 model stage 전부에 tier: 추가,
   model_routing.stages 블록은 근거/이력 출처로 그대로 유지. 재검증 결과
   `runner.py "manifest.yaml" --validate-only` → FAIL 0건/WARN 0건(방역 manifest와
   동일 수준). validate_manifest.py(v2 스키마 검증기)도 그대로 FAIL 0/WARN 4(기존
   schema_ref 경로 문제 4건만 남음, tier 관련 아님) PASS.

2. order_classification_bot stage에 stop_condition 필드가 없다.
   12봇_kind분류표.yaml(209행)에는 "order_classification이 단순문의|일반통화|
   스팸무관이면 여기서 파이프라인 종료"라는 stop_condition이 명시돼 있고
   run_pipeline.py도 STOP_CLASSIFICATIONS 상수로 실제 그렇게 동작하는데,
   manifest.yaml의 이 stage에는 stop_condition 키 자체가 없다(on_fail만 있음).
   manifest.yaml 파일 상단 주석은 "이 파일과 12봇_kind분류표.yaml은 항상
   100% 동기화해야 한다"고 적어놨는데 이 필드가 누락된 것 — 두 파일 불일치.
   방역의 should_stop은 stage.get("stop_condition")을 실제로 읽어서 판정하지만,
   꽃집은 그 필드가 없으므로 이 어댑터의 should_stop()은 stage_id로 직접
   분기해서 run_pipeline.py의 실제 동작(STOP_CLASSIFICATIONS)을 재현한다.

3. order_split_bot 이후의 "다중주문 순차 loop"를 러너의 batch_items로
   표현할 수 없다(구조적 한계, 아래 상세).
   run_pipeline.py는 collection_bot~order_split_bot(1~4번)을 통화/문자 1건당
   딱 1번만 실행하고, order_split_bot이 만든 order_segments 개수만큼
   correction_bot~sms_ledger_bot(5~14번)만 순차 loop로 반복한다(HANDOFF.md:
   "다중주문은 fan-out 대신 순차 loop, bundle_id/bundle_sequence/bundle_status
   로 추적").
   그런데 runner.py의 batch_items 계약은 "entry_stage 하나를 기준으로,
   그 이후 tail 전체를 통째로 loop하거나 안 하거나" 둘 중 하나만 가능하다
   (Runner.run(): head=order[:entry_idx+1], tail=나머지 전부, batch_fn이
   None이 아니면 tail 전체를 매 item마다 반복 실행). 이게 성립하려면
   "아이템 개수를 결정하는 stage"가 곧 entry_stage여야 하는데(방역의
   리마인더봇처럼 — 리마인더봇 자신이 스케줄 트리거의 entry_stage이자
   due_list를 만드는 stage), 꽃집은 아이템 개수(세그먼트 수)를 정하는 stage
   (order_split_bot)가 파이프라인 중간(4번째)에 있고 entry_stage(수신 시점,
   1번째인 collection_bot)와 다르다. entry_stage를 order_split_bot으로
   두면 reachable_from()이 순방향(그 이후 stage)만 따라가므로 앞의 3개
   stage(collection_bot/transcription_bot/order_classification_bot)가
   통째로 실행 순서에서 빠져버린다. entry_stage를 collection_bot으로 두면
   batch_items가 불려지는 시점(head=[collection_bot] 실행 직후)에는 아직
   order_split_bot이 안 돌아서 세그먼트 개수를 알 수 없다.
   즉 "일부 구간만 fan-out"은 현재 runner.py MVP 범위 밖 — 억지로 끼워
   맞추지 않고 batch_items()는 항상 None을 반환한다(=fan-out 없음).
   다행히 지금 order_split_bot의 규칙기반 버전은 "항상 세그먼트 1개짜리
   배열만 반환"하는 게 이미 문서화된 알려진 한계(order_split_bot.py docstring,
   HANDOFF.md)라서, 오늘 시점 실제 동작에는 차이가 없다. 나중에 이 stage가
   실제 LLM으로 교체돼 세그먼트가 2개 이상 나오기 시작하면, 이 러너 경로는
   1번째 세그먼트만 처리하고 나머지는 유실한다(아래 run_order_split_bot의
   경고 로그로 감지 가능하게는 해뒀지만, 근본 해결은 아님) — 근본 해결은
   runner.py에 "entry_stage와 독립적인 batch 시작 지점" 개념을 추가하거나,
   flower 쪽 manifest를 2단계 파이프라인(entry_points 여러 개)으로 재설계
   해야 함. 이번 작업 범위 밖이라 여기 기록만 하고 넘어간다.

4. human_reviewer의 on_reject(반려) 워크플로우에 대응하는 mock이 없다.
   manifest.yaml의 human_reviewer stage에는 on_reject(default:
   review_manager_bot, max_loops: 3, on_exhaust: escalate_human)가 선언돼
   있지만, run_pipeline.py의 실제 mock(_mock_human_stage + 인라인 로직)은
   반려 분기 자체가 없다 — 항상 무조건 "검수저장"으로 자동승인한다(방역의
   대표자검수/문서승인처럼 _input의 human_decisions나 문서승인_시뮬레이션
   같은 반려 시뮬레이션 입력 채널이 없음). HANDOFF.md "아직 안 된 것 2번"에
   "human_reviewer 승인 UI 없음"으로 이미 명시된 한계와 같은 맥락이다.
   그래서 이 어댑터의 pending_rejections()는 항상 {}을 반환한다 — on_reject
   루프 자체가 이 mock 단계에서는 절대 발동하지 않는다(억지로 반려 시뮬레이션을
   지어내지 않음).

5. (참고, 에러는 아님) storage_bot.save_order()는 manifest.yaml이 나눠 선언한
   3개 필드(order/workflow_event/version)를 그렇게 분리해서 반환하지 않고
   record 하나(딕셔너리)로 합쳐서 반환한다. ctx["order"] = record로 채우는 건
   자연스럽다(print_prep_bot/dispatch_bot/sms_ledger_bot이 전부 이 record
   형태를 "order" 인자로 그대로 기대하고 있어서 오히려 맞아떨어짐). 다만
   ctx["workflow_event"]는 save_order()가 별도로 돌려주지 않아서(내부적으로만
   append) 이 어댑터가 storage_bot.py의 내부 append 로직(84~89행)과 동일한
   모양으로 재구성한다 — 새 판단을 넣은 게 아니라 이미 코드에 있는 구조를
   그대로 옮겨적은 것.

6. (참고, 에러는 아님) manifest.yaml의 shared_context는 어떤 필드에도
   `type:` 을 선언하지 않았다(12봇_kind분류표.yaml의 shared_context에는
   type: string/object/array 등이 있는데, manifest.yaml은 2026-07-16에
   io.reads/writes만 기계적으로 집계해 만들면서 type을 안 옮겨적음 — 헤더
   주석의 "두 파일 100% 일치" 원칙에 어긋나는 또 다른 지점). 그 결과 러너의
   boundary_check 타입검증(TYPE_MAP 비교)은 이 스킬에서는 사실상 항상
   스킵된다(존재 여부만 검사됨) — 안전망이 약화된 상태이지만 러너/어댑터
   버그는 아니고 manifest.yaml의 정보 누락이다.
"""

import sys
from pathlib import Path

# 꽃집 code/ 폴더 위치 — 볼트 루트 기준(러너: ai공장짓기/runner/adapters/, 여기서
# parents[3] == "1. Projects" 폴더. pest_adapter.py와 동일한 계산 재사용).
VAULT_ROOT = Path(__file__).resolve().parents[3]
FLOWER_DIR = VAULT_ROOT / "클로드 꽃집 ai"
FLOWER_CODE_DIR = FLOWER_DIR / "code"

if not FLOWER_CODE_DIR.is_dir():
    raise FileNotFoundError(f"꽃집 code/ 폴더를 찾을 수 없음: {FLOWER_CODE_DIR}")

# run_pipeline.py와 동일한 방식(무수정 원칙 유지 — import 방식만 재사용).
# 꽃집 모듈끼리 서로 top-level import(예: sms_ledger_bot.py의 `import storage_bot`)
# 하기 때문에, importlib로 파일마다 개별 로드하면 storage_bot이 중복 로드돼 깨진다.
if str(FLOWER_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(FLOWER_CODE_DIR))

import collection_bot
import transcription_bot
import order_classification_bot as ocb
import order_split_bot as osb
import correction_bot
import order_draft_bot
import ribbon_price_bot
import review_manager_bot
import storage_bot
import print_prep_bot
import dispatch_bot
import delivery_photo_bot
import sms_ledger_bot


# order_classification_bot이 이 값 중 하나면 파이프라인을 여기서 종료한다.
# run_pipeline.py의 STOP_CLASSIFICATIONS 그대로(발견사항 2 — manifest.yaml에는
# 이 규칙이 stop_condition 필드로 선언돼 있지 않아 stage_id로 직접 재현).
STOP_CLASSIFICATIONS = {"단순문의", "일반통화", "스팸무관"}


# ----------------------------------------------------------------------
# 1) STAGE_FUNCS — 14개 stage_id -> fn(ctx, stage) 래퍼
# ----------------------------------------------------------------------

def run_collection_bot(ctx, stage):
    inp = ctx.get("_input") or {}
    result = collection_bot.collect(
        source_type=inp.get("source_type"),
        raw_text=inp.get("raw_text"),
        raw_image=inp.get("raw_image"),
        raw_audio=inp.get("raw_audio"),
        created_at=inp.get("created_at"),
    )
    ctx.update(result)
    return f"source_type={result['source_type']} — raw 필드 수집 완료(collection_bot.collect 그대로 호출)"


def run_transcription_bot(ctx, stage):
    result = transcription_bot.transcribe(
        raw_audio=ctx.get("raw_audio"),
        raw_image=ctx.get("raw_image"),
        raw_text=ctx.get("raw_text"),
    )
    ctx.update(result)
    return f"cleaned_text 길이={len(result['cleaned_text'] or '')} (transcription_bot.transcribe 그대로 호출)"


def run_order_classification_bot(ctx, stage):
    text = ctx.get("stt_text") or ctx.get("ocr_text") or ctx.get("raw_text") or ""
    result = ocb.classify_order(text)
    ctx["order_classification"] = result["order_classification"]
    return f"{result['order_classification']} (confidence={result['confidence']}) — {result['reason']}"


def run_order_split_bot(ctx, stage):
    text = ctx.get("stt_text") or ctx.get("ocr_text") or ctx.get("raw_text") or ""
    result = osb.split_order(text)
    segments = result["order_segments"]
    ctx["order_segments"] = segments
    ctx["split_status"] = result["split_status"]
    ctx["bundle_id"] = result["bundle_id"]
    # [발견사항 2026-07-17 / 항목 3, 보정] manifest.yaml은 이 stage의 io.writes에
    # 최상위 bundle_sequence를 선언하지만 split_order()는 최상위로는 그 필드를
    # 만들지 않는다(세그먼트마다 order_segments[i]["bundle_sequence"]로만 존재).
    # 지금 규칙기반 버전은 세그먼트가 항상 1개뿐이라(알려진 한계), 그 1개짜리
    # 세그먼트의 bundle_sequence를 최상위로 끌어올려 계약을 만족시킨다 — 값을
    # 새로 지어내는 게 아니라 이미 존재하는 값의 위치만 옮기는 것.
    ctx["bundle_sequence"] = segments[0]["bundle_sequence"] if segments else None
    warn = ""
    if len(segments) > 1:
        warn = (
            f" [경고: 세그먼트 {len(segments)}건 감지 — 이 러너 경로는 부분 fan-out을 "
            f"지원하지 않아(발견사항 3 참고) 1번째 세그먼트만 처리되고 나머지는 유실됨]"
        )
    return (
        f"split_status={result['split_status']}, segment 수={len(segments)}"
        f"(규칙기반 버전은 경계 확정이 아니라 가능성 감지까지만 함 — 알려진 한계){warn}"
    )


def run_correction_bot(ctx, stage):
    segments = ctx.get("order_segments") or []
    segment_text = segments[0]["segment_text"] if segments else ""
    result = correction_bot.correct_text(segment_text)
    ctx["normalized_text"] = result["normalized_text"]
    ctx["correction_log"] = result["correction_log"]
    ctx["candidates"] = result["candidates"]
    return (
        f"정규화 완료(단위정규화 {len(result['correction_log'])}건, "
        f"불확실 후보 {len(result['candidates'])}건)"
    )


def run_order_draft_bot(ctx, stage):
    result = order_draft_bot.build_draft(ctx.get("normalized_text"))
    ctx["order_draft"] = result["order_draft"]
    ctx["field_confidence"] = result["field_confidence"]
    ctx["field_sources"] = result["field_sources"]
    ctx["missing_fields"] = result["missing_fields"]
    filled = len(result["order_draft"]) - len(result["missing_fields"])
    return f"필드 {filled}/{len(result['order_draft'])}개 채움 (missing={result['missing_fields']})"


def run_ribbon_price_bot(ctx, stage):
    result = ribbon_price_bot.process_ribbon_and_price(ctx.get("order_draft"), ctx.get("normalized_text"))
    ctx["ribbon_message_raw"] = result["ribbon_message_raw"]
    ctx["ribbon_message_final"] = result["ribbon_message_final"]
    ctx["product_name"] = result["product_name"]
    ctx["price"] = result["price"]
    ctx["quantity"] = result["quantity"]
    return (
        f"product_name={result['product_name']}, price={result['price']}, "
        f"ribbon_message_final={result['ribbon_message_final']}"
    )


def run_review_manager_bot(ctx, stage):
    result = review_manager_bot.build_review(
        order_draft=ctx.get("order_draft"),
        field_confidence=ctx.get("field_confidence"),
        field_sources=ctx.get("field_sources"),
        missing_fields=ctx.get("missing_fields"),
        candidates=ctx.get("candidates"),
        ribbon_message_raw=ctx.get("ribbon_message_raw"),
        ribbon_message_final=ctx.get("ribbon_message_final"),
        product_name=ctx.get("product_name"),
        price=ctx.get("price"),
        quantity=ctx.get("quantity"),
        correction_log=ctx.get("correction_log"),
        split_status=ctx.get("split_status"),
    )
    ctx["review_checklist"] = result["review_checklist"]
    ctx["review_priority"] = result["review_priority"]
    ctx["editable_fields"] = result["editable_fields"]
    return f"review_priority={result['review_priority']}, checklist 항목 {len(result['review_checklist'])}건"


def run_human_reviewer(ctx, stage):
    """
    run_pipeline.py의 _mock_human_stage + 인라인 자동승인 로직(189~198행)을 그대로
    재현한다. run_pipeline.py는 이 조합을 별도 함수로 빼두지 않아서(재사용 가능한
    export가 없음) 어댑터가 동일한 필드 조합을 여기서 재구성한다 — 새 판단을 넣는
    게 아니라 run_pipeline.py에 이미 있는 코드를 그대로 옮겨적은 것.
    [발견사항 4] 반려 분기 자체가 원본에 없어 여기도 항상 자동승인만 한다.
    """
    order_draft = ctx.get("order_draft") or {}
    confirmed_fields = dict(order_draft)
    confirmed_fields["normalized_text"] = ctx.get("normalized_text")
    confirmed_fields["ribbon_message_raw"] = ctx.get("ribbon_message_raw")
    confirmed_fields["ribbon_message_final"] = ctx.get("ribbon_message_final")
    confirmed_fields["product_name"] = ctx.get("product_name")
    confirmed_fields["price"] = ctx.get("price")
    confirmed_fields["quantity"] = ctx.get("quantity")
    ctx["confirmed_fields"] = confirmed_fields
    ctx["manual_edits"] = {}
    ctx["approval_action"] = "검수저장"
    return (
        "[MOCK-human] human_reviewer → 여기서 사람 승인 대기. 데모 목적으로만 자동 "
        "'검수저장' 처리(실제 사람 승인 아님 — run_pipeline.py의 _mock_human_stage/"
        "인라인 로직과 동일, 알려진 한계 그대로 재현)"
    )


def run_storage_bot(ctx, stage):
    inp = ctx.get("_input") or {}
    db_path = inp.get("db_path") or storage_bot.DB_PATH
    record = storage_bot.save_order(
        confirmed_fields=ctx.get("confirmed_fields"),
        manual_edits=ctx.get("manual_edits"),
        approval_action=ctx.get("approval_action") or "검수저장",
        bundle_id=ctx.get("bundle_id"),
        bundle_sequence=ctx.get("bundle_sequence"),
        db_path=db_path,
    )
    ctx["order"] = record
    # [발견사항 5] save_order()는 workflow_event를 따로 반환하지 않아(내부적으로만
    # append), storage_bot.py 84~89행과 동일한 모양으로 재구성한다.
    ctx["workflow_event"] = {
        "order_id": record["order_id"],
        "event_type": "created",
        "detail": {"approval_action": record["approval_action"], "확인_필요_필드": record["확인_필요_필드"]},
        "created_at": record["created_at"],
    }
    ctx["version"] = record["version"]
    ctx["_db_path"] = str(db_path)  # 내부용 pass-through(공식 io 계약 아님) — sms_ledger_bot이 같은 db를 보게 함
    return f"order_id={record['order_id']} 저장됨 (확인_필요_필드={record['확인_필요_필드']})"


def run_print_prep_bot(ctx, stage):
    result = print_prep_bot.prepare_print(ctx.get("order"))
    ctx["order_print"] = result["order_print"]
    ctx["ribbon_print"] = result["ribbon_print"]
    ctx["delivery_memo"] = result["delivery_memo"]
    ctx["driver_summary"] = result["driver_summary"]
    return "order_print/ribbon_print/delivery_memo/driver_summary 생성됨"


def run_dispatch_bot(ctx, stage):
    inp = ctx.get("_input") or {}
    result = dispatch_bot.dispatch(
        ctx.get("order"), ctx.get("driver_summary"), ctx.get("delivery_memo"),
        driver_id=inp.get("driver_id"),
    )
    ctx["dispatch_record"] = result["dispatch_record"]
    return f"dispatch_id={result['dispatch_record']['dispatch_id']}"


def run_delivery_photo_bot(ctx, stage):
    inp = ctx.get("_input") or {}
    result = delivery_photo_bot.capture_delivery_photo(
        ctx.get("dispatch_record"), photo_uri=inp.get("photo_uri")
    )
    ctx["delivery_photo"] = result["delivery_photo"]
    ctx["photo_status"] = result["photo_status"]
    return f"photo_status={result['photo_status']}"


def run_sms_ledger_bot(ctx, stage):
    inp = ctx.get("_input") or {}
    db_path = ctx.get("_db_path") or inp.get("db_path") or storage_bot.DB_PATH
    result = sms_ledger_bot.send_and_ledger(
        order=ctx.get("order"),
        delivery_photo=ctx.get("delivery_photo"),
        photo_status=ctx.get("photo_status"),
        bundle_id=ctx.get("bundle_id"),
        bundle_sequence=ctx.get("bundle_sequence"),
        to=inp.get("to"),
        db_path=db_path,
    )
    ctx["message_job"] = result["message_job"]
    ctx["message_result"] = result["message_result"]
    ctx["history_log"] = result["history_log"]
    ctx["bundle_status"] = result["bundle_status"]
    return f"message_result={result['message_result']['status']}, bundle_status={result['bundle_status']}"


STAGE_FUNCS = {
    "collection_bot": run_collection_bot,
    "transcription_bot": run_transcription_bot,
    "order_classification_bot": run_order_classification_bot,
    "order_split_bot": run_order_split_bot,
    "correction_bot": run_correction_bot,
    "order_draft_bot": run_order_draft_bot,
    "ribbon_price_bot": run_ribbon_price_bot,
    "review_manager_bot": run_review_manager_bot,
    "human_reviewer": run_human_reviewer,
    "storage_bot": run_storage_bot,
    "print_prep_bot": run_print_prep_bot,
    "dispatch_bot": run_dispatch_bot,
    "delivery_photo_bot": run_delivery_photo_bot,
    "sms_ledger_bot": run_sms_ledger_bot,
}


# ----------------------------------------------------------------------
# 2) evaluate_run_if — 미노출
#    꽃집 manifest.yaml의 14개 stage 중 run_if를 쓰는 stage가 하나도 없다(grep
#    확인). 러너 기본 동작(핸들러 훅 없으면 "condition None → 항상 실행")이 이미
#    정확히 맞아떨어져서, 이 어댑터는 evaluate_run_if를 따로 정의하지 않는다.
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# 3) pending_rejections — human_reviewer에 반려 시뮬레이션 채널이 없음(발견사항 4)
# ----------------------------------------------------------------------

def pending_rejections(ctx, stage_id):
    return {}


# ----------------------------------------------------------------------
# 4) should_stop — order_classification_bot의 STOP_CLASSIFICATIONS 재현(발견사항 2)
# ----------------------------------------------------------------------

def should_stop(ctx, stage):
    if stage.get("id") == "order_classification_bot" and ctx.get("order_classification") in STOP_CLASSIFICATIONS:
        return True, (
            f"stop_condition(어댑터에서 보정 — manifest.yaml에 이 필드가 없음, 발견사항 2 참고): "
            f"order_classification={ctx.get('order_classification')} — run_pipeline.py의 "
            f"STOP_CLASSIFICATIONS와 동일 판정"
        )
    return False, ""


# ----------------------------------------------------------------------
# 5) batch_items — 부분 fan-out은 runner.py MVP 범위 밖(발견사항 3) → 항상 None
# ----------------------------------------------------------------------

def batch_items(ctx, entry_stage):
    return None
