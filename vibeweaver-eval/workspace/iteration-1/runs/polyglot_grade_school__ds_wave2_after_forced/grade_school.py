class School:
    def __init__(self):
        self._students_by_grade = {}

    def add_student(self, name, grade):
        for students in self._students_by_grade.values():
            if name in students:
                return False
        self._students_by_grade.setdefault(grade, []).append(name)
        return True

    def roster(self):
        students = []
        for grade in sorted(self._students_by_grade):
            students.extend(sorted(self._students_by_grade[grade]))
        return students

    def grade(self, grade_number):
        return sorted(self._students_by_grade.get(grade_number, []))

    def added(self):
        return [
            name
            for students in self._students_by_grade.values()
            for name in students
        ]
