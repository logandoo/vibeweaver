class School:
    def __init__(self):
        self._students = {}
        self._added_log = []

    def add_student(self, name, grade):
        if name in self._students:
            self._added_log.append(False)
            return False
        self._students[name] = grade
        self._added_log.append(True)
        return True

    def roster(self):
        result = []
        for grade_num in sorted(set(self._students.values())):
            students_in_grade = sorted(
                name for name, g in self._students.items() if g == grade_num
            )
            result.extend(students_in_grade)
        return result

    def grade(self, grade_number):
        students = sorted(
            name for name, g in self._students.items() if g == grade_number
        )
        return students

    def added(self):
        return list(self._added_log)
