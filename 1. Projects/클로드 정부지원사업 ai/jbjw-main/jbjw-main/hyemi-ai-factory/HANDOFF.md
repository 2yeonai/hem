# HANDOFF.md — 세션 인계문 (최신: 2026-07-08, gov-support-skill 연동 어댑터 추가)

새 세션은 CLAUDE.md → 이 파일 → 06_locks/LOCK_STATUS.md 순으로 읽는다.

## gov-support-skill 연동: govskill_adapter.py (2026-07-08 세션)

목적: 이 앱(jbjw/hyemi-ai-factory)의 데이터를 gov-support-matching-skill의
`review_application(business_profile, announcement, ref_date)` 판정 로직
(위험표현사전/PSST/8인 가상 심사위원/감점 전파 모델)에 통과시켜, 이 앱 자체의
규칙 기반 판정 위에 그 4개 서브시스템 결과를 추가로 얻을 수 있게 함.

**원칙**: `engines.py`/`draft_engine.py`/`present_engine.py`/`app.py`/`run_factory.py`
등 기존 판정 로직·화면·파이프라인은 전혀 건드리지 않았다. 새 파일 1개
(`08_factory_tools/govskill_adapter.py`)만 추가 — 데이터 형태 변환(번역)만
한다. gov-support-skill 쪽 로직도 재작성하지 않고 그대로 재사용한다.

### 1. 확정 아이디어 판정 기준

`data["selected_idea_id"]`(문자열, ideas[] 중 하나의 id) + `data["approvals"]["idea_selected"]`
(boolean)가 둘 다 있어야 확정으로 인정 — `input_schema.json`에 이미 공식
문서화된 필드이며, `engines.lock_engine()`/`draft_engine.pick_idea()`가
이미 쓰는 것과 동일 기준(새로 지어낸 규칙 아님). 확정 안 됐으면 어댑터는
아무것도 호출하지 않고 `PENDING_APPROVAL`로 멈춘다.

### 2. eligibility_keyword_safety_check() — 이번 세션 추가

문제: notice의 자격/제외조건이 자유서술이라 gov-support-skill의 구조화된
eligibility 필드로 옮길 수 없어 빈 채로 전달했었다. 그 결과 gov-support-skill
쪽에서 정량 자격기준 체크(criteria)가 통째로 비어(`[]`) `_score_criteria([])`가
기계적으로 1.0(만점)을 반환 — "확인해서 통과"가 아니라 "검사 자체가 없어서
만점"인데 겉보기엔 구분이 안 되는 문제가 있었다.

해결(완벽한 파싱이 아니라 안전장치): notice.eligibility + notice.exclusions +
notice.raw_text를 합친 텍스트에서 핵심 키워드 4종("업력","매출","지역","체납")이
최소 한 번이라도 언급됐는지만 확인(단순 부분 문자열 포함 여부, 자연어 이해 아님).
하나라도 없으면 "확인 필요"로 명시 경고. **gov-support-skill의 base confidence
계산 로직 자체는 전혀 바꾸지 않았다** — 경고는 어댑터 쪽 `translation_notes`와
새 반환 필드 `eligibility_safety_check`에만 기록됨.

검증: sample-demo 데이터로 실행 시 실제로 "매출","지역" 키워드가 원문에 없어
`all_found: false`, "확인 필요" 경고가 정상적으로 뜨는 것을 확인함(base
confidence는 여전히 1.0으로 계산되지만 경고가 붙어 있음).

### 3. required_documents 매핑 안 하기로 한 결정 (이유 포함)

`input_schema.json` 전체를 다시 훑었지만 "서류 준비 상태"를 나타내는 필드는
uploads/attachments/documents_status 등 어떤 이름으로도 존재하지 않는다.
가장 가까운 것은 `evidence.owned`/`evidence.planned`인데, 이는 "증빙 자료가
실물로 있는지"의 범용 리스트이지 공고별 `required_documents` 항목 이름과
1:1 대응하는 체크리스트가 아니다(예: "사업자등록증"은 있어도 "국세 납세증명서"
같은 공고 고유 서류명과 이름이 맞는다는 보장이 없음 — 억지로 매칭하면 이름
유사도 추측이 되어 새로운 판정 로직을 만드는 셈이 됨, 스코프 밖).

