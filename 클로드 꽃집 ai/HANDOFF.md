# HANDOFF — gov-support-matching-skill

다음에 이 프로젝트를 이어받는 사람(사람 또는 다른 세션의 나 자신)을 위한 인수인계 문서.

## 개요
정부지원사업 매칭 스킬. business_profile(사업자 정보) + target_period(조회기간)를 입력받아
공고 매칭, 신청서 초안 작성, 심사위원 모드 자기검수까지 수행한다. 스펙은 `manifest.yaml`,
동작 설명은 `SKILL.md`, 실제 구현은 `scripts/run.py`.

## 현재 상태 (v0.4.0 기준)
- **버전**: manifest.yaml `version: 0.4.0`
- **이번 버전(v0.4.0)에서 한 일**: 실제 PDF 공고문("2026년 경력단절여성 창업케어 프로그램 공고문") + 실제 사업자 데이터(mo,on/모온)로 테스트해서 발견한 문제 5개 중 사용자가 선택한 3개를 수정함.
  1. **예산 정합성 체크 추가** — `check_budget_compatibility()`. 사업자의 `budget_detail`(flat list 또는 phase 구조 dict) 총액을 공고의 `budget_criteria.max_grant_krw`와 비교해 초과 여부 확인, `budget_criteria.excluded_categories`에 해당하는 예산 항목이 있으면 별도 경고. `judge_mode_self_review()`의 `rejection_risks`에 반영됨.
  2. **심사배점(rubric) 매칭 로직 개선** — 기존엔 rubric item의 "첫 단어만" 문자열 포함 검사라 실제 공고 5개 항목이 전부 오탐(false negative)했음. 동의어 테이블(`RUBRIC_SYNONYMS`: 창업/사업, 아이템/아이디어/서비스/제품/솔루션, 사업화/사업) + 불용어 제거 + "가점" 항목은 매칭 대상에서 제외(`None` 처리)하는 방식으로 교체. **주의**: 중간 구현에서 "토큰 앞 2글자만 맞아도 매칭"이라는 fallback을 넣었다가 전 항목이 오탐(over-match)하는 걸 회귀 테스트로 발견 → 제거함. 현재는 동의어 테이블에 등록된 어근을 포함하는 토큰만 부분매칭 허용, 나머지는 전체 문자열 정확 일치 요구. 그래도 여전히 키워드 휴리스틱이지 의미 기반(NLP) 매칭은 아님 — 알려진 한계로 명시.
  3. **eligibility 스키마에 성별/경력단절 필드 추가** — business_profile에 `gender`, `career_interruption_status`, `career_interruption_reason` 추가. 공고(announcement) 쪽엔 `eligibility.required_gender`, `eligibility.requires_career_interruption` 추가. 값이 없으면 기존 다른 자격요건과 동일하게 "확인 필요"(unresolved, None)로 처리 — 조용히 무시되지 않음.
- **선택되지 않아 미수정으로 남은 문제 (사용자가 명시적으로 보류)**:
  1. PDF/HWP 공고문 자동 파싱 — 여전히 100% 수동 파싱(`scripts/real_announcements.json`은 사람이 손으로 옮겨 적은 것).
  3. 사업자 보유 문서명과 공고 required_documents 문자열의 fuzzy 매칭 — 여전히 정확히 일치해야 매칭됨.
- **회귀 테스트 결과 (6개 케이스, 전부 통과)**:
  - `sample_input.json` → DRAFT, confidence 0.85 (기존과 동일)
  - `sample_input_edge.json` → DRAFT, confidence 0.68 (기존과 동일)
  - `sample_input_ideal.json` → READY_FOR_APPROVAL, confidence 1.0 (기존과 동일)
  - `test/my_business_profile_input.json` (mo,on 실제 데이터 + 목업 공고) → DRAFT, confidence 0.35 (기존과 동일 — 이 케이스엔 budget_criteria/gender 요건이 있는 공고가 없어서 영향 없음)
  - `test/real_program_input.json` (실제 PDF 공고 + 실제 today 기준) → 마감일(2026-04-02)이 실제 오늘(2026-07-06)보다 과거라 매칭 0건으로 제외됨 — 정상 동작(공고가 이미 마감된 것이 맞음)
  - `test/real_program_input_simulated.json` (`GOV_SKILL_TODAY=2026-03-15`로 시뮬레이션) → DRAFT, confidence 0.35. **새로 발견된 리스크**: (a) 예산 총액 4,000만원이 공고 한도 1,000만원 초과, (b) 예산계획에 공고가 제외한 "인건비"/"기계장치" 카테고리 항목 포함, (c) 성별/경력단절 요건이 profile에 없어 "확인 필요"로 정확히 표시됨 (v0.3.0까지는 이 두 조건이 아예 체크되지 않고 조용히 넘어갔음). rubric 커버리지 오탐은 0건(수정 전엔 5/5 전부 오탐).
