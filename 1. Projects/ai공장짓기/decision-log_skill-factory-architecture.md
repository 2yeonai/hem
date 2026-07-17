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
- [[1. Projects/클로드 정부지원사업 ai/마이그레이션_diff_리포트_v1_to_v2|마이그레이션_diff_리포트_v1_to_v2]]
- [[1. Projects/클로드 방역 ai/법정요구사항_대조표_2026-07-07|법정요구사항_대조표_2026-07-07]]
- [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]
- [[ai공장짓기/runner/README|README]]
- [[ai공장짓기/failure_log|failure_log]]
- [[ai공장짓기/HANDOFF|HANDOFF]]
- [[ai공장짓기/설계노트/1_플랫폼_공통_스펙_(모든_공장이_따르는_것)|1_플랫폼_공통_스펙_(모든_공장이_따르는_것)]]
- [[0. Docs/글로벌지침_Fable프로토콜|글로벌지침_Fable프로토콜]]

## 2026-07-13 — 배치 결정 세션 (Fable 5)

- **입력**: 발견카드_전체스캔_2026-07-13 + 핵심맥락 결정포인트 3개 + Fable_작업대기열. 원문 재스캔 없이 카드만으로 결정 (효율전략 준수).
- **C1 잘림 버그 재발방지 (신규 볼트 규칙)**: ① 신규/전면 재작성은 heredoc+바이트확인만 ② 모든 md 마지막 줄 `<!-- ok -->` sentinel + 수정 직후 verify_write.py PASS 필수 ③ 복구는 git HEAD 대조. 근거: 잘림은 항상 파일 끝 → sentinel 부재=잘림, 기계 판정 가능.
- **U1**: _inbox 중복 인덱스는 Archive로 이동(삭제 금지), Resources판 정본 확정.
- **U2**: 깨진 링크 ~150개는 `_원문` 실제 파일명으로 스크립트 재매핑 — 확정 건만 자동, 나머지 목록 보고.
- **U3**: 원본 바이너리 부재는 의도적 설계로 간주, 스캔에서 비-md 링크 제외. 혜미 yes/no 1개만.
- **D1 방역 3봇**: 지금 판정 안 함. R1 골든셋(혜미 30~60분) → R2 배치 → Sonnet 판정, 충돌 시에만 F3.
- **D2 정부지원**: 스크래핑·PPT류 둘 다 착수 안 함. 스크래핑=F1(8월), PPT류 트리거=선정 통보. R3 실전 투입은 지금 진행.
- **D3 플랫폼**: 9개 후보=9월 F4 후 1순위 라인부터. Fable 총설계 3개=방역 검증 직후 8월 초 1회.
- **F1/F2**: 아직 아님(8월/9월 유지). F4: 9월 유지.
- **산출물**: [[ai공장짓기/감사_로드맵_2026-07-13|감사_로드맵_2026-07-13]] (실행 순서 E1~E7 포함).

<!-- ok -->

## 2026-07-13 (2차) — 운영 우선순위 판정 (Fable 5)

- **질문**: 혜미 제안 순서(옵시디언→정부지원→AI회사→mo,on)가 맞는가.
- **판정**: 옵시디언 최우선 동의(단 반나절 범위 제한). 정부지원 완성=mo,on 신청 — 같은 작업이라 분리 불가, mo,on을 AI회사보다 앞으로. AI회사는 기존 결정 유지(8월 총설계·9월 착수). 제안에 빠진 방역 골든셋(혜미 1시간)을 ⓪순위로 추가 — 여전히 유일 병목.
- **부수 결정**: 강의=기존 최종선별 4개 유지+Zapier 이월 권장 / 모델="고민되면 Sonnet" 한 줄로 위임 / 정보 유입=기존 운영규칙 1번 재확인(새 규칙 없음) / 루트 떠돌이·꽃집 오염 정리는 Sonnet 위임.
- **산출물**: [[0. Docs/혜미_운영지침서_2026-07-13|혜미_운영지침서_2026-07-13]] (§1~§6 + 병렬 라인 A/B/C).

## 8. 결정 로그: 공장 설계 재확정 — 탭 A/B/C (2026-07-13, Fable 5)

### 8.1 배경
신규 11개 공장(플랫폼 9개 후보 + 학습변환 + 자료정리 등)을 구조화하기 위해 Fable 5 세션을 탭 A/B/C 3개로 나눠 병렬 진행. 전제 조건: "앱형(제작자 본인이 앱처럼 만들어 쓰는 형태) · 소수공유(제작자 본인+지인 소수와만 공유, 비상용)". 탭 A=플랫폼 공통조건, 탭 B=학습변환 공장, 탭 C=자료정리 공장. 3건 모두 설계 판단만 완료된 상태이고, manifest.yaml/SKILL.md 등 실제 파일 반영과 해당 공장 폴더 생성 자체가 아직 없음 (근거: `2. Areas/Claude 세션로그/2026-07-13.md` "### 공장 설계 재확정" 섹션 및 같은 파일 "공장설계 탭 A/B/C(플랫폼공통조건/학습변환/자료정리) 3건은 판단만 나온 상태 — manifest/SKILL.md 실제 반영은 다음 실행 세션 과제" 문장).

### 8.2 결정 1 (탭 A) — 플랫폼 공통조건 확정

**결정 배경**
신규 11개 공장이 기존 3개 공장(정부지원사업/꽃집/방역)과 달리 "제작자 본인+지인 소수 공유, 비상용" 조건이라는 점이 처음 판정 대상이 됨. 기존 stages 구조(local/model/human)를 그대로 쓸 수 있는지, 아니면 소수공유·비상용이라는 조건 때문에 스키마를 바꿔야 하는지가 미결이었음.

**확정된 구조**
stages 구조(local/model/human) 자체는 변경 불필요. 대신 다음 5개가 추가로 필요하다고 판정: ① 데이터 네임스페이스, ② human 담당자 속성, ③ 자격증명 분리, ④ model 비용 상한, ⑤ 공유장부 scope 플래그. 판정 기준 2가지도 함께 확정: 검수 권한은 "데이터 소유권을 따른다" 원칙, 공동/개인 장부 판별은 "서로의 항목을 봐야 업무가 성립하는가" 기준. 법정서식(방역의 소독증명서 등)은 심사(승인) 여부와 무관하게 법정요건을 그대로 적용한다는 기존 원칙(§7 결정 3 참조)도 재확인됨.

**why_fable**
공유·비상용이라는 새 전제가 기존 3개 공장에 없던 조건이라 저비용 모델로는 판단 불가한 architecture_decision. 11개 신규 공장 전체에 적용될 공통 스키마 확장이라 되돌리기 비용이 크고, "검수 권한=데이터 소유권" "공동/개인 장부 판별 기준" 등 아직 아무 문서에도 없던 새 판단기준을 만드는 작업이라 회사 CLAUDE.md의 "새 설계 결정" 기준(Fable/고비용 티어 대상)에 해당.

**아직 반영 안 된 것**
5개 필드(데이터 네임스페이스/human 담당자 속성/자격증명 분리/model 비용 상한/공유장부 scope 플래그)의 `manifest.schema.v2.yaml` 반영 없음. 기존 3개 공장(방역 등) manifest.yaml에도 아직 미적용. 검수 권한·공동/개인 장부 판별 기준을 문서화한 별도 설계노트 없음. 신규 11개 공장 폴더 자체가 아직 미생성.

**다음 액션**
- [ ] 5개 필드를 `ai공장짓기/manifest.schema.v2.yaml`에 반영
- [ ] "검수 권한=데이터 소유권" / "공동·개인 장부 판별=서로의 항목을 봐야 업무가 성립하는가" 두 원칙을 설계노트로 문서화
- [ ] 신규 11개 공장 중 1개를 골라 위 스키마로 최초 적용 검증

### 8.3 결정 2 (탭 B) — 학습변환 공장 재설계

**결정 배경**
기존에 구상돼 있던 학습변환 공장 골격("영상 1개 → 단발 요약")이 실제 사용 패턴(강의를 여러 회차에 걸쳐 듣고 누적 학습)과 맞지 않는다는 문제가 제기되어 재설계 판단이 필요했음. 특히 여러 회차를 반복 요약하면 내용이 조금씩 왜곡되는 "드리프트" 문제를 어떻게 막을지가 핵심 쟁점.

**확정된 구조**
기존 "영상 1개→단발 요약" 골격 폐기, "회차별 정리본 + 누적 종합본" 이원 구조로 재설계. 종합본은 이전 회차의 산문(요약 텍스트)을 다시 입력으로 되먹이지 않고, 구조화된 course-state(강의 전체의 구조화된 상태 데이터)에서 렌더링하여 반복 재요약으로 인한 드리프트를 방지. 강사 스타일 카드(강사의 화법·설명 패턴을 정리한 카드)는 1회만 추출해 이후 재사용. N회차마다 checkpoint-rebuild(누적 상태를 처음부터 다시 조립해 드리프트를 교정하는 단계)를 수행. stages 9개로 재정의: ingest(수집) → normalize(정규화) → style-profile(강사 스타일 카드 추출) → derive-session(회차별 정리본 도출) → link(연결) → merge-cumulative(누적본 병합) → inspect(검수) → assemble(종합본 조립) → checkpoint-rebuild(드리프트 교정 재조립).

**why_fable**
"영상 1개→단발 요약"이라는 기존 골격 자체를 폐기하는 결정이라 파이프라인 구조를 되돌리기 어려운 architecture_decision. 반복 재요약 드리프트라는, 저비용 모델 판단으로는 놓치기 쉬운 blind spot(누적 종합본을 산문 재입력으로 만들면 왜 위험한지)을 짚어내는 판단이 포함돼 있어 Fable 5 승격 대상.

**아직 반영 안 된 것**
학습변환 공장 폴더 자체가 미생성. `manifest.yaml`에 stages 9개(ingest/normalize/style-profile/derive-session/link/merge-cumulative/inspect/assemble/checkpoint-rebuild) 미반영. `SKILL.md`, course-state 스키마, checkpoint-rebuild 트리거 주기(몇 회차마다인지 구체값) 모두 미정/미작성.

**다음 액션**
- [ ] 학습변환 공장 폴더 생성 + `manifest.yaml` 초안에 stages 9개 반영
- [ ] course-state 구조(필드 스키마) 정의
- [ ] checkpoint-rebuild 주기(N값) 확정
- [ ] `SKILL.md` 작성 (알려진 한계 포함)

