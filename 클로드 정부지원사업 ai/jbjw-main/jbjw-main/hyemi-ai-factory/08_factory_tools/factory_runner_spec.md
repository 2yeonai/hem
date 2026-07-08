# factory_runner_spec.md — 공장 실행기 사양

구현: run_factory.py / 원칙: **규칙으로 판정 가능한 것은 코드가, 판단이 필요한 것은 AI 프롬프트 생성으로, 확정은 사람이.**

## 단계별 실행 순서 (7단계 파이프라인)

| # | 단계 | 하는 일 | 산출물 | 유형 |
|---|---|---|---|---|
| 1 | notice | 입력에서 공고 기준 요약 생성, 미확보 항목 [확인 필요] 수집 | notice_summary.md | 코드 |
| 2 | risk | 자격·리스크 룰 체크 (체납·중복수혜·업종코드·미확인 항목) | applicant_risk_check.md | 코드 + 사람 승인 |
| 3 | ideas | 후보 프로필 표 생성 + 증빙 보유량 집계 + **AI 채점 프롬프트 생성** | idea_comparison_table.md, ai_prompt_ideas.md | 코드 + AI |
| 4 | lock | selected_idea_id 있으면 LOCK 초안 + 과제명 후보 AI 프롬프트 / 없으면 PENDING_APPROVAL 중단 | selected_idea_lock.md, ai_prompt_lock.md | 코드 + 사람 승인 + AI |
| 5 | review | **위험 표현 스캔(danger_words.md 자동 대조)** + 미확인·미증빙 집계 + 심사위원 모드 AI 프롬프트 생성 | review_scan_report.md, ai_prompt_judge.md | 코드 + AI |
| 6 | revision | 감지된 문제 전체(확인 필요, 위험 표현, 승인 대기)를 우선순위별 재작업 지시서로 | revision_order_auto.md | 코드 |
| 7 | handoff | 상태 요약 + 다음 명령 포함 인계문 | 10_handoff/HANDOFF_<p>.md | 코드 |

## 단계별 검수 조건 (다음 단계 진행 조건)

- notice → risk: notice_summary 생성됨 (raw_text 미확보여도 진행하되 needs_confirmation 누적)
- risk → ideas: **BLOCKED 아님** (아래 중단 조건 참조)
- ideas → lock: 후보 1개 이상 존재
- lock → review: `selected_idea_id` 지정 + `approvals.idea_selected == true` (둘 중 하나라도 없으면 PENDING_APPROVAL로 파이프라인 정지)
- review → revision: 항상 진행 가능 (revision은 문제 집계라서)
- revision → handoff: 항상 진행 가능
- **어떤 단계도 코드가 LOCKED로 올리지 않는다.** 최대 DRAFT/REVIEWED까지. LOCKED는 사람이 LOCK_STATUS.md에 기록.

## 실패 시 중단 조건 (BLOCKED — 즉시 정지)

1. `applicant.tax_arrears == true` → 접수 요건 미달
2. `applicant.duplicate_grant_history == true` → 중복수혜
3. input.json 파싱 불가 / 필수 키(project_name, notice, applicant, ideas) 누락
4. 프로젝트 폴더 불일치 (input은 있는데 project.json 없음 → create_project부터)

BLOCKED 해제: 사람이 사실관계 확인 후 input.json 수정 + blockers 사유 소명 → 재실행

## 사람 승인 지점

human_approval_points.md 참조 (approvals.* 필드와 1:1 대응)

## 최종 HANDOFF 생성 조건

- handoff 단계는 언제든 실행 가능하되, 미완 단계는 "미완성" 목록으로 정직하게 기재
- PENDING_APPROVAL·BLOCKED 상태면 HANDOFF에 해제 방법을 반드시 포함

## AI 프롬프트 파일 규약 (ai_prompt_*.md)

- CLI가 판단 단계에서 생성하는 붙여넣기용 프롬프트. Claude 세션에 그대로 붙여넣으면 해당 단계의 AI 판단 산출물이 규칙(00_rules)에 맞게 생성된다.
- 후속 확장: AI API 연동 시 이 프롬프트를 그대로 API 호출 본문으로 사용 (TODO_CLI.md #1)
