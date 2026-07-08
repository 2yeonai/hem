# error_handling_rules.md — 오류·중단 처리 규칙

## 오류 등급

| 등급 | 정의 | 동작 | 예 |
|---|---|---|---|
| FATAL | 실행 불가 | 즉시 종료, exit code 2 | input.json 없음/파싱 실패, 프로젝트 미생성 |
| BLOCKED | 탈락급 리스크 | 해당 단계에서 파이프라인 정지, project.json blockers 기록, exit code 3 | 체납 true, 중복수혜 true |
| PENDING_APPROVAL | 사람 승인 필요 | 파이프라인 정지(오류 아님), 승인 방법 안내 출력, exit code 4 | selected_idea_id 없음, 자격 3종 미확인 |
| WARNING | 진행 가능한 문제 | 계속 진행, warnings·needs_confirmation 누적 | raw_text 미확보, 배점표 없음, 증빙 0건 후보 |

## 원칙

1. **조용히 넘어가지 않는다** — 모든 미확보·미확인은 needs_confirmation에 누적되고 revision 단계에서 재작업 지시서로 나온다.
2. **부분 실패 시 전체 롤백하지 않는다** — 완료된 단계 산출물은 보존, 실패 단계부터 재실행 (`--step <이름>`).
3. **덮어쓰기 규칙**: 재실행 시 같은 단계 산출물은 덮어쓴다. 단, 상태가 REVIEWED 이상인 단계는 `--force` 없이 덮어쓰기 거부 (검수 결과 보호).
4. **자동 LOCK 금지**: 코드가 LOCKED 상태를 쓰는 것은 어떤 경로로도 금지.
5. **문장 중간 중단 금지**: 파일 쓰기는 완성된 내용을 한 번에 (임시 파일 → rename 은 v2, 지금은 완성 문자열 일괄 쓰기).
6. exit code: 0 정상 / 2 FATAL / 3 BLOCKED / 4 PENDING_APPROVAL — 쉘 스크립트·CI에서 분기 가능.

## 사람에게 보고하는 형식 (정지 시 CLI 출력)

```
[BLOCKED] 단계: risk
사유: applicant.tax_arrears = true (접수 요건 미달 가능)
해제 방법: 납세증명서로 사실 확인 → input.json 수정 → 재실행
기록 위치: 04_outputs/<p>/project.json > blockers
```
