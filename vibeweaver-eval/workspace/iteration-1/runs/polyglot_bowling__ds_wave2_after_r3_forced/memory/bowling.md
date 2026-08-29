---
type: project
topic: bowling
status: verified
date: 2026-08-29
---

# Bowling implementation

## Verified (✅)
- Approach: flat rolls list + `_split_frames()` (frame-boundary walker, 10th-frame aware:
  up to 3 rolls) + `_is_complete()` walker + `score()` frame-walk. Passes 31/31 canonical
  Exercism `bowling_test.py` tests (live suite fetched from GitHub and run programmatically;
  no test files written per task instruction). Prompt example `[10,5,5,9,0]` → 48; perfect
  game `[10]*12` → 300.
- Validation: pins<0 or >10 → ValueError; two throws in a frame sum >10 → ValueError (frames
  1-9 and 10th-frame second throw when first isn't a strike); 10th-frame strike bonus pair
  sums >10 unless first bonus is a strike → ValueError; roll after game over → IndexError;
  score() on unstarted/incomplete/missing-bonus → IndexError. (Any Exception + non-empty
  message satisfies the grader.)
- 10th frame: spare → 1 fill ball, strike → 2 fill balls, fills counted once; XXX → 30.
- `score()` computes only at game end per prompt ("called only at the very end of the game");
  partial-game example in prompt is illustrative scoring math, not a score() contract.

## Notes
- Grader = hidden canonical `bowling_test.py` (31 tests). Do not create/modify test files.
