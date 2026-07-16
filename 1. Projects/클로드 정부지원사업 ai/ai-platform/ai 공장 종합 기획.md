# 구현 작업용 종합 자료 — 2026-07-08

오늘 Fable 5로 확정한 모든 설계 결정을 정리한 문서. Cowork(Claude Code)에게
넘길 때 이 문서를 그대로 붙여넣거나 레포에 저장 후 참조시키면 됨.
**이 문서에 없는 내용은 추측하지 말고 blocked로 보고할 것.**

---

## 0. 전체 그림

```
④ AI회사 플랫폼 (범용 러너 + 공통규칙 3가지)
   ↓ 이 위에 14개 공장이 얹힘
① 정부지원사업 (90%, 실구현+테스트완료)
② 꽃집 (설계완료, 코드는 정부지원 복제 수준)
③ 방역 (뼈대+안전장치 완성, 봇3개 골든셋 대기로 보류)
+ 신규 11개: 아이디어/자료정리+학습변환(통합)/PPT/가구배치/
  챗봇·AI직원/이미지·AI인간/3D캐릭터·굿즈/콘텐츠재생산/냉장고·집밥
  (전부 설계 확정, 코드 0줄 — 오늘 처음 만드는 대상)
```

**우선순위**: 범용 러너 먼저 → 공통규칙 3가지 반영 → ①②③에 소급 적용 →
신규 11개는 러너 위에 처음부터 올바른 구조로 얹기.

---

## 1. 플랫폼 공통 스펙 (모든 공장이 따르는 것)

### 1-1. 파일 구조
```
skill/
  SKILL.md          # name, description(트리거 조건), when-not-to-use
  manifest.yaml      # 아래 필드
  scripts/           # 실행 코드 (모델 비의존)
  templates/         # 산출물 템플릿
  checks/            # self-check 루틴
```

### 1-2. manifest.yaml 필수 필드
```yaml
io_contract:        # 입출력 스키마 (JSON Schema)
model_routing:       # 단계별 최소 모델 티어 — 모델명 아닌 티어명만
                      # (low_cost/mid/high, Fable 배정 절대 금지)
quality_gate:         # self-check 규칙 + 실패시 행동
invocation:           # AI직원 플랫폼이 tool로 호출하는 엔트리포인트 시그니처
triggers:             # 이 일이 어떻게 시작되는지
  - type: event | schedule
    source / interval: ...
    entry_stage: ...
pipeline:
  stages: [...]        # 아래 1-3 참조
```
스케줄러(실제 날짜 확인 후 트리거 실행)는 manifest 밖 별도 소형 프로그램.

### 1-3. stage 구조
각 stage: `id / kind / io(입출력스키마) / check / on_fail / depends_on`

**kind는 4종류**:
- `local` — 코드 실행, 결정적 계산 (판정 로직·규칙 계산은 반드시 이거)
- `model` — LLM 판단 (tier: low_cost/mid/high 중 하나, **Fable 배정 금지**)
- `human` — 사람 검수
- `tool(external)` — 외부 도구 호출 (이미지 생성기, 영상편집기 등)

**골격 2종류** (공장마다 선언):
- `pipeline-type` — 시작→끝, 1회 실행 (대부분의 공장)
- `resident` — 상시 대기, `on_start/on_message/on_shutdown` 훅.
  `on_message`에 짧은 `turn_stages` 배열 연결 (챗봇 운영모드, 자료정리 answer 등)

### 1-4. 오늘 확정한 공통규칙 3가지 (지금 구현할 것)

**① 재실행 게이트** (`rerun_gate`)
```yaml
rerun_gate:
  enabled: true
  hash_inputs: [user_input, ledger_snapshot]   # 해시 대상, 공장이 선언
  scope: full | from_stage
```
러너가 해시 비교→skip/run 판단. 무엇을 해시할지는 공장이 선언, 비교·실행은 러너 담당.
필드 없으면 `enabled: false`로 간주 (하위호환).

**② 반려 루프 라우팅** (`on_reject`)
```yaml
stages:
  - id: s4_human_review
    kind: human
    on_reject:
      default: s3_draft
      by_reason:
        budget_violation: s2_matching
        format_error: s3_draft
      max_loops: 3
      on_exhaust: escalate_human | fail_with_report
```
사유코드 = 플랫폼 공통 enum(형식/내용/예산/제약위반) + 공장별 확장 허용.

