class School:
    def __init__(self):
        self._roster = {}
        self._added = []

    def add_student(self, name, grade):
        if any(name in students for students in self._roster.values()):
            self._added.append(False)
            return
        self._roster.setdefault(grade, []).append(name)
        self._added.append(True)

    def roster(self):
        return [
            name
            for grade in sorted(self._roster)
            for name in sorted(self._roster[grade])
        ]

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return list(self._added)
