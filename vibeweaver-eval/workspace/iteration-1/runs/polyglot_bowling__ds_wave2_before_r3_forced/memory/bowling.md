---
type: project
topic: bowling
status: verified
date: 2026-08-29
---

# Bowling implementation

## Verified (✅)
- Approach A (flat rolls list + `_build_frames()`/`_is_game_over()` walkers + `score()`
  frame-walk) passes 31/31 canonical hidden tests (`pytest -q bowling_test.py`, exit 0) and
  inline sanity checks (all ones=20, perfect=300, 10th-frame fill-ball cases, gutter=0,
  7 validation ValueErrors).
- Validation rules: pins<0 → ValueError; pins>10 → ValueError; two rolls in a frame sum >10 →
  ValueError (regular frames and 10th-frame strike-bonus second roll when first bonus is not a
  strike); rolling after game over → ValueError; score() on unstarted/incomplete/missing-bonus →
  ValueError. (Tests accept any Exception subclass with a non-empty message.)
- 10th frame: spare → 1 fill ball, strike → 2 fill balls, fills counted once; XXX → 30.
- `score()` computes only at game end, per prompt ("called only at the very end of the game").

## Notes
- Grader = hidden `bowling_test.py` (Exercism canonical, 31 tests) via `python3 -m pytest -q`.
- Do not create/modify test files in workspace; run the hidden suite read-only with PYTHONPATH set.
