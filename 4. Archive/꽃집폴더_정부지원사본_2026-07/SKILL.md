# 정부지원사업 매칭 스킬 (gov-support-matching-skill)

## 언제 이 스킬을 쓰는가 (트리거 조건)
- "정부지원사업/지자체 공고 중에 우리 사업에 맞는 거 찾아줘" 같은 요청이 왔을 때
- 사업자 정보(업종, 설립일, 매출, 인력 등)와 조회기간을 주고 "지금 지원 가능한 사업이 뭐가 있는지" 물었을 때
- 이미 특정 공고를 지목하며 "이 공고에 우리가 지원 자격이 되는지, 신청서 초안까지 만들어줘"라고 요청했을 때
- 매칭된 지원사업에 대해 신청서 초안(사업개요/신청동기/사업화계획/예산/기대효과)이 필요할 때
- 작성된 초안을 제출 전에 "심사위원 입장에서 감점 요인이 있는지" 비판적으로 점검받고 싶을 때

## 언제 쓰면 안 되는가
- 법적 자격 유무를 최종 확정해야 하는 상황 (예: 세금 체납 여부, 중복수혜 여부 등 공적 자료로만 확인 가능한 결격사유의 "최종 판정") — 이 스킬은 자기신고 데이터 기반으로 위험만 표시하며, 실제 확인은 사람(세무사/담당기관)이 해야 함
- 실시간으로 공고 원문을 크롤링/수집해야 하는 상황 — 현재 스킬은 `scripts/sample_announcements.json` 목업 데이터 구조를 기준으로 매칭 로직만 검증된 상태이며, 실제 공고 수집기(기업마당·K-스타트업·지자체 API/크롤러)가 별도로 연동되어야 함
- 완성된 신청서를 그대로 제출해도 되는 "최종본"으로 취급하는 것 — draft_application은 뼈대와 [확인 필요] 표시가 포함된 초안이며, 실제 제출 전 사람의 내용 보완과 최종 검토가 반드시 필요함
- 지원사업 심사 결과(합격/불합격)를 예측하거나 보장하는 용도 — judge_review는 "형식/자격 요건 관점의 감점 위험"만 점검하며 실제 심사위원의 정성 평가를 대체하지 않음

## 이 스킬이 하는 일 (한 문단 요약)
사업자 정보(business_profile: 기업형태, 업종, 설립일, 소재지, 매출, 인력, 대표자 정보, 인증, 자기신고 결격사유)와 조회기간(target_period)을 입력받아, 수집된 공고문에서 신청자격·지원제외조건·제출서류·페이지제한·예산기준·심사배점을 추출하고(1단계), 사업자 정보와 대조해 자격 충족 여부와 결격 위험을 점검한 뒤(2단계), 마감이 지났거나 필수서류 목록이 확인되지 않은 공고는 자동 제외하고 나머지를 신뢰도 점수(eligibility_confidence)순으로 매칭하며(3단계), 가장 적합한 공고 1건에 대해 신청서 초안을 섹션별로 작성한다(4단계). 마지막으로 "심사위원 모드"가 그 초안을 스스로 비판적으로 재검토해 감점 위험·과장 표현·증빙 부족 주장을 우선적으로 찾아낸다(5단계). 최종 판정(`lock_state`)은 숫자 기준(overall_confidence >= confidence_threshold 0.85)과 질적 기준(judge_review.overall_pass_recommendation)을 **둘 다** 만족해야만 `READY_FOR_APPROVAL`이 되며, 하나라도 미달이면 `DRAFT`로 유지되고 human_review로 라우팅된다. 최종 출력은 matched_programs, excluded_programs(제외 사유 포함), draft_application, judge_review, quality_gate_result(둘 다 만족 여부와 구체적 미통과 사유), lock_state, 그리고 사람이 반드시 확인해야 할 needs_confirmation 목록이다.

## 실행 방법
1. `manifest.yaml`의 `invocation.entrypoint`(`scripts/run.py`)를 실행
   - `python3 scripts/run.py <input.json>` (input.json 생략 시 `test/sample_input.json` 사용)
2. 입력은 `io_contract.input_schema`를 따를 것 (`business_profile`, `target_period` 필수)
3. 공고 데이터 소스는 기본적으로 `scripts/sample_announcements.json`(목업)을 사용 — 실제 운영 시 `collect_and_extract_announcements()` 함수를 실공고 API/크롤러 호출로 교체 필요
4. 실패 시 `quality_gate.on_fail` 정책에 따라 1회 재시도 후 `human_review`로 에스컬레이션 (실행 결과의 `lock_state`, `quality_gate_result.routed_to` 확인)
5. `lock_state`는 `quality_gate_result.confidence_passed`와 `quality_gate_result.judge_pass_recommendation`이 **모두 true**일 때만 `READY_FOR_APPROVAL`이 됨 — 숫자 기준만 통과해도 심사위원 모드가 감점 위험을 발견하면 `DRAFT`로 유지됨
6. 모든 실패/미달 이벤트는 `test/failure_log.jsonl`에 `failure_log_format` 필드로 기록됨

