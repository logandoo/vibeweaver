class School:
    def __init__(self):
        self._grades = {}
        self._added = []

    def add_student(self, name, grade):
        already_enrolled = any(
            name in students for students in self._grades.values()
        )
        if already_enrolled:
            self._added.append(False)
            return False
        self._grades.setdefault(grade, []).append(name)
        self._added.append(True)
        return True

    def roster(self):
        return [
            name
            for grade in sorted(self._grades)
            for name in sorted(self._grades[grade])
        ]

    def grade(self, grade_number):
        return sorted(self._grades.get(grade_number, []))

    def added(self):
        return self._added
