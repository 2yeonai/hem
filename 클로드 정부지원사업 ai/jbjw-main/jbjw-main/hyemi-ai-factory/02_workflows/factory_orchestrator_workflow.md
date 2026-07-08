# factory_orchestrator_workflow.md — 오케스트레이터: 공장 전체 운영 규칙

## 세션 시작

1. CLAUDE.md → HANDOFF.md → 06_locks/LOCK_STATUS.md 순으로 읽는다.
2. 진행 중 프로젝트가 있으면 해당 단계부터 재개. 새 요청이면 라우팅.

## 라우팅 규칙

| 입력 신호 | 라인 | 워크플로우 |
|---|---|---|
| 공고문·지원사업·심사표 | A | grant_workflow.md |
| 발표자료·PPT·슬라이드 (제출본 LOCK 후) | B | presentation_workflow.md |
| 발표연습·대본·Q&A·예상질문 | C | qna_workflow.md |
| 블로그·인스타·릴스·카드뉴스·후기 변환 | D | content_workflow.md |
| 업무자동화·라벨·주문정리·체크리스트 | E | automation_item_workflow.md |

순서 강제: A(제출본 LOCK) 전에 B 시작 금지. B(발표자료 LOCK) 전에 C의 대본 생성 금지. D·E는 독립 실행 가능.

## LOCK 게이트 운영

- 각 단계 종료 시 lock_rules.md에 따라 상태 기록 (DRAFT/REVIEWED/LOCKED)
- 사람 확정 필수 지점(자격, 최종 아이디어, 예산, 제출본)에서는 **추천+근거만 제시하고 사용자 확정 대기**. 단, 테스트·샘플 실행에서는 `[확인 필요]` 태그로 가정 확정하고 진행.
- LOCK 변경 요청 시: DECISIONS.md 기록 → 하위 LOCK 연쇄 해제 여부 판단 → 사용자 승인

## 품질 게이트

산출물 생성 → 심사위원 모드(AGENTS.md #5) 검수 → 통과 시 REVIEWED, 실패 시 revision_order 생성 → 수정 → 재검수

## 세션 종료 (필수)

1. LOCK_STATUS.md 갱신
2. DECISIONS.md 갱신
3. HANDOFF.md 갱신: 완료 / 미완성 / 유지할 LOCK / 다음 작업 / 재개 프롬프트
4. 커밋·푸시

## 중단 프로토콜 (출력 제한·토큰 부족 시)

문장 중간에서 끊지 않고 CHECKPOINT 형식으로 중단:
완료한 것 / 미완성 / LOCK된 것 / 검수 필요 / 다음 위치 / CONTINUE_FROM / NEXT_COMMAND
