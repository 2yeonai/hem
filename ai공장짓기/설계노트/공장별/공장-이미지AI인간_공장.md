---
type: design-note
source: "[[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]"
created: 2026-07-12
tags: [ai공장, 설계, 공장설계]
---

# 이미지·AI인간 공장 공장 설계 (5-6)

> 원본: [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]] · 상위: [[ai공장짓기/설계노트/5_신규_11개_공장_—_stages_설계_확정본|신규 11개 공장 확정본]] · 실행기: [[ai공장짓기/runner/README|범용 러너]]
> 수정은 원본에서. 이 노트는 그래프 연결·검색용.

### 5-6. 이미지·AI인간 공장 (파이프라인형, 7단계)
```
brief_intake(local) → persona_design(model, 경량사전권리필터포함) → prompt_pack(model)
→ image_generate(tool-external) → rights_check(model, 전용저작권합격기준)
→ human_review(human, 최종직전) → channel_package(local+model)
```
- 저작권검수 이중배치: 경량필터(2번, 외부호출 전 비용절감) + 본검수(5번, 픽셀단위)
- human검수는 최종직전(6번) — 자동검수 뒤라 큐량 감소, 페르소나+프롬프트+이미지 전체맥락 필요
- 반려루프: 3갈래(페르소나문제→2번, 프롬프트문제→3번, 개별이미지→4번부분재생성+seed변경필수)

