class School:
    def __init__(self):
        self._students = []  # list of (name, grade) in insertion order
        self._names = set()   # for O(1) duplicate detection

    def add_student(self, name, grade):
        if name in self._names:
            raise ValueError(f"Student {name} already exists")
        self._students.append((name, grade))
        self._names.add(name)

    def roster(self):
        return [name for name, grade in sorted(self._students, key=lambda x: (x[1], x[0]))]

    def grade(self, grade_number):
        return sorted([name for name, grade in self._students if grade == grade_number])

    def added(self):
        return [name for name, grade in self._students]
