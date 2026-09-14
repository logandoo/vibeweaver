class School:
    def __init__(self):
        self._roster = {}  # grade -> list of student names
        self._added = []   # ordered list of (name, grade) tuples as added

    def add_student(self, name, grade):
        # Check if student is already in this grade
        if name in self._roster.get(grade, []):
            raise ValueError(f"Student {name} is already in grade {grade}")
        # Check if student is already in ANY grade
        for g_students in self._roster.values():
            if name in g_students:
                raise ValueError(f"Student {name} is already enrolled")
        if grade not in self._roster:
            self._roster[grade] = []
        self._roster[grade].append(name)
        self._added.append((name, grade))

    def roster(self):
        result = []
        for grade in sorted(self._roster.keys()):
            result.extend(sorted(self._roster[grade]))
        return result

    def grade(self, grade_number):
        return sorted(self._roster.get(grade_number, []))

    def added(self):
        return list(self._added)
