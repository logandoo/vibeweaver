# Acceptance Criteria — Bowling Game scoring (prompt.md + exercism canonical-data)

> cap=5  stall=3×

Source: prompt.md (Bowling Game exercise) + authoritative hidden test suite
`tasks/polyglot_bowling/hidden_tests/bowling_test.py` (exercism canonical-data,
2023-07-21).

1. `score()` returns 0 for a game of all zeros, and 90 for ten open 3/6 frames.
2. A spare is scored 10 + the next roll; consecutive spares each receive a one-roll bonus (5,5,3,7,4,... = 31).
3. A spare in the 10th frame receives exactly one fill ball counted once (0×18,7,3,7 = 17).
4. A strike is scored 10 + the next two rolls; consecutive strikes each receive a two-roll bonus (10,10,10,5,3,... = 81).
5. A strike in the 10th frame receives exactly two fill balls counted once (0×18,10,7,1 = 18).
6. 10th-frame fill balls: spare → one fill, strike → two fills, no extra fills beyond that (0×18,10,7,3 = 20; 0×18,10,10,10 = 30; 0×18,10,10,0,1 = 31; 0×18,7,3,10 = 20).
7. A perfect game (12 strikes) scores 300.
8. `roll()` raises Exception for negative pins and for pins > 10.
9. `roll()` raises Exception when two rolls in a frame sum to more than 10, and for invalid 10th-frame bonus sequences (bonus pair > 10 after a non-strike; second bonus a strike when the first bonus is not).
10. `roll()` raises Exception when rolling after the game is already complete.
11. `score()` raises Exception when the game is unstarted, incomplete, or is missing required 10th-frame bonus rolls.
