# Review Package — two_bucket measure() implementation (A4.9)

- **Upstream (A4.4.3):** acceptance criteria `tests/acceptance.md`; iteration log `tests/verification_log.md` (iter 1 FAIL RED, iter 2 PASS canonical, iter 3 PASS differential).
- **Diff range reviewed:** `git diff 16cf1b9..0d632b3` scoped to this workspace directory (baseline `backup: before changes` → implementation commit). Sibling-run commits inside the range are excluded from this package.
- **Change-wave stat (scoped):** 5 files changed, 456 insertions, 1 deletion:
  - `two_bucket.py` (+57/-1 — behavior-semantic change: stub → full implementation)
  - `tests/acceptance.md` (new, 23 lines)
  - `tests/verification_log.md` (new, 10 lines)
  - `tests/verify_run.log` (new, evidence)
  - `tests/differential_run.log` (new, evidence)
- **Trigger(s):** new feature · ≥3 files changed · behavior-semantic change.

## Verdict Contract (reviewer must follow)

1. READ-ONLY: review only, never modify any file.
2. Read `two_bucket.py` (current tree) + this package's diff below.
3. Answer: Strengths · Critical / Important / Minor findings (dimension-tagged Bugs / Security / Compliance, Minors itemized ≤5, each with `file:line` + why) · Assessment (verdict: pass with minors / fix Critical-Important then re-review / reject).
4. Key contract points to verify:
   - Signature/return contract: `measure(bucket_one, bucket_two, goal, start_bucket)` → `(moves, goal_bucket, other_bucket)`; `ValueError` when impossible.
   - Canonical forbidden-state rule: after any action, must NOT arrive at a state where the starting bucket is empty AND the other bucket is full.
   - Initial state = starting bucket filled counts as move 1; goal-check on start state returns `(1, start_bucket, other)`.
   - BFS minimality, visited-set correctness, both pour directions, fill/empty on all states.
   - Edge cases: `goal == 0`, goal equals a bucket capacity, goal > both capacities, unreachable goals, equal capacities, start_bucket invalid value (not part of contract — ignore).

## Diff (scoped)

```diff
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_wave2_before_r2_forced/two_bucket.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_wave2_before_r2_forced/two_bucket.py
index 7029bcb..80ce299 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_wave2_before_r2_forced/two_bucket.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_wave2_before_r2_forced/two_bucket.py
@@ -1,2 +1,59 @@
+from collections import deque
+
+
 def measure(bucket_one, bucket_two, goal, start_bucket):
-    pass
+    capacities = (bucket_one, bucket_two)
+    start_index = 0 if start_bucket == "one" else 1
+
+    start_state = [0, 0]
+    start_state[start_index] = capacities[start_index]
+
+    forbidden = [0, 0]
+    forbidden[1 - start_index] = capacities[1 - start_index]
+
+    def is_goal(state):
+        return state[0] == goal or state[1] == goal
+
+    if is_goal(start_state):
+        other = start_state[1 - start_index]
+        return (1, start_bucket, other)
+
+    visited = {tuple(start_state)}
+    queue = deque([(start_state[0], start_state[1], 1)])
+
+    while queue:
+        v1, v2, moves = queue.popleft()
+        for nxt in next_states(v1, v2, capacities):
+            if nxt == tuple(forbidden):
+                continue
+            if nxt in visited:
+                continue
+            visited.add(nxt)
+            nv1, nv2 = nxt
+            if is_goal((nv1, nv2)):
+                if nv1 == goal:
+                    return (moves + 1, "one", nv2)
+                return (moves + 1, "two", nv1)
+            queue.append((nv1, nv2, moves + 1))
+
+    raise ValueError("The goal amount cannot be measured.")
+
+
+def next_states(v1, v2, capacities):
+    cap1, cap2 = capacities
+    states = []
+    if v1 < cap1:
+        states.append((cap1, v2))
+    if v2 < cap2:
+        states.append((v1, cap2))
+    if v1 > 0:
+        states.append((0, v2))
+    if v2 > 0:
+        states.append((v1, 0))
+    if v1 > 0 and v2 < cap2:
+        pour = min(v1, cap2 - v2)
+        states.append((v1 - pour, v2 + pour))
+    if v2 > 0 and v1 < cap1:
+        pour = min(v2, cap1 - v1)
+        states.append((v1 + pour, v2 - pour))
+    return states
```

## Full iteration log (evidence the reviewer may cross-check)

`tests/verification_log.md` — baseline GREEN; probe note (backend-only, no media); iter 1 FAIL RED (0/11, diagnosis: stub returns None); iter 2 PASS (11/11 canonical, `tests/verify_run.log`); iter 3 PASS (1408-case differential sweep, 232 reachable-by-both, 0 mismatches, `tests/differential_run.log`).
