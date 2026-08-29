> cap=5  stall=3×
# Acceptance — polyglot_robot_name (Robot Name)

Upstream: prompt.md + hidden test contract (tests/robot_name_test.py).

| # | Criterion | How it is verified |
|---|-----------|--------------------|
| 1 | Every robot's name matches `^[A-Z]{2}\d{3}$` (2 letters + 3 digits) | hidden `test_has_name`; smoke c1 |
| 2 | The name is stable across repeated reads | hidden `test_name_sticks`; smoke c2 |
| 3 | Different robots get different names | hidden `test_different_robots_have_different_names`; smoke c3 |
| 4 | `reset()` gives a new, different, valid name | hidden `test_reset_name`; smoke c4 |
| 5 | Names are random, not predictable/sequential; unique across 2000 robots | smoke c5/c6 (uniqueness sweep, prefix/suffix variation, no fixed sequence) |

Stop-condition: > cap=5 iterations or stall=3× on the same diagnosis without a fix.
