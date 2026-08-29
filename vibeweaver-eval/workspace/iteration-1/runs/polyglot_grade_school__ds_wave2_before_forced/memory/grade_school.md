---
name: Fix: Grade School School class (exercism)
description: Implemented School class for the grade-school exercise — roster/grade/added contract, added() is a bool-per-call list, duplicates rejected across all grades
type: fix
date: 2026-08-29
status: ⏳
commit: N/A
---

# Fix: Grade School School class (exercism)

**Problem:** The exercise workspace shipped a `grade_school.py` stub with an empty `School` class (`add_student`/`roster`/`grade`/`added` all `pass`). The exercism test suite (canonical-data.json 2023-07-19) requires: `add_student(name, grade)` accepts keyword args; `roster()` = all students sorted by grade then name; `grade(n)` = students in grade n sorted by name; `added()` = a list of booleans — one per `add_student` call (`True` if the add succeeded, `False` if the name is a duplicate in ANY grade, including a different grade). A duplicate add must NOT appear in `roster()`/`grade()` and must not change existing enrollment.

**Attempted Fix:** `School` stores `self._students` as a list of `(name, grade)` tuples and `self._added` as a parallel list of booleans appended on every `add_student` call. Duplicate detection scans existing names; on rejection append `False` and return `False`. `roster()` sorts by `(grade, name)`; `grade(n)` filters then sorts by name; `added()` returns a copy of the bool list. Keyword args work automatically (parameter names are `name`, `grade`).

**Verification:** TDD RED→GREEN via the acceptance driver (20/20 canonical checks PASS, exit 0), lifecycle `script/linux/start.sh` smoke check exit 0, FRESH cold-import rerun 20/20 PASS, `tests/assert_artifacts.py --existing --backend-only` exit 0. Evidence: `tests/verification_run.log`, `tests/verification_log.md`.

**Rejected Alternatives:**
- Dict-of-sets keyed by grade: loses call order for `added()` (dicts/sets unordered) and needs extra bookkeeping to record rejected adds and to detect cross-grade duplicates (must scan all sets). Rejected — a flat list of tuples preserves insertion order and makes both duplicate checks and sorting trivial for this small domain.
- Naming the attribute `self.added`: shadows the `added()` method — calling `school.added()` would return the attribute, not the bool list. Rejected — internal attribute is `self._added`.
- Returning `True`/`False` from `added()` based on last call: contradicted by canonical tests that expect `[True, True, False, True]`. Rejected.

**Files:** `grade_school.py`

**Status:** ⏳ Pending — awaiting user confirmation
