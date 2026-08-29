---
name: Fix: Two Bucket measure() — implement BFS solution
description: Stub → working measure() via BFS shortest-path over bucket states; ValueError on unreachable; canonical 11/11 + differential sweep 1074/1074 GREEN
type: fix
date: 2026-08-29
status: ⏳
commit: 9079be5
---

# Fix: Two Bucket measure() — implement BFS solution

**Problem:** `two_bucket.py` was a stub (`def measure(...): pass`) — returned
`None` for every input; no exercise behavior implemented.

**Attempted Fix:** Breadth-first search over `(bucket_one_level,
bucket_two_level)` states. The initial state is the fill of the starting
bucket (counts as action 1); each legal transition (fill/empty/pour) costs 1
action; the forbidden state (start bucket empty + other bucket full) is
excluded from the search; on first reach of `goal` the function returns
`(actions, goal_bucket, other_liters)`, and when the finite state space is
exhausted it raises `ValueError`.

**Rejected Alternatives:**
- Number-theoretic gcd/closed-form approach — error-prone around the
  forbidden-state rule and goal-bucket determination.
- Classic fill/pour/empty alternating loop — not optimal in general
  (e.g. `(2,3,3,"one")` yields 8 actions vs the true optimum 2, so it is
  unusable as a min-move oracle).

**Files:** `two_bucket.py`

**Status:** ⏳ Pending — awaiting user confirmation. Tests GREEN: 11/11
canonical cases (9 reachable triples exact + 2 `ValueError`) and 0/1074
differential-sweep mismatches against an independent label-correcting
reference with legal-path simulation (`tb_verify/tb_green.log`, exit 0).

**A4.9 review findings (deferred Minor, no action taken):**
1. `two_bucket.py:9-10` — `initial == forbidden` guard is dead code for any
   positive-capacity input (harmless defensive guard).
2. `two_bucket.py:6` — `start_bucket` not validated; a non-`"one"` value is
   silently treated as `"two"` (outside canonical scope).
3. `two_bucket.py:11-14` — `goal == 0` would succeed via the untouched bucket
   (physically meaningless; outside canonical scope).
