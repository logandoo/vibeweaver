import pytest
from grade_school import School


def test_empty_roster():
    school = School()
    assert school.roster() == []


def test_empty_grade():
    school = School()
    assert school.grade(1) == []


def test_empty_added():
    school = School()
    assert school.added() == []


def test_add_jim_to_grade_2():
    school = School()
    school.add_student("Jim", 2)
    assert school.grade(2) == ["Jim"]
    assert school.roster() == ["Jim"]
    assert school.added() == ["Jim"]


def test_add_multiple_students_same_grade():
    school = School()
    school.add_student("Aimee", 2)
    school.add_student("Bea", 2)
    assert school.roster() == ["Aimee", "Bea"]
    assert school.grade(2) == ["Aimee", "Bea"]
    assert school.added() == ["Aimee", "Bea"]


def test_add_students_different_grades():
    school = School()
    school.add_student("Aimee", 2)
    school.add_student("Bea", 3)
    assert school.roster() == ["Aimee", "Bea"]
    assert school.grade(2) == ["Aimee"]
    assert school.grade(3) == ["Bea"]
    assert school.added() == ["Aimee", "Bea"]


def test_grade_sorted_alphabetically():
    school = School()
    school.add_student("Bea", 2)
    school.add_student("Aimee", 2)
    school.add_student("Zoe", 1)
    school.add_student("Alex", 2)
    assert school.grade(2) == ["Aimee", "Alex", "Bea"]
    assert school.grade(1) == ["Zoe"]


def test_roster_sorted_by_grade_then_name():
    school = School()
    school.add_student("Bea", 2)
    school.add_student("Aimee", 2)
    school.add_student("Zoe", 1)
    school.add_student("Alex", 2)
    assert school.roster() == ["Zoe", "Aimee", "Alex", "Bea"]


def test_roster_example_from_spec():
    school = School()
    school.add_student("Anna", 1)
    school.add_student("Barb", 1)
    school.add_student("Charlie", 1)
    school.add_student("Alex", 2)
    school.add_student("Peter", 2)
    school.add_student("Zoe", 2)
    school.add_student("Jim", 5)
    assert school.roster() == ["Anna", "Barb", "Charlie", "Alex", "Peter", "Zoe", "Jim"]
    assert school.grade(1) == ["Anna", "Barb", "Charlie"]
    assert school.grade(2) == ["Alex", "Peter", "Zoe"]
    assert school.grade(5) == ["Jim"]
    assert school.added() == ["Anna", "Barb", "Charlie", "Alex", "Peter", "Zoe", "Jim"]


def test_added_returns_insertion_order():
    school = School()
    school.add_student("Bea", 2)
    school.add_student("Aimee", 2)
    school.add_student("Zoe", 1)
    assert school.added() == ["Bea", "Aimee", "Zoe"]


def test_add_duplicate_same_grade_raises_error():
    school = School()
    school.add_student("Aimee", 2)
    with pytest.raises(ValueError):
        school.add_student("Aimee", 2)


def test_add_duplicate_different_grade_raises_error():
    school = School()
    school.add_student("Aimee", 2)
    with pytest.raises(ValueError):
        school.add_student("Aimee", 3)
