class School:
    def __init__(self):
        self._grades = {}
        self._added = []

    def add_student(self, name, grade):
        if any(name in students for students in self._grades.values()):
            self._added.append(False)
            return False
        self._grades.setdefault(grade, []).append(name)
        self._added.append(True)
        return True

    def roster(self):
        result = []
        for grade in sorted(self._grades):
            result.extend(sorted(self._grades[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._grades.get(grade_number, []))

    def added(self):
        return list(self._added)
