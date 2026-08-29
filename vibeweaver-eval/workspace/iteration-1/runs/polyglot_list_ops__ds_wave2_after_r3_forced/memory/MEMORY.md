# Project Memory Index

## User Context
- [Eval Workspace Agent](user_role_prefs.md) — Autonomous agent in a vibeweaver eval workspace: implement exercises, no test-file creation/modification, verify via on-disk logs

## Feedback — Validated Approaches
- [Verify via Driver Script + Differential Sweep](feedback_verify_driver.md) — Name verification scripts outside test_*/*_test patterns (avoid pytest collection), drive with python3, log exit codes to .run.log files

## Fix Tracking
- ⏳ [Fix: list_ops 8 operations](fix_list_ops.md) — Implemented all 8 ops with explicit iteration (no builtin higher-order delegation); RED→GREEN TDD, 33/33 driver, 405-case differential sweep, consumer smoke PASS. Awaiting grader confirmation.

## External References
- [Exercism list-ops spec](reference_exercism_listops.md) — Canonical API: append(l1,l2), concat(lists), filter(fn,l), length(l), map(fn,l), foldl(fn,l,init), foldr(fn,l,init), reverse(l); folds call fn(acc, item)
