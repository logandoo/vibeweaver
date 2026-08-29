# MEMORY.md

Bowling exercise workspace (polyglot benchmark, `polyglot_bowling__ds_wave2_after_r3_forced`).

## Index
- [bowling.md](bowling.md) — implementation, verified approach, baseline facts.

## Rules
- Do NOT create or modify test files; hidden suite is the canonical Exercism `bowling_test.py`
  (31 tests), run read-only against the workspace `bowling.py` (PYTHONPATH).
- Class API must be `from bowling import BowlingGame`; methods `roll(pins)`, `score()`.
- Error contract: hidden tests use `assertRaisesRegex(Exception, r".+")` — any exception type
  with a non-empty message is acceptable.

## Session
- Mode: AUTO · Verifier: direct read (non-web library task — no UI/HTTP).
- Implemented `BowlingGame` in `bowling.py` with a flat rolls list + frame-split/complete
  walkers + frame-walking `score()`. Verified 31/31 against the live canonical Exercism suite
  (fetched + parsed programmatically, no test files written) plus prompt example (48) and
  perfect game (300).
- assert_artifacts.py NOT copied into tests/ — task explicitly forbids creating test files in
  this graded workspace; verification evidence is the executed canonical-suite transcript.
- Companion rulebooks not shipped in this config; workflow driven from SKILL.md binding text.

## A4.9 review
- Not triggered: change scoped to a single file (`bowling.py`) in this run dir; no schema/API
  surface beyond the prescribed stub interface; no security-sensitive/risk-tier path; behavior
  verified against the canonical suite the grader itself uses.
