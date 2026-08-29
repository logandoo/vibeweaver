> cap=5  stall=3×
1. `add_student(name, grade)` returns True when a student is newly enrolled and False when the same student is added again (to any grade).
2. `added()` returns the ordered list of results from each add_student call (e.g. `[True, True, False, True]`).
3. `roster()` returns all enrolled student names, sorted by grade ascending then name alphabetically.
4. `grade(n)` returns the names enrolled in grade n sorted alphabetically, or `[]` when no students are in that grade.
5. No student ever appears more than once in the roster or in any grade output (dedup enforced at add time).
