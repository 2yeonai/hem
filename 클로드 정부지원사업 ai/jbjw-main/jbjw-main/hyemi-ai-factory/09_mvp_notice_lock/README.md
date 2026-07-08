# 09_mvp_notice_lock — 첫 MVP: 공고 분석·아이디어 LOCK 생성기

도구 정의: 08_factory_tools/mvp_notice_lock_generator.md
첫 테스트 실행: 04_outputs/mvp_test_01/ (입력: 07_samples/)
검수 결과: 05_reviews/mvp_test_01/

## 실행 방법 (다음 세션에서 그대로 사용)

1. `01_inputs/input_form.md`를 복사해 `01_inputs/<프로젝트명>/input.md`로 채운다.
2. 아래 프롬프트를 붙여넣는다.

```text
hyemi-ai-factory의 CLAUDE.md와 00_rules/ 전체를 읽고 적용해라.

MVP "공고 분석·아이디어 LOCK 생성기"를 실행해라.
도구 정의: 08_factory_tools/mvp_notice_lock_generator.md
입력: 01_inputs/<프로젝트명>/input.md

처리 11단계를 순서대로 실행하고, 04_outputs/<프로젝트명>/에
notice_summary.md, applicant_risk_check.md, idea_comparison_table.md,
scoring_strategy.md, selected_idea_lock.md, next_step_prompt.md를 생성해라.

규칙:
- 없는 입력은 임의 확정하지 말고 [확인 필요]로 표시하고 가정값으로 진행해라.
- 탈락급 리스크 발견 시 STOP하고 보고해라.
- 완료 후 반드시 심사위원 모드로 전환해서 05_reviews/<프로젝트명>/에
  final_judge_review.md, score_estimation_table.md, risk_register.md,
  missing_evidence_list.md, budget_risk_review.md, dangerous_expression_review.md,
  presentation_attack_qna.md, revision_order.md를 생성해라.
- 마지막에 HANDOFF.md를 갱신하고 커밋·푸시해라.
```

## 상태

- 2026-07-03: 샘플 데이터(mvp_test_01)로 첫 실행 및 검수 완료. 실제 공고 입력 대기 중.
