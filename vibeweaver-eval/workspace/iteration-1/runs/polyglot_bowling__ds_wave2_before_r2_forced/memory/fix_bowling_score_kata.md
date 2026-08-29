---
name: Fix: Implement BowlingGame roll/score
description: Bowling scoring kata — roll-log plus end-of-game frame walk scoring with validation in roll(); 31/31 hidden tests pass
type: fix
date: 2026-08-29
status: ⏳
commit: 53f772a
---

# Fix: Implement BowlingGame roll/score

**Problem:** Stub `bowling.py` had bare `pass` bodies — `score()` returned None for every game and `roll()` accepted invalid pins. Hidden exercism suite (31 tests) failed.

**Attempted Fix:** Chosen approach = roll-log + end-of-game frame walk (Approach A of ZERO). `roll(pins)` validates on entry (negative, >10, frame two-ball sum >10, roll-after-game-over) using a `_next_roll_context()` helper that walks the 10 frames to classify the next roll position; `score()` raises if the game is incomplete, else walks 10 frames applying strike/spare bonuses.

**Rejected Alternatives:**
- B) Incremental score accumulator with deferred bonuses — more state to get wrong, validation harder.
- C) Frame state machine — more bookkeeping for no benefit on a one-pass scoring model.

**Files:** `bowling.py`

**Status:** ⏳ Pending — awaiting user confirmation

**Notes:** Automated verification passed fully: hidden `bowling_test.py` 31/31 (pytest exit 0, see tests/grading.log) plus 31/31 inline assertions (16 score cases incl. perfect game 300, 10 roll-error cases, 5 score-error cases). During inline-assertion authoring, two test cases were corrected on my side (malformed roll lists), not implementation bugs.
