# HANDOFF — gov-support-matching-skill

다음에 이 프로젝트를 이어받는 사람(사람 또는 다른 세션의 나 자신)을 위한 인수인계 문서.

> **먼저 [[1. Projects/클로드 정부지원사업 ai/기능_인덱스|기능_인덱스]]를 읽을 것.** 이 HANDOFF는 세부 이력이라 길고 회차별로 쌓여있음 — "이미 뭐가 있나"는 인덱스 표 하나로 먼저 확인하고, 세부가 필요할 때만 아래 이력을 읽는다.

## AI 작업 시작 규칙 — 반드시 먼저 적용 [hyemi, 2026-07-20 신설]

- 기능_인덱스와 이 구역만 먼저 읽는다.
- 아래 과거 이력 전체를 처음부터 읽지 않는다. (이 문서는 46,000자가 넘는다 — 전체 정독 = 토큰 수만 개 낭비)
- 프로젝트 전체 검색과 폴더 구조 재조사를 금지한다.
- 현재 작업에 지정된 파일만 읽는다.
- 추가 파일이 필요하면 파일명과 이유를 말하고 멈춘다.
- 전체 테스트, 전체 빌드, 패키지 설치를 자동 실행하지 않는다.
- 세션을 마칠 때 아래 "현재 작업"/"다음 한 단계"를 최신으로 갱신한다. (안 그러면 이 구역이 금방 낡는다)

### 현재 작업
- 입력표_템플릿.yaml 빈칸 보완
- 통합 운영앱 구현 및 모바일 우선 UI 개편 완료 — 공개 코드는 GitHub `2yeonai/jbjw` PR #2, 비공개 실행은 `.runtime`(Git 제외)

### 먼저 읽을 파일
- 기능_인덱스.md
- 입력표_템플릿.yaml
- 작성단계_업무지시서_2026-07-20.md

### 읽지 않을 범위
- 이 HANDOFF의 과거 이력 전체
- 4. Archive
- outputs
- 이전 완료 문서

### 다음 한 단계
- 빈 입력값과 증빙 필요 항목만 목록화
- 통합 앱은 `정부지원AI_실행.bat` 실행 후 휴대폰 크기 화면과 후보공고 상세 검수를 사람이 최종 확인한다. 실제 제출·발송은 앱이 하지 않는다.

## 개요
정부지원사업 매칭 스킬. business_profile(사업자 정보) + target_period(조회기간)를 입력받아
공고 매칭, 신청서 초안 작성, 심사위원 모드 자기검수까지 수행한다. 스펙은 `manifest.yaml`,
동작 설명은 `SKILL.md`, 실제 구현은 `scripts/run.py`.

## 현재 상태 (v0.5.0 기준)
- **버전**: manifest.yaml `version: 0.5.0`
- **이번 버전(v0.5.0)에서 한 일**: `gov-support-skill/정부지원사업_판정로직_확장스펙.md`(위험표현 사전/PSST/8인 가상 심사위원/감점 전파 모델 4개 표)를 스펙 그대로 구현. `judge_mode_self_review()`에 질적 판정 레이어 4개를 순서대로 추가(위험표현 → PSST → 8인심사위원 → 감점전파, 각 단계 뒤가 앞 단계 결과를 입력으로 씀). **절대 원칙 준수**: 기존 `overall_confidence` 숫자 공식은 전혀 건드리지 않음. 4개는 전부 `judge_pass_recommendation`(이진 게이트)의 판정 근거를 "형식요건만" → "형식+내용품질"로 넓히는 데만 사용.
  1. **위험표현 사전** — `RISK_PHRASE_DICTIONARY`(9종 고정세트: 완벽히 해결/100% 자동화/AI가 판단한다/자동 발송/외주 개발만 하면 된다/단순 구독/장비 구매/플랫폼으로 대박 확장/기존 문제를 다 없앤다) + `scan_risk_phrases()`. 발견 시 `exaggeration_flags`에 "원문 표현 + 대체문구 제안" 형태로 **추가**(기존 `EXAGGERATION_WORDS` 체크는 대체하지 않고 유지). 자동 치환 없음 — 제안만.
  2. **PSST 자동검수** — `assess_psst()`. Problem/Solution/Support/Traction 4구간을 draft 섹션 존재여부 + 숫자·단위 정규식(`_MEASURE_UNIT_RE`) + budget_detail/documents_status 존재여부로 pass/fail 판정, `psst_review` 필드 신설. 판정만 하고 문장을 대신 써주지 않음 — "무엇이 없는지"만 지적.
  3. **8인 가상 심사위원** — `run_judge_panel()`. 공고적합성/자격규정/문제정의/AI필요성/실행계획/예산증빙/성과확장/발표Q&A 8인이 이미 계산된 기존 신호(자격미확정/미준비서류/결격위험/예산리스크/위험표현/PSST결과)를 근거로 0~5점+즉시경고 판정, `judge_panel_review` 필드 신설. 8인 로직 자체는 공고 불변, `mapped_rubric_items`만 공고의 `scoring_rubric`에 키워드 기반으로 가변 매핑.
  4. **감점 전파 모델** — `build_deduction_map()`. 대표 이슈 5종(예산근거누락/자격증빙미확보/작업시간실측없음/AI필요성불명확/산출물미정의)의 발생 여부를 판정하고, 발생 시 스펙 원문 고정 계수로 다른 평가항목 전파 리스크를 설명하는 `deduction_map` 필드 신설. `overall_confidence`는 건드리지 않음 — 설명 문장 전용.
  5. **`overall_pass_recommendation` 갱신**: 기존 조건(미준비서류==0, 확인필요섹션==0, 결격위험없음, 페이지제한존재)에 `psst_review 전항목 pass` AND `judge_panel_review.warning_count==0`를 **AND로 추가**(대체 아님).
- **작업 중 발견한 버그(즉시 수정)**: PSST 숫자+단위 정규식(`_MEASURE_UNIT_RE`) 최초 버전이 "300만 개"/"1.5억원"처럼 만/억 단위가 낀 한국어 수량 표현을 인식하지 못해, `sample_input_ideal.json`의 Problem 구간을 오탐(FAIL)시키고 `lock_state`가 `READY_FOR_APPROVAL` → `DRAFT`로 잘못 바뀌는 회귀를 유발함. 정규식에 `(만|억)?` 옵션 그룹을 추가해 수정, 회귀테스트로 재확인함. (v0.4.0의 rubric 2글자 부분매칭 오탐과 같은 패턴의 실수 — "숫자/키워드 휴리스틱은 반드시 실제 텍스트로 재검증" 원칙 다시 확인됨.)
- **회귀 테스트 결과 (6개 케이스, 전부 기존과 동일한 lock_state/confidence로 통과)**:
  - `sample_input.json` → DRAFT, confidence 0.85 (기존과 동일). psst 4구간 전부 fail(서술형 필드 자체가 없음), judge_panel 경고 5건, deduction 이슈 4건 — 모두 예상대로.
  - `sample_input_edge.json` → DRAFT, confidence 0.68 (기존과 동일). psst/judge_panel 결과는 sample_input.json과 동일 패턴.
  - `sample_input_ideal.json` → READY_FOR_APPROVAL, confidence 1.0 (기존과 동일, 위 정규식 버그 수정 후 재확인). psst 4구간 전부 pass, judge_panel 경고 0건, deduction 이슈 0건.
  - `test/my_business_profile_input.json` → DRAFT, confidence 0.35 (기존과 동일). psst: problem/solution/traction pass, support fail(문서명 불일치로 준비된 서류가 0건 집계 — 기존부터 있던 known limitation). judge_panel 경고 1건(자격규정), deduction 이슈 1건(자격 증빙 미확보).
  - `test/real_program_input.json` → 매칭 0건(마감 지남)이라 기존과 동일하게 DRAFT, psst/judge_panel/deduction 전부 not_applicable 처리(크래시 없음 확인).
  - `test/real_program_input_simulated.json` → DRAFT, confidence 0.35 (기존과 동일). psst: support fail(문서명 불일치), judge_panel 경고 2건(자격규정+예산증빙 — 기존 v0.4.0 예산초과/집행제외 리스크가 새 예산증빙 심사위원에도 그대로 반영됨), deduction 이슈 2건(예산 근거 누락, 자격 증빙 미확보).
- **합성 결함 테스트 (사용자 추가 지시로 신규 작성, `test/synthetic_*.json` 4종)**: 회귀테스트 6개가 전부 "정상 케이스"라 신규 로직이 실제로 문제를 잡아내는지 검증이 안 되는 문제를 보완. 4개 전부 의도한 대로 정확히 감지됨을 확인:
  - `synthetic_risk_phrases.json`: "100% 자동화로 완벽히 해결"+"AI가 판단한다"+"자동 발송" 포함 → `exaggeration_flags`에 4건 모두 원문+대체문구로 정확히 노출됨.
  - `synthetic_psst_problem_fail.json`: Problem에 감성서사만 있고 수치 없음 → `psst_review.problem.result=fail`, 나머지 3구간(solution/support/traction)은 정상으로 채워 pass 확인 — 격리 성공.
  - `synthetic_judge_panel_equipment.json`: budget_detail이 "장비 구매"(견적 없음) 단일 항목 → 예산·증빙 심사위원만 `score=1, warning=True`로 정확히 트리거, 나머지 7인은 전부 정상 — 격리 성공.
  - `synthetic_deduction_qualification.json`: 필수서류 전부 미준비 → `deduction_map`에 "자격 증빙 미확보"(직접감점 BLOCK, 전파 실행 -3/발표 -3) 정확히 노출.
  - 이 4개 파일은 정식 회귀테스트 스위트 편입 여부 판단 보류 상태(사용자 지시) — 지금은 "신규 로직 발동 확인" 용도로만 존재.
- **lock_state 판정 규칙**: `quality_gate_result.confidence_passed` AND `judge_pass_recommendation`이 둘 다 true일 때만 `READY_FOR_APPROVAL`. (게이트 구조 자체는 v0.5.0에서도 안 바뀜 — `judge_pass_recommendation` 계산에 들어가는 재료만 넓어짐.)
- **Git 이력**: `.git`을 프로젝트 폴더 안에 직접 두지 않고 `gov-support-matching-skill.bundle` 파일로 관리 중. 커밋 이력: 84c5163(v0.1.0) → 4000860(v0.2.0) → 7f64411(HANDOFF.md) → a1e8f8e(실제 공고 테스트 데이터 추가) → 365f3f8(v0.4.0) → 3949f05(HANDOFF.md 루트 통합) → 76defad(v0.5.0: 4개 서브시스템) → d91bf00(AI활용지원사업 공고 추가+검증, 이번 라운드).
  - 로컬에서 히스토리 복원: `git clone gov-support-matching-skill.bundle my-skill` 또는 기존 폴더에서 `git pull gov-support-matching-skill.bundle master`

## 추가 라운드 (real_announcements.json에 실제 공고 2번째 추가 + 8인심사위원 4번 검증)
- `scripts/real_announcements.json`에 **두 번째 실제 공고** 추가(기존 경력단절여성 공고 유지, 병행): `gov-support-skill/1_2026년 혁신 소상공인 AI 활용지원 사업 참여 소상공인 모집공고(수정).pdf` 파싱. deadline 2026-07-03, `budget_criteria.max_grant_krw=40,000,000`, `excluded_categories=["인건비"]`(정부지원금 집행항목 7종엔 인건비가 없고 자부담금 전용 항목이라 확인됨). `scoring_rubric`: AI활용 적합성(15+15=30) / 성장가능성(20+20=40) / 참여역량(15+15=30). `_unmapped_requirements`에 업종별 상시근로자·매출액 차등기준, 지원제외업종 40+개, 공동대표 제한, 사전 온라인교육 이수 조건, 4단계 선정구조(서류평가 100점은 전체 평가의 일부일 뿐 발표평가 배점표는 원문에 없음) 기록.
- `test/synthetic_ai_judge_exaggeration.json` vs `test/synthetic_ai_judge_concrete.json`: 위 공고를 실제 매칭 대상으로 8인심사위원 4번(AI 필요성 심사위원)이 과장 케이스(완벽히 해결/100% 자동화/AI가 판단한다 포함)와 구체적 AI계획 케이스(반자동화/대표자 확인/승인 후 발송)를 정확히 구분하는지 검증 — `score=1,warning=true` vs `score=5,warning=false`로 정확히 판정됨. GOV_SKILL_TODAY=2026-06-20으로 시뮬레이션해야 이 공고가 마감 전으로 잡힘(경력단절여성 공고는 이 시점 기준 이미 마감이라 자동 제외되어 AI 공고가 top_match로 깔끔하게 격리됨).
- **알려진 한계 추가 발견**: `mapped_rubric_items`가 AI활용 적합성(30점) 2개 항목은 정확히 잡지만, "성장가능성 - AI 적용을 통한 사업모델 개선 가능성"(20점) 항목도 텍스트에 "AI"가 포함돼 있어 AI필요성 심사위원에 추가로 매핑됨 — 키워드 휴리스틱이 "AI"라는 짧은 키워드로 인해 다소 넓게 잡히는 현상. 틀린 매핑은 아니지만(그 항목도 실제 AI 관련 내용) 향후 키워드 정교화 여지로 기록.
- `.gitignore`에 `*.truncated-*` 패턴 추가(동기화 마운트 truncation 복구 시 남는 백업 파일이 git에 안 잡히도록).
- 6개 회귀테스트 이번에도 전부 기존과 동일하게 통과 재확인(두 번째 공고 추가가 기존 케이스에 영향 없음).

