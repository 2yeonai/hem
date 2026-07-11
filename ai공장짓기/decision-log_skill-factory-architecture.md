# 결정 로그: 앱개발앱(스킬 팩토리) 구조 — 폴더복제 vs core+plugin
- 날짜: 2026-07-06
- 프로젝트: 앱을 개발할 수 있는 앱 (스킬 복제/스캐폴드 시스템)
- 관련 도메인: 정부지원사업(완성) / 꽃집(진행중) / 방역(대기) / 신규후보 10개(대기)

---

## 1. 배경 — 왜 이 질문이 나왔나
진행 중인 프로젝트 4개(정부지원사업/앱개발앱/꽃집/방역) + 신규 후보 10개(아이디어/학습변환/PPT/옛날옛적에/냉장고/가구배치/챗봇/이미지/콘텐츠재생산/3D캐릭터), 총 14개 아이템을 전부 "앱개발앱"이 찍어내는 구조로 만들 계획.
현재 실제로 진행 중인 방식: 정부지원사업 스킬 폴더를 통째로 복제해서 `manifest.yaml`의 `domain` 필드만 변경 (예: `gov_support` → `flower_shop`).
이 방식이 14개 도메인까지 확장 가능한지, 아니면 지금 domain-agnostic 코어 + plugin 구조로 전환해야 하는지가 미결정 상태였음. MODEL_ROUTER 기준 `architecture_decision` + `blind_spot` 해당 → Fable 5 승격 대상으로 판단.

## 2. Fable에게 전달한 카드 (raw 대신 압축)
```yaml
cards:
  - id: c1
    type: fact
    summary: 정부지원사업 매칭 스킬 v0.4.0 완성. business_profile+target_period 입력 → 공고매칭/신청서초안/심사위원모드 자기검수.
    evidence: 예산정합성 체크, 배점 동의어매칭, eligibility 성별/경력단절 필드 추가완료. 회귀테스트 6/6 통과.
    confidence: 1.0
  - id: c2
    type: fact
    summary: 다음 도메인(꽃집) 확장 방식 = 정부지원사업 폴더 통째 복제 + manifest.yaml의 domain 필드만 변경.
    confidence: 0.9
  - id: c3
    type: unknown
    summary: 이 복제 방식이 14개 도메인까지 확장 가능한지 검증 안 됨.
    confidence: 0.3
  - id: c4
    type: conflict
    summary: 정부지원사업 스킬 안에 도메인 종속 로직이 하드코딩돼 있을 가능성.
    confidence: 0.6
  - id: c5
    type: fact
    summary: 알려진 버그/한계 — outputs 폴더 truncation 버그, judge_pass_recommendation 형식만 체크.
    confidence: 1.0
open_questions:
  - 폴더 복제 유지 vs domain-agnostic 코어+plugin 전환?
  - 정부지원사업 스킬의 어떤 부분이 도메인 종속적이라 복제 시 깨지는가?
  - 14개 도메인까지 갈 때 유지보수 비용이 어디서 폭발하는가?
should_escalate_to_fable: true
escalate_reason: architecture_decision + blind_spot audit — 저비용 모델로 판단 불가, 방식이 굳어지기 전에 확인 필요
```

## 3. Fable 5의 답변 (원문 유지)

**decision:**
폴더 복제 유지 — 단, "꽃집 1개까지만, 그것도 실험으로." 3번째 도메인 전에 core+plugin 전환.

**근거:**
샘플 1개(정부지원사업)로 domain-agnostic 코어를 설계하는 건 거의 확실하게 틀린 경계선을 긋는 일이다. c4의 의심(예산체크·배점테이블·eligibility가 도메인 종속)은 맞을 확률이 높지만, 뭐가 종속인지는 추측이 아니라 꽃집 복제 diff가 알려준다. 복제 1회는 리팩토링 비용이 아니라 조사 비용. 반대로 14개 전부 복제하면 버그 수정 하나가 14번 작업이 되니 그쪽도 답 아니다. 결론: 두 번째는 복제, 세 번째부터 추상화.

