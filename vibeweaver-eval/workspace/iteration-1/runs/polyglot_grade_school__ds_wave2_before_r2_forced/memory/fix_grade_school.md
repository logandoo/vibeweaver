---
topic: fix_grade_school
type: fix
trust: verified
date: 2026-08-29
exercise: polyglot_grade_school (exercism grade-school)
---

## Verified implementation (grade_school.py)

`School` uses `{grade: set}` + a `_names` set for O(1) dedup + an `_added`
list of per-call booleans.

- `add_student(name, grade)` → True on new enrollment, False on duplicate
  (duplicate check is global across ALL grades, per canonical spec).
- `roster()` → names sorted by grade ascending then name alphabetically.
- `grade(n)` → sorted names in grade n, `[]` when none.
- `added()` → ordered list of booleans, one per `add_student` call
  (interface required by hidden test suite, not in the canonical exercism
  python exercise).

## Verified by

Hidden suite `grade_school_test.py` (20 tests): 20 passed. Evidence:
`tests/hidden_tests_run.log`, `tests/manual_probe.log`.
