# MEMORY.md

Transpose exercise workspace (polyglot benchmark, `polyglot_transpose__ds_wave2_after_r3_forced`).

## Index
- [transpose.md](transpose.md) — implementation, verified approach, baseline facts.

## Rules
- Do NOT create or modify test files; hidden suite lives in `tasks/polyglot_transpose/hidden_tests/` and is run from /tmp copies.
- Grader command: `python3 -m pytest -q` with `transpose_test.py` (canonical Exercism, 12 tests).
- Module API must be `from transpose import transpose`.

## Session
- Mode: AUTO · Verifier: direct read (non-web).
- Companion files R1/R2/R1b/R9 not shipped in this config (only SKILL.md); verify scripts (mm_probe.py/vision.py) absent — assert_artifacts.py reused from sibling run's verified copy (D-3).

## A4.9 review (2026-08-29) — APPROVED
- 0 Critical / 0 Important / 4 Minor (Bugs): M1 dead `if not rows:` guard → FIXED (removed, iter 2 re-verified green); M2 trailing-strip invariant (`len(line)-1` row index holds only because join emits one char/row) → accepted, documented in transpose.md; M3 while-loop readability → accepted as-is; M4 no docstring → accepted (behavior-only deliverable). Reviewer also fuzz-verified 50,000 cases vs independent reference (0 failures).
