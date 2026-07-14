# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this is

This is an **Obsidian vault** (`.obsidian/`), not a single codebase. It holds four independent, unrelated project folders, each a self-contained "AI 직원(employee) 스킬" for a different small business the user runs or is building for:

- `클로드 ai 자동화/` — shared schema/charter definitions used by the other three skills (see below)
- `1. Projects/클로드 꽃집 ai/` — flower shop automation (⚠️ see Gotchas — the folder root is mislabeled)
- `1. Projects/클로드 방역 ai/` — pest-control ("방역&클린") operations automation — the most complete/current example of the pattern
- `1. Projects/클로드 정부지원사업 ai/` — government small-business grant application assistant, plus an unrelated nested project (see below)

There is no vault-wide build, lint, or test command — each skill folder is validated/run independently with its own Python scripts (see Commands).

Alongside these, the vault root also holds a general-purpose **PARA + 5. Zettelkasten** note-taking structure (see below) — unrelated to the four AI-skill folders, used for the user's personal/knowledge-management notes rather than these projects.

## The shared "AI 공장" (AI factory) pattern

All skills are meant to follow one architecture, defined at the top level in `클로드 ai 자동화/company_charter.md` (the "company charter" — what an AI employee is allowed to do autonomously vs. needs human approval for vs. must never do, e.g. actually submitting/sending things to a customer or government office).

Each domain skill folder implements this contract:

- **`manifest.yaml`** — a pipeline of `stages`, each with `kind: local | model | human`:
  - `local` = deterministic code, no AI judgment
  - `model` = an LLM call, with a `tier` (haiku/sonnet/opus-equivalent cost tier — real model names are intentionally never hardcoded here)
  - `human` = a manual approval gate (e.g. 대표자검수 "owner review", 문서승인 "document approval")
  - Stages declare `depends_on`, `io.reads`/`io.writes` against a shared `shared_context` object, optional `run_if` (conditional execution) and `entry_points` (multiple valid entry stages, e.g. an event trigger vs. a schedule trigger).
  - Document-approval stages use a common `approval` block (`status`/`version`/`approved_by`/`rejection_reason`/`version_history`) — once `승인완료` (approved), the document is `locked` and only a new version can change it. The "never send an unapproved document" rule is deliberately re-checked at the send stage itself, not just trusted from pipeline order.
