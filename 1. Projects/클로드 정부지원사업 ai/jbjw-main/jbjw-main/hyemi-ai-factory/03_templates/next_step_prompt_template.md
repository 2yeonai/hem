# next_step_prompt_template.md — 다음 단계 프롬프트 템플릿

# 다음 단계 작업 프롬프트: [프로젝트명]

이 파일은 다음 세션(또는 다음 단계)에서 그대로 붙여넣을 명령문이다.

## 현재 위치

- 완료된 LOCK: [번호와 이름]
- 다음 단계: [grant_workflow.md 기준 단계]

## 붙여넣을 프롬프트

```text
hyemi-ai-factory의 CLAUDE.md, HANDOFF.md, 06_locks/LOCK_STATUS.md를 먼저 읽어라.

프로젝트: [프로젝트명]
현재 LOCK 상태: [예: 6번 최종 아이디어 LOCK까지 완료]
유지할 LOCK: [변경 금지 항목]

다음 작업: [예: grant_workflow.md 7단계 작성전략 수립부터 시작해서
scoring_strategy.md를 확정하고, 8단계 본문 구조 작성까지 진행해라.]

입력자료: 01_inputs/[프로젝트명]/ 참조
규칙: 00_rules/ 전체 적용. 특히 danger_words.md와 무조건 긍정 금지.
산출물 위치: 04_outputs/[프로젝트명]/
완료 후: 심사위원 모드 검수 → 05_reviews/[프로젝트명]/ → HANDOFF.md 갱신
```

## 다음 단계에서 필요한 입력 (사용자 준비물)

- [예: 실제 견적서, 증빙 사진 목록 등]

<!-- ok -->
