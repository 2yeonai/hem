---
tags: [꽃집, ai공장, 지침]
created: 2026-07-14
updated: 2026-07-17
---

# HANDOFF — 클로드 꽃집 ai (온천꽃식물원 주문 자동화 파이프라인)

> **새 기능을 설계·제안하기 전에 [[1. Projects/클로드 꽃집 ai/기능_인덱스|기능_인덱스]]부터 확인할 것.** "이미 있는 기능"을 다시 설계하는 사고를 막기 위한 단일 진입점(정부지원 스킬에 이미 있는 패턴, decision-log §19 판정2로 이 스킬에도 신설, 2026-07-17).

다음에 이 프로젝트를 이어받는 사람(사람 또는 다른 세션의 나 자신)을 위한 인수인계 문서.

## AI 작업 시작 규칙 — 반드시 먼저 적용 ([hyemi, 2026-07-20] 신설)

- 기능_인덱스와 이 구역만 먼저 읽는다. 아래 과거 이력 전체를 처음부터 읽지 않는다.
- 프로젝트 전체 검색과 폴더 구조 재조사를 금지한다.
- 현재 작업에 지정된 파일만 읽는다. 추가 파일이 필요하면 파일명과 이유를 말하고 멈춘다.
- 전체 테스트, 전체 빌드, 패키지 설치를 자동 실행하지 않는다.
- 세션 종료 시 아래 "현재 작업"을 갱신한다.

### 현재 작업
- [2026-07-20] Render 실배포 진행 중. 남은 것: ①Render Environment Variables에 ANTHROPIC_API_KEY 등록 여부 혜미 확인 대기 ②webapp/DEPLOY_RENDER.md의 Root Directory 안내를 실제 우회법(Build/Start Command에 cd 넣기)으로 갱신 필요 ③이름 자동추출 정책 변경분(아래 "아직 안 된 것" 2026-07-20 항목)이 실 Render 배포에서 정상 동작하는지 실사용 확인 필요. 자세한 내용은 아래 "아직 안 된 것" 2026-07-20 항목 참고.

### 읽지 않을 범위
- 이 HANDOFF의 과거 이력 전체 / 4. Archive / outputs

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

1. ~~**kind:model 6개 전부 실 LLM 미연동**~~ → **해결 (2026-07-17)**. 혜미가 새로 발급한 진짜 Anthropic API 키를 `code/.env`(gitignore 대상, 이 파일은 절대 커밋되지 않음)에 저장 후, 6개 model stage 전부(`order_classification_bot`/`order_split_bot`/`correction_bot`/`order_draft_bot`/`ribbon_price_bot`/`review_manager_bot`) `*_ENGINE`을 실제 Claude 호출 버전으로 교체 완료. 공통 호출부는 신규 `code/llm_client.py`(tier→모델명 매핑, .env 로더, JSON 파싱). 각 봇은 `_xxx_llm`(진짜 호출) + `_xxx_auto`(LLM 우선 시도, 실패 시 기존 규칙기반으로 자동 대체 — 안전망) 구조. **실측 확인**: `order_classification_bot`/`order_draft_bot` 단독 호출 테스트 통과(특히 order_draft_bot은 "이름 절대 추측 금지" 원칙을 실제로 지킴 — 코드 레벨 이중 안전망까지 확인), 러너로 전체 14 stage 파이프라인을 진짜 LLM으로 2회 실행해 전부 OK 확인(2회차는 LLM이 규칙기반보다 더 신중하게 판단해 split_status=확인필요/product 미확정으로 사람에게 넘긴 것도 관찰 — "애매하면 안 채운다" 원칙이 실제로 작동). 이 과정에서 만들어진 테스트용 파일(`flower_orders.json`, 러너 로그/상태)은 실데이터가 아니므로 정리함.
2. **kind:human 1개 승인 UI 없음**: human_reviewer(사람 검수자) — 실제 검수 화면/버튼([검수저장]/[주문확정]/[출력준비]) 없음. run_pipeline.py는 데모 목적으로만 자동 통과시킴(실제 사람 승인 아님을 로그에 명시). 이번 작업(2026-07-14 model 4봇 구현)에서도 이 stage는 의도적으로 그대로 mock 유지. → ✅ 완료(2026-07-17, 근거: 아래 "다음 세션에서 이어받을 사람을 위한 시작점" 섹션 및 `webapp/app.py`) — 실제 저장되고 실제 AI가 판단하는 Flask 웹앱(`webapp/app.py`) 신설로 해소. 휴대폰 브라우저에서 새 문의 입력→AI 판단→검수 대기 목록→상세 확인/수정→승인(또는 반려)까지 진짜 동작함. 단, run_pipeline.py 자체의 데모용 자동승인 mock은 그대로 남아있음(별개 파일, 의도적으로 안 건드림).
3. transcription_bot의 STT/OCR — 실 API 키 미연동, 항등(identity) 목업.
4. sms_ledger_bot의 문자 발송 — 실 게이트웨이(알리고 등) 미연동, mock 항상 성공.
5. order_classification_bot/order_split_bot의 규칙기반 한계(003 오판정, call_007 자동 2분리 불가) — 2026-07-07부터 이미 문서화된 기존 한계, 새로 발견된 것 아님.
6. **[신규] order_draft_bot의 "미분리 원문 입력 시 필드 혼선" 한계**: order_split_bot이 call_007처럼 여러 주문을 하나로 남겨두면, order_draft_bot은 서로 다른 주문의 직함/기관명을 recipient/sender 두 슬롯에 뒤섞어 배정한다(test_order_draft_bot.py의 call_007 케이스에 재현돼 있음). order_split_bot이 실제 분리를 하게 되면 자동으로 해소될 문제 — order_draft_bot 자체를 고칠 필요는 없다.
7. **[신규] review_manager_bot의 review_priority 색상 매핑은 미확정 제안값**: 12봇_kind분류표.yaml open_questions에 "확인 필요"로 남아있던 항목을 이번 구현에서 구체적 규칙(빨강/노랑/파랑/초록 조건)으로 제안했지만, 실측 데이터로 검증된 것은 아니다 — review_manager_bot.py docstring 참고.
8. 12봇_kind분류표.yaml의 나머지 open_questions(위 "미해결" 참고) — 특히 order_draft_bot/order_classification_bot/order_split_bot의 tier가 실측 없이 제안값이라는 점.

