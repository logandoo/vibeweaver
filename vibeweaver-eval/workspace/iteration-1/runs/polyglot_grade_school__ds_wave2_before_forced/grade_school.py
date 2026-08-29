class School:
    def __init__(self):
        self._students = []
        self._added = []

    def add_student(self, name, grade):
        if any(student == name for student, _ in self._students):
            self._added.append(False)
            return False
        self._students.append((name, grade))
        self._added.append(True)
        return True

    def roster(self):
        return [name for name, _ in sorted(self._students, key=lambda s: (s[1], s[0]))]

    def grade(self, grade_number):
        return [name for name, grade in sorted(self._students, key=lambda s: s[0]) if grade == grade_number]

    def added(self):
        return list(self._added)
