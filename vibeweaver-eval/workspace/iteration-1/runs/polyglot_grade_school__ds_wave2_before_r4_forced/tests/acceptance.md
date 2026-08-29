> cap=5  stall=3×

# Acceptance Criteria — grade_school exercise (C7 non-web library)

Verifier: direct read (non-web). Each criterion is a yes/no checkable on
observable `School` output via the verification driver transcript.

1. `School.roster()` returns `[]` when no students have been added.
2. `School.add_student(name, grade)` records the student; `School.added()`
   returns a list with one boolean per add attempt — `True` when the
   student was accepted.
3. A student added once appears in `roster()` (e.g. add "Aimee" grade 2 →
   `["Aimee"]`).
4. Multiple students in the same grade all appear in `roster()` and
   `added()` records `[True, True, True]` for three distinct accepts.
5. Adding the SAME student to the SAME grade twice is rejected: `added()`
   is `[True, True, False, True]` for Blair, James, James, Paul, and
   `roster()` still lists `["Blair", "James", "Paul"]`.
6. Adding the same student to a DIFFERENT grade is rejected: Blair g2,
   James g2, James g3, Paul g3 → `added()` is `[True, True, False, True]`
   and the student keeps only the first grade.
7. `roster()` sorts by grade number first (1, 2, 3 …), then alphabetically
   by name within each grade (e.g. add Jim g3, Peter g2, Anna g1 →
   `["Anna", "Peter", "Jim"]`).
8. `roster()` sorts students in the same grade alphabetically (e.g. add
   Peter, Zoe, Alex to grade 2 → `["Alex", "Peter", "Zoe"]`).
9. `School.grade(grade_number)` returns the sorted list of names in that
   grade only; `[]` when no students are enrolled in that grade.
10. `School.added()` returns the per-attempt booleans in insertion order
    across multiple grades (e.g. Chelsea g3, Logan g7 → `[True, True]`).
11. The module imports cleanly (`python3 -c "from grade_school import School"`)
    with no syntax or runtime errors; empty-roster / empty-grade edge cases
    return `[]`.
12. No file matching the exercise test-suite discovery patterns
    (`test_*.py` / `*_test.py`) is created or modified; the verification
    driver is named `verify_grade_school.py` to stay out of pytest collection.
