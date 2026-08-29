# MEMORY.md

Bowling exercise workspace (polyglot benchmark, `polyglot_bowling__ds_wave2_after_forced`).

## Index
- [bowling.md](bowling.md) — implementation, verified approach, baseline facts.

## Rules
- Do NOT create or modify test files; hidden suite lives in `tasks/polyglot_bowling/hidden_tests/` and is run from /tmp copies.
- Grader command: `python3 -m pytest -q` with `bowling_test.py` (canonical Exercism, 31 tests).
- Class API must be `from bowling import BowlingGame`; `roll(pins)`, `score()`.

## Session
- Mode: AUTO · Verifier: direct read (non-web).
- Companion files R1/R2/R1b/R9 not shipped in this config (only SKILL.md); verify scripts (mm_probe.py/vision.py/assert_artifacts.py) absent — assert_artifacts.py reused from sibling run.

## A4.9 review (2026-08-29) — APPROVE
- 0 Critical / 0 Important / 4 Minor (Quality): M1 `_frame_state` returns next-ball number `len(frame_rolls)+1` (works, confusing name); M2 frames-1-9 walk duplicated in `_frame_state`/`_is_complete`; M3 pin-range checks precede game-over check (ValueError vs IndexError ordering — both Exception, tests pass); M4 two walks per roll() call (negligible ≤21 rolls). Rulings: all accepted/deferred, no code change (functional impact none; verified tree stays green).
