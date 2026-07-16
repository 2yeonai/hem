---
type: doc
status: draft
tags: [ai공장, 정부지원]
---

# 설계: 정부지원 공장 뒷단 자동화 — 선정 후 PPT·발표대본·예상Q&A (2026-07-16, Fable 5)

> **이 문서는 설계 문서다 — 코드/manifest 반영은 하지 않았다.** 실제 manifest.yaml 반영과 run.py mock 구현은 이후 Sonnet 세션 몫.
> 판단 근거와 결정 요약은 [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]] §17에 기록됨. 트리거 원결정은 §7(2026-07-13 배치결정) D2: "PPT류 트리거=선정 통보".

## 1. 범위와 전제

- **범위**: 매칭~초안~자기검수(v0.5.x, 구현 완료)와 공고 스크래핑 앞단(§14~16, 설계+MVP 구현 완료) **이후**, "공고에 선정됐다"는 통보를 받은 시점부터 발표 준비 산출물 3종(PPT·발표대본·예상Q&A)을 만들어 승인·보관하는 구간.
- **실제 선례 존재**: 온천꽃식물원 "생활문화 혁신지원" 선정건에서 이 3종을 사람이 수작업으로 만들었음 — `gov-support-skill/2. 발표 대본.pdf`, `gov-support-skill/QnA.pdf`, `4. Archive/.../발표자료/최종.pptx`, 발표 심사기준표 이미지. **이 실물들이 산출물 형태의 골든 레퍼런스다** — 산출물 스키마를 추측으로 정하지 않고 이 실물 구조를 따른다.
- **입력 전제 (중요)**: 뒷단의 콘텐츠 원천은 중간구간의 `draft_application`(초안)이 아니라 **사람이 실제로 제출한 확정본**이다. 초안과 제출본은 다를 수 있고(혜미가 제출 전 수정), 발표는 심사위원이 이미 읽은 제출본과 일치해야 한다. 따라서 선정 접수 시 제출확정본 참조를 사람이 지정한다(아래 `submitted_application_ref`).

## 2. 트리거

```yaml
triggers:
  - type: event
    source: selection_notice        # 선정 통보 — 외부(관공서)에서 오므로 감지 자동화 대상 아님. 혜미가 통보를 받아 직접 시작시킨다.
    entry_stage: 선정접수
```

- schedule 트리거 없음(선정은 날짜 예측 불가한 외부 이벤트). entry_points 불필요(진입 경로 단일).

## 3. Stage 설계 (8 stage: local 2 / model 4 / human 2)

| # | stage id | kind | tier | depends_on | run_if | writes | 왜 이 kind/tier인가 |
|---|---|---|---|---|---|---|---|
| 1 | 선정접수 | local | – | [] | – | selection_notice, submitted_application_ref | 선정 통보 내용(발표일시·방식)과 제출확정본 경로를 구조화해 받는 접수 — AI 판단 없음 |
| 2 | 발표요건추출 | model | low_cost | [선정접수] | – | presentation_requirements | 통보문+정본 공고에서 발표시간/슬라이드 제한/발표평가 배점표를 추출. 분류·추출 수준. 원문에 없는 값은 `[확인 필요]`로 비워둠(추측 금지 원칙 승계) |
| 3 | PPT초안생성 | model | mid | [발표요건추출] | 발표평가_또는_발표자료가_요구됨 | ppt_draft (approval 블록 포함) | 제출확정본+발표 배점표 → 슬라이드 아웃라인+슬라이드별 내용. 구조화 생성 작업 — mid로 충분 |
| 4 | PPT승인 | human | – | [PPT초안생성] | 〃 | ppt_draft.approval | **승인 게이트 ①.** 헌장 3절 "발표자료 확정"은 명시적 승인 필요 항목 |
| 5 | 발표대본생성 | model | mid | [PPT승인] | 〃 | presentation_script (approval 블록 포함) | 승인완료·locked된 PPT의 슬라이드 순서·내용 기준으로 발표시간에 맞춘 대본 작성 |
| 6 | 예상QNA생성 | model | high | [PPT승인] | 〃 | expected_qna (approval 블록 포함) | 8인 가상 심사위원·감점전파·`[확인 필요]` 목록을 입력으로 약점 기반 예상 질문+답변 생성. 적대적 심사위원 시뮬레이션 — 기존 파이프라인에서도 "심사위원 모드 자기검수"가 high였던 것과 동급 |
| 7 | 발표패키지승인 | human | – | [발표대본생성, 예상QNA생성] | 〃 | presentation_script.approval, expected_qna.approval | **승인 게이트 ②.** 대본+Q&A를 한 게이트에서 일괄 승인(문서별 approval 상태는 독립) |
| 8 | 발표패키지저장 | local | – | [발표패키지승인] | 〃 | presentation_package_record | 승인완료본을 보관 경로에 기록. **저장 직전 3종 문서 전부 `approval.status=승인완료`인지 재검증, 아니면 강제 중단** — 방역 문자장부봇의 이중 검증 패턴 그대로 |

