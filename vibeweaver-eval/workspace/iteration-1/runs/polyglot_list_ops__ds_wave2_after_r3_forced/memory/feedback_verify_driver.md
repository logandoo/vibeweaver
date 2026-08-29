---
name: Verify via Driver Script + Differential Sweep
description: Validated verification approach — drive verification with python3 scripts outside test_* naming, log exit codes to .run.log, plus differential sweep vs independent oracles
type: feedback
date: 2026-08-29
---

# Verify via Driver Script + Differential Sweep

Confirmed approach for library exercises where the grader's tests must not be created/modified by us.

**Why:** The eval constraint forbids touching test files; a pytest-discoverable `test_*.py` would either be graded directly or contaminate the suite. TDD RED→GREEN via a custom driver is the verified loop; differential sweeps against independent builtin oracles catch subtle order/type bugs that pass unit tests.

**How to apply:** Name verification drivers `tests/verify_*.py` (plus `diff_sweep.py`, `consumer_smoke.py`, `import_check`), run with `python3`, tee exit code + summary to `tests/*.run.log`. Keep oracle checks type-exact (string vs string, list vs list) — earlier string/list type mismatches produced false FAILs.
