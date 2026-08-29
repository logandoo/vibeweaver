# MEMORY.md

Bowling exercise workspace (polyglot benchmark, `polyglot_bowling__ds_wave2_before_r3_forced`).

## Index
- [bowling.md](bowling.md) — implementation, verified approach, baseline facts.

## Rules
- Do NOT create or modify test files; hidden suite lives in `tasks/polyglot_bowling/hidden_tests/` and is run read-only from the workspace (PYTHONPATH).
- Grader command: `python3 -m pytest -q bowling_test.py` (canonical Exercism, 31 tests).
- Class API must be `from bowling import BowlingGame`; methods `roll(pins)`, `score()`.

## Session
- Mode: Modify-Existing · Verifier: direct read (no multimodal probe — companion scripts
  mm_probe.py / vision.py / assert_artifacts.py not shipped in this config; only SKILL.md present).
- Companion rulebooks (TESTING_PROTOCOLS.md, COMPLETION_GATE.md, REFERENCE.md, etc.) not shipped;
  workflow driven from SKILL.md binding summaries. Web search API unavailable (HTTP 429) — ZERO
  research skip stated explicitly (algorithm is standard, unambiguously derivable from spec).

## A4.9 review (2026-08-29) — APPROVE (independent reviewer, verdict CORRECT)
- 0 Critical / 0 Important / 5 Minor (all deferred, no code change):
  M1 `self.rolls` public + unvalidated on access (fine for harness) · M2 roll() re-parses list
  each throw, O(n) with n ≤ 21, negligible · M3 frame logic split across
  `_build_frames`/`_valid_tenth`/`_is_game_over` (correct, less auditable than one stateful
  list) · M4 `_valid_tenth` lone-roll `return True` relies on `_is_game_over` refusing to end
  on one roll (subtle coupling) · M5 Security/Compliance N/A (no I/O/secrets).
  Rulings: all accepted/deferred; verified tree stays green at 31/31.
