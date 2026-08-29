# Verification Log

## Task: implement Robot Name in `robot_name.py` (Modify-Existing, backend-only pure library)

- Baseline verified GREEN — stub `robot_name.py` (`class Robot: def __init__(self): pass`) compiles (`python3 -m py_compile` exit 0) and constructs (`Robot()` OK). The only pre-existing failure is the start.sh smoke check (`AttributeError: no attribute 'name'`) — that IS the task (feature unimplemented in the stub), not a regression. No build/service/UI runtime exists in this exercise workspace, so there is no build/start step to baseline-test beyond py_compile + construct (COV-9 baseline entry recorded).
- COV-9 baseline commit made, scoped to this run dir only: `b2ab5c0 backup: before changes` (`git add -A .` from the run directory — no unrelated harness changes staged).

### Verifier probe (COV-5)
- `mm_probe.py --generate` run (wrote `tests/probe_vision.png`); the Read tool returned `ERROR: Cannot read image (this model does not support image input)` → behavioral probe FAIL. No `vision.py` (mm-sensor) installed. → **Verifier: direct read (non-web)** — backend-only library task, no UI media captured; evidence = executed-check run log (`tests/verification_run.log`) + exit codes, cross-checked against `robot_name.py` source.

### TDD RED evidence (A4.8 — run against the stub BEFORE implementation)
- Spec-derived verification (kept inline via `python3 - <<EOF`, no test files written into the workspace per the harness "no test files" constraint) against the stub produced the expected failure:
  - criterion 2: AttributeError: 'Robot' object has no attribute 'name'
  - SUMMARY: 1/7 passed (criterion 1 = imports/constructs PASS; criteria 2–7 FAIL)

### Loop iterations
- iter 1 PASS: criteria #1–#7 — 7/7 executed checks in `tests/verification_run.log` all PASS (format regex `^[A-Z]{2}[0-9]{3}$`; name stable across reads; distinct across instances; reset yields new valid name; 500-robot uniqueness sweep; non-sequential prefix variety — 350 distinct 2-letter prefixes / 401 distinct digit suffixes on 500-sample); extended sweep: 3000 more robots unique, 200 sequential resets all valid + different-from-prev, 3500 total names unique; changed: `robot_name.py` (stub → full implementation).

## FRESH run on final tree
- `python3 -m py_compile robot_name.py` → exit 0 (no syntax errors).
- `bash script/linux/start.sh` (smoke check on final tree) → OK (`smoke check OK: YN624`).
- `bash script/linux/restart.sh` + `bash script/linux/stop.sh` → OK.
- `tests/verification_run.log` re-run after all edits on final tree → 7/7 PASS, 0 failed (runner exit 0).
