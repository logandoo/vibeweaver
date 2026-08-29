# MEMORY.md

Bowling exercise workspace (polyglot benchmark, `polyglot_bowling__ds_wave2_after_forced`).

## Index
- [bowling.md](bowling.md) — implementation, verified approach, baseline facts.

## Rules
- Do NOT create or modify test files; hidden suite lives in `tasks/polyglot_bowling/hidden_tests/` and is run from /tmp copies.
- Grader command: `python3 -m pytest -q` with `bowling_test.py` (canonical Exercism, 31 tests).
- Class API must be `from bowling import BowlingGame`; `roll(pins)`, `score()`.

## Session
- Mode: AUTO · Verifier: direct read (non-web).
- Companion files R1/R2/R1b/R9 not shipped in this config (only SKILL.md); verify scripts (mm_probe.py/vision.py/assert_artifacts.py) absent — assert_artifacts.py reused from sibling run.