- **lock_state 판정 규칙**: `quality_gate_result.confidence_passed` AND `judge_pass_recommendation`이 둘 다 true일 때만 `READY_FOR_APPROVAL`. 하나라도 false면 `DRAFT` + `routed_to=human_review`, reasons에 구체적 사유 기록. (v0.4.0에서도 이 게이트 자체는 안 바뀜 — budget/rubric 리스크는 confidence 점수 감점에는 반영되지만 judge_pass_recommendation 이진 판정 자체엔 아직 안 들어감, 알려진 한계.)
- **입력 스키마**: business_description/team_experience/budget_detail/expected_outcomes는 string(v0.2.0) 또는 중첩 object(v0.3.0) 둘 다 지원. documents_status도 flat map 또는 prepared/not_prepared 배열 구조 둘 다 지원. v0.4.0에서 business_profile에 gender/career_interruption_status/career_interruption_reason 추가.
- **공고 데이터**: `scripts/sample_announcements.json`(목업 3건, 회귀테스트용)과 `scripts/real_announcements.json`(실제 PDF 1건, 손수 파싱) 두 파일을 병행 사용 중. `run.py [input.json] [announcements.json]` 형태로 두 번째 인자에 공고 파일 경로 지정 가능(기본값은 sample_announcements.json).
- **Git 이력**: `.git`을 프로젝트 폴더 안에 직접 두지 않고 `gov-support-matching-skill.bundle` 파일로 관리 중. 커밋 이력(v0.4.0 반영): 84c5163(v0.1.0) → 4000860(v0.2.0) → 7f64411(HANDOFF.md) → a1e8f8e(실제 공고 테스트 데이터 추가) → 365f3f8(v0.4.0) → [파일 배치 정리 커밋, 이번에 추가].
  - 로컬에서 히스토리 복원: `git clone gov-support-matching-skill.bundle my-skill` 또는 기존 폴더에서 `git pull gov-support-matching-skill.bundle master`

## 파일 배치 컨벤션
- **HANDOFF.md는 프로젝트 루트에만 둔다.** 하위 폴더(`gov-support-skill/` 등)에는 만들지 않는다. (과거 `gov-support-skill/HANDOFF.md`라는 오래된 사본이 실수로 남아있었는데 — 루트 버전과 내용이 어긋나 혼란을 줄 수 있어 삭제함. git bundle 히스토리에는 남아있으니 필요하면 복원 가능.)
- **`gov-support-skill/` 폴더는 사용자가 업로드한 원본 데이터 폴더**(예: `my_business_profile.json`)이고 스킬 코드 저장소와는 별개다. `.gitignore`에 추가해서 git 추적 대상에서 제외함 — 실수로 커밋되지 않도록.