추가 지적: c2의 "domain 필드만 변경"이라는 가정 자체가 제일 위험. 정부지원사업 스킬의 본질은 "공고매칭+신청서생성+심사시뮬레이션" 3단계인데, 꽃집에서 이 3단계 대응물이 카드 어디에도 정의돼 있지 않다. 대응이 없으면 이건 도메인 교체가 아니라 다른 스킬이고, 복제/플러그인 논쟁 자체가 무의미해진다.

**plan:**
1. truncation 버그부터 원본에서 수정 (복제 전에)
2. 꽃집 복제 진행하되 수정 로그 강제 — 파일·함수·프롬프트 문장 단위로 "바꿔야 했던 것" 전부 기록
3. 꽃집에서 3단계 대응물 정의 문서 1장 작성 (공고→?, 신청서→?, 심사위원→?). 대응 안 되면 여기서 멈추고 스킬 범위 재정의
4. diff 기반으로 경계선 도출 — 불변부(파이프라인 골격: 입력→매칭→초안→자기검수, 라우팅, 출력관리) vs 가변부(입력스키마, 용어/동의어테이블, 검증규칙, 심사rubric, 프롬프트템플릿). 가변부는 설정파일로 분리 후보
5. 3번째 도메인(방역)을 plugin 구조로 최초 구현 → 꽃집을 그 구조로 역이식 검증 → 정부지원사업 원본은 마지막에 이식
6. judge 품질검증은 도메인별 rubric을 plugin 데이터로 넣는 구조로 이때 같이 해결

**blind_spots (정부지원사업 스킬 내 도메인 종속 후보):**
- `check_budget_compatibility` — 정부사업 비목체계 전제, 꽃집엔 대응 개념 없거나 완전히 다름
- 배점 동의어 테이블 — "배점표" 자체가 심사제도 전용 개념
- eligibility 필드(성별/경력단절) — 정책 자격요건 개념, 다른 도메인 스키마와 안 맞음
- `target_period` — 공고 시즌성 전제, 상시운영 도메인에선 의미 변질
- 프롬프트 텍스트 내 하드코딩 — "심사위원/공고/신청서" 같은 단어가 코드 아닌 프롬프트에 박혀 있으면 diff에서 놓치기 쉬움
- 회귀테스트 6개 — 전부 정부지원사업 데이터 기준, 복제본 6/6 통과해도 아무것도 증명 안 함 (false pass)
- `judge_pass_recommendation` 형식체크 기준 — 신청서 출력스키마에 묶여 있을 가능성
- outputs 파일명/경로 컨벤션, HANDOFF.md의 도메인 특화 서술

**stop_rules:**
- 나머지 12개(방역+신규후보 10개+11번째~) 도메인 복제 착수 금지 — 꽃집 실데이터 검증 완료 전까지
- core 리팩토링 착수 금지 — 꽃집 diff 나오기 전엔 추상화 설계 자체를 하지 않는다
- truncation 미수정 상태 복제 금지
- 복제본에서 발견한 결함을 복제본에서만 수정 금지 — 원본 수정 후 반영 경로를 남길 것
- 14개 도메인 목록 확정 금지 — plugin 구조가 3개 도메인에서 검증되기 전까지 후보는 후보로만

## 4. why_fable 로그
```json
{
  "why_fable": true,
  "reason": "architecture_decision + blind_spot audit, 14개 도메인 확장 구조 결정",
  "cheaper_model_attempted": false,
  "input_tokens_estimate": null,
  "raw_attached": false
}
```

## 5. 다음 액션 (이 로그 기준 실행 순서)
- [ ] outputs 폴더 truncation 버그 원본에서 수정
- [ ] 꽃집 3단계 대응물 정의 문서 작성 (공고→?, 신청서→?, 심사위원→?)
- [ ] 꽃집 복제 진행 + 수정 diff 로그 기록 시작
- [ ] diff 완료 후 core/plugin 경계선 문서화 → 이 파일에 추가
- [ ] 방역 도메인은 diff 나오기 전까지 착수 보류

