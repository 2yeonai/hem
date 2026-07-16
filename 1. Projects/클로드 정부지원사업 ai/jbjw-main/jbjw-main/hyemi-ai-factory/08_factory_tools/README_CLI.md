# README_CLI.md — 공장 CLI 사용법 (v0.1)

요구사항: Python 3.9+ (외부 라이브러리 불필요). 모든 명령은 `hyemi-ai-factory/` 폴더에서 실행.

## 3분 시작

```bash
# 1. 새 프로젝트 생성
python 08_factory_tools/create_project.py 2026-my-notice

# 2. 입력 채우기 (에디터로)
#    01_inputs/2026-my-notice/input.json
#    - notice.raw_text 에 공고문 원문 전체
#    - 모르는 값은 "미확보"/"미확인" 그대로 두기 (비우지 말 것)

# 3. 공장 실행
python 08_factory_tools/run_factory.py 2026-my-notice --step all
```

## 실행하면 생기는 것

| 위치 | 파일 | 내용 |
|---|---|---|
| 04_outputs/<p>/ | notice_summary.md | 공고 기준 요약 (+확인 필요 목록) |
| | applicant_risk_check.md | 자격·리스크 룰 체크 |
| | idea_comparison_table.md | 후보표 (AI 채점 대기 표 포함) |
| | ai_prompt_ideas.md / ai_prompt_lock.md | **Claude에 붙여넣는 프롬프트** |
| | selected_idea_lock.md | LOCK 초안 (사람 승인 후에만 생성) |
| | project.json | 단계 상태·경고·차단 사유 |
| 05_reviews/<p>/ | review_scan_report.md | 위험 표현 자동 스캔 결과 |
| | ai_prompt_judge.md | 심사위원 모드 검수 프롬프트 |
| | revision_order_auto.md | 자동 재작업 지시서 |
| 10_handoff/ | HANDOFF_<p>.md | 프로젝트 인계문 |

## 코드가 하는 일 vs AI가 하는 일 vs 사람이 하는 일

- **코드**: 폴더 생성, 요약표 생성, 자격 룰 체크, 위험 표현 스캔, 누락 추적, 상태 관리, 지시서·인계문 생성
- **AI (프롬프트 붙여넣기)**: 아이디어 10축 채점, 과제명·한줄요약 생성, 심사위원 8종 검수
- **사람**: 자격 3종 서류 확인, 최종 아이디어 확정(`selected_idea_id` + `approvals.idea_selected: true`), 예산·제출 승인, LOCK_STATUS.md 기재

## 정지 상태와 해제

| exit code | 의미 | 해제 |
|---|---|---|
| 3 (BLOCKED) | 체납·중복수혜 true 등 탈락급 | 사실 확인 → input.json 수정 → 재실행 |
| 4 (PENDING_APPROVAL) | 사람 승인 대기 | input.json에 selected_idea_id + approvals 기록 → 재실행 |

정지되어도 revision_order_auto.md와 HANDOFF는 생성된다.

## 자주 하는 실수

- 값을 빈 문자열로 지우기 → "미확보"로 둬야 [확인 필요]로 추적된다
- ai_prompt 실행 없이 LOCK 진행 → 채점 없는 선정은 감으로 고르는 것과 같다
- mvp_test_01 내용 재사용 → 샘플이다 (D-006)

<!-- ok -->
