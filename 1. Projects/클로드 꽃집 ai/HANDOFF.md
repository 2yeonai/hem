---
tags: [꽃집, ai공장, 지침]
created: 2026-07-14
updated: 2026-07-14
---

# HANDOFF — 클로드 꽃집 ai (온천꽃식물원 주문 자동화 파이프라인)

> **새 기능을 설계·제안하기 전에 [[1. Projects/클로드 꽃집 ai/기능_인덱스|기능_인덱스]]부터 확인할 것.** "이미 있는 기능"을 다시 설계하는 사고를 막기 위한 단일 진입점(정부지원 스킬에 이미 있는 패턴, decision-log §19 판정2로 이 스킬에도 신설, 2026-07-17).

다음에 이 프로젝트를 이어받는 사람(사람 또는 다른 세션의 나 자신)을 위한 인수인계 문서.

**주의**: 이 파일은 예전에 `1. Projects/클로드 정부지원사업 ai/HANDOFF.md`의 옛 버전 오사본이 잘못 놓여 있던 자리다(2026-07-13 R4 정리 때 SKILL.md/manifest.yaml/scripts/test/gov-support-skill/은 `4. Archive/꽃집폴더_정부지원사본_2026-07/`로 이동됐는데 이 파일만 그때 누락됐었음). 오사본은 2026-07-14에 같은 Archive 폴더로 마저 이동했고, 이 파일이 이 프로젝트의 진짜 HANDOFF다.

## 개요

꽃집(온천꽃식물원) 주문 접수~배송까지의 14 stage AI 파이프라인. 통화/문자/카톡/사진으로 들어오는 주문을 수집→전사→주문판정→분리→보정→구조화→리본/가격정리→검수→사람승인→저장→인쇄준비→배송전달→배송사진→문자장부 순으로 처리한다. 설계는 `12봇_kind분류표.yaml`(파일명은 "12봇"이지만 실제로는 14 stage — 2026-07-07에 order_classification_bot/order_split_bot 2개가 추가됨), 실데이터 근거는 `golden_set.yaml`(실제 통화/문자 6건, 001~006), 결정 서사는 `decision-log_12to14봇.md`.

**2026-07-16 갱신**: 이 폴더 루트에 `manifest.yaml`이 복구됐다. 위 문단(정부지원 스킬 패턴이 없다는 서술)은 07-14 시점엔 사실이었지만 더 이상 아니다 — `4. Archive/꽃집폴더_정부지원사본_2026-07/`에 있던 manifest.yaml이 실은 정부지원 사본이 아니라 꽃집 전용으로 처음부터 새로 작성된 정본이었음이 Fable 5 판정(decision-log §12, 2026-07-16)으로 확인돼, 구조만 고쳐(`pipeline:` 중첩 해제 + `shared_context:` 신규 추가) 이 폴더 루트로 복구했다. `validate_manifest.py` 실행 결과 FAIL 0 / WARN 4(전부 schema_ref 파일 위치 문제, 무시 가능). `12봇_kind분류표.yaml`은 여전히 설계 근거·open_questions 동반 문서 역할을 겸하고, manifest.yaml과 항목이 100% 일치함(Fable 판정 시 대조 완료) — 한쪽 수정 시 둘 다 갱신하는 원칙 유지.

## 현재 상태 (2026-07-14 갱신 — kind:model 4봇 신규 구현)

### 설계 (12봇_kind분류표.yaml)
- schema_version: v2. 총 14 stage: **local 7개**(collection_bot, transcription_bot, storage_bot, print_prep_bot, dispatch_bot, delivery_photo_bot, sms_ledger_bot), **model 6개**(order_classification_bot, order_split_bot, correction_bot, order_draft_bot, ribbon_price_bot, review_manager_bot), **human 1개**(human_reviewer).
- 2026-07-06 Fable 5 결정으로 kind 골격(local/model/human) 확정 → 2026-07-07 실데이터 diff 로그 #2에서 "주문 아닌 통화가 파이프라인에 흘러듦"(false-positive) + "한 통화에 여러 주문이 섞임"(다중주문) 두 구멍 발견 → order_classification_bot(주문판정봇)/order_split_bot(주문분리봇) 신설, 12봇→14봇으로 확장. 다중주문은 fan-out(병렬) 대신 **순차 loop**로 처리하기로 결정(bundle_id/bundle_sequence/bundle_status 필드로 추적).
- 미해결 open_questions(임의로 확정 안 하고 남긴 것): transcription_bot의 kind local/model 불일치, order_draft_bot/review_manager_bot/신규 2봇의 tier(sonnet 제안이지 실측 아님), dispatch_bot의 kind 분류 근거(Fable 답변에 명시 없음, Sonnet 5 추론), human_reviewer의 반려-복귀(return_to) UX 정합성, review_manager_bot의 confidence 색상→수치 매핑(2026-07-14 review_manager_bot.py 구현에서 작업 가정으로 제안했으나 여전히 미확정 — 아래 참고).

