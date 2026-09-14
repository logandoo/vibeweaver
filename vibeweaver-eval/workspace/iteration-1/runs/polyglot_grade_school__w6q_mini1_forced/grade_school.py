class School:
    def __init__(self):
        self._students = {}
        self._added = []

    def add_student(self, name, grade):
        for students in self._students.values():
            if name in students:
                return
        if grade not in self._students:
            self._students[grade] = []
        self._students[grade].append(name)
        self._added.append((name, grade))

    def roster(self):
        result = []
        for grade in sorted(self._students.keys()):
            result.extend(sorted(self._students[grade]))
        return result

    def grade(self, grade_number):
        if grade_number not in self._students:
            return []
        return sorted(self._students[grade_number])

    def added(self):
        return list(self._added)
