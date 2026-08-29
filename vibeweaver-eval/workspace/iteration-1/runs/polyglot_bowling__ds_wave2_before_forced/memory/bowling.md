---
type: fix
status: verified
date: 2026-08-29
---

# bowling.md — Bowling exercise

## Problem
Score a ten-pin bowling game: `BowlingGame.roll(pins)` per ball, `score()` at the very end.
10 frames; open = frame pins; spare = 10 + next roll; strike = 10 + next two rolls;
10th-frame spare gets 1 fill ball, strike gets 2 (fill balls never chain).

## Approach (evaluated, chose A)
- **A — rolls list + frame-walk (chosen):** store all rolls; `score()` walks 10 frames with index
  arithmetic (fill balls are just rolls in the walk); `roll()` validates against a frame-position
  walk. Minimal state, scoring in one place, canonical Exercism pattern.
- B — frame-object list w/ bonus appending at roll time: duplicated state, harder 10th-frame validation.
- C — incremental score tracking w/ pending-bonus counters: spreads scoring into `roll()`, error-prone.

## Key implementation details
- `_current_frame_state()` walks completed frames (1-9) and returns (frame_no, ball_in_frame,
  rolls_of_current_frame). **Critical invariant:** stop at an in-progress 1-roll non-strike frame —
  advancing past it breaks `roll(5); roll(6)` → frame-over-10 must raise ValueError.
- `_is_complete()`: frames 1-9 done + 10th-frame 2 rolls (open) or 3 rolls (strike/spare).
- `score()` raises IndexError if not complete; `roll()` raises IndexError after game over,
  ValueError for negative/>10 pins and frame or non-strike-bonus sums > 10.

## Evidence
- 29/29 runner checks; canonical Exercism `bowling_test.py` 31/31 OK; 5000-game random
  differential vs independent frame reference: 0 mismatches. Evidence in `tests/verification_run.log`,
  `tests/canonical_suite.log`, `tests/differential_check.log`.
