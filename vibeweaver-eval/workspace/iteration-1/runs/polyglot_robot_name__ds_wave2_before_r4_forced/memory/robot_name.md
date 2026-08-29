# Robot Name — memory

## Contract (prompt.md + hidden tests/robot_name_test.py)
- `Robot().name` matches `^[A-Z]{2}\d{3}$` (2 uppercase letters + 3 digits).
- Name is stable across reads (`test_name_sticks`).
- Two robots never share a name (`test_different_robots_have_different_names`).
- `reset()` assigns a new, different, valid name (`test_reset_name`).
- Names must not follow a predictable/sequential pattern (prompt requirement).

## Implementation
- `robot_name.py`: class-level `_used_names = set()`; `__init__`/`reset()` call
  `_new_name()`, which generates `2 letters + 3 digits` via `random.choice` and
  retries on collision. Loop bounded by `_NAMESPACE_SIZE = 26*26*10*10*10`
  (676k); raises `RuntimeError` if the space is exhausted.

## Gotchas (learned)
- The hidden reset test re-seeds `random.seed("Totally random.")` BEFORE both
  `Robot()` and `reset()`. Without the collision-retry set, the re-seeded RNG
  would produce the SAME name again and `test_reset_name` would fail. The
  uniqueness set is what forces a retry to a different name.
- Names are never released on `reset()` (kept forever) — required so
  `test_different_robots_have_different_names` and the reset test stay green
  under the seeded RNG.
- `_used_names` lives at class level so every instance shares one namespace
  (global uniqueness across robots).
- Thread-safety of check-then-add: not handled (single-threaded graded suite);
  would need a lock if multi-threaded.
- Verifier: direct-read (backend-only library, no UI/media).

## Verification artifacts (tests/)
- `baseline_stub.run.log` (RED: 4 failed on stub), `robot_name_hidden.run.log`
  (GREEN: 4 passed), `consumer_smoke.run.log` (9/9), `assert_artifacts.py`
  gate result.
