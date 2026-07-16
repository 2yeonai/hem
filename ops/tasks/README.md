---
type: ops-folder-readme
tags: [ai공장, ai운영체제, 지침]
created: 2026-07-15
updated: 2026-07-15
---
# ops/tasks/ — 작업 폴더

> 2026-07-15 정정: 이 폴더 규칙은 처음에 유실 추정으로 잘못 재구성했다가, 혜미가 실제 원본(`AI_OS_설계서.md`·`START-HERE.md`·`ORCHESTRATION-LAYER.md`·`templates/TASK-PACKET.md`·`templates/RESULT-CARD.md`)을 직접 제공해 정정함. 아래는 그 원본 기준.

## 규칙 (원본 기준)
- 작업 1건당 폴더 1개: `ops/tasks/{오늘날짜}_{작업명}/`
- 폴더 안 파일은 접두 번호로 진행 상태를 나타낸다(폴더만 봐도 상태가 보이는 것이 목적):
  - `00_PACKET.md` — [[templates/TASK-PACKET|TASK-PACKET]] 양식으로 작성한 작업 발주서
  - `10_`, `13_` 등 `1x_` — 병렬로 나눈 파생 패킷(비범위가 서로 배타적이어야 함)
  - `2x_RESULT-{도구}.md` — 각 실행 AI가 돌려준 [[templates/RESULT-CARD|RESULT-CARD]]
  - `90_FINAL.md` — 카드가 2장 이상일 때 총괄(ChatGPT)이 종합한 최종본(상충 판정 포함)
  - `99_APPROVED.md` — 혜미 승인 한 줄 메모
- 완료된 폴더는 삭제하지 않고 보관 — 재사용 가치 있는 결정은 `ai공장짓기/decision-log_skill-factory-architecture.md`로 승격.
- 저난도·단발·되돌릴 수 있는 작업은 패킷 생략 가능 — 기준은 [[START-HERE|START-HERE]] 예외 규칙 참고("결과가 틀려도 5분 안에 다시 시킬 수 있는가?").

## 관련 문서
- [[START-HERE|START-HERE]] (배치: 루트)
- [[ai공장짓기/AI_OS_설계서|AI_OS_설계서]] §9 폴더 구조
- [[ai공장짓기/ORCHESTRATION-LAYER|ORCHESTRATION-LAYER]]
- [[prompts/routing-policy|routing-policy]]
- [[templates/TASK-PACKET|TASK-PACKET]] · [[templates/RESULT-CARD|RESULT-CARD]]
- [[ops/usage|usage]]

## 현재 상태 (2026-07-15)
비어 있음 — 아직 이 규칙으로 쌓인 실제 작업 폴더가 없음. 다음 실전 작업부터 적용 시작.

<!-- ok -->
