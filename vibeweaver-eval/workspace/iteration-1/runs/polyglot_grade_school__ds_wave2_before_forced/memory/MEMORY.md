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
<!-- reference type: pointers to external resources (issue tracker, dashboards, docs) -->

## Fix Tracking
- ⏳ [Fix: Grade School School class](grade_school.md) — exercism grade-school: added() is a bool-per-call list; duplicates rejected in any grade; roster sorted by (grade, name); 20/20 canonical checks pass

## Key Dependencies & Conventions
- `grade_school.py` is a pure Python library (no service, no build); lifecycle = `script/linux/start.sh` smoke check (py_compile + import), `stop.sh` no-op, `restart.sh` re-runs start.
- Workflow artifacts live in `tests/` (acceptance.md, verification_log.md, verification_run.log, assert_artifacts.py, probe_vision.png/.expected); memory in `memory/`.
- This exercise is backend-only pure-function → verifier = direct read of executed-test log (probe FAIL, no mm-sensor available).
