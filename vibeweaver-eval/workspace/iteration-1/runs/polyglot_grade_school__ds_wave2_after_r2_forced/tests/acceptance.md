> cap=5  stall=3×

1. `School()` constructs an empty roster: `roster()` returns `[]`.
2. `add_student(name, grade)` records `True` in `added()` for each new student.
3. `roster()` returns all added students as a flat list sorted by grade (1,2,3...) then alphabetically by name.
4. `grade(grade_number)` returns the alphabetically sorted list of students in that grade, or `[]` if none.
5. Adding the same student again (same grade or different grade) records `False` in `added()` and does not duplicate the student in the roster/grade.
6. `added()` returns the recorded `True`/`False` history and resets its buffer.
