> cap=5  stall=3×
1. `robot_name.py` imports and `Robot()` constructs with no syntax or runtime errors.
2. `Robot().name` matches the format `^[A-Z]{2}[0-9]{3}$` (two uppercase letters followed by three digits).
3. A robot's `name` is stable across repeated reads (it does not change until `reset()` is called).
4. Two distinct `Robot()` instances get different names (names are unique across robots).
5. `reset()` gives the robot a new valid name different from its previous name.
6. Names remain unique across many instances and after resets (500 `Robot()` instances all have distinct names).
7. Names are random / non-sequential (across 500 robots, ≥20 distinct 2-letter prefixes appear, not one fixed sequence).