**[2026-07-20, k9cjhmw7z9] Render 실사용 배포 + 이름 추출 정책 변경 + webapp UX 수정** — 혜미가 실제로 Render 배포를 진행하며 발견한 것들:
- Render 배포 완료(무료 플랜, `flower-shop-webapp.onrender.com`). Root Directory 칸이 한글 경로를 거부해서 Root Directory는 비워두고 Build/Start Command에 `cd "1. Projects/클로드 꽃집 ai/webapp" && ...`로 폴더 이동을 넣는 방식으로 우회(가이드 문서와 다른 실제 작동 방법 — `webapp/DEPLOY_RENDER.md`는 아직 원래 방식 그대로라 다음에 배포하는 사람은 이 우회법을 알아야 함, 문서 갱신 필요).
- 실사용 테스트 중 두 가지 문제 발견 및 수정: ①검수 화면에 recipient_org 등 영문 필드명이 그대로 노출됨 → `webapp/app.py`에 `FIELD_LABELS_KO` 한글 라벨 매핑 추가로 해결. ②받는 분 배송지가 항상 빈칸이던 것 → recipient_org+recipient_name이 있으면 "OOO OOO님" 형태로 기본값 제안(여전히 사람이 수정 가능)하도록 추가.
- **이름(recipient_name/sender_name) 추출 정책 변경(혜미 명시적 승인)**: 기존엔 golden_set 001 실사고(이름 뒤바뀜) 때문에 LLM이 이름을 채워도 코드로 강제 null 처리(이중 안전망)했는데, 혜미가 "자동 추출 켜되 이미 있는 사람 승인 단계를 안전장치로 삼자"고 승인해 `code/order_draft_bot.py`의 LLM 경로(`_draft_llm`)가 이제 이름도 위치 휴리스틱으로 추출을 시도한다. 강제 null 코드는 제거했고, 대신 field_confidence를 낮게(기본 0.4) 매겨 webapp 검수 화면에 "⚠ AI 추정치 - 꼭 확인" 경고가 뜨게 만들었다(신규 `LOW_CONFIDENCE_THRESHOLD` 로직, 값이 있어도 확신도 낮으면 경고). 규칙기반 폴백(`_draft_rule_based`, LLM 실패 시에만 탐)은 그대로 이름을 시도 안 함(정규식으로는 안전 판별 불가). `test_order_draft_bot.py` 4/4 통과 확인(로컬은 API 키 없어 폴백 경로만 검증됨 — 실 LLM 경로는 Render 실사용에서 확인 필요). 결정 서사는 `decision-log_12to14봇.md` 2026-07-20 항목 참고.
- 위 코드 변경을 커밋·푸시해 Render 자동 배포 트리거함(git push 성공 여부와 실제 Render 재배포 결과는 이 세션 마지막에 혜미가 확인).
- **다음 세션에서 이어받을 사람에게**: ①`ANTHROPIC_API_KEY`가 Render Environment Variables에 실제로 등록됐는지 혜미가 아직 확인 중이었음 — 확인 안 됐으면 LLM 경로가 전부 폴백돼 이름/기타 필드가 거의 안 채워짐. ②`webapp/DEPLOY_RENDER.md`의 "Root Directory: 1. Projects/클로드 꽃집 ai/webapp" 안내가 실제로는 안 먹혀서 위 우회법으로 배포했는데, 이 문서 자체는 아직 안 고쳤음 — 다음에 손대는 사람이 문서도 같이 갱신할 것.
- **[2026-07-20 추가] `llm_client.py`의 tier→모델명 오타 발견·수정**: `TIER_MODEL_MAP["low_cost"]`가 `"claude-haiku-4-5"`로 돼 있었는데, 정확한 모델 ID는 `"claude-haiku-4-5-20251001"`(날짜 접미사 필요)이다. 이 오타 때문에 low_cost tier를 쓰는 `order_draft_bot`/`ribbon_price_bot`의 API 호출이 (API 키가 있어도) 매번 실패해 조용히 규칙기반으로 폴백되고 있었다 — 혜미가 API 키를 등록했는데도 이름 자동추출이 안 되는 것처럼 보인 원인으로 추정됨. `mid` tier(`claude-sonnet-5`, correction_bot/order_classification_bot/order_split_bot/review_manager_bot이 씀)는 원래부터 정확했다. 수정 후 실사용 재확인 필요 - 다음 세션에서 이 커밋 배포 후 실제로 이름/금액/상품이 잘 채워지는지 꼭 확인할 것.
- **[2026-07-20 추가] 통화녹음 음성인식(STT) 신규 연동**: 혜미 요청("통화녹음도 가능해야지"). 확인 결과 Anthropic Claude API는 오디오 입력 미지원(2026-07 기준 공식 확인)이라 이미 있는 ANTHROPIC_API_KEY로는 안 되고, 별도로 OpenAI Whisper API를 새로 붙임(혜미가 OpenAI Whisper API를 선택). 신규 `code/stt_client.py`(llm_client.py와 동일한 안전망 패턴 - 키 없거나 실패하면 조용히 "음성인식 실패"로 폴백, 파이프라인은 안 깨짐), `transcription_bot.py`의 STT_ENGINE을 실 API 우선+폴백으로 교체, `webapp/app.py`에 "새 문의 입력" 화면에 녹음파일 첨부 칸 추가(문자 입력칸과 양자택일, 둘 다 비면 에러 메시지). 파일 크기 25MB 제한(Whisper API 자체 제한과 동일 + Render 무료 메모리 보호). 비용: whisper-1 모델 기준 분당 약 8원(0.006달러, 1350원/달러 환산) - 정확한 최신 가격은 https://openai.com/business/pricing/ 참고, 통화량 늘면 재추정 필요. **필요한 준비**: 혜미가 OpenAI 계정을 새로 만들고(AI가 대신 못 함) API 키 발급 후 Render Environment Variables에 `OPENAI_API_KEY`로 추가해야 동작(`webapp/DEPLOY_RENDER.md` 갱신됨) - 없어도 문자 입력 기능은 그대로 작동, 녹음파일 첨부만 "음성인식 실패" 메시지. `test_transcription_bot.py` 8/8 통과 유지, `run_pipeline.py` 전체 스모크 테스트도 통과 확인. OCR(사진 주문)은 여전히 미연동 상태 그대로(알려진 한계, 이번 작업 범위 밖).

