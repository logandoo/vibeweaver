# Eval harness facts

- Grading: `harness/grade_polyglot.py` copies the run workdir, injects
  `hidden_tests/bowling_test.py`, then runs `python3 -m pytest -q`.
- The deliverable is `bowling.py`; the harness does not require any artifact files,
  but the vibeweaver gate requires them for compliance.
- Do not create or modify test files in the deliverable. The oracle is executed from an
  isolated temp dir (`/tmp/bowling_verify`) so nothing test-related ships.
- Workspace is untracked inside the parent eval repo, so no baseline commit is made
  (COV-9 recorded as skipped).