## 진행 중 이슈 / 알아둘 것
1. **outputs 폴더는 파일 삭제·덮어쓰기가 제한된 동기화 마운트다.** 기존 파일을 Edit 도구로 직접 수정하거나 Write로 덮어쓰면 간헐적으로 파일이 중간에 잘려서(truncated) 문법 오류가 난다(`ls -la`의 수정시각이 실제와 안 맞는 것으로 확인 가능, 또는 `wc -l`로 줄 수가 안 맞는 것으로 확인 가능). 재현되는 우회법: **기존 파일을 새 이름으로 `mv`(rename)한 뒤, 원래 경로에 완전히 새로운 내용으로 Write.** "새 파일 생성"은 항상 안전하게 동작한다. 큰 폭의 수정은 물론이고, Edit 도구로 몇 줄만 추가하는 작은 수정에서도 재현된 적이 있음(2026-07-06, HANDOFF.md/.gitignore 둘 다) — **Edit 도구를 이 폴더의 기존 파일에 쓸 때는 매번 수정 직후 `wc -l`/`py_compile`/`yaml.safe_load`로 검증할 것.** 이상하면 즉시 rename+Write로 다시 쓸 것.
2. **같은 이유로 `git init`을 outputs 폴더 안에서 직접 실행하면 `.git/config`가 깨진다.** git 작업은 항상 `/tmp` 같은 완전히 자유로운 스크래치 공간에서 하고, 완료되면 `git bundle create ... --all`로 묶어서 단일 파일로 outputs에 복사한다. 파일 삭제가 필요하면 `mcp__cowork__allow_cowork_file_delete` 툴로 먼저 권한을 받아야 한다.
3. **judge_pass_recommendation은 여전히 "형식 요건" 체크일 뿐 "내용 품질" 체크가 아니다.** unconfirmed_sections==0 / unprepared==0 / 결격위험 없음(마감/서류 등 하드 실격 사유) / 페이지제한 존재라는 조건만 본다. 예산초과·rubric 미달 등은 confidence 점수엔 반영되지만 이 이진 게이트엔 아직 안 들어간다 — 실제 설득력·타당성 검증은 여전히 사람 몫이다.
4. **공고 자동 수집이 안 된다.** `collect_and_extract_announcements()`는 여전히 로컬 JSON 파일(목업 또는 손수 파싱한 실제 공고)만 읽는다. 기업마당/K-스타트업 API·PDF 자동 파싱 연동은 미착수(사용자가 이번 라운드에 명시적으로 보류함).
5. **rubric 매칭은 여전히 키워드 휴리스틱이다.** 동의어 테이블(v0.4.0)로 개선했지만 의미 기반(NLP) 매칭이 아니라서, 테이블에 없는 새로운 표현이 나오면 다시 오탐/누락 가능하다.
6. **문서명 fuzzy 매칭 미지원(사용자가 이번 라운드에 명시적으로 보류함).** documents_status의 document_name이 공고 required_documents 문자열과 정확히 일치해야 매칭된다. 실제 사업자 파일 테스트에서 문서명 표기가 달라(예: "사업자등록증" vs "사업자등록증 사본") 실제로는 준비된 서류도 전부 미준비로 집계됨.

## 실행 방법
```
python3 scripts/run.py test/sample_input_ideal.json                                    # READY_FOR_APPROVAL 재현 (목업 공고)
python3 scripts/run.py test/sample_input.json                                          # 정상이지만 서술형 필드 없어 DRAFT (목업 공고)
python3 scripts/run.py test/sample_input_edge.json                                     # 자격 데이터 일부 누락 -> DRAFT (목업 공고)
python3 scripts/run.py test/my_business_profile_input.json                             # 실제 mo,on 사업자 데이터 (목업 공고)
python3 scripts/run.py test/real_program_input.json scripts/real_announcements.json     # 실제 PDF 공고 + 실제 오늘 날짜 (이미 마감됨)
GOV_SKILL_TODAY=2026-03-15 python3 scripts/run.py test/real_program_input_simulated.json scripts/real_announcements.json  # 실제 PDF 공고 + 마감 전 날짜로 시뮬레이션
```
결과는 stdout(JSON)로 출력되고, quality_gate 미달/DRAFT 유지 이벤트는 `test/failure_log.jsonl`에 append됨.

## 다음에 할 만한 작업 (제안, 아직 미착수)
- PDF/HWP 공고문 자동 파싱 (이번 라운드에 보류됨)
- 문서명 fuzzy 매칭 (이번 라운드에 보류됨)
- `collect_and_extract_announcements()`를 실제 공고 소스(API/크롤러)에 연결
- judge_mode_self_review에 "내용 품질" 체크 보강, 예산/rubric 리스크를 judge_pass_recommendation 게이트에도 반영할지 검토
- 지자체별/타 부처 사업 스키마 확장 시 `eligibility` 스키마 필드 보완
