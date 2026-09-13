---
type: project
topic: two_bucket
updated: 2026-09-14
---

# Two Bucket — solution memory

## ✅ Verified
- `measure(bucket_one, bucket_two, goal, start_bucket)` implemented as BFS over
  states `(one, two)`; initial state is the first fill of `start_bucket`, moves
  counted from 1. Returns `(moves, "one"|"two", other_liters)`.
- Forbidden state after any action: start bucket empty AND other bucket full.
- Impossible goals exhaust the queue → `ValueError` with a message.
- All 11 canonical `problem-specifications` cases pass (see
  `tests/verification_log.md`); `py_compile` clean.
- Independent A4.9 review: correct BFS minimality, correct forbidden rule,
  correct pour math, no security concerns.

## ⏳ Known limitation (adjudicated, not a canonical failure)
- When BOTH buckets can hold `goal` at the same minimal move count, the
  reported bucket is decided by fixed successor ordering (fill-one, fill-two,
  empty-one, empty-two, pour-one→two, pour-two→one). The exercise spec does not
  define a tie-break and canonical data never exercises it. Left as-is to avoid
  diverging from the reference suite.
- Input validation (invalid `start_bucket`, negative/zero capacities, `goal<=0`)
  is not implemented; the Python exercise does not require it.

## ⛔ Forbidden
- Do not add comments to `two_bucket.py` (project convention / skill rule).