### 실데이터 (golden_set.yaml)
- 실제 통화/문자 6건(001~006). 005/006은 같은 통화(call_007) 원문을 공유하는 두 주문이라 실무상 "5개 케이스"로 취급.
  - 001: SMS 주문(백승흔/박혜미, 난, 10만원) — 수신인/발신인이 스크린샷과 타이핑 버전에서 뒤바뀌어 있어 이름은 확정 안 하고 null+"확인 필요"로 둠.
  - 002/004: non_order(안부 전화/일정 문의) — false negative 방지용 negative example.
  - 003: "꽃 심으러 가야 되는데..." — "꽃"이라는 키워드는 있지만 주문이 아닌 false-positive 함정 사례. 규칙기반 판정봇이 아직 이걸 못 거르는 게 알려진 한계.
  - 005/006: 부곡면장/북면장 승진축하 통화 — 한 통화에 독립된 주문 2건이 섞인 다중주문 분리 근거 사례. 북면(recipient_region)은 창녕군 공식 행정구역에 없어 확인 필요로 남김(`참고자료_행정구역_지명사전.yaml` 참고).

### 구현 (code/) — **kind:local 7개 + kind:model 6개 전부 구현 완료** (2026-07-14 기준)

| stage | 파일 | 상태 |
|---|---|---|
| collection_bot | code/collection_bot.py | 8/8 PASS (local) |
| transcription_bot | code/transcription_bot.py | 8/8 PASS — STT/OCR 실 API 없어 항등(identity) 목업 (local) |
| order_classification_bot | code/order_classification_bot.py | 4/5 PASS — 규칙기반, golden_set 003 known limitation (model, 2026-07-07 구현) |
| order_split_bot | code/order_split_bot.py | 3/3 PASS — 규칙기반, call_007 자동 2분리는 못 함(known limitation) (model, 2026-07-07 구현) |
| **correction_bot** | code/correction_bot.py | **4/4 PASS — 신규(2026-07-14), 규칙기반(사전+정규식)** |
| **order_draft_bot** | code/order_draft_bot.py | **4/4 PASS — 신규(2026-07-14), 규칙기반(정규식+위치휴리스틱)** |
| **ribbon_price_bot** | code/ribbon_price_bot.py | **4/4 PASS — 신규(2026-07-14), 규칙기반(사전+템플릿)** |
| **review_manager_bot** | code/review_manager_bot.py | **3/3 PASS — 신규(2026-07-14), 규칙기반(체크리스트+우선순위 규칙)** |
| storage_bot | code/storage_bot.py | 12/12 PASS (2026-07-12 이전 구현, local) |
| print_prep_bot | code/print_prep_bot.py | 9/9 PASS (local) |
| dispatch_bot | code/dispatch_bot.py | 6/6 PASS (local) |
| delivery_photo_bot | code/delivery_photo_bot.py | 4/4 PASS — 실 카메라 연동 없음(mock, local) |
| sms_ledger_bot | code/sms_ledger_bot.py | 5/5 PASS — 실 문자 게이트웨이(알리고 등) 미연동(mock, local) |

