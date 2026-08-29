# robot_name — Exercism "Robot Name" kata (polyglot_robot_name)

- Task: implement `Robot` in `robot_name.py` to pass hidden tests
  `../../tasks/polyglot_robot_name/hidden_tests/robot_name_test.py`.
- Contract: `Robot().name` → `^[A-Z]{2}\d{3}$`; name sticks across accesses;
  two robots always differ; `reset()` clears the name, next access yields a
  NEW different name; global uniqueness across all robots, even across resets.
- Chosen implementation (ADR D-3): lazy `name` property + class-level
  `_used_names` set + collision-retry loop using stdlib `random` —
  matches Exercism canonical `example.py`. Reset test passes because the
  re-seeded RNG reproduces the already-used candidate, which the loop skips.
- Verified: hidden suite 4/4 + consumer smoke 9/9 (uniqueness sweep 2000,
  variation checks). See `tests/verification_log.md`.
- Rejected: eager generation in `__init__`; pre-generating the 676k-name
  namespace (YAGNI).
- Do NOT create test_*.py files in the workspace (grading pytest collects).
