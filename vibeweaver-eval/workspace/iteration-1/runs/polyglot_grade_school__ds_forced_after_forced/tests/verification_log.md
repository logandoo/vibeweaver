# Verification Log

## Task: implement the `School` roster in `grade_school.py` (Modify-Existing, backend-only pure class)

- Baseline verified GREEN — stub `grade_school.py` compiles (`python3 -m py_compile` exit 0) and imports; the module is a pure library with no service/UI/build runtime in this exercise workspace, so there is no build/start service to baseline-test (COV-9 baseline entry recorded).
- COV-9 note: no git baseline commit made — the run directory is fully untracked (`?? ./`) inside the parent repo; the harness does not require a commit for this exercise (Commit column = N/A).

### Verifier probe (COV-5)
- `mm_probe.py` is NOT installed in this skill distribution (skill dir contains only `SKILL.md`; `scripts/` absent) → probe step 1 cannot run. No `vision.py` (mm-sensor) listed → step 2 unavailable. → **Verifier: direct read** — backend-only task with no UI/media; evidence = executed-test output logs inspected on disk (`tests/verification_run.log`, `tests/verification_run_red.log`, `tests/smoke_run.log`), cross-checked by re-reading the implementation.
- Companion rulebooks (TESTING_PROTOCOLS.md / COMPLETION_GATE.md / REFERENCE.md) are not shipped in this install; the inline binding text of SKILL.md (§A4.1/§A4.4/§A4.7) is applied, following the sibling run's recorded artifact pattern.

### Loop iterations
- iter RED FAIL: criteria #1–#8 — hidden suite run against the unmodified stub fails 20/20 (`AssertionError: None != ['Chelsea', 'Logan']`, `Ran 20 tests … FAILED (failures=20)`, log: `tests/verification_run_red.log`) | diagnosis: stub methods return `None`/do nothing; no state exists to answer `roster()`/`grade()`/`added()` | changed: (stub, pre-implementation — A4.8 RED evidence).
- iter 1 PASS: criteria #1–#8 — implementation in `grade_school.py` (dict[grade]->set + global name-set + per-call result log); hidden suite 20/20 OK (`tests/verification_run.log`, exit 0) + `script/linux/start.sh` smoke check OK (`tests/smoke_run.log`, exit 0), covering empty roster, True/False add returns, `added()` order log, grade-then-name sort, per-grade sort, same-grade duplicate rejection, cross-grade duplicate rejection | changed: `grade_school.py` (full implementation), `script/linux/{start,stop,restart}.sh`.

### A4.9 independent review (COV-8)
- Dispatched read-only reviewer over `grade_school.py` (stub→implementation is a behavior-semantic change). Verdict: **Contract satisfied: yes**; Critical: none; Important: none.
- Minor 1 (grade param unused on duplicate rejection) → ruling: accepted by design — rejection is name-based across all grades, so grade is intentionally not used on the reject path.
- Minor 2 (name-hashing assumption) → ruling: accepted by design — names are strings per the exercise contract. Minors recorded to `memory/grade_school.md`.

## FRESH run on final tree
- `python3 -m py_compile grade_school.py` → exit 0 (no syntax errors).
- `bash script/linux/start.sh` (smoke check on final tree, COV-2 lifecycle) → exit 0, `smoke check OK`.
- Hidden suite re-run on final tree via inline unittest loader (no test files created/modified) → `Ran 20 tests … OK`, exit 0.
