# A4.9 Review Package — list_ops.py

Repo: untracked eval sandbox (no git baseline; Commit = N/A). Diff reconstructed
from the original 30-line stub (read before modification) vs the delivered file.

## Task
Implement basic list operations in `list_ops.py` per `prompt.md`: `append`,
`concat`, `filter`, `length`, `map`, `foldl`, `foldr`, `reverse`, without
using existing built-in operations that do the whole job (len/sum/map/filter/
reduce/reversed). Fold argument order is significant: `foldl(function, list,
initial)` / `foldr(function, list, initial)`.

## Acceptance criteria
`tests/acceptance.md` (13 criteria) — canonical Exercism Python oracle values,
including direction-sensitive folds: `foldl(lambda acc,el: el/acc, [1,2,3,4], 24)==64`,
`foldr(...)==9`, `foldr(el+acc, [e,x,e,r,c,i,s,m], "!")=="exercism!"`,
one-level-only concat flattening, reverse without flattening.

## DIFF (stub → delivered)
```diff
--- list_ops.py (original stub)
+++ list_ops.py (delivered)
@@
-def append(list1, list2):
-    pass
+def append(list1, list2):
+    result = []
+    for item in list1:
+        result.append(item)
+    for item in list2:
+        result.append(item)
+    return result
@@
-def concat(lists):
-    pass
+def concat(lists):
+    result = []
+    for lst in lists:
+        for item in lst:
+            result.append(item)
+    return result
@@
-def filter(function, list):
-    pass
+def filter(function, list):
+    result = []
+    for item in list:
+        if function(item):
+            result.append(item)
+    return result
@@
-def length(list):
-    pass
+def length(list):
+    count = 0
+    for _ in list:
+        count += 1
+    return count
@@
-def map(function, list):
-    pass
+def map(function, list):
+    result = []
+    for item in list:
+        result.append(function(item))
+    return result
@@
-def foldl(function, list, initial):
-    pass
+def foldl(function, list, initial):
+    acc = initial
+    for item in list:
+        acc = function(acc, item)
+    return acc
@@
-def foldr(function, list, initial):
-    pass
+def foldr(function, list, initial):
+    acc = initial
+    for item in reverse(list):
+        acc = function(acc, item)
+    return acc
@@
-def reverse(list):
-    pass
+def reverse(list):
+    result = []
+    for item in list:
+        result.insert(0, item)
+    return result
```

## Verification evidence
- `tests/verification_run.log`: 24/24 executed canonical cases pass (exit 0).
- `script/linux/start.sh` smoke check → `smoke check OK`.
- `python3 -m py_compile list_ops.py` → exit 0.

## Files changed (all)
list_ops.py (logic) · tests/acceptance.md · tests/verification_log.md ·
tests/verification_run.log · tests/assert_artifacts.py (copied canonical) ·
tests/probe_vision.png (probe artifact) · script/linux/{start,stop,restart}.sh ·
memory/{MEMORY.md,list_ops.md}
