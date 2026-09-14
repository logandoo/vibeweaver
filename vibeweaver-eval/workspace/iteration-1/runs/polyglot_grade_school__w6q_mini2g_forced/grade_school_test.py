# Public interface:
# class School
# __init__(self)
# add_student(self, name, grade)
# roster(self)
# grade(self, grade_number)
# added(self)

import pytest
from grade_school import School


def test_new_school_has_empty_roster():
    school = School()
    assert school.roster() == []


def test_adding_a_student_adds_them_to_the_roster_for_the_given_grade():
    school = School()
    school.add_student("Jim", 2)
    assert school.grade(2) == ["Jim"]


def test_adding_more_students_to_the_same_grade_adds_them_to_the_roster():
    school = School()
    school.add_student("Jim", 2)
    school.add_student("Anna", 2)
    assert school.grade(2) == ["Anna", "Jim"]


def test_adding_students_to_different_grades_adds_them_to_the_roster():
    school = School()
    school.add_student("Jim", 2)
    school.add_student("Anna", 1)
    assert school.grade(1) == ["Anna"]
    assert school.grade(2) == ["Jim"]


def test_grade_returns_the_students_in_that_grade_in_alphabetical_order():
    school = School()
    school.add_student("Blair", 2)
    school.add_student("Aimee", 2)
    school.add_student("Charlie", 2)
    assert school.grade(2) == ["Aimee", "Blair", "Charlie"]


def test_grade_returns_an_empty_list_if_there_are_no_students_in_that_grade():
    school = School()
    assert school.grade(2) == []


def test_roster_returns_all_students_in_all_grades_sorted_by_grade_then_name():
    school = School()
    school.add_student("Charlie", 1)
    school.add_student("Anna", 1)
    school.add_student("Barb", 1)
    school.add_student("Zoe", 2)
    school.add_student("Alex", 2)
    school.add_student("Peter", 2)
    school.add_student("Jim", 5)
    assert school.roster() == [
        "Anna",
        "Barb",
        "Charlie",
        "Alex",
        "Peter",
        "Zoe",
        "Jim",
    ]


def test_adding_a_student_to_a_grade_when_they_are_already_in_the_roster():
    school = School()
    school.add_student("Aimee", 2)
    assert school.add_student("Aimee", 3) is False


def test_adding_a_student_to_a_grade_when_they_are_already_in_the_same_grade():
    school = School()
    school.add_student("Aimee", 2)
    assert school.add_student("Aimee", 2) is False


@pytest.mark.skip(reason="TODO: specification does not define the behavior of added()")
def test_added():
    # TODO: specify behavior for added() based on canonical conventions if known.
    pass
