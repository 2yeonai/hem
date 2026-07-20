---
title: "AI Context Index"
doc_type: "reference"
updated: "2026-07-13"
owner: "본인"
summary: "다른 AI 도구(ChatGPT 등)가 이 볼트에서 맥락을 빠르게 파악하기 위한 진입점 인덱스"
scope: "볼트 전체 — 여러 AI 계정/도구가 이어서 작업할 때의 공통 출입구"
audience: "본인, ChatGPT Work, 그 외 이 볼트를 읽는 모든 AI"
keywords: ["context", "index", "chatgpt", "cross-ai", "hub"]
related: ["AI Working Rules", "ai공장짓기/AI공장_허브"]
status: "active"
---

# AI Context Index

> ⚠️ **주의 (2026-07-18 [gombeck1])**: 아래 "현재 진행 중인 프로젝트" 표는 2026-07-13 기준으로 멈춰 있음. 최신 업무 상태의 정본은 `0. Docs/혜미_자동화_운영표.md` §2. 이 문서와 [[AI Working Rules]]는 ChatGPT-GitHub 연동용 진입점으로 유지 판정(2026-07-18 N1) — 연동 실사용 여부는 혜미 확인 대기.

> 이 문서는 **혼자만 보는 문서가 아니라, Claude/Cowork/Codex/ChatGPT처럼 서로 다른 AI 도구·계정이 이 Obsidian 볼트를 공유 맥락으로 이어 쓰기 위한 진입 지점**이다. 새 AI 세션(특히 ChatGPT — 로컬 볼트가 아니라 GitHub 저장소 사본을 읽음)은 다른 파일보다 먼저 이 문서를 읽어야 한다.

## 1. 이 볼트의 목적

이 Obsidian 볼트(`hem`)는 두 가지를 같이 담는다.

1. **"AI 공장" 프로젝트들** — 혜미(mo,on 대표, 비개발자 AI 공장 설계자)가 자기 사업(mo,on)과 다른 소상공인 업종을 위해 짓고 있는 자동화 스킬들. `1. Projects/` 아래 4개(방역/꽃집/정부지원사업/콘텐츠) + 공통 인프라(`클로드 ai 자동화/`, `ai공장짓기/`).
2. **개인 지식·업무 관리** — PARA(Projects/Areas/Resources/Archive) + Zettelkasten 구조로 된 일반 노트 시스템. AI 공장 프로젝트와는 성격이 다르지만 같은 볼트 안에서 링크로 연결된다.

누가 어떤 존재인지, 왜 이 시스템을 짓는지는 [[2. Areas/핵심맥락|핵심맥락]] 문서가 가장 먼저 답한다.

## 2. 주요 폴더 설명

| 폴더 | 역할 |
|---|---|
| `0. Docs/` | 볼트 운영 규칙·정책 문서 (이 문서 포함) |
| `1. Projects/` | 마감일 있는 프로젝트. **4개 AI 공장 스킬(방역/꽃집/정부지원사업/콘텐츠)이 하위 폴더로 여기 있음** (2026-07-13 이전) |
| `2. Areas/` | 지속 책임 영역 — 핵심맥락, mo,on 사업 운영, 세션로그 |
| `3. Resources/` | 참고 자료 |
| `4. Archive/` | 완료/비활성 항목 |
| `5. Zettelkasten/` | 영구 지식 — 00.Inbox → 10.Literature → 20.Permanent |
| `6. Templates/` | 노트 템플릿 |
| `7. Attachments/` | 첨부 바이너리 |
| `클로드 ai 자동화/` | 공통 헌장(company_charter)·v1 스키마 — 특정 프로젝트가 아니라 전체가 공유하는 규약이라 루트에 유지 |
| `ai공장짓기/` | 공통 v2 스키마·범용 러너·설계노트·허브 — 역시 루트에 유지 |
| `_inbox/` | 다운로드/녹음 파일 임시 반입함, 매일 밤 자동 분류 |

각 PARA/Zettelkasten 폴더는 자체 `CLAUDE.md`(Codex는 `AGENTS.md`)에 상세 규칙(프론트매터 스키마, 태그 규칙)이 있다 — 폴더 이름만 보고 추측하지 말고 그 폴더의 규칙 문서를 먼저 읽을 것.

## 3. 현재 진행 중인 프로젝트 목록

