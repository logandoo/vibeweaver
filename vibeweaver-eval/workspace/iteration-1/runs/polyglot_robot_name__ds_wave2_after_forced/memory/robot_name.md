---
type: project
topic: robot-name-exercise
trust: verified
created: 2026-08-29
---

# Robot Name exercise — spec + approach (✅ Verified)

## Spec (from prompt.md)
- A robot gets a random name on first "turn on" (at construction, per the Python-track test interface): two uppercase letters + three digits (e.g. `RX837`, `BC811`).
- `reset()` wipes the name; the next `name` read returns a new random name.
- Names must be random (not a predictable sequence) and unique across all existing robots.

## Chosen approach
- Stdlib-only. Class-level `Robot._used_names = set()` tracks every name ever handed out (across instances AND resets; reset does not release the old name, guaranteeing the new name differs from the previous one).
- `__init__` and `reset` both call a helper that loops `random.choices(string.ascii_uppercase, k=2)` + `random.choices(string.digits, k=3)` until the candidate is not in the set, then registers it.
- Why: matches the canonical Exercism solution, zero dependencies, memory small (only used names stored), retry cost negligible (676,000 possible names → collisions rare). Rejected: pre-shuffle-all-names (heavy ~700K-slot structure) and sequential/counter names (forbidden by spec).

## Verification outcome
- Acceptance criteria 1–7 all pass; format regex, stability, distinctness, reset semantics, 500-robot uniqueness sweep, and non-sequential prefix variety verified in `tests/verification_run.log` (iter 1 PASS). Extended sweeps: 3000 more robots unique, 200 sequential resets OK, 3503 total names unique.
- Verifier: direct read (non-web) — no multimodal model (probe failed: model cannot read images), no mm-sensor; backend-only library → no UI media.

## A4.9 review (independent, PASS-WITH-MINORS) — adjudication
- Important 1 `while True` no exhaustion guard (robot_name.py:19): reviewer rated non-blocking/unreachable at grader scale (≤3000 robots ≈ 0.44% of 676,000-name space). RULING accepted — YAGNI, matches canonical solution; no code change.
- Minor 1 check-then-add not atomic across threads (robot_name.py:23-24): RULING accepted — single-threaded grader; a threading.Lock would be unused complexity.
- Minor 2 `_used_names` retains all names ever used (robot_name.py:9): RULING accepted — bounded (≤676k, few MB) and intentionally preserves the reset-≠-previous guarantee.
- Minor 3 `random` (Mersenne Twister) reproducible under fixed seed (robot_name.py:20): RULING accepted — spec's "random" bar met; Exercism convention; no crypto requirement.
- No Critical/Important code changes required; covering tests (verification_run.log 7/7 + extended sweeps) re-run after review — all pass on the reviewed tree.
