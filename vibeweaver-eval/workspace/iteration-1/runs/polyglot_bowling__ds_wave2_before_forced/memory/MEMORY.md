# MEMORY.md — project memory index

Project: polyglot exercise workspace — `bowling.py` (Exercism-style "Bowling" kata).
Mode: Modify-Existing (starter stub `class BowlingGame: __init__/roll/score`).

## User / constraints
- Harness constraint: "Do NOT create or modify any test files" — verification runner stays OUTSIDE the workspace (`/var/folders/.../T/opencode/bowling_verify.py`); only log evidence lands in `tests/` (no collectable test files).
- Graded by hidden tests run against `bowling.py`; interface must be `BowlingGame` → `.roll(pins)` / `.score()`. Canonical Exercism suite = the reference contract.
- Run directory is untracked inside the parent repo; baseline commit was scoped to this dir (`44a8187 backup: before changes`), final commit scoped likewise (Commit column = short hash).

## Topics
- [bowling.md](bowling.md) — spec + chosen approach for the Bowling exercise (✅ Verified)

## Verified / Failed / Forbidden
- ✅ Verified: rolls-list + frame-walk approach (`score()` walks 10 frames; `roll()` validates via `_current_frame_state`); 29/29 runner checks + 31/31 canonical Exercism suite + 5000-game random differential vs independent frame reference all PASS.
- ✅ Verified: `_current_frame_state` walker MUST stop at an in-progress 1-roll non-strike frame (`elif i + 1 < len(self.rolls)` / `break`) — the naive `while frame < 10 and i < len(self.rolls)` advance skips the pending second roll and drops frame-over-10 validation (iter 1 FAIL, fixed).
- ❌ Failed: (none for the final algorithm; iter-1 test-data bug was in the runner, not the module — canonical strike games are 19 (or 17) rolls, not 20).
- ⛔ Forbidden: writing any collectable test file into the workspace; raw build/lifecycle commands bypassing `script/`.

## A4.9 review verdict (2026-08-29) — PASS
Independent read-only reviewer: no Critical / no Important findings; PASS. Independent re-testing:
200k random deep trials (15% illegal pins) vs reference validator, 30k valid games vs frame-based
scorer, exhaustive legal-prefix depth-5 checks — all 0 mismatches.
Minors recorded (not fixed — style/perf only, leave validated code untouched):
1. `_current_frame_state` returns `ball = len(frame_rolls)+1` (1-based "next ball") — slightly unintuitive naming, nested if/elif chain; cosmetic.
2. `_current_frame_state` rescans rolls from 0 each call → O(n²) worst case; irrelevant at max 21 rolls.
3. No docstrings/type hints on public interface — cosmetic.
