# LOCK_STATUS.md — LOCK 현황판

상태 정의: DRAFT(작성 중) / REVIEWED(검수 통과) / LOCKED(사람 확정, 변경 금지)

## 공장 구조 (전 프로젝트 공통)

| 항목 | 상태 | 날짜 | 확정자 | 근거 |
|---|---|---|---|---|
| 공장 설계 (5개 생산라인, 폴더 구조) | **LOCKED** | 2026-07-03 | 사용자 지시 기반 | FACTORY_DESIGN.md, D-001 |
| 운영규칙 8종 (00_rules) | **LOCKED** | 2026-07-03 | 사용자 첨부 운영규칙 기반 | D-002, D-008 |
| 워크플로우 6종 (02_workflows) | REVIEWED | 2026-07-03 | AI | 실전 1회 후 LOCKED 전환 판단 |
| 템플릿 8종 (03_templates) | REVIEWED | 2026-07-03 | AI | 실전 사용하며 개선 가능 |
| MVP 정의 (11단계 입출력) | **LOCKED** | 2026-07-03 | 사용자 지시 기반 | D-005 |

## 프로젝트: mvp_test_01 [샘플]

| LOCK 단계 | 상태 | 비고 |
|---|---|---|
| 1. 공고 기준 | DRAFT | 공고 원문 없음 — [확인 필요] 다수 |
| 2. 프로젝트 분리 | REVIEWED | 중심 아이템 1개(후보1), 후보2·3 분리 완료 |
| 3. 자격·리스크 | DRAFT | 중복수혜·체납·업종코드 사람 확인 대기 |
| 4. 아이디어 후보 | REVIEWED | 후보 3개 등록 완료 |
| 5. 심사표 분석 | DRAFT | 배점이 가정값 |
| 6. 최종 아이디어 | DRAFT | AI 추천(후보1)까지. **사람 확정 금지 상태 유지** — 샘플이므로 |
| 7~17 | 미진행 | 실전 프로젝트에서 진행 |

## 규칙

- LOCKED 변경은 사용자 승인 + DECISIONS.md 기록 필수
- mvp_test_01은 어떤 단계도 LOCKED로 올리지 않는다 (샘플, D-006)

## 앱 MVP (Hyemi Grant Factory v0.1) — 2026-07-03 추가

| 항목 | 상태 | 비고 |
|---|---|---|
| 실행 구조·스키마 (input/output_schema, 스펙 5종) | **LOCKED** | D-009~D-011 |
| 엔진·앱 코드 (engines/export_md/app/CLI) | REVIEWED | 테스트 29/29 + 화면 검증. 실전 1회전 후 LOCKED 판단 |
| 앱 판정: 부분 완성 (82/100) | - | 05_reviews/app_mvp_final_judgement.md |
| sample-demo 프로젝트 | 샘플 | 어떤 단계도 LOCKED 금지 (D-006) |
