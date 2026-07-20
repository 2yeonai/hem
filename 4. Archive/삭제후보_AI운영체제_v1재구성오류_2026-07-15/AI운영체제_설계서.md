---
type: design-doc
tags: [ai공장, ai운영체제, 지침]
created: 2026-07-15
version: v1-재구성
---
# AI운영체제(Operating System) 설계서

> ⚠️ **재구성 안내 (맨 위 고정)**: 2026-07-15 세션에서 "설계서 §8·§9 정합 + §18 거버넌스 신규 추가"까지 완료했다고 세션로그에 기록됐으나, 실제 파일이 볼트에 저장되지 않은 채 세션이 끝나 유실됨. §1~§17에 해당하는 원본 내용도 전혀 남아있지 않아, 이 문서는 그 원본의 "복구"가 아니라 **처음부터 새로 구성한 v1**이다. 세션로그의 요약 한 단락(2026-07-15.md)과 볼트 기존 규칙(decision-log, ai공장짓기/CLAUDE.md, 명령어_사전 등)을 근거로 재구성했다. 원본과 문구·세부 조항이 다를 수 있으니 혜미 검토 후 확정할 것.

## 1. 목적
개별 공장(꽃집/방역/정부지원/콘텐츠 등)의 manifest.yaml이 "그 공장 안에서 문의 하나가 어떻게 처리되는가"를 다루는 것과 달리, 이 설계서는 **Claude 세션 자체가 여러 공장/여러 요청에 걸쳐 어떻게 일을 조직하는가**를 다룬다. 공장이 "제품 라인"이라면 이 설계서는 "공장 전체를 운영하는 본사 규정"에 해당.

## 2. 계층 구조
| 계층 | 문서 | 역할 |
|---|---|---|
| 진입점 | [[ai공장짓기/START-HERE|START-HERE]] | 새 세션이 제일 먼저 읽는 순서 안내 |
| 흐름도 | [[ai공장짓기/ORCHESTRATION-LAYER|ORCHESTRATION-LAYER]] | 요청 → PRD/PACKET → 실행 → RESULT-CARD → 승인의 전체 흐름 |
| 모델 라우팅 | [[ai공장짓기/routing-policy|routing-policy]] | Haiku/Sonnet/Fable 중 무엇을 쓸지 |
| 작업 단위 | [[ai공장짓기/TASK-PACKET_v1|TASK-PACKET_v1]] | "일" 하나의 정의 양식 |
| 결과 기록 | [[ai공장짓기/RESULT-CARD_v1|RESULT-CARD_v1]] | "일"이 끝났을 때 남기는 기록 양식 |
| 자원 관리 | [[ai공장짓기/usage.md|usage.md]] | 세션 한도 신호등 |

## 3. 폴더 구조 (실제 파일 배치와 일치)
```
hem/ (볼트 루트)
├── CLAUDE.md                          ← 전체 규칙, START-HERE보다 먼저 읽음
├── ai공장짓기/                         ← 이 설계서와 하위 정책 문서들
│   ├── AI운영체제_설계서.md            (이 문서)
│   ├── START-HERE.md
│   ├── ORCHESTRATION-LAYER.md
│   ├── routing-policy.md
│   ├── TASK-PACKET_v1.md
│   ├── RESULT-CARD_v1.md
│   ├── usage.md
│   └── decision-log_skill-factory-architecture.md
├── ops/
│   └── tasks/                         ← v1부터: 실제 작업 폴더 (구 reports/ 대체)
│       └── <날짜>_<식별자>/
│           ├── packet.md              (TASK-PACKET)
│           └── result-card.md         (RESULT-CARD)
├── 1. Projects/클로드 방역 ai/ 등      ← 개별 공장 (manifest.yaml 레이어, 이 설계서와 별개 층위)
└── 2. Areas/Claude 세션로그/           ← 세션 단위 기록 (TASK-PACKET보다 상위 단위)
```
과거 표현이었던 `reports/` 폴더·"결과카드"는 v1부터 각각 `ops/tasks/`와 RESULT-CARD로 전면 교체한다. 이전 세션 기록에서 그 표현이 나오면 이 매핑으로 읽는다.

## 4. PRD ↔ TASK-PACKET 계층 관계
- **PRD**(Product Requirement Doc): 여러 단계·여러 산출물이 필요한 큰 단위 작업의 요구사항 정의. 예: "AI 운영체제 v1 구축" 자체가 PRD 하나가 될 수 있음.
- **TASK-PACKET**: 실행 가능한 최소 단위. **1 PRD → n TASK-PACKET** (하나의 PRD가 여러 패킷으로 쪼개짐).
- **단발 업무**(예: "이 파일 하나 고쳐줘")는 PRD를 만들지 않고 **TASK-PACKET 하나만** 바로 생성해 시작한다 — 모든 일에 PRD를 강제하지 않음, 오버헤드 방지가 목적.
- 판단 기준: 산출물이 2개 이상이거나, 여러 세션에 걸칠 것으로 예상되면 PRD 먼저. 아니면 패킷만.