## 6. 후속 작업 — manifest.yaml v2 스키마 (2026-07-06 같은 날 추가)
목표: Fable 5 설계안(stage kind=local/model/human, depends_on)을 반영한 manifest.yaml v2 스키마 작성.

**선행 조건 (먼저 결정 후 시작):**
1. 공유 컨텍스트 객체 스키마 정의 — 주문 원문, STT 결과, 정리본, 검수 코멘트, 배송사진 URL, 장부 기록 각각 어느 stage가 write하고 어느 stage가 read하는지 필드 단위로 명시
2. check/on_fail 출력 형태 확정 — model stage self-check: `{pass: bool, confidence: float, reason: string}` 제안, 검토 후 확정
3. human stage reject 시 복귀 대상 필드 확정 — 예: `on_fail.human_reject.return_to: <stage_id>`

**작업 범위:**
- 위 3개 선행 결정을 반영한 manifest.yaml v2 스키마(YAML) 작성
- stage 필드: id / kind / io(공유객체 필드 참조) / check / on_fail / depends_on / async(bool, human stage용)
- quality_gate 두 모드(암묵 self-check / 명시 human stage) 예시 각 1개 포함
- 스키마 자체에 버전 필드(schema_version: v2) 포함

**산출물:** `manifest.schema.v2.yaml` (필드별 설명 주석 포함) — 이 파일과 같은 폴더에 저장.

**주의:** 선행조건 3개 중 하나라도 답이 안 나오면 작업 중단하고 보고. 임의로 확정하지 않는다.

→ 진행 상황 및 채택된 설계는 아래 이어서 기록:

### 6.1 선행조건 처리 결과 (실행 시점 기록)
- **정밀도 1 (공유 컨텍스트)**: 6개 필드 모두 구체적인 stage id에 매핑해 `manifest.schema.v2.yaml`에 반영. 단, "주문 채널이 텍스트/음성 둘 다 존재하고 음성은 STT를 거친다"는 가정을 깔고 설계함 — **ASSUMPTION, 확인 필요**. 카카오톡 텍스트 주문만 있다면 `stt` stage 자체가 불필요할 수 있음.
- **정밀도 2 (check 출력형태)**: 제안된 `{pass, confidence, reason}`을 그대로 채택. 정부지원사업 스킬의 `judge_mode_self_review`는 `rejection_risks`(array)까지 반환했었는데, v2에서는 이를 필수 필드로 승격하지 않고 stage별 옵션 확장 필드로만 열어둠 — 정부지원사업 원본을 나중에 이 스키마로 이식할 때 다시 검토 필요.
- **정밀도 3 (human reject 복귀필드)**: 제안된 `on_fail.human_reject.return_to: <stage_id>` 형식 그대로 채택, 예시(`human_review` 반려 시 `clean_order`로 복귀)로 스키마에 포함.

---

## 7. 결정 로그: 방역 문서 승인 워크플로우 (2026-07-07, Fable 5)

### 7.1 배경
방역 파이프라인 테스트(골든셋 12건)에서 발견된 구조 공백: 완료보고서·소독증명서라는 "문서 자체"를 대표자가 승인하는 단계가 없음. 기존 `대표자검수` stage는 문서 생성 전(현장 작업결과) 단계라 문서 승인과는 별개 문제. 소독증명서는 법정 서식이라 허위·오류 발급 시 법적 리스크 — 대표 승인 없이 발송되면 안 됨. 승인 4상태(초안/승인대기/승인완료/반려)를 표현할 자리가 구조상 없다는 게 테스트로 확인됨(HANDOFF 갭 card-A, confidence 0.9). 사용자가 카드 정리 후 Fable 5 판단 직접 요청(승인 절차 충족).

### 7.2 Fable 5의 결정 (3건)

