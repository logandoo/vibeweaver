class School:
    def __init__(self):
        self._students = {}
        self._added = []

    def add_student(self, name, grade):
        if name in self._students:
            self._added.append(False)
            return False
        self._students[name] = grade
        self._added.append(True)
        return True

    def roster(self):
        by_grade = {}
        for name, grade in self._students.items():
            by_grade.setdefault(grade, []).append(name)
        return [name for grade in sorted(by_grade) for name in sorted(by_grade[grade])]

    def grade(self, grade_number):
        return sorted(name for name, grade in self._students.items() if grade == grade_number)

    def added(self):
        return list(self._added)
