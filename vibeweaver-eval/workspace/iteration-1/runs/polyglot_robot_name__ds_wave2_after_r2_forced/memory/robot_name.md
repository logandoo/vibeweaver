---
title: robot_name — Robot Name implementation
type: project
tier: ✅ Verified
date: 2026-08-29
---

## Summary
Implemented `robot_name.py` for the Robot Name exercise: robots get a unique
random name in the format two uppercase letters + three digits (e.g. `RX837`).

## Design
- `Robot._used_names` (class-level set) tracks every name ever assigned — never reused.
- `name` is a lazy property: generated on first access (`_generate_name`), stable across reads.
- `reset()` sets `_name = None` so the next access generates a fresh, unused name.
- Generation: `random.choice` over uppercase letters ×2 + `f"{random.randrange(1000):03d}"`,
  retry loop until the candidate is not in `_used_names` (uniqueness by construction).

## Approach choice (ADR D-3)
Chose used-set + random retry over a shuffled-permutation-of-all-676k-names
approach: simpler, idiomatic, zero memory cost; both satisfy the spec.

## Verification
- 26/26 behavior checks PASS on final tree (`tests/fresh_run.log`, exit=0): format,
  consistency, uniqueness across 500 robots, reset changes name, reset names never reused,
  varied/random names. RED evidence captured (AttributeError on stub) — TDD §A4.8.

## Pitfalls / notes
- Names must never be reused after reset (spec + canonical tests) → used-set is persistent.
- Randomness spec: names must not follow a predictable sequence → `random` module, not a counter.

## A4.9 review (2026-08-29)
APPROVE, 0 Critical/Important. Minors deferred: (1) no exhaustion guard on `_generate_name` `while True` (unreachable at realistic scale, 676k space); (2) `_used_names` unbounded for process lifetime (bounded at 676k; required by no-reuse); (3) Mersenne Twister `random` is deterministic under a fixed seed (acceptable per spec; `secrets` would break seeded determinism).
