class School:
    def __init__(self):
        self._students = []
        self._roster = {}

    def add_student(self, name, grade):
        if name in self._students:
            raise ValueError("Student already added")
        self._students.append(name)
        if grade not in self._roster:
            self._roster[grade] = []
        self._roster[grade].append(name)

    def roster(self):
        result = []
        for grade in sorted(self._roster.keys()):
            result.extend(sorted(self._roster[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return list(self._students)