### 8.4 결정 3 (탭 C) — 자료정리 공장 재설계

**결정 배경**
기존 자료정리 공장 골격이 질의응답형(ingest→answer, 자료를 넣으면 질문에 답하는 방식)으로 구상돼 있었으나, 실제 필요는 "여러 자료를 모아 하나의 학습 로드맵으로 합성"하는 배치 처리 쪽이라는 문제 제기로 재설계 판단이 필요했음. 또한 같은 세션에서 다룬 학습변환 공장(탭 B)과 패턴이 겹치는지 여부도 함께 판단 대상이었음.

**확정된 구조**
기존 질의응답형(ingest→answer) 골격 폐기, "주제별 배치 종합"(로드맵 합성) 파이프라인형으로 전환. 8단계로 재설계: 형식별 어댑터(입력 자료 형식마다 다른 처리) → 카드 정규화 → 주제 클러스터링 → 중복병합 → 학습메타 태깅 → 순서그래프(학습 순서 관계 그래프) → 로드맵 합성. 학습변환 공장(탭 B)과 "동일 패턴, 프로파일만 다름"으로 판단하여, 별도 공장으로 복제하지 말고 `ordering: given|inferred`(순서가 주어져 있는지, 추론해야 하는지) 파라미터로 하나의 파이프라인에 통합할 것을 권고.

**why_fable**
기존 질의응답형 골격을 폐기하고 파이프라인형으로 전환하는 architecture_decision인 데다, "학습변환 공장과 별도 복제할지 통합할지"라는 §6(2026-07-06)의 "3번째 도메인부터 core+plugin 전환" 원칙과 직결되는 재사용성 판단이 겹쳐 있어 저비용 모델 단독 판단으로는 부적합. 두 공장을 하나로 합칠지 여부는 이후 전체 11개 공장 구조에 영향을 주는 되돌리기 비싼 결정.

**아직 반영 안 된 것**
자료정리 공장 폴더 자체가 미생성. 학습변환 공장과의 통합 파이프라인(`ordering: given|inferred` 파라미터 포함) 설계가 `manifest.schema.v2.yaml`이나 개별 `manifest.yaml`에 전혀 반영 안 됨. 8단계(형식별 어댑터/카드 정규화/주제 클러스터링/중복병합/학습메타 태깅/순서그래프/로드맵 합성 — 7개로 나열됐으나 세션로그 원문은 "8단계"로 명명, 단계 경계 재확인 필요) 구조 자체도 문서화 안 됨.

**다음 액션**
- [ ] 학습변환 공장(8.3)과의 통합 여부를 실제 설계 작업 시작 전에 재확인 (원문상 "8단계"라는 명명과 나열된 7개 항목 간 불일치 여부부터 확인)
- [ ] `ordering: given|inferred` 파라미터를 `manifest.schema.v2.yaml`에 반영할지, 개별 manifest에만 둘지 결정
- [ ] 자료정리 공장(또는 통합 공장) 폴더 생성 + manifest 초안 작성

### 8.5 공통 메모
3건 모두 "제작자 본인+지인 소수 공유, 비상용" 전제 위에서 나온 판단이며, 실전(다수 사용자·상용) 조건으로 바뀌면 8.2의 5개 필드부터 재검토 필요. 3건 다 이번 세션에서는 설계 판단만 확정됐고 실행(파일 반영)은 다음 Sonnet 세션 과제로 남김 — 이 규칙은 이 항목 작성 시점에도 그대로 지켜, manifest.yaml/SKILL.md 등은 이번 decision-log 갱신에서 손대지 않음.

---
2026-07-14 Sonnet 세션: 2026-07-13 Fable 5 세션(탭 A/B/C)의 플랫폼 공통조건·학습변환 공장·자료정리 공장 재설계 결정 3건을 `2. Areas/Claude 세션로그/2026-07-13.md` 원문 근거로 §8에 기록 완료 — manifest.yaml/SKILL.md 등 실제 파일 반영은 하지 않음(다음 실행 세션 과제로 유지).

## 9. 결정: "옛날옛적에" 동화공장 Fable 게이트 카드 3건 해소 (2026-07-14, 혜미 회신)

**배경**: 2026-07-13 세션(Fable 5)에서 정리된 라우팅 카드 3건(scope-ost conf 0.55, safety-free-input conf 0.6, ip-collision conf 0.5)이 미결 상태였음. 2026-07-14 혜미가 직접 답변해 3건 모두 해소.

**해소 1 — scope-ost (OST/노래 기능 MVP 포함 여부)**: **확정: 포함.**

**해소 2 — safety-free-input (아이 자유입력 안전필터 설계)**: 전제 자체가 변경됨 — 애초 상정했던 "아이가 직접 자유 텍스트를 입력"하는 형식이 아니라, **"부모가 아이가 말한 것을 대신 입력해주는"** 형식으로 확정. 입력 주체가 아동이 아니라 보호자이므로 "아동 실시간 자유입력 유해 콘텐츠 필터"라는 원래 문제 정의 자체가 바뀜. 다만 부모가 입력한 내용도 그대로 아동 대상 콘텐츠(동화·노래)로 렌더링되므로, 최소 수준의 부적절 표현 필터는 입력 주체와 무관하게 여전히 필요하다고 판단(콘텐츠의 최종 소비자가 아동이라는 사실이 안전 요구를 만드는 것이지, 입력 주체 문제가 아님).

**해소 3 — ip-collision (실존 IP 캐릭터명 입력 시 대응)**: **현재 단계는 허용.** 지금이 "개인 소유 + 테스트" 용도이므로 실존 캐릭터명 사용 가능. 단, **배포(다수 사용자 대상 서비스화) 시점에는 재검토 필수** — 저작권·라이선스 리스크가 테스트 단계와 다르게 작동하므로, 이 조건은 배포 게이트에서 다시 걸리는 것으로 남겨둠.

**아직 반영 안 된 것**: 옛날옛적에 공장 폴더 자체가 미생성 상태 유지. §7(D3 결정, 2026-07-13)에 따라 9개 신규 후보 착수 시점은 **9월, F4 재감사 이후**로 이미 확정돼 있음 — 이번 해소는 "설계 질문 3개에 대한 답"이지 "지금 착수해도 된다"는 뜻이 아니다. manifest.yaml/SKILL.md 실제 작성은 9월 착수 시점에 이 3개 답을 그대로 반영해서 진행.

**다음 액션**:
- [ ] 9월 착수 시점에 scope-ost/safety-free-input/ip-collision 3건 답을 옛날옛적에 manifest.yaml/SKILL.md에 반영
- [ ] 배포 검토 시점에 ip-collision 재검토(캐릭터별 라이선스 확인)

---
2026-07-14 Sonnet 세션(2차): 옛날옛적에 Fable 게이트 카드 3건에 대한 혜미 답변을 §9로 기록. 실제 착수는 여전히 9월(D3 결정 유지).

## 10. 옛날옛적에 1차 스캐폴드 착수 (2026-07-14, 혜미 명시적 승인)

**배경**: §9에서 D3 결정(9월, F4 재감사 이후 착수)을 유지한다고 기록했으나, 같은 날 혜미가 이 공장 1건에 한해 "지금 바로 착수해도 된다"고 명시적으로 승인함. 나머지 신규 후보(9개, 옛날옛적에 포함 시 10개)는 여전히 9월 착수 원칙을 유지 — 이번 승인은 옛날옛적에 1건에만 적용되는 예외.

**실행 내용**: `1. Projects/클로드 옛날옛적에 ai/` 폴더 신규 생성, SKILL.md/manifest.yaml(schema_version v2, domain: kids_story, 8 stage — local 4/model 3/human 1)/scripts/run.py(mock stub)/test/sample_input.json 1차 스캐폴드 작성 완료. §9에서 해소된 3건(scope-ost/safety-free-input/ip-collision) 전부 manifest.yaml 각 stage 주석과 SKILL.md에 반영함(OST생성봇=①, 발화수집봇+안전선별봇=②, 캐릭터_IP_점검봇=③). `validate_manifest.py` FAIL 0/WARN 0 확인, `run.py test/sample_input.json` 8개 stage 전부 통과(PASS) 확인.

**아직 반영 안 된 것**: 원본 기획서("전체본.md")가 vault에 없어 실제 UI/사용자 플로우/타겟 연령대는 1차 추정 — SKILL.md "알려진 한계"에 명시. 실제 모델(동화 창작/작사/TTS) 연동, 안전선별봇의 local vs model 격상 여부, OST 저작권 필터, 배포 게이트 정식 IP 목록/절차는 모두 미착수(manifest.yaml open_questions 참고).

**다음 액션**:
- [ ] 혜미가 원본 "전체본.md" 기획서를 다시 vault에 올리면 manifest.yaml/SKILL.md의 1차 추정 필드 재검토
- [ ] 배포 검토 시점에 ip-collision 재검토(캐릭터별 라이선스 확인) — §9에서 이미 예정된 항목, 착수 시점만 당겨짐

## 11. 방역 3봇(현장분리봇/견적금액산정봇/현장사진봇) 판정 — 골든셋 기반 (2026-07-16, Sonnet 세션 T2)

**배경**: §7(2026-07-13 배치결정 세션) D1에서 "지금 판정 안 함. R1 골든셋(혜미 30~60분) → R2 배치 → Sonnet 판정, 충돌 시에만 F3"로 미뤄둔 항목. 2026-07-15 대표자 실사례 인터뷰로 `golden_set.yaml`이 채워짐(R1 완료). 이번 세션(T2)에서 배치테스트 재실행(R2) + `golden_set.yaml`의 `추가_확인사항` 답변을 근거로 3봇 필요 여부를 Sonnet이 판정(충돌 없어 F3 미해당).

**배치테스트 결과**: `python3 scripts/test_12cases_batch.py` 전체 PASS. 실행된 12케이스 전부 만족도수집봇까지 도달, [검증 1] 문서요청 종류 분기, [검증 2] 승인 4상태(초안/승인대기/승인완료/반려) + 반려 2갈래 복귀 + 미승인 발송 차단 안전장치, [검증 3] D-day/리마인더 스케줄 이어짐 — 3개 검증 모두 `[해결됨]`으로 통과. 3봇은 manifest.yaml 설계대로 `run_if: 미정_골든셋수집후결정` 상태라 파이프라인 로그에 `[SKIP] ... 골든셋 확보 전까지 기본 꺼짐`으로 정상적으로 건너뛰며, 이 SKIP 상태에서도 나머지 파이프라인은 문제없이 끝까지 진행됨을 재확인.

