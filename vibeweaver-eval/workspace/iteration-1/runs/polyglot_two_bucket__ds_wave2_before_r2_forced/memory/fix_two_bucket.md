---
name: Fix: Implement two_bucket measure()
description: Implement Exercism two-bucket measure() via BFS state-space search; returns (moves, goal_bucket, other_bucket), ValueError on impossible
type: fix
date: 2026-08-29
status: ⏳
commit: 0d632b3
---

# Fix: Implement two_bucket measure()

**Problem:** `two_bucket.py` was a stub (`pass`); needed a working `measure(bucket_one, bucket_two, goal, start_bucket)` per prompt.md (Exercism two-bucket).

**Attempted Fix:** BFS over `(v1, v2)` states. Actions: fill/empty either bucket, pour either direction. Initial state = starting bucket filled (counts as 1 move). Prune the canonical forbidden state (after an action: starting bucket empty AND other bucket full). First state with either bucket == goal returns `(moves, goal_bucket, other_bucket)`; BFS exhausts → raise `ValueError`.

**Rejected Alternatives:**
- Deterministic alternating fill/pour sequence: error-prone around the start-bucket forbidden-state rule; not guaranteed minimal; rejected for BFS.
- Mathematical/Bézout closed-form: complex to make correct against all canonical edge cases; rejected.

**Files:** `two_bucket.py`

**Verification:** 11/11 canonical cases pass (tests/verify_run.log); 1408-case differential sweep vs complete independent BFS reference (584 reachable-both, 824 unreachable-both), 0 mismatches (tests/differential_run.log); `py_compile` clean; module run exits 0.

**A4.9 review (tests/review_package.md):** PASS (minors only), 0 Critical/Important.
- Deferred minors (no action required, outside contract):
  - Minor 1 — `start_bucket` values other than `"one"` silently map to bucket two (no validation).
  - Minor 2 — `goal == 0` short-circuits as reachable in 1 move (returns `(1, start_bucket, 0)`).
  - Minor 3 — at `goal == 0` with state `(0,0)`, tie-break returns goal_bucket `"one"` unconditionally.
- Minor 4 (differential reference guard excluded most sweep cases): FIXED — sweep reference rewritten as structurally independent complete BFS; re-run: 1408 cases, 0 mismatches (evidence strengthened).

**Status:** ⏳ Pending — awaiting user/harness confirmation (hidden grading runs externally)
