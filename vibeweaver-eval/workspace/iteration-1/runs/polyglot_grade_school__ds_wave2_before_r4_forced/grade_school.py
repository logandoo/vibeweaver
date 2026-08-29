class School:
    def __init__(self):
        self._students = {}
        self._added = []

    def add_student(self, name, grade):
        for names in self._students.values():
            if name in names:
                self._added.append(False)
                return False
        self._students.setdefault(grade, set()).add(name)
        self._added.append(True)
        return True

    def roster(self):
        return [name for grade in sorted(self._students)
                for name in sorted(self._students[grade])]

    def grade(self, grade_number):
        return sorted(self._students.get(grade_number, set()))

    def added(self):
        return self._added