**판정 1 — 현장분리봇: 보류**
근거: `golden_set.yaml 추가_확인사항.한_통화에_여러_현장_이야기가_섞이는_일이_실제로_자주_있나요` = "가끔 있음 - 한 고객이 빌라 여러 채를 요청하는 경우, 단 자주는 아님". 발생 자체는 실사례로 확인됐지만 빈도가 낮아, 지금 model(sonnet) tier 스테이지를 새로 켤 만큼의 비용 대비 효과가 불분명. 현재도 대표자검수(human) 게이트가 남아있어 드문 다현장 건은 사람이 직접 알아채 처리 가능. 다현장 실사례가 몇 건 더 쌓여 빈도·패턴이 뚜렷해지면 재판정.

**판정 2 — 견적금액산정봇: 불필요**
근거: `golden_set.yaml 추가_확인사항.방역_견적_금액을_정해진_표나_기준으로_계산하시나요` = "평수·벌레 종류 기준 대략적인 틀은 있음(20평 이하는 2만5천원 동일, 이후 평수가 늘수록 증가·예 30평=10만원, 해충 종류별로도 다름)... 다만 정해진 고정 표는 아니고 사장님이 현장을 직접 보고 판단해서 견적을 냄." 최종 금액이 표 계산이 아니라 현장 육안 판단에 좌우되므로, 자동 산정 로직 자체가 실제 견적 방식과 맞지 않음. 대략적인 틀(구간값)은 참고자료로만 남기고, 자동 계산 stage는 만들지 않는다.

**판정 3 — 현장사진봇: 보류 (용도 불일치 — 재설계 필요)**
근거: `golden_set.yaml 추가_확인사항.현장_방역_끝나고_사진을_찍어두시나요` = "네, 마케팅 콘텐츠용으로 현장 사진/동영상을 찍음". 사진을 찍는 관행 자체는 확인되지만, 목적이 "마케팅 콘텐츠"이지 manifest.yaml의 `site_photo` 필드 설계(현재 `read_by: [문서생성봇]`, 설명: "현장 완료 증빙 사진")가 전제하는 "문서 증빙용"과 다름. `법정요구사항_대조표_2026-07-07.md` 기준으로도 소독증명서(별지 제28호서식)에 사진 첨부 요건은 없어, 문서생성봇이 사진을 필요로 할 근거가 약함. 이 상태로 그대로 켜면 잘못된 용도(문서첨부)로 쓰이게 되므로, 켜기 전에 "마케팅 콘텐츠 관리"라는 별개 목적의 스테이지로 io.reads/writes를 재설계해야 함 — 지금 단계에서는 켜지 않는다.

**다음 액션**:
- [ ] 3건 모두 manifest.yaml `summary.optional_run_if_pending` 유지, `run_if: 미정_골든셋수집후결정` 그대로 유지 (이번 판정으로 "당장 킨다"는 결론 아님 — 불필요/보류 모두 off 유지가 결과)
- [ ] 견적금액산정봇: 향후 SKILL.md "알려진 한계"에 "고정표 자동산정 불가 — 사장님 현장판단 필수" 명시 검토
- [ ] 현장사진봇: 필요 시 별도 "마케팅콘텐츠봇"으로 목적 분리해 설계 검토(문서생성봇 io에서 site_photo 의존 제거 여부 재확인)
- [ ] 현장분리봇: 다현장 실사례가 추가로 누적되면(예 3건 이상) 재판정

## 12. F5 판정: 꽃집 manifest.yaml 방향 — 기존본 복구+구조수정으로 확정 (2026-07-16, Fable 5, 혜미 승인)

**배경**: `Fable_작업대기열.md` F5 카드(2026-07-16 혜미 승인). 문서 3건 충돌 — ① 감사_로드맵 R4(07-09) "14봇 분류표 기준 꽃집 자체 manifest.yaml 작성" ② `4. Archive/꽃집폴더_정부지원사본_2026-07/manifest.yaml`(07-13 작성 흔적, 14 stage, 단 stages가 `pipeline:` 아래 중첩) ③ 꽃집 HANDOFF.md(07-14) "꽃집은 4-factory manifest 패턴 아직 안 씀, 12봇_kind분류표.yaml이 스펙 겸함".

**이번 세션 실측 (판정 전 원문 재검증)**:
- 아카이브의 manifest는 정부지원 사본이 아니라 **꽃집 전용으로 새로 작성된 정본** — 파일 헤더에 "예전 gov-support 사본 manifest는 폐기, 종합기획(2026-07-08 Fable 확정) §1·§3 기준으로 신규 작성"이라고 명시돼 있음. io_contract / model_routing / quality_gate / rerun_gate / failure_log_format 등 분류표에 없는 플랫폼 계약 정보를 포함.
- 14 stage의 id/kind/순서가 `12봇_kind분류표.yaml`과 **100% 일치**(python 대조 결과 True). 내용 충돌은 없고, 문제는 `pipeline:` 중첩 구조 하나뿐(이 때문에 validate_manifest.py가 최상위 stages를 못 찾아 0건 검사 후 가짜 PASS).

**판정: 옵션 B — 아카이브의 꽃집 전용 manifest.yaml을 꽃집 루트로 복구하고, pipeline.stages 중첩만 최상위 구조로 수정한다.**
- A(신규 작성) 기각: 이미 존재하는, 분류표와 완전 일치하는 작업의 중복 생산.
- C(manifest 포기) 기각: 플랫폼 패턴 이탈 고착 + io_contract 등 계약 정보의 거처 상실.

**충돌 해석**: HANDOFF(07-14)의 "manifest 안 씀"은 의도적 번복이 아니라 **정보 결손**으로 판단 — 이 manifest는 07-13 R4 정리 때 정부지원 사본 무더기와 함께 잘못 아카이브됐고(R4 이동 지시가 "manifest.yaml" 파일명을 통째로 지목), 07-14 세션은 꽃집 루트에 manifest가 없는 상태만 보고 서술한 것. 따라서 "최신 문서 우선" 원칙의 적용 대상이 아님.

**역할 위계 확정**: manifest.yaml = 플랫폼 계약 정본("무엇을 하는가") / 12봇_kind분류표.yaml = 설계 근거·open_questions 동반 문서("왜 이렇게 정했나"). manifest 헤더의 동기화 규칙(한쪽 수정 시 둘 다 갱신) 유지. 둘이 충돌하면 골든셋·구현 코드가 이긴다(§7 원리 "골든셋이 설계를 이긴다" 적용).

**open question 2 답 — 소급 적용 아님**: "스킬당 manifest 정본 1 + 동반 근거문서" 원칙은 방역/정부지원/옛날옛적에에 이미 성립해 있음. 꽃집이 유일한 이탈이었고 이번 결정으로 복귀. 타 공장 추가 작업 없음.

**다음 액션 (실행은 Sonnet — T6 계속, Fable 불필요)**:
- [x] manifest.yaml을 `1. Projects/클로드 꽃집 ai/` 루트로 복구 (내용은 그대로, 구조만 수정해 새로 저장 — Archive 원본은 백업으로 그대로 둠, 삭제 안 함)
- [x] `pipeline:` 중첩 해제(stages/shared_context 최상위) 후 validate_manifest.py 재검증 — **14 stage 실검사 확인됨** (아래 §13 참고, 0건 검사 가짜 PASS 재발 안 함)
- [x] 꽃집 HANDOFF.md의 "manifest 패턴 안 씀" 문단(§개요)을 이 결정 반영해 갱신
- [x] ~~주의: ai공장짓기/scripts/가 현재 비어 있음~~ → **정정: 실제로는 비어있지 않았음. §13 참고.**

```json
{"why_fable": true, "reason": "evidence conflicts across sources — 꽃집 manifest.yaml 방향 3갈래 문서 충돌", "cheaper_model_attempted": true, "input_tokens_estimate": 2200, "raw_attached": false}
```

## 13. T6 완료 + 정정: `ai공장짓기/scripts/` 미유실 확인 (2026-07-16, Sonnet 세션)

**정정 (중요)**: §12 액션 항목과 `Fable_작업대기열.md` F5 카드 c2에 "ai공장짓기/scripts/ 폴더가 비어있다(v2 validate_manifest.py·verify_write.py 유실)"고 기록했었는데, 이건 사실이 아니었다. 원인은 데이터 유실이 아니라 **bash 마운트가 이 특정 하위폴더(`1. Projects/ai공장짓기/`)의 디렉토리 목록(readdir)을 일시적으로 빈 것처럼 보여준 캐시/동기화 결함**이었다 — `ls`/`glob`은 0건으로 보였지만, 파일 도구(Read, Windows 경로 기준)로 직접 열어보니 `validate_manifest.py`(205줄)와 `verify_write.py`(197줄) 둘 다 처음부터 온전히 존재했다. `git status`로도 확인: 이 폴더는 원래 볼트 루트에 있던 `ai공장짓기/`가 2026-07-13/14 사이 어느 세션에서 `1. Projects/ai공장짓기/`로 복사됐지만 `git mv`가 아니라 일반 복사였는지 git이 구경로는 전부 "삭제됨", 신경로는 "추적 안 됨(untracked)"으로 인식하고 있음(커밋 안 된 상태) — 이 자체가 별개의 정리 필요 항목(아래 참고)이지만, **scripts 폴더 내용물 자체는 처음부터 손실된 적 없다.**

**T6 완료 결과**:
- `manifest.yaml`을 Archive에서 꽃집 루트로 복구, `pipeline:` 중첩 해제 + `shared_context`(46개 필드, 기존 stage io 선언에서 기계적으로 도출 — 새 판단 없음) 신규 추가.
- 방금 복구 확인된 진짜 v2 `validate_manifest.py`로 실제 실행: **FAIL 0건 / WARN 4건**(전부 `manifest.schema.v2.yaml`이 다른 폴더에 있어 못 찾는다는 경로 경고, 내용 문제 아님). §12에서 우려한 "가짜 PASS"가 아니라 **14 stage/46 shared_context 필드를 전부 실제로 검사한 진짜 PASS**.
- HANDOFF.md 개요 문단 갱신(§ 위 참고).

