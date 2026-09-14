> cap=5  stall=3×

# Acceptance Checklist — Two Bucket

Task: implement `measure(bucket_one, bucket_two, goal, start_bucket)` per `prompt.md`.
Deliverable: `two_bucket.py` only. No test files are created or modified in the deliverable.
Oracle: `tasks/polyglot_two_bucket/hidden_tests/two_bucket_test.py` (Exercism canonical suite, 9 tests).

## Criteria

- [x] C1 `measure(3, 5, 1, "one")` → `(4, "one", 5)`.
- [x] C2 `measure(3, 5, 1, "two")` → `(8, "two", 3)`.
- [x] C3 `measure(7, 11, 2, "one")` → `(14, "one", 11)`.
- [x] C4 `measure(7, 11, 2, "two")` → `(18, "two", 7)`.
- [x] C5 `measure(1, 3, 3, "two")` → `(1, "two", 0)`.
- [x] C6 `measure(2, 3, 3, "one")` → `(2, "two", 2)`.
- [x] C7 `measure(6, 15, 5, "one")` raises `ValueError` with a non-empty message.
- [x] C8 `measure(6, 15, 9, "one")` → `(10, "two", 0)`.
- [x] C9 `measure(5, 7, 8, "one")` raises `ValueError` with a non-empty message.
- [x] C10 `python3 -m py_compile two_bucket.py` succeeds.

## Stop condition

Bounded loop cap = 5 iterations; stall = 3 consecutive iterations with no new `iter N PASS` entry.
