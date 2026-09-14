> cap=5  stall=3×

1. `roll(pins)` appends each throw to the game's roll sequence without error.
2. `score()` returns the sum of the 10 frame scores for an open-frame game (no strikes/spares).
3. A spare scores 10 + the next single roll.
4. A strike scores 10 + the next two rolls (including the two-strike lookahead case).
5. The 10th-frame fill balls are scored correctly: spare+fill = 10-frame total, three strikes = 30.
6. Known end-to-end games return exact totals: all-gutters=0, all-spares(5/)=150, perfect game=300, prompt example (X|5/|90)=48.
7. The module imports and runs with no syntax or runtime errors.
