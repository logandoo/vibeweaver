# Independent Code Review — grade_school.py (A4.9 / COV-8)

Reviewer: read-only subagent (opencode task) over tests/review_diff.txt.
Trigger: behavior-semantic change (new feature from stubs; diff = grade_school.py).

## Verdict summary
- Strengths: minimal correct implementation; global duplicate rejection per
  canonical `added()` semantics; strong verification (23/23 local driver +
  20/20 independent grading harness on the hidden suite).
- Critical: none
- Important: none
- Minor (2, all deferred to memory — none block completion):
  1. grade_school.py:23 `added()` returns internal `_added` by reference;
     caller mutation could corrupt state — canonical does the same, harmless here.
  2. grade_school.py:11 `setdefault(grade, set())` eagerly builds a throwaway
     set on every call — trivial inefficiency only.

## Adjudication
- Critical/Important: none → no code changes required, no re-review needed.
- Minor 1: ruling = accept as-is (canonical parity; returning a fresh list is
  premature hardening for a read-only exercise API). Recorded in memory.
- Minor 2: ruling = accept (YAGNI; scale trivial).

Verification re-run after review: not required (no changes made). Covering tests
were already green at review time (tests/verify_green.run.log,
tests/grade_school_test.run.log, tests/harness_grade.out.json).
