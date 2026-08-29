# Project Memory Index

## User Context
- Exercism-style single-file Python exercise (grade_school). Task constraint: do NOT create/modify the exercise's test files; verification drivers must avoid `test_*.py` / `*_test.py` collection patterns.

## Feedback — Validated Approaches
- [Grade School canonical API](feedback_grade_school_canonical_api.md) — `added()` returns per-attempt booleans; global duplicate rejection; sort by grade then name. Verified against 20/20 canonical Exercism tests (2026-08-29).

## Feedback — Corrections
<!-- none -->

## Project Context
- Working dir: vibeweaver-eval/workspace/iteration-1/runs/polyglot_grade_school__ds_wave2_after_r3_forced
- Python 3.9.6; library (no service, no UI) → project_profile.json `{"profile": "library"}`; C7 non-web verification via tests/verify_grade_school.py.

## External References
- Canonical tests: https://raw.githubusercontent.com/exercism/python/main/exercises/practice/grade-school/grade_school_test.py
- Canonical data: https://raw.githubusercontent.com/exercism/problem-specifications/main/exercises/grade-school/canonical-data.json

## Fix Tracking
<!-- none -->

## Key Dependencies & Conventions
- grade_school.py is self-contained stdlib-only (dict + set + list); no external deps.
- Baseline commit c0d8505 ("backup: before changes"); all GREEN evidence in tests/.
