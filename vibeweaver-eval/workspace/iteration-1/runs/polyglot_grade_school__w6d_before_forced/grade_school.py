class School:
    def __init__(self):
        self._roster = {}
        self._added = []
        self._names = set()

    def add_student(self, name, grade):
        if name in self._names:
            self._added.append(False)
            return
        self._names.add(name)
        self._roster.setdefault(grade, []).append(name)
        self._added.append(True)

    def roster(self):
        students = []
        for grade in sorted(self._roster):
            students.extend(sorted(self._roster[grade]))
        return students

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return list(self._added)
