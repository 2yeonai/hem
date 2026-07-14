---
title: "AI Working Rules"
doc_type: "policy"
updated: "2026-07-13"
owner: "본인"
summary: "여러 AI(Claude/Cowork/Codex/ChatGPT)가 이 볼트를 공유 맥락으로 쓸 때 지켜야 할 작업 원칙"
scope: "이 볼트에서 작업하는 모든 AI 도구/계정"
audience: "본인, ChatGPT Work, 그 외 이 볼트를 읽고 쓰는 모든 AI"
keywords: ["working rules", "principles", "chatgpt", "cross-ai", "governance"]
related: ["AI Context Index"]
status: "active"
---

# AI Working Rules

> [[0. Docs/AI Context Index|AI Context Index]]가 "어디를 봐야 하는지"를 안내한다면, 이 문서는 "본 걸 어떻게 다뤄야 하는지"를 정한다.

## 원칙

1. **Obsidian 문서를 사실의 원본(source of truth)으로 쓴다.** GitHub 사본이나 ChatGPT의 기억, 이전 대화 내용이 아니라 이 볼트의 현재 파일 내용이 기준이다. 볼트와 자기 기억이 다르면 볼트를 믿는다.
2. **기존 결정을 임의로 덮어쓰지 않는다.** 이미 `decision-log_*.md`나 문서 본문의 "[확정 YYYY-MM-DD]" 섹션에 적힌 결정은, 그 결정을 뒤집을 새로운 근거가 생겼을 때만 변경한다. 변경할 때는 기존 내용을 지우지 말고 왜 바뀌는지 같은 문서에 이어서 기록한다.
3. **문서 간 충돌 시, 최신 수정일만 보지 말고 본문의 상태 표기를 먼저 확인한다.** 예: `status: active`인 오래된 결정 문서가, 더 최근에 수정됐지만 `status: draft`인 문서보다 우선한다. 이 볼트는 `status`(todo/in-progress/completed/on-hold, 또는 active/deprecated)를 신뢰 신호로 쓴다.
4. **추측과 확정사항을 구분해서 말한다.** "~인 것 같다"와 "~로 확정됨"을 다른 문장으로 쓴다. 확정 근거가 없는데 확정처럼 보고하지 않는다. (이 원칙은 볼트 전체의 기존 관례이기도 하다 — `SKILL.md`의 "알려진 한계" 섹션, manifest 검증의 WARN/FAIL 구분 등.)
5. **작업 전, 해당 프로젝트의 표준 3종 문서를 먼저 확인한다.** 이 볼트는 README/Context/Status 대신 다음 조합을 쓴다(자세한 매핑은 Context Index 5번 참고):
   - `SKILL.md` (개요·트리거·한계)
   - `HANDOFF.md` (현재 상태·세션 인수인계)
   - `decision-log_*.md` (결정 근거)

   이 세 파일을 안 읽고 바로 파일을 고치거나 새로 만들지 않는다.
6. **작업 후 변경사항과 결정사항을 해당 프로젝트 문서에 반영한다.** 대화에서만 결정하고 끝내지 않는다 — HANDOFF나 decision-log에 한 줄이라도 남겨야 다음 세션(다른 AI 포함)이 이어받을 수 있다.
7. **되돌릴 수 없는 일은 항상 사람 승인 게이트를 거친다.** 문서 발송, 정부지원사업 접수 제출, GitHub push, 실제 코드/설정의 대규모 변경 등 — `클로드 ai 자동화/company_charter.md`(공통 헌장)에 정의된 원칙과 동일하다. AI가 스스로 판단해서 실행하지 않는다.
8. **업데이트, 중복 생성 금지.** 같은 주제·같은 역할의 문서가 이미 있으면 새로 만들지 말고 기존 문서를 갱신한다. 새 파일을 만들 때만 정당한 사유(진짜 새로운 주제)를 남긴다.
9. **민감정보는 GitHub 동기화 대상이 아니다.** `_inbox/`의 원본 PDF·음성파일(사업계획서, 강의자료), 개인 식별정보, 계약서 원본 등은 로컬 Obsidian에만 두고 GitHub에는 올리지 않는다. 이미 올라간 것이 있는지 의심되면 먼저 사람에게 확인하고, 임의로 push하지 않는다.
10. **모델 티어는 정책 문서를 따른다.** 기본 Sonnet, 사소한 분류는 Haiku, 새로운 설계 결정·충돌 상황에서만 상위 티어(Fable 등) — 반드시 먼저 사람 승인 후 사용. (`ai공장짓기/CLAUDE.md` 참고)

## 충돌 발생 시 보고 방식

문서 내용과 지금 대화에서 사람이 말한 내용이 다르면:
1. 무엇이 다른지 구체적으로 짚는다 (어느 문서의 어느 문장 vs 지금 한 말).
2. 임의로 어느 한쪽을 정답으로 단정하지 않는다.
3. 특별히 지시가 없으면, **지금 대화(현재 세션의 사람 지시)를 우선**하되, 왜 문서와 다른지는 반드시 남긴다.

## 업데이트 로그
- 2026-07-13: 최초 작성. [[0. Docs/AI Context Index|AI Context Index]]와 함께 생성.

<!-- ok -->
