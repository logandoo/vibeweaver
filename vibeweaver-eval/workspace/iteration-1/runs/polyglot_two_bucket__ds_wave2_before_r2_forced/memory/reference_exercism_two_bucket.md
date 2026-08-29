---
name: Exercism Two Bucket Canonical Reference
description: Canonical API + test data for the two-bucket exercise (raw.githubusercontent.com/exercism) — source of the expected (moves, goal_bucket, other_bucket) tuples
type: reference
date: 2026-08-29
---

# Exercism Two Bucket Canonical Reference

**Location:** https://raw.githubusercontent.com/exercism/python/main/exercises/practice/two-bucket/ and https://github.com/exercism/problem-specifications/tree/main/exercises/two-bucket

**Purpose:** Ground-truth API and expected outputs used to derive acceptance criteria. Canonical signature `measure(bucket_one, bucket_two, goal, start_bucket)` returning a tuple `(moves, goal_bucket, other_bucket)`; `ValueError` for unreachable goals. Rules: fill/empty/pour one action at a time; never end an action with the starting bucket empty and the other bucket full.