합계: **local 2 / model 4 / human 2 = 8 stage.**

### run_if: 발표평가_또는_발표자료가_요구됨
서류만으로 최종 선정되는 공고(발표평가 없음)면 stage 3~8 전체가 스킵된다. 발표요건추출(stage 2)까지는 항상 실행해 "발표가 있는지 없는지"부터 확인한다. v2 스키마 관례대로 run_if는 단순 조건 식별자 문자열이며, 스킵 시 해당 stage의 writes 필드는 빈 채로 남는다.

## 4. 순차 vs 병렬 판단

- **PPT → (대본, Q&A)는 순차.** 대본은 슬라이드 순서·문구에 정확히 종속된다. PPT가 승인·잠금되기 전에 대본을 쓰면, PPT 반려 1회가 대본 재작업까지 연쇄시킨다(반려 전파 비용 배가). 그래서 대본·Q&A의 depends_on은 PPT초안생성이 아니라 **PPT승인**이다.
- **대본 ∥ Q&A는 의존 그래프상 병렬.** 둘 다 [PPT승인]만 선행 조건이고 서로의 산출물을 읽지 않는다(Q&A는 슬라이드 세부 문구가 아니라 제출확정본의 내용+검수 약점 신호에 종속). 단 **실행은 기존 원칙대로 순차**(대본→Q&A 순으로 나열) — v2 스키마에 병렬 실행 문법을 추가하지 않는다는 기존 결정(schema §5, bundle 순차 결정)을 그대로 따르며, DAG 형태만 다이아몬드로 두어 나중에 병렬 실행기가 생기면 그대로 활용 가능하게 한다.

## 5. 승인 게이트: 2개, 위치와 근거

| 게이트 | 위치 | 승인 대상 | 반려 복귀(rejection_target 매핑) |
|---|---|---|---|
| ① PPT승인 | PPT초안생성 뒤 | ppt_draft | 내용오류 → PPT초안생성 (version+1) |
| ② 발표패키지승인 | 대본·Q&A 생성 뒤 | presentation_script + expected_qna (+ppt_draft 최종 확인) | 대본문제 → 발표대본생성 / 질문답변문제 → 예상QNA생성 / PPT문제 → PPT초안생성(재승인 필요, 게이트 ① 재통과) |

**왜 1개가 아니라 2개인가**: 최종 게이트 1곳만 두면 PPT 오류가 대본·Q&A까지 다 만들어진 뒤에야 발견되어 3종 전부 재작업된다. 게이트 수 판단 기준은 "반려 시 재작업 전파 범위" — PPT는 하류 2개 산출물의 기반이므로 먼저 잠근다.
**왜 3개가 아닌가**: 대본과 Q&A는 상호 독립이고, 같은 사람(혜미)이 같은 시점(발표 준비)에 함께 검토하는 물건이다. 게이트를 나누면 혜미의 승인 왕복만 늘고 반려 전파 차단 효과는 없다. 대신 **문서별 approval 블록은 각자 가진다**(방역에서 보고서·증명서가 각각 status를 갖되 게이트 stage는 1개였던 패턴과 동일) — 대본만 반려하고 Q&A는 승인하는 부분 반려가 가능하다.

**헌장 적용**: 헌장 3절 기준으로 초안 작성(stage 3·5·6)은 자동실행 가능, "발표자료 확정"은 승인 필요, 실제 제출·발송 행위는 절대 자동화 금지. 이 뒷단에는 "발송" stage 자체가 없다 — 파이프라인은 **저장까지만** 하고, 발표 현장에서 실제로 쓰는 행위는 사람 몫이다. 승인 안 된 문서가 실전에 쓰이는 것을 막는 장치는 ① 게이트 ② 뒤에만 저장이 오는 DAG 순서, ② 저장 stage 자체의 승인상태 재검증(이중 검증)이다.
**헌장 재작성 트리거 발동**: 헌장 5절은 "정부지원사업 스킬에 발표자료 하위 공정이 실제로 추가될 때" 헌장을 다시 쓰라고 정해두었다. 이 설계가 그 조건에 해당하므로, **Sonnet이 manifest 반영할 때 헌장 개정(발표 산출물 승인 규정 명문화)도 함께 혜미에게 상신할 것.**

## 6. shared_context 신규 필드 (7개)

