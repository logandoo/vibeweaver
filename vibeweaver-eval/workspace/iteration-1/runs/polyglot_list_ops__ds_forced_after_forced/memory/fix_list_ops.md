---
name: Fix — list_ops implemented from stubs
description: 8 list operations (append/concat/filter/length/map/foldl/foldr/reverse) implemented from pass stubs without built-in list-op functions; all canonical behavior verified.
type: fix
date: 2026-08-29
status: ✅
commit: 822fa13
---

# Fix: list_ops implemented from stubs

**Problem:** `list_ops.py` shipped as `pass` stubs for 8 list operations
(Exercism list-ops). Task: implement them "without using existing functions".

**Solution (validated):** hand-rolled loops + list concatenation; no
`len`/`map`/`filter`/`sum`/`reduce`/`reversed`/slicing. `foldr` reuses
`reverse(list)` then folds left-to-right with `function(acc, item)`.

**Key semantics (verified against hidden test suite):**
- `foldl`/`foldr` both call `function(acc, item)` — argument order significant.
- `foldr` traverses right-to-left (`foldr(lambda acc, el: el/acc, [1,2,3,4], 24) == 9`).
- `concat` flattens exactly one level; `reverse` does not flatten nested lists.

**Evidence:** RED run 1/25 (stub) → GREEN 25/25 acceptance; differential
sweep 1600/1600 vs built-in oracle; hidden `list_ops_test.py` 24/24.

**Deferred Minors (A4.9 reviewer, non-defects):** `reverse` is O(n²) via
`[item] + result`; `foldr` materializes a reversed copy (list input required);
parameter names `function`/`list` shadow builtins (mandated by stub);
`result.append` is a method, not a prohibited function. None block correctness.