## 5. 오늘(2026-07-15) 재구성에서 실제로 있었던 일
- 원래 세션에서 있었다고 기록된 작업: "§8·§9 구버전 잔재(`reports/`·결과카드)를 v1 규약으로 전면 교체", "폴더 구조도를 실제 파일 배치와 일치", "PRD↔TASK-PACKET 계층 관계 정의", "§18 거버넌스 신규 추가", "usage.md 신규 추가".
- 위 내용은 **모두 이번 재구성본(§3, §4, §7)에 반영**했다 — 다만 이건 "복구"가 아니라 요약 문장 하나를 근거로 새로 쓴 것이라는 점을 다시 강조.
- 8개 파일 세트(설계서/ORCHESTRATION-LAYER/START-HERE/routing-policy/TASK-PACKET v1/RESULT-CARD v1/usage/프로젝트 CLAUDE.md) 중 프로젝트 CLAUDE.md 연동은 전면 재작성 대신 루트·ai공장짓기 CLAUDE.md에 짧은 참조 링크만 추가하는 것으로 범위를 좁혔다(개별 공장 4곳 CLAUDE.md까지 전부 새로 쓰는 건 원본에 없던 확대 해석 위험이 있다고 판단).

## 6. Fable 감사 대기 상태
7/15 원본과 동일하게, 이 v1 재구성본도 구조 결정(§4 PRD/PACKET 계층, §7 거버넌스)을 포함하므로 **ChatGPT 감사 대기 상태**로 둔다. [[ai공장짓기/RESULT-CARD_v1|RESULT-CARD_v1]]의 감사 3항목 기준으로 검토 요청할 것 — 단, 그 3항목 자체도 이번에 임의로 채운 추정값이라 먼저 혜미 확인이 필요.

## 7. §18 거버넌스
> 원본 세션로그에 "§18"로 명명되어 있어 번호를 그대로 유지함(§1~§17은 존재하지 않는 재구성본이라 이 문서 안에서는 실질적으로 §7이지만, 원본과의 대응을 위해 제목에 §18 표기를 병기).

**기획·구현**: Claude 단독 수행 (구조 결정이 필요한 부분은 현재 Fable 티어 — [[ai공장짓기/routing-policy|routing-policy]] 기준, 승인 후).

**ChatGPT의 역할**: 완성본 감사만, 아래 3항목 한정.
> ⚠️ 재구성 추정 — 원본 3항목 문구가 세션로그에 남지 않아 임의로 채움, 확인 필요.
> 1. 논리적 일관성(기존 decision-log와 모순 없는지)
> 2. 위험 신호(되돌리기 비싼 결정·안전/저작권/개인정보 누락 여부)
> 3. 완료 조건 누락 확인

**사용자(혜미)의 역할**: 승인만. 새 아이디어는 즉시 실행하지 않고 inbox(`_inbox/` 또는 `5. Zettelkasten/00. Inbox/`)에 적립 후 **분기 단위**로 반영 검토. 예외는 혜미가 명시적으로 즉시 착수를 승인한 건(예: 2026-07-14 옛날옛적에 공장).

**Fable 종료 시 승계 계획**: 승계자는 **Claude Code/Cowork의 Opus+Sonnet 조합**. 절차는 "이 설계서 + `ai공장짓기/decision-log_skill-factory-architecture.md`를 읽는 것"으로 종료 — 별도 인수인계 세션을 만들지 않는 것이 원칙.

## 8. 알려진 한계 (이 재구성본 자체의)
- §1~§17에 해당하는 원본 내용을 전혀 모른 채 쓴 v1이라, 원본과 실제로 겹치는 부분이 얼마나 되는지 알 수 없음.
- ChatGPT 감사 3항목(§7), usage.md 신호 격상 임계값은 순수 추정치.
- 개별 공장 4곳(꽃집/방역/정부지원/콘텐츠)의 CLAUDE.md는 이번에 손대지 않음 — 필요하면 별도 TASK-PACKET으로 진행.
- `ops/tasks/` 폴더는 만들었지만 아직 실제 TASK-PACKET이 하나도 없는 빈 상태.

## 관련 문서
- [[ai공장짓기/START-HERE|START-HERE]]
- [[ai공장짓기/ORCHESTRATION-LAYER|ORCHESTRATION-LAYER]]
- [[ai공장짓기/routing-policy|routing-policy]]
- [[ai공장짓기/TASK-PACKET_v1|TASK-PACKET_v1]]
- [[ai공장짓기/RESULT-CARD_v1|RESULT-CARD_v1]]
- [[ai공장짓기/usage.md|usage.md]]
- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]]
- [[2. Areas/Claude 세션로그/2026-07-15|세션로그 2026-07-15(유실 발견 기록)]]

<!-- ok -->
