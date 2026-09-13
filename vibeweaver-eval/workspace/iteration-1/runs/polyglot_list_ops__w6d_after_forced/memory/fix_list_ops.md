---
type: fix
status: verified
tags: [list-ops, python, exercise]
---

# list_ops — basic list operations

## ✅ Verified
- Implemented `append`, `concat`, `filter`, `length`, `map`, `foldl`, `foldr`,
  `reverse` in `list_ops.py` using plain loops/recursion, without the matching
  Python built-ins (`map`, `filter`, `reduce`, `len`, `reversed`, slicing).
- `foldl` and `foldr` both call the callback as `function(acc, el)` (Python-track
  convention); `foldr` folds from the right by iterating a reversed copy. This
  argument-order detail is the exercise's documented trap.
- `concat` flattens exactly one level (nested lists stay as items).
- Verification: 24/24 canonical criteria pass, exit 0 (`tests/run_checks.log`).

## Notes
- No build/start lifecycle; COV-2 N/A (decisions.md D-2).
- `tests/assert_artifacts.py` not available in this exercise/skill install.

## Minor (independent review, deferred — no correctness impact)
- `result = result + [item]` in loops is O(n²) for very large inputs; use
  `.append`/in-place growth if throughput ever matters. Not a criterion failure.
- `reverse` calls `length(list)` first; fine here, could fold into a single pass.

## ❌ Failed directions
- (none)
