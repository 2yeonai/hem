---
type: entry-point
tags: [ai공장, ai운영체제, 지침]
created: 2026-07-15
---
# START-HERE.md — 새 세션이 제일 먼저 읽는 문서

> ⚠️ 재구성 안내: 2026-07-15 세션 원본 유실로 인한 v1 재구성본.

## 읽는 순서 (새 Claude 세션 시작 시)
1. **`CLAUDE.md`(볼트 루트)** — 전체 구조, Gotchas, 혜미와의 소통 규칙
2. **`2. Areas/핵심맥락.md`** — 혜미가 누구고 지금 뭘 하고 있는지
3. **이 문서 이후 → [[ai공장짓기/AI운영체제_설계서|AI운영체제_설계서]]** — 일이 어떻게 조직되는지(ORCHESTRATION-LAYER/routing-policy/TASK-PACKET/RESULT-CARD)
4. **최신 [[2. Areas/Claude 세션로그|세션로그]]** — 어제/오늘까지 어디까지 했는지, "이어서 해줘"의 근거
5. 그 다음에야 구체적 작업 폴더(`ops/tasks/`, 각 프로젝트 폴더)로 들어간다

## "이어서 해줘"를 받았을 때
`0. Docs/명령어_사전.md` 규칙대로: 최신 세션로그 + 해당 폴더 HANDOFF를 읽고 기록된 지점부터 재개. 이번 문서(START-HERE)가 그 첫 진입점 역할을 한다 — 세션로그만 보고 바로 작업 시작하지 말고, 이 순서를 한 번 거치면 맥락 누락을 줄일 수 있다.

## Fable 종료 시 승계 절차 (§18 거버넌스 참고)
Fable 서비스가 종료되면 승계자는 **Claude Code/Cowork의 Opus+Sonnet 조합**. 절차는 "이 설계서 + `ai공장짓기/decision-log_skill-factory-architecture.md` 읽기"로 끝 — 별도 인수인계 세션 없이 이 문서들만 읽으면 이어갈 수 있게 만드는 것이 목적.

## 신규 아이디어가 떠올랐을 때
바로 실행하지 말고 inbox(`_inbox/` 또는 `5. Zettelkasten/00. Inbox/`)에 적립 — 분기 단위로 반영 검토(§18 거버넌스). 예외: 혜미가 명시적으로 "지금 바로 착수해도 된다"고 승인한 건(예: 2026-07-14 옛날옛적에 공장 1건).

## 관련 문서
- [[CLAUDE|루트 CLAUDE.md]]
- [[2. Areas/핵심맥락|핵심맥락]]
- [[ai공장짓기/AI운영체제_설계서|AI운영체제_설계서]]
- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]]
- [[0. Docs/명령어_사전|명령어_사전]]

<!-- ok -->
