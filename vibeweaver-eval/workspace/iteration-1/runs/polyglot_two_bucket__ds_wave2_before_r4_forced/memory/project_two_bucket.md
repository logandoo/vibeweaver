---
name: Two Bucket exercise — project context
description: Exercism two-bucket kata; measure() semantics, forbidden-state rule, and the verification approach used in this run
type: project
date: 2026-08-29
---

# Two Bucket exercise

**Why:** This run workspace implements the Exercism "Two Bucket" exercise as a
single-file library task (`two_bucket.py`). No UI, no service, no config, no
`script/` lifecycle.

**Semantics of `measure(bucket_one, bucket_two, goal, start_bucket)`:**
- Returns `(actions:int, goal_bucket:"one"|"two", other_liters:int)`.
- Raises `ValueError` when the goal is unreachable.
- Exactly three action types; one action at a time; any change to either/both
  buckets counts as one action; the first fill of the start bucket counts as
  action 1.
- Forbidden after-action state: the starting bucket is empty AND the other
  bucket is full.

**How to apply:** Keep the BFS approach (minimal actions by construction). Do
NOT add test files to the workspace — the verification harness lives in the
temp dir (`tb_verify/`). Ground truth = Exercism canonical-data cases plus a
differential sweep against an independent label-correcting solver.
