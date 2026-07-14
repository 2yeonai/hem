---
type: design-note
source: "[[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]"
created: 2026-07-09
tags: [ai공장, 설계, 플랫폼]
---

# 5. 신규 11개 공장 — stages 설계 확정본

> 원본: [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]] (2026-07-08 Fable 확정). 수정은 원본에, 이 노트는 그래프 연결·검색용.

## 5. 신규 11개 공장 — stages 설계 확정본

### 5-1. 아이디어 공장 (파이프라인형, 6단계)
```
s1_intake(local, 재실행게이트) → s2_classify(model) → s3_score(model, 전용 평가원)
→ s4_plan(model, 전용 기획원) → s5_validate(local, 실패시 원인단계로만 반송 최대2회)
→ s6_record(local)
```
- 전용 직원 2명 필요: **평가원**(4축 점수+근거, SKILL.md에 앵커 루브릭 필수 —
  안 그러면 실행마다 ±3점 흔들림), **기획원**(MVP축소안+액션3개, 반드시 축소안에서 파생)
- s3·s4 절대 합치지 말 것 (점수 오염+토큰낭비)
- human 단계 불필요 (내부도구, 저위험) → risk_tier: T3
- 위험: 점수 캘리브레이션 드리프트, 입력품질게이트 부재(한줄메모도 자신만만한 점수 나옴),
  s5→s3/s4 조건부 반송을 `on_reject`로 표현

### 5-2. 자료정리 + 학습변환 (통합 템플릿, 골격은 분리 유지)
**중요**: 완전히 하나로 합치치 말 것. **템플릿(stages)은 공유, 런타임(골격타입)은 분리**.

3개 파라미터로 분기: `ordering(given|inferred)`, `arrival(batch|incremental)`, `has_speaker(true|false)`

통합 stages:
```
ingest → normalize → [profile: has_speaker=true일 때만]
→ structure(항상 실행: inferred=클러스터링+정렬추론 / given=주어진순서 기록만, "건너뛰기 아님")
→ derive → link → merge([batch: state=∅ / incremental: state+delta]) → synthesize
→ inspect(양쪽 필수) → [gap_audit: 선택적] → [checkpoint-rebuild: arrival=incremental만]
```
- 자료정리(주제별 로드맵) = batch, 파이프라인형
- 학습변환(강의 회차누적) = incremental, **상주형 성격** (state 보유, checkpoint-rebuild 필요)
- 학습변환 핵심: 종합본을 계속 재요약하면 안 됨(복리손실) → course-state 갱신 + 영향섹션만 patch,
  5회차마다 전체 재빌드(Batch API)로 드리프트 교정
- 스타일 유지: 추출(profile, 1회)/적용(derive+merge 둘다)/검증(inspect) 3단계 분리

### 5-3. PPT 공장 (파이프라인형, 8단계)
```
ingest(local) → summarize(model) → structure(model, 덱스펙+layout_type필드필수)
→ draft-slides(model) → draft-script(model) → inspect(model, 반려대상stage지정)
→ human-review(조건부, review_policy: optional기본) → package(local, 순수렌더러)
```
- 포장원(package)은 **local 확정, 단 순수렌더러 한정** — 스펙 불완전시 임의보정 금지,
  구조적 실패로 반려(structure/draft-slides로)
- "코드가 결정적 수행 가능+판단여지가 스펙으로 소거됐는가"가 local/model 분류 기준

### 5-4. 가구배치 공장 (파이프라인형, 6단계)
```
interpret(model, 조건부 — 폼입력이면 스킵) → validate(local) → solve(local, 판정라이브러리 내부호출)
→ judge(local, 규칙판정원, manifest가 규칙표 주입) → render(local) → explain(model, 읽기전용+숫자는 템플릿치환만)
```
- **model은 solve/judge 코어에 절대 개입 금지** — interpret과 explain 앞뒤로만
- interpret 결과는 echo-back으로 사용자 승인 필수(환각치수 방지)
- 위험: "배치불가"(infeasible)와 "탐색실패"(not_found) 반드시 별도 상태로 — 안 그러면 거짓판정
- 회전각도 이산화 여부 지금 결정, 공장 상수로(규칙표 아님)
- risk_tier: T3 (규칙판정 핵심, opus검수 불필요 — 골든셋 회귀테스트가 검수 대체)

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

