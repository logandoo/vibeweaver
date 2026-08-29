"""Verification driver for grade_school.py (vibeweaver C7 non-web library).

Deliberately NOT named test_*.py / *_test.py so it stays out of the
exercise test-suite's pytest collection (task constraint: do not create or
modify the exercise's test files). This driver exercises the public API and
prints a per-check verdict; exit code 0 = all checks pass.

Checks map 1:1 to tests/acceptance.md criteria 1-12, and mirror the
canonical Exercism grade-school test cases (grade_school_test.py).
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grade_school import School


def check(name, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run():
    ok = True

    # C1: empty roster
    s = School()
    ok &= check("C1 roster empty", s.roster() == [])

    # C2 + C3: add a student, added() records True, roster shows student
    s = School()
    s.add_student(name="Aimee", grade=2)
    ok &= check("C2 added True on first add", s.added() == [True])
    ok &= check("C3 student in roster", s.roster() == ["Aimee"])

    # C4: multiple students same grade, all accepted
    s = School()
    s.add_student(name="Blair", grade=2)
    s.add_student(name="James", grade=2)
    s.add_student(name="Paul", grade=2)
    ok &= check("C4 added three Trues", s.added() == [True, True, True])
    ok &= check("C4 three in roster", s.roster() == ["Blair", "James", "Paul"])

    # C5: duplicate in SAME grade rejected
    s = School()
    s.add_student(name="Blair", grade=2)
    s.add_student(name="James", grade=2)
    s.add_student(name="James", grade=2)
    s.add_student(name="Paul", grade=2)
    ok &= check("C5 same-grade dup added", s.added() == [True, True, False, True])
    ok &= check("C5 same-grade dup roster", s.roster() == ["Blair", "James", "Paul"])
    ok &= check("C5 same-grade dup grade-list",
                s.grade(2) == ["Blair", "James", "Paul"])

    # C6: same student in a DIFFERENT grade rejected
    s = School()
    s.add_student(name="Blair", grade=2)
    s.add_student(name="James", grade=2)
    s.add_student(name="James", grade=3)
    s.add_student(name="Paul", grade=3)
    ok &= check("C6 cross-grade dup added", s.added() == [True, True, False, True])
    ok &= check("C6 cross-grade keeps first", s.grade(2) == ["Blair", "James"])
    ok &= check("C6 cross-grade other", s.grade(3) == ["Paul"])

    # C7: sorted by grade then name
    s = School()
    s.add_student(name="Jim", grade=3)
    s.add_student(name="Peter", grade=2)
    s.add_student(name="Anna", grade=1)
    ok &= check("C7 sorted by grade", s.roster() == ["Anna", "Peter", "Jim"])

    # C8: sorted by name within a grade
    s = School()
    s.add_student(name="Peter", grade=2)
    s.add_student(name="Zoe", grade=2)
    s.add_student(name="Alex", grade=2)
    ok &= check("C8 sorted by name", s.roster() == ["Alex", "Peter", "Zoe"])

    # C8 full canonical: grades and then names
    s = School()
    for name, grade in [("Peter", 2), ("Anna", 1), ("Barb", 1), ("Zoe", 2),
                        ("Alex", 2), ("Jim", 3), ("Charlie", 1)]:
        s.add_student(name=name, grade=grade)
    ok &= check("C8 grade+name full sort",
                s.roster() == ["Anna", "Barb", "Charlie", "Alex", "Peter", "Zoe", "Jim"])

    # C9: grade() per-grade lists, sorted, empty when none
    s = School()
    ok &= check("C9 grade empty-roster", s.grade(1) == [])
    s.add_student(name="Peter", grade=2)
    s.add_student(name="Zoe", grade=2)
    s.add_student(name="Alex", grade=2)
    s.add_student(name="Jim", grade=3)
    ok &= check("C9 grade missing-grade", s.grade(1) == [])
    ok &= check("C9 grade list sorted", s.grade(2) == ["Alex", "Peter", "Zoe"])
    s = School()
    s.add_student(name="Franklin", grade=5)
    s.add_student(name="Bradley", grade=5)
    s.add_student(name="Jeff", grade=1)
    ok &= check("C9 grade sorted-by-name", s.grade(5) == ["Bradley", "Franklin"])

    # C10: added() order across grades
    s = School()
    s.add_student(name="Chelsea", grade=3)
    s.add_student(name="Logan", grade=7)
    ok &= check("C10 added multi-grade", s.added() == [True, True])
    ok &= check("C10 roster multi-grade", s.roster() == ["Chelsea", "Logan"])

    # C11: import cleanliness is implied by the top-level import; edge cases
    s = School()
    ok &= check("C11 fresh roster empty", s.roster() == [])
    ok &= check("C11 fresh grade empty", s.grade(99) == [])

    # C12: no grader test files created (static check of tree)
    testfiles = glob.glob("test_*.py") + glob.glob("*_test.py")
    ok &= check("C12 no grader test files",
                not testfiles, f"found={testfiles}" if testfiles else "none")

    print(f"\nRESULT: {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    run()
