---
name: Fix list_ops 8 operations
description: Implemented Exercism list_ops in list_ops.py (append/concat/filter/length/map/foldl/foldr/reverse) via explicit iteration, no builtin higher-order delegation. RED->GREEN TDD. Awaiting grader.
type: fix
date: 2026-08-29
status: ⏳
commit: 697f026
---

# Fix: list_ops 8 operations

**Problem:** The stub `list_ops.py` returned `None` for all 8 required list operations (`append`, `concat`, `filter`, `length`, `map`, `foldl`, `foldr`, `reverse`); hidden grader tests would fail on every assertion.

**Root Cause:** Placeholder stubs — functions declared but empty (implicit `None` returns).

**Correct Fix:** Implemented each operation with explicit `for`-loop iteration / index math — no delegation to builtin higher-order functions (`map`/`filter`/`reduce`/`len`), no slicing. `foldl`/`foldr` call the function as `fn(acc, item)` (arg order significant). `foldr` reuses module `reverse` then folds left. `concat` flattens nested lists via `extend`.

**Failed Approaches (DO NOT retry):**
- iter 2 verify-driver oracle asserted `foldr(sub) != foldl(sub)` to check fold order — logically impossible because subtraction is order-invariant under full reversal (a-b-c == a-c-b); assertion fails for ANY correct implementation. Fix: order-sensitive string-consing checks ("123"/"321").
- iter 3 differential-sweep string-order checks compared a string result against a list oracle (type mismatch) and consumer_smoke expected the wrong foldr string. Fix: compare string-vs-string, expected `"".join(reversed(s))` for foldr.

**Rejected Alternatives (deferred, non-functional):**
- `reverse` via `insert(0, item)` is O(n²) — acceptable for test-scale data, kept for simplicity.
- Parameter names `list`/`function` shadow builtins — kept, matches canonical exercise naming.
- `foldr` materializes a reversed copy — benign for list-ops sizes.
- `foldr` relies on `reverse` defined later in module — safe at call time.
- No argument validation — same as reference implementations.

**Files:** `list_ops.py`
**Status:** ⏳ Pending — awaiting grader confirmation