| 프로젝트 | 폴더 | 핵심 문서 | 상태(2026-07-13 기준) |
|---|---|---|---|
| ① 정부지원사업 공장 | `1. Projects/클로드 정부지원사업 ai/` | [[1. Projects/클로드 정부지원사업 ai/SKILL\|SKILL]] · [[1. Projects/클로드 정부지원사업 ai/HANDOFF\|HANDOFF]] | v0.5.0, 매칭·초안·8인심사위원 완성. 공고 자동수집 미착수 |
| ② 꽃집 공장 | `1. Projects/클로드 꽃집 ai/` | [[1. Projects/클로드 꽃집 ai/SKILL\|SKILL]] · [[1. Projects/클로드 꽃집 ai/HANDOFF\|HANDOFF]] | 14봇 설계 완료, 실제 코드 미착수 |
| ③ 방역 공장 | `1. Projects/클로드 방역 ai/` | [[1. Projects/클로드 방역 ai/SKILL\|SKILL]] | 18단계 파이프라인 완성, 실제 골든셋 검증 대기 |
| 콘텐츠 공장 | `1. Projects/클로드 콘텐츠 ai/` | [[1. Projects/클로드 콘텐츠 ai/SKILL\|SKILL]] · [[1. Projects/클로드 콘텐츠 ai/HANDOFF\|HANDOFF]] | 러너 위 mock 신축, 게시 연동은 혜미 회신 대기 |
| ④ AI회사 플랫폼(범용 러너) | `ai공장짓기/runner/` | [[ai공장짓기/runner/README\|README]] | MVP 완성(2026-07-12), 실LLM 연동 미착수 |
| 강사방법론 추출 | `1. Projects/강사방법론/` | [[1. Projects/강사방법론_추출\|강사방법론_추출]] | 골든셋 G1~G8 + 페르소나카드 v1 완료, 강의 계속 진행 중 |

## 4. ChatGPT가 먼저 읽어야 할 문서 순서

1. 이 문서 (AI Context Index) — 전체 지도
2. [[0. Docs/AI Working Rules|AI Working Rules]] — 작업 원칙
3. [[2. Areas/핵심맥락|핵심맥락]] — 혜미가 누구인지, 전체 그림
4. 작업하려는 프로젝트의 `SKILL.md`(또는 `HANDOFF.md`) — 이 볼트는 README/Context/Status 대신 **SKILL.md(트리거·요약·한계) + HANDOFF.md(세션 인수인계) + decision-log(결정근거)** 조합을 표준으로 쓴다 (아래 5번 참고)
5. 해당 프로젝트의 최신 decision-log / HANDOFF
6. [[ai공장짓기/AI공장_허브|AI공장 허브]] — 전체 프로젝트 그래프뷰 중심점, 두 클릭 안에 모든 문서 도달

## 5. 문서 컨벤션 매핑 (일반적인 README/Context/Status/DecisionLog/NextActions 대신)

이 볼트는 프로젝트마다 README.md를 새로 만들지 않는다. 대신:

- **README/Context 역할** → `SKILL.md` (언제 트리거되는지, 언제 쓰지 않는지, 전체 흐름 요약, 알려진 한계)
- **Current Status 역할** → `HANDOFF.md` (세션 간 인수인계, 현재 상태) 또는 `2. Areas/핵심맥락.md`의 "진행 중인 스킬별 현재 상태" 섹션
- **Decision Log 역할** → 각 프로젝트 폴더의 `decision-log_*.md` (예: `ai공장짓기/decision-log_skill-factory-architecture.md`)
- **Next Actions 역할** → `2. Areas/핵심맥락.md`의 "다음 결정 포인트" 섹션, 또는 `ai공장짓기/감사_로드맵_2026-07-09.md`

같은 역할의 문서가 이미 있으면 새로 중복 생성하지 말 것 (볼트 공통 규칙).

## 6. 최근 결정사항 링크

- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log_skill-factory-architecture]] — 공장 아키텍처 결정 전반
- [[1. Projects/강사방법론_추출|강사방법론_추출]] "[확정 2026-07-12]" 섹션 — 홍재우 방법론을 정부지원 공장 9번째 심사위원으로 채택
- [[1. Projects/클로드 꽃집 ai/decision-log_12to14봇|꽃집 12→14봇 decision-log]]

## 7. 교차-AI 작업 기록 위치

- Claude/Cowork 세션 기록: `2. Areas/Claude 세션로그/` (매일 22:30 자동 + 일요일 주간종합)
- Codex 세션 기록: `2. Areas/Codex 세션로그/` (있는 경우)
- 각 AI는 자기 이름의 세션로그 폴더에 기록하고, 다른 AI가 남긴 세션로그도 읽고 이어받을 것 — 세션로그가 곧 "끊긴 지점에서 이어받는" 메커니즘.

## 8. GitHub 동기화 상태 (ChatGPT 접근용)

- 원격 저장소: `github.com/2yeonai/hem` (private 여부는 GitHub에서 직접 확인 — 이 문서가 보장하지 않음)
- Obsidian 볼트가 원본(source of truth). GitHub은 ChatGPT가 읽기 위한 사본.
- `_inbox/`의 원본 PDF·음성파일, 개인정보·계약서 원본은 동기화 제외 대상 (자세한 내용은 `.gitignore` 및 [[0. Docs/AI Working Rules|AI Working Rules]] 참고)

## 업데이트 로그
- 2026-07-13: 최초 작성. 4개 AI 공장 폴더를 `1. Projects/` 밑으로 이동한 재구조화와 함께 생성.

<!-- ok -->
