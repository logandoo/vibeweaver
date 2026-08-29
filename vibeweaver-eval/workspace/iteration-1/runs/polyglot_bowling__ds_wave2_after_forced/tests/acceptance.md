> cap=5  stall=3×

# Bowling Game — Acceptance Criteria

Derived from prompt.md + canonical Exercism bowling test suite (tasks/polyglot_bowling/hidden_tests/bowling_test.py).

1. A complete game of all zeros scores 0.
2. A complete game with no strikes/spares scores the plain pin sum (20 rolls of `3,6` → 90).
3. A spare scores 10 plus the next roll; consecutive spares each get their one-roll bonus.
4. A strike scores 10 plus the next two rolls; consecutive strikes each get the two-roll bonus.
5. The 10th frame awards fill balls: one after a spare, two after a strike; fill balls are counted once (XXX → 30; X1/ → 20; 10,7,3 → 20).
6. A perfect game (12 strikes) scores 300.
7. Validation: a negative roll raises an exception.
8. Validation: a roll scoring more than 10 pins raises an exception.
9. Validation: two rolls in a frame summing over 10 raise an exception (regular frames and 10th-frame strike-bonus frame when first bonus is not a strike).
10. Validation: after a non-strike first bonus roll in the 10th frame, the second bonus roll may not exceed 10 minus the first (10,6 → roll(10) raises).
11. Validation: rolling after the game is complete raises an exception.
12. Validation: score() raises an exception when the game is unstarted, incomplete, or its bonus rolls are missing.
13. `score()` returns the correct running total at game end, and the module imports as `from bowling import BowlingGame`.
14. Implementation lives in bowling.py only; no test files created or modified.
