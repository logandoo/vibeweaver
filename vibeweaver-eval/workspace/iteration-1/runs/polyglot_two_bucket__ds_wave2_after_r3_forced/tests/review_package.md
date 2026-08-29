# Review Package — two_bucket.measure (Exercism two-bucket kata)

**Change type:** new feature (stub -> BFS implementation), behavior-semantic.

## Contract under review (from prompt.md / official exercism spec)

`measure(bucket_one, bucket_two, goal, start_bucket)` returns
`(num_actions, goal_bucket_in_["one","two"], liters_in_other_bucket)`:
- start: fill the `start_bucket` (counts as 1 action); action = pour (until source empty or dest full), fill, or empty a bucket; any change to either/both buckets = 1 action
- forbidden state: after any action, the start bucket must NOT be empty while the other bucket is full
- impossible goals raise ValueError (message non-empty)

## Diff under review

```diff
+from collections import deque
+
+
 def measure(bucket_one, bucket_two, goal, start_bucket):
-    pass
+    capacities = (bucket_one, bucket_two)
+    start_index = 0 if start_bucket == "one" else 1
+
+    initial = [0, 0]
+    initial[start_index] = capacities[start_index]
+
+    forbidden = [0, 0]
+    forbidden[1 - start_index] = capacities[1 - start_index]
+
+    def possible_next_states(a, b):
+        states = [
+            (capacities[0], b),
+            (a, capacities[1]),
+            (0, b),
+            (a, 0),
+            (max(0, a - (capacities[1] - b)), min(capacities[1], a + b)),
+            (min(capacities[0], a + b), max(0, b - (capacities[0] - a))),
+        ]
+        return states
+
+    queue = deque([(tuple(initial), 1)])
+    visited = {tuple(initial)}
+
+    while queue:
+        state, actions = queue.popleft()
+        if goal in state:
+            goal_index = state.index(goal)
+            goal_bucket = "one" if goal_index == 0 else "two"
+            return actions, goal_bucket, state[1 - goal_index]
+
+        for next_state in possible_next_states(*state):
+            if next_state == tuple(forbidden) or next_state in visited:
+                continue
+            visited.add(next_state)
+            queue.append((next_state, actions + 1))
+
+    raise ValueError("No more moves!")
```

## Reviewer task
Read-only. Independently analyze the diff for correctness bugs against the
contract above. Pay special attention to:
1. correctness of both pour formulas (amount = min(source, capacity_dest - dest))
2. forbidden-state exclusion for BOTH start buckets
3. goal-in-start-bucket-at-start => 1 action
4. minimality (BFS), termination (visited), impossibility => ValueError
5. any edge case the author's 1152-input sweep could have missed (e.g. goal
   equal to forbidden-state volume, self-loops, start bucket label validation)
Return: verdict (APPROVE / REQUEST-CHANGES with severity list), each finding
with file:line and a concrete failing input if any.
