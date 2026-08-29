> cap=5  stall=3×

# Acceptance Criteria — Two Bucket (two_bucket.py)

Each criterion is independently checkable via an executed test against
`measure(bucket_one, bucket_two, goal, start_bucket)` (returns
`(moves, goal_bucket, other_bucket)`, raises `ValueError` when impossible).

1. Module `two_bucket` imports without syntax or import errors.
2. `measure(3, 5, 1, "one") == (4, "one", 5)` — start bucket one.
3. `measure(3, 5, 1, "two") == (8, "two", 3)` — start bucket two.
4. `measure(7, 11, 2, "one") == (14, "one", 11)`.
5. `measure(7, 11, 2, "two") == (18, "two", 7)`.
6. `measure(1, 3, 3, "two") == (1, "two", 0)` — goal reached in one step.
7. `measure(2, 3, 3, "one") == (2, "two", 2)` — fill other bucket mid-flow.
8. `measure(5, 1, 2, "one") == (6, "one", 1)` — bucket one much bigger.
9. `measure(3, 15, 9, "one") == (6, "two", 0)` — bucket one much smaller.
10. `measure(6, 15, 9, "one") == (10, "two", 0)` — same buckets, different goal.
11. `measure(6, 15, 5, "one")` raises `ValueError` (unreachable goal).
12. `measure(5, 7, 8, "one")` raises `ValueError` (goal larger than both buckets).
13. No solution path reaches a state where the starting bucket is empty and the
    other bucket is full (canonical forbidden-state rule; verified through the
    canonical expected move-counts/values above, which depend on it).