**결정**: 매핑하지 않는다. `required_documents`는 빈 리스트로 두고, 그 결과
gov-support-skill의 PSST-Support 판정과 서류 체크리스트가 항상 "0건 준비"로
나온다는 사실을 `translation_notes`에 명확히 남긴다 — 이건 실제 미준비를
뜻하는 게 아니라 "이 데이터가 아예 없다"는 뜻이며, 사람이 직접 서류 준비
상태를 확인해야 한다.

### 4. 보류 결정 (심각도 낮음, 손대지 않음)

- **founded_date 근사**: applicant에 `biz_years`(연차 숫자)만 있고 개업일이
  없어 오늘 날짜에서 biz_years년을 빼 근사 계산한다 — 일/월 단위 오차 가능.
- **budget_detail.category 없음**: `budget_plan` 항목에 category 필드가
  없어(item/purpose 텍스트만 있음) gov-support-skill의
  `excluded_categories`(집행 불가 항목) 매칭이 항상 통과로 나온다. 단,
  이 위험 자체는 이 앱의 `engines.budget_risk_checker`가 이미 별도
  키워드 매칭(인건비/임차 등)으로 잡고 있어 완전히 놓치는 건 아니다.

### 5. 테스트 결과 (전부 기존과 동일 — 회귀 없음)

- 이 앱(jbjw) `08_factory_tools/test_engines.py`: **77/77 통과**
  (참고: 사용자가 이전에 "57개"로 알고 있었으나 실제 파일 기준 77개가 맞음)
- gov-support-matching-skill 회귀 5개 커맨드 전부 기존 기록값과 동일하게 통과:
  `sample_input_ideal.json`→READY_FOR_APPROVAL/1.0,
  `sample_input.json`→DRAFT/0.85, `sample_input_edge.json`→DRAFT/0.68,
  `real_program_input.json`→DRAFT/0.0(매칭 0건),
  `real_program_input_simulated.json`(2026-03-15 시뮬레이션)→DRAFT/0.35
- 둘 다 기존 코드를 전혀 안 건드렸으니 당연한 결과지만, 매번 실제로 재실행해서
  확인했음(추측으로 "통과"라고 보고하지 않음).

### 6. git 백업 상태 (중요 — 다음 세션 필독)

이 작업은 GitHub `2yeonai/jbjw` 저장소의 zip을 압축 해제한 폴더
(`1. Projects/클로드 정부지원사업 ai/jbjw-main/jbjw-main/`, `.git` 없음)에서 진행됐다.
이 세션 후반에 아래 방식으로 git 이력을 만들어 백업했다:

1. 이 샌드박스에서 `git clone`/`curl`/codeload.github.com zip 다운로드가
   전부 프록시 403으로 막혀 있어(네트워크 인프라 제약, 우회 시도 안 함),
   GitHub의 `git/trees` API로 `main` 브랜치의 파일 트리(blob SHA 140개)만
   가져왔다.
2. 로컬 zip 압축해제 폴더의 모든 파일에 대해 `git hash-object`로 blob 해시를
   계산해서 GitHub 트리의 SHA와 전부 대조 — **140/140 파일이 정확히 일치**,
   불일치 0건, 누락 0건. 유일한 차이는 `govskill_adapter.py` 1개 파일 추가뿐
   (이번 세션에 만든 파일이라 GitHub엔 당연히 없음). 압축 해제 과정에서 생긴
   인코딩 깨짐이나 의도치 않은 변경은 없었다는 뜻.
3. 이 검증을 바탕으로 로컬에 새 git 저장소를 만들어 baseline 커밋(GitHub main과
   동일 내용, 단 실제 커밋 이력은 없음 — 트리 내용만 검증된 스냅샷) 후,
   `govskill_adapter.py`를 추가하는 두 번째 커밋을 만들었다.

**주의**: 이건 진짜 `git clone`이 아니다 — 실제 GitHub 커밋 히스토리(17개
커밋)는 가져오지 못했고, "현재 main 브랜치 내용과 트리가 일치함"만 암호학적으로
검증했다.

