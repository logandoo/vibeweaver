commit c75d763

implement two-bucket measure via BFS state search


diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_forced_after_forced/two_bucket.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_forced_after_forced/two_bucket.py
index 7029bcb..819b6f6 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_forced_after_forced/two_bucket.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_forced_after_forced/two_bucket.py
@@ -1,2 +1,50 @@
+from collections import deque
+
+
 def measure(bucket_one, bucket_two, goal, start_bucket):
-    pass
+    if start_bucket == "one":
+        start_state = (bucket_one, 0)
+    else:
+        start_state = (0, bucket_two)
+
+    if start_state[0] == goal:
+        return (1, "one", start_state[1])
+    if start_state[1] == goal:
+        return (1, "two", start_state[0])
+
+    def forbidden(a, b):
+        if start_bucket == "one":
+            return a == 0 and b == bucket_two
+        return b == 0 and a == bucket_one
+
+    seen = {start_state}
+    queue = deque([(start_state, 1)])
+
+    while queue:
+        (a, b), moves = queue.popleft()
+
+        pour_one_to_two = min(a, bucket_two - b)
+        pour_two_to_one = min(b, bucket_one - a)
+
+        next_states = (
+            (bucket_one, b),
+            (a, bucket_two),
+            (0, b),
+            (a, 0),
+            (a - pour_one_to_two, b + pour_one_to_two),
+            (a + pour_two_to_one, b - pour_two_to_one),
+        )
+
+        for na, nb in next_states:
+            if (na, nb) in seen:
+                continue
+            if forbidden(na, nb):
+                continue
+            if na == goal:
+                return (moves + 1, "one", nb)
+            if nb == goal:
+                return (moves + 1, "two", na)
+            seen.add((na, nb))
+            queue.append(((na, nb), moves + 1))
+
+    raise ValueError("Goal is impossible to reach")