| 필드 | type | written_by | read_by | 설명 |
|---|---|---|---|---|
| selection_notice | object | 선정접수 | 발표요건추출, PPT초안생성 | 선정 통보 정보: 공고 id(정본 real_announcements.json의 id 참조), 발표일시, 발표방식(대면/온라인), 통보 원문 |
| submitted_application_ref | string | 선정접수 | PPT초안생성, 발표대본생성, 예상QNA생성 | **사람이 실제 제출한 확정본**의 경로/참조. draft_application(초안)이 아님 — 1절 전제 참고 |
| presentation_requirements | object | 발표요건추출 | PPT초안생성, 발표대본생성 | 발표시간(분), 슬라이드 제한, 발표평가 배점표(공고 scoring_rubric_note 활용), 질의응답 시간. 미확인 항목은 `[확인 필요]` |
| ppt_draft | object | PPT초안생성, PPT승인 | 발표대본생성, 예상QNA생성, 발표패키지승인, 발표패키지저장 | 슬라이드 아웃라인+내용. `approval_required: true` + approval 블록(status/version/approved_by/rejection_reason/version_history) + locked — 방역 문서 패턴 그대로 |
| presentation_script | object | 발표대본생성, 발표패키지승인 | 발표패키지저장 | 발표대본. approval 블록 동일 적용 |
| expected_qna | object | 예상QNA생성, 발표패키지승인 | 발표패키지저장 | 예상 질문+답변 목록(질문 근거: judge_panel_review 경고, deduction_map, needs_confirmation, 위험표현 flag). approval 블록 동일 적용 |
| presentation_package_record | object | 발표패키지저장 | (없음) | 승인완료 패키지의 보관 기록(경로, 버전, 승인자, 시각) |

**기존 구간과의 연결(신규 필드 아님, 읽기만)**: 앞단 정본 계층(`scripts/real_announcements.json`)의 해당 공고(scoring_rubric/scoring_rubric_note) ← selection_notice.공고 id로 조회. 중간구간 결과의 judge_panel_review / deduction_map / psst_review / needs_confirmation / exaggeration_flags ← 예상QNA생성이 질문 소재로 읽음. 즉 **뒷단은 새 판정 로직을 만들지 않고, 중간구간이 이미 계산해 둔 약점 신호를 재사용한다.**

## 7. tier 제안 (모델명 하드코딩 금지 — 기존 manifest의 low_cost/mid/high 어휘 유지)

| stage | tier | 근거 |
|---|---|---|
| 발표요건추출 | low_cost | 추출·분류 수준, 창의 판단 없음 |
| PPT초안생성 | mid | 제출확정본의 재구성 — 새 내용 창작이 아니라 구조 변환+요약 |
| 발표대본생성 | mid | 잠긴 PPT에 종속된 문장 생성 |
| 예상QNA생성 | high | 심사위원 관점 적대적 시뮬레이션 — 기존 "심사위원 모드 자기검수"(high)와 동급 난이도. 여기서 약점을 못 잡으면 실전 Q&A에서 그대로 노출됨 |

## 8. 알려진 한계 / 미결 (임의 확정하지 않은 것)

- **PPT 파일(.pptx) 실물 생성은 이 파이프라인 범위 밖.** ppt_draft는 구조화된 슬라이드 내용(아웃라인+본문)까지이고, .pptx 렌더링은 실행 시점의 도구(pptx 스킬 등) 몫 — manifest는 도구를 하드코딩하지 않는다.
- **발표 통보문 서식이 공고마다 다름** — 발표요건추출의 추출 정확도는 미검증. 미확인 항목 `[확인 필요]` 원칙으로 방어하되, 실사례 누적 전까지 low_cost tier 적정성도 잠정값.
- **반려 재시도 최대 횟수 미정** — 방역과 동일한 open question(방역 mock 3회는 임의값). 이 뒷단도 같은 값으로 시작하되 정식 결정은 실사용 후.
- **run_if 조건("발표평가_또는_발표자료가_요구됨") 판정 주체**: 발표요건추출 결과가 `[확인 필요]`뿐이면 자동 스킵하지 말고 사람에게 물을 것(모름≠발표없음 — "모르면 낙관 처리 않는다" 원칙).
- 발표 **연습**(리허설 피드백) 공정은 이번 범위에 넣지 않음 — 헌장 5절이 언급하는 "발표연습"은 별도 판단 대상으로 남김.

## 9. 다음 액션 (전부 Sonnet, Fable 불필요)

- [ ] manifest.yaml에 뒷단 8 stage + shared_context 7필드 반영 (schema v2 어휘, 기존 중간구간과 같은 파일에 넣을지 별도 manifest로 둘지는 기존 파일 구조 확인 후 결정 — v1 스타일 manifest라 stage 삽입 방식 주의)
- [ ] scripts/run.py mock 확장: 승인 루프(방역 `_run_document_approval_cycle` 패턴 이식) + 저장 전 승인상태 강제검증
- [ ] 골든 레퍼런스(온천꽃집 발표대본/QnA/최종.pptx)와 mock 산출물 구조 대조 테스트 1건
- [ ] 헌장 5절 재작성 트리거 발동 사실을 혜미에게 보고, 헌장 개정안 상신
- [ ] validate_manifest.py + 회귀테스트 12종 전부 기존과 동일 결과 확인(뒷단 추가가 중간구간 결과에 영향 없어야 함)

<!-- ok -->
