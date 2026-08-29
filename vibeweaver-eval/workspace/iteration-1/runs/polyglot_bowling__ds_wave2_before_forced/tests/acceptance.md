> cap=5  stall=3×
1. `bowling.py` imports and `BowlingGame()` constructs with no syntax or runtime errors.
2. Open frames score the pins knocked down (e.g. 20 zeros → 0; 3,6 ×10 frames → 90).
3. A spare scores 10 plus the next roll (e.g. `6,4,3,0…` → 16; consecutive spares `5,5,3,7,4,0…` → 31).
4. A strike scores 10 plus the next two rolls (e.g. `10,5,3,0…` → 26; consecutive strikes `10,10,10,5,3,0…` → 81).
5. 10th-frame spare gets one fill ball, scored once (e.g. `[0,0]×9 + 7,3,7` → 17; `7,3,10` → 20).
6. 10th-frame strike gets two fill balls, scored once (e.g. `[0,0]×9 + 10,7,1` → 18; `10,7,3` → 20; `10,10,10` → 30).
7. Perfect game: 12 strikes → 300.
8. Invalid rolls raise errors: negative pins and >10 pins raise `ValueError`; two rolls in a frame (or two bonus rolls after a non-strike) summing >10 raise `ValueError`; rolling after the game is over and scoring before completion raise `IndexError`.
