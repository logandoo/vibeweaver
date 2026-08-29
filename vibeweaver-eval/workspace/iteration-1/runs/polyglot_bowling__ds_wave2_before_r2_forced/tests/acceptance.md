> cap=5  stall=3×

# Acceptance Criteria — Bowling scoring kata (exercism "bowling")

1. An open game with no strikes or spares (rolls 3,6 repeated 10x) scores 90.
2. A spare counts 10 plus the next roll (6,4,3,0,...) scores 16; a spare followed by zeros scores 10.
3. A strike counts 10 plus the next two rolls (10,5,3,...) scores 26.
4. Consecutive strikes apply two-roll bonuses correctly (10,10,10,5,3,...) scores 81; a perfect game (12 strikes) scores 300.
5. A 10th-frame spare gets one fill ball counted once (...,7,3,7) scores 17.
6. A 10th-frame strike gets two fill balls counted once (...,10,7,1) scores 18; X1/ scores 20; XXX scores 30; ...,10,10,6 scores 26.
7. roll() raises an exception for negative pins, pins > 10, a frame whose two balls exceed 10, and rolling after the game is over.
8. score() raises an exception when the game is unstarted or incomplete (including missing fill balls).