**중요: "규칙기반 구현"은 "실 LLM 연동"이 아니다.** kind:model 6개 전부 이제 정규식/사전/휴리스틱으로 동작하지만, 이 작업 환경에 Claude API 키가 연결돼 있지 않아 실제 LLM 호출은 여전히 하나도 없다. 각 파일 docstring에 known limitation이 명시돼 있다:
  - order_classification_bot/order_split_bot(2026-07-07 구현, 기존): golden_set 003 오판정, call_007 자동 2분리 불가.
  - correction_bot(신규): 사전에 없는 낯선 오인식(golden_set 005 "보호구 매장")은 전혀 못 잡음.
  - order_draft_bot(신규): 위치 휴리스틱(받는사람 정보 먼저/보내는사람 정보 나중)을 가정 — 이 어순이 깨지면 오분류. 직함에서 유추한 지역명(예: "북면"→"북면")의 행정구역 실재 여부는 검증 안 함. 상류(order_split_bot)가 아직 실제 분리를 못 하면(golden_set call_007처럼) 서로 다른 주문의 필드가 recipient/sender 슬롯에 뒤섞일 수 있음(상류 한계의 전파 — 이 봇의 버그 아님). 사람 이름(recipient_name/sender_name)은 의도적으로 절대 추출 시도 안 함(golden_set 001의 실제 이름 뒤바뀜 사례 근거).
  - ribbon_price_bot(신규): "{어근}을/를 축하드립니다." 템플릿 한 가지만 지원(근조/결혼 등 다른 경조사 톤 없음). "숫자+개"류 명시적 수량 표기만 인식, 한글 수사("두 개") 인식 못 함, 수량 미명시 시 1개로 임의 가정하지 않고 None 유지.
  - review_manager_bot(신규): review_priority(초록/노랑/빨강/파랑) 색상 규칙 자체가 이 구현에서 제안한 작업 가정 — 12봇_kind분류표.yaml open_questions에 "확인 필요"로 명시된 미확정 항목을 이번에 규칙으로 구체화했을 뿐, 실측/공식 확정은 아님(review_manager_bot.py docstring 참고).

`code/run_pipeline.py`(2026-07-14 갱신): 12봇_kind분류표.yaml의 depends_on을 위상정렬해 실행 순서를 코드에 하드코딩하지 않고 계산. kind:local은 실제 함수 호출, kind:model 6개 전부 실제 규칙기반 함수 호출(더 이상 mock 로그만 남기지 않음), kind:human 1개(human_reviewer)만 여전히 로그만 남기고 값을 자동 통과시키는 mock으로 남김(이건 그대로 두라고 명시된 지시사항). golden_set 5개 케이스로 전체 파이프라인 스모크 테스트 실행 결과: **PASS(알려진 한계 1건 제외)** — 001/005·006은 끝까지 진행(order_draft/ribbon/review 전부 실제 값으로 채워지고 storage·인쇄·배송·문자·장부 전부 통과), 002/004는 stop_condition에서 정상 종료, 003은 규칙기반 판정봇의 기존 알려진 한계로 끝까지 진행(새 버그 아님, test_order_classification_bot.py의 KNOWN_LIMITATIONS과 동일 케이스).

실행 방법: `python3 code/run_pipeline.py` (골든셋 5케이스 자동 실행, 종료 코드 0=PASS). 개별 봇 테스트: `python3 code/test_<bot_name>.py`.

## 문서 요약

- `decision-log_12to14봇.md` — 12봇→14봇 확장 결정 서사(2026-07-06 Fable 결정 → 2026-07-07 실데이터 구멍 발견 → 2026-07-14 local 6봇+run_pipeline 구현). "골든셋이 설계를 이긴다"는 원리를 이번 확장의 핵심 교훈으로 기록.
- `최종점검_리포트_2026-07-14.md` — 2026-07-14 local 6봇+run_pipeline.py 구현분의 점검 리포트(작성 시점 기준 model 4봇은 아직 미구현이었음 — 이후 같은 날 안에 model 4봇도 구현 완료됨, 이 HANDOFF.md가 최신 상태).
- `최종점검_리포트_2026-07-07.md` — 실데이터 diff 로그 #2 기반 12봇→14봇 확장 시점의 점검 리포트(이전 라운드).
- `실데이터_diff_로그_001.md`, `_002.md` — golden_set 진입 원본 분석 기록.
- `리스크_메모_통화녹음_제3자동의.md` — 통화 녹음/전사에 제3자(수신인 등) 동의 이슈 리스크 메모(법적/윤리 이슈, 아직 결론 안 남 — 다음 세션에서 확인 필요할 수 있음).
- `참고자료_행정구역_지명사전.yaml` — 창녕군 등 행정구역/지명 사전(005/006의 "북면" 확인 등에 참고).

## 아직 안 된 것 (알려진 한계)