### 5-6. 이미지·AI인간 공장 (파이프라인형, 7단계)
```
brief_intake(local) → persona_design(model, 경량사전권리필터포함) → prompt_pack(model)
→ image_generate(tool-external) → rights_check(model, 전용저작권합격기준)
→ human_review(human, 최종직전) → channel_package(local+model)
```
- 저작권검수 이중배치: 경량필터(2번, 외부호출 전 비용절감) + 본검수(5번, 픽셀단위)
- human검수는 최종직전(6번) — 자동검수 뒤라 큐량 감소, 페르소나+프롬프트+이미지 전체맥락 필요
- 반려루프: 3갈래(페르소나문제→2번, 프롬프트문제→3번, 개별이미지→4번부분재생성+seed변경필수)

### 5-7. 3D캐릭터·굿즈 공장 (파이프라인형, 9단계)
```
s1_intake(local,재실행게이트) → s2_bible(model) → s3_ip_gate1(model+human, 반려시s2로)
→ s4_pose_set(model) → s5_goods(model) → s6_spec3d(model,규칙표참고자료)
→ s7_rulecheck(local,규칙판정원,반려시s6으로) → s8_ip_gate2(human,반려시s5로) → s9_assemble(local)
```
- 저작권게이트 2개: s3(바이블직후, 정체성확정시점, model프리스크린+human경계케이스),
  s8(최종직전, 굿즈단계 새리스크—트레이드드레스 등)
- 규칙표: s6에 참고자료(생성가이드) + s7에 판정권위(local만) — 둘다, 역할분리

### 5-8. 콘텐츠재생산 공장 (파이프라인형, 병렬팬아웃)
```
ingest(local) → transcribe(local) → analyze(model, 분석카드=공유장부기록)
→ [팬아웃 3갈래, 전부 analyze에서 직접분기]:
  - shorts_plan→shorts_edit(tool-external)→shorts_gate(local)
  - blog_write(model)
  - cards_plan(model)→cards_render(tool-external)
→ review(human, join, 산출물별 부분승인 배열출력)
```
- **카드뉴스를 블로그에서 파생시키지 말 것** — 셋 다 분석카드 하나로만 수렴
- shorts_gate(길이/배속/해상도)는 local 확정. 적용파라미터 결정은 조건테이블화 가능한
  것만 local로, 질적판단 섞이면 model(shorts_plan)에 남김
- 반려시 브랜치별 라우팅: 숏폼→shorts_plan/edit, 블로그→blog_write, 카드→cards_plan

### 5-9. 냉장고·집밥 공장 (파이프라인형, 7단계)
```
s1_ledger_read(local) → s2_input_normalize(local) → s3_priority_calc(local)
→ s4_plan_generate(model) → s5_feasibility_check(local, 실패시s4로 최대3회)
→ s6_shopping_diff(local) → s7_ledger_write(local, 낙관적동시성제어)
```
- 유통기한·예산 계산은 반드시 local (s3,s5 이중잠금), model(s4)은 "뭘 요리할지"만
- 공유장부: 매실행 s1에서 필수읽기(캐시금지), 쓰기시 버전재확인
- 재실행게이트: 재고체크섬+입력해시 동일시 s3이후 스킵 — `last_run` 필드 표준후보
- 알림기능 원하면 별도 초소형 resident 감시원으로 분리 (이 공장에 섞지 않음)
- human 단계 없음(조건부만): s6뒤 "사용자확인" 선택플래그, 기본 자동통과

---

## 관련 문서

- [[ai공장짓기/설계노트/0_전체_그림|0_전체_그림]]
- [[ai공장짓기/설계노트/1_플랫폼_공통_스펙_(모든_공장이_따르는_것)|1_플랫폼_공통_스펙_(모든_공장이_따르는_것)]]
- [[ai공장짓기/설계노트/2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)|2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)]]
- [[ai공장짓기/설계노트/3_②_꽃집_스킬|3_②_꽃집_스킬]]
- [[ai공장짓기/runner/README|README]]
- [[ai공장짓기/감사_로드맵_2026-07-09|감사_로드맵_2026-07-09]]

<!-- ok -->
