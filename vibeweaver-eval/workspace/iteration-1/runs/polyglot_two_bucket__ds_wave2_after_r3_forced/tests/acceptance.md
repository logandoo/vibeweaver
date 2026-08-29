> cap=5  stall=3×

# Acceptance Criteria — two_bucket.measure (two-bucket kata)

Each criterion is a single checkable yes/no statement over observable output
(CLI transcript / return value / exit code). Source of expected values: the
canonical Exercism two-bucket specification (fetched via Context7 from
exercism/python `exercises/practice/two-bucket`).

1. measure(3, 5, 1, "one") returns (4, "one", 5)
2. measure(3, 5, 1, "two") returns (8, "two", 3)
3. measure(7, 11, 2, "one") returns (14, "one", 11) and measure(7, 11, 2, "two") returns (18, "two", 7)
4. measure(1, 3, 3, "two") returns (1, "two", 0) — goal equals start-bucket capacity → exactly 1 action
5. measure(2, 3, 3, "one") returns (2, "two", 2) — goal reached by filling the non-start bucket
6. measure(5, 1, 2, "one") returns (6, "one", 1) — start bucket much bigger than the other
7. measure(3, 15, 9, "one") returns (6, "two", 0) and measure(6, 15, 9, "one") returns (10, "two", 0) — start bucket much smaller; same goal different start
8. measure(6, 15, 5, "one") raises ValueError and measure(5, 7, 8, "one") raises ValueError — unreachable goals
9. Differential sweep: for every bucket pair (a,b) with 1<=a,b<=8 and every goal 1..a+b for both start buckets, measure() matches an independently-written reference BFS (same action count, goal bucket, other amount) on 100% of inputs
10. two_bucket.py imports cleanly and measure executes for all canonical inputs with exit code 0 (no syntax/runtime errors)
