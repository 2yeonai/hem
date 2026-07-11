# 정부지원사업 스킬 manifest v1 → v2 마이그레이션 diff 리포트 (작업 B)
- 날짜: 2026-07-07
- 산출물: `정부지원_manifest_v2.yaml` (같은 폴더)

## 핵심 결론
**run.py 동작은 전혀 바뀌지 않았고, 바뀔 수도 없다.** run.py는 manifest.yaml을 파싱해서 실행하는 러너가 아니라, 로직이 함수 단위로 하드코딩돼 있고 manifest.yaml은 "이 값과 동일해야 함" 주석으로만 연결된 문서다(예: `run.py` 69행 `CONFIDENCE_THRESHOLD = 0.85  # manifest.yaml quality_gate.confidence_threshold와 동일해야 함`). 코드 안에 `model_routing`이나 `manifest` 파싱 호출은 없음(grep으로 확인).

따라서 이번 마이그레이션의 "성공 기준"은 애초에 "회귀 테스트가 이전과 동일한 결과를 낸다"가 아니라 — **run.py 파일을 건드리지 않았으니 당연히 동일하다** — 는 것을 재확인하는 수준이다. 진짜 검증 가치는 v2 스키마가 v1의 개념을 손실 없이 표현할 수 있는지에 있다.

## 회귀 테스트 결과 (마이그레이션 전/후 동일 — 예상대로)
| 케이스 | lock_state | confidence |
|---|---|---|
| `test/my_business_profile_input.json` (실제 mo,on 데이터) | DRAFT | 0.35 |
| `test/real_program_input_simulated.json` (실제 PDF 공고, 시뮬레이션 날짜) | DRAFT | 0.35 |
| `test/sample_input_ideal.json` (목업, 이상적 케이스) | READY_FOR_APPROVAL | 1.0 |

**참고 — 프로젝트 현황 메시지의 사실관계 정정**: "실제 사업자 데이터(mo,on)로 검증 완료, READY_FOR_APPROVAL 도달 확인"이라고 알고 계셨는데, 실제로 실행해보면 실제 사업자 데이터(mo,on) 케이스는 항상 DRAFT(confidence 0.35)에 머무릅니다. READY_FOR_APPROVAL은 `sample_input_ideal.json`(사람이 손으로 만든 이상적 목업 입력)에서만 도달했고, 이는 HANDOFF.md 회귀테스트 섹션에도 그렇게 기록돼 있습니다. 실제 데이터가 DRAFT인 이유는 버그가 아니라 정상 동작입니다 — mo,on 케이스는 목업 공고 기준으로는 자격/서류 요건이 완전히 충족되지 않아서, real_program 케이스는 예산초과·성별/경력단절 확인필요 리스크가 있어서 그렇습니다(HANDOFF.md 참고).

## 필드 매핑표 (v1 → v2)
| v1 위치 | v2 위치 | 비고 |
|---|---|---|
| `model_routing.stages[0]` (공고문 수집, tier: low_cost) | `stages.collect_announcements` (kind: model, tier: haiku) | |
| `model_routing.stages[1]` (자격/결격 점검, tier: mid) | `stages.eligibility_screen` (kind: model, tier: sonnet) | |
| `model_routing.stages[2]` (자격요건 매칭, tier: mid) | `stages.program_matching` (kind: model, tier: sonnet) | |
| `model_routing.stages[3]` (신청서 초안, tier: mid) | `stages.draft_application_stage` (kind: model, tier: sonnet) | |
| `model_routing.stages[4]` (심사위원 자기검수, tier: high) | `stages.judge_self_review` (kind: model, tier: opus) + `check` | v2에서 유일하게 check/on_fail이 붙는 stage |
| `io_contract.input_schema.business_profile` | `shared_context.business_profile` | written_by: [] (외부 주입) |
| `io_contract.input_schema.target_period` | `shared_context.target_period` | written_by: [] (외부 주입) |
| (암묵적, `collect_and_extract_announcements()` 결과) | `shared_context.raw_announcements` | v1엔 명시적 공유객체 필드 없었음 — v2 신규 |
| (암묵적, `check_eligibility_and_disqualification()` 결과) | `shared_context.eligibility_check_result` | v2 신규 |
| `output_schema.matched_programs` / `excluded_programs` | `shared_context.matched_programs` / `excluded_programs` | |
| `output_schema.draft_application` | `shared_context.draft_application` | |
| `output_schema.judge_review` | `shared_context.judge_review` | |
| `output_schema.quality_gate_result` | `shared_context.quality_gate_result` + `judge_self_review.check` 매핑 | 아래 "표현 안 되는 부분" 참고 |
| `quality_gate.on_fail.retry_count: 1` / `escalation_target: human_review` | `judge_self_review.on_fail.action: route_to_human` | retry_count는 v2 stage-level `exec_params.retry_count`로 옮길 자리가 있으나, v1은 이 retry가 judge_self_review 하나에만 걸려있던 게 아니라 파이프라인 전체에 걸린 정책이라 1:1 대응이 애매함 — 아래 기록 |

