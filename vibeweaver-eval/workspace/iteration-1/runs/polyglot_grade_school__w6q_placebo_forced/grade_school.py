class School:
    def __init__(self):
        self._students = {}  # grade -> list of student names
        self._all_students = set()

    def add_student(self, name, grade):
        if name in self._all_students:
            return False
        if grade not in self._students:
            self._students[grade] = []
        self._students[grade].append(name)
        self._all_students.add(name)
        return True

    def roster(self):
        result = []
        for grade in sorted(self._students.keys()):
            result.extend(sorted(self._students[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._students.get(grade_number, []))

    def added(self):
        return self._all_students.copy()
