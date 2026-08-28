# Acceptance Criteria — Robot Name

> cap=5  stall=3×

1. `Robot().name` matches the format `^[A-Z]{2}\d{3}$` (two uppercase letters + three digits).
2. Repeated reads of `name` on the same robot return the same name (name sticks).
3. Different robot instances have different names (globally unique).
4. After `reset()`, the next `name` read returns a new, well-formed name different from the previous one — including when `random` is re-seeded before the reset (hidden `test_reset_name` scenario).
5. The module imports and runs standalone with no syntax or runtime errors.
