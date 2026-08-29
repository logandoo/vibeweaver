> cap=5  stall=3×

# Acceptance Criteria — Grade School

Backend-only pure-function exercise. All criteria are unit-level (see E2E depth note below). Verification = direct read of executed-test log (`tests/verification_run.log`) produced by the TDD harness (RED on stub → GREEN on implementation) plus a FRESH cold-import run on the final tree.

1. [x] The module `grade_school.py` imports with no syntax or import errors (`python3 -m py_compile` exit 0; `import grade_school` OK).
2. [x] `School.add_student(name, grade)` returns `True` for a new student and records them in the given grade.
3. [x] `School.add_student` accepts keyword arguments (`add_student(name="Aimee", grade=2)`).
4. [x] `School.added()` returns a list of booleans, one per `add_student` call — `[True]` after one successful add.
5. [x] Adding a duplicate student name to the SAME grade returns `False`; `added()` becomes `[True, True, False, True]` in the canonical sequence.
6. [x] Adding a student who is already in a DIFFERENT grade also returns `False` (a student is not enrolled in multiple grades).
7. [x] `School.roster()` returns all students sorted by grade, then by name.
8. [x] `School.grade(n)` returns the students in grade `n` sorted by name; returns `[]` when no students are in that grade.
9. [x] Fresh `School()` starts empty — `roster()` is `[]` and `grade(1)` is `[]`.

## E2E depth

- **E2E depth: unit-only.** No HTTP service, no endpoints, no UI, no cross-component behavior — `School` is a pure in-process class. A full end-to-end exercise would be redundant (no transport to exercise). API-doc-driven test loop (§A4.7) and Playwright (§A1) do not apply.
