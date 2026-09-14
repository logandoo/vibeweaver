"""Deterministic tests for the grade school roster exercise.

Each test maps to one requirement from prompt.md.
Expected values are copied directly from the spec's own examples.
"""
import pytest
from grade_school import School


class TestAddStudent:
    """Add a student's name to the roster for a grade."""

    def test_add_student(self):
        school = School()
        school.add_student("Jim", 2)
        assert school.grade(2) == ["Jim"]


class TestGetGradeList:
    """Get a list of all students enrolled in a grade."""

    def test_empty_grade(self):
        school = School()
        assert school.grade(2) == []

    def test_single_student(self):
        school = School()
        school.add_student("Jim", 2)
        assert school.grade(2) == ["Jim"]

    def test_multiple_students_same_grade(self):
        school = School()
        school.add_student("Barb", 1)
        school.add_student("Anna", 1)
        school.add_student("Charlie", 1)
        assert school.grade(1) == ["Anna", "Barb", "Charlie"]


class TestGetFullRoster:
    """Get a sorted list of all students in all grades.
    Grades sort 1, 2, 3, etc. Students within a grade sort alphabetically.
    """

    def test_empty_roster(self):
        school = School()
        assert school.roster() == []

    def test_full_example_from_spec(self):
        school = School()
        school.add_student("Jim", 5)
        school.add_student("Zoe", 2)
        school.add_student("Peter", 2)
        school.add_student("Alex", 2)
        school.add_student("Charlie", 1)
        school.add_student("Barb", 1)
        school.add_student("Anna", 1)
        # Spec says: "Anna, Barb, Charlie, Alex, Peter, Zoe and Jim"
        assert school.roster() == ["Anna", "Barb", "Charlie", "Alex", "Peter", "Zoe", "Jim"]


class TestDuplicatePrevention:
    """Each student cannot be added more than once to a grade or the roster.
    When a test attempts to add the same student more than once, indicate that this is incorrect.
    """

    def test_duplicate_in_same_grade(self):
        school = School()
        school.add_student("Jim", 2)
        result = school.add_student("Jim", 2)
        assert result is False
        assert school.grade(2) == ["Jim"]

    def test_duplicate_in_different_grade(self):
        school = School()
        school.add_student("Jim", 2)
        result = school.add_student("Jim", 5)
        assert result is False
        assert school.grade(2) == ["Jim"]
        assert school.grade(5) == []


class TestAddedMethod:
    """The added() method returns all students that have been added (sorted roster)."""

    def test_added_empty(self):
        school = School()
        assert school.added() == []

    def test_added_with_students(self):
        school = School()
        school.add_student("Jim", 5)
        school.add_student("Zoe", 2)
        school.add_student("Alex", 2)
        school.add_student("Anna", 1)
        assert school.added() == ["Anna", "Alex", "Zoe", "Jim"]
