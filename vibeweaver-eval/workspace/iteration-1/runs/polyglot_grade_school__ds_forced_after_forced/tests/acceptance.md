> cap=5  stall=3×
1. A fresh `School()` returns an empty roster: `school.roster() == []`.
2. `add_student(name, grade)` returns `True` when a student is first added.
3. `added()` returns the list of `add_student` return values in call order (e.g. `[True, True, False, True]`).
4. `roster()` returns all enrolled students sorted by grade ascending, then alphabetically by name within each grade (e.g. `["Anna","Barb","Charlie","Alex","Peter","Zoe","Jim"]`).
5. `grade(n)` returns the alphabetically sorted names of students in grade `n`, or `[]` when the grade has no students.
6. Adding the same student twice to the same grade returns `False` and does not duplicate the name in `roster()`.
7. Adding the same student to a different grade returns `False` and keeps the student only in their original grade.
8. `grade_school.py` compiles and the full hidden test suite (20 tests) passes with no syntax or runtime errors.
