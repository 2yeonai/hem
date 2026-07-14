---
tags: [꽃집, ai공장, 지침]
created: 2026-07-14
---

# HANDOFF — 클로드 꽃집 ai (온천꽃식물원 주문 자동화 파이프라인)

다음에 이 프로젝트를 이어받는 사람(사람 또는 다른 세션의 나 자신)을 위한 인수인계 문서.

**주의**: 이 파일은 예전에 `1. Projects/클로드 정부지원사업 ai/HANDOFF.md`의 옛 버전 오사본이 잘못 놓여 있던 자리다(2026-07-13 R4 정리 때 SKILL.md/manifest.yaml/scripts/test/gov-support-skill/은 `4. Archive/꽃집폴더_정부지원사본_2026-07/`로 이동됐는데 이 파일만 그때 누락됐었음). 오사본은 2026-07-14에 같은 Archive 폴더로 마저 이동했고, 이 파일이 이 프로젝트의 진짜 HANDOFF다.

## 개요

꽃집(온천꽃식물원) 주문 접수~배송까지의 14 stage AI 파이프라인. 통화/문자/카톡/사진으로 들어오는 주문을 수집→전사→주문판정→분리→보정→구조화→리본/가격정리→검수→사람승인→저장→인쇄준비→배송전달→배송사진→문자장부 순으로 처리한다. 설계는 `12봇_kind분류표.yaml`(파일명은 "12봇"이지만 실제로는 14 stage — 2026-07-07에 order_classification_bot/order_split_bot 2개가 추가됨), 실데이터 근거는 `golden_set.yaml`(실제 통화/문자 6건, 001~006), 결정 서사는 `decision-log_12to14봇.md`.

이 폴더 루트에는 정부지원사업 스킬 패턴(SKILL.md/manifest.yaml/scripts/test/)이 없다 — 꽃집 프로젝트는 그 4-factory 공통 매니페스트 패턴을 아직 안 쓰고, `12봇_kind분류표.yaml` 자체가 설계 스펙 역할을 겸하고 있다.

## 현재 상태 (2026-07-14 기준)

### 설계 (12봇_kind분류표.yaml)
- schema_version: v2. 총 14 stage: **local 7개**(collection_bot, transcription_bot, storage_bot, print_prep_bot, dispatch_bot, delivery_photo_bot, sms_ledger_bot), **model 6개**(order_classification_bot, order_split_bot, correction_bot, order_draft_bot, ribbon_price_bot, review_manager_bot), **human 1개**(human_reviewer).
- 2026-07-06 Fable 5 결정으로 kind 골격(local/model/human) 확정 → 2026-07-07 실데이터 diff 로그 #2에서 "주문 아닌 통화가 파이프라인에 흘러듦"(false-positive) + "한 통화에 여러 주문이 섞임"(다중주문) 두 구멍 발견 → order_classification_bot(주문판정봇)/order_split_bot(주문분리봇) 신설, 12봇→14봇으로 확장. 다중주문은 fan-out(병렬) 대신 **순차 loop**로 처리하기로 결정(bundle_id/bundle_sequence/bundle_status 필드로 추적).
- 미해결 open_questions(임의로 확정 안 하고 남긴 것): transcription_bot의 kind local/model 불일치, order_draft_bot/review_manager_bot/신규 2봇의 tier(sonnet 제안이지 실측 아님), dispatch_bot의 kind 분류 근거(Fable 답변에 명시 없음, Sonnet 5 추론), human_reviewer의 반려-복귀(return_to) UX 정합성, review_manager_bot의 confidence 색상→수치 매핑.