**별도로 남는 정리 항목 (T6 범위 밖, 다음에 판단)**:
- git이 구 `ai공장짓기/`(루트) 전체를 "삭제됨", 신 `1. Projects/ai공장짓기/`를 "추적 안 됨"으로 보고 있어 커밋 이력이 끊겨 있음. `git add`/`git mv` 정리가 필요하지만 이건 저장소 조작이라 임의로 하지 않음 — 혜미 확인 후 별도 세션에서 처리 권장.
- 위와 같은 하위폴더 캐시 결함이 다른 폴더에서도 재현될 수 있음 — bash `ls`/`cat`이 "없음"으로 보고해도 곧바로 "유실"로 단정하지 말고 Read 도구(Windows 경로)로 먼저 재확인하는 습관 필요(이번 건도 그렇게 해서 정정함).

## 14. F1(T7) 판정: 정부지원 공고 수집 파이프라인 설계 — R5 질문 4개 확정 (2026-07-16, Fable 5, 혜미 승인)

**입력**: `Fable_작업대기열.md` F1 카드(c1~c4) + 근거 원문 대조(감사_로드맵 R5, 상태메모_2026-07-16, SKILL.md 알려진 한계, `scripts/real_announcements.json` 실제 스키마).

### Q1. 대상 사이트 목록 / 우선순위
**기업마당(bizinfo.go.kr) 단일 소스로 시작한다.** T3 실측에서 발견된 유효 공고 후보 전원이 bizinfo에 있었고(pblancId로 안정적 식별 가능), bizinfo 자체가 중앙부처+지자체 공고 집계 사이트라 1개 소스로 커버리지 대부분을 얻는다. 외부 의존 표면을 최소로 유지하는 것이 이 설계의 제1원칙(R5의 "유지비" 우려에 대한 직접 대응).
- **2순위(조건부)**: K-스타트업(k-startup.go.kr) — 운영 1개월 후 bizinfo에 없는 공고가 실제로 확인될 때만 추가. 미리 만들지 않는다.
- **제외**: 경남·진주시 지자체 개별 페이지 — T3 실측에서 발견분이 전부 스킬 유형 불일치(설비지원 등)였고, 페이지 구조 변경 빈도 대비 수확이 낮다. 2027년 1~2월 사이클 전 재평가.
- **구현 방식 [확인 필요→Sonnet 구현 시 1차 확인]**: 공공데이터포털에 기업마당 지원사업정보 open API가 있는지 먼저 확인하고, 있으면 **API 우선**(HTML 파싱보다 구조변경 리스크가 한 자릿수 낮음), 없을 때만 목록 페이지 스크래핑.

### Q2. 수집 주기 (triggers.schedule)
**일 1회, 매일 07:00.** 근거: T3에서 확인된 공고들의 접수기간이 전부 2주~7주 단위 — 시간 단위 신선도는 가치가 없다. 1~5월 성수기/하반기 비수기 구분 없이 연중 동일 주기로 단순하게 유지(주기 전환 로직 자체가 유지비). **체크섬 게이트 필수**: 목록 해시가 전일과 동일하면 수집만 하고 후속 추출 단계는 스킵(비수기 7~12월엔 거의 매일 스킵될 것 — 이게 정상).

### Q3. 실패 시 재시도 정책
실패를 두 종류로 구분한다 — 이 구분이 정책의 핵심:
- **일시 장애**(네트워크/타임아웃/5xx): 당일 3회 재시도(5분→15분→45분 백오프). 그래도 실패면 그날은 포기하고 다음날 정기 실행에 맡긴다. **3일 연속 실패 시에만 사람 알림.** 접수기간이 주 단위라 하루 이틀 공백은 실익 손실이 없고, 단발 장애 알림은 소음이다.
- **구조 변경 의심**(응답은 정상인데 파싱 결과 0건, 또는 필수 필드 결손율 급증): 재시도 무의미 — **즉시 사람 알림 1회**(재시도로 해결 안 되고 코드 수정이 필요한 상황이므로). 알림 채널은 기존 HANDOFF/일일 로그 체계에 맞춰 Sonnet 구현 시 결정.

### Q4. 수집물→매칭 스킬 io_contract
**자동 변환으로 real_announcements.json에 직접 쓰는 것을 금지한다.** eligibility/scoring_rubric/budget_criteria는 본문·HWP 첨부를 읽어야 나오는 필드라 추출 오류가 매칭 결과를 직접 오염시킨다(마감일 하나 틀리면 스킬 전체가 헛돈다). 3계층으로 분리:
1. **raw 계층** (수집기, 코드만): `scripts/inbox/announcements_raw_YYYY-MM-DD.json` — 기계적으로 확실한 필드만(title/agency/url/pblancId/announcement_date/deadline/첨부링크). 여기서 마감 경과분·기수집분(pblancId 중복) 필터링.
2. **candidate 계층** (Haiku/Sonnet 추출 — 모델정책상 Fable 투입 금지 구간): raw에서 살아남은 건만 real_announcements.json과 **동일 스키마**로 구조화 + 추가 메타필드 `source_url/collected_at/extraction_confidence/unresolved[]`(미해석 항목은 비워두고 표시, 추측 금지 — 상태메모의 "확인 안 된 걸 확인됐다고 적지 않는다" 원칙 승계).
3. **정본 계층**: **사람 검수 게이트는 candidate→real_announcements.json 병합 지점 단 한 곳.** 혜미가 candidate 카드를 승인해야 정본에 들어가고, 그 이후는 기존 매칭 파이프라인 그대로(스킬 수정 불필요 — 이게 이 설계의 최대 장점).

### 우선순위 판단 (질문에 없었지만 필요한 결정)
상태메모 실측대로 다음 공고 대사이클은 **2027년 1~2월**. 따라서 구현(Sonnet)은 급하지 않으며, **2026년 12월 말까지 가동**을 데드라인으로 잡으면 충분하다. 지금 서둘러 짓고 6개월간 빈 결과만 수집하는 것은 유지비 낭비 — 단, 설계는 오늘로 확정됐으니 구현 착수 시 이 §14만 보면 된다.

**다음 액션 (전부 Sonnet 이하, Fable 불필요)**:
- [ ] bizinfo open API 존재 여부 확인 → 수집기 MVP (raw 계층 + 체크섬 게이트)
- [ ] candidate 추출 프롬프트/스크립트 + 검수용 카드 출력 형식
- [ ] triggers.schedule 등록(매일 07:00) + 실패 알림 배선
- [ ] 시점: 2026-12 말 가동 목표, 그 전이면 언제든

```json
{"why_fable": true, "reason": "architecture_decision — 외부 사이트 의존 수집 파이프라인 설계(R5 지정), 혜미 승인 2026-07-16", "cheaper_model_attempted": false, "input_tokens_estimate": 6500, "raw_attached": true}
```

## 15. §14 설계 수정: 단일 창업공고 → 3사업(온천꽃식물원·대륙창업·모온) 상시 매칭 (2026-07-16, Fable 5, 혜미 지시)

**계기**: §14 직후 혜미가 요구사항을 정정 — 스크래핑 대상은 "모온 예비창업 공고 하나"가 아니라 **혜미네 3개 사업 전체에 적용·지원 가능한 공고를 AI가 상시 자동 수집**하는 것. 사업자등록 정보 2건(온천꽃식물원·대륙창업) + 모온 개업 계획(3개월 내) 제공받음.

**신설 파일**: `1. Projects/클로드 정부지원사업 ai/scripts/business_profiles.yaml` — 3사업 프로필 정본(사업자등록 정보 + 매칭 필드 + 사업별 수집 키워드). 수집기와 매칭 엔진이 공통 참조. yaml 검증 PASS(3 profiles).

| id | 사업 | 상태 | 매칭 성격 |
|---|---|---|---|
| oncheon_flower | 온천꽃식물원 (이문숙, 2015~, 창녕, 화훼·조경 도소매, 면세) | 운영중 11년차 | 소상공인·화훼·경영지원 — **창업 트랙 제외** |
| daeryuk | 대륙창업 (박수길, 2013~, 창녕, 소독·위생/행사/음향) | 운영중 12년차 | 소상공인·소독방역·행사·장비 — **창업 트랙 제외** |
| moon | mo,on (진주 예정, 산모 회복 서비스) | 창업준비중, ~2026-10 개업 예정 | 예비→초기창업 전환기 + 여성창업 |

**§14 판정 중 뒤집는 것 2건 (전제가 바뀌었으므로 — §14가 틀렸던 게 아니라 단일 프로필 전제였음)**:
1. **지자체 페이지 제외 → 2단계 포함으로 변경.** §14의 제외 근거(T3에서 진주시 설비지원 공고가 유형 불일치)는 모온 단일 전제에서만 성립. 그 "불일치" 공고(인테리어·간판·키오스크)가 **꽃집·대륙창업 같은 기존 소상공인에겐 정확히 맞는 유형**이다. → 1단계 bizinfo 가동 후, 2단계로 경남도·창녕군 공고 페이지 추가(진주시는 모온 개업·소재지 확정 후). 유지비 우려는 여전하므로 순서만 뒤로.
2. **구현 시점 2026-12 말 → 앞당김: Sonnet 구현 즉시 착수 가능, 2026-08 내 가동 목표.** §14의 "12월 말" 근거(창업 대사이클 1~2월)는 창업 공고에만 해당. 소상공인·기존기업 지원(경영환경개선·장비·고용 등)은 연중 수시 공고라 지금부터 수확이 있고, 모온 개업(~10월) 직후 초기창업 트랙 대응도 필요.

**§14 판정 중 유지하는 것**: bizinfo 1순위(소상공인 지원까지 집계하므로 오히려 더 유효)/일 1회 07:00+체크섬 게이트/재시도 정책/3계층 io_contract와 사람 검수 게이트 1곳 — 전부 그대로. io_contract에 필드 1개만 추가: candidate 카드에 `matched_profiles[]`(어느 사업에 해당하는지 태그, 키워드 1개 이상 매칭 시 승격, 최종 판단은 검수 게이트).

**모온 자격 전환 경고 (사람 판단 필요)**: 개업하는 순간 예비창업 트랙 자격 상실 → 초기창업(3년 이내) 트랙으로 전환. **개업일 확정 전에 "예비 자격으로만 지원 가능한 공고가 접수 중인지" 확인이 선행돼야 함** — 개업 시점이 지원 자격을 좌우하는 유일한 변수라, 다음 예비창업 사이클(2027년 1~2월 추정)까지 개업을 미룰 가치가 있는지는 혜미만 판단할 수 있는 사업 결정.

