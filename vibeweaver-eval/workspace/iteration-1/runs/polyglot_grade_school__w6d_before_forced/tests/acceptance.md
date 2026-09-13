> cap=5  stall=3×

1. `School()` with no students returns `[]` from `roster()`.
2. `add_student(name, grade)` records `True` in `added()` on first insertion.
3. Adding the same name to the same grade twice records `False` the second time and does not duplicate the roster.
4. Adding the same name to a different grade records `False` and does not enroll it there (global uniqueness).
5. `roster()` returns all students sorted by grade ascending, then by name alphabetically.
6. `grade(n)` returns students in grade `n` sorted alphabetically, `[]` when none.
7. `added()` returns the per-call boolean history in insertion order.