**백업 파일**: 이 폴더(`jbjw-main/jbjw-main/`, 즉 이 저장소의 실제 루트) 바로
아래에 `jbjw_backup.bundle`을 만들어뒀다 — 3개 커밋(baseline 스냅샷 →
govskill_adapter.py 추가 → 이 HANDOFF.md 갱신) 전체가 들어있는 git bundle
파일이며 임시 샌드박스가 아니라 사용자 로컬 폴더에 저장돼 세션이 끝나도
남는다. 복원 방법(gov-support-matching-skill.bundle과 동일한 패턴):
```bash
git clone jbjw_backup.bundle my-jbjw-restore   # 새로 복원
# 또는 기존 클론이 있으면: git pull jbjw_backup.bundle master
```
실제 GitHub(`2yeonai/jbjw`)에 반영하려면, 프록시 제약이 없는 환경(사용자의
실제 PC 등)에서 `git clone https://github.com/2yeonai/jbjw`로 진짜 클론을
받은 뒤, 그 클론 안에서 `git pull jbjw_backup.bundle master` (또는 그냥
`govskill_adapter.py` 파일과 이 HANDOFF.md 갱신분만 복사)해서 반영하고
`git push`하면 된다.


## 현재 상태 한 줄 요약

앱 v0.2가 혜미 방식 **17단계 전체(0~16)를 자동화**한다: 공고 분석 → 자격 판정 → 아이디어 평가 → **서류 초안 → 연결형 예산표 → 발표자료(PPTX 생성) → 대본 → Q&A 방어 → 발표연습기**. 테스트 57/57 통과.
실전 프로젝트 **2026_ai_support**는 0단계(신청자 입력 대기) — 신청자·아이디어를 입력하면 서류·발표 라인이 자동으로 풀린다. 실행: `python3 08_factory_tools/app.py`

## 앱 v0.2 확장 (2026-07-04 세션)

- **서류 라인** `draft_engine.py` (7~13단계): 작성전략표(배점=분량), 본문 6절 초안(문제→대안한계→해결→실행→성장→역량), 증빙 연결표, 연결형 예산표(항목→목적→산출물→근거→평가항목→성과), 분량 점검, 위험 표현 자동 치환+기록, 최종 점검 9종
- **발표 라인** `present_engine.py` (14~16단계): 슬라이드 11장(배점 기준 재구성·시간 배분), 대본 3종(풀·압축·쉬운말), WHY 3종·예산 방어 답변, 슬라이드별 예상 질문
- **PPTX 생성** `pptx_writer.py`: 표준 라이브러리 zip만으로 PowerPoint에서 열리는 slides.pptx 생성 (16:9, XML 유효성 검증)
- **앱 UI**: 공정 0~16 진행바(모든 탭 상단), ⑧ 서류 초안 / ⑨ 발표자료(PPTX 다운로드) / ⑩ 발표연습기(JS 타이머·공격질문·위험표현 실시간 감지) 탭 추가 — 총 11탭, 산출물 24종/프로젝트
- **안전 설계 유지**: 아이디어 미선정(0단계)이면 서류·발표 라인 잠김(섞임 방지). 초안 문장은 위험 표현 치환기 자동 통과. LOCKED는 여전히 사람만 기재

## 🚨 즉시 확인 (사람)

1. **신청 마감 = 2026-07-03(금) 16:00 = 오늘.** 소상공인24 접수 여부/가능 여부부터 확인. 마감을 넘겼다면 이 프로젝트는 차기 공고 대비용으로 전환 (폼의 0번 섹션에 기록).
2. notice.md는 원문 HWP의 **정리본** — 지원제외 업종표·가점 항목·사업계획서 서식은 원본 확인 필요.

## 실전 프로젝트 2026_ai_support 상태