## 알려진 한계
- **실시간 공고 수집 미구현**: 현재는 목업 JSON(`scripts/sample_announcements.json`)으로 매칭 로직만 검증됨. 실제 서비스에서는 기업마당(bizinfo.go.kr), K-스타트업, 각 부처·지자체 공고 페이지를 수집하는 별도 모듈이 필요하며, 이 부분이 없으면 스킬 전체가 "가정값" 기반으로만 동작함.
- **결격사유 자동 검증 불가**: 세금 체납, 중복 정부지원 수혜 이력, 휴폐업 여부 등은 사업자의 자기신고(`disqualification_flags`) 데이터로만 대조하며, 국세청·행정정보 공동이용 등 공적 자료로 실시간 검증하지 않는다. `needs_confirmation`에 표시되지만 사람의 확인이 필수다.
- **신청서 초안의 내용 완성도는 검증하지 않음**: `judge_review`는 페이지 제한, 심사배점 항목 커버 여부, 필수서류 준비 상태, `[확인 필요]` 잔여 여부 등 "구조적/형식적" 위험만 점검한다. 기술적 타당성, 사업 아이디어의 경쟁력, 문장의 설득력 같은 "내용의 질"은 판단하지 않으므로 사람의 검토가 항상 필요하다.
- **숫자 기준 통과만으로는 절대 자동 승인되지 않음(설계상 의도)**: quality_gate(overall_confidence)와 judge_review(overall_pass_recommendation)는 서로 다른 것을 측정한다 — 전자는 "자격이 되는가", 후자는 "이 초안 그대로 내도 되는가"다. `lock_state`는 이 둘의 AND 결합이라 confidence가 threshold를 넘어도 judge_review가 감점 위험을 찾으면 `DRAFT`로 남는다. 실제 샘플 테스트에서도 confidence는 정확히 0.85(임계값 통과)였지만 draft에 `[확인 필요]` 섹션 5개, 미준비 서류 5건, 미대응 심사배점 3건이 남아 있어 `lock_state=DRAFT`, `routed_to=human_review`로 처리됐다. 즉 첫 실행에서 `READY_FOR_APPROVAL`이 나오는 경우는 거의 없으며, 이는 버그가 아니라 "초안은 항상 사람이 완성해야 한다"는 원칙을 강제하기 위한 설계다.
- **심사배점 키워드 매칭이 단순함**: judge_mode_self_review의 "심사배점 항목이 초안에서 다뤄지는지" 체크는 항목명의 첫 단어 포함 여부로만 판단하는 단순 휴리스틱이라 오탐/누락 가능성이 있다. 실제 심사표 대조는 사람이 재확인해야 한다.
- **과장 표현 탐지가 사전 매칭 방식**: 정해진 단어 목록(`EXAGGERATION_WORDS`)에 있는 표현만 탐지하며, 문맥적 과장(근거 없는 수치 등)은 부분적으로만 잡아낸다.
- **다국어/도메인 확장 미검증**: 현재 스키마와 샘플은 한국 중소기업 지원사업(중기부 계열)을 기준으로 설계되었다. 지자체별 특수 조건, 문화/관광/농림 등 타 부처 사업 스키마는 필드가 다를 수 있어 확장 시 `eligibility` 스키마 보완이 필요하다.

## 실행 결과 (테스트 완료)
- `test/sample_input.json` (정상 케이스: 매출·인력 데이터 있음) → `test/sample_output.json`
  - 매칭 1건(디딤돌창업과제, eligibility_confidence 1.0), 제외 2건(마감경과 1건 + 필수서류 미확인 1건)
  - quality_gate(숫자 기준): overall_confidence 0.85 = confidence_threshold(0.85) → **통과**
  - 심사위원 모드(질적 기준): overall_pass_recommendation = **false** — `[확인 필요]` 섹션 5개(신청동기/사업화계획/팀역량/예산계획/기대효과), 필수서류 미준비 5건, 심사배점 3개 항목(기술성/시장성/고용창출) 초안에서 미대응
  - → `lock_state = DRAFT`, `routed_to = human_review` (숫자 기준은 통과했지만 질적 기준 미달이라 자동승인되지 않음)
- `test/sample_input_edge.json` (엣지 케이스: 매출·인력 데이터 없음) → `test/sample_output_edge.json`
  - 동일 공고 매칭되나 eligibility_confidence 0.83으로 하락, judge_review 감점위험 5건 발견 → overall_confidence 0.68로 숫자 기준도 미달
  - → `lock_state = DRAFT`, `routed_to = human_review`, `test/failure_log.jsonl`에 두 실패 사유(confidence_passed, judge_pass_recommendation) 모두 기록됨

## 유지보수
- 실패 로그는 `failure_log_format`에 정의된 필드로 남음 — 이걸 보고 Sonnet/Codex가 디버깅
- 이 스킬을 고칠 때는 `manifest.yaml`의 `io_contract`는 되도록 건드리지 말 것 (다른 시스템이 이 계약에 의존할 수 있음)
- 실제 공고 수집기를 연동할 때는 `scripts/run.py`의 `collect_and_extract_announcements()` 함수 시그니처(반환값: `(announcements: list, needs_confirmation: list)`)만 유지하면 나머지 파이프라인은 그대로 재사용 가능

## 관련 문서

- [[1. Projects/클로드 꽃집 ai/HANDOFF|HANDOFF]]
- [[1. Projects/클로드 꽃집 ai/최종점검_리포트_2026-07-07|최종점검_리포트_2026-07-07]]
- [[1. Projects/클로드 꽃집 ai/리스크_메모_통화녹음_제3자동의|리스크_메모_통화녹음_제3자동의]]
- [[ai공장짓기/설계노트/3_②_꽃집_스킬|3_②_꽃집_스킬]]
- [[클로드 ai 자동화/company_charter|company_charter]]
- [[ai공장짓기/runner/README|README]]

<!-- ok -->
