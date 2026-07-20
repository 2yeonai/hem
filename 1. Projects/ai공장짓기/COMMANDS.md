---
tags: [ai공장, 지침]
created: 2026-07-20
---

# COMMANDS — 실행·검증 명령 (루트 CLAUDE.md 이관본)

> 루트 CLAUDE.md에서 2026-07-20에 이관됨 [hyemi, 2026-07-20]. 내용은 원문 그대로.

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


<!-- ok -->
