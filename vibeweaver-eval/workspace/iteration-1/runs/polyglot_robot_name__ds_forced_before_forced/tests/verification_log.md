# Verification Log — Robot Name

## polyglot_robot_name (iteration-1 run: ds_forced_before_forced)

- Baseline verified GREEN — `python3 -c "import robot_name; Robot()"` on the stub ran without error; scoped backup commit `af04f6e` (repo root is harness repo; `git add -A` would stage unrelated untracked eval data, so the commit was scoped to `robot_name.py`).
- iter 1 RED: hidden test `robot_name_test.py` run against the stub in a temp copy — `4 failed in 0.03s` (`AttributeError: 'Robot' object has no attribute 'name'`) — A4.8 RED evidence.
- iter 1 GREEN: implemented `robot_name.py` (lazy `name` property + class-level `used_names` set, names kept forever). Hidden test in temp copy: `4 passed in 0.01s`, pytest exit 0 — exact grader command (`python3 -m pytest -q robot_name_test.py`). Changed: robot_name.py.
- iter 1 PASS (robustness, `tests/verification_run.log`): format over 500 robots PASS · 500 unique PASS · name sticks PASS · double-reset distinct PASS · re-seed+reset different PASS · fresh-robot None PASS. Changed: none.
- iter 1 PASS (syntax/runtime): `python3 -m py_compile robot_name.py` OK · standalone `python3 robot_name.py` exit 0 · import+use prints correct sample.
- iter 1 summary: criteria 1–5 all PASS on iteration 1; no stalls, no cap hits.