## 3번째 실제 공고 추가 (생활문화 혁신지원, 실제 합격사례로 검증) — 2026-07-08 세션

- `scripts/real_announcements.json`에 **세 번째 실제 공고** 추가(기존 두 공고 유지, 병행): `gov-support-skill/260508_(공고 제2026-325호) 2026년 소상공인 생활문화 혁신지원 참여소상공인 모집 공고.pdf` 파싱. deadline 2026-06-08, `budget_criteria.max_grant_krw=100,000,000`(유형①②단독/협업 기준. 유형③다수소상공인+지역특화기관 공동신청은 최대 3억원이나 단일 필드에 못 담아 note로만 기록), `excluded_categories=[]`(이 공고는 인건비가 기술개발 항목으로 정부지원금 집행 허용됨 — 총사업비 20% 캡이 있으나 캡 체크 자체는 미구현). `scoring_rubric`: 서면평가(1차, 100점) 기준 추진전략(50)/수행역량(30)/파급효과(20). 발표평가(2차, 대면평가, 실질적 최종선정 단계) 100점 세부표는 공고문 자체엔 없었으나(원문 "별도 안내 예정") 사용자가 별도로 확보한 '소상공인 생활문화 발표 심사기준표' 이미지 자료로 구조를 확인해 `scoring_rubric_note`에 전체 기록(창의성·도전성20/기술성검토40/사업성검토40).
- **실제 합격 사례로 검증**: `test/real_program_3rd_input.json`을 실제 합격한 사업계획서(`합격)소상공인_생활문화_혁신지원_참여소상공인사업계획서.pdf`, 온천꽃식물원/이문숙, "창녕 안심이동 생태 테라리움 기프트")를 그대로 구조화해서 작성. `GOV_SKILL_TODAY=2026-05-25 python3 scripts/run.py test/real_program_3rd_input.json scripts/real_announcements.json`로 실행(원문 마감 2026-06-08 이전 시점으로 시뮬레이션 필요 — 오늘 날짜로 돌리면 세 공고 다 마감 지나 매칭 0건).
  - **결과: `lock_state=DRAFT`, `overall_confidence=0.35`, `overall_pass_recommendation=false`.** 사용자 사전 안내대로 "실제 합격 사례도 형식적으로는 완벽하지 않을 수 있다"는 것이 그대로 재현됨 — 버그가 아니라 구조적으로 예상된 결과. 원인 3가지:
    1. **profile 최상위 자격 플랫필드(`biz_type`/`founded_date`/`employees`/`annual_revenue_krw`/`region`) 전부 없음** → `기업형태` 자격기준이 "미확정"으로 처리되어 `eligibility_confidence=0.5`, 초안의 `1_사업개요`/`4_팀_역량`/`6_기대효과` 섹션에 `[확인 필요]` 플레이스홀더가 남음. 원인: 확보한 "합격 사업계획서" PDF는 <서식2> 사업신청서의 "표지"(설립년월일/상시근로자수 등을 적는 온라인 입력 항목) 없이 본문(추진전략/수행역량/파급효과 서술)과 산출물 시안만 담고 있어서, 애초에 이 플랫필드 값 자체가 소스 자료에 없음. `test/my_business_profile_input.json`(mo,on)도 동일한 구조적 한계로 이미 DRAFT/0.35였음 — 이번 3번째 공고도 같은 패턴 재확인.
    2. **`documents_status`를 전부 "확인 필요"로 둠(추측 안 함)** → PSST-Support fail, judge_panel "자격·규정 심사위원" warning. 원인: 합격 사업계획서 PDF 자체에는 소상공인24 온라인 신청서상의 서류 준비상태 자가진단 정보가 없음 — 실제로 서류를 다 갖췄을 가능성이 높지만(합격했으므로), 원문에 없는 걸 준비완료로 추측해서 채우면 이 스킬의 "모르면 낙관적으로 처리하지 않는다" 원칙 위반이라 의도적으로 비워둠.
    3. **`budget_detail` 총액(111,200,000원, 정부지원금+기업부담금 합계) > `max_grant_krw`(100,000,000원, 정부지원금 단독 상한)** → judge_review에 "예산계획 총액이 지원한도를 초과함" 경고. 실제로는 정부지원금 100,000,000원 + 기업부담금(자부담) 11,200,000원으로 지원한도를 정확히 충족하는 정상적인 예산 구성이지만, `budget_detail`이 정부지원금분과 자부담분을 구분하지 않고 총 사업비를 한 리스트에 나열하는 구조라 `check_budget_compatibility()`가 이를 "지원한도 초과"로 오판함. **이건 이 3번째 사업자 데이터만의 문제가 아니라 스킬 스키마 자체의 구조적 공백**(budget_detail에 "정부지원금분/자부담분" 구분 필드가 없음) — mo,on 사례(`real_program_input_simulated.json`)에서도 총 예산이 지원한도를 크게 초과해 같은 경고가 떴던 것과 동일 계열의 known limitation. 즉시 로직 수정하지 않고 기록만 함(사용자 지시).
      - **[2026-07-09 세션에서 스키마 수정으로 해결]** 아래 "budget_detail 정부지원분/자기부담분 구분 (v0.5.3)" 섹션 참고 — `fund_source` 필드 도입으로 이 오탐은 해소됨(재검증 결과 confidence 0.35→0.40, 이 예산 경고 소멸). 단 이 3번째 사업자 데이터 자체에는 항목별 `fund_source`를 채우지 않았음(원문에 항목별 구분이 없어 추측 금지) — 자세한 내용은 새 섹션 참고.
    4. **Traction(PSST) fail의 오해 소지 있는 메시지**: `expected_outcomes`를 상세히 채웠음에도 불구하고 그 안의 `revenue_goals`(매출 목표 금액환산 - 원문에 근거 없어 정직하게 `[확인 필요]`로 표기)에 "[확인 필요]" 문자열이 하나라도 있으면 `assess_psst()`의 traction 체크가 "expected_outcomes가 없어"라는 메시지로 fail 처리함 — 실제로는 필드가 없는 게 아니라 일부 하위 항목만 정직하게 비워둔 것인데, 에러 메시지가 "전체가 없다"는 뉘앙스로 나와 오해 소지가 있음. "모르면 [확인 필요]로 낙관 처리 안 한다" 원칙과 "PSST-Traction 체크의 블런트한 문자열 검사" 사이에 실질적 긴장 관계가 있다는 것을 확인 — 정직하게 gap을 표시할수록 자동판정에서 더 불리해지는 구조. 향후 개선 여지로만 기록.
  - **심사위원 rubric 키워드 매핑(4번 지시 검증) — "AI" 과다매칭 재현 여부**: 이 공고는 AI 관련 공고가 아니라서(제품 개발/사업화 공고) `AI 필요성 심사위원`(keywords: AI/기술/차별성/혁신)이 `mapped_rubric_items=[]`로 정확히 매핑 안 됨 — 지난 라운드에 발견된 "AI" 키워드 과다매칭(성장가능성 항목까지 잘못 잡힘) 문제는 **이번엔 재현되지 않음**(해당 문제는 공고 자체가 AI 관련일 때만 발생하는 것으로 재확인).
    - 대신 **새로운 종류의 매핑 갭 발견**: `예산·증빙 심사위원`(keywords: 예산/자금)과 `성과·확장 심사위원`(keywords: 성과/확장/고용/사회적)이 이 공고의 rubric 항목 텍스트("추진전략 - ...사업비 비목별 집행계획", "파급효과 - 사업수행 기대효과")와 전혀 매칭이 안 됨 — 원인은 이 공고가 "예산/자금" 대신 "사업비"라는 표현을, "성과" 대신 "기대효과"라는 표현을 씀. 과다매칭이 아니라 **과소매칭(키워드 커버리지 부족)** 사례. `JUDGE_DEFINITIONS[*].rubric_keywords`가 아직 "사업비"/"기대효과" 같은 흔한 동의어를 커버하지 못함 — 향후 키워드 테이블 보강 여지(즉시 수정하지 않음, 기록만).
  - `judge_panel_review.warning_count=3`(자격·규정/예산·증빙/성과·확장), `deduction_map.triggered_issues=3`(예산 근거 누락/자격 증빙 미확보/산출물 미정의) — 전부 위 1~4 원인과 1:1 대응, 새로운 미지 버그 없음.
- **[확인 필요]로 남긴 필드 목록** (추측하지 않고 명시적으로 비워둔 항목, 원문 재확인 시 채울 것):
  - 공고 쪽: 업종별 상시근로자·매출액 차등기준, 지원제외업종 전체 코드, 신청유형③(공동신청) 3억원 한도, "로컬창업가" 정의, 발표평가 세부배점(별도자료로는 확보했으나 공고문 자체엔 없음)
  - 사업자 프로필 쪽: `brand_meaning`(원문에 없어 제품소개문으로 대체), 대표자 보유 자격증/교육이력, 신규채용예정자 교육계획, `revenue_goals`의 단가/금액환산 매출목표(원문은 판매건수·비율 목표만 있고 금액환산 없음), `documents_status` 5건 전체(원문에 자가진단 정보 없음), profile 최상위 `biz_type`/`founded_date`/`employees`/`annual_revenue_krw`/`region`(신청서 표지 양식 정보 - 확보한 PDF에 미포함)
- **회귀테스트 12개 전부(6개 정식 + AI판사 대조군 2개 + synthetic 4개) 재확인 완료, 전부 기존과 동일한 lock_state/confidence로 통과** — 3번째 공고 추가가 기존 케이스에 영향 없음(특히 `real_program_input.json`은 오늘 날짜 기준 세 공고 다 마감 지나 매칭 0건인 것도 동일 유지).

## 문서명 fuzzy 매칭 도입 (v0.5.2) — 2026-07-08 세션

