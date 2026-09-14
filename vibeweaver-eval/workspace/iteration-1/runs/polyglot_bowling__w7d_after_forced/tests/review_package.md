# Review Package — Bowling Scorer (A4.9)

Change class: new feature + behavior-semantic → independent review non-skippable.
Reviewer: fresh-context subagent (no shared history with the author).

## Artifact under review
- `bowling.py` (`BowlingGame.roll`, `score`, `_is_complete`, `_frame_complete`, `_validate_roll`).

## Inputs given to the reviewer
- `prompt.md` (spec)
- `hidden_tests/bowling_test.py` (trusted oracle, 31 tests)
- The implementation file

## What the reviewer did
- Differential fuzz: 115,552 randomly generated completed games compared against an
  independent reference scorer → 0 wrong values, 0 unexpected exceptions.
- 10th-frame exhaustive sweep: all 1,464 roll sequences of length 0–3 over 0–10 →
  0 illegal accepts, 0 legal rejects, 0 wrong scores.
- Mixed-game enumeration: 1,835,008 games across strike/spare/open and 7 tenth-frame
  outcomes → 0 mismatches.
- Two-roll validation for frames 1–9 (all 121 pairs): accept iff `a==10 or a+b<=10`.
- Re-ran the oracle: 31/31 pass.

## Verdict
APPROVE — no correctness bugs found.

## Nits
- `roll()` rejects `bool`/non-`int` pins (stricter than the spec's `int` annotation,
  oracle-compatible). Accepted as-is.

## Residual risk
Low. The `len==1 & rolls[0]==10` branch in `_validate_roll` is unreachable because a
strike closes frames 1–9 immediately; harmless.
