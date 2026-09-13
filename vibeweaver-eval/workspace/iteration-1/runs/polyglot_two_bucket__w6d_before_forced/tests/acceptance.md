> cap=5  stall=3×

# Acceptance Criteria — two_bucket

Derived from prompt.md and the official Exercism Python two-bucket
canonical data. Each line is one checkable pass/fail assertion on `measure()`.

1. `measure(3, 5, 1, "one")` returns `(4, "one", 5)`.
2. `measure(3, 5, 1, "two")` returns `(8, "two", 3)`.
3. `measure(7, 11, 2, "one")` returns `(14, "one", 11)`.
4. `measure(7, 11, 2, "two")` returns `(18, "two", 7)`.
5. `measure(1, 3, 3, "two")` returns `(1, "two", 0)` (one-step fill hits goal).
6. `measure(2, 3, 3, "one")` returns `(2, "two", 2)`.
7. `measure(5, 1, 2, "one")` returns `(6, "one", 1)`.
8. `measure(3, 15, 9, "one")` returns `(6, "two", 0)`.
9. `measure(6, 15, 9, "one")` returns `(10, "two", 0)`.
10. `measure(6, 15, 5, "one")` raises `ValueError` (unreachable — gcd).
11. `measure(5, 7, 8, "one")` raises `ValueError` (goal larger than both buckets).
12. Return shape: goal bucket is only `"one"`/`"two"`, other liters in
    `[0, other_capacity]`, action count `>= 1`.
13. Module imports/compiles with no errors and keeps the stub signature
    `measure(bucket_one, bucket_two, goal, start_bucket)`.