- **배경**: 기존 known limitation #6 — `documents_status`의 `document_name`이 공고 `required_documents` 문자열과 정확히 일치해야만 매칭됨. `match_document_status()` 신설로 "완전일치 → 정규화(공백 제거) 후 완전일치 → 화이트리스트 동의어 그룹 매칭" 3단계로 확장. `RUBRIC_SYNONYMS`/`_rubric_covered()`와 동일 원칙(등록된 것끼리만 매칭, 짧은 어근 무분별 부분매칭 금지 — v0.4.0 "창업"/"사업" 과다매칭 실수를 반복하지 않는다)을 그대로 적용. `DOCUMENT_NAME_SYNONYM_GROUPS`에 안전하게 등록 가능한 4개 그룹만 등록(사업자등록증류/중소기업확인서류/법인등기부등본류/부가가치과세표준증명류). 매칭 실패 시 이유를 `document_match_notes`에 기록(향후 동의어 테이블 보강용).
- **자체 발견 및 수정한 버그(사용자에게 보고하기 전에 유닛테스트로 캐치)**: 최초 구현에서 "정규화" 단계가 공백뿐 아니라 괄호 안 내용까지 제거하도록 만들었더니, `납세증명(국세)`와 `납세증명(지방세)`처럼 **괄호 안 내용이 서로 다른 문서를 구분하는 유일한 단서인 경우**가 둘 다 `납세증명`으로 붕괴해 화이트리스트 등록 여부와 무관하게 2단계(정규화)에서 곧바로 오매칭(충돌)되는 것을 유닛테스트(`match_document_status()` 직접 호출)로 발견함. 원인: 괄호 제거를 "정규화"(전체 문서명에 무조건 적용)와 "동의어 그룹 조회"(화이트리스트 멤버십 확인) 두 단계에 모두 넣어서, 화이트리스트 밖의 조합도 정규화 단계에서 이미 충돌해버림. **수정**: 괄호 제거를 동의어 그룹 조회 전용 함수(`_normalize_doc_name_for_synonym`)로만 국한하고, 일반 "정규화" 단계(`_normalize_whitespace`)는 공백 제거만 하도록 분리. 재검증 결과 `납세증명(국세)`/`납세증명(지방세)`는 더 이상 매칭되지 않음(unmatched로 정확히 처리), 나머지 안전한 케이스(사업자등록증 계열 등)는 정상 매칭 유지.
- **재테스트 결과 — `my_business_profile_input.json`**: 필수서류 5건 중 `'사업자등록증 사본'`이 동의어 그룹(그룹 0: 사업자등록증류) 매칭으로 `documents_status`의 `'사업자등록증'` 항목과 연결됨(이전엔 unmatched). 단, 그 `'사업자등록증'` 항목 자체가 원본 데이터에 `"예비창업자 기준 미보유 또는 확인 필요"`로 기재되어 있어 `prepared=False`로 정확히 집계됨 — **매칭은 성공했지만 실제로 서류가 준비되지 않은 상태라 결과는 이전과 동일**(`prepared_count=0/5`, PSST-Support 여전히 fail, `lock_state=DRAFT`, `confidence=0.35`, 전과 완전히 동일). 나머지 4건(`사업계획서 (지정양식)`/`중소기업(소상공인) 확인서`/`4대보험 가입자 명부`/`국세/지방세 완납증명서`)은 동의어 테이블에 등록된 후보가 없어 여전히 unmatched — 특히 `국세/지방세 완납증명서`는 위에서 설명한 충돌 위험 때문에 의도적으로 그룹 미등록 상태로 남겨둠.
- **재테스트 결과 — `real_program_input_simulated.json`**: 필수서류 6건(`참가신청서`/`경력단절여성 사유 확인서`/`서약서 및 동의서`/`사업계획서 (지정양식, [붙임1])`/`건강보험자격득실확인서`/`사업자등록여부 확인 서류(사실증명)`) 전부 여전히 unmatched. 원인: 이 공고의 필수서류 명칭들이 애초에 등록된 4개 동의어 그룹(사업자등록증/중소기업확인서/법인등기부등본/부가가치과세표준증명)과 무관한 어휘라서(`documents_status`에 대응 항목 자체가 없음) — **서류명 표기 차이 문제가 아니라 애초에 대응하는 문서가 documents_status에 없는 케이스**이므로 fuzzy 매칭 확장으로 해결될 사안이 아님. `lock_state=DRAFT`, `confidence=0.35`로 이전과 완전히 동일.
- **회귀테스트 12개 전부(6개 정식 + AI판사 대조군 2개 + synthetic 4개) 재확인 완료, 전부 기존과 동일한 lock_state/confidence로 통과** — 문서명 fuzzy 매칭 도입이 기존 케이스 결과에 영향 없음(`sample_input_ideal.json`은 5건 전부 `match_type=exact`로 기존 완전일치 동작 그대로 보존됨). `real_program_3rd_input.json`(3번째 공고, `GOV_SKILL_TODAY=2026-05-25`)도 5건 전부 `match_type=exact`로 fuzzy 로직에 영향받지 않고 기존 DRAFT/0.35(judge_panel 경고 3건, deduction 이슈 3건: 예산근거누락/자격증빙미확보/산출물미정의) 그대로 재확인됨.
- **결론(과대 주장 금지)**: known limitation #6은 "완전 해결"이 아니라 **부분 해결**임 — 화이트리스트에 명시적으로 등록된 4개 그룹 범위 내에서만 표기 차이를 흡수하고, 그 밖의 표현 차이는 여전히 미매칭으로 남는다. 실제 재테스트한 두 케이스(`my_business_profile_input.json`, `real_program_input_simulated.json`) 모두 `lock_state`/`confidence`가 이전과 전혀 바뀌지 않았다 — 하나는 매칭은 됐지만 서류 자체가 미준비 상태였고, 다른 하나는 애초에 대응하는 documents_status 항목이 없었기 때문. 사용자 사전 안내대로 "무조건 pass로 바뀌어야 하는 건 아니다"가 그대로 확인됨.

## budget_detail 정부지원분/자기부담분 구분 (v0.5.3) — 2026-07-09 세션

- **배경**: 위 "3번째 실제 공고 추가" 섹션에서 발견된 스키마 공백(budget_detail이 총사업비만 표현하고 정부지원분/자기부담분을 구분하지 못해, 자기부담이 정상적으로 포함된 예산도 "한도 초과"로 오탐하는 문제)을 스키마 레벨에서 수정. 이 문제는 3번째 공고 하나만의 문제가 아니라 `real_program_input_simulated.json`(mo,on 사례)에서도 동일하게 나타났던 반복 구조적 공백이었음.
- **스키마 변경**: `manifest.yaml`의 `business_profile.budget_detail` 항목(v0.2.0 리스트 방식/v0.3.0 phase 방식 둘 다)에 `fund_source`("government"|"self", 선택 필드) 추가. 먼저 기존 스키마에 유사 의도 필드가 있는지 확인함 — `self_funding_note`(phase 방식에만 존재하는 자유서술 필드) 하나뿐이었고 구조화된 필드는 없어서, 사용자 제안대로 `fund_source`를 새로 추가하기로 함(임의 확정 아님, 기존 필드 확장 불가 확인 후 결정).
- **`check_budget_compatibility()` 수정**: 기존에는 `budget_detail` 총액을 그대로 `budget_criteria.max_grant_krw`와 비교했음. v0.5.3부터 `fund_source=="government"`로 명시된 항목의 합계만 한도 비교에 사용하도록 수정. `judge_review.budget_breakdown` 필드를 새로 노출해 `total_krw`(전체 총액)/`confirmed_government_krw`(정부지원분 확인분)/`confirmed_self_krw`(자기부담분 확인분)/`unresolved_krw`/`unresolved_count`를 항상 함께 보여줌 — 총액만 보여주고 끝내지 않고 어느 기준으로 판정됐는지 명확히 드러나게 함(지시사항 3번 반영).
- **후행 호환 판단 — 사람이 결정하도록 요청함(지시사항 4·8번)**: `fund_source`가 없는 기존 데이터(현재 `test/*.json` 전부 해당)를 어떻게 취급할지 임의로 정하지 않고, "전부 정부지원분으로 간주"(A안)와 "전부 확인필요로 제외"(B안) 두 방식을 실제로 시뮬레이션해서 6개 회귀테스트에 대한 영향을 사용자에게 보고함. **시뮬레이션 결과: 6개 정식 회귀테스트는 A안/B안 어느 쪽을 택해도 최종 `lock_state`/`confidence`/`judge_panel_review`/`deduction_map`이 전혀 달라지지 않았음**(차이는 오직 신규 3번째 공고 사례에서만 나타남 — A안은 기존과 동일하게 오탐이 남고, B안은 오탐은 사라지지만 "모른다"를 "문제없음"으로 보이게 하는 반대 방향의 부작용이 있었음). 이 결과를 사용자에게 보고한 뒤, 사용자가 **C안(확인 필요로 별도 표시)**을 선택함 — A안도 B안도 아닌 절충안:
  - 자동 판정(quality_gate/8인심사위원/감점전파)에는 `fund_source` 미지정 항목을 아예 반영하지 않음(B안과 동일하게 오탐 방지 우선 — `fund_source=="government"`로 명시된 항목의 합계만으로 한도초과를 판정).
  - 그러면서도 미지정 항목이 있다는 사실 자체는 `budget_breakdown.unresolved_note`에 "확인 필요" 안내문으로 별도 노출. 이 note는 `rejection_risks`/`budget_risks`에 넣지 않아서 8인심사위원 "예산·증빙" 심사위원이나 `deduction_map`의 자동 판정에는 전혀 영향을 주지 않음(`deduction_map`이 이미 쓰고 있는 "확인은 시키되 confidence는 다시 안 깎는다"는 원칙과 동일 패턴 적용).
- **재검증 — `real_program_3rd_input.json`(111.2백만원 케이스)**: `GOV_SKILL_TODAY=2026-05-25 python3 scripts/run.py test/real_program_3rd_input.json scripts/real_announcements.json`로 재실행. 예산 관련 오탐이 해소됨을 확인:
  - `overall_confidence`: 0.35 → **0.40** (감점위험 3건→2건으로 줄어 penalty 0.15→0.10)
  - `judge_panel_review.warning_count`: 3 → **2**, "예산·증빙 심사위원"이 `score=1,warning=True` → `score=5,warning=False`로 전환
  - `deduction_map.triggered_issues`에서 "예산 근거 누락" 소멸(2건 남음: 자격 증빙 미확보, 산출물 미정의 — 둘 다 예산과 무관한 별개의 실제 이슈, 지시사항 5번대로 그대로 남겨둠)
  - `budget_breakdown`: `{total_krw: 111,200,000, confirmed_government_krw: 0, confirmed_self_krw: 0, unresolved_krw: 111,200,000, unresolved_count: 8, unresolved_note: "예산 항목 8건에 fund_source(...)가 지정되지 않아... 사람이 직접 확인 필요"}` — **중요**: 이 3번째 사업자 데이터의 실제 8개 예산 항목에 `fund_source`를 채워 넣지는 않았음. 원본 합격 사업계획서(`합격)소상공인_생활문화_혁신지원_참여소상공인사업계획서.pdf`)의 "사업비 비목별 집행계획(세부)" 표에는 항목별 정부지원/자부담 구분 컬럼이 없고, "총사업비 111.2백만원(정부지원금 100백만원, 기업부담금 11.2백만원)"이라는 **총액 단위 구분 한 문장**만 존재함(공고 자체의 신청서 서식에는 기술개발/사업화 단계별로 정부지원금/기업부담금을 나누는 표가 있으나, 이 사업자가 실제로 그 표를 채운 버전은 확보하지 못함). 사용자에게 이 사실을 그대로 알리고 항목별로 임의 배정하지 않기로 확인받음(2026-07-09) — 즉 이번 개선은 "항목별로 정확히 확인해서 통과시킨 것"이 아니라 **"확인 안 된 상태를 정직하게 '확인 필요'로 남기고, 그로 인해 근거 없는 초과 경고만 제거한 것"**.
- **회귀테스트 12개 전부(6개 정식 + AI판사 대조군 2개 + synthetic 4개) 재확인 완료, 전부 기존과 동일한 `lock_state`/`confidence`/`judge_panel_review.warning_count`/`deduction_map.triggered_issues`로 통과** — `fund_source` 스키마 추가가 기존 결과에 전혀 영향 없음(모든 기존 테스트 파일이 `fund_source` 미지정 상태이므로 C안에 따라 자동 판정에서 완전히 배제되어, 기존 동작을 그대로 보존함).
- **`scripts/run.py` 동기화 마운트 truncation 재발 + 복구**: 이번 세션에도 `check_budget_compatibility()` 수정을 적용하는 과정에서 파일이 두 차례 잘리는 문제가 재발함(1차: `psst_fails = [...]` 문 중간에서 끊김, `main()`/`if __name__` 블록 소실 — `py_compile`로 감지됨. 2차: `outputs` 스크래치 마운트에서도 동일 증상 재현, `return output`의 마지막 부분이 "retu"로 끊김 — 이번엔 `py_compile`은 통과했지만 실행 시 `NameError`로 감지됨. 3차: `manifest.yaml` 수정 중에도 UTF-8 멀티바이트 문자 중간에서 끊기는 동일 패턴 재발). 매번 기존에 확립된 절차대로 `Read` 도구로 진짜 내용을 확보한 뒤 bash `cat > file << 'EOF' ... EOF` heredoc으로 직접 덮어써서 복구함(Edit/Write 도구를 최종 쓰기 단계에서 아예 거치지 않음). 매 복구 후 `wc -l`/`md5sum`/`py_compile` 또는 `yaml.safe_load` + 실제 실행 테스트로 검증.

## 심사위원 rubric 키워드 과소매칭 해소 (v0.5.4) — 2026-07-09 세션

