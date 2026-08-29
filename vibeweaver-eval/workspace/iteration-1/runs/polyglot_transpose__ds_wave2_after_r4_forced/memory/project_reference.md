---
type: reference
topic: harness constraints + canonical spec
status: verified
date: 2026-08-29
---

# project_reference.md — transpose exercise (✅ Verified)

## Harness constraints
- Working dir: `polyglot_transpose__ds_wave2_after_r4_forced/`.
- Implement in `transpose.py` only; do NOT create/modify test files (grader
  owns the test suite).
- `prompt.md` = Exercism "transpose" problem statement (rows→columns; pad
  short rows left with spaces, never pad right; all input chars must survive,
  including real trailing spaces).
- Files in the eval workspace are NOT git-tracked (only `run.log` is); the
  `backup:` baseline commit belongs to sibling tasks. No `script/` directory —
  pure-function exercise, no build/service lifecycle (COV-2 = na).

## Canonical spec (authoritative)
- Reference solution (exercism `.meta/example.py`): sentinel-substitute spaces
  with `_`, pad right with `ljust`, `zip`-transpose, `rstrip`, restore `_`→space.
  Drawback: input containing `_` is corrupted — this repo's implementation
  avoids sentinels entirely.
- Canonical test expectations fetched from:
  `exercism/python .../exercises/practice/transpose/transpose_test.py` (12
  tests, incl. `test_mixed_line_length` which requires preserving `"h   "` —
  three REAL trailing spaces).

## Verifier
- Non-web runtime task (pure function) → preset `Verifier: direct read (non-web)`.
- Evidence model: CLI/function invocation transcript + exit code + on-disk log
  (`tests/verification_evidence.txt`).
