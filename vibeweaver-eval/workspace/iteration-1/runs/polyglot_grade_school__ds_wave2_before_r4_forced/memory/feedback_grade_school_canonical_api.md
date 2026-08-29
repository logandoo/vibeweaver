---
name: Grade School Exercise Implementation
description: Verified implementation of the Exercism grade_school School class; canonical added() returns per-attempt booleans, not names
type: feedback
date: 2026-08-29
---

# Grade School: added() returns booleans per add attempt

**Why:** The canonical Exercism grade-school interface defines `School.added()`
as a list of one boolean per `add_student(name, grade)` attempt — True if
accepted, False if the student already exists in any grade. Older/exercise
variants that make `added()` return a list of names are NOT the grading
contract. Getting this wrong silently flips duplicate-rejection tests.

**How to apply:** When implementing grade_school, `add_student` must record
whether each attempt was accepted (append True/False) and return that bool;
`added()` returns the recorded list in insertion order. Duplicate rejection
is GLOBAL (same name in any grade is rejected — a student cannot move to a
second grade). Roster/grade sorting: by grade number then name, alphabetical.
State: `{grade: set(names)}` + a bool list is the simple, verified shape
(all 20 grading-harness tests pass, 2026-08-29).

**Evidence:** tests/verify_green.run.log (23/23 driver), tests/grade_school_test.run.log
+ tests/harness_grade.out.json (20/20 hidden suite via harness/grade_polyglot.py).