- **배경**: "다음에 할 만한 작업" backlog 항목 — 3번째 공고(생활문화 혁신지원) 검증 중 발견된 `JUDGE_DEFINITIONS[*].rubric_keywords` 과소매칭("예산·증빙"/"성과·확장" 심사위원이 이 공고의 "사업비"/"기대효과" 표현과 매칭 안 됨, AI활용지원 공고의 "AI" 키워드 과다매칭과 대조되는 반대 방향 문제).
- **키워드 추가 전 확인**: 먼저 8인 전원의 `rubric_keywords` 테이블을 확인함(공고적합성: 적합/목적/부합, 자격규정: 자격/규정/요건, 문제정의: 필요성/문제/기술성, AI필요성: AI/기술/차별성/혁신, 실행계획: 실행/계획/사업화, 예산증빙: 예산/자금, 성과확장: 성과/확장/고용/사회적, 발표QA: 없음·항상 제외). "사업비"/"기대효과"와 유사 의도의 키워드가 이미 있는지 확인 후 없음을 확인.
- **충돌(과다매칭) 사전 검증**: `real_announcements.json`(3개 공고) + `sample_announcements.json`(3개 공고) 전체의 `scoring_rubric` 텍스트와 그 외 모든 JSON 필드를 정규식으로 스캔해서, "사업비"/"기대효과"가 무관한 단어(예: "사업비전"처럼 "사업비"를 우연히 포함하는 단어) 안에 우연히 포함되는 사례가 있는지 먼저 확인함 — 전부 실제 예산/성과 관련 문맥에서만 등장함을 확인한 뒤 추가함(v0.4.0에서 "창업"/"사업" 같은 짧은 키워드를 무분별하게 부분매칭 허용했다가 전 항목 과다커버로 회귀했던 실수를 반복하지 않기 위함).
- **추가한 키워드**: `예산증빙` 심사위원에 `"사업비"` 추가(`["예산","자금"]` → `["예산","자금","사업비"]`), `성과확장` 심사위원에 `"기대효과"` 추가(`["성과","확장","고용","사회적"]` → `["성과","확장","고용","사회적","기대효과"]`).
- **교차 검증 (지시사항 3번)**: 기존 2개 공고(경력단절여성/AI활용지원) + 3번째 공고(생활문화) 전부 재실행:
  - 경력단절여성 공고: rubric 텍스트에 "사업비"/"기대효과"가 아예 없어 매핑 변화 없음(기존과 완전히 동일).
  - AI활용지원 공고(과장 케이스 `synthetic_ai_judge_exaggeration.json` + 구체 케이스 대조군 `synthetic_ai_judge_concrete.json`): **"AI" 키워드 과다매칭 재발 없음** 확인 — `AI 필요성 심사위원`의 `mapped_rubric_items`가 이전과 동일한 3개 항목(AI활용 적합성 x2, 성장가능성-AI적용)만 그대로 유지됨. 과장 케이스는 여전히 `score=1,warning=True`, 구체 케이스는 여전히 `score=5,warning=False`로 정확히 구분됨(신규 키워드 2개가 이 공고 rubric 텍스트에 등장하지 않으므로 이론적으로도 영향 없음이 맞음).
  - 3번째 공고(생활문화): `예산·증빙 심사위원`이 "추진전략 - ...사업비 비목별 집행계획(50점)" 항목에, `성과·확장 심사위원`이 "파급효과 - 사업수행 기대효과(20점)" 항목에 각각 정확히 매핑됨(이전엔 둘 다 `mapped_rubric_items=[]`였음). `score`/`warning`은 매핑과 무관하게 이미 다른 신호(PSST 등)로 계산되던 값이라 그대로 유지됨(예산증빙: score=5/warning=False 유지, 성과확장: score=1/warning=True 유지 — PSST-Traction fail 때문, 매핑 변화와 무관).
- **회귀테스트 12개 재확인 완료 — 전부 기존과 완전히 동일한 `lock_state`/`confidence`/`judge_panel_review.warning_count`/`deduction_map.triggered_issues`.** 코드 구조상으로도 당연한 결과: `run_judge_panel()`에서 `score`/`warning`은 `mapped_rubric_items`를 채우기 전에 이미 다른 신호(자격미확정/미준비서류/결격위험/예산리스크/위험표현/PSST결과)로 계산되고, `mapped_rubric_items`는 그 이후 순수 표시용으로만 채워짐 — `rubric_keywords` 변경이 판정 결과 자체에 영향을 줄 수 없는 구조임을 코드로 재확인함.
- **[정직하게 기록] 완전 해소 아님, 부분 해소**:
  1. 이번에 지시받은 두 사례(예산·증빙↔사업비, 성과·확장↔기대효과)는 해소됨.
  2. 다만 이번 교차검증 중 3번째 공고의 **"수행역량 - 참여인력현황및경험/참여인력별 수행역할"(30점) 항목이 8인 중 어느 심사위원에도 여전히 매핑되지 않는다**는 것을 추가로 발견함. 이건 어휘 차이(키워드 보강으로 고칠 수 있는 문제)가 아니라, **스펙상 고정된 8인 심사위원 중 "팀/참여인력의 역량"을 평가 목적으로 하는 심사위원이 애초에 없는 구조적 공백**으로 판단됨. 억지로 기존 심사위원(예: 실행계획) 키워드에 "역량"/"인력" 등을 끼워 넣으면 그 심사위원의 실제 평가 취지("6개월 내 범위가 현실적인가")와 안 맞는 항목을 억지로 연결하는 셈이라, 8인 로직 자체는 스펙상 공고 불변이라는 원칙에 따라 이번 라운드에서는 손대지 않고 기록만 함(다음에 할 만한 작업에 새 항목으로 추가).
  3. 키워드 휴리스틱 자체의 근본 한계는 여전함 — 의미 기반(NLP) 매칭이 아니므로, 앞으로 새로운 공고에서 또 다른 표현("사업추진비", "실현효과" 등)이 나오면 같은 종류의 과소매칭이 재발할 수 있음. 이번 수정은 "지금까지 실제로 관찰된 2개 사례"를 메운 것이지, 이 휴리스틱 자체를 근본적으로 고친 것은 아님.

## 웹앱화 (review_app.html) — 2026-07-11~12 세션

- **배경**: 사용자 요청 "이걸 인웹형태나 앱으로 작동 할 수 있게 해줘". 앱스토어 배포는 아니고 지인에게 파일로 공유 가능한 형태를 원함 → **더블클릭으로 여는 단일 HTML 파일**로 구현(설치/서버/API 키 불필요). 기능 범위는 "전체 기능"(run.py의 자격심사/문서매칭/예산분리/PSST/8인심사위원/감점전파/quality_gate 전부), 입력 방식은 공고문·사업자서류 PDF/이미지 업로드, 자동 인식 방식은 "오프라인 자동추출 + 사람이 검토"(서버·클라우드 AI 호출 없음, pdf.js/Tesseract.js로 브라우저 안에서만 처리 후 사람이 편집).
- **`engine.js`** — `scripts/run.py`(v0.5.4)의 `review_application(business_profile, announcement, ref_date)` 경로(단일 공고 검토용 진입점, 배치 매칭 `match_programs`/`collect_and_extract_announcements`는 웹앱에 불필요해 포팅 대상에서 제외)를 JavaScript로 1:1 포팅. 상수 테이블(`EXAGGERATION_WORDS`/`RISK_PHRASE_DICTIONARY`/`DOCUMENT_NAME_SYNONYM_GROUPS`/`JUDGE_DEFINITIONS`(v0.5.4 키워드 포함)/`DEDUCTION_PROPAGATION_TABLE`)과 전체 함수(자격심사→문서fuzzy매칭→예산fund_source분리→초안작성→PSST→8인심사위원→감점전파→quality_gate)를 그대로 옮김.
  - **검증 방법**: Python `review_application()`을 직접 호출해 12개 케이스(정식 회귀 6 + AI판사 대조군 2 + synthetic 4)의 실제 출력 JSON을 새로 뽑고, 동일 입력을 JS 포팅본에 넣어 **딥 구조비교(재귀 diff)**로 완전히 동일한지 검증. 최종 **12개 케이스 전부 0 diff**(완전 일치) 확인.
  - **포팅 중 발견·수정한 실제 버그 2건**(둘 다 diff 비교로 잡아냄, 감으로 넘어가지 않음):
    1. `draft_application()`은 초안 문구의 "업력"/"대표자 연령"을 계산할 때 `review_application()`에 전달된 `ref_date`를 쓰지 않고 **항상 실제 오늘 날짜(`today()`)를 다시 호출**한다 — 원본 소스 자체의 기존 동작(자격심사는 `ref_date` 기준, 초안 문구는 실제 오늘 기준으로 서로 다른 날짜를 씀). 최초 JS 포팅에서는 이걸 놓치고 `ref_date`를 그대로 재사용해서 나이/업력이 어긋났음 — Python 원본과 diff로 발견, `now = new Date()`로 분리해 원본 동작 그대로 재현(버그를 "고친" 게 아니라 원본의 기존 동작을 정확히 재현한 것).
    2. Python의 `dict.get(key, default)`는 키가 아예 없을 때만 default를 쓰고, 키가 있는데 값이 `None`이면 `None`을 그대로 반환(문구에 "None"이 그대로 노출되는 원본의 사소한 표시버그 포함) — JS의 `??`/`||` 연산자는 이 구분을 못 해서 처음엔 항상 default로 대체해버리는 차이가 있었음. `pyGet()`/`pyNoneOnly()`/`pyRepr()` 헬퍼로 Python의 정확한 동작을 재현. 그 밖에 float(예: `matching_fund_ratio=0.0`)이 문구에 들어갈 때 Python은 `"0.0"`으로 찍지만 JS는 `"0"`으로 찍는 차이도 `pyRepr()`로 맞춤(정수 스키마 필드인 `employees` 등에는 이 float 강제를 적용하면 안 돼서 별도 `pyNoneOnly()`로 분리).
  - **`engine.js`는 Node에서도(테스트용) 브라우저에서도(실제 앱) 그대로 동작**하도록 `module.exports` 가드를 달아둠.
- **`review_app.html`** — 위 `engine.js` + 앱 로직(`app.js` 내용)을 하나의 파일로 합친 최종 결과물. 구조:
  1. 사업자 정보 입력(파일 업로드 자동인식 + 수동 폼: 기업형태/업종코드/설립일/지역/근로자수/매출/대표자생년월일/성별/경력단절여부/결격사유 체크박스/사업설명/팀경력/인증/예산항목(정부지원분·자기부담분 구분 select 포함)/기대효과)
  2. 공고문 정보 입력(파일 업로드 자동인식 + 수동 폼: 사업명/마감일/자격조건 전체/제외조건/필수서류/심사배점표/지원한도/자기부담비율/제외예산카테고리/페이지제한)
  3. 필수서류 체크리스트(2단계 필수서류 목록 기반 자동 생성, 사람이 준비상태 표시)
  4. "검토하기" 버튼 → `reviewApplication()` 호출 → 결과 렌더링(판정배너/판정이유/PSST 4구간/8인심사위원표/거절위험/과장표현/예산breakdown/감점전파/신청서초안 6섹션)
- **자동 인식(OCR/PDF) 레이어**: `pdf.js`(cdnjs, v6.1.200, `<script type="module">`로 로드)로 PDF 텍스트 레이어 추출, 텍스트 레이어가 거의 없는 스캔본이면 1페이지를 캔버스에 렌더링해 `Tesseract.js`(cdnjs, v6.0.1, `kor+eng` 언어팩)로 OCR 보완. 이미지 파일은 바로 Tesseract.js. **전부 브라우저 안에서만 실행되고 서버/API 키를 쓰지 않음**(사용자가 고른 "오프라인 자동추출" 방식 그대로).
  - 정규식 기반 필드 추정(`guessAnnouncementFields`/`guessProfileFields`): 마감일/업력조건/근로자수상한/지역/지원한도/자기부담비율/페이지제한/필수서류목록(공고), 기업형태/설립일/생년월일/지역/근로자수/업종코드/매출액(사업자서류)을 정규식으로 best-effort 추정. 한국어 금액 표현(`1억 5,000만원` 등) 파서(`parseKrwAmount`)와 날짜 패턴 파서(`findDatesInText`) 포함.
  - **추정값은 사용자가 아직 입력하지 않은 빈 칸에만 채워지고(이미 입력한 값은 덮어쓰지 않음), 자동 채움 필드는 노란색으로 표시**되어 사람이 반드시 확인하도록 설계(사용자가 선택한 "자동추출+사람이 검토" 원칙 그대로 구현). 인식된 원문 텍스트도 접이식으로 항상 볼 수 있게 함.
  - **검증**: Node에 최소 DOM 스텁을 직접 만들어(jsdom 설치 시도했으나 샌드박스 네트워크 정책상 npm registry 403으로 차단되어 미설치) `parseKrwAmount`(억/만/원 조합 6개 케이스 전부 정확), `findDatesInText`(YYYY-MM-DD/YYYY.MM.DD/YYYY년M월D일 3개 형식 전부 인식), `guessAnnouncementFields`/`guessProfileFields`(3번째 실제 공고 원문을 흉내낸 텍스트로 마감일/근로자수/지역/지원한도/자기부담비율/페이지제한/필수서류 전부 정확 추정)를 개별 검증. 이어서 폼 입력 → `buildBusinessProfile()`/`buildAnnouncement()` → `reviewApplication()` 전체 배선을 가짜 DOM으로 end-to-end 실행해 `fund_source` 구분(정부지원분/미지정)이 `budget_breakdown`에 정확히 반영되는 것까지 확인.
