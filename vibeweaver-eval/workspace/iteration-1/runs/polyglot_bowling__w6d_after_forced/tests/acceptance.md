> cap=5  stall=3×

# Acceptance Criteria — BowlingGame

1. `roll(pins)` records each throw; `score()` returns the total for a completed 10-frame game.
2. Gutter game (20 rolls of 0) scores 0.
3. All ones (20 rolls of 1) scores 20.
4. A single spare followed by a 3 scores 16 for that frame.
5. A single strike followed by 3 then 4 scores 24 for that frame.
6. Perfect game (12 strikes) scores 300.
7. 10th-frame spare with one fill ball (5,5,3) scores 13.
8. 10th-frame strike with two fill balls (10,3,4) scores 17.
9. Prompt mixed example: X, 5/, 9,0 then gutter fill → running total 48.
10. No syntax or runtime errors when importing and exercising the class.
