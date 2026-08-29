# Verification Log — grade_school (polyglot_grade_school)

Task: implement `School` in `grade_school.py` per exercism grade-school spec (prompt.md + hidden test suite `tasks/polyglot_grade_school/hidden_tests/grade_school_test.py`).

- COV-9 skipped — reason: from-stub exercise — baseline run executed (unimplemented stub → `20 failed in 0.08s`, expected RED, logged below), no pre-existing working runtime to preserve; not a regression.
- Baseline verified RED (expected, from-stub): `python3 -m pytest -q <hidden_tests>/grade_school_test.py` → `20 failed in 0.08s` (all methods return `None`).
- iter 1 PASS: criteria #1-5 | evidence: full hidden suite `20 passed in 0.01s` (tests/hidden_tests_run.log) + manual prompt-scenario probe (tests/manual_probe.log: `added()` = [True,…,False] dedup, roster/grade sorted, grade 5 empty after duplicate Jim rejected) | changed: grade_school.py
