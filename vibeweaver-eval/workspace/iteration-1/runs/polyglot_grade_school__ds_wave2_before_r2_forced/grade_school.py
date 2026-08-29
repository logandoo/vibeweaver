class School:
    def __init__(self):
        self._students = {}
        self._names = set()
        self._added = []

    def add_student(self, name, grade):
        if name in self._names:
            self._added.append(False)
            return False
        self._names.add(name)
        self._students.setdefault(grade, set()).add(name)
        self._added.append(True)
        return True

    def roster(self):
        return [name for grade in sorted(self._students) for name in sorted(self._students[grade])]

    def grade(self, grade_number):
        return sorted(self._students.get(grade_number, []))

    def added(self):
        return self._added