- **UI 단순화(알려진 한계)**: 실제 스키마는 `eligibility.biz_type`/`region`이 배열(예: `["법인","개인"]`)이지만, 비개발자 대상 폼에서는 "제한없음/법인만/개인만" 단일 선택으로 단순화함(실무상 대부분의 공고가 "법인+개인 모두 가능"=제한없음 이거나 한쪽만 제외하는 경우라 커버리지는 충분하다고 판단했으나, 법인·개인을 모두 허용하면서 제3의 형태만 제외하는 특이 케이스는 표현 불가). `eligibility.min_employees`도 UI에 노출하지 않음(실제 공고 3건 중 사용 사례 없어 생략).
- **파일 위치**: `review_app.html`(프로젝트 루트, 이 파일이 최종 배포 대상 — 지인에게 이 파일 하나만 공유하면 됨), `engine.js`/`app.js`(스크래치 폴더에만 존재하는 개발용 소스 — `review_app.html`은 이 둘을 인라인으로 합친 완성본이라 배포 시 `engine.js`/`app.js`는 필요 없음).
- **알려진 한계**:
  - 정규식 기반 자동 인식은 문서 서식이 조금만 달라도 못 잡을 수 있음 — 그래서 전 필드가 항상 수동 수정 가능하고, 자동 인식은 "시작점"일 뿐 최종 판단은 사람이 하도록 설계됨(엔진 자체의 known limitation과 동일 철학).
  - 스캔 이미지 OCR(Tesseract.js)은 저해상도·기울어진 스캔본에서는 정확도가 떨어질 수 있음 — 원문 텍스트 보기 기능으로 항상 대조 가능하게 함.
  - `engine.js`가 Python `review_application()`과 100% 동일하다는 것은 검증됐지만, `run.py`가 갖고 있는 known limitation(키워드 휴리스틱 한계, "수행역량" 항목 미매핑 등 위 섹션들 참고)은 웹앱에도 그대로 남아있음 — 웹앱화는 이식이지 로직 개선이 아님.

## 파일 배치 컨벤션
- **HANDOFF.md는 프로젝트 루트에만 둔다.** 하위 폴더(`gov-support-skill/` 등)에는 만들지 않는다. (과거 `gov-support-skill/HANDOFF.md`라는 오래된 사본을 삭제하려 했으나, 이 마운트 폴더의 파일 삭제 제한 때문에 실제로는 물리적으로 남아있을 수 있음 — 발견 시 내용을 신뢰하지 말고 이 루트 파일을 기준으로 삼을 것.)
- **`gov-support-skill/` 폴더는 사용자가 업로드한 원본 데이터 폴더**(예: `my_business_profile.json`, `정부지원사업_판정로직_확장스펙.md`, 공고 PDF들)이고 스킬 코드 저장소와는 별개다. `.gitignore`에 추가해서 git 추적 대상에서 제외함.


## 진행 중 이슈 / 알아둘 것
1. **outputs 폴더는 파일 삭제·덮어쓰기가 제한된 동기화 마운트다.** 기존 파일을 Edit 도구로 직접 수정하거나 Write로 덮어쓰면 간헐적으로 파일이 중간에 잘려서(truncated) 문법 오류가 난다(`wc -l`로 줄 수가 안 맞는 것으로 확인 가능). v0.5.0 작업 중에도 `scripts/run.py`, `manifest.yaml`, `HANDOFF.md`(이 파일 자체, 이번 라운드에도 Edit 1회 재현), `.gitignore`, `scripts/real_announcements.json` 전부에서 재현됨 — 파일 크기와 무관하게 발생. 재현되는 우회법: **기존 파일을 새 이름으로 `mv`(rename)한 뒤, 원래 경로에 완전히 새로운 내용으로 Write.** 매 수정 직후 `wc -l`/`py_compile`/`yaml.safe_load`/`json.load`로 검증할 것. 파일 삭제가 안 되므로(`rm` permission denied) 잘린 사본은 `*.truncated-<timestamp>` 이름으로 폴더에 남아있음(`.gitignore`에 이미 패턴 추가해둠) — 무시하면 됨. 반대로 바이너리 파일(`.bundle` 등)은 bash `cp`로 덮어쓰면 truncation 없이 정상 동작함(Edit/Write 도구 특유의 문제로 보임).
2. **같은 이유로 `git init`을 outputs 폴더 안에서 직접 실행하면 `.git/config`가 깨진다.** git 작업은 항상 `/tmp` 같은 완전히 자유로운 스크래치 공간에서 하고, 완료되면 `git bundle create ... --all`로 묶어서 단일 파일로 만든 뒤 bash `cp`로 outputs에 덮어쓴다(파일명 그대로 덮어쓰기 가능, 위 1번 참고). 이번 라운드에는 `/tmp/bundle_check2/restored`에 기존 bundle을 clone해서 작업 파일들을 복사해 넣고 커밋 → 새 bundle 생성 → `cp`로 교체하는 흐름을 반복 사용함.
3. **`judge_pass_recommendation`이 이제 형식요건 + PSST/8인심사위원 경고까지 반영한다(v0.5.0).** 다만 PSST/8인심사위원 판정 자체가 여전히 키워드·구조존재여부 기반 휴리스틱이다(숫자+단위 정규식, budget_detail 존재여부, 문서 준비여부 등) — 의미 기반 판단이 아니므로 최종 판단은 사람 몫이다. 특히 8인심사위원의 rubric 키워드 매핑(`JUDGE_DEFINITIONS[*].rubric_keywords`)은 공고마다 표현이 달라지면 매핑이 빗나갈 수 있다(위 "추가 라운드"의 "AI" 키워드 과다매칭 사례 참고).
4. **공고 자동 수집이 안 된다.** `collect_and_extract_announcements()`는 여전히 로컬 JSON 파일(목업 또는 손수 파싱한 실제 공고)만 읽는다. 기업마당/K-스타트업 API·PDF 자동 파싱 연동은 미착수.
5. **rubric 매칭(v0.4.0)과 PSST/8인심사위원 판정(v0.5.0)은 전부 키워드·구조 기반 휴리스틱이다.** 의미 기반(NLP) 매칭이 아니라서, 테이블/정규식에 없는 새로운 표현이 나오면 오탐/누락 가능하다. 이번 라운드에도 "300만 개" 만/억 단위 누락 버그가 실제로 발생했다(위 참고).
6. **문서명 fuzzy 매칭 — 부분 해결됨(v0.5.2).** `match_document_status()`로 완전일치 → 정규화(공백 제거) 후 완전일치 → 화이트리스트 동의어 그룹(4개: 사업자등록증류/중소기업확인서류/법인등기부등본류/부가가치과세표준증명류) 매칭까지 확장됨(아래 "문서명 fuzzy 매칭 도입" 섹션 참고). 단, 등록되지 않은 표현(그룹 밖 문서명)은 여전히 미매칭 — 화이트리스트 확장이 필요할 때마다 `document_match_notes`의 실패 사유를 참고해 수동으로 그룹을 추가해야 한다. `my_business_profile_input.json`/`real_program_input_simulated.json`은 이번 확장으로도 `lock_state`/`confidence`가 바뀌지 않음(전자는 매칭은 됐으나 서류 자체가 미준비, 후자는 애초에 대응 항목이 documents_status에 없음).
7. **위험표현 사전(9종)은 고정 세트로 시작했다.** 스펙 원문 비고: "새로운 탈락사례가 나오면 계속 업데이트되는 걸 전제". 표에 없는 새 과장 표현은 감지되지 않는다.
8. **혁신 소상공인 AI 활용지원 사업은 실제로는 2026-07-03 16시에 이미 마감됐다(오늘 2026-07-07 기준).** `real_program_input.json`류 "실제 오늘 날짜" 테스트로 돌리면 두 공고 다 마감 지남으로 제외된다 — 정상 동작. 이 공고를 마감 전 상태로 테스트하려면 `GOV_SKILL_TODAY=2026-06-2x` 같은 시뮬레이션 날짜가 필요하다(경력단절여성 공고는 그 시점 기준 반대로 이미 마감이라 자동 제외되므로 두 공고가 서로 겹치지 않게 격리됨).

## 실행 방법
```
python3 scripts/run.py test/sample_input_ideal.json                                    # READY_FOR_APPROVAL 재현 (목업 공고)
python3 scripts/run.py test/sample_input.json                                          # 정상이지만 서술형 필드 없어 DRAFT (목업 공고)
python3 scripts/run.py test/sample_input_edge.json                                     # 자격 데이터 일부 누락 -> DRAFT (목업 공고)
python3 scripts/run.py test/my_business_profile_input.json                             # 실제 mo,on 사업자 데이터 (목업 공고)
python3 scripts/run.py test/real_program_input.json scripts/real_announcements.json     # 실제 공고 2건 + 실제 오늘 날짜 (둘 다 이미 마감됨)
GOV_SKILL_TODAY=2026-03-15 python3 scripts/run.py test/real_program_input_simulated.json scripts/real_announcements.json  # 경력단절여성 공고 마감 전 날짜로 시뮬레이션
GOV_SKILL_TODAY=2026-06-20 python3 scripts/run.py test/synthetic_ai_judge_exaggeration.json scripts/real_announcements.json  # AI활용지원사업 마감 전 날짜로 시뮬레이션 (AI필요성 심사위원 과장 케이스)
GOV_SKILL_TODAY=2026-06-20 python3 scripts/run.py test/synthetic_ai_judge_concrete.json scripts/real_announcements.json     # 동일 공고, 구체적 AI계획 케이스(대조군)

# v0.5.0 합성 결함 테스트 (신규 로직 발동 확인용, 정식 회귀 스위트 아님)
python3 scripts/run.py test/synthetic_risk_phrases.json              # 위험표현 사전 4건 검출 확인
python3 scripts/run.py test/synthetic_psst_problem_fail.json         # PSST-Problem만 FAIL 확인
python3 scripts/run.py test/synthetic_judge_panel_equipment.json     # 예산·증빙 심사위원 즉시경고 확인
python3 scripts/run.py test/synthetic_deduction_qualification.json   # 자격증빙미확보 -> 실행/발표 전파 확인
```
결과는 stdout(JSON)로 출력되고, quality_gate 미달/DRAFT 유지 이벤트는 `test/failure_log.jsonl`에 append됨.

## 다음에 할 만한 작업 (제안, 아직 미착수)
- PDF/HWP 공고문 자동 파싱
- ~~문서명 fuzzy 매칭~~ → 2026-07-08 세션에서 부분 구현(화이트리스트 동의어 그룹 4개, 위 "문서명 fuzzy 매칭 도입" 섹션 참고). 완전 해결 아님 — 아래 항목으로 계속:
- `DOCUMENT_NAME_SYNONYM_GROUPS` 화이트리스트 확장 검토 (실제 사례에서 `document_match_notes` 실패 사유가 쌓이면 안전하게 확장 가능한 것부터 추가. 단 괄호 안 내용이 문서를 구분하는 유일한 단서인 경우(국세/지방세 납세증명서 등)는 등록 금지 원칙 유지)
- `collect_and_extract_announcements()`를 실제 공고 소스(API/크롤러)에 연결
- 위험표현 사전(9종)을 실제 탈락사례 누적에 따라 계속 확장할지 검토
- PSST 숫자+단위 정규식을 더 다양한 한국어 수량 표현(예: "3배", "절반", 서수 등)까지 인식하도록 넓힐지 검토
- 8인심사위원 rubric 키워드 매핑 테이블을 공고 사례가 늘어나면서 보완 (특히 "AI" 같은 짧은 키워드의 과다매칭 문제)
- `test/synthetic_*.json` 6종(기존 4 + AI심사위원 대조 2)을 정식 회귀테스트 스위트에 편입할지 결정 (현재 보류 상태)
- 지자체별/타 부처 사업 스키마 확장 시 `eligibility` 스키마 필드 보완
- ~~실제 공고 3번째("소상공인 생활문화 혁신지원" 등, gov-support-skill/ 폴더에 PDF 이미 존재)도 필요 시 추가 파싱~~ → 2026-07-08 세션에서 완료(위 "3번째 실제 공고 추가" 섹션 참고)
- ~~`budget_detail`에 "정부지원금분/자부담분" 구분 필드 추가 검토~~ → 2026-07-09 세션에서 완료(위 "budget_detail 정부지원분/자기부담분 구분 (v0.5.3)" 섹션 참고). `fund_source` 필드 신설 + 미지정 항목 처리 방식은 사용자 결정(C안: 자동판정 제외 + 참고정보로만 노출)
- ~~`JUDGE_DEFINITIONS[*].rubric_keywords`에 "사업비"(예산 동의어), "기대효과"(성과 동의어) 등 흔한 동의어 보강 검토~~ → 2026-07-09 세션에서 완료(위 "심사위원 rubric 키워드 과소매칭 해소 (v0.5.4)" 섹션 참고). 지시받은 2개 사례는 해소, 키워드 휴리스틱 자체의 근본 한계는 여전함(부분 해소)
- **[신규 발견, 2026-07-09]** 3번째 공고의 "수행역량"(참여인력 경험/역할) 항목이 8인 중 어느 심사위원에도 매핑 안 됨 — 어휘 문제가 아니라 "팀/참여인력 역량"을 평가하는 심사위원이 8인 세트에 애초에 없는 구조적 공백. 기존 심사위원에 억지로 끼워맞추지 않기로 함(8인 로직은 스펙상 공고 불변 원칙). 9번째 심사위원 신설 여부는 스펙 원문(`정부지원사업_판정로직_확장스펙.md`) 재검토 후 사람이 판단해야 함 — 이번 세션에서는 손대지 않음
- PSST-Traction fail 메시지가 "필드 없음"과 "필드는 있으나 일부만 [확인 필요]"를 구분하지 못하는 문제 개선 검토
- **[신규, 2026-07-12]** `review_app.html`의 정규식 기반 자동 인식기를 더 다양한 실제 공고/사업자서류 서식으로 테스트해서 `guessAnnouncementFields`/`guessProfileFields` 커버리지 넓히기 (현재는 3번째 공고류 서식 기준으로만 검증됨)
- **[신규, 2026-07-12]** `eligibility.biz_type`/`region`을 웹앱 폼에서도 다중선택 가능하게 확장할지 검토 (현재는 단일선택으로 단순화됨 — 위 "웹앱화" 섹션 "UI 단순화" 참고)

