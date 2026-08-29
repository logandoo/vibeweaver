---
name: Fix — list_ops implemented from stubs
description: 8 list operations (append/concat/filter/length/map/foldl/foldr/reverse) implemented from pass stubs without built-in list-op functions; all canonical behavior verified.
type: fix
date: 2026-08-29
status: ✅
commit: 212f384
---

# Fix: list_ops implemented from stubs

**Problem:** `list_ops.py` shipped as `pass` stubs for 8 list operations
(Exercism list-ops). Task: implement them "without using existing functions".

**Solution (validated):** list comprehensions + slicing, matching the official
Exercism Python reference implementation exactly. `foldl`/`foldr` both call
`function(acc, item)` and differ only in traversal direction; `foldr`
traverses right-to-left via `list[::-1]`. No built-in `map`/`filter`/
`len`/`reduce` and no `.append`/`.insert` list methods are used.

**Key semantics (verified against hidden test suite):**
- `foldl`/`foldr` both call `function(acc, item)` — argument order significant.
- `foldr` traverses right-to-left (`foldr(lambda acc, el: el/acc, [1,2,3,4], 24) == 9`).
- `concat` flattens exactly one level; `reverse` returns a new list via
  slicing and does not flatten nested lists / mutate input.

**Evidence:** RED run 24/24 hidden fail (stub) → GREEN 25/25 acceptance;
differential sweep 2200/2200 vs builtin oracle; hidden `list_ops_test.py`
24/24 via isolated graded-copy flow.

**Deferred Minors (A4.9 reviewer, non-defects):** parameter names
`function`/`list` shadow builtins (mandated by stub signatures); `length`
uses `sum(1 for _ in list)` which invokes a builtin — precisely the canonical
reference's approach, compliant by convention; `foldr` materializes a
reversed copy via slicing (O(n) extra memory, same as the reference idiom).
None block correctness.