**프로필 결손 필드 (혜미 확인 필요, 추측 금지)**: 온천꽃식물원·대륙창업의 연매출/직원수/대표 생년월일/자격·인증(대륙창업 소독업 신고증 등)/결격 자기신고 — 매출·직원수 상한이 걸린 공고 판정에 필요. business_profiles.yaml에 `[확인 필요]`로 표시해둠.

**다음 액션 (Sonnet, Fable 불필요)**:
- [ ] 수집기 MVP: bizinfo(API 우선 확인) → raw → 3프로필 키워드 매칭 → candidate 카드(matched_profiles 태그) — **지금 착수 가능**
- [ ] run.py 매칭 엔진이 business_profiles.yaml의 복수 프로필을 받도록 입력 확장
- [ ] 2단계: 경남도·창녕군 공고 페이지 수집기 추가
- [ ] 혜미: 결손 필드 5종 확인 + 모온 개업일·예비 트랙 선행 확인

```json
{"why_fable": true, "reason": "architecture_decision 수정 — 요구사항 변경(단일→3사업 상시)으로 §14 판정 2건 번복 필요, 전제 충돌 해소", "cheaper_model_attempted": false, "input_tokens_estimate": 9000, "raw_attached": true}
```

## 16. 수집기 MVP + run.py 다중 프로필 — Sonnet 병렬 구현 완료, 설계 질문 4건 판정 (2026-07-16, Fable 5)

**구현 완료 (Sonnet 2세션 병렬)**:
- A(수집기): `scripts/collector/collect_bizinfo.py`(API 우선+페이지 폴백, 마감·중복 필터, 체크섬 게이트, 3회 백오프) + `promote_candidates.py`(3프로필 키워드 매칭→candidate, matched_profiles 태그) + fixture 테스트 raw 5건→candidate 3건(프로필별 1건씩, 마감 2건 제외) PASS. **bizinfo open API 실존 확인**(bizinfo.go.kr/apiDetail.do?id=bizinfoApi, crtfcKey 방식). 샌드박스 네트워크 차단으로 라이브 호출은 미검증 — FIELD_MAP은 추정치(TODO).
- B(매칭엔진): `run.py` v0.6.0 — `--profiles` 모드 신설(프로필별 결과 저장), 어댑터/예비·기창업 분기/excluded_types 반영. 기존 단일 입력 경로 **바이트 단위 회귀 동일** 확인. 예비창업패키지=적격·초기창업패키지=부적격(moon, 개업 전) 분기 유닛테스트 PASS.

**Sonnet이 올린 설계 질문 4건 — Fable 판정**:
1. **창업 트랙 판별 키워드가 두 곳에 중복 생성됨**(collector의 STARTUP_TRACK_MARKERS / run.py의 `_is_startup_track_announcement()`) → **business_profiles.yaml에 `startup_track_markers` 목록으로 단일 정본화하고 양쪽 코드가 이를 로드하도록 통일**(후속 Sonnet 작업). 같은 규칙이 두 곳에서 따로 진화하면 반드시 어긋난다.
2. **판별 규칙의 보수성 방향**: 자동 "제외"는 확실할 때만. 애매한 공고는 제외하지 말고 candidate에 남기고 `unresolved`에 "트랙 판별 불확실" 표시 — **거르는 건 사람 검수 게이트의 몫**(§14 게이트 1곳 원칙과 일치). 놓친 공고의 비용 > 오탐 후보 1건 검수 비용.
3. **업종코드 매핑 부재**: 표준산업분류 코드는 추측으로 채우지 않는다. 코드 확인 전까지 `industry_codes` 불일치는 **부적격이 아니라 needs_confirmation으로 처리**("모름≠미달" 원칙). 혜미가 홈택스/세무서에서 두 사업 업종코드 확인해 yaml에 채우면 정밀도 상승 — 필수는 아님.
4. **multi-profile 기본 target_period 180일**: 승인. 일 1회 수집 + raw 단계 마감 필터가 이미 있어 민감하지 않은 값.

**남은 사람 몫**: ①bizinfo API 키 발급(bizinfo.go.kr/apiDetail.do?id=bizinfoApi → `BIZINFO_API_KEY` 환경변수 또는 collector/config.yaml) ②키 발급 후 실응답 1건으로 FIELD_MAP 재검증(Sonnet) ③(선택) 업종코드 2건 확인.

**남은 Sonnet 몫**: 판정 1(키워드 정본화) 반영 + FIELD_MAP 실검증 + 스케줄 등록(매일 07:00)은 API 키 발급 후.

```json
{"why_fable": true, "reason": "cheaper models disagree/ambiguous — 병렬 Sonnet 2세션의 중복 구현 충돌(트랙 판별 규칙 2벌) 및 설계 질문 4건 tie-break", "cheaper_model_attempted": true, "input_tokens_estimate": 4000, "raw_attached": false}
```

**§16 후속 (같은 날, 3차 Sonnet 세션)**: 판정 1~3 코드 반영 완료 — `startup_track_markers` 10개를 business_profiles.yaml 최상위로 정본화(양쪽 코드 로드+하드코딩 폴백), certain/ambiguous/none 3단계 분류(구체 마커=certain, "창업" 단독=ambiguous→제외 안 하고 unresolved/needs_confirmation 기록, 수치 근거 max/min_years가 있으면 certain으로 격상), 자유서술 업종은 `industry_code_verified=False`로 needs_confirmation 처리. 회귀 전부 불변, 합성 케이스 3종 검증 PASS. Sonnet이 잠정 구현한 certain/ambiguous 이분법은 **Fable 승인** — "제외는 확실할 때만" 원칙의 올바른 최소 구현("창업케어" 실사례가 수치 근거로 certain 유지되는 것까지 확인됨). bash 마운트 캐시 결함이 이날 3개 세션 모두에서 재발(매번 Read로 실물 무결 확인, `mv f f.tmp && mv f.tmp f`로 캐시 무효화) — 재발 빈도가 높아져 상습 결함으로 격상, 새 세션은 bash의 파일 상태 보고를 신뢰하지 말 것.

## 17. 정부지원 공장 뒷단(선정 후: PPT·발표대본·예상Q&A) 설계 확정 (2026-07-16, Fable 5)

**배경**: §7 D2(2026-07-13)에서 "PPT류 트리거=선정 통보"로만 정해두고 설계 자체는 미착수였던 구간. 앞단 스크래핑(§14~16)과 중간구간(매칭~초안~8인심사위원, v0.5.x 구현 완료·90%)이 끝나 뒷단만 완전 공백이었음. 헌장 5절이 "정부지원 스킬에 발표자료 하위 공정이 실제로 추가될 때"를 헌장 재작성 트리거로 명시해둔 상태라, 이 설계는 헌장 적용 판단(승인 게이트 위치)을 반드시 포함해야 했음. 판단 전 원문 실측: 온천꽃식물원 생활문화 선정건에서 이 3종 산출물을 사람이 실제로 만들었던 실물(`gov-support-skill/2. 발표 대본.pdf`, `QnA.pdf`, `4. Archive/.../발표자료/최종.pptx`, 발표 심사기준표 이미지)이 존재함을 확인 — 산출물 스키마는 추측이 아니라 이 실물을 골든 레퍼런스로 따른다.

**판정 1 — 8 stage (local 2 / model 4 / human 2), 트리거는 event:selection_notice 단일**: 선정접수(local) → 발표요건추출(model low_cost) → PPT초안생성(model mid) → PPT승인(human) → 발표대본생성(model mid) ∥ 예상QNA생성(model high) → 발표패키지승인(human) → 발표패키지저장(local). 선정 통보는 외부에서 오는 예측 불가 이벤트라 schedule 트리거 없음, 진입 경로 단일이라 entry_points 불필요. 발표평가가 없는 공고(서류만으로 선정)를 위해 stage 3~8에 `run_if: 발표평가_또는_발표자료가_요구됨` — 단 요건이 [확인 필요]뿐이면 자동 스킵하지 말고 사람에게 확인(모름≠발표없음).

**판정 2 — 순차/병렬**: PPT→(대본·Q&A)는 순차. 대본은 슬라이드 순서·문구에 종속되므로 depends_on을 PPT초안생성이 아니라 **PPT승인**에 건다 — PPT가 잠기기 전에 대본을 쓰면 PPT 반려 1회가 대본 재작업까지 연쇄된다. 대본∥Q&A는 그래프상 병렬(둘 다 [PPT승인]만 선행, 서로 안 읽음 — Q&A는 슬라이드 문구가 아니라 제출확정본 내용+검수 약점 신호에 종속). 실행은 기존 원칙(스키마에 병렬 문법 없음, §5 bundle 순차 결정)대로 순차 나열, DAG 형태만 다이아몬드로 유지.

**판정 3 — 승인 게이트는 2개 (1개도 3개도 아님)**: ① PPT승인(PPT초안 뒤), ② 발표패키지승인(대본+Q&A 일괄, 문서별 approval 블록은 독립 — 부분 반려 가능). 기준은 "반려 시 재작업 전파 범위": 최종 1곳만 두면 PPT 오류가 대본·Q&A까지 만들어진 뒤 발견돼 3종 전부 재작업이므로 기반 문서(PPT)를 먼저 잠근다. 3곳으로 쪼개지 않는 이유는 대본·Q&A가 상호 독립이고 같은 사람이 같은 시점에 함께 보는 물건이라 게이트 분리의 전파 차단 효과가 없음. 방역 §7 원칙("상태는 문서가 갖고, 파이프라인엔 게이트 최소") 그대로 — approval 블록(status/version/approved_by/rejection_reason/version_history, 승인완료 시 locked)을 ppt_draft/presentation_script/expected_qna 3개 문서에 각각 적용, 반려는 rejection_target 매핑(대본문제→발표대본생성/질문답변문제→예상QNA생성/PPT문제→PPT초안생성+게이트① 재통과). **헌장 적용**: 이 뒷단엔 "발송" stage 자체가 없다 — 파이프라인은 저장까지만, 발표 현장 사용은 사람. 미승인 문서 실전 사용 차단은 DAG 순서+저장 stage의 승인상태 강제 재검증(방역 문자장부봇 이중 검증 패턴). **헌장 5절 재작성 트리거가 이 설계로 발동됨** — manifest 반영 시 헌장 개정안을 혜미에게 상신할 것.

