---
type: fix
status: verified
tags: [list-ops, python, exercise]
---

# list_ops — basic list operations

## ✅ Verified
- Implemented `append`, `concat`, `filter`, `length`, `map`, `foldl`, `foldr`,
  `reverse` in `list_ops.py` without using Python built-ins for those operations.
- `foldl` and `foldr` both pass the callback as `function(acc, el)`
  (Python-track convention); `foldr` folds from the right by iterating a
  reversed copy.
- `concat` flattens exactly one level (nested lists are preserved as items).
- Verification: 24/24 canonical Exercism criteria pass (`tests/run_checks.log`).

## Notes
- No build/start lifecycle exists for this exercise; COV-2 is N/A.
- `tests/assert_artifacts.py` unavailable in the skill installation (scripts/
  missing); gate run manually.

## ❌ Failed directions
- (none)
