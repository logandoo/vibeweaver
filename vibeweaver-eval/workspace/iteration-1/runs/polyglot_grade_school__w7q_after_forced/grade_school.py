class School:
    def __init__(self):
        self._roster = {}
        self._all_students = set()

    def add_student(self, name, grade):
        if name in self._all_students:
            return False
        if grade not in self._roster:
            self._roster[grade] = []
        self._roster[grade].append(name)
        self._all_students.add(name)
        return True

    def roster(self):
        result = []
        for grade in sorted(self._roster.keys()):
            result.extend(sorted(self._roster[grade]))
        return result

    def grade(self, grade_number):
        if grade_number in self._roster:
            return sorted(self._roster[grade_number])
        return []

    def added(self):
        return list(self._all_students)