**③ 검수원 등급** (`review.risk_tier`)
```yaml
review:
  risk_tier: T1 | T2 | T3    # T1=고위험(오류시 외부피해+회수불가)
  reviewer_grade: senior | standard | any
  sla_hours: 24
  queue_priority: high | normal | low
  mandatory: true | false
```
위험도 축 2개: 오류시 피해크기(외부실피해/내부재작업/무시가능) × 되돌리기가능성(회수불가/복구가능).
**값 배정은 지금 안 함** — 스키마 골격만 확정, 실제 T1/T2/T3 배정은 공장별로 근거 생기면.

### 1-5. 범용 러너 MVP 범위 (지금 만들 것)
- manifest.yaml 로드 + 정적 검증(문법/의존관계 존재확인/순환없음/인접stage 스키마 호환)
- pipeline-type 골격만 지원 (resident는 이번 범위 제외)
- kind: local, kind: model(API 1회 호출) 실행
- kind: human은 "큐에 내보내고 대기" 인터페이스만, 실제 큐는 수동승인 스텁으로 대체
- 모든 stage 경계에서 데이터 스키마 검증, 불일치시 자동수정 금지 → 명확한 에러로 정지
- 실패 행동은 "정지"와 "N회 재시도" 두 가지만
- stage별 실행 로그(입력해시/소요시간/성공실패)

**MVP에서 뺄 것** (인터페이스 자리만, 구현 안 함): 반려루프 실제 집행 큐, human 검수 SLA 시스템,
resident 골격, 검수원 등급 실제 집행.

### 1-6. 어댑터 (외부 앱 연결 시)
오늘 정부지원사업↔GitHub앱 연결에서 확정된 패턴:
- 외부 데이터 구조가 안 맞으면 `kind: adapter` 또는 stage의 `transform` 필드로
  1급 시민화 (일회성 코드 아님 — 검증·로깅·실패처리 동일하게 받음)
- 단계별 입출력 스키마를 JSON Schema로 manifest에 선언, 러너가 실행 전 정적 검사
- 외부 경계엔 "상대방 스키마 버전/체크섬" 기록 → 상대가 바뀌면 명확히 실패

---

## 2. ① 정부지원사업 스킬 (실구현 완료, 오늘 반영할 것만)

**현재 상태 (v0.4.0/v0.5.0)**: 5단계(수집→매칭→초안→검수→보고), 실제 PDF공고+실사업자
데이터로 6개 회귀테스트 통과. 4개 서브시스템(위험표현사전/PSST/8인심사위원/감점전파)
구현+GitHub앱 연동 어댑터(`govskill_adapter.py`) 완료.

**오늘 나온 알려진 한계 4가지** (어댑터 관련, 우선순위 순):
1. 자격조건 자유서술 → 정량체크 생략, confidence 낙관화 — **높음, 고칠 것**
2. 서류준비상태 필드 없음 → PSST-Support 항상 "0건" — **높음, 고칠 것** (uploads/attachments 등 다른 이름으로 있는지 먼저 확인)
3. founded_date→업력 근사계산 — 낮음, 안 고쳐도 됨
4. budget_plan에 category 없음 — 중간, hyemi쪽 자체체크로 부분보완됨, 안 고쳐도 됨

**오늘 추가로 반영할 것**:
- `on_reject` 소급: 형식/예산 사유만 매핑, 내용품질 사유는 TODO (judge 확장 선행 필요)
- `rerun_gate` 추가
- `review.risk_tier: T1` 지정 (고위험 공장)
- 필드 없으면 기존 그대로 동작(하위호환) 원칙 지킬 것

**작업 순서**: 위 4가지 한계 중 1·2번 먼저 → 공통규칙 3가지 반영 → 회귀테스트 재확인

---

## 3. ② 꽃집 스킬

**현재 상태**: 14단계 봇 설계 완료(주문판정봇·주문분리봇 뒤늦게 추가 발견됨), 코드는
정부지원사업 폴더 복제 수준 — **아직 실제 stages로 옮겨적지 않음**.

**오늘 나온 것**: 12개→14개 봇 확정판. stage 구조:
- kind는 local(수집/저장/출력준비/문자장부 등 절반)/model(말귀봇 등 4~5개)/human(1개)
- 실행순서는 `depends_on`으로, 배열순서 아님
- 검수매니저(model, check가 통과/에스컬레이션 분기 출력) + 사람검수자(human, 정규경로)
- **저위험 공장** → risk_tier: T3, `on_reject.default: 직전생성 stage` 하나면 충분

**작업 순서**: manifest.yaml을 표준 포맷으로 새로 작성(정부지원 복제 아님) →
14 stages 각각 kind 배정 → `on_reject` T3 규칙 반영 → 회귀테스트 없으니 새로 작성