## 관련 문서

- [[1. Projects/클로드 정부지원사업 ai/gov-support-skill/정부지원사업_판정로직_확장스펙|정부지원사업_판정로직_확장스펙]]
- [[1. Projects/클로드 정부지원사업 ai/gov-support-skill/README|gov-support-skill 폴더 안내 (온천꽃집 AI활용지원 신청자료)]]
- [[4. Archive/정부지원_완료건/소상공인생활문화_온천꽃집_선정건_2026-07/사업계획서 최종제출본/최종 사업계획서|온천꽃집 "생활문화 혁신지원" 선정건 최종 사업계획서 (완료·별개 공고, 4. Archive)]] — 최종 산출물: `발표자료/최종.pptx`, `최종 슬라이드/`(슬라이드0001~0012.jpg), `이미지/`(증빙), `기타서류.pdf`, 업무협약서 2건(따오기 호텔·신라호텔). 가이드: [[3. Resources/정부지원사업_자료/소상공인 생활문화 혁신지원 작성용 전자책|소상공인 생활문화 혁신지원 작성용 전자책]]
- [[1. Projects/클로드 정부지원사업 ai/마이그레이션_diff_리포트_v1_to_v2|마이그레이션_diff_리포트_v1_to_v2]]
- [[클로드 ai 자동화/future-vision|future-vision]]
- [[1. Projects/클로드 정부지원사업 ai/SKILL|SKILL]]
- [[ai공장짓기/설계노트/2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)|2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)]]
- [[ai공장짓기/failure_log|failure_log]]
- [[2. Areas/핵심맥락|핵심맥락]]

## 현재 상태 (2026-07-17 기준 — 이 섹션이 최신 정본) [k9cjhmw7z9]

2026-07-13 이후(T7~T11) 진행분 요약 — 세부는 [[1. Projects/클로드 정부지원사업 ai/기능_인덱스|기능_인덱스]]와 decision-log §14~§20 참조.

- **T7 공고 수집기**: bizinfo 단일소스, raw→candidate(추출)→사람검수 3계층 설계(§14) → 3사업(온천꽃식물원·대륙창업·모온) 상시매칭으로 확장(§15) → `scripts/collector/` 구현 완료(2026-07-16). API 실응답은 샌드박스 네트워크 차단으로 미검증.
- **T8 발표 뒷단 8 stage**(선정접수→PPT초안→**승인**→발표대본/QNA→**승인**→저장): 설계(§17)+manifest v2+mock 구현 완료, 테스트 5종 PASS, 헌장 §5 개정(발표자료 하위공정 승인 규정) 완료.
- **T9 end-to-end 연결**(§18): 홍재우 9번째 심사위원(20개 중 5개 구현, 강제반려 검증) 반영, 소제목:내용 포맷 전환, 수집기↔매칭 파이프라인 연결(검수완료분만, 우회 없음 확인), PPT/QnA/발표대본 실물화(python-pptx, 규칙기반 템플릿). 회귀+발표뒷단 테스트 전부 PASS. 품질이슈(PPT초안에 안내문·개인정보동의서 혼입)는 범위 밖으로 이월.
- **T10**: bizinfo API 키(`X9HC6x`) 발급 확인 완료, `config.yaml` 저장. 실응답 검증은 실제 실행 환경(혜미 PC+작업 스케줄러) 필요. → ✅ 완료(2026-07-17, 근거: 세션로그 추가기록11) — 로컬 Claude Code 세션에서 실제 bizinfo API 호출 성공, 진짜 공고 1,496건 실시간 수집 + 3개 사업체 매칭 후보 156(온천꽃식물원)/142(대륙창업)/3(모온)건 생성(`scripts/inbox/candidates_2026-07-17.json`). 일부 공고 마감일 파싱 실패는 경고만(차단 아님).
- **T11 블라인드 테스트**(생활문화 혁신지원, 온천꽃식물원): 실제 합격서 미참조 입력으로 초안 생성, eligibility 1.0 매칭이나 `judge_pass_recommendation=false`(예산근거누락 등 3건) → `lock_state=DRAFT`. 아이템·팀·예산·기대효과 4섹션이 `[확인 필요]`로 정직하게 비워짐.
- **2026-07-17(§19 판정3~5)**: 예산배분/기대효과 AI 초안 제안(`[AI 제안]`/`[확인 필요]` 구분) 추가, "대표자 정보"→"대표자 연령" 라벨 정정(블라인드 원칙 주석), 팀원 플레이스홀더 자동 추가(rubric 조건부).

**다음 할 일**: ①bizinfo 키 재확인 후 매일 07:00 스케줄 등록 → 키 재확인은 ✅ 완료(2026-07-17, 실제 1,496건 수집 성공으로 확인됨), 남은 건 작업 스케줄러 등록뿐 + 수집된 후보 156/142/3건 검수(reviewed:true 표시) ②PPT초안 앵커 절단 정제(안내문·개인정보동의서 혼입 제거) ③PPT/대본/QNA 실 LLM 연동(QNA는 "5개 만능답변 템플릿" 구조로 재설계 필요) ④run.py 버전 헤더 정리(v0.5.4→반영 안 됨) ⑤홍재우 나머지 15개 판단기준.

## 후보 156건 지역필터 미적용 발견·수정 + 모온 사업정보 확정 (2026-07-19, [hyemi] Cowork 세션)

- **버그 발견(혜미 지적)**: T10에서 만든 candidate 156건(온천꽃식물원)이 `promote_candidates.py`의 `min_keyword_match=1` 로직 때문에 **제목에 "소상공인" 같은 키워드 1개만 걸리면 후보로 승격**되고, 지역(소재지)·대표자 나이는 전혀 검증하지 않은 채로 나온 것이었음. 실측: 156건 중 116건(74%)이 경남이 아닌 타 시/도 지자체 전용 공고(경북25·전남광주18·경기9·대전9 등)라 애초에 신청 자격이 없었음. 원인은 `collect_bizinfo.py`의 `RAW_SCHEMA_FIELDS`(title/agency/url/pblancId/announcement_date/deadline/attachment_links)에 지역/연령 필드 자체가 없고, `promote_candidates.py`가 제목 텍스트 키워드 매칭 1개만으로 승격시키는 구조였기 때문 — 사람 검수 게이트가 있으니 괜찮다고 생각했지만, 실제로는 검수 부담을 줄이는 사전 필터가 전혀 없었던 것이 문제.
- **1차 조치(코드 미변경, 후처리 필터)**: `promote_candidates.py`/`collect_bizinfo.py` 본체는 건드리지 않고, 검수용 엑셀을 만드는 단계에서 2단계 지역필터를 적용해 156건→28건(온천꽃식물원·대륙창업)으로 축소:
  1. agency가 "경상남도" 또는 중앙부처(중소벤처기업부/농림축산식품부/조달청/지식재산처 등)인 것만 남김(1차, 40건).
  2. 그중에서도 제목에 창녕·부곡 이외의 구체적 지명(함안/하동/거제/타 시도명/타 지역 창조경제혁신센터명 등)이 있으면 "그 지역 소재 사업자 전용"으로 보고 추가 제외(2차, 28건).
  - ⚠ 표시 2종도 추가: 업력요건 의심("백년소상공인"류 — 보통 15년↑ 요구, 온천 11년·대륙 12년은 미달 가능), 창업트랙 애매(원래 candidate의 `unresolved`에 이미 있던 신호를 노출).
  - **정식화는 아직 안 함** — `promote_candidates.py`에 지역 사전필터 로직을 실제로 넣을지는 다음 스크래핑 라운드 전에 별도 판단 필요(이번엔 엑셀 생성 스크립트에서만 임시 적용, `scripts/inbox/candidates_*.json` 원본은 안 건드림).
  - 산출물: `scripts/inbox/정부지원_후보검수_2026-07-19_v2.xlsx` (시트1: 온천꽃식물원·대륙창업 28건 검수용, 시트2: 요약, 시트3: mo,on 범용 프로그램 웹검색 결과).
- **`business_profiles.yaml` 갱신**: 대표자 생년월일 확보 — 온천꽃식물원 이문숙(1969-08-30), 대륙창업 박수길(1964-06-05, 청년/시니어 창업 트랙 자격판정용). `region`에 "부곡면" 추가(창녕군 내 세부 위치, 지역필터 정밀화용). 모온 `industry`를 "SaaS(산모 회복 기록 관리) + 출장형 산모 회복 컨디셔닝"으로 확정, `biz_category_strategy_note`/`search_strategy_note` 신규 필드 추가(아래 참고).
- **모온 사업정보 확정(혜미 지시)**: SaaS + 출장 산후관리 서비스, 진주시 소재 예정. "괜찮은 지자체/정부 지원사업이 있으면 그거에 맞춰 창업하고 바로 지원한다"는 전략이라, 오늘 열려있는 공고가 아니라 **연중 상시/매년 재공고되는 범용 트랙**을 웹검색으로 조사(bizinfo 스크래핑 결과만으로는 부족 — 그건 "오늘 열린 공고"만 잡음). 조사 결과 6개(초기창업패키지/여성기업육성사업/진주형 1인 창조기업 육성/청년창업사관학교/진주창업지원센터 입주/진주시 신규고용보조금)를 엑셀 3번째 시트에 정리. **⚠ 청년창업사관학교는 대표자(혜미) 만 39세 이하 여부 확인 필요**(미확인) — 초과 시 대상 아님.
- **업종(업태/종목) 신고 전략 — 법률 자문 아님, 사실관계만 정리, 확정은 세무사·행정사 확인 후**: 혜미가 "카페→제과점처럼 법적 제약 적은 쪽으로" 요청. 웹검색 결과, 한국에서 "안마"(수기요법)는 의료법 82·88조상 시각장애인 안마사 전용이며 무자격 영리 안마는 3년 이하 징역/1천만원 이하 벌금 대상. 다만 "마사지업"은 한국표준산업분류상 별도 업종코드(930208)로 존재하고, 업계 관행상 "안마"라는 표현만 피하면(스웨디시/테라피/케어 등으로 명칭) 마사지업(930208)·피부미용업(930205)·체형관리서비스업(930209) 중 하나로 등록하는 사례가 많음 — 다만 판례가 갈려 완전히 안전하다고 단정할 순 없는 회색지대. 모온은 이미 미용사(피부) 국가자격증을 보유하고 있어 **"피부미용업(930205)"으로 등록 + 서비스명은 "마사지" 대신 "회복 케어/바디 컨디셔닝" 등으로 표기**하는 방향이 자격증과도 맞고 리스크도 낮아 보이는 후보안 — 단 확정 아님, `business_profiles.yaml`에 `[확인 필요]`로 남겨둠.

## 후보 검수 결과 반영 + 7건 원문 확인 (2026-07-19 같은 세션 이어서, [hyemi])

- **검수 반영**: 혜미가 엑셀에 표시한 28건 검수 결과(적합/후보 8, 부적합 4, 나머지 15는 "관심없음=제외"로 확정)를 `scripts/inbox/candidates_2026-07-17.json`에 반영 — 해당 9건에 `reviewed:true`+`reviewer_note`(승인 사유), 부적합 4건엔 `reviewer_note`(거절 사유)만 기록. `run.py --profiles`로 매칭엔진을 실행해 `reviewed:true` 카드만 정확히 읽히는 것 확인(다만 candidate 카드는 여전히 eligibility/budget 등 본문 필드가 null이라 아직 매칭 0건 — 정상, 아래 참고).
- **7건(투자연계 LIPS·통합공고 제외) 원문 확인(Claude in Chrome로 bizinfo 상세페이지 직접 열람)**:
  - **⚠ 정정 발견**: "제11회 소상공인 쇼케이스데이"(혜미가 적합으로 표시)는 실제로 **"창업 7년 이내 소상공인"** 자격요건이 있음 — 온천꽃식물원(11년)·대륙창업(12년) 둘 다 초과라 **부적격**으로 정정(`reviewed:false`로 되돌림, 사유 기록). 제목만으로는 알 수 없던 조건이라 원문 확인이 실제로 오류를 잡아낸 사례.
  - 나머지 6건은 전부 자격 문제 없음 확인 — 법률세무노무 상담/찾아가는 디지털교육/유통플랫폼MD상담회/온라인판로지원/IP출원지원사업/경영안정바우처(매출 6천만원으로 요건 충족, 1개사 25만원 한도). 상세 자격·신청기간·신청방법·문의처는 각 candidate의 `reviewer_note`에 기록.
  - **구조적으로 중요한 발견**: 이 7건은 전부 "PSST 사업계획서 심사형" 그랜트가 아니라 **간단 신청형(무료상담/바우처/교육/판로지원 서비스)** — 기존 엔진(`draft_application`/8인심사위원/PSST)은 생활문화혁신지원·초기창업패키지처럼 경쟁형 사업계획서 심사에 맞춰 설계된 것이라 이런 유형엔 안 맞음. 즉 이 8건(쇼케이스데이 제외)은 신청서 초안을 만들 필요 없이 **각자의 신청 사이트(네이버폼/판판대로/소상공인24/지역지식재산센터 등)에서 바로 신청하면 되는 것들** — 매칭엔진이 "매칭 0건"이라고 뜨는 게 버그가 아니라 애초에 이 엔진이 처리할 대상이 아니었던 것.
  - **다음에 할 만한 작업(신규)**: 향후 candidate 승격 시 "간단신청형 vs PSST사업계획서형"을 구분하는 필드를 추가할지 검토(현재는 사람이 원문을 읽어야만 구분 가능). 업력요건(예: "창업 O년 이내")을 raw 단계에서부터 추출하도록 `collect_bizinfo.py`/`promote_candidates.py`를 보강하면 이번 같은 사후발견을 줄일 수 있음 — 이번엔 손대지 않고 기록만.