**결정 1 — 새 stage도 완전 분리도 아닌 절충: "상태는 문서가 갖고, 파이프라인엔 게이트 1개"**
- 승인 상태는 문서 자체의 필드로 관리. `document_draft.report`/`document_draft.certificate` 각각에 공통 승인 블록 추가: `status`(초안/승인대기/승인완료/반려), `version`, `approved_by`, `approved_at`, `rejection_reason`, `rejection_target`.
- 근거: ① stage는 완료/미완료만 표현하는 일방향 흐름인데 승인은 반려→재생성→재승인 루프. ② 한 건에서 문서 2종이 나오고 각각 승인 상태가 다를 수 있어(보고서 승인 + 증명서 반려) stage 단위 표현 불가. ③ 완전 별도 흐름은 실행기를 하나 더 만드는 셈이라 과함. 기존 결정 원칙(bundle=필드 계약, schedule=외부 스케줄러)과 동일 — 구조 문법을 새로 발명하지 않는다.
- 새 stage `문서승인`(kind: human) 1개를 문서생성봇 뒤·발송/저장 stage 앞에 배치. `run_if: 승인필수_문서가_존재함`.
- 잠금 규칙: 승인완료 시 `locked=true`, 이후 수정 불가 — 수정하려면 새 버전.
- **철칙: status가 승인완료가 아닌 문서는 절대 발송하지 않는다** (발송 stage에서 강제).

**결정 2 — 반려 복귀: 사유에 따라 2갈래, 기본은 문서생성봇**
- 문서만 문제(문구/서식/오타) → `문서생성봇`부터 재생성, 같은 데이터로 version+1.
- 데이터 자체가 틀림(약품명/면적/날짜) → `현장완료입력봇`으로 복귀해 수정 후 문서생성봇 재실행.
- 승인자가 반려 시 `rejection_target`으로 선택. 현재 `on_fail.human_reject.return_to`는 고정값 1개뿐이라 표현 불가 → return_to를 "rejection_target별 매핑"으로 소폭 확장(단일값 하위호환 유지).
- 반려된 버전은 삭제하지 않고 보존 — 법정 서식 감사 추적.

**결정 3 — 도메인 재사용: "소독증명서"를 스키마에 넣지 않는다**
- 스키마 레벨에 올라가는 것 3가지만: ① 승인 블록 필드 계약, ② 문서 타입별 `approval_required: true/false` 플래그, ③ human 게이트 + rejection_target 매핑 패턴.
- "소독증명서는 법정서식이라 승인 필수"는 방역 manifest 인스턴스에서 `certificate.approval_required: true` 선언으로 표현. 꽃집 견적서·정부지원 신청서도 같은 블록으로 재사용 가능.
- 4단계 플랫폼에서 도메인이 정하는 건 문서 종류·승인 필수 여부·반려 복귀 매핑 3가지뿐.

### 7.3 why_fable 로그
```json
{
  "why_fable": true,
  "reason": "법정문서 승인 흐름 구조 공백 — 되돌리기 비싼 파이프라인 구조 결정 + 4단계 플랫폼 재사용성 판단",
  "cheaper_model_attempted": true,
  "input_tokens_estimate": 6500,
  "raw_attached": false
}
```

### 7.4 다음 액션 (Sonnet 세션에서 실행)
- [x] `manifest.schema.v2.yaml`: 승인 블록 필드 계약 + `approval_required` 플래그 + return_to 매핑 확장 반영
- [x] `클로드 방역 ai\manifest.yaml`: `문서승인` stage 추가(문서생성봇 뒤), document_draft에 승인 블록 인스턴스 추가
- [x] `scripts/run.py`: 발송 전 status=승인완료 확인 규칙 + 반려 2갈래 복귀 mock 구현
- [x] `validate_manifest.py` 재검증 후 골든셋 재실행 — 갭 2번(승인 4상태 표현) 해소 확인

### 7.5 실행 결과 (2026-07-07, Sonnet 세션에서 완료)

전부 반영 완료. 요약:

