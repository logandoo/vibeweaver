> cap=5  stall=3x
1. A new robot's name matches format `^[A-Z]{2}\d{3}$` (two uppercase letters + three digits).
2. A robot's name is consistent across reads (same robot, same name).
3. Different robots have different names (unique among existing robots).
4. `reset()` wipes the name; next access yields a new name different from the previous one.
5. After reset, the new name is not one of the names already used (no reuse).
6. Names are random, not a predictable sequence (multiple robots produce varied, unique names).
