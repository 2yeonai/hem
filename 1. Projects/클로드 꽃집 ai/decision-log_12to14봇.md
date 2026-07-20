---
tags: [꽃집, ai공장, decision-log]
created: 2026-07-12
---

# decision-log: 꽃집 12봇 → 14봇 결정 서사 (소급 정리, 2026-07-12)

> 흩어져 있던 결정 근거(12봇_kind분류표 주석, 실데이터 diff 로그 #1·#2, Fable 결정 2026-07-06)를 한 곳에 모음. 원본이 정본, 이 노트는 서사 요약.

## 타임라인

1. **2026-07-06 (Fable 5 결정)** — kind는 local/model/human 세 값만. 12봇 파이프라인 골격 확정. 검수매니저 tier는 답변에서 누락 → Sonnet 5가 "판단 복잡도 기준 haiku/sonnet 중 결정"으로 보완.
2. **2026-07-07 (실데이터 diff 로그 #2)** — 실제 주문 데이터 대조 중 두 가지 구멍 발견:
   - 주문이 아닌 문의/잡담이 파이프라인에 흘러듦 → **order_classification_bot(주문판정봇)** 신설 (false-positive 방지)
   - 한 메시지에 여러 주문이 섞임 → **order_split_bot(주문분리봇)** 신설 (다중주문 분리)
   - 배치 논점: 혜미는 "수집봇 다음"을 원했으나 텍스트가 있어야 판정 가능 → transcription_bot 다음으로 배치 (이견 시 변경 가능으로 남김)
   - fan-out 논점: 분리된 주문들 병렬 처리 대신 **순차 처리**로 결정 — bundle_id/sequence/status 필드 신설
3. **파일명은 "12봇" 유지** — 기존 참조 안 깨지게. 실제는 14 stage (local 7 / model 6 / human 1).
4. **2026-07-14 — 나머지 local 6봇 구현 + run_pipeline.py 완성.** 상세는 아래 "2026-07-14 갱신" 섹션 참고.

## 왜 이 확장이 "설계 실패"가 아니라 "정상 작동"인가
골든셋(실데이터)이 설계를 이긴 사례 — 책상 설계로는 못 본 구멍을 실데이터 6건이 바로 드러냄. 방역 골든셋 수집을 서두르는 이유와 동일한 원리. → 영구노트 후보: "골든셋은 설계를 이긴다".

## 2026-07-14 갱신 — local 6봇 신규 구현 + run_pipeline.py

12봇_kind분류표.yaml을 다시 정독해 kind: local 7개(collection_bot, transcription_bot, storage_bot, print_prep_bot, dispatch_bot, delivery_photo_bot, sms_ledger_bot) 중 storage_bot을 제외한 **6개를 신규 구현**했다(storage_bot은 2026-07-12 이전에 이미 구현·테스트 완료 상태였음).

- `code/collection_bot.py` — 채널 원본을 그대로 shared_context에 담음. source_type 검증 + "raw_* 전부 없으면 거부"(원본 소실 금지)만 판단. 테스트 8/8 PASS.
- `code/transcription_bot.py` — STT/OCR을 호출하는 자리. **알려진 한계**: 실제 STT/OCR API 키가 이 환경에 없어 STT_ENGINE/OCR_ENGINE은 항등(identity) 목업(입력을 그대로 텍스트로 반환) — engine_meta.real_api_connected=False로 숨기지 않고 명시. cleaned_text는 연속 공백 정리 등 최소 정리만 하고 의미 보정(말귀봇 몫)은 하지 않음. 테스트 8/8 PASS.
- `code/print_prep_bot.py` — 확정 주문에서 주문서/리본/배송메모/기사요약 4종 생성. 값이 None이면 "확인 필요"로 표시하고 임의로 채우지 않음. golden_set 필드명이 항목마다 다른 문제(001은 recipient_org, 006은 recipient_title)를 여러 후보 필드명 fallback으로 흡수. 테스트 9/9 PASS.
- `code/dispatch_bot.py` — 기사 화면 라우팅 기록(dispatch_record) 생성, driver_id 없으면 "미배정". 테스트 6/6 PASS.
- `code/delivery_photo_bot.py` — 배송사진 촬영 흐름 mock(photo_uri 있으면 완료, 없으면 대기). 실제 카메라 연동 없음(알려진 한계). 테스트 4/4 PASS.
- `code/sms_ledger_bot.py` — 문자 발송(mock, 알리고 등 실제 게이트웨이 미연동) + storage_bot.get_bundle_status() 재사용으로 bundle_status(진행중/완료) 계산. 테스트 5/5 PASS(005만 저장 시 진행중 → 006까지 저장 시 완료로 전환 확인).
- `code/run_pipeline.py` — 신규. 12봇_kind분류표.yaml의 depends_on을 위상정렬해 14 stage 실행 순서를 코드에 하드코딩하지 않고 계산. kind:local은 실제 함수 호출, 이미 구현된 kind:model 2개(order_classification_bot/order_split_bot)는 규칙기반 버전을 실제로 호출, 아직 미구현인 kind:model 4개(correction_bot/order_draft_bot/ribbon_price_bot/review_manager_bot)와 kind:human(human_reviewer)은 로그만 남기고 값을 임의로 채우지 않은 채(None/원문 그대로) 통과시킴. order_segments는 fan-out이 아니라 순차 loop로 처리(2026-07-07 결정 그대로). golden_set 6건(= 001/002/003/004/005·006 5케이스, 005·006은 같은 call_007 원문 공유 — 기존 테스트들과 동일 관례) 전체 실행 결과: 001·005/006은 끝까지 진행(order 저장·인쇄·배송·문자·장부 전부 통과), 002·004는 stop_condition(일반통화)에서 정상 종료, 003은 order_classification_bot의 기존 알려진 한계(문맥 못 읽음)로 인해 끝까지 진행됨 — test_order_classification_bot.py의 KNOWN_LIMITATIONS과 동일한 케이스라 새로운 버그 아님. 최종 "전체 파이프라인 스모크 테스트: PASS(알려진 한계 1건 제외)".

**환경 이슈 재현**: run_pipeline.py 및 이 노트 자체를 작성하는 과정에서 Edit/Write 도구 모두 CLAUDE.md에 문서화된 mid-byte 잘림 버그가 재현됨(한글 멀티바이트 문자 중간에서 파일이 끊김, `wc -c`로 바이트 수 불일치 확인). 규칙대로 `.stale-<timestamp>`로 rename 후 bash heredoc으로 전체 재작성해 복구 — `code/run_pipeline.py.stale-1783960900`, `decision-log_12to14봇.md.stale-1783961098`로 백업 남아있음(삭제하지 않음). 이번 세션에서는 Write 도구도 truncation을 일으키는 것을 새로 확인함 — 기존 문서는 "Edit 도구"만 언급했으나 범위가 Write까지 넓다.

**남은 미구현(범위 밖, 알려진 한계로 명시)**: correction_bot/order_draft_bot/ribbon_price_bot/review_manager_bot(kind:model, sonnet/haiku 실제 LLM 호출 없음)과 human_reviewer(kind:human, 실제 사람 승인 UI 없음) — 전부 run_pipeline.py에서 로그만 남기는 mock 상태. 이 4개 model stage에 실제 LLM을 붙이면 order_draft/ribbon/review_checklist 등의 필드가 채워지고, 그때 storage_bot 저장 결과의 확인_필요_필드 구성도 달라질 것으로 예상됨(지금은 mock이라 거의 모든 필드가 확인_필요로 표시됨 — 이것도 "임의로 채우지 않는다" 원칙이 정확히 지켜지고 있다는 증거로 봄).

**별도 발견(이번 작업 범위 밖, 알려드리기만 함)**: 프로젝트 루트의 `HANDOFF.md`는 여전히 gov-support-matching-skill 내용이다(CLAUDE.md Gotchas에 이미 문서화된 문제). 2026-07-13 R4 정리에서 SKILL.md·manifest.yaml·scripts/·test/·gov-support-skill/은 `4. Archive/꽃집폴더_정부지원사본_2026-07/`로 이미 이동됐는데 HANDOFF.md만 그때 빠진 것으로 보인다(이동 안 되고 루트에 그대로 남음). 이번 작업 결과는 이 노트와 `최종점검_리포트_2026-07-14.md`에 기록했고, 잘못 남은 HANDOFF.md는 건드리지 않았다 — 필요하면 다음 세션에서 R4와 같은 방식(Archive로 이동)으로 마저 정리 권장.

## 현재 코드 상태 (2026-07-14 실측)
- 구현 완료+테스트 전부 PASS: storage_bot, order_classification_bot(4/5, 1건은 알려진 한계), order_split_bot(사람 인계까지가 목표), collection_bot(8/8), transcription_bot(8/8), print_prep_bot(9/9), dispatch_bot(6/6), delivery_photo_bot(4/4), sms_ledger_bot(5/5) — kind:local 7개 전부 구현 완료.
- run_pipeline.py로 14 stage 전체가 golden_set 6건 기준 end-to-end 1회 이상 정상 실행됨(위 요약 참고).
- 14봇 yaml: v2 스키마 검증 PASS(기존 상태 유지, 이번에 변경 없음).
- 미구현: kind:model 6개 중 4개(correction_bot/order_draft_bot/ribbon_price_bot/review_manager_bot)와 kind:human 1개(human_reviewer) — 전부 실 LLM/실 사람 승인 UI 없이 mock 로그만.

## 미결(open_questions 요약 — 원본: 12봇_kind분류표.yaml)
transcription_bot kind 불일치 / order_draft·review_manager·신규 2봇 tier 실측 없음 / human_reviewer 반려-복귀 UX 정합 / confidence 색상→수치 매핑 / bundle_status와 실제 DB 스키마 정합(구현 단계 재확인 — 2026-07-14 기준 JSON 파일 DB로 실측 완료, 별문제 없음 확인)

## 2026-07-20 갱신 — order_draft_bot 이름(recipient_name/sender_name) 추출 정책 변경 [k9cjhmw7z9]

**배경**: 혜미가 Render에 실제로 웹앱을 배포하고 첫 실사용 테스트를 하던 중("창녕군의회 이수진. 승진축하 창녕군시설관리공단 문정훈 10만원 난"), 검수 화면에서 받는사람/보내는사람 이름이 항상 비어있고 매번 손으로 채워야 하는 걸 보고 "이것도 직접추출"(자동 추출로 바꿔달라)이라고 요청함.

**충돌**: 기존 설계(2026-07-06~07-17에 걸쳐 반복 확인·강화된 원칙)는 golden_set 001의 실사고(스크린샷/타이핑 버전에서 받는사람/보내는사람 이름이 실제로 뒤바뀐 사례) 때문에 "이름은 절대 자동 채우지 않는다"를 프롬프트+코드 이중 안전망으로 강제하고 있었음(webapp 승인 UI 신설 완료 보고 시점에도 "코드 레벨 이중 안전망까지 확인"이라고 재확인된 결정이었음, HANDOFF.md 참고).

**판단(Sonnet 5, 세션 내 확인 후 진행)**: 이건 안전 원칙 자체를 버리는 게 아니라 안전장치의 위치를 옮기는 결정이라고 봄 — 예전엔 "이름을 아예 못 채우게" 코드가 막았지만, 지금은 webapp에 이미 "사람이 승인 화면에서 확인 후 승인 버튼을 눌러야만 실제 처리(저장~문자발송)가 진행되는" 인간 승인 게이트가 실제로 존재한다(2026-07-17 완료). 즉 자동 채움 값이 틀려도 사람이 승인하기 전에 걸러질 구조적 안전망이 이미 있으므로, "AI가 추정값을 제시 + 확신도 표시 + 사람이 최종 확인"으로 바꿔도 golden_set 001급 사고(사람이 확인 안 하고 그대로 승인)는 다른 층위(사람의 검수 습관)의 문제이지 이 봇의 설계 문제가 아니라고 판단. 다만 되돌릴 수 없는 실사고 이력이 있는 규칙이라, 사용자(혜미)에게 정확히 이 트레이드오프(편해지지만 뒤바뀔 위험 재발)를 설명하고 명시적 승인을 받은 뒤에만 진행함(AskUserQuestion으로 확인, 답변: "자동 추출로 변경, 승인해야 처리되니까 안전장치 있음").

**변경 내용**: `code/order_draft_bot.py` — LLM 경로(`_draft_llm`) 시스템 프롬프트에서 "이름 절대 채우지 마세요" 절대 규칙을 "다른 필드와 같은 위치 휴리스틱(pivot 앞/뒤)으로 이름도 채워보되, 애매하면(후보 3개 이상, 순서 불명확 등) null로"로 완화. 코드의 강제 null 오버라이드는 제거하고, 대신 모델이 이름을 채웠는데 confidence를 안 줬으면 보수적으로 0.4를 기본값으로 매기게 함. 규칙기반 폴백(`_draft_rule_based`, LLM 실패시만 탐)은 그대로 이름 시도 안 함(정규식으로는 안전 판별 근거 없음 — 유지). `webapp/app.py`에 field_confidence를 검수 화면까지 전달해 confidence < 0.6인 필드는 값이 있어도 "⚠ AI 추정치 - 꼭 확인" 경고를 뜨게 만들어, 이름 필드가 채워져도 사람이 확인하도록 시각적으로 강조함. `test_order_draft_bot.py` 4/4 통과 유지(로컬은 API 키 없어 규칙기반 폴백 경로만 검증 — LLM 경로의 실제 이름 추출 정확도는 Render 실사용에서 검증 필요, 다음 세션 확인 권장).

**재사용 가능성(extract-approach 대상 여부 검토)**: "자동화 vs 안전"의 트레이드오프를, 안전장치를 없애는 게 아니라 이미 존재하는 사람 승인 게이트로 위치를 옮겨서 재해결한다는 패턴은 방역/정부지원 등 다른 공장의 "AI 추정값 + 사람 최종 확인" 구조에도 재사용 가능한 일반 원칙으로 보임 — 영구노트화는 다음 세션에서 혜미에게 제안 예정(이번 세션은 시간 관계상 보류).

## 관련 문서
- [[1. Projects/클로드 꽃집 ai/실데이터_diff_로그_001|diff_로그_001]] · [[1. Projects/클로드 꽃집 ai/실데이터_diff_로그_002|diff_로그_002]] · [[1. Projects/클로드 꽃집 ai/최종점검_리포트_2026-07-07|최종점검_리포트_2026-07-07]] · [[1. Projects/클로드 꽃집 ai/최종점검_리포트_2026-07-14|최종점검_리포트_2026-07-14]] · [[ai공장짓기/decision-log_skill-factory-architecture|플랫폼 decision-log]] · [[2. Areas/핵심맥락|핵심맥락]] · [[5. Zettelkasten/20. Permanent/골든셋은 설계를 이긴다|골든셋은 설계를 이긴다(영구노트)]] · [[LLM위키_홈]]

<!-- ok -->
