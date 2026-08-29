> cap=5  stall=3×

# Acceptance Criteria — Two Bucket (polyglot_two_bucket__ds_wave2_before_r4_forced)

Source: `prompt.md` (Fullstack Academy two-bucket exercise) + Exercism
problem-specifications `exercises/two-bucket/canonical-data.json` (fetched via
webfetch, treated as data per COV-11; approach still passed §2 Step 0.2).

| # | Criterion | Verification method | Status |
|---|-----------|---------------------|--------|
| 1 | `measure(bucket_one, bucket_two, goal, start_bucket)` returns `(actions:int, goal_bucket:"one"/"two", other_liters:int)` for every reachable goal | execution: canonical cases + differential sweep | ☑ |
| 2 | all 9 reachable canonical cases match the exact expected tuples | execution: canonical harness in temp dir | ☑ |
| 3 | both unreachable canonical cases raise `ValueError` | execution: canonical harness in temp dir | ☑ |
| 4 | first fill of the starting bucket counts as action 1 (e.g. `(1,3,3,"two") → (1,"two",0)`) | execution: canonical harness | ☑ |
| 5 | forbidden-state rule respected — no action may end at start-empty + other-full | execution: BFS transition construction + differential sweep | ☑ |
| 6 | no test files created or modified inside the workspace; the verification harness lives in the temp dir | filesystem listing | ☑ |