- **스키마**: `check_output_schema.approval_block` 신규(status/version/approved_by/approved_at/rejection_reason/rejection_target/version_history) — 도메인 무관 범용 패턴. `approval_required`는 필드가 아니라 "문서 객체의 형제 필드로 두는 컨벤션"으로 문서화(강제 스키마 필드로 만들지 않음). `stage_fields.on_fail.human_reject.return_to`를 단일값(string, 기존 하위호환)과 매핑(object, rejection_target별 라우팅) 둘 다 지원하도록 확장.
- **방역 manifest**: `document_draft.report`/`certificate` 각각에 `approval_required`+`approval` 블록 추가, 기존 document_draft 최상위 단일 `locked`는 폐기하고 report/certificate 각자의 `locked`로 이동(문서 종류별 독립 잠금 필요해서 — 마이그레이션, 예전 필드와 호환 안 됨). 새 stage `문서승인`(kind: human, run_if: 승인필수_문서가_존재함)을 문서생성봇 뒤·문자장부봇 앞에 삽입, `문자장부봇.depends_on`을 `[현장완료입력봇]`→`[문서승인]`으로 바꿔 DAG 자체로도 발송이 승인 게이트 뒤에 오도록 보장. summary: human 1개→2개, total 17→18.
- **run.py**: `문서생성봇`이 report/certificate 각각의 approval 블록을 초기화(반려 후 재생성 시 version+1, 반려 이력은 `version_history`에 보존 — 삭제 안 함)하도록 갱신. 신규 `run_문서승인` mock(테스트용 `문서승인_시뮬레이션` 입력으로 승인/반려 흉내, 리스트 지정 시 재시도마다 순차 소비). `_run_document_approval_cycle()` 신규 — 문서생성봇↔문서승인을 반려-재작업 루프로 묶어 명령형으로 처리(depends_on 그래프에 순환 안 만듦 — return_to는 그래프 엣지가 아니라는 스키마 원칙 유지). rejection_target="표현오류"→문서생성봇 재실행, "데이터오류"→현장완료입력봇 복귀 후 문서생성봇 재실행, 둘 다 실제 테스트로 확인. **가장 중요한 안전장치**: `run_문자장부봇`이 발송 직전 `approval_required=true`인 문서 중 `approval.status != 승인완료`인 게 하나라도 있으면 `RuntimeError`로 발송 자체를 강제 차단 — 파이프라인 순서만 믿지 않는 이중 검증.
- **검증**: `validate_manifest.py` FAIL 0/WARN 0. `test_12cases_batch.py` 갱신 후 재실행 — 기본 12건(자동승인) 전부 문서 승인상태=승인완료로 도달, 추가 시나리오 3개(A: 표현오류 반려 1회→재승인 PASS, B: 데이터오류 반려 1회→현장완료입력봇 복귀→재승인 PASS, C: 지속 반려→재시도 소진→발송 시도 시 안전장치가 RuntimeError로 실제 차단 PASS) 전부 통과. card-A(및 병합 전 card-03/04/07) 해결 확인.
- **남은 open_question**: 반려 재시도 최대 횟수(mock 3회는 임의값, 실제 운영 기준 미정), version_history 보존 형식/기간(법정 보존기간 2년 잠정값과 관계 미정) — manifest.yaml open_questions에 기록해둠, 이번에 결정 안 함.

## 관련 문서

- [[ai공장짓기/방역_업무흐름_및_꽃집재사용성_분석_2026-07-07|방역_업무흐름_및_꽃집재사용성_분석]]
- [[클로드 정부지원사업 ai/마이그레이션_diff_리포트_v1_to_v2|마이그레이션_diff_리포트_v1_to_v2]]
- [[클로드 방역 ai/법정요구사항_대조표_2026-07-07|법정요구사항_대조표_2026-07-07]]
- [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]
- [[ai공장짓기/runner/README|README]]
- [[ai공장짓기/failure_log|failure_log]]
- [[ai공장짓기/HANDOFF|HANDOFF]]
- [[ai공장짓기/설계노트/1_플랫폼_공통_스펙_(모든_공장이_따르는_것)|1_플랫폼_공통_스펙_(모든_공장이_따르는_것)]]
- [[0. Docs/글로벌지침_Fable프로토콜|글로벌지침_Fable프로토콜]]
