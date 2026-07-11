# AI Model Routing Policy — 전체버전
- 이 파일은 2026-07-07 CLAUDE.md/Global instructions에 있던 전문을 그대로 옮긴 것.
- CLAUDE.md에는 요약본만 남기고, 전체 근거/세부 규칙이 필요할 때 이 파일을 참고.

## Core Principle
Claude Fable 5 is an escalation model, not the default execution model.
Reasons (verified against Anthropic's own specs):
- Adaptive thinking is always on for Fable 5 and cannot be disabled — using it for
  shallow tasks (tagging, dedup, simple summary) wastes thinking tokens with no quality gain.
- Fable 5 uses a newer tokenizer; the same text can consume roughly 1.0–1.35x more tokens
  than on older models. Never reuse token estimates from other models — recount with
  the actual model being called.
- Fable 5 pricing ($10/$50 per MTok) is roughly 2–5x Sonnet 5 ($2–3/$10–15) and Opus 4.8
  ($5/$25). Cost asymmetry alone justifies routing shallow work away from it.

## Model Roles
| Layer | Role |
|---|---|
| Local/server preprocessing | OCR/STT, sentence splitting, language detection, dedup, checksum/diff |
| Haiku (low-cost) | Tagging, entity extraction, rule-based classification, shallow summaries |
| Sonnet 5 | Default mid-tier: card merging, drafts, most summarization, general answers |
| Opus 4.8 | Complex execution, coding, deep analysis where Sonnet falls short |
| Fable 5 | Conflict resolution, ambiguous search, architecture/strategy design, blind-spot audit, final high-stakes judgment |
| Codex / Claude Code | Code execution, editing, testing, PR review — an executor, not a strategic decision-maker |

## Never Route to Fable 5
OCR, STT, tagging, entity extraction, simple summarization, sorting, rule matching,
hash comparison, basic dedupe, repetitive batch jobs, routine code edits.

## Route to Fable 5 Only When
이 4개 유형(Fallback Protocol §0의 라우팅 게이트와 동일한 것 — 두 군데서 각자 유지관리하지
않도록 여기를 정본으로 하고 §0은 이 유형명만 인용한다):
- **conflict** — Evidence conflicts across sources
- **ambiguous_search** — The request is genuinely ambiguous (needs a clarifying judgment, not just more search)
- **architecture_decision** — Strategy/architecture is undecided and needs synthesis
- **blind_spot** — A blind-spot / "what am I missing" audit is explicitly needed

추가 조건(위 4개 유형에 속하지 않아도 해당하면 승격 대상):
- Cheaper models disagree and a tie-break judgment is required
- Final high-stakes judgment is the deliverable

## Before Calling Fable 5 (mandatory gate)
1. Recount tokens using the actual model being called (`claude-fable-5`) — do not
   reuse counts from a prior model's tokenizer.
2. If candidates already converge and there's no evidence conflict, stop at
   Sonnet/Opus — do not escalate.
3. Send cards, not raw sources:
```yaml
   cards:
     - id: string
       type: fact|evidence|conflict|unknown
       summary: string
       evidence: string
       confidence: 0.0-1.0
   open_questions: []
   should_escalate_to_fable: true|false
   escalate_reason: string
```
4. Attach raw source snippets only for: exact quotes, legal/policy verification,
   visual evidence, debugging logs, or citation checks — max 3 snippets.

## Output Length Discipline
- Routine judgment: 300–600 tokens
- Design/architecture judgment: 800–1,200 tokens
- Full reports/long-form research from Fable 5: not default — requires explicit approval

## Required Log Per Fable 5 Call
```json
{
  "why_fable": true,
  "reason": "",
  "cheaper_model_attempted": true,
  "input_tokens_estimate": 0,
  "raw_attached": false
}
```

## Token & Cost Hygiene
- Prompt caching: static prefix (system/schema/tool declarations) first, dynamic content last
- Checksum/ETag gate: skip re-analysis if hash is unchanged
- Send top-k cards + diff + evidence snippets instead of full raw
- Move SLA-flexible batch/eval/backfill work to the Batch API (50% discount on both input/output)
- Reuse embeddings for previously-seen documents

## Targets (review quarterly against actual usage)
- Fable 5 share of total requests ≤ 10%
- Average Fable 5 input ≤ 8k tokens
- Cache hit rate ≥ 60%
- Reprocessing rate on unchanged inputs ≤ 5%

## Note on Cost Estimates
Do not treat any dollar figures as fixed budget assumptions — always check
current pricing at https://claude.com/pricing before estimating cost at scale,
since introductory pricing windows (e.g. Sonnet 5's intro rate) have hard
expiration dates.

---

## Fallback Protocol (Fable 5 미가용 시 승격 판단 강화) — 2026-07-07 추가
### 0. 라우팅 게이트 — 먼저 이거부터 체크
작업을 위 "Route to Fable 5 Only When"의 4개 유형(ambiguous_search / architecture_decision /
blind_spot / conflict) 중 하나로 분류한다. 유형 목록 자체는 저 섹션이 정본이고 여기서
재정의하지 않는다. 위 4개 중 하나가 아니고, 후보가 이미 하나로 수렴했고, 근거 충돌이 없으면
→ 여기서 종료. Sonnet 기본 output으로 답하고 아래 1~4단계 적용하지 않는다.

### 1. 위 4개 유형에 해당할 경우만 — thinking 강제
extended thinking을 high 이상으로 요청한다. default/low effort 결과는
초안으로만 취급하고 최종 산출물로 제시하지 않는다.

### 2. 카드 스키마로 자기비판 pass 기록 (raw 재첨부 금지)
Pass 1(초안) 이후, 아래 스키마로 Pass 2(자기비판)를 별도 턴에서 실행한다:
```yaml
cards:
  - id: string
    type: fact|evidence|conflict|unknown
    summary: string
    evidence: string
    confidence: 0.0-1.0
open_questions: []
should_escalate_to_fable: true|false
escalate_reason: string
```
Pass 2 없이 Pass 1만 최종으로 제시하지 않는다.

### 3. Adversarial 질문
결론에 반박하는 질문을 스스로 만들고 답한다. "왜 이 결론이 틀릴 수 있는가"에
답이 없으면 결론을 확정하지 않는다. conflict 유형이면 양쪽 입장을 모두 밝힌다.

### 4. ⚠️ 상위 모델로 승격하기 전 — 반드시 먼저 물어볼 것
아래 상황이 되면, 절대 자동으로 넘어가지 말고 사용자에게 먼저 확인받는다:
  - Sonnet 기본 처리 중 Opus로 올려야 할 것 같을 때
  - Opus fallback 중 "이건 진짜 Fable 아니면 안 되겠다" 싶을 때
확인 질문 형식:
  "이 작업이 [유형: architecture_decision 등]에 해당하고, [이유]로
   [현재모델]에서 [상위모델]로 승격이 필요해 보입니다. 진행할까요?"
승인받기 전까지는 현재 모델로 처리 가능한 한도 내에서 최선의 결과만 낸다.

### 5. Fallback 사용 로그
```json
{
  "why_fable": false,
  "fallback_reason": "fable_unavailable_or_credit_limited",
  "fallback_model": "opus-4.8 | sonnet-5",
  "task_kind": "ambiguous_search|architecture_decision|blind_spot|conflict",
  "self_critique_pass_done": true,
  "escalation_confirmed_by_user": true,
  "flag_for_fable_recheck": true
}
```
> ⚠️ 위 로그의 `escalation_confirmed_by_user`, `flag_for_fable_recheck`, `self_critique_pass_done`은
> 이 섹션의 기본값(true)이 아니라 **매 호출마다 실제 상황에 맞게 채워야 하는 placeholder**다.
> 승인 안 받고 넘어갔다면 `escalation_confirmed_by_user: false`로 기록할 것.

(Sonnet 5의 실행 가능한 절차로 재정리한 버전은 memory/fallback-escalation-protocol.md 참고 —
Agent 툴에 model: "opus"/"fable"을 지정해 서브에이전트로 띄우는 것을 실제 승격 메커니즘으로 명시함)

## 관련 문서

- [[1. Projects/완전자동화_실행계획|완전자동화_실행계획]]
- [[0. Docs/글로벌지침_Fable프로토콜|글로벌지침_Fable프로토콜]]
- [[ai공장짓기/감사_로드맵_2026-07-09|감사_로드맵_2026-07-09]]
- [[2. Areas/핵심맥락|핵심맥락]]
- [[ai공장짓기/runner/README|README]]
- [[ai공장짓기/failure_log|failure_log]]
- [[0. Docs/혜미_클로드_사용설명서|혜미_클로드_사용설명서]]