**판정 4 — shared_context 신규 필드 7개**: selection_notice / submitted_application_ref / presentation_requirements / ppt_draft / presentation_script / expected_qna / presentation_package_record. 핵심 판단 2가지: ① 뒷단의 콘텐츠 원천은 draft_application(초안)이 아니라 **사람이 실제 제출한 확정본**(submitted_application_ref, 선정접수 때 사람이 지정) — 발표는 심사위원이 읽은 제출본과 일치해야 함. ② 예상QNA생성은 새 판정 로직을 만들지 않고 중간구간이 이미 계산한 약점 신호(judge_panel_review/deduction_map/psst_review/needs_confirmation/exaggeration_flags)를 질문 소재로 재사용, 앞단 정본 계층(real_announcements.json)의 scoring_rubric_note는 selection_notice의 공고 id로 조회 — 앞단·중간구간 기존 필드는 하나도 안 바꾼다.

**판정 5 — tier (기존 manifest의 low_cost/mid/high 어휘 유지, 모델명 하드코딩 금지)**: 발표요건추출=low_cost(추출·분류), PPT초안생성·발표대본생성=mid(창작이 아니라 제출확정본의 구조 변환), 예상QNA생성=high(심사위원 적대적 시뮬레이션 — 기존 "심사위원 모드 자기검수" high와 동급 난이도).

**아직 반영 안 된 것**: manifest.yaml/run.py 미반영(설계만 확정 — 이번 세션 지시사항). .pptx 실물 렌더링은 파이프라인 범위 밖(도구 하드코딩 안 함). 반려 재시도 최대 횟수는 방역과 동일 open question. 발표 "연습" 공정은 범위에서 의도적으로 제외(별도 판단 대상).

**산출물**: [[1. Projects/클로드 정부지원사업 ai/설계_뒷단자동화_PPT발표대본QNA|설계_뒷단자동화_PPT발표대본QNA]] (stage 표/게이트/필드/tier 상세).

**다음 액션 (전부 Sonnet, Fable 불필요)**:
- [ ] manifest.yaml에 8 stage + shared_context 7필드 반영 (기존 v1 스타일 파일에 삽입할지 별도 manifest로 둘지 파일 구조 확인 후 결정)
- [ ] run.py mock 확장: 방역 `_run_document_approval_cycle` 패턴 이식 + 저장 전 승인상태 강제검증
- [ ] 골든 레퍼런스(온천꽃집 발표대본/QnA/최종.pptx) 대조 테스트 1건 + 기존 회귀 12종 불변 확인
- [ ] 헌장 5절 개정안(발표 산출물 승인 규정) 혜미 상신

```json
{"why_fable": true, "reason": "architecture_decision — 미설계 구간(선정 후 뒷단) 신규 파이프라인 구조 + 승인 게이트 배치 + 헌장 적용 판단", "cheaper_model_attempted": false, "input_tokens_estimate": 12000, "raw_attached": false}
```

**§17 후속 (같은 날, Sonnet 구현)**: 다음 액션 4건 중 3건 완료 — ①`정부지원_manifest_v2.yaml`에 triggers+shared_context 7필드+8 stage 반영, `validate_manifest.py` FAIL 0/WARN 0(누락됐던 `needs_confirmation` shared_context 필드도 이번에 정식 등록, judge_self_review.writes에 추가) ②`scripts/run.py`에 `run_presentation_backend()` + stage_* 함수 8개 mock 구현(기존 함수 무변경) ③golden 레퍼런스(온천꽃식물원 발표대본.pdf/QnA.pdf) pdftotext 실측 대조 + 회귀 3종(sample_input/ideal/edge) 불변 확인. 테스트 5종(happy path/PPT+대본 반려 후 재승인/저장 안전장치/run_if 스킵/제출본 누락 중단) 전부 PASS. ④헌장 §5 개정 상신은 혜미 승인으로 완료(company_charter.md v0.1→0.2). **실측으로 새로 발견된 것**: QnA.pdf 실물이 "약점별 1문항"이 아니라 "5개 만능답변 템플릿+질문 매핑" 구조 — mock은 배선 증명 목적이라 그대로 두고 `정부지원_manifest_v2.yaml` open_issues에 실 LLM 연동 시 재설계 항목으로 기록. 상세: [[1. Projects/완전자동화_실행계획|완전자동화_실행계획]] T8.

## 18. end-to-end 재확인: 홍재우 9인 심사위원·포맷 미반영 + 수집기↔매칭 미연결 — 이 2건만 남았음 (2026-07-16, Fable 5, 혜미 지시)

**계기**: 혜미가 "스크래핑부터 지원, 합격 시 발표자료까지 쭉 이어지길" 반복 요청. 전체 재확인 결과 **발표자료 뒷단은 이미 §17/T8에서 완료돼 있었음**(stage_선정접수~stage_발표패키지저장 8개 함수, manifest v2, 테스트 5종 PASS, 헌장 §5 개정까지 완료) — 새로 설계할 필요 없음, 혼동해서 §17을 중복 작성할 뻔했다가 확인 후 취소.

**실제로 비어있는 연결 지점 2건**:
1. **수집기(§14~16, 오늘 신설) ↔ 매칭 파이프라인 stage 1이 아직 안 이어짐.** `정부지원_manifest_v2.yaml` stage 1("공고문 수집 및 핵심 기준 추출")은 여전히 `real_announcements.json` 정적 파일을 본다는 전제이고, 오늘 만든 `collector/collect_bizinfo.py`→`promote_candidates.py`의 산출물(`scripts/inbox/candidates_*.json`, 사람 검수 게이트 통과분)을 읽지 않는다. `run.py`의 `collect_and_extract_announcements()` 함수 시그니처(SKILL.md 유지보수 항목에 명시)만 지키면 교체 가능 — 이미 예정된 확장점.
2. **홍재우 9번째 심사위원 + 소제목:내용 포맷이 run.py에 미반영.** `홍재우_페르소나카드.md`/`작성_포맷_규칙.md` 둘 다 스스로 "아직 미반영"이라 기록해둔 상태 그대로.

**판정**:
1. **수집기 연결**: `collect_and_extract_announcements()`를 "최신 검수완료 candidates 파일이 있으면 그걸 우선, 없으면 기존 정적 파일로 폴백"하는 방식으로 교체. 사람 검수 게이트(§14)를 우회하지 않도록, 검수 미완료 candidate는 절대 이 함수가 읽지 않게 — 검수완료 표시는 candidate 카드에 `reviewed: true`/`reviewed_by`/`reviewed_at` 필드를 추가해 표시(신규, 사람이 검수 후 도구나 파일 편집으로 표시하는 최소 구현 — 검수 UI는 범위 밖).
2. **홍재우 반영**: `run_judge_panel()`에 9번째 심사위원 함수를 추가하고, 8인과 판정이 갈리면 페르소나카드 확정 규칙대로 홍재우가 이긴다. `deduction_map`/`lock_state` 결합 로직은 기존 것 그대로 두되 홍재우의 `부적격`/`보류` 판정이 나오면 8인 결과와 무관하게 `overall_pass_recommendation=false`로 강제.
3. **포맷 반영**: draft 생성 함수가 각 섹션 항목을 "○ 소제목(3~10자) : 내용(1~3문장, 수치·근거 포함)" 불릿으로 출력하도록 수정. 실제 텍스트를 베끼지 않고 구조(불릿 형식, 표 최소화, PSST 골격)만 이식 — 원 예시 파일은 참고용.
4. **발표 뒷단 실물화(§17에서 open issue로 남겨둔 것)**: PPT/대본/QNA 3개 model stage는 mock 그대로 두지 않고 이번에 실제로 연결한다 — PPT는 pptx 스킬로 실제 파일 생성(승인된 submitted_application_ref 내용만 사용, 신규 창작 금지), QNA는 §17에서 실측된 "5개 만능답변 템플릿+질문 매핑" 구조로 재설계.

**다음 액션 (Sonnet)**:
- [ ] `collect_and_extract_announcements()` 교체 + `reviewed` 필드 스펙 확정
- [ ] `run_judge_panel()`에 홍재우 심사위원 추가, lock_state 강제 로직
- [ ] draft 생성 포맷을 소제목:내용으로 전환
- [ ] PPT/대본/QNA mock → 실물 연결(pptx 스킬 + 만능답변 템플릿 구조)
- [ ] 회귀 3종(sample_input/ideal/edge) + multi-profile 테스트 + 발표뒷단 테스트 5종 불변 확인

```json
{"why_fable": true, "reason": "architecture_decision — 기완성 자산(§17 발표뒷단, 홍재우 페르소나) 재확인으로 중복 설계 방지, 실제 미연결 지점 특정 및 뒷단 실물화 판정", "cheaper_model_attempted": false, "input_tokens_estimate": 5000, "raw_attached": false}
```

## 19. 4건 판정: bizinfo 접근제약 근본원인, 볼트 전체 감사, 예산/기대효과 자동생성, 팀원 플레이스홀더 (2026-07-16, Fable 5, 혜미 지시)

**판정 1 — bizinfo 접근 문제는 "네트워크 차단"이 아니라 "API 키의 IP/URL 등록제"였음.** `mcp__workspace__web_fetch`로 직접 확인: `api.github.com`·`data.go.kr`는 정상 응답(대용량 HTML까지 받아옴) → 이 환경의 아웃바운드 자체는 열려있음. 반면 `bizinfo.go.kr/uss/rss/bizinfoApi.do`(정식 API 엔드포인트, URL 형식은 웹서치로 재확인해 맞음)는 매번 빈 응답 — bizinfo API 발급 화면 자체가 "IP주소 또는 시스템URL을 입력하여 발급"이라 명시하므로, **발급 시 등록한 IP/URL과 실제 호출 IP가 다르면 조용히 거부**하는 구조로 추정됨(Cowork 샌드박스의 아웃바운드 IP는 세션마다 바뀔 수 있어 애초에 고정 등록이 불가능). 즉 "제약없는 환경"의 정체는 네트워크 자유도가 아니라 **등록된 IP에서 도는 안정적인 실행 위치**. → **해결**: Claude 세션(이 환경이든 예약작업이든)이 아니라 **혜미의 PC에서 Windows 작업 스케줄러로 독립 실행되는 순수 파이썬 스크립트**를 돌린다. 사람이 발급받은 키를 등록한 그 위치(집/사무실 IP 또는 고정 URL)와 실행 위치가 일치해야 하므로, 이게 유일하게 안정적인 답. **코드 확인 결과 `scripts/collector/collect_bizinfo.py`가 이미 이 조건을 만족함**(`BIZINFO_API_KEY` 환경변수를 쓰면 PyYAML도 필요 없이 표준 urllib만으로 완결 — 새 스크립트를 만들려다 §18과 같은 "이미 있는 걸 다시 만들 뻔"할 위험을 발견해 취소함) — 신설 대신 **기존 스크립트 + Windows 작업 스케줄러 등록 배치파일/안내문서**만 만든다. 실행 결과(`scripts/inbox/`)는 볼트 폴더에 그대로 쓰이므로, 다음에 Claude 세션이 열리면 그 결과를 이어받아 candidate 승격·검수 게이트·매칭까지 처리(이 부분은 그대로 Claude 쪽 작업).

