# Project Memory Index

## User Context
<!-- user type entries -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing -->

## Feedback — Corrections
<!-- feedback type: what to avoid -->

## Project Context
- Exercism "list-ops" exercise workspace (`polyglot_list_ops__ds_forced_after_forced`).
  Pure Python library module `list_ops.py`, no UI, no server. Task constraint:
  do NOT create or modify test files; hidden grader injects `list_ops_test.py`
  and runs pytest on it alone.

## External References
- Exercism Python list-ops canonical instructions + test suite (fetched as data).

## Fix Tracking
- ✅ [Fix: list_ops implemented from stubs](fix_list_ops.md) — 8 list ops, no built-in list-op functions; verified 24/24 hidden + 1600/1600 differential.

## Key Dependencies & Conventions
- Grading copies `list_ops.py` into a fresh dir with the hidden test; artifact dirs `tests/`, `memory/`, `script/` are workflow outputs, not part of the module.
- Fold argument order is significant: both `foldl` and `foldr` call `function(acc, item)`; `foldr` traverses right-to-left.
