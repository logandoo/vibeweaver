class School:
    def __init__(self):
        self._students = {}
        self._all_students = set()

    def add_student(self, name, grade):
        if name in self._all_students:
            return False
        self._all_students.add(name)
        if grade not in self._students:
            self._students[grade] = []
        self._students[grade].append(name)
        self._students[grade].sort()
        return True

    def roster(self):
        result = []
        for grade_num in sorted(self._students.keys()):
            result.extend(self._students[grade_num])
        return result

    def grade(self, grade_number):
        return sorted(self._students.get(grade_number, []))

    def added(self):
        return sorted(self._all_students)
