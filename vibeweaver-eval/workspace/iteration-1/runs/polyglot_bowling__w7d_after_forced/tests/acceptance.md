> cap=5  stall=3×

# Acceptance Checklist — Bowling Scorer

Task: implement `BowlingGame.roll(pins)` / `BowlingGame.score()` per `prompt.md`.
Deliverable: `bowling.py` only. No test files are created or modified in the deliverable.

## Criteria

- [x] C1 `roll(pins)` accepts each throw; `score()` returns the total after a completed game.
- [x] C2 Open-frame, spare, and strike tabulation match the prompt examples (48 for the 3-frame sample).
- [x] C3 10th-frame fill-ball rules: strike → two bonus rolls; spare → one bonus roll; fill-ball strike/spare grants no extra rolls.
- [x] C4 Input validation: reject negative pins, pins > 10, frame totals > 10, and invalid bonus sequences (raise `Exception` with a non-empty message).
- [x] C5 State validation: `score()` raises on an unstarted or incomplete game; `roll()` raises after the game is complete.
- [x] C6 All 31 tests in the trusted oracle (`bowling_test.py`) pass.
- [x] C7 `python3 -m py_compile bowling.py` succeeds.

## Stop condition

Bounded loop cap = 5 iterations; stall = 3 consecutive iterations with no new `iter N PASS` entry.