## 다음 세션에서 이어받을 사람을 위한 시작점

**2026-07-17 갱신**: 위 우선순위 (a)(실 LLM 연동)는 완료됨(바로 위 "아직 안 된 것" 1번 참고). (b) human_reviewer 승인 UI도 같은 날 이어서 완료 — `webapp/app.py`(신규, Flask) 참고. **지금 여기서부터 시작하면 됨**: `webapp/DEPLOY_RENDER.md`를 따라 Render에 배포(혜미가 직접 계정 가입 필요)한 뒤 실사용 시작. 그 다음으로는 golden_set.yaml 5개 케이스 전체로 실 LLM 회귀 테스트를 돌려서 규칙기반 버전과 결과가 어떻게 달라지는지 표로 정리하는 것(001/005/006처럼 결과가 달라지는 건 정상이니 "달라짐=버그"로 오판하지 말 것 — 오히려 LLM이 규칙기반보다 더 신중하게 판단하는 사례를 이번에 이미 1건 관찰함).

**꽃집 human_reviewer 승인 UI 실제 연결 완료 (2026-07-17)**: `webapp/app.py` 신설 — 휴대폰 브라우저에서 새 문의를 입력하면 `collection_bot`~`review_manager_bot`까지 실제로 실행해 검수 대기 목록에 올리고, 상세 화면에서 값을 확인/수정 후 승인을 누르면 `storage_bot`~`sms_ledger_bot`까지 실제로 실행하는 **진짜 동작하는 웹앱**(승인화면_프로토타입_v1.html은 정적 목업이었던 것과 다름). `code/` 폴더의 봇 파일은 한 글자도 안 고침(run_pipeline.py/flower_adapter.py와 동일한 sys.path 재사용 원칙). 로컬에서 실제 API 호출로 스모크 테스트 완료(대기 등록→상세 조회→승인→저장까지 전체 흐름 확인, 테스트 데이터는 정리함). Render 무료 서버 배포 가이드(`webapp/DEPLOY_RENDER.md`)까지 작성 — 계정 가입은 혜미가 직접 해야 하는 부분이라 남겨둠.
알려진 한계(그대로 문서화): 다중 주문 감지 시 첫 세그먼트만 처리(flower_adapter.py 발견사항 3과 동일), 3단계 승인(검수저장/주문확정/출력준비) 대신 1단계로 단순화, 동시 접속 충돌 처리 없음(1인 운영 가정).

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
