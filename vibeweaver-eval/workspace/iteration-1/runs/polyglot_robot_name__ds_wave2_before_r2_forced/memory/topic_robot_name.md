---
type: fix
topic: robot_name
status: verified
date: 2026-08-29
---

# ✅ robot_name: Robot factory settings implementation

## Verified approach
- `Robot` uses a class-level `_used_names` set + random retry loop for global uniqueness.
- Lazy generation: `name` is a property; `_name = None` until first access (and after `reset()`).
- Format: two `random.choice(string.ascii_uppercase)` (letters may repeat) + `f"{random.randint(0,999):03d}"` (zero-padded).
- Names are never removed from `_used_names` on reset (conservative uniqueness; old names never reappear).
- Verified 10/10 checks PASS (format, stability, distinctness, reset, 1000-robot uniqueness) — see tests/verify_run.log. A4.9 independent review APPROVE.

## Deferred minors (accepted, non-test-reachable)
- ❌/✅ No exhaustion guard if all 676,000 names are claimed — infinite loop theoretical; not reachable in tests.
- Names permanently held in `_used_names` — slight memory growth, intentional.
