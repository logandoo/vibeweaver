> cap=5  stall=3×

# Acceptance Criteria — Robot Name

Source: task request (`prompt.md`) — polyglot_robot_name, Exercism "Robot Name" kata.
Derivation: AUTO decision D-1 (criteria below taken from the request's explicit
words + the hidden test contract in `../../tasks/polyglot_robot_name/hidden_tests/robot_name_test.py`).

1. `Robot().name` returns a string matching `^[A-Z]{2}\d{3}$` (two uppercase
   letters followed by three digits). — hidden `test_has_name`
2. Repeated access to `robot.name` returns the SAME name (name sticks). — hidden `test_name_sticks`
3. Two different `Robot` instances have different names. — hidden `test_different_robots_have_different_names`
4. After `robot.reset()`, the next access to `robot.name` returns a NEW name
   that differs from the previous one and still matches the format. — hidden `test_reset_name`
5. Global uniqueness: no name is ever reused by any existing Robot, even
   across resets — empirically: a 2000-robot sweep yields 2000 distinct names
   (0 collisions).
6. Names are random, not a fixed sequential pattern — empirically: a sweep of
   generated names shows variation in both the letter-prefix and the digit
   suffix beyond a single counter (criterion 5's checks also require this:
   sequential `AA000..AA999` would collide at 1001 robots).

| # | Criterion | Verifiable how |
|---|-----------|----------------|
| 1 | name format regex | hidden suite + consumer smoke |
| 2 | name stability | hidden suite + consumer smoke |
| 3 | different robots differ | hidden suite + consumer smoke |
| 4 | reset yields new name | hidden suite (seeded) + consumer smoke |
| 5 | global uniqueness 2000 robots | consumer smoke sweep |
| 6 | non-sequential randomness | consumer smoke variation checks |
