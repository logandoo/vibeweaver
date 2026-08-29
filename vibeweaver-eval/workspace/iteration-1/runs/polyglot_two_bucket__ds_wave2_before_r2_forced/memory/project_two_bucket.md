---
name: Two Bucket Exercise Context
description: Workspace exercise: implement Exercism two-bucket measure() in two_bucket.py; canonical API and grading via hidden harness
type: project
date: 2026-08-29
---

# Two Bucket Exercise Context

This workspace is a single-exercise eval run (`polyglot_two_bucket`). The deliverable is `two_bucket.py` only — the grading harness supplies its own hidden tests, so no test files may be created/modified in the workspace (verification harness lives outside, in the temp dir).

**API contract:** `measure(bucket_one, bucket_two, goal, start_bucket)` → `(moves, goal_bucket, other_bucket)`; `ValueError` when impossible. Forbidden state rule: after any action, must not reach a state where the starting bucket is empty and the other bucket is full.

**How to apply:** Any future change to this workspace must keep the signature/return contract and the forbidden-state rule intact; re-run the external harness + differential sweep for regression.