## kind 분류 근거
5단계 전부 `kind: model`로 분류했다. 근거: v1 manifest가 이미 5단계 모두에 tier(low_cost/mid/high)를 부여해뒀다는 것 자체가 "판단이 필요한 단계"라는 선언이라고 봤다. 실제 `run.py` 구현은 결정론적 Python 규칙(LLM API 호출 없음, `grep`으로 확인됨)이지만, 이건 "지금은 결정론적 코드로 시뮬레이션된 model stage"로 해석하는 게 맞다고 판단했다 — 정부지원사업 스킬은 원래 AI 에이전트(Claude 등)가 공고문을 읽고 판단하는 걸 상정한 스킬이고, 지금 코드는 그 판단을 규칙 기반으로 근사한 것이기 때문이다. kind: local 후보였던 "PDF/HWP 원문 파싱"은 애초에 구현이 안 돼 있어서(HANDOFF 보류 항목) v2에 stage로 넣지 않았다.

## v1 → v2에서 표현이 안 되거나 임의로 결정하지 않은 것 (막히면 보고 — 이 3가지)
1. **human stage 없음.** v2는 "human stage에서 반려 시 지정 stage로 복귀"를 전제하는데, v1은 quality_gate 미달 시 `routed_to=human_review`로 파이프라인이 **종료**되는 구조다. 사람이 본 뒤 재실행하는 것은 "run.py를 다시 호출하는 외부 프로세스"일 뿐, pipeline 내부에 있는 재개 가능한 stage가 아니다. `judge_self_review.on_fail.human_reject.return_to`를 임의로 아무 stage나 채워 넣지 않고 `null`로 남겨뒀다.
2. **kind=local 전처리 stage 없음.** PDF/HWP → `raw_announcements` 자동 추출은 설계상 있어야 자연스럽지만 실제로 구현된 적이 없다(HANDOFF.md에 의도적 보류로 명시). 없는 코드를 매니페스트에만 그려 넣지 않았다.
3. **tier 어휘 변환이 검증된 매핑이 아니다.** low_cost→haiku, mid→sonnet, high→opus로 옮겼지만, 이게 실제로 맞는 대응인지는 확인되지 않았다(ASSUMPTION). 특히 mid 단계 3개(자격점검/매칭/초안작성)를 전부 sonnet으로 뭉뚱그린 게 맞는지는 재검토가 필요하다.

이 3가지는 스키마나 코드 어느 한쪽을 임의로 늘려서 억지로 봉합하지 않고 그대로 열어뒀습니다. 확인해서 알려주시면 반영하겠습니다.

## 관련 문서

- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log_skill-factory-architecture]]
- [[클로드 정부지원사업 ai/HANDOFF|HANDOFF (정부지원사업)]]
- [[클로드 정부지원사업 ai/SKILL|SKILL]]
- [[ai공장짓기/설계노트/2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)|2_①_정부지원사업_스킬_(실구현_완료,_오늘_반영할_것만)]]
- [[ai공장짓기/MASTER_SETUP|MASTER_SETUP]]
