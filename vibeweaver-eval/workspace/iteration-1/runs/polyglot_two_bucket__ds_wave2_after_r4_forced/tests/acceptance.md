> cap=5  stall=3×

# Acceptance Criteria — two_bucket.measure (Exercism two-bucket kata)

Each criterion is a single checkable yes/no statement over observable output
(return tuple / raised exception / exit code). Expected values sourced from the
official Exercism canonical data (fetched via Context7 from
exercism/problem-specifications `two-bucket/canonical-data.json`).

1. measure(3, 5, 1, "one") returns (4, "one", 5)
2. measure(3, 5, 1, "two") returns (8, "two", 3)
3. measure(7, 11, 2, "one") returns (14, "one", 11)
4. measure(7, 11, 2, "two") returns (18, "two", 7)
5. measure(1, 3, 3, "two") returns (1, "two", 0) — goal equals start-bucket capacity → exactly 1 action
6. measure(2, 3, 3, "one") returns (2, "two", 2) — goal reached by filling non-start bucket
7. measure(5, 1, 2, "one") returns (6, "one", 1) — start bucket much bigger than other
8. measure(3, 15, 9, "one") returns (6, "two", 0) and measure(6, 15, 9, "one") returns (10, "two", 0)
9. measure(6, 15, 5, "one") raises ValueError (unreachable: 5 not divisible by gcd(6,15)=3)
10. measure(5, 7, 8, "one") raises ValueError (goal > both bucket capacities)
11. Differential sweep: for every pair (a,b), 1<=a<=8, 1<=b<=8, every goal 1..a+b, both start buckets → measure() matches an independently-written reference BFS (action count, goal bucket, other amount) on 100% of inputs
12. two_bucket.py imports cleanly and measure executes for all canonical inputs with exit code 0 (no syntax/runtime errors)
