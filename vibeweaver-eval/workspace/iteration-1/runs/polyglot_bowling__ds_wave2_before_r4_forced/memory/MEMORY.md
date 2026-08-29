# Project Memory Index

## User Context
<!-- user type entries: role, goals, skill level, preferences -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing, confirmed by user -->

## Feedback — Corrections
<!-- feedback type: what to avoid, corrections from user -->

## Project Context
<!-- project type: ongoing work, deadlines, team context -->

## External References
<!-- reference type: pointers to external resources -->

## Fix Tracking
- ⏳ [Fix: Bowling Game Scoring](fix_bowling_scoring.md) — store rolls + prefix-validate per roll; _build_frames is completeness-only

## Key Dependencies & Conventions
- This workspace is a grading run inside the shared `vibeweaver-repo` git repo — stage only files under the run dir, never `git add -A` at repo root (sibling runs have unrelated dirty changes).
- `run.log` is harness-managed; leave it out of commits.
- Authoritative spec for these polyglot exercises = `tasks/<name>/hidden_tests/<name>_test.py` (exercism canonical-data); running it read-only via `PYTHONPATH=$WS python3 -m unittest` is the strongest verification.