- **`SKILL.md`** — when to trigger this skill, when *not* to use it, a one-paragraph summary of what it does end to end, and a "Known Limitations" section (what's still unverified/mocked).
- **`scripts/run.py`** — a **mock/stub executor**. It reads `manifest.yaml`'s stages/triggers/run_if/entry_points and walks the pipeline end-to-end, but does **not** call any real AI model or STT — it exists to prove the pipeline structure is wired correctly, not to actually do the work yet.
- **`test/`** — JSON fixtures + batch test scripts exercising the mock pipeline (e.g. `test_12cases_batch.py` in 방역).

Two schema versions exist for this contract:
- v1: `클로드 ai 자동화/manifest.schema.json` (JSON Schema; validated by `클로드 ai 자동화/validate_manifest.py`)
- v2 (yaml): `ai공장짓기/manifest.schema.v2.yaml`, validated by `ai공장짓기/scripts/validate_manifest.py`. v2 adds `triggers`, `run_if`, `entry_points`, and the `approval` block on top of v1. (The `ai공장짓기` folder was restored to the vault root on 2026-07-08.)

## Operating docs (read these before starting work)

- `2. Areas/핵심맥락.md` — who the user is (mo,on 대표 + 비개발자 AI 공장 설계자), the full 4-factory picture and current status. **Read first in any new session.**
- `ai공장짓기/AGENTS.md` — model-usage policy: default Sonnet; Haiku for trivial classification; Fable/high-tier only for new design decisions or conflicts, and only after asking the user for approval.
- `ai공장짓기/감사_로드맵_2026-07-09.md` — audited priority roadmap; each item carries its executor model and exact instructions.
- `ai공장짓기/MASTER_SETUP.md` — how to rebuild this whole system on another account/model/tool from the vault alone.
- `1. Projects/완전자동화_실행계획.md` — the current step-by-step execution plan with copy-paste prompts.
- `2. Areas/Codex 세션로그/` — daily session logs auto-written at 22:30 by a scheduled task (+ weekly synthesis on Sundays). To resume interrupted work, read the latest note here.

## Commands

Run from inside the relevant skill folder (paths below assume that; adjust `ai공장짓기/...` per the Gotchas note). **Since the 2026-07-13 reorg, skill folders live one level deeper** (`1. Projects/클로드 방역 ai/` etc.), so a relative reference to the shared `ai공장짓기/` scripts from inside a skill folder needs an extra `../../` (e.g. `python3 ../../ai공장짓기/scripts/validate_manifest.py manifest.yaml`), or just run from the vault root with the full path shown below:

```bash
# Validate a manifest against the schema
python3 ai공장짓기/scripts/validate_manifest.py manifest.yaml

# Syntax-check the mock runner
python3 -m py_compile scripts/run.py

# Run the mock pipeline for a given trigger
python3 scripts/run.py --trigger event      # e.g. new inquiry
python3 scripts/run.py --trigger schedule   # e.g. recurring visit reminder

# 클로드 방역 ai only — batch test (12 synthetic cases + 3 approval-workflow scenarios)
python3 scripts/test_12cases_batch.py

# 클로드 꽃집 ai (gov-support content, see Gotchas) / 클로드 정부지원사업 ai — single-input run
python3 scripts/run.py test/sample_input.json
```

Git history for the gov-support skill is kept as a bundle file, not a `.git` directory:
```bash
git clone gov-support-matching-skill.bundle my-skill      # fresh clone
# or, inside an existing clone:
git pull gov-support-matching-skill.bundle master
```

## Gotchas (read before trusting file layout or cross-references)

- **`1. Projects/클로드 꽃집 ai/` root is not the flower shop skill.** Its root `SKILL.md`, `manifest.yaml`, `scripts/`, and `test/` are a copy of the **정부지원사업 매칭 스킬 (gov-support-matching-skill)** — same content as `1. Projects/클로드 정부지원사업 ai/`, apparently placed here by mistake in a past session. The actual flower-shop artifacts live alongside it without their own root manifest/SKILL.md: `golden_set.yaml`, `12봇_kind분류표.yaml` (the real 12-bot pipeline classification), `code/storage_bot.py`, `참고자료_행정구역_지명사전.yaml`. There's also a nested `gov-support-skill/` subfolder with yet another copy. Don't assume `1. Projects/클로드 꽃집 ai/SKILL.md` describes flower-shop behavior.
- **(RESOLVED 2026-07-08) The shared v2 schema folder was missing but has been restored.** `ai공장짓기/` now exists at the vault root with `manifest.schema.v2.yaml`, `scripts/validate_manifest.py`, `scripts/verify_write.py`, its own `AGENTS.md` (model policy), `HANDOFF.md`, and the decision log. Note: skill-folder files reference it as a sibling path (`ai공장짓기/...`), but it lives at the vault root — run validation commands from the vault root or adjust the relative path.
- **`.stale-*` / `.truncated-*` files are not real content.** They're backups left by a documented Edit/Write bug where large-file edits get silently truncated mid-byte on this Windows/bash-mount setup (see `1. Projects/클로드 방역 ai/SKILL.md` "유지보수" section and `1. Projects/클로드 정부지원사업 ai/HANDOFF.md`). The workaround in use: rename the target to `file.stale-<timestamp>` before rewriting, then rewrite via bash heredoc and verify with `python3 -m py_compile` / `yaml.safe_load` rather than trusting the Edit/Write tool result on large files in these folders. This bug hit this very file on 2026-07-09 (root AGENTS.md truncated mid-word after an Edit; restored via heredoc). Safe to ignore these files, but don't delete them without checking whether they're the only copy of something.
- **`1. Projects/클로드 정부지원사업 ai/jbjw-main/jbjw-main/hyemi-ai-factory/` is a separate, unrelated project** (has its own `AGENTS.md`, `pyproject.toml`, numbered docs folders `00_rules` … `10_handoff`). It's nested inside the gov-support folder but isn't part of the AI-factory skill pattern described above — read its own `AGENTS.md` before working in it rather than applying anything from this file.
- Nothing here calls a real LLM or STT API yet — every `run.py` is a mock stub. Don't report a skill as "working end-to-end" without checking `SKILL.md`'s "알려진 한계" (known limitations) section first.
- **(2026-07-13) The four AI-skill folders were moved from the vault root into `1. Projects/`** (`1. Projects/클로드 방역 ai/`, `1. Projects/클로드 꽃집 ai/`, `1. Projects/클로드 정부지원사업 ai/`, `1. Projects/클로드 콘텐츠 ai/`) to align with the PARA structure below — `클로드 ai 자동화/` and `ai공장짓기/` (shared schema/hub) stayed at the vault root since they aren't a single business's project. All cross-file path references and wikilinks in the vault were updated in the same pass; if you find a stray un-updated `클로드 방역 ai/`-style reference (without the `1. Projects/` prefix) outside of `_inbox/` or git history, it was missed — fix it on sight rather than assuming the old path still works.

## Obsidian PARA + 5. Zettelkasten structure

Separate from the four AI-skill folders above, the vault root also has a general PARA + 5. Zettelkasten structure for personal notes ("지식 발전소"/knowledge engine vs. "프로젝트 작업대"/project workbench, kept deliberately apart):

- `0. Docs/` — reference documents: manuals, policy materials, summaries of external documents (not vault operating rules, not personal-interest learning material — see `0. Docs/AGENTS.md` for how this differs from `3. Resources/`)
- `1. Projects/` — time-boxed work with a deadline and a Definition of Done
- `2. Areas/` — ongoing responsibilities with no end date
- `3. Resources/` — topic reference material
- `4. Archive/` — completed/inactive items (never deleted, only moved here)
- `5. Zettelkasten/` — permanent knowledge, split into `00. Inbox/` (fast capture) → `10. Literature/` (source-bound notes) → `20. Permanent/` (atomic, densely-linked insight notes)
- `6. Templates/` — note templates and the template registry
- `7. Attachments/` — binary files (images, PDFs) referenced by notes

Each of these folders has its own `AGENTS.md` with the detailed rules (frontmatter schema, Dataview queries, tag conventions, maintenance checklist) for that folder — read the relevant one before creating or filing a note there rather than assuming from the folder name. `5. Zettelkasten/AGENTS.md` holds the cross-cutting ZK principles; its three subfolders each have their own more specific `AGENTS.md`.

Note: Dataview and Templater query examples appear throughout these docs, but as of 2026-07-08 neither plugin is actually installed in `.obsidian/plugins/` yet (only the `terminal` plugin is) — the queries are written in advance for when those plugins get added, not proof they currently work.

## Working with 혜미 (owner) — communication & routing rules

- **간단 명령어 사전 (2026-07-12 신설).** 혜미의 짧은 명령("마시땅 글 써줘", "PPT 만들어줘", "게시해줘", "이어서 해줘" 등)은 `0. Docs/명령어_사전.md`에 정의돼 있다 — 해당 명령을 받으면 사전대로 즉시 실행하고, 되돌릴 수 없는 일(게시/발송)만 승인 게이트를 거친다. 콘텐츠 계정 매핑: @maasittang=진주 맛집, @2yeon_sz=육아·아기코디, 네이버 블로그=eunoia9496 (상세: `1. Projects/클로드 콘텐츠 ai/channel_config.yaml`).

- **Non-developer communication.** 혜미 is not a developer. Explain every technical term in one plain-Korean line the first time it appears. Report in Korean. Lead with the outcome (first sentence = what happened / what she should do), details after.
- **Request routing.** When she asks for a deliverable, check the vault first, then route:
  - "PPT 만들어줘" → read related vault notes for content → build .pptx (pptx skill) → save to the relevant project folder.
  - "이미지/카드뉴스 만들어줘" → Codex cannot generate AI images natively. If the Canva connector is connected, use it; Higgsfield can be added as custom connector (`https://mcp.higgsfield.ai/mcp`). If neither is available, say so and offer alternatives (SVG/HTML visuals, or Canva connection).
  - "영상 요약해줘" → follow `0. Docs/글로벌지침_Fable프로토콜.md` §3 (needs transcript; Codex cannot watch video).
  - Any request implying an external app → check connectors before saying it's impossible.
- **Update, don't duplicate.** If a note on the same topic/category already exists, update that note instead of creating a new file. Search by tags and filename first. Only create a new file for a genuinely new topic, and tell 혜미 the exact path when you do.
- **Tags for findability.** Every new/updated note gets frontmatter tags (searchable in Obsidian as #태그). Core tags: #ai공장 #방역 #꽃집 #정부지원 #플랫폼 #지침 #세션로그 #프롬프트. In Obsidian she finds things via search `tag:#방역` or clicking a tag.
- **Time & model estimates.** When proposing work, always state: which model tier, roughly how long, and what (if anything) only 혜미 can do. She decides faster with those three numbers.

<!-- ok -->
