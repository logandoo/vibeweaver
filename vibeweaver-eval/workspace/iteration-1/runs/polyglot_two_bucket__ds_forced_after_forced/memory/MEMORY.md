# Project Memory Index

## User Context
<!-- user type entries -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing -->

## Feedback — Corrections
<!-- feedback type: what to avoid -->

## Project Context
- Exercism "two-bucket" exercise workspace
  (`polyglot_two_bucket__ds_forced_after_forced`). Pure Python module
  `two_bucket.py`, no UI, no server. Task constraint: do NOT create or modify
  test files; hidden grader injects `two_bucket_test.py` and runs it against
  the module alone.

## External References
- Exercism Python two-bucket canonical instructions + `two_bucket_test.py` +
  problem-specifications `canonical-data.json` (fetched as data, 2026-08-29).

## Fix Tracking
- ✅ [Fix: two_bucket measure implemented from stub](fix_two_bucket.md) —
  BFS over (b1, b2) states, forbidden-state rule, first action fills start
  bucket; verified 13/13 acceptance, 1050/1050 differential, official suite 11/11.

## Key Dependencies & Conventions
- Grading imports `measure` from `two_bucket.py`; artifact dirs `tests/`,
  `memory/`, `script/` are workflow outputs, not part of the module.
- Forbidden-state rule: skip any state where the START bucket is empty AND the
  OTHER bucket is full — applied to intermediate transitions, not to the
  mandatory first fill of the start bucket.
- Impossible goals raise `ValueError` (unreachable / goal > both buckets).
