> cap=5  stall=3×

# Acceptance Criteria — grade_school.py

1. `School.add_student(name, grade)` adds a student to the given grade.
2. `School.added()` returns a list of booleans recording the success of each `add_student` call, in call order.
3. Adding a student whose name already exists (same grade or any other grade) is rejected: `add_student` returns `False` and `added()` records `False`.
4. `School.roster()` returns all students sorted by grade ascending, then by name alphabetically.
5. `School.grade(n)` returns the students in grade `n` sorted alphabetically; empty list if none.
6. Empty school: `roster()` returns `[]` and `grade(n)` returns `[]`.
