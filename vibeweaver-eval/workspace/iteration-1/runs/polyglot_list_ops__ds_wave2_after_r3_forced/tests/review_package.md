# A4.9 Review Package — list_ops exercise

## Diff (working tree list_ops.py vs baseline c049cf3)

```diff
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_list_ops__ds_wave2_after_r3_forced/list_ops.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_list_ops__ds_wave2_after_r3_forced/list_ops.py
index 6497809..69c0222 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_list_ops__ds_wave2_after_r3_forced/list_ops.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_list_ops__ds_wave2_after_r3_forced/list_ops.py
@@ -1,30 +1,58 @@
 def append(list1, list2):
-    pass
+    result = []
+    for item in list1:
+        result.append(item)
+    for item in list2:
+        result.append(item)
+    return result
 
 
 def concat(lists):
-    pass
+    result = []
+    for lst in lists:
+        for item in lst:
+            result.append(item)
+    return result
 
 
 def filter(function, list):
-    pass
+    result = []
+    for item in list:
+        if function(item):
+            result.append(item)
+    return result
 
 
 def length(list):
-    pass
+    count = 0
+    for _ in list:
+        count += 1
+    return count
 
 
 def map(function, list):
-    pass
+    result = []
+    for item in list:
+        result.append(function(item))
+    return result
 
 
 def foldl(function, list, initial):
-    pass
+    accumulator = initial
+    for item in list:
+        accumulator = function(accumulator, item)
+    return accumulator
 
 
 def foldr(function, list, initial):
-    pass
+    accumulator = initial
+    for item in reverse(list):
+        accumulator = function(accumulator, item)
+    return accumulator
 
 
 def reverse(list):
-    pass
+    result = []
+    for item in list:
+        result.insert(0, item)
+    return result

```

## Acceptance criteria (tests/acceptance.md)

> cap=5  stall=3×

# Acceptance Criteria — list_ops exercise (C7 non-web library)

Verifier: direct read (non-web). Each criterion is a yes/no checkable on
observable function output via the verification driver transcript.

1. `append(list1, list2)` returns a new list containing all items of list1
   followed by all items of list2; neither input list is mutated.
2. `concat(lists)` returns a single flattened list combining all items from
   all lists in the given series, in order.
3. `filter(function, list)` returns a new list of all items for which
   `function(item)` is True, preserving order.
4. `length(list)` returns the total number of items in the list (0 for an
   empty list).
5. `map(function, list)` returns a new list of `function(item)` applied to
   every item, preserving order.
6. `foldl(function, list, initial)` folds from the left, calling
   `function(accumulator, item)` for each item in order, returning the final
   accumulator.
7. `foldr(function, list, initial)` folds from the right, calling
   `function(accumulator, item)` over items in reverse order, returning the
   final accumulator.
8. `reverse(list)` returns a new list with all original items in reversed
   order; the input list is not mutated.
9. Every operation is implemented by explicit iteration/construction — none
   delegates to a builtin higher-order list operation (map/filter/reduce/
   sorted/sum/reversed as the implementation).
10. The module imports cleanly (`python3 -c "import list_ops"`) with no
    syntax or runtime errors, and handles empty-list edge cases.
11. No file matching the exercise test-suite discovery patterns
    (`test_*.py` / `*_test.py`) is created or modified; the verification
    driver is named `verify_list_ops.py` to stay out of pytest collection.


## Verification evidence

verify_green.run.log: [PASS] C1 append basic — got [1, 2, 3, 4]
[PASS] C1 append empty-second
[PASS] C1 append empty-first
[PASS] C1 append both-empty
[PASS] C1 append no-mutation — a=[1, 2] b=[3, 4]
[PASS] C2 concat basic
[PASS] C2 concat three
[PASS] C2 concat empty-series
[PASS] C2 concat empty-lists
[PASS] C3 filter evens
[PASS] C3 filter all-true
[PASS] C3 filter none-true
[PASS] C3 filter empty
[PASS] C4 length basic
[PASS] C4 length empty
[PASS] C4 length singleton
[PASS] C4 length strings
[PASS] C5 map double
[PASS] C5 map str
[PASS] C5 map empty
[PASS] C6 foldl sum
[PASS] C6 foldl concat
[PASS] C6 foldl empty
[PASS] C6 foldl sub-order
[PASS] C7 foldr concat
[PASS] C7 foldr sub-order
[PASS] C7 foldr empty
[PASS] C7 foldr order-sens
[PASS] C7 foldl order-sens
[PASS] C8 reverse basic
[PASS] C8 reverse empty
[PASS] C8 reverse singleton
[PASS] C8 reverse no-mutation — s=[1, 2, 3]
[PASS] C9 no-builtin-delegation — clean
[PASS] C11 no grader test files — none

RESULT: ALL PASS

diff_sweep.run.log: DIFF-SWEEP: ALL AGREE (405 base cases x sweeps, no mismatches)

consumer_smoke.run.log: CONSUMER-SMOKE: PASS — pipeline (map→filter→length→foldl→reverse→concat→foldr) OK