### 실데이터 (golden_set.yaml)
- 실제 통화/문자 6건(001~006). 005/006은 같은 통화(call_007) 원문을 공유하는 두 주문이라 실무상 "5개 케이스"로 취급.
  - 001: SMS 주문(백승흔/박혜미, 난, 10만원) — 수신인/발신인이 스크린샷과 타이핑 버전에서 뒤바뀌어 있어 이름은 확정 안 하고 null+"확인 필요"로 둠.
  - 002/004: non_order(안부 전화/일정 문의) — false negative 방지용 negative example.
  - 003: "꽃 심으러 가야 되는데..." — "꽃"이라는 키워드는 있지만 주문이 아닌 false-positive 함정 사례. 규칙기반 판정봇이 아직 이걸 못 거르는 게 알려진 한계.
  - 005/006: 부곡면장/북면장 승진축하 통화 — 한 통화에 독립된 주문 2건이 섞인 다중주문 분리 근거 사례. 북면(recipient_region)은 창녕군 공식 행정구역에 없어 확인 필요로 남김(`참고자료_행정구역_지명사전.yaml` 참고).

### 구현 (code/)
2026-07-14에 local 6개 봇 + run_pipeline.py를 신규 구현(storage_bot은 그 이전부터 구현·테스트 완료 상태였음). **kind:local 7개 전부 구현 완료**:

| stage | 파일 | 상태 |
|---|---|---|
| collection_bot | code/collection_bot.py | 8/8 PASS (기존) |
| transcription_bot | code/transcription_bot.py | 8/8 PASS — STT/OCR 실 API 없어 항등(identity) 목업 |
| storage_bot | code/storage_bot.py | 12/12 PASS (2026-07-12 이전 구현) |
| print_prep_bot | code/print_prep_bot.py | 9/9 PASS |
| dispatch_bot | code/dispatch_bot.py | 6/6 PASS |
| delivery_photo_bot | code/delivery_photo_bot.py | 4/4 PASS — 실 카메라 연동 없음(mock) |
| sms_ledger_bot | code/sms_ledger_bot.py | 5/5 PASS — 실 문자 게이트웨이(알리고 등) 미연동(mock) |

kind:model 6개 중 **2개는 규칙기반 임시 구현**(order_classification_bot, order_split_bot — 실 LLM 아님, known limitation 문서화됨: 003 오판정/call_007 자동 2분리 불가), **나머지 4개는 미구현**(correction_bot/order_draft_bot/ribbon_price_bot/review_manager_bot). kind:human 1개(human_reviewer)도 실 승인 UI 없음.

`code/run_pipeline.py`(303줄, 신규): 12봇_kind분류표.yaml의 depends_on을 위상정렬해 실행 순서를 코드에 하드코딩하지 않고 계산. kind:local은 실제 함수 호출, 구현된 model 2개는 실제 규칙기반 호출, 미구현 model 4개+human 1개는 로그만 남기고 값을 임의로 채우지 않음(None/원문 그대로 pass-through). golden_set 5개 케이스로 전체 파이프라인 스모크 테스트 실행 결과: **PASS(알려진 한계 1건 제외)** — 001/005·006은 끝까지 진행(저장·인쇄·배송·문자·장부 전부 통과), 002/004는 stop_condition에서 정상 종료, 003은 규칙기반 판정봇의 기존 알려진 한계로 끝까지 진행(새 버그 아님, test_order_classification_bot.py의 KNOWN_LIMITATIONS과 동일 케이스).

실행 방법: `python3 code/run_pipeline.py` (골든셋 5케이스 자동 실행, 종료 코드 0=PASS).

## 문서 요약

