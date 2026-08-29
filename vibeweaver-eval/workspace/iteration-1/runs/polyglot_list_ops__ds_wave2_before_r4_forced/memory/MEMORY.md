# Project Memory Index

## User Context
<!-- user type entries -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing -->

## Feedback — Corrections
<!-- feedback type: what to avoid -->

## Project Context
- Exercism "list-ops" exercise workspace
  (`polyglot_list_ops__ds_wave2_before_r4_forced`). Pure Python library module
  `list_ops.py`, no UI, no server. Task constraint: do NOT create or modify
  test files; hidden grader copies `list_ops.py` next to `list_ops_test.py`
  and runs `python3 -m pytest -q` on it alone. Workflow dirs `tests/`,
  `memory/`, `script/` are vibeweaver artifacts, not part of the graded module.

## External References
- Exercism Python list-ops hidden test suite:
  `workspace/iteration-1/tasks/polyglot_list_ops/hidden_tests/list_ops_test.py`
  (24 tests, canonical data 2023-07-19). Official reference implementation:
  `exercism/python` exercises/practice/list-ops/.meta/example.py.

## Fix Tracking
- ⏳ [Fix: list_ops implemented from stubs](fix_list_ops.md) — 8 list ops, no
  built-in list-op functions; 24/24 hidden + 2700/2700 differential pass.

## Key Dependencies & Conventions
- Grading flow: isolated graded-copy dir (module + hidden test), workspace
  test files untouched.
- Fold argument order is significant: both `foldl` and `foldr` call
  `function(acc, item)`; `foldr` traverses right-to-left (via `reverse`).