**판정 2 — 볼트 전체 기록/폴더규칙 문제는 Fable 감사 대상이 맞고, 지금(9월 예정 F4보다 앞당겨) 착수한다.** Explore 조사 결과 실제로 문제가 확인됨: "프로젝트 시작 위치 고정" 규칙(2026-07-16 신설)이 신설 당일부터 깨짐(`prompts/routing-policy.md`·`ops/usage.md`가 규칙 신설 이후에도 볼트 루트에서 계속 편집됨, `_inbox/`의 "삭제후보" 표시만 되고 미정리 폴더 2건), 방역·꽃집 스킬에 정부지원처럼 `기능_인덱스.md`가 없어 재발 위험이 정부지원보다 높음(특히 방역 — 산출물이 가장 방대), `완전자동화_실행계획.md`의 T-테이블이 T9~T11 본문은 있는데 표에 반영이 안 돼 있어 "표만 보면 다 안다"는 이 파일의 존재 이유 자체가 깨지는 중. 다만 decision-log 자체(§14~§18)는 스킬 문서와 모순 없이 정합적 — "기록을 안 남겨서"가 아니라 "남긴 기록을 표/인덱스로 압축하는 마지막 단계를 매번 빼먹어서" 생기는 문제로 특정됨. → **판정**: F4(신규공장 착수 전 재감사, 9월 예정)와는 별개로, **지금 즉시 3가지만 좁게 처리**(전체 재설계 아님 — 그건 여전히 9월 F4 몫): ①방역·꽃집에도 기능_인덱스.md 생성 ②`완전자동화_실행계획.md` T-테이블에 T9~T11 행 추가 ③볼트 루트에 남은 규칙 위반 파일(`prompts/`, `ops/`, `무제.canvas`) 이관 또는 정리. 다음 액션에 반영.

**판정 3 — 예산_계획·기대효과 섹션은 "정보 없음"이 아니라 "AI가 채워야 할 작업"으로 재정의.** 혜미 지적이 맞음: `budget_detail`/`expected_outcomes`가 business_profile에 없으면 무조건 `[확인 필요]`로 비워두던 기존 로직(v0.5.x)은 "모르는 걸 지어내지 않는다" 원칙을 예산·기대효과에까지 과도 적용한 설계 오류다. 실제 사업계획서 작성에서 예산 배분과 정량 기대효과는 **사업주가 아니라 공고 요건(budget_criteria, scoring_rubric)에 맞춰 작성자가 제안하는 것**이 표준 관행(종합본 3강: "계량목표 4가지는 실제 계획이 없어도 반드시 명시해야 붙는다", 4강: "준비가 안 돼 있어도 이미 다 준비된 것처럼 써야 한다"). → **판정**: `budget_detail`/`expected_outcomes`가 비어있을 때, 매칭된 공고의 `budget_criteria.max_grant_krw`(상한)와 `budget_criteria.excluded_categories`(집행 금지 항목 회피), `scoring_rubric`(배점 큰 항목에 더 배분)을 근거로 **AI가 표준 카테고리 비율로 예산 초안을 배분**(재료비/인건비/마케팅/기타 등, excluded_categories는 자동 제외)하고, 기대효과는 `annual_revenue_krw`(있으면) 대비 %성장 목표 + 신규고용 목표(팀 규모 대비)를 계량 수치로 제안한다. **단, 이건 "확정값"이 아니라 "AI 제안 초안"이므로 각 항목 앞에 `[AI 제안 — 실제 집행 전 사업주 확정 필요]`를 명시**해 SKILL.md의 "완성된 신청서를 최종본으로 취급하지 않는다" 원칙은 지킨다. `[확인 필요]`(정말 몰라서 못 채움)와 `[AI 제안]`(계산해서 채웠지만 확정 아님)을 텍스트로 구분해 사람이 한눈에 무엇을 검토해야 하는지 알게 한다.

**판정 4 — "대표자 정보" 필드는 버그가 아니라 블라인드 원칙(종합본 3강 "회사소개·연혁·상호 등은 넣지 않음")에 따른 의도된 설계 — 다만 라벨이 혼동을 유발해 이름 수정.** 코드 확인 결과 이 필드는 애초에 대표자 **이름**이 아니라 **연령**(ceo_birth_date로 계산)만 다룬다 — 이름은 io_contract 스키마에 아예 없다(블라인드 심사 원칙과 일치, business_profiles.yaml의 `ceo`는 사업자등록 정본 보관용이지 신청서 본문에 노출할 값이 아님). 혜미가 "기록이 안 됐다"고 느낀 건 실제로는 **생년월일**(청년/시니어 조건 판정용, 아직 미확인 상태로 그대로 남아있는 항목)이 비어서 뜬 `[확인 필요]`를 이름 누락으로 오인한 것 — 데이터 유실이 전혀 아님. → **판정**: 필드 라벨을 "대표자 정보"→"대표자 연령"으로 바꿔 혼동을 없애고, 코드 주석에 "이름은 의도적으로 미포함(블라인드 원칙)"을 명시.

**판정 5 — 팀원 플레이스홀더 자동 추가.** 혜미 지시(홍재우 의견 반영: "팀원이 더 있으면 유리한 경우") 그대로 채택. 매칭된 공고의 `scoring_rubric`에 참여인력/수행역량/실행계획류 항목이 있거나, 홍재우 판단기준 20 "증빙 문서 결정력"·종합본 4강 "대표자(팀) 경력·네트워크가 전혀 없으면 무조건 탈락" 조건에 해당하면, `team_experience`가 대표 1인뿐일 때 **역할이 명확한 플레이스홀더 팀원 1~2명을 "OOO"로 자동 추가**(예: "제작·운영 보조(OOO) — 상품 제작·포장, 고객 응대 보조" 식으로 사업 성격에 맞는 역할 텍스트까지 채움, 이름만 사람이 나중에 실명으로 교체). 무조건 추가하지 않고 **rubric에 팀 관련 배점이 실제로 있을 때만** 트리거 — 없는 공고에 억지로 팀을 부풀리지 않는다.

**다음 액션 (Sonnet)**:
- [x] (Fable 직접) 기존 `collect_bizinfo.py` 그대로 사용 확인, 작업 스케줄러 등록용 `.bat`+안내문서 작성 (판정1, 신규 스크립트 불필요로 확정)
- [ ] 방역·꽃집 `기능_인덱스.md` 생성, 실행계획 T-테이블에 T9~T11 추가, 볼트 루트 위반 파일 정리 (판정2, 좁은 범위만)
- [ ] `draft_application()`의 예산_계획/기대효과 섹션 자동생성 로직 (판정3)
- [ ] "대표자 정보"→"대표자 연령" 라벨 수정 + 주석 (판정4)
- [ ] 팀원 플레이스홀더 자동 추가 로직, rubric 조건부 트리거 (판정5)

```json
{"why_fable": true, "reason": "architecture_decision + blind-spot audit — 네트워크 근본원인 진단, 볼트 전체 감사 범위 판단, 예산/기대효과 생성원칙 재정의, 팀원 플레이스홀더 신규 정책", "cheaper_model_attempted": false, "input_tokens_estimate": 8000, "raw_attached": false}
```

