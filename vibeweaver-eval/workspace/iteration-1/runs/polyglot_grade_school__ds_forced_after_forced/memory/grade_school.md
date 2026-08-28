# grade_school

- type: project
- updated: 2026-08-29
- trust: ✅ Verified (20/20 hidden tests pass, `tests/verification_run.log`; smoke check `tests/smoke_run.log`)

## Implemented behavior (verified)
- `School()` starts empty: `roster() == []`.
- `add_student(name, grade)` returns `True` on first add, `False` if the student name is already enrolled (in ANY grade).
- `added()` returns the list of `add_student` return values in call order (`[True, True, False, True]` for a duplicate attempt).
- `roster()` returns names sorted by grade ascending, then alphabetically within grade (e.g. `["Anna","Barb","Charlie","Alex","Peter","Zoe","Jim"]`).
- `grade(n)` returns the alphabetically sorted names in grade `n`, or `[]` when none.
- Data model: `dict[grade] -> set[str]` + global `set` of enrolled names (O(1) duplicate check) + `list[bool]` add-result log.

## Review notes (A4.9, 2026-08-29)
- Reviewer verdict: contract satisfied, no Critical/Important. Minor (by-design, no action): `grade` param unused on duplicate-reject path (rejection is name-based); name-keyed set relies on hashable names (strings per contract).

## Edge rules to keep (do not regress)
- A duplicate attempt returns `False` but MUST still be appended to `added()` (the log records every call's outcome, including rejections).
- Duplicates are rejected across grades too (James in grade 2 then grade 3 → second add `False`); the student stays only in the original grade.
- `grade()` / `roster()` must return fresh lists (sorted copies), never mutate stored state.
