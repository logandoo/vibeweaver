class School:
    def __init__(self):
        self._students = {}
        self._all_names = set()
        self._added_results = []

    def add_student(self, name, grade):
        if name in self._all_names:
            self._added_results.append(False)
            return False
        self._all_names.add(name)
        self._students.setdefault(grade, set()).add(name)
        self._added_results.append(True)
        return True

    def roster(self):
        return [name for grade in sorted(self._students)
                for name in sorted(self._students[grade])]

    def grade(self, grade_number):
        return sorted(self._students.get(grade_number, []))

    def added(self):
        return list(self._added_results)
