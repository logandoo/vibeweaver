> cap=5  stall=3×

# Two Bucket — Acceptance Criteria

1. `measure(3, 5, 1, "one")` returns `(4, "one", 5)`.
2. `measure(3, 5, 1, "two")` returns `(8, "two", 3)`.
3. `measure(7, 11, 2, "one")` returns `(14, "one", 11)`.
4. `measure(7, 11, 2, "two")` returns `(18, "two", 7)`.
5. `measure(1, 3, 3, "two")` returns `(1, "two", 0)`.
6. `measure(2, 3, 3, "one")` returns `(2, "two", 2)`.
7. `measure(6, 15, 5, "one")` raises `ValueError` (goal not reachable).
8. `two_bucket.py` imports cleanly and runs with no syntax/runtime errors.