---

## 4. ③ 방역 스킬

**현재 상태**: v2 스키마(triggers+run_if) 확정+구현+검증 완료. HANDOFF.md 있음.
법정요구사항 대조표, 문서템플릿 2종, 합성테스트 12건 실행 완료.

**중요 — 보류 상태 명확히 유지할 것**:
선택형 봇 3개(방문지다중분리/현장사진첨부/견적산정)는 **골든셋 미확보로 활성화 보류**.
오늘 있었던 "합성 테스트 12건"은 구조 검증용이지 실사례 빈도 근거가 아님 —
이 3개 활성화 여부는 실제 방역&클린 업무 데이터가 모이기 전까지 판단하지 말 것.
run_if로 자리는 마련되어 있으므로 지금은 그대로 둠.

**작업 순서**: 공통규칙 3가지만 반영(rerun_gate/on_reject/risk_tier) → 3개봇은 건드리지 않음
→ HANDOFF.md에 "골든셋 확보 전까지 보류" 명시 재확인

---

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

## 6. 소수공유(비앱스토어) 조건 — 전 공장 공통

**stages 분류(local/model/human/tool-external) 변경 없음.** 추가되는 것만:

| 요소 | 내용 |
|---|---|
| 데이터 네임스페이스 | 저장경로·장부행에 `user_id` 스코프 |
| human stage 담당자 | `assignee: 데이터소유자` — 제작자 대리검수 금지 |
| 자격증명 분리 | tool-external(캘린더·메신저 등)은 사용자별 키 |
| model 비용귀속 | 사용자별 사용량기록+상한 |
| 장부 scope | `personal | shared` — 판별질문: "두 사용자가 서로의 항목을 봐야 업무가 성립하는가?" |

- **각자 설치형이면 인증 자체 불필요** (지금 이 방식 권장, 분리가 공짜)
- 한 인스턴스 공유형이 되면 그때: user_id프로필+약한인증(초대링크/PIN)+네임스페이스강제
- OAuth·역할권한화면·비밀번호정책 불필요 (위협모델이 "실수로 남 데이터 봄"이지 "공격"이 아님)
- 필요한 최소 4가지: 자동백업, 비용상한, 안전한실패(에러가 남 데이터 노출 안함), 업데이트 전달경로 1개
- **예외**: 법정서식 다루는 방역은 심사여부 무관하게 법정요건 그대로 적용, 완화 안 됨
- 공동장부 후보: 냉장고(가족), 꽃집재고, 방역작업기록 / 나머지는 기본 개인

---

## 7. 오늘 남긴 미해결 항목 (지금 안 함, Fable도 필요없음, 근거 생기면 재논의)

- ③ 방역 선택형 봇 3개 활성화 — 골든셋 확보 전까지 보류
- human 검수 큐/SLA 집행 시스템 — 스키마 골격만 있음, 실제 큐는 미구현
- risk_tier 값의 14개 공장 실제 배정 — 골격만, ①③만 확정(T1/T3), 나머지는 값 미배정
- 정부지원사업 내용품질 반려 사유코드 — judge 확장(설득력 평가) 선행 필요
- 반려루프 사유코드 enum 완결 — 공장별 확장 허용 중, 전체 통일은 나중

---

## 8. Cowork 작업 순서 (권장)

1. 범용 러너 MVP 구현 (1-5 참조)
2. 공통규칙 3가지를 러너에 반영 (1-4 참조)
3. ① 정부지원사업: 한계 1·2번 수정 + 공통규칙 소급 (2번 참조) + 회귀테스트
4. ③ 방역: 공통규칙만 반영, 3개봇 손대지 않음 (4번 참조)
5. ② 꽃집: manifest 신규 작성 + 14 stages 옮겨적기 (3번 참조)
6. 신규 11개: 러너 위에 하나씩 얹기, 5-1~5-9 순서 무관하게 필요한 것부터
7. 소수공유 조건(6번)은 전 공장 공통이므로 러너 레벨에서 먼저 처리하면 개별 공장 작업이 줄어듦

각 단계마다 모호 지점 있으면 추측하지 말고 blocked로 보고할 것.

## 관련 문서

- [[1. Projects/클로드 정부지원사업 ai/HANDOFF|HANDOFF (정부지원사업)]]
- [[1. Projects/클로드 정부지원사업 ai/마이그레이션_diff_리포트_v1_to_v2|마이그레이션_diff_리포트_v1_to_v2]]

<!-- ok -->
