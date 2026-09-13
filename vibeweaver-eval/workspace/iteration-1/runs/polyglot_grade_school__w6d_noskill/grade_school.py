class School:
    def __init__(self):
        self._roster = {}
        self._added = []

    def add_student(self, name, grade):
        success = True
        for students in self._roster.values():
            if name in students:
                success = False
                break
        if success:
            self._roster.setdefault(grade, []).append(name)
        self._added.append(success)

    def roster(self):
        result = []
        for grade in sorted(self._roster):
            result.extend(sorted(self._roster[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return self._added
