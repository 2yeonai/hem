# mvp_notice_lock_generator.md — 도구 정의: 공고 분석·아이디어 LOCK 생성기

공장의 첫 MVP 도구. AI 세션에서 프롬프트로 실행하는 도구이며, 후속 확장에서 스크립트/앱으로 구현할 수 있게 입출력을 고정한다.

## 입력 (01_inputs/input_form.md 형식)

1. 공고문 텍스트 / 2. 신청자 정보 / 3. 아이디어 후보 1~5개 / 4. 심사표·평가기준 / 5. 예산 기준 / 6. 제출양식 / 7. 페이지 제한 / 8. 발표 여부 / 9. 확보된 증빙자료

누락 입력 처리: 임의 확정 금지. `[확인 필요]` 표시 후 합리적 가정값으로 진행하고, 가정값 목록을 출력 맨 앞에 명시.

## 처리 11단계

1. 공고 핵심 기준 추출 → notice_summary.md
2. 신청자격 체크 ┐
3. 지원제외·결격 위험 체크 ┘→ applicant_risk_check.md (탈락급 발견 시 STOP 보고)
4. 심사표·배점 분석 → scoring_strategy.md (1부)
5. 아이디어 후보 비교 (10축 5점 척도) ┐
6. 아이디어별 감점 위험 표시 ┘→ idea_comparison_table.md
7. 최적 아이디어 추천 (근거 = 심사표 배점)
8. 과제명 후보 5개 ([고객·현장]+[문제]+[해결수단]+[결과물])
9. 한 줄 요약 후보 5개
10. 최종 아이디어 LOCK 문서 → selected_idea_lock.md (사람 확정 전 DRAFT)
11. 다음 단계 작업 프롬프트 → next_step_prompt.md

## 출력 6종 (04_outputs/<프로젝트>/)

notice_summary.md / applicant_risk_check.md / idea_comparison_table.md / scoring_strategy.md / selected_idea_lock.md / next_step_prompt.md

## 실행 후 의무

- 심사위원 모드 검수(05_reviews) 없이 LOCK 금지
- 테스트 실행 시 test_report.md 작성: 입력 요약 / 출력 요약 / 잘 작동한 것 / 누락 / 사람 확인 필요 / 수정 우선순위

## 실행 프롬프트

09_mvp_notice_lock/README.md 참조.