1. **kind:model 6개 전부 실 LLM 미연동**: order_classification_bot/order_split_bot(2026-07-07)에 이어 correction_bot(말귀봇)/order_draft_bot(주문정리봇)/ribbon_price_bot(리본상품금액봇)/review_manager_bot(검수매니저)도 2026-07-14에 규칙기반으로 구현됐지만, 6개 전부 여전히 실제 LLM 호출이 아니다(API 키 미연동). 각 파일 상단 docstring에 known limitation이 구체적으로 적혀 있다 — 위 표 참고.
2. **kind:human 1개 승인 UI 없음**: human_reviewer(사람 검수자) — 실제 검수 화면/버튼([검수저장]/[주문확정]/[출력준비]) 없음. run_pipeline.py는 데모 목적으로만 자동 통과시킴(실제 사람 승인 아님을 로그에 명시). 이번 작업(2026-07-14 model 4봇 구현)에서도 이 stage는 의도적으로 그대로 mock 유지.
3. transcription_bot의 STT/OCR — 실 API 키 미연동, 항등(identity) 목업.
4. sms_ledger_bot의 문자 발송 — 실 게이트웨이(알리고 등) 미연동, mock 항상 성공.
5. order_classification_bot/order_split_bot의 규칙기반 한계(003 오판정, call_007 자동 2분리 불가) — 2026-07-07부터 이미 문서화된 기존 한계, 새로 발견된 것 아님.
6. **[신규] order_draft_bot의 "미분리 원문 입력 시 필드 혼선" 한계**: order_split_bot이 call_007처럼 여러 주문을 하나로 남겨두면, order_draft_bot은 서로 다른 주문의 직함/기관명을 recipient/sender 두 슬롯에 뒤섞어 배정한다(test_order_draft_bot.py의 call_007 케이스에 재현돼 있음). order_split_bot이 실제 분리를 하게 되면 자동으로 해소될 문제 — order_draft_bot 자체를 고칠 필요는 없다.
7. **[신규] review_manager_bot의 review_priority 색상 매핑은 미확정 제안값**: 12봇_kind분류표.yaml open_questions에 "확인 필요"로 남아있던 항목을 이번 구현에서 구체적 규칙(빨강/노랑/파랑/초록 조건)으로 제안했지만, 실측 데이터로 검증된 것은 아니다 — review_manager_bot.py docstring 참고.
8. 12봇_kind분류표.yaml의 나머지 open_questions(위 "미해결" 참고) — 특히 order_draft_bot/order_classification_bot/order_split_bot의 tier가 실측 없이 제안값이라는 점.

## 다음 세션에서 이어받을 사람을 위한 시작점

**지금 여기서부터 시작하면 됨**: kind:model 6개 전부 규칙기반 구현은 끝났으니, 다음 우선순위는 (a) 실제 Claude API 키를 연결해 6개 model stage를 하나씩 실 LLM 호출로 교체하는 것(각 파일의 `*_ENGINE` 변수 자리에 LLM 호출 함수만 갈아끼우면 되도록 이미 구조가 분리돼 있음 — 예: `correction_bot.CORRECTION_ENGINE = correct_text_llm`), 아니면 (b) human_reviewer 승인 UI(간단한 웹 폼도 가능)를 붙이는 것. golden_set.yaml 5개 케이스로 회귀 테스트하는 것을 잊지 말 것 — 특히 001(SMS)과 005/006(call_007)은 실제 LLM이 붙으면 지금의 규칙기반 결과와 달라지는 게 정상이니 "달라짐=버그"로 오판하지 않도록 주의(특히 order_draft_bot의 위치 휴리스틱이나 ribbon_price_bot의 단일 템플릿처럼, 지금 값은 어차피 규칙기반의 근사치일 뿐이다).

그 다음으로는 리스크_메모_통화녹음_제3자동의.md의 법적 이슈를 정리하는 것도 우선순위 후보.

## 관련 문서

- [[1. Projects/클로드 꽃집 ai/golden_set|golden_set]]
- [[1. Projects/클로드 꽃집 ai/decision-log_12to14봇|decision-log_12to14봇]]
- [[1. Projects/클로드 꽃집 ai/최종점검_리포트_2026-07-14|최종점검_리포트_2026-07-14]]
- [[1. Projects/클로드 꽃집 ai/최종점검_리포트_2026-07-07|최종점검_리포트_2026-07-07]]
- [[1. Projects/클로드 꽃집 ai/실데이터_diff_로그_001|실데이터_diff_로그_001]]
- [[1. Projects/클로드 꽃집 ai/실데이터_diff_로그_002|실데이터_diff_로그_002]]
- [[1. Projects/클로드 꽃집 ai/리스크_메모_통화녹음_제3자동의|리스크_메모_통화녹음_제3자동의]]
- [[4. Archive/꽃집폴더_정부지원사본_2026-07/HANDOFF|HANDOFF (정부지원사업 오사본, 이 위치에서 이동됨)]]
- [[ai공장짓기/설계노트/3_②_꽃집_스킬|3_②_꽃집_스킬]]
- [[2. Areas/핵심맥락|핵심맥락]]

<!-- ok -->
