---
tags: [꽃집, ai공장, decision-log]
created: 2026-07-12
---

# decision-log: 꽃집 12봇 → 14봇 결정 서사 (소급 정리, 2026-07-12)

> 흩어져 있던 결정 근거(12봇_kind분류표 주석, 실데이터 diff 로그 #1·#2, Fable 결정 2026-07-06)를 한 곳에 모음. 원본이 정본, 이 노트는 서사 요약.

## 타임라인

1. **2026-07-06 (Fable 5 결정)** — kind는 local/model/human 세 값만. 12봇 파이프라인 골격 확정. 검수매니저 tier는 답변에서 누락 → Sonnet 5가 "판단 복잡도 기준 haiku/sonnet 중 결정"으로 보완.
2. **2026-07-07 (실데이터 diff 로그 #2)** — 실제 주문 데이터 대조 중 두 가지 구멍 발견:
   - 주문이 아닌 문의/잡담이 파이프라인에 흘러듦 → **order_classification_bot(주문판정봇)** 신설 (false-positive 방지)
   - 한 메시지에 여러 주문이 섞임 → **order_split_bot(주문분리봇)** 신설 (다중주문 분리)
   - 배치 논점: 혜미는 "수집봇 다음"을 원했으나 텍스트가 있어야 판정 가능 → transcription_bot 다음으로 배치 (이견 시 변경 가능으로 남김)
   - fan-out 논점: 분리된 주문들 병렬 처리 대신 **순차 처리**로 결정 — bundle_id/sequence/status 필드 신설
3. **파일명은 "12봇" 유지** — 기존 참조 안 깨지게. 실제는 14 stage (local 7 / model 6 / human 1).

## 왜 이 확장이 "설계 실패"가 아니라 "정상 작동"인가
골든셋(실데이터)이 설계를 이긴 사례 — 책상 설계로는 못 본 구멍을 실데이터 6건이 바로 드러냄. 방역 골든셋 수집을 서두르는 이유와 동일한 원리. → 영구노트 후보: "골든셋은 설계를 이긴다".

## 현재 코드 상태 (2026-07-12 실측)
- 구현 완료+테스트: storage_bot(12/12 PASS), order_classification_bot(4/5 — 1건은 알려진 한계), order_split_bot(사람 인계까지가 이 버전 목표, LLM 연결 후 재검증 필요)
- 14봇 yaml: v2 스키마 검증 PASS
- 미구현: 나머지 11개 봇 mock + 러너 어댑터(방역 pest_adapter 방식) — [[ai공장짓기/착수_2026-07-12|착수 노트]] 참고

## 미결(open_questions 요약 — 원본: 12봇_kind분류표.yaml)
transcription_bot kind 불일치 / order_draft·review_manager·신규 2봇 tier 실측 없음 / human_reviewer 반려-복귀 UX 정합 / confidence 색상→수치 매핑 / bundle_status와 실제 DB 스키마 정합(구현 단계 재확인)

## 관련 문서
- [[클로드 꽃집 ai/실데이터_diff_로그_001|diff_로그_001]] · [[클로드 꽃집 ai/실데이터_diff_로그_002|diff_로그_002]] · [[클로드 꽃집 ai/최종점검_리포트_2026-07-07|최종점검_리포트]] · [[ai공장짓기/decision-log_skill-factory-architecture|플랫폼 decision-log]] · [[2. Areas/핵심맥락|핵심맥락]] · [[LLM위키_홈]]
