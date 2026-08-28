---
type: project
topic: robot-name-exercise
trust: verified
created: 2026-08-29
---

# Robot Name exercise — spec + approach (✅ Verified)

## Spec (from prompt.md)
- A robot gets a random name on first "turn on" (i.e. at construction, per the Python-track test interface): two uppercase letters + three digits (e.g. `RX837`, `BC811`).
- `reset()` wipes the name; the next `name` read returns a new random name.
- Names must be random (not a predictable sequence) and unique across all existing robots.

## Chosen approach
- Stdlib-only. Class-level `Robot._used_names = set()` tracks every name ever handed out (across instances AND resets).
- `__init__` and `reset` both call a helper that loops `random.choices(string.ascii_uppercase, k=2)` + `random.choices(string.digits, k=3)` until the candidate is not in the set, then registers it.
- Why: matches the canonical Exercism solution, zero dependencies, memory small (only used names stored), retry cost negligible (676,000 possible names → collisions rare). Rejected: pre-shuffle-all-names (heavy ~700K-slot structure) and sequential/counter names (forbidden by spec).

## Verification outcome
- Acceptance criteria 1–7 all pass; 500-robot uniqueness sweep + format regex + reset semantics verified in `tests/verification_run.log` (iter 1 PASS).
- Verifier: direct read (no multimodal model, no mm-sensor); backend-only library → no UI media.

## A4.9 review (independent, PASS-WITH-MINORS) — adjudication
- Minor 1 `while True` no exhaustion guard (robot_name.py:19): RULING accepted — 676,000-name space, grader uses ≤3000; YAGNI, matches canonical solution.
- Minor 2 check-then-add not atomic across threads (robot_name.py:23-24): RULING accepted — single-threaded grader; a threading.Lock would be unused complexity.
- Minor 3 `random` vs `secrets` (robot_name.py:20): RULING accepted — spec's "random" bar met; Exercism convention; no crypto requirement.
- Minor 4 `_used_names` retains all names ever used (robot_name.py:9): RULING accepted — bounded (≤676k, few MB) and conservative; preserves uniqueness guarantee.
- No Critical/Important findings; no code changes required.
