# human_approval_points.md — 사람 승인 지점 정의

FACTORY_DESIGN.md의 "사람 검수 지점 6곳"을 실행 구조로 매핑한 것. approvals.* 필드는 **사람이 input.json에 직접 기록**한다 (AI·코드가 대신 쓰는 것 금지).

| # | 승인 지점 | approvals 필드 | 게이트 위치 | 승인 전 확인할 것 | 미승인 시 동작 |
|---|---|---|---|---|---|
| 1 | 자격 3종 확인 (중복수혜·체납·업종코드) | eligibility_confirmed | risk → ideas | 납세증명서, 수혜 이력 조회, 사업자등록증 업종코드 vs 공고 제외 조항 | WARNING으로 진행하되 revision 1순위에 기재. tax_arrears/duplicate=true면 BLOCKED |
| 2 | 최종 아이디어 선정 | idea_selected (+ selected_idea_id) | lock 단계 진입 | idea_comparison_table + AI 채점 결과 검토 | **PENDING_APPROVAL 정지** — lock 이후 진행 불가 |
| 3 | 예산 확정 | budget_confirmed | (v1 파이프라인 밖 — 본문 작성 단계) | 견적서 실물, 허용 항목 대조 | 본문·예산표 작성 진입 금지 (AI 세션이 준수) |
| 4 | 최종 제출 승인 | final_submission_approved | (v1 파이프라인 밖) | final_review_checklist 전 항목 | 제출본 LOCK 금지 |

## 승인 기록 방법

```json
"selected_idea_id": "idea1",
"approvals": { "eligibility_confirmed": true, "idea_selected": true }
```

수정 후 `python 08_factory_tools/run_factory.py <project> --step all` 재실행 — 정지했던 지점부터 통과된다.

## 승인의 의미

- 승인 = "사람이 사실을 확인하고 책임지고 결정했다"는 기록. AI 추천을 그대로 승인하는 것도 가능하지만, 기록의 주체는 항상 사람.
- 승인 없이 산출물이 좋아 보여도 다음 단계로 넘기지 않는 것이 이 공장의 품질 장치다 (무조건 긍정 금지 원칙의 실행형).
