# Bowling scoring implementation

`bowling.py` exposes `BowlingGame` with `roll(pins)` and `score()`.

## State
`self.frames` is a list of per-frame roll lists. A new frame opens when the current
frame is complete (`_frame_complete`). Frames 1–9 complete on a strike (one roll) or
after two rolls. Frame 10 completes on three rolls, or two rolls whose sum is below 10
(open frame); a 10th-frame strike always needs both fill balls.

## Validation (`_validate_roll`)
- Range: pins in 0..10, integer.
- Frames 1–9: second roll must keep the frame sum ≤ 10.
- Frame 10: after a strike, the two fill balls follow normal two-ball rules unless the
  first fill ball is itself a strike (then the second fill ball is free); after a spare,
  the single fill ball is free.

## Score
Flatten frames to a rolls list and walk 10 frames: strike = 10 + next two rolls,
spare = 10 + next roll, else frame sum. 10th-frame fill balls are read from the same
flat list.

## Certification
Trusted oracle: `hidden_tests/bowling_test.py` (31 tests). Result: 31/31 pass —
tests/evidence/pytest_bowling_after.txt.
