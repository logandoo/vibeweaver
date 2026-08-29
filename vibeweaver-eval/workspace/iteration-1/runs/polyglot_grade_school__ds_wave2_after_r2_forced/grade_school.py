class School:
    def __init__(self):
        self.students = {}
        self._added = []

    def add_student(self, name, grade):
        if name in self.students:
            self._added.append(False)
        else:
            self.students[name] = grade
            self._added.append(True)

    def roster(self):
        by_grade = {}
        for name, grade in self.students.items():
            by_grade.setdefault(grade, []).append(name)
        result = []
        for grade in sorted(by_grade):
            result.extend(sorted(by_grade[grade]))
        return result

    def grade(self, grade_number):
        return sorted(
            name for name, grade in self.students.items() if grade == grade_number
        )

    def added(self):
        result = self._added[:]
        self._added = []
        return result
