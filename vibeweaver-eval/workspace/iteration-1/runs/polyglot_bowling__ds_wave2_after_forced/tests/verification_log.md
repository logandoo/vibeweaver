# Verification Log

## Task: implement Bowling scoring in `bowling.py` (Modify-Existing, backend-only pure library)

- Baseline verified GREEN — starter stub `bowling.py` compiles (`python3 -m py_compile bowling.py` exit 0) and `BowlingGame()` constructs with bound `roll`/`score` methods; no behavior implemented, as expected for a stub (31/31 hidden tests fail on the stub by design, not as a regression — ADR-1). No build/service/UI runtime exists in this exercise workspace (pure library), so there is no build/start step to baseline-test (COV-9).
- COV-9 baseline commit scoped to this run dir: `796962b backup: before changes`.

### Verifier (COV-5)
- Backend-only pure-library task → no UI/media to capture; evidence = executed test transcripts + exit codes. `mm_probe.py`/`vision.py` not shipped in this skill install (only SKILL.md; checked via `ls -la` of the skill dir → 1 file) → **Verifier: direct read (non-web)**; maker/checker split preserved via an independent frame-object reference scorer.

### Loop iterations
- iter 1 PASS: criteria #1-#14 — implementation written (Approach A: flat rolls list + `_frame_state()`/`_is_complete()` walkers + frame-walk `score()`; validation at `roll()` time). Evidence:
  - `tests/canonical_run.log` — `31 passed in 0.01s`, exit 0 (covers criteria #1-#12, all 31 canonical cases incl. every validation contract).
  - `tests/differential_run.log` — `score mismatches: 0/5000`, `roll-validation mismatches: 0/4000`, `incomplete-score mismatches: 0/2000` vs independent reference (criterion #13 cross-check, 11000 total comparisons).
  - Perfect game sanity: `python3 -c ...` → `300` (criterion #6).
  - Criterion #14: no test files created/modified in workspace — suites run from `/var/folders/.../T/opencode/bowling_verify/` copies; workspace `tests/` holds logs only (verified via `ls` + `git status`).
  changed: bowling.py
- Fresh-run on final committed tree: `tests/fresh_run.log` → 31/31 passed post-commit.

### Lifecycle (COV-2)
- `bash script/linux/restart.sh` → exit 0, `smoke check OK: perfect game = 300` (`tests/restart_run.log`).
