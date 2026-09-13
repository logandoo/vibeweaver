---
type: fix
status: verified
updated: 2026-09-14
---

# grade-school roster implementation

✅ Verified — `grade_school.py` implements `School` with `_roster` (dict grade→[names]),
`_added` (bool history), `_names` (set for O(1) global uniqueness).

- `add_student` rejects a name already enrolled in ANY grade (appends `False`); else
  appends `True` and enrolls.
- `roster()` sorts grades ascending then names alphabetically.
- `grade(n)` returns sorted names or `[]`.
- `added()` returns a copy of the per-call boolean history.

Evidence: hidden canonical suite `20 passed` (`tests/green_run.log`), `py_compile` OK.
Gotcha: uniqueness is GLOBAL across grades, not per-grade — the spec's
"cannot be added more than once to a grade or the roster" means roster-wide.