| 단계 | 상태 | 산출물 |
|---|---|---|
| 0. 기준자료 확인·1차 분석 | **완료 (DRAFT)** | 01_inputs/2026_ai_support_notice/ — notice.md, notice_summary.md, scoring_strategy.md, applicant_input_form.md |
| 0-b. **앱 등록 완료** | 완료 | 앱 프로젝트 `2026_ai_support` (0단계 모드) — `python3 08_factory_tools/app.py` → 대시보드에서 열기. 분석 16종 생성됨 (04_outputs/2026_ai_support/) |
| 1~2. 신청자 정보·자격 판정 | **대기 — 입력 필요** | 앱의 "신청자·아이디어 입력" 화면 또는 applicant_input_form.md |
| 3~. 아이디어 평가·LOCK | 금지 상태 | 신청자 정보·후보 없음 — **LOCK·제출 판정 금지 유지** (앱이 구조적으로 차단 중) |

### 앱 확장 (이번 세션)

- 0단계 모드 추가: 아이디어 없이 공고만으로 프로젝트 생성 가능 → 배점 전략(배점군 자동 묶기: 성장가능성 40 확인)·신청자 질문지 자동 생성, 판정 "판정 불가" 고정
- 신청자·아이디어 입력/수정 화면(/edit) 추가 — 폼 저장 시 자동 재분석
- 테스트 35/35 통과. 실전 프로젝트 input.json은 0단계 상태(전부 미확보)로 유지 — 실제 정보 입력은 사람 몫

### 공고 핵심 (분석 요약)

- 2단계: STEP1 서류(1,000개사) → STEP2 발표(680개사, 최대 4,000만원, 자부담 20% 현금 계획 필요)
- 배점: **성장가능성 40** > AI활용 적합성 30 = 참여역량 30 → "시간 절감"이 아니라 **"AI로 사업모델이 어떻게 커지는가"**가 승부처 (scoring_strategy.md 전략 5개)
- 감점 지뢰(공고 명시): 단순 ChatGPT 구독, 단순 외주 앱 개발, 완전 자동화 주장, 실측 없는 수치, 기성품 구매, AI 적용 지점 불명확, 예산-산출물 미연결
- 집행 금지: 부가세 10%, 친족 거래, 현·전 재직 기업 외주
- 발표(9월) 주대표 참석 필수 + 보안성·운영안정성 우대 → 서류부터 선반영

## 유지해야 할 LOCK / 변경 금지

- DECISIONS.md D-001~D-011, 06_locks/LOCK_STATUS.md
- **이 프로젝트에서 아이디어 LOCK·제출 가능 판정은 applicant_input_form.md 완성 + 자격 확인 전까지 금지**
- sample-demo·mvp_test_01은 샘플 — 실전 재사용 금지 (D-006)

## 다음에 이어서 할 일

1. (사람) 접수 상태 확인 + applicant_input_form.md 작성 — 특히 결격 체크(2번)와 동시수행 사업 목록(2-9)
2. (다음 세션) 폼 기반 자격 판정 → 아이디어 후보 평가 → 필요 시 앱(input.json 변환) 실행
3. (병행 가능) 원본 HWP에서 지원제외 업종표·가점·서식 확보

## 다음 실행 프롬프트

```text
hyemi-ai-factory의 CLAUDE.md, HANDOFF.md, 01_inputs/2026_ai_support_notice/ 전체를 읽어라.

applicant_input_form.md 작성을 완료했다. 실전 프로젝트 2026_ai_support를 이어서 진행해라.
1. 폼 내용으로 자격·지원제외·동시수행 위험을 판정해라 (결격 '있음' 발견 시 즉시 STOP 보고).
2. 아이디어 후보를 scoring_strategy.md의 배점 구조(성장가능성 40점 중심)와
   감점 지뢰 7개 기준으로 평가하고 추천을 제시해라.
3. 폼 내용을 08_factory_tools/input_schema.json 형식의 input.json으로 변환해
   앱 분석 15종도 생성해라.
4. LOCK은 조건 충족 + 내 확정 전까지 DRAFT 유지. 완료 후 HANDOFF 갱신, 커밋·푸시.
```

## 주의해야 할 위험

1. 마감 시각 (오늘 16:00) — 모든 것에 우선
2. 폼 없이 아이디어 논의로 건너뛰기 — 자격 미확인 상태의 LOCK은 금지
3. 정리본을 원문으로 착각 — 지원제외 업종·가점은 원본 대조 전 확정 금지
4. 규칙 점수·기계 추천을 확정으로 오신 (KNOWN_LIMITATIONS.md)

<!-- ok -->