## mo,on — 초기창업패키지(일반형) 실제 공고 정본화 + 드라이런 (2026-07-19 같은 세션 이어서, [hyemi])

- **배경**: 혜미 지시("초기창업패키지나 지난 공고들로 돌리자") — 모온은 아직 미창업이라 bizinfo 검수 대상 후보가 없음(이번 라운드 3건 전부 융자성 정책자금, 매칭 대상 아님). 대신 이전에 웹검색으로 찾아둔 범용 프로그램 중 가장 유력한 "초기창업패키지(일반형)"의 **실제 공고문 원문**(중소벤처기업부 공고 제2026-38호, `https://www.cku.ac.kr/bbs/startup/1136/149077/download.do`)을 Claude in Chrome으로 전문 확인 후 `scripts/real_announcements.json`에 **4번째 정본**으로 추가(자격요건/제외대상 12종/제출서류/예산기준/평가지표까지 원문 그대로 구조화).
- **드라이런 실행**: `test/my_business_profile_input.json`(mo,on 기존 프로필 초안) + 위 신규 정본을 `review_application(business_profile, announcement, ref_date=2026-02-01)`로 직접 실행(이번 사이클은 이미 마감이라 GOV_SKILL_TODAY 시뮬레이션 방식, T11 블라인드테스트와 동일 패턴). 결과: `test/moon_ilban_dryrun_output.json`.
- **결과 — 내용은 이미 탄탄함, 막힌 건 순수 행정서류뿐**:
  - PSST 4구간 중 3개 PASS(문제/해결/성과), Support(서류)만 FAIL — 필수서류 3건(사업계획서 정부지정양식/신분증/사업자등록증명) 전부 아직 없음(당연함, 미창업 상태).
  - **홍재우(9번째 심사위원) 판정: "잘 보완됨", 위반 0건.** 8인 심사위원 중 7명 5점/무경고, "자격·규정 심사위원"만 경고(기업형태·업력 미확정 — 역시 미창업 때문).
  - `overall_confidence=0.35`, `lock_state=DRAFT` — 낮은 건 콘텐츠 부실이 아니라 **"아직 사업자등록을 안 해서 자격 확정 필드 자체가 없다"**는 구조적 이유. 창업 후 이 필드들만 채우면 confidence가 크게 오를 가능성 높음(다른 두 실제 공고 사례에서 서류 확보만으로 0.35→0.85까지 오른 전례 있음).
- **실제 공고 핵심 조건 요약**:
  - 자격: 창업 후 3년 이내(개인/법인 무관), 지원제외 12종(체납·채무불이행·창업제외업종 등, 모온 해당 없음)
  - 지원금: 평균 5천만원(최대 1억원), 자기부담비율은 지역별 차등(창녕군·함안군=우대지원 20%로 명시되지만 **진주시는 목록에 없어 일반지역 25%로 추정, 확정 아님**)
  - 협약기간 10개월, 3단계 평가(서류→심층인터뷰30분→발표30분 대면)
  - 신청은 K-Startup, 본점 소재지 기준 권역별 주관기관 1곳 선택 필수 — 진주시는 동부권, **영산대학교(경남)가 지리적으로 가장 가까움**(2026년 설명회가 경상국립대 칠암캠퍼스에서 열림)
  - **이번 사이클은 마감(2026.01.23~02.13), 다음 사이클은 2027년 1~2월 예상** — 지금부터 준비하면 여유 있음
- **다음에 할 만한 작업**: ①실제 사업자등록 후 `test/my_business_profile_input.json`의 기업형태/업력/사업자번호 등 확정 필드 채우기 ②정부 지정 [별첨1] 사업계획서 양식에 맞춰 콘텐츠 옮기기(현재 콘텐츠는 스킬 내부 포맷) ③진주시 자기부담비율 25% 추정치 검증(주관기관 문의) ④영산대학교 초기창업패키지 담당자 연락처 확인.

## mo,on — 예비창업패키지 실제 공고 정본화 + 초창패 vs 예창패 비교문서 (2026-07-19 같은 세션 이어서, [hyemi])

- 혜미 지시("초창패 예창패 두 양식 다 돌려봐줘, 내가 좀 보게")로 "2026년도 예비창업패키지 예비창업자 모집공고(수정)"(중기부 공고 제2026-143호, bizinfo PBLN_000000000119019, 원문 `https://www.inu.ac.kr/bbs/inu/2611/379514/download.do`) 원문도 확인해 `scripts/real_announcements.json`에 5번째 정본으로 추가, `review_application(ref_date=2026-03-10)`로 드라이런(`test/moon_yechangpae_dryrun_output.json`).
- **핵심 발견 — 두 사업은 상호 배타**: 정부 공고 [붙임2] 제외사업 목록에 예비창업패키지·초기창업패키지가 서로 포함되어 있어, 하나에 선정·협약하면 다른 하나는 영구 재신청 불가. 예창패는 자기부담금 0원(정부지원 100%)이지만 커트라인 70점(초창패는 60점)으로 더 엄격, 협약 8개월(초창패 10개월), 지원액도 평균 4천만원(초창패 평균 5천만원)으로 약간 낮음. 예창패는 지금(미창업 상태) 바로 신청 가능하나, 초창패는 선등록 필요.
- 드라이런 결과는 초창패와 완전히 동일한 패턴(같은 business_profile 사용) — 홍재우 "잘 보완됨"·위반 0건, PSST 3/4 통과(서류만 미창업 사유로 fail).
- **산출물**: `mo,on_예비창업패키지/초창패_예창패_비교_2026-07-19.docx` — 비교표+두 드라이런 결과+신청서 초안 내용(6섹션)+참고용 판단 메모(어느 쪽이 유리한지는 확정 조언 없이 트레이드오프만 제시, 최종 선택은 혜미 몫). LibreOffice로 PDF 렌더링해 5페이지 전부 육안 확인 완료.
- **다음에 할 만한 작업**: 두 사업 중 실제로 어느 쪽으로 갈지 혜미가 결정하면(자금 여유·창업 시점에 달림), 그에 맞춰 `business_profiles.yaml`의 `excluded_types`/`transition_note`를 확정 반영 — 현재는 "예비창업 제외, 초기창업 목표"로 이미 기록돼 있으나 이번 비교 결과를 보고 재확인이 필요할 수 있음.

## mo,on — 새 아이디어 기반 예창패/초창패 완성본 초안 2건 신규 작성 (2026-07-19 같은 세션 이어서, [hyemi])

- **배경**: 혜미가 "이거 작성한거 내가 썻던거 옮긴거아냐?"라고 지적 — 직전 드라이런 초안이 `test/my_business_profile_input.json`(2026-07-06 구버전 프로필) 필드를 조립한 것일 뿐 새로 작성된 게 아니었음을 인정. 이에 혜미가 "기존 정보는 없고 아이디어만 있는 상태에서의 완성본"을 요구하며 MVP 4종 축소·확장기능 분리·"고객 응대 기준 확보"(책임공방 판별 표현 우회) 등 홍재우 코칭이 반영된 새 아이디어 전문을 채팅으로 직접 붙여넣음.
- **처리 순서**: ① 업로드된 파일(`신청서초안_2026-07-14.md`)이 아이디어가 아니라 과거 매칭 실패 로그였음을 확인하고 혜미에게 정직하게 플래그 ② `탈락분석_2026-07_예창패.md` 전문 재확인(실제 심사평 5건 + 홍재우 8건 교차분석 v3→v4 체크리스트) ③ 경쟁사 리서치(케어네이션/맘스매니저/째깍악어/닥터맘/마터케어/친정맘 — 전부 "매칭·예약" 단계 상품, mo,on의 "매칭 이후 운영기록" 영역은 미충족) ④ 시장규모는 추측 대신 웹서치로 확인한 통계청 2025 출생아수(25.4만명, 잠정)를 근거로 한 하향식 추정 방식 사용, 정부 등록 제공기관 수는 미확인이라고 명시 ⑤ `작성_포맷_규칙.md`의 "○소제목:내용" 불릿 포맷 그대로 적용, 표는 경쟁사 한계표·일반현황표 등 최소한만 사용.
- **탈락분석 5개 급소 전부 정면 대응**: 차별화 부족→에이전시(B2B) 재정의+"엑셀·카톡"을 진짜 경쟁자로 명시, 데이터기반 상징성→MVP 단계 정량목표(인수인계 15분→3분, 클레임 처리 50%단축) 삽입, 수요조사 부재→설문/인터뷰 목표치를 "계획 단계"로 정직하게 표기(완료로 과장하지 않음), 성장전략 구체성→항목별 금액의 자금소요·KPI표, 시장크기 미제시→통계 근거 추정치 삽입. 문서 내 "부록. 과거 탈락 사유 반영 현황" 섹션에 5개 대응을 명시적으로 정리.
- **산출물** (`mo,on_예비창업패키지/` 폴더):
  - `mo,on_예비창업패키지_사업계획서초안_2026-07-19.docx` (5p) — 회사명 "예비 mo,on(모온)", 여성특화분야, 자기부담 없음, 1단계 2천만원 예산 배분.
  - `mo,on_초기창업패키지_사업계획서초안_2026-07-19.docx` (5p) — 회사명 "mo,on(모온)", 창업 완료 가정, 자기부담 추정 25%, 정부지원금 신청액 4,500만원 예산 배분.
  - 두 문서 모두 최상단에 예창패/초창패 상호배타 경고 박스 + "이 초안은 기존 자료 재사용 없이 새로 작성했으며 정량지표 중 상당수는 계획단계"라는 출처 투명성 고지 박스 포함(혜미의 지적을 반영한 조치).
  - LibreOffice→PDF→JPEG 변환 후 전체 페이지 육안 확인 완료(표·불릿·색상 정상 렌더링).
- **알려진 한계**: 두 초안 모두 정부 지정 [별첨1] 양식이 아닌 PSST 4항목 자유 서술 구조 — 실제 제출 전 지정 양식으로 옮겨 담아야 함(문서 내에도 명시). 시장규모·페인포인트 수치 상당수는 "실측/실증 예정"이며 제출 전 실제 설문·인터뷰로 검증 필요.
- **다음에 할 만한 작업**: 혜미가 실제 설문 30~50건·업체 인터뷰 5곳을 진행하면 그 결과로 "예정" 표기 수치를 실측치로 교체, 업종신고(피부미용업 등) 세무사·행정사 확인 완료되면 문서의 [확인 필요] 문구 제거, 최종 결정된 프로그램 하나만 골라 정부 지정 [별첨1] 양식으로 이관.

## mo,on 초안 v2 — 외부감사 대조 반영 + 예산 재설계 (2026-07-20, [hyemi])

