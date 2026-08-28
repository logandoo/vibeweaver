---
title: two-bucket BFS solution
type: reference
status: verified
tags: [two-bucket, bfs, exercism, water-jug]
date: 2026-08-29
---

# two-bucket: BFS solution (validated)

## Context
Exercism "two-bucket": given two bucket sizes + goal + which bucket to fill
first, return `(moves, goal_bucket, other_liters)`, raising `ValueError` when
unreachable. Constraints: only fill / empty / pour-until-full-or-empty; never
arrive at a state where the **starting** bucket is empty and the **other**
bucket is full; first fill of the starting bucket counts as 1 action.

## Solution (verified 11/11 canonical cases, Exercism canonical-data.json)
BFS over `(bucket_one, bucket_two)` states:
- forbidden state = starting bucket empty + other bucket full (only the
  `other_index` slot set to its capacity — start amount stays 0).
- start state = starting bucket filled, count = 1; pre-check goal in start
  bucket returns `(1, start_bucket, 0)`.
- check goal on generated neighbors BEFORE enqueue (preserves minimal count);
  unreachable → `ValueError("impossible")` after state space exhausts.
- `neighbors()` yields the 6 transitions; self-loops absorbed by `visited`.

## Independent review (A4.9, ses_fb6dc8655ffe9w7arkpkG4TUj0)
Verdict APPROVE; 0 Critical, 0 Important. Minors deferred (non-blocking):
1. If both buckets hit the goal simultaneously, `"one"` wins unconditionally
   (`two_bucket.py:28`) — Exercism's "prefer starting bucket" tie rule not
   honored for `start_bucket == "two"`. No canonical test exercises it.
2. Non-`"one"` `start_bucket` silently maps to `"two"`; no input validation.
3. `neighbors` defined after `measure` (readability); forbidden-state block
   worth a comment.
4. BFS is O((cap1+1)×(cap2+1)) with no gcd unreachability shortcut — fine for
   canonical sizes.
