class School:
    def __init__(self):
        self._roster = {}
        self._added = []

    def add_student(self, name, grade):
        if name in self._roster:
            self._added.append(False)
            return False
        self._roster[name] = grade
        self._added.append(True)
        return True

    def roster(self):
        return [
            name
            for name, _ in sorted(self._roster.items(), key=lambda item: (item[1], item[0]))
        ]

    def grade(self, grade_number):
        return sorted(
            name for name, grade in self._roster.items() if grade == grade_number
        )

    def added(self):
        return list(self._added)
