class School:
    def __init__(self):
        self._roster = {}

    def add_student(self, name, grade):
        if name in self.all_students():
            return
        if grade not in self._roster:
            self._roster[grade] = []
        self._roster[grade].append(name)

    def roster(self):
        result = []
        for grade in sorted(self._roster):
            result.extend(sorted(self._roster[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return self._roster

    def all_students(self):
        students = []
        for grade_students in self._roster.values():
            students.extend(grade_students)
        return students
