> cap=5  stall=3×
1. School() constructs without error.
2. add_student(name, grade) accepts keyword arguments and returns True on a successful add.
3. Adding the same name twice (same grade or a different grade) returns False and leaves the roster unchanged.
4. added() returns the list of boolean results of every add attempt, in order (e.g. [True, True, False, True]).
5. grade(grade_number) returns the alphabetically-sorted list of students in that grade, or [] when empty.
6. roster() returns all students sorted ascending by grade, then alphabetically by name, with no duplicates, or [] when empty.
