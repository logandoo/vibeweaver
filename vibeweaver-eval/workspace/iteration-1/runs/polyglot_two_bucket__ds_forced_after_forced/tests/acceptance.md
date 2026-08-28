> cap=5  stall=3×

# Acceptance Criteria — two_bucket

Behavioral criteria derived from prompt.md and the official Exercism Python
two-bucket test suite (exercism/python `two_bucket_test.py`, generated from
problem-specifications `canonical-data.json`, fetched 2026-08-29). Each
criterion is a single checkable pass/fail assertion against `measure()`.

1. `measure(3, 5, 1, "one")` returns `(4, "one", 5)` (start bucket one, goal 1).
2. `measure(3, 5, 1, "two")` returns `(8, "two", 3)` (start bucket two, goal 1).
3. `measure(7, 11, 2, "one")` returns `(14, "one", 11)`.
4. `measure(7, 11, 2, "two")` returns `(18, "two", 7)`.
5. `measure(1, 3, 3, "two")` returns `(1, "two", 0)` (one-step: fill start bucket two hits goal immediately).
6. `measure(2, 3, 3, "one")` returns `(2, "two", 2)` (goal equals other bucket capacity, start bucket one).
7. `measure(5, 1, 2, "one")` returns `(6, "one", 1)` (bucket one much bigger; repeated pour no-refill).
8. `measure(3, 15, 9, "one")` returns `(6, "two", 0)` (bucket one much smaller).
9. `measure(6, 15, 5, "one")` raises `ValueError` (goal not reachable — gcd constraint).
10. `measure(6, 15, 9, "one")` returns `(10, "two", 0)` (same buckets, reachable goal).
11. `measure(5, 7, 8, "one")` raises `ValueError` (goal larger than both buckets).
12. Returned `goal_bucket` is only ever `"one"` or `"two"`; `other_liters` is never negative and never exceeds the other bucket's capacity; actions count ≥ 1.
13. Module imports and compiles with no syntax/runtime errors; `measure` keeps the stub signature `measure(bucket_one, bucket_two, goal, start_bucket)`.
