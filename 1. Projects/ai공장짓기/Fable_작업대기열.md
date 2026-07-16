---
type: queue
created: 2026-07-12
tags: [ai공장, 프롬프트, 지침]
---

# Fable 작업대기열 — 비싼 모델에만 시킬 일 #ai공장

> 규칙: 여기 있는 것만 Fable(승인 후). 나머지는 전부 Sonnet 이하.
> 실행 후에는 결과를 decision-log에 기록하고 이 목록에서 지운다.

## 대기 중 (우선순위 순)
| # | 작업 | 시점 | 왜 Fable인가 | 프롬프트 위치 |
|---|---|---|---|---|
| F1 | 정부지원 스크래핑 설계 | **지금 (혜미 승인 2026-07-16, 원래는 8월 예정이었음)** | 외부 의존 구조 결정 — 실수 비용 큼. T3(mo,on) 실행에서 "웹서치로 후보는 찾았지만 전부 마감 지남"이 실제로 발생해 필요성 재확인됨 | 바로 아래 "F1 카드" 섹션 |
| F2 | mock→실제 AI 호출 전환 설계 | 9월 | 비용 구조·모델 라우팅이 걸린 플랫폼 결정 | 신규 — 그때 카드 작성 |
| F3 | 방역 미정 봇 3개 최종 판정 | 골든셋 후 **충돌 시에만** | 골든셋 근거가 기존 설계와 모순될 때만 | [[1. Projects/완전자동화_실행계획|실행계획]] 2단계 |
| F4 | 신규 공장 착수 전 설계 재감사 (9월, 1회) | 9-1 직전 | 2개월 지난 설계의 blind-spot 점검 | 설계노트/공장별 노트 첨부해 감사 요청 |

## F1 카드 (정부지원 스크래핑 설계 — 2026-07-16, 혜미 승인, Fable 세션에 그대로 붙여넣기)

```yaml
cards:
  - id: c1
    type: fact
    summary: 감사_로드맵_2026-07-09.md R5는 "정부지원 스크래핑 설계는 Fable, 구현은 Sonnet"이라며 4개 질문(대상 공고 사이트 목록 / 수집 주기 / 실패 시 재시도 정책 / 수집물→매칭 스킬 io_contract)을 그대로 물으라고 지정해둠. 원래 시점은 "R1~R3 완료 후, 8월"이었음.
    evidence: "1. Projects/ai공장짓기/감사_로드맵_2026-07-09.md R5 섹션 원문"
    confidence: 1.0
  - id: c2
    type: fact
    summary: 정부지원사업 매칭 스킬은 현재 scripts/real_announcements.json(사람이 수동으로 구조화한 공고 3건, 전부 마감 지남)만 참조하는 목업 상태 - SKILL.md "알려진 한계"에도 명시. 실시간 공고 수집기가 없어 새로 뜬 공고를 스스로 찾지 못함.
    evidence: "1. Projects/클로드 정부지원사업 ai/mo,on_예비창업패키지/신청서초안_2026-07-14.md"
    confidence: 1.0
  - id: c3
    type: fact
    summary: 2026-07-16 T3 세션에서 실제로 WebSearch로 mo,on이 지원할 만한 공고를 여러 건 찾았으나(기업마당/K-스타트업/경남·진주시), 확인해보니 전부 마감이 지났거나(대부분 1~5월 마감) 이 스킬 구조(사업계획서 심사형)에 안 맞는 유형(공모전 등)이었음 - "지금 이 시점에 접수 중인 공고"를 안정적으로 찾을 방법이 없다는 R1~R3 단계의 실측 확인.
    evidence: "1. Projects/클로드 정부지원사업 ai/mo,on_예비창업패키지/상태메모_2026-07-16_공고탐색결과.md"
    confidence: 0.9
  - id: c4
    type: unknown
    summary: R5가 지정한 4개 질문(사이트 목록/수집주기/재시도정책/io_contract) 중 어느 것도 아직 답이 없음 - 이번 Fable 세션의 실제 산출물이 돼야 함.
    confidence: 1.0
open_questions:
  - "대상 공고 사이트 목록: 기업마당(bizinfo.go.kr)/K-스타트업/경남·진주시 지자체 공고 중 어디까지 포함할지, 우선순위는?"
  - "수집 주기(triggers.schedule): 하루 몇 회? 실시간에 가까울 필요가 있는지, 일 1회로 충분한지?"
  - "실패 시 재시도 정책: 대상 사이트가 구조를 바꾸거나 접근 실패 시 몇 회/몇 분 간격으로 재시도, 이후 사람에게 어떻게 알릴지?"
  - "수집물→매칭 스킬 io_contract: scripts/real_announcements.json과 같은 스키마(eligibility/exclusion_conditions/required_documents/budget_criteria/scoring_rubric)로 자동 변환 가능한지, 사람 검수 게이트가 어디에 들어가야 하는지?"
should_escalate_to_fable: true
escalate_reason: "architecture_decision — 외부 사이트 의존 구조 설계, 실수 비용 큼(R5 원래 지정 사유). 혜미가 시점을 8월에서 지금으로 앞당기는 것을 명시적으로 승인함(2026-07-16)."
```

```json
{"why_fable": true, "reason": "architecture_decision — 정부지원 공고 스크래핑 파이프라인 설계, 외부 의존", "cheaper_model_attempted": false, "input_tokens_estimate": 1800, "raw_attached": false}
```

## 처리 완료 (decision-log로 이관)

- ~~F5 꽃집 manifest.yaml 방향 결정~~ — 2026-07-16 Fable 5 실행 완료. 판정: 아카이브의 꽃집 전용 manifest 복구 + `pipeline:` 중첩만 구조 수정(신규 작성 아님, manifest 포기도 아님). 근거·다음 액션 전문: [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]] §12. 후속 실행은 Sonnet(T6 계속).

## Fable에 다시 물으면 안 되는 것 (이미 답 있음 — 중복 질문 = 낭비)
14개 공장 stages 설계 ✅ / 공통규칙 3종(재실행게이트·반려루프·검수등급) ✅ / 러너 MVP 범위 ✅ / 파이프라인형·상주형 구분 기준 ✅ / 소수공유 조건 ✅ / 자료정리+학습변환 통합(3축) ✅ / **꽃집 manifest 방향(B: 복구+구조수정) ✅ (§12)** — 전부 [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|종합 기획]]과 [[ai공장짓기/설계노트/공장별/공장-아이디어_공장|설계노트]], [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]]에 있음. 새 세션이 이걸 다시 물으려 하면 이 문서를 보여줄 것.

## 자동으로 Fable급 판단이 도는 곳
매주 일요일 21:00 주간종합 (예약 작업) — 별도 요청 불필요.

<!-- ok -->
