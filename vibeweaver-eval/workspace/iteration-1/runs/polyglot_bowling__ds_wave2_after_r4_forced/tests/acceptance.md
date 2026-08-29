> cap=5  stall=3×
1. BowlingGame.roll(pins) records each pin count without error for a full valid game.
2. score() returns 48 for the prompt's example game (X, 5/, 9-0, rest gutter).
3. score() returns 300 for a perfect game (12 strikes).
4. score() returns 0 for a gutter game (20 zero rolls).
5. score() correctly scores the 10th-frame special cases: X1/ -> 20, XXX -> 30, 5/ + 7 -> 17.
6. score() returns 150 for an all-spares game (21 rolls).
7. Consecutive-strike bonus chaining is correct (e.g. two strikes + open = 47).
8. bowling.py has no syntax or runtime errors (compiles; class imports cleanly).
