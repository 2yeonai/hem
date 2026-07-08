# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This is an **Obsidian vault** (`.obsidian/`), not a single codebase. It holds four independent, unrelated project folders, each a self-contained "AI 직원(employee) 스킬" for a different small business the user runs or is building for:

- `클로드 ai 자동화/` — shared schema/charter definitions used by the other three skills (see below)
- `클로드 꽃집 ai/` — flower shop automation (⚠️ see Gotchas — the folder root is mislabeled)
- `클로드 방역 ai/` — pest-control ("방역&클린") operations automation — the most complete/current example of the pattern
- `클로드 정부지원사업 ai/` — government small-business grant application assistant, plus an unrelated nested project (see below)

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
- v2 (yaml): referenced everywhere else as `ai공장짓기/manifest.schema.v2.yaml` and `ai공장짓기/scripts/validate_manifest.py` — **this `ai공장짓기` folder does not currently exist in the vault** (see Gotchas). v2 adds `triggers`, `run_if`, `entry_points`, and the `approval` block on top of v1.

## Commands

Run from inside the relevant skill folder (paths below assume that; adjust `ai공장짓기/...` per the Gotchas note):

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

- **`클로드 꽃집 ai/` root is not the flower shop skill.** Its root `SKILL.md`, `manifest.yaml`, `scripts/`, and `test/` are a copy of the **정부지원사업 매칭 스킬 (gov-support-matching-skill)** — same content as `클로드 정부지원사업 ai/`, apparently placed here by mistake in a past session. The actual flower-shop artifacts live alongside it without their own root manifest/SKILL.md: `golden_set.yaml`, `12봇_kind분류표.yaml` (the real 12-bot pipeline classification), `code/storage_bot.py`, `참고자료_행정구역_지명사전.yaml`. There's also a nested `gov-support-skill/` subfolder with yet another copy. Don't assume `클로드 꽃집 ai/SKILL.md` describes flower-shop behavior.
- **The shared v2 schema folder is missing.** `클로드 방역 ai/manifest.yaml` and `클로드 꽃집 ai/12봇_kind분류표.yaml` both reference `ai공장짓기/manifest.schema.v2.yaml` and `ai공장짓기/scripts/validate_manifest.py` as if they were siblings of each skill folder. As of 2026-07-08 no `ai공장짓기` folder exists anywhere in the vault (it existed as recently as 2026-07-07 per `클로드 꽃집 ai/최종점검_리포트_2026-07-07.md`). It most likely needs to be restored/relocated — possibly related to `클로드 ai 자동화/` (which has the older v1 `manifest.schema.json` but not a v2 yaml). Commands that reference this path will fail until it's resolved — ask the user where it went before recreating it from scratch.
- **`.stale-*` / `.truncated-*` files are not real content.** They're backups left by a documented Edit/Write bug where large-file edits get silently truncated mid-byte on this Windows/bash-mount setup (see `클로드 방역 ai/SKILL.md` "유지보수" section and `클로드 정부지원사업 ai/HANDOFF.md`). The workaround in use: rename the target to `file.stale-<timestamp>` before rewriting, then rewrite via bash heredoc and verify with `python3 -m py_compile` / `yaml.safe_load` rather than trusting the Edit/Write tool result on large files in these folders. Safe to ignore these files, but don't delete them without checking whether they're the only copy of something.
- **`클로드 정부지원사업 ai/jbjw-main/jbjw-main/hyemi-ai-factory/` is a separate, unrelated project** (has its own `CLAUDE.md`, `pyproject.toml`, numbered docs folders `00_rules` … `10_handoff`). It's nested inside the gov-support folder but isn't part of the AI-factory skill pattern described above — read its own `CLAUDE.md` before working in it rather than applying anything from this file.
- Nothing here calls a real LLM or STT API yet — every `run.py` is a mock stub. Don't report a skill as "working end-to-end" without checking `SKILL.md`'s "알려진 한계" (known limitations) section first.

## Obsidian PARA + 5. Zettelkasten structure

Separate from the four AI-skill folders above, the vault root also has a general PARA + 5. Zettelkasten structure for personal notes ("지식 발전소"/knowledge engine vs. "프로젝트 작업대"/project workbench, kept deliberately apart):

- `0. Docs/` — reference documents: manuals, policy materials, summaries of external documents (not vault operating rules, not personal-interest learning material — see `0. Docs/CLAUDE.md` for how this differs from `3. Resources/`)
- `1. Projects/` — time-boxed work with a deadline and a Definition of Done
- `2. Areas/` — ongoing responsibilities with no end date
- `3. Resources/` — topic reference material
- `4. Archive/` — completed/inactive items (never deleted, only moved here)
- `5. Zettelkasten/` — permanent knowledge, split into `00. Inbox/` (fast capture) → `10. Literature/` (source-bound notes) → `20. Permanent/` (atomic, densely-linked insight notes)
- `6. Templates/` — note templates and the template registry
- `7. Attachments/` — binary files (images, PDFs) referenced by notes

Each of these folders has its own `CLAUDE.md` with the detailed rules (frontmatter schema, Dataview queries, tag conventions, maintenance checklist) for that folder — read the relevant one before creating or filing a note there rather than assuming from the folder name. `5. Zettelkasten/CLAUDE.md` holds the cross-cutting ZK principles; its three subfolders each have their own more specific `CLAUDE.md`.

Note: Dataview and Templater query examples appear throughout these docs, but as of 2026-07-08 neither plugin is actually installed in `.obsidian/plugins/` yet (only the `terminal` plugin is) — the queries are written in advance for when those plugins get added, not proof they currently work.
