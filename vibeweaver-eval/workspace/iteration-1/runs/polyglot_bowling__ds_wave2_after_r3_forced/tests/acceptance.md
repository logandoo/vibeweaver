> cap=5  stall=3×

Acceptance criteria for bowling.py (user-owned stop condition):

1. bowling.py compiles with no syntax errors (py_compile exit 0).
2. score() returns 0 for a gutter game ([0]*20).
3. score() returns 90 for no strikes/spares ([3,6]*10).
4. score() returns 10 for a spare followed by zeros ([6,4]+[0]*18).
5. score() returns 16 for a spare whose bonus is counted twice ([6,4,3]+[0]*17).
6. score() returns 31 for consecutive spares ([5,5,3,7,4]+[0]*15).
7. score() returns 10 for a single-strike frame ([10]+[0]*18).
8. score() returns 26 for a strike with two-roll bonus ([10,5,3]+[0]*16).
9. score() returns 81 for consecutive strikes ([10,10,10,5,3]+[0]*12).
10. score() returns 300 for a perfect game ([10]*12).
11. score() returns 17 for a last-frame spare with one bonus ([0]*18+[7,3,7]).
12. score() returns 18 for a last-frame strike with two bonuses ([0]*18+[10,7,1]).
13. score() returns 20 for last-frame [10,7,3] and [7,3,10].
14. score() returns 30 for last-frame XXX ([0]*18+[10,10,10]).
15. score() returns 31 for [0]*16+[10,10,0,1].
16. score() returns 26 for [0]*18+[10,10,6].
17. roll() raises for pins < 0 or pins > 10.
18. roll() raises when two rolls in a frame exceed 10 ([5] then 6).
19. roll() raises on invalid fill balls (bonus pair sums > 10 unless first is a strike).
20. roll() raises when the game is already complete (extra roll after 10 frames / after bonuses).
21. score() raises on an unstarted or incomplete game (including missing last-frame bonuses).
22. The prompt's three-frame example (X, 5/, 9-0) scores 48 when rolled as a full game leading to that total.
