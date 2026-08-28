---
name: Fix — two_bucket measure implemented from stub
description: BFS state search over (bucket_one, bucket_two) liters for the Exercism two-bucket exercise; returns (moves, goal_bucket, other_liters), raises ValueError on impossible goals. All canonical behavior verified.
type: fix
date: 2026-08-29
status: ✅
commit: pending
---

# Fix: two_bucket measure implemented from stub

**Problem:** `two_bucket.py` shipped as a `measure(...)` `pass` stub (Exercism
two-bucket). Task: return `(actions, goal_bucket, other_liters)` for the
minimal number of actions to measure `goal` liters, starting by filling
`start_bucket`, honoring the forbidden-state rule.

**Solution (validated):** BFS over `(a, b)` = (bucket_one liters, bucket_two
liters). Initial state = fill the start bucket (1 action). Six candidate
moves per state: fill/empty each bucket, pour one→two / two→one (pour stops
at source-empty or target-full). Skip a move that lands on a state where the
start bucket is empty AND the other bucket is full (rule 3). First state
whose `a == goal` or `b == goal` wins → minimal actions. Exhausted queue →
`ValueError` (unreachable goal, e.g. goal not divisible by gcd, or goal larger
than both buckets).

**Key semantics (verified):**
- One-step case when goal == start bucket capacity: e.g.
  `measure(1, 3, 3, "two") == (1, "two", 0)`.
- Goal equal to the OTHER bucket's capacity is reachable in 2 moves by
  filling it second: `measure(2, 3, 3, "one") == (2, "two", 2)`.
- Start bucket is empty in the final "other" reading only when the goal lands
  in the OTHER bucket; final states are not otherwise restricted.

**Evidence:** RED 1/13 (stub) → GREEN 13/13 acceptance (canonical 11 cases +
sanity); differential sweep 1050/1050 vs independent BFS oracle (bucket sizes
1..9); official exercism/python `two_bucket_test.py` 11/11 in an isolated
graded copy.

**A4.9 independent review (commit c75d763):** verdict `ready` — no
Critical/Important. Four Minors adjudicated as no-change (all non-defects):
(1) `forbidden()` re-branches on `start_bucket` per call — stylistic, kept for
clarity; (2) no input validation for `start_bucket`/capacities — contract only
specifies valid canonical inputs; (3) forbidden filter precedes goal checks —
matches the stated rule, goal stays reachable via non-forbidden paths
(sweep-confirmed); (4) no tie-break if both buckets simultaneously hold the
goal — no canonical case exercises it. BFS worst case explores all
(cap1+1)*(cap2+1) states — fine for canonical sizes; no early gcd
short-circuit; `seen` set retained for the whole search (memory trivial here).
