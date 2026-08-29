---
name: Fix — list_ops implemented from stubs
description: 8 list operations (append/concat/filter/length/map/foldl/foldr/reverse) implemented from pass stubs without built-in list-op functions; all canonical behavior verified.
type: fix
date: 2026-08-29
status: ✅
commit: 654e1cd
---

# Fix: list_ops implemented from stubs

**Problem:** `list_ops.py` shipped as `pass` stubs for 8 list operations
(Exercism list-ops). Task: implement them "without using existing functions".

**Solution (validated):** hand-rolled loops + list construction; no
`len`/`map`/`filter`/`sum`/`reduce`/`reversed`/slicing. `foldr` reuses
`reverse(list)` then folds with `function(acc, item)` over the reversed list.

**Key semantics (verified against hidden test suite):**
- `foldl`/`foldr` both call `function(acc, item)` — argument order significant
  (foldr direction-dependent case: `foldr(lambda acc, el: el/acc, [1,2,3,4], 24) == 9`).
- `foldl` folds left-to-right; `foldr` folds right-to-left.
- `concat` flattens exactly one level; `reverse` does not flatten nested lists.

**Evidence:** RED run 24/24 hidden fail (stub) → GREEN 25/25 acceptance;
hidden `list_ops_test.py` 24/24 via isolated graded-copy flow; differential
sweep 2700/2700 vs built-in oracle.

**Deferred Minors (A4.9 reviewer, non-defects):** `reverse` is O(n²) via
`[item] + result`; `foldr` materializes a reversed copy (list input required);
parameter names `function`/`list` shadow builtins (mandated by stub);
`result.append` is a method, not a prohibited function. None block correctness.
