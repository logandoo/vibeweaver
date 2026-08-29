# Project Memory Index

## User Context
<!-- user type entries -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing -->

## Feedback — Corrections
<!-- feedback type: what to avoid -->

## Project Context
- Exercism "list-ops" exercise workspace
  (`polyglot_list_ops__ds_wave2_after_forced`). Pure Python library module
  `list_ops.py`, no UI, no server. Task constraint: do NOT create or modify
  test files; hidden grader injects `list_ops_test.py` and runs pytest on it
  alone. Workflow dirs `tests/`, `memory/`, `script/` are vibeweaver
  artifacts, not part of the graded module.

## External References
- Exercism Python list-ops instructions + hidden test suite
  (workspace/iteration-1/tasks/polyglot_list_ops/hidden_tests/list_ops_test.py, 24 tests).

## Fix Tracking
- ✅ [Fix: list_ops implemented from stubs](fix_list_ops.md) — 8 list ops, no
  built-in list-op functions; 24/24 hidden + 2200/2200 differential pass.

## Key Dependencies & Conventions
- Grading copies `list_ops.py` into a fresh dir with the hidden test; the
  graded-copy flow keeps workspace test files untouched.
- Fold argument order is significant: both `foldl` and `foldr` call
  `function(acc, item)`; `foldr` traverses right-to-left.
