> cap=5  stall=3x
1. Robot.name returns a 5-char name matching `[A-Z]{2}[0-9]{3}` (e.g. RX837).
2. Robot.name is stable across repeated access (no regeneration).
3. Two different robots get different names.
4. Robot.reset() wipes the name; the next name access returns a new random name.
5. The name after reset still matches `[A-Z]{2}[0-9]{3}` and differs from other robots.
6. 1000 robots instantiated in one run all receive unique names.