- `decision-log_12to14봇.md` — 12봇→14봇 확장 결정 서사(2026-07-06 Fable 결정 → 2026-07-07 실데이터 구멍 발견 → 2026-07-14 local 6봇+run_pipeline 구현). "골든셋이 설계를 이긴다"는 원리를 이번 확장의 핵심 교훈으로 기록.
- `최종점검_리포트_2026-07-14.md` — 2026-07-14 구현분(local 6봇+run_pipeline.py)의 점검 리포트. 신규 6개 봇 40/40 체크 PASS, 기존 회귀 테스트(storage_bot 12/12, order_classification_bot 4/5, order_split_bot 3/3) 이상 없음 확인. test_manifest.py는 FAIL이지만 이는 manifest.yaml이 2026-07-13 R4 정리로 이미 Archive로 옮겨진 것이 원인 — 이번 작업과 무관한 기존 이슈.
- `최종점검_리포트_2026-07-07.md` — 실데이터 diff 로그 #2 기반 12봇→14봇 확장 시점의 점검 리포트(이전 라운드).
- `실데이터_diff_로그_001.md`, `_002.md` — golden_set 진입 원본 분석 기록.
- `리스크_메모_통화녹음_제3자동의.md` — 통화 녹음/전사에 제3자(수신인 등) 동의 이슈 리스크 메모(법적/윤리 이슈, 아직 결론 안 남 — 다음 세션에서 확인 필요할 수 있음).
- `참고자료_행정구역_지명사전.yaml` — 창녕군 등 행정구역/지명 사전(005/006의 "북면" 확인 등에 참고).

## 아직 안 된 것 (알려진 한계)

1. **kind:model 4개 실 LLM 미연동**: correction_bot(말귀봇, 구어체/오인식 보정), order_draft_bot(주문정리봇, haiku 제안), ribbon_price_bot(리본상품금액봇, haiku), review_manager_bot(검수매니저, sonnet 제안) — 전부 run_pipeline.py에서 로그만 남기고 필드를 채우지 않는 mock 상태. 이 4개가 실제로 붙으면 order_draft/ribbon_message/review_checklist 등 필드가 채워지고 storage_bot 저장 결과의 "확인 필요" 필드 구성도 달라질 것으로 예상.
2. **kind:human 1개 승인 UI 없음**: human_reviewer(사람 검수자) — 실제 검수 화면/버튼([검수저장]/[주문확정]/[출력준비]) 없음. run_pipeline.py는 데모 목적으로만 자동 통과시킴(실제 사람 승인 아님을 로그에 명시).
3. transcription_bot의 STT/OCR — 실 API 키 미연동, 항등(identity) 목업.
4. sms_ledger_bot의 문자 발송 — 실 게이트웨이(알리고 등) 미연동, mock 항상 성공.
5. order_classification_bot/order_split_bot의 규칙기반 한계(003 오판정, call_007 자동 2분리 불가) — 2026-07-07부터 이미 문서화된 기존 한계, 새로 발견된 것 아님.
6. 12봇_kind분류표.yaml의 open_questions 전부(위 "미해결" 참고) — 특히 review_manager_bot/order_draft_bot의 tier가 실측 없이 제안값이라는 점.

## 다음 세션에서 이어받을 사람을 위한 시작점

**지금 여기서부터 시작하면 됨**: kind:model 4개(correction_bot/order_draft_bot/ribbon_price_bot/review_manager_bot) 중 하나를 골라 실제 LLM(sonnet/haiku, `ai공장짓기/CLAUDE.md` 모델 정책 참고) 연동을 시작. 순서상 correction_bot(말귀봇)이 order_draft_bot 앞이므로 먼저 붙이는 게 자연스럽다. 각 봇의 io.reads/writes는 `12봇_kind분류표.yaml`의 shared_context 정의를 그대로 따르면 되고, run_pipeline.py의 해당 mock 분기(현재 로그만 남기는 부분)를 실제 호출로 교체하면 된다. golden_set.yaml 5개 케이스로 회귀 테스트하는 것을 잊지 말 것 — 특히 001(SMS)과 005/006(call_007)은 실제 필드가 채워졌을 때 이전 mock 결과와 달라지는 게 정상이니 "달라짐=버그"로 오판하지 않도록 주의.

그 다음으로는 human_reviewer 승인 UI(간단한 웹 폼도 가능)를 붙이거나, 리스크_메모_통화녹음_제3자동의.md의 법적 이슈를 먼저 정리하는 것도 우선순위 후보.

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
