class School:
    def __init__(self):
        self._grades = {}
        self._all_students = set()

    def add_student(self, name, grade):
        if name in self._all_students:
            return False
        self._all_students.add(name)
        if grade not in self._grades:
            self._grades[grade] = []
        self._grades[grade].append(name)
        self._grades[grade].sort()
        return True

    def roster(self):
        result = []
        for grade_num in sorted(self._grades.keys()):
            result.extend(self._grades[grade_num])
        return result

    def grade(self, grade_number):
        return sorted(self._grades.get(grade_number, []))

    def added(self):
        return self.roster()
