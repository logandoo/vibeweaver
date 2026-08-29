# fix_grade_school.md

- type: fix
- status: ✅ Verified (2026-08-29)
- problem: Starter `grade_school.py` stubs (`pass`) for the Exercism "Grade School" exercise did nothing.
- solution: Implemented `School` with a `name → grade` dict (`_students`) plus an `_added` attempt-results list. `add_student` rejects globally-duplicate names (returns False, logs False), `roster()` sorts by grade then name, `grade(n)` returns sorted names, `added()` returns the ordered boolean results. grade_school.py.
- verification: tests/verification_run.log — 20/20 canonical cases pass; `python3 -m py_compile` OK; A4.9 independent review PASS.
- avoided pitfall: `added()` semantics = booleans (not names) — confirmed from canonical-data.json "add" property and official example.py.
