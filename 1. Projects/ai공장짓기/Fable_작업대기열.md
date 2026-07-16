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
| F2 | mock→실제 AI 호출 전환 설계 | 9월 | 비용 구조·모델 라우팅이 걸린 플랫폼 결정 | 신규 — 그때 카드 작성 |
| F3 | 방역 미정 봇 3개 최종 판정 | 골든셋 후 **충돌 시에만** | 골든셋 근거가 기존 설계와 모순될 때만 | [[1. Projects/완전자동화_실행계획|실행계획]] 2단계 |
| F4 | 신규 공장 착수 전 설계 재감사 (9월, 1회) | 9-1 직전 | 2개월 지난 설계의 blind-spot 점검 | 설계노트/공장별 노트 첨부해 감사 요청 |

## 처리 완료 (decision-log로 이관)

- ~~F6 정부지원 뒷단(선정 후 PPT·발표대본·QNA) 설계~~ — 2026-07-16 Fable 5 실행 완료(F-대기열에 사전 등록 없이 혜미 요청으로 즉시 실행 — 급한 건이라 대기열 절차 생략, 사후 기록). 판정: 8 stage(local 2/model 4/human 2), 승인 게이트 2곳(PPT승인/발표패키지승인), 헌장 §5 트리거 발동 확인. 같은 날 Sonnet이 manifest v2 반영+run.py mock 구현+테스트 5종 PASS까지 완료. 전문: [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]] §17.
- ~~F1 정부지원 스크래핑 설계~~ — 2026-07-16 Fable 5 실행 완료. 판정: bizinfo 1순위(API 우선)/일 1회 07:00+체크섬 게이트/일시장애 3회 백오프·구조변경 즉시 알림/3계층 io_contract(raw→candidate→사람 검수 게이트 1곳→정본). **같은 날 §15로 확장**: 혜미 정정 지시로 모온 단일 → 3사업(온천꽃식물원·대륙창업·모온) 상시 매칭, 지자체 2단계 포함, 구현 2026-08 목표로 앞당김. 프로필 정본 `클로드 정부지원사업 ai/scripts/business_profiles.yaml` 신설. 전문: [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]] §14·§15.
- ~~F5 꽃집 manifest.yaml 방향 결정~~ — 2026-07-16 Fable 5 실행 완료. 판정: 아카이브의 꽃집 전용 manifest 복구 + `pipeline:` 중첩만 구조 수정(신규 작성 아님, manifest 포기도 아님). 근거·다음 액션 전문: [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]] §12. 후속 실행은 Sonnet(T6 계속).

## Fable에 다시 물으면 안 되는 것 (이미 답 있음 — 중복 질문 = 낭비)
14개 공장 stages 설계 ✅ / 공통규칙 3종(재실행게이트·반려루프·검수등급) ✅ / 러너 MVP 범위 ✅ / 파이프라인형·상주형 구분 기준 ✅ / 소수공유 조건 ✅ / 자료정리+학습변환 통합(3축) ✅ / **꽃집 manifest 방향(B: 복구+구조수정) ✅ (§12)** / **정부지원 스크래핑 설계 4문항 ✅ (§14)** — 전부 [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|종합 기획]]과 [[ai공장짓기/설계노트/공장별/공장-아이디어_공장|설계노트]], [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]]에 있음. 새 세션이 이걸 다시 물으려 하면 이 문서를 보여줄 것.

## 자동으로 Fable급 판단이 도는 곳
매주 일요일 21:00 주간종합 (예약 작업) — 별도 요청 불필요.

<!-- ok -->
