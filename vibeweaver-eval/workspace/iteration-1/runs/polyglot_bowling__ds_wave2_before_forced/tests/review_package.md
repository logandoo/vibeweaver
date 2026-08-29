# A4.9 Review Package — Bowling exercise (`bowling.py`)

Reviewer scope: READ-ONLY. Review the candidate implementation below against the spec.
Deliver a verdict: Strengths · Critical / Important / Minor (dimension-tagged
Bugs/Security/Compliance, Minors <= 5 itemized, with file:line + why) · Assessment.

## Task spec (prompt.md, verbatim requirements)
- `roll(pins : int)` is called each time the player rolls a ball; argument = pins knocked down.
- `score() : int` is called only at the very end of the game; returns the total score.
- 10 frames; a frame = 1-2 throws, 10 pins standing at frame initialization.
- Open frame (<10): score = pins knocked down. Spare (10 by 2nd throw): 10 + next throw.
  Strike (10 by 1st throw): 10 + next two throws; consecutive strikes need an extra roll to resolve.
- 10th frame special case: spare → 1 fill ball, strike → 2 fill balls; fill balls exist only to
  calculate the 10th frame; scoring on a fill ball gives no more fill balls; the 10th frame's value
  is the total number of pins knocked down (e.g. X1/ = 20, XXX = 30).

## Expected interface (hidden grader = Exercism-style Python test, official `bowling_test.py`)
- `BowlingGame()` constructs; `.roll(pins)` per ball; `.score()` at the very end.
- 31 official tests: scoring (zeros/90, spare/strike bonuses, 10th-frame fills, perfect 300) +
  error contracts (ValueError-family on negative/>10/frame-over-10/bonus-over-10-after-non-strike;
  IndexError-family on score-before-complete and roll-after-game-over) — any Exception with a
  non-empty message passes the error tests.

## Candidate implementation (bowling.py — full diff from baseline stub `44a8187`; 1 file, +71/-6)
```python
class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0:
            raise ValueError("Negative roll is invalid")
        if pins > 10:
            raise ValueError("Pin count exceeds pins on the lane")
        if self._is_complete():
            raise IndexError("Cannot roll after the game is over")

        frame, ball, frame_rolls = self._current_frame_state()
        if ball >= 2:
            if frame < 10:
                if frame_rolls[0] + pins > 10:
                    raise ValueError("Pin count exceeds pins on the lane")
            elif frame_rolls[0] != 10 and ball == 2:
                if frame_rolls[0] + pins > 10:
                    raise ValueError("Pin count exceeds pins on the lane")
            elif frame_rolls[0] == 10 and ball == 3 and frame_rolls[1] != 10:
                if frame_rolls[1] + pins > 10:
                    raise ValueError("Pin count exceeds pins on the lane")
        self.rolls.append(pins)

    def score(self):
        if not self._is_complete():
            raise IndexError("Score cannot be taken until the end of the game")

        total = 0
        i = 0
        for _ in range(10):
            if self.rolls[i] == 10:
                total += 10 + self.rolls[i + 1] + self.rolls[i + 2]
                i += 1
            elif self.rolls[i] + self.rolls[i + 1] == 10:
                total += 10 + self.rolls[i + 2]
                i += 2
            else:
                total += self.rolls[i] + self.rolls[i + 1]
                i += 2
        return total

    def _current_frame_state(self):
        i = 0
        frame = 1
        while frame < 10:
            if i >= len(self.rolls):
                break
            if self.rolls[i] == 10:
                i += 1
                frame += 1
            elif i + 1 < len(self.rolls):
                i += 2
                frame += 1
            else:
                break
        frame_rolls = self.rolls[i:]
        return frame, len(frame_rolls) + 1, frame_rolls

    def _is_complete(self):
        i = 0
        frame = 1
        while frame < 10:
            if i >= len(self.rolls):
                return False
            if self.rolls[i] == 10:
                i += 1
            else:
                if i + 1 >= len(self.rolls):
                    return False
                i += 2
            frame += 1

        frame_10_rolls = len(self.rolls) - i
        if frame_10_rolls < 2:
            return False
        if self.rolls[i] == 10 or self.rolls[i] + self.rolls[i + 1] == 10:
            return frame_10_rolls >= 3
        return True
```

## Acceptance criteria exercised (tests/acceptance.md)
1. imports + constructs; 2. open frames (0, 90); 3. spare bonus (10, 16, 31); 4. strike bonus
(10, 26, 81, last-two-strikes 31); 5. 10th spare (17, 20); 6. 10th strike (18, 20, 30);
7. perfect 300; 8. error contracts (ValueError/IndexError per spec).

## Evidence summary
- `tests/verification_run.log`: 29/29 runner checks PASS.
- `tests/canonical_suite.log`: official Exercism `bowling_test.py` → 31/31 OK.
- `tests/differential_check.log`: 5000 random valid games vs independent frame reference → 0 mismatches.
- Baseline GREEN (`44a8187`), iter-1 FAIL diagnosed and fixed, fresh run on final tree PASS.
