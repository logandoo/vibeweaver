# Two Bucket — Acceptance Criteria

> cap=5  stall=3×

Acceptance criteria (one criterion = one yes/no sentence). Expected values come from the Exercism `two-bucket` canonical-data.json and the Python track's `two_bucket_test.py`.

1. `measure(3, 5, 1, "one")` returns `(4, "one", 5)`.
2. `measure(3, 5, 1, "two")` returns `(8, "two", 3)`.
3. `measure(7, 11, 2, "one")` returns `(14, "one", 11)`.
4. `measure(7, 11, 2, "two")` returns `(18, "two", 7)`.
5. `measure(1, 3, 3, "two")` returns `(1, "two", 0)`.
6. `measure(2, 3, 3, "one")` returns `(2, "two", 2)`.
7. `measure(5, 1, 2, "one")` returns `(6, "one", 1)`.
8. `measure(3, 15, 9, "one")` returns `(6, "two", 0)`.
9. `measure(6, 15, 5, "one")` raises `ValueError` (goal unreachable).
10. `measure(6, 15, 9, "one")` returns `(10, "two", 0)`.
11. `measure(5, 7, 8, "one")` raises `ValueError` (goal > both bucket capacities).