**§18 후속 (같은 날, Sonnet 병렬 2세션)**: 다음 액션 5건 전부 반영, 같은 run.py를 동시 편집했지만 함수 영역이 겹치지 않아 충돌 없이 병합됨(양쪽 다 최종 py_compile+회귀로 확인).
- **홍재우 9인 반영**: `_run_hong_jaewoo_review()` 신규, 판단기준 20개 중 텍스트 스캔으로 근거 있게 판별 가능한 5개만 구현(#3 문제→해결→AI 순서/#5 차별화 실체 없음/#15 구체성/#16 완료형 서술/#19 경제성 최우선), 나머지 15개는 TODO(추측 구현 안 함). 8인과 무관하게 홍재우 부적격/보류 시 `overall_pass_recommendation` 강제 False — 8인 전원 통과(warning 0건)인데 홍재우 단독 부적격을 내는 합성 케이스로 강제 작동 확인. 판정어 매핑의 위반개수 임계값(0/1/2/3+)은 카드에 명시 안 된 이번 세션 추정치임을 코드 주석에 명시해둠 — 실 사례 쌓이면 조정 필요.
- **소제목:내용 포맷**: draft_application() 6개 섹션 전부 "○ 소제목 : 내용" 불릿으로 전환.
- **수집기↔매칭 연결**: `collect_and_extract_announcements()` — 경로 명시 호출은 기존 동작 유지(회귀 안정성), 기본 호출일 때만 `scripts/inbox/candidates_*.json` 최신분에서 `reviewed:true`만 조회, 없으면 정적 파일 폴백. candidate 카드에 `reviewed`/`reviewed_by`/`reviewed_at`(기본 false) 추가. 검수 게이트 우회 없음(reviewed:false 카드가 실제로 제외됨을 테스트로 확인) — §14 원칙 지켜짐.
- **PPT 실물화**: python-pptx로 실제 .pptx 생성 성공. submitted_application_ref를 PSST 앵커 정규식(실제 합격 사업계획서 pdftotext 실측 기준 표기)으로 절단해 배치, 신규 문장 창작 없음. 앵커 매칭 부족 시 `fallback_equal_split`로 정직하게 전환하고 `extraction_method`에 기록(숨기지 않음).
- **QnA 5템플릿**: QnA.pdf 재실측으로 카테고리 확정(①상품·차별성 ②기술·검증 ③시장·수요·판로 ④예산·지원금 ⑤실행·대표역량·모르는질문=catch-all). 새 판정 로직 만들지 않고 기존 8인 JUDGE_DEFINITIONS를 5개에 매핑(§17 판정4 원칙 지킴), 애매한 신호는 억지로 1~4에 끼우지 않고 ⑤로 보냄(§16 판정2와 일관).
- **발표뒷단 기존 테스트 5종 + 회귀 4종(sample/edge/ideal/multi-profile) 전부 PASS**(matched_programs/excluded_programs/lock_state 불변, 신규 필드 추가만 발생).
- **불변 확인 필요 항목(사람 판단 아님, 다음 세션 정리)**: `stage_발표대본생성`이 outline의 `slide` 키에 의존해 PPT 쪽에서 번호를 채워 넣는 임시 방편으로 연결됨(발표대본생성 자체는 무변경 원칙 지킴) — 다음에 대본 실물화할 때 이 연결부 재검토 필요. run.py 버전 헤더(v0.5.4)가 이번 변경들을 반영 못 하고 있어 다음 세션에서 v0.7.0으로 정리 권장.

**§19 후속 (2026-07-17, Sonnet 구현 + Fable 직접작업)**:
- **판정1(수동)**: 신규 스크립트를 만들려다 기존 `collect_bizinfo.py`가 이미 `BIZINFO_API_KEY` 환경변수 경로에서 PyYAML 없이 순수 표준 urllib만으로 완결됨을 확인해 **신설 취소**(§18과 같은 중복설계 함정을 재확인 직전에 피함). 대신 `scripts/collector/run_daily_collect.bat` + `작업스케줄러_등록방법.md` 작성 — 혜미 PC에서 Windows 작업 스케줄러로 매일 07:00 실행, `run_log.txt`에 exit code 기록.
- **판정2**: 방역·꽃집에 `기능_인덱스.md` 신설(정부지원과 동일 형식), 각 SKILL.md/HANDOFF.md에 "설계 전 인덱스 확인" 배너 추가. 실행계획 T-테이블에 T9~T11 행 추가(본문은 이미 있었음). 볼트 루트의 `prompts/`·`ops/`는 AI_OS_설계서 체계 소속 예외로 CLAUDE.md에 각주만 추가(이동 안 함 — 링크 파손 위험). `무제.canvas`(빈 파일, 2바이트) 삭제 확인.
- **판정3~5**: `_propose_budget_allocation()`/`_propose_expected_outcomes()`(예산상한·배점 기준 카테고리 배분, `[AI 제안]` 표시) + "대표자 정보"→"대표자 연령" 라벨(블라인드 원칙 주석) + `_propose_team_placeholders()`(rubric에 팀 관련 배점 있을 때만 "OOO" 플레이스홀더, 업종별 역할 문장 4패턴) 전부 구현. 회귀(sample/edge/ideal/multi-profile) 불변 확인. 블라인드 테스트(T11) 재실행 결과: 예산 5개 카테고리 `[AI 제안]`으로 채워짐, 기대효과 매출 +12%·신규고용 1명 `[AI 제안]`, 대표자 연령은 여전히 `[확인 필요]`(생년월일 진짜 미확인이라 정상), 팀 역량에 "제작·운영 보조(OOO)" 플레이스홀더 추가(이 공고 rubric에 수행역량 30점이 있어 정상 트리거).
- **부수 사고 처리**: Sonnet이 `git stash` 중 `.git/index.lock` 충돌로 git 인덱스가 일시 오염(작업트리 파일은 무손상 확인) → `git reset`으로 안전 복구, 커밋 없었으므로 이력 손실 없음. 이 사고가 아래 §20(다중계정 동시작업 규칙)의 직접 계기가 됨.

## 20. 다중계정 동시작업 안전 프로토콜 (2026-07-17, Fable 5, 혜미 지시)

**계기**: 혜미가 "여러 계정으로 hem폴더를 같이 작업해서 이상해지는 것 같다"고 지적 — 실제로 이번 세션 도중 `완전자동화_실행계획.md`의 T3 항목이 이 세션이 손대지 않은 채로 다른 세션에 의해 갱신되는 것이 실시간으로 관측됨(system reminder로 확인), §19 후속에서는 git index.lock 충돌까지 발생. 완전한 파일 잠금 시스템은 과설계이므로, 저비용 신호(계정 태그 + append-only + 작업선언 파일 + 최신본 재확인 + 잦은 커밋) 5개로 판정.

**판정**: 혜미가 제안한 "gombeck 작업" 아이디어를 채택하되 형식을 통일 — 계정 이메일의 `@` 앞부분을 대괄호 태그로 씀(`[gombeck1]`), 날짜·모델태그 옆에 병기(`(2026-07-17, [gombeck1] Fable 5, ...)`). 소급 적용은 안 함(생산성 낭비, 과거 기록은 이미 날짜만으로 충분히 식별 가능). 상세 규칙 5개(계정태그/append-only/작업선언파일/최신본재확인/잦은커밋)는 신설 문서에 분리 — CLAUDE.md 본문이 계속 길어지는 걸 막기 위해 포인터만 남김.

**산출물**: `0. Docs/동시작업_계정규칙.md`(규칙 5개 전문) + `1. Projects/ai공장짓기/현재작업현황.md`(작업선언 파일, 신규) + `CLAUDE.md` "Working with 혜미" 섹션에 포인터 1단락 추가.

**다음 액션**: 없음(전부 이번 세션에서 즉시 적용 완료). 다른 계정이 나타나면 각자 자기 이메일 앞부분을 태그로 쓰면 되므로 별도 등록 절차 불필요.

```json
{"why_fable": true, "reason": "architecture_decision — 다중 세션/계정 동시편집 충돌(실측: git index 오염, 문서 동시수정) 재발 방지 프로토콜 신규 설계", "cheaper_model_attempted": false, "input_tokens_estimate": 3000, "raw_attached": false}
```

**§20 Fable 5 승인 (2026-07-17, [gombeck1], 별도 Fable 5 서브에이전트 검수 — 혜미 지시로 재요청)**: c2(기능_인덱스 분산 패턴)·c3(동시작업 규칙 5개) 둘 다 **승인**. 근거: 분산 인덱스가 통합 인덱스보다 나음(4개 스킬이 독립 폴더이고 설계 사고는 항상 특정 스킬 안에서 나므로 확인 지점도 그 안에 있어야 함, 통합 인덱스는 오히려 모든 세션이 한 파일에 몰려 규칙2로도 못 막는 충돌점이 됨). 소규모 개선 2건 반영 지시받아 즉시 이행: ①규칙3(작업선언 파일)에 "24시간 경과 선언은 stale로 간주, 무시·삭제 가능" 완화 조항 추가(삭제 누락이 영구 블로킹 되지 않도록) — `0. Docs/동시작업_계정규칙.md`에 반영 완료. ②규칙5(잦은 커밋)는 `.git/index.lock` 미해결 이슈(CLAUDE.md 기록)로 실효성이 제한적이라는 점을 인지만 하고 별도 조치는 보류(선행과제로 남김). **최종 판정: 승인.** 검수 세션이 "§20이 파일에 없다"고 일시 오보고한 건 이 볼트의 상습 bash 마운트 캐시 결함(CLAUDE.md 기존 기록과 동일 패턴) — Read 도구로 재확인해 §20 실재 확인, 데이터 유실 아님.
## §21 기록체계 재설계 — 정본 지정·진입점 단일화·스크립트 검사 (2026-07-17, Fable 5) [k9cjhmw7z9]

**계기**: 혜미 지시("반복되는 버그들의 문제점을 재설계해서 확인해줘 — 기록이 여러 곳에 흩어져 많은 파일을 읽어야 하는 것도 문제, HANDOFF 작업마다 갱신 규칙도 안 지켜짐"). Sonnet 실태조사(같은 날)로 가설 실증: 맥락 파악에 파일 12~20개 필요, 진입점 3개 병존, HANDOFF 5~9일 stale(§18 재설계 사고의 직접 원인), 같은 사실 최대 6곳 중복, "HANDOFF 갱신" 규칙은 운영표 §3 한 곳에만 있고 강제 장치 없음.

**결정** (전문: `0. Docs/기록체계_재설계_2026-07-17.md`):
1. **정본 지정** — 사실 종류별로 갱신하는 파일을 1개로 고정(공장 상태=HANDOFF "현재 상태" 1화면, 기능=기능_인덱스, 결정=이 로그, 일상=세션로그, 큐=T-테이블). 그 외 파일엔 링크만. 기존 중복은 소급 삭제 안 함.
2. **진입점 단일화** — `0. 최우선_확인파일.md` 1개. 세션 필독 3개(진입점→최신 세션로그→해당 공장 HANDOFF+기능_인덱스)로 제한. START-HERE는 AI_OS 목차로 강등.
3. **규칙의 스크립트화** — `handoff_check.py` 신설(HANDOFF가 폴더 최근 작업일보다 2일+ 밀리면 WARN). "지켜라"가 아니라 "안 지키면 잔소리하는 장치"로 전환.
4. **append 전용 vs 덮어쓰기 문서 구분 명문화** — 동시작업 규칙 ②의 적용 범위를 명확히(세션로그·decision-log만 append 전용, HANDOFF 현재상태·기능_인덱스·T-테이블은 덮어쓰기 허용+저장 전 재읽기).
5. **TASK-PACKET/RESULT-CARD 보류 선언** — 실사용 0건(ops/tasks README만 존재), 필독 목록에서 제외. 삭제 아님.
6. **버그 3종 대응 확정** — truncation: heredoc+sentinel 유지(실증됨) / bash 캐시 오판: "Read 재확인 전 유실 단정 금지" 규칙 승격 / index.lock: git 작업 전 현재작업현황에 [git] 선언(한 번에 한 세션) + `sync_vault.sh` 도우미 신설. §20 승인 시 보류됐던 "규칙5(잦은 커밋) 실효성 제한" 선행과제에 대한 응답이기도 함.

**산출물**: `0. Docs/기록체계_재설계_2026-07-17.md`(설계 전문) + `scripts/handoff_check.py`·`scripts/sync_vault.sh`(Sonnet 구현) + 정부지원·ai공장짓기 HANDOFF "현재 상태" 섹션(Sonnet, 5~9일 공백 해소) + `0. 최우선_확인파일.md` 필독 3개 섹션.

**다음 액션**: 22:30 예약 작업에 handoff_check.py 포함(예약 작업 수정 필요 — 다음 세션).

```json
{"why_fable": true, "reason": "architecture_decision — 기록체계 전면 재설계(정본 지정, 진입점 단일화, 규칙의 스크립트화). 실태조사는 Sonnet 위임, 설계 판단만 Fable", "cheaper_model_attempted": true, "input_tokens_estimate": 9000, "raw_attached": false}
```

<!-- ok -->
