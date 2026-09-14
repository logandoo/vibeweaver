> cap=5  stall=3×

1. `Robot().name` matches `^[A-Z]{2}\d{3}$` on first access.
2. Repeated `robot.name` reads return the same value (name sticks until reset).
3. Two independently created robots have different names.
4. `robot.reset()` wipes the name; the next `name` access yields a valid name different from the previous one (canonical seeded-RNG reset test).
5. Across many live robots no two share a name, and a reset robot never receives a name already issued to any existing robot.