- **배경**: 혜미가 초안을 외부 AI 감사로 돌려 `mo,on_예비창업패키지/초창패_예창패_초안 평가_2026-07-19.md`로 결과를 저장, "이런 지적이 강의에도 있었는데 기록이 빠진 거 아니냐"는 질문과 함께 예산을 "신청 최대금액 + 자부담은 현금 대신 현물(인건비)로" 재설계해 달라고 요청.
- **원문 재대조로 팩트체크**: 초창패(cku.ac.kr)·예창패(inu.ac.kr) 공고 PDF를 다시 원문으로 fetch해 외부감사 주장을 하나씩 대조.
  - **외부감사가 맞았던 것**: ① 시장규모 계산에 10배 오류 있었음(300~500개소×5만원×12개월=1.8억~3억원이 맞음, 이전 초안의 18억~30억원은 계산 실수) — 수정 반영. ② "영구 상호배타·둘 중 하나만" 서술은 부정확 — 원문 재확인 결과 초창패→예창패 방향만 배타적이고(예창패 공고 붙임2에 초창패가 제외사유로 있음), 예창패→초창패는 오히려 서류평가 면제가 붙는 공식 연계 트랙(초창패 공고 붙임4-2에는 예창패가 제외사유로 없음) — 경고 박스를 비대칭 관계로 재작성.
  - **외부감사가 틀렸던 것**: 초창패 자기부담금 25%를 "근거 없는 추정이니 삭제하라"고 했으나, 공고 [붙임6] 지방 우대 시범사업 지역 분류표를 직접 재확인한 결과 진주시는 특별·우대지원 목록에 없어 "일반지역 25%(정부지원 75%)"로 확정되는 게 맞음(원래 수치가 옳았음) — 반영 안 함.
  - **판단 보류**: 예창패 총 지원금 "최대 8천만원" 주장은 이번 재확인에서도 공고 원문에 숫자로 확인 안 됨(원문은 평균 0.4억원+1단계 2천만원 고정만 명시). 외부감사가 인용한 출처명("한국정보사회진흥원")도 이 사업의 실제 주관기관(창업진흥원)과 다른 이름이라 신뢰도 낮다고 판단 — 양쪽 다 확정 안 하고 [확인 필요]로 유지.
- **예산 재설계(혜미 지시 반영)**: 초창패는 정부지원금 신청액을 최대치인 1억원으로(평균 지급액 0.5억원보다 높게 신청 — "어차피 심사 후 차등지급되니 최대로 신청" 전략), 자기부담사업비는 공고 붙임6의 공식 비율표(일반지역: 정부지원75%+현금10%이상+현물15%이하)로 재계산해 현금 최소선(1,334만원)만 남기고 나머지(현물 2,000만원)는 전액 대표자 본인 인건비로 계상 — 100% 현물 대체는 공고상 불가능(현금 10%는 의무)하다는 점도 문서에 명시. 예창패는 1단계가 2천만원 고정이라 조정 불가, 2단계는 "신청 가능한 최대치로 신청" 전략만 문구로 반영(정확한 상한 숫자는 [확인 필요]).
- **홍재우 방법론 정합성 확인(혜미 질문 대응)**: "자부담 현금 최소화·현물(인건비) 최대화" 전략은 강의녹취 4강(01:16~01:22)·6월세미나(00:25·01:21~01:24)에 실제로 나온 내용이나, `종합본.md`에는 한 줄 요약("현금자부담 약10%·현물자부담 약20% 역산")만 있었고 `홍재우_페르소나카드.md`의 24개 판단기준에는 별도 항목으로 없었음(누락 확인) — 25번 기준 "[자부담 현금최소화]"로 신규 추가, 이번에 재확인한 초창패 실제 수치(일반지역 정부지원75%·현금10%·현물15%)로 각주 보강.
- **산출물**: `mo,on_예비창업패키지_사업계획서초안_2026-07-20.docx`, `mo,on_초기창업패키지_사업계획서초안_2026-07-20.docx`(둘 다 6p, 이전 07-19판을 대체, 07-19판은 이력 보존 목적으로 폴더에 남겨둠) — 문서 최상단 경고박스·안내박스, 본문 시장규모·예산 항목 수정, 문서 끝에 "외부감사 반영 메모" 섹션 신설(반영함/반영 안 함/판단보류/미반영 4갈래로 투명하게 정리). LibreOffice PDF 렌더링으로 전체 페이지 육안 확인 완료.
- **다음에 할 만한 작업**: 외부감사가 지적한 콘텐츠 품질 이슈(MVP 4개→2개로 축소, 고객군을 "관리사 3~20명 업체"로 좁히기, 구간제 가격 설계, 설문·인터뷰 실측 전환)는 타당하나 혜미의 전략적 결정이 필요해 이번엔 반영 보류 — 진행 여부 확인 필요. 예창패 2단계·초창패 자기부담 관련 [확인 필요] 항목은 실제 접수 시스템(K-Startup)에서 재확인 권장.

## 공장 수리 — "부실 초안" 구조적 원인 제거: 내용 게이트·병렬 작성 구간 신설 (2026-07-20, [gombeck1])

- **배경**: 혜미가 외부감사 전문을 첨부하며 "문서를 다시 만들지 말고, 부실 초안이 나오는 버그 자체를 잡아라. 하위모델이 병렬로 작성해야 한다"고 지시. 외부감사 결론(부실의 60%는 자동화 설계 문제)을 그대로 이행.
- **원인 진단**: 기존 공장은 검수기(자격판정·PSST·9인 심사)일 뿐 작성기가 아니었음 — ①사실/가정/목표 구분 없음 ②예창패·초창패 단계 분리 로직 없음 ③산술 검증 없음(10배 오류 통과) ④심사 후 수정본을 만드는 단계 자체가 없음 ⑤내부 메모가 제출본에 섞임.
- **수리 내역**:
  - `scripts/content_gate.py` 신설(결정론적, LLM 호출 없음) — 입력충분성 진단(14필드)/산술 역산(실제 10배 오류 재현 테스트 통과)/예산 합계/초창패 시나리오 필수 7필드/예창패·초창패 유사도 80% 복사본 차단/증빙원장 7종 상태값/출처 없는 수치 사실형 차단/고객군 혼합·피부미용업 탐지/제출본·내부본 분리. self-test 9종 전부 PASS.
  - `정부지원_manifest_v2.yaml` v0.7.0 append — 트리거 draft_build_request + shared_context 15필드 + 12 stage(입력충분성진단→시나리오확정(human)→잠금값추출→작성 4섹션 병렬(sonnet, async)→초안통합→내용검증게이트(local)→수정본생성→재검증→출력분리). validate_manifest.py PASS(오류 0·경고 0). 기존 stage는 append-only 원칙대로 무수정(open_issues에 judge reads 문제 기록).
  - `작성단계_업무지시서_2026-07-20.md` — 하위모델(Sonnet) 세션 4개에 병렬 배분하는 TASK-PACKET 6종 + 공통 규칙(상태값·잠금값·금지표현) + 잠금값 카드 + 예창패/초창패 시나리오 카드(초창패 가상 현재실적 포함).
  - `입력표_템플릿.yaml` — 감사 "최소 입력 정보" 표를 상태값 스키마로. 대표자 100만개 판매 경력 복원(증빙 확보 필요 표시).
  - `자동화_개선지시_외부감사_2026-07-20.md` — 감사 지시 15개 이행 상태표(완료 9/부분 4/규칙화 2) + 남은 일 4건. 감사 원문은 `외부감사원문_초창패예창패_2026-07-19.md`로 볼트에 보존.
- **팩트체크 유지**: 감사 vs 공고 원문 대조 결과(자기부담 25%는 감사가 틀림 / 예창패 8천만원은 보류 / MVP 4종 잠금)는 이전 세션 판단 그대로 잠금값에 반영.
- **다음에 할 일**: ① 혜미가 `입력표_템플릿.yaml` 빈칸 채우기(특히 대표자 경력 증빙) ② 업무지시서 3단계 사용법대로 Sonnet 4세션 병렬 작성 실행 ③ content_gate 신규 테스트를 기존 회귀테스트에 편입(Sonnet ~30분). 07-20판 docx 2건은 새 파이프라인 결과물이 나오면 대체 예정.

## jbjw 공개앱 + HEM 비공개 운영 통합 (2026-07-21, [eunoia9496] GPT/Codex)

- **목적**: GitHub `2yeonai/jbjw`를 공개 앱 코드의 정본으로 유지하고, 사업자 프로필·실공고·API 키·신청서·승인기록은 HEM에만 보관하는 로컬 운영 시스템으로 통합.
- **공개 앱 구현**: `/operations` 한 화면에 `수집 → 사람 검수 → 사업체 매칭 → jbjw+HEM 엄격 통합 판정 → 신청서 사람 승인 → 실제 제출·선정 확인 → PPT·대본·Q&A 생성·반려·버전별 승인` 흐름을 연결. 기본 접속은 `127.0.0.1`, 휴대폰 접속은 별도 LAN 실행파일에서만 허용.
- **판정·안전장치**: 마감일 `YYYYMMDD`·점·슬래시·하이픈 형식 해석, 미확정 마감일과 `reviewed:false` 후보 차단, 정확한 개업일·지역·매출·직원수·대표자 생년월일·제출서류 상태·예산 출처 우선 매핑, 자격정보 누락 시 낙관 승인 금지. 자동 상태는 `DRAFT → READY_FOR_APPROVAL`까지만, `LOCKED → SUBMITTED → SELECTED`는 사람 기록만 허용. 실제 접수·발송·게시 자동화 없음.
- **발표 공정**: HEM의 기존 PPT·대본·Q&A 생성 stage만 재사용하고 테스트용 자동승인 함수는 호출하지 않음. 문서별 `승인대기/승인완료/반려`와 버전 이력을 비공개 실행 폴더에 저장하며, 반려 후 v2가 생성돼도 자동 재승인되지 않음. 세 문서가 모두 승인되지 않으면 최종 패키지 저장 차단.
- **로컬 실행**: 프로젝트 루트에 `정부지원AI_설치.bat/.ps1`, `정부지원AI_실행.bat`, `정부지원AI_휴대폰실행.bat` 추가. 앱 코드와 가상환경·산출물은 Git 제외 `.runtime/`에 분리. 실행파일의 LF 줄바꿈 때문에 `YEMI_GOV_ROOT`·`A_ROOT`·시간 입력 오류가 발생한 뒤 Windows CRLF로 교정하고 `.gitattributes`로 재발 방지, 실제 배치 실행 후 `/operations` HTTP 200 확인.
- **검증**: 기존 jbjw 검사 77/77, 통합 회귀검사 18/18, Python 문법검사, HEM manifest FAIL 0/WARN 0, Markdown 센티널·vault 검사 통과. 합성 공고로 `READY_FOR_APPROVAL → SELECTED → PPT v1 반려 → v2 재생성·사람 승인 → 대본/Q&A 승인 → PACKAGE_SAVED` 완주했고 PPTX·DOCX·JSON 무결성 확인. 기존 실데이터 후보 156/142/3건과 검수 8건 보존.
- **민감정보·정리**: jbjw 공개 diff에서 실사업자 정보·실후보 데이터·API 키·신청서·로컬 절대경로 0건 확인. PR 생성과 새 로컬 경로 검증 후 HEM의 옛 추적 사본 `jbjw-main` 143개 제거(HEM Git 이력과 GitHub에서 복구 가능).
- **Git 전달**: jbjw `codex/gov-ai-integration` 커밋 `6db3eb7`, GitHub 초안 PR `2yeonai/jbjw#2`. HEM `codex/gov-ai-integration` 커밋 `1b3923c`, Windows 실행 수정 `3f8b90a`, 원격 브랜치 푸시 완료. `main` 직접 수정·서버 배포·PR 병합은 하지 않음.
- **다음 한 단계**: 혜미가 `정부지원AI_실행.bat`으로 로컬 화면을 실사용해 후보공고를 승인하고, 이상 없으면 jbjw PR #2를 최종 확인·병합. 이후 서버 로그인·DB·백업·HTTPS는 별도 후속 작업으로 설계.

## 통합 운영앱 모바일 우선 UI 개편 (2026-07-21, [eunoia9496] GPT/Codex)

- **변경 전**: `/operations`에서 시스템 경로·수집·검색과 공고별 전체 검수 양식이 한 화면에 이어져, 390px 휴대폰에서 급한 공고보다 긴 입력칸이 먼저 보였음.
- **변경 후**: 첫 화면을 `검수 필요 / 14일 안 마감 / 수집 연결 → 검색·상태 필터 → 짧은 공고 목록 → 접힌 시스템 상세` 순서로 재구성. 공고 행을 누르면 새 GET 화면 `/candidate/<index>`에서 기존 네 가지 검수값을 편집함.
- **보존 범위**: 수집·검수·프로젝트 생성 POST API, 후보 JSON 구조, HEM 연결, 승인·제출 규칙, 기존 심사 엔진은 변경하지 않음. 작업 화면에서 둥근 카드 사용 0개, 그라데이션·키프레임 0개, 버튼 최소 44px와 120ms 누름 반응만 적용.
- **검증**: 공개 커밋 `69bbe7c`를 기존 PR #2 브랜치에 푸시. Ruff lint, mypy typecheck, compileall build, 기존 77/77, 통합 18/18 통과. 실제 `/operations`와 후보 상세 HTTP 200, 한글 대체문자 0, 민감정보·절대 로컬 경로 공개 diff 0건.
- **미완료 확인 1건**: 앱 내 브라우저 연결 자체가 내부 오류로 열리지 않아 390×844·430×932·1440×900 스크린샷 육안 검증은 못 함. 세 크기의 반응형 분기, 44px 버튼, 긴 경로 접기, 가로 넘침을 숨기는 CSS 미사용은 실제 HTML·CSS로 확인했으며 혜미의 최종 육안 확인이 남음.

<!-- ok -->
