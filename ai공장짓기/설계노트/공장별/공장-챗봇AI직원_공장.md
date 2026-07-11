---
type: design-note
source: "[[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]"
created: 2026-07-12
tags: [ai공장, 설계, 공장설계]
---

# 챗봇·AI직원 공장 공장 설계 (5-5)

> 원본: [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]] · 상위: [[ai공장짓기/설계노트/5_신규_11개_공장_—_stages_설계_확정본|신규 11개 공장 확정본]] · 실행기: [[ai공장짓기/runner/README|범용 러너]]
> 수정은 원본에서. 이 노트는 그래프 연결·검색용.

### 5-5. 챗봇·AI직원 공장 (구축+운영 이중구조)
**구축** (pipeline-type, 6단계):
```
ingest(local, 재실행게이트) → extract(model) → intent_taxonomy(model)
→ answer_policy(model) → handoff_rules(model) → review_and_package(human→local)
```
**운영** (resident): `execution: resident`, `on_message`에 연결되는 turn_stages:
```
classify(model, intent_taxonomy참조) → answer_draft(model, answer_policy참조)
→ handoff_gate(local, handoff_rules 런타임읽기) → respond_or_escalate(local/human)
```
- 사람이관 규칙: `run_if` 인라인 금지, `handoff_gate`는 구조(항상존재)+규칙은 데이터(재배포없이 갱신)
- 후속 미결: escalate 큐 SLA(다른 공장보다 압박 큼, 최우선 처리 필요), 이관후 복귀경로

