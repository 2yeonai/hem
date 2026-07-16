---
type: design-note
source: "[[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]"
created: 2026-07-12
tags: [ai공장, 설계, 공장설계]
---

# PPT 공장 공장 설계 (5-3)

> 원본: [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]] · 상위: [[ai공장짓기/설계노트/5_신규_11개_공장_—_stages_설계_확정본|신규 11개 공장 확정본]] · 실행기: [[ai공장짓기/runner/README|범용 러너]]
> 수정은 원본에서. 이 노트는 그래프 연결·검색용.

### 5-3. PPT 공장 (파이프라인형, 8단계)
```
ingest(local) → summarize(model) → structure(model, 덱스펙+layout_type필드필수)
→ draft-slides(model) → draft-script(model) → inspect(model, 반려대상stage지정)
→ human-review(조건부, review_policy: optional기본) → package(local, 순수렌더러)
```
- 포장원(package)은 **local 확정, 단 순수렌더러 한정** — 스펙 불완전시 임의보정 금지,
  구조적 실패로 반려(structure/draft-slides로)
- "코드가 결정적 수행 가능+판단여지가 스펙으로 소거됐는가"가 local/model 분류 기준


<!-- ok -->
