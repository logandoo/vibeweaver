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

## A4.9 review (2026-08-29) — NOT REQUIRED
- A4.9 not triggered — verified via `git diff --stat d1dc499..HEAD`: 1 file changed (transpose.py), pure-function behavior on a single library file with no schema/API-surface/security/risk-tier implications; the entire change-wave test surface (12 canonical cases) re-run green. No independent review dispatched (single-file, no risk-tier paths, no cross-module interface).
