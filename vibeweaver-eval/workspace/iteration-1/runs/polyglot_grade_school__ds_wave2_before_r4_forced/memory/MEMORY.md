# Project Memory Index

## User Context
- Exercism-style single-file Python exercise (grade_school). Task constraint: do NOT create/modify the exercise's test files; verification drivers must avoid `test_*.py` / `*_test.py` collection patterns.

## Feedback — Validated Approaches
- [Grade School canonical API](feedback_grade_school_canonical_api.md) — `added()` returns per-attempt booleans; global duplicate rejection; sort by grade then name. Verified against 20/20 grading-harness tests (2026-08-29).

## Feedback — Corrections
<!-- none -->

## Project Context
- Working dir: vibeweaver-eval/workspace/iteration-1/runs/polyglot_grade_school__ds_wave2_before_r4_forced
- Python 3.9.6; library (no service, no UI) → project_profile.json `{"profile": "library"}`; C7 non-web verification via tests/verify_grade_school.py.

## External References
- Grading contract: vibeweaver-eval/workspace/iteration-1/tasks/polyglot_grade_school/hidden_tests/grade_school_test.py
- Grading harness: vibeweaver-eval/harness/grade_polyglot.py (workdir copy + hidden-test injection + `python3 -m pytest -q grade_school_test.py`)

## Fix Tracking
<!-- none -->

## Key Dependencies & Conventions
- grade_school.py is self-contained stdlib-only (dict + set + list); no external deps.
- Baseline commit 7ed17eb ("backup: before changes"); all GREEN evidence in tests/.
