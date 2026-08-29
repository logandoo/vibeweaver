# Project Memory Index

## User Context
<!-- No user-type entries yet -->

## Feedback — Validated Approaches
<!-- No feedback-type entries yet -->

## Feedback — Corrections
<!-- No corrections yet -->

## Project Context
- [Two Bucket Exercise](project_two_bucket.md) — Exercism two-bucket exercise in this workspace; canonical API + BFS approach

## External References
- [Exercism canonical tests](reference_exercism_two_bucket.md) — canonical test data source (bucket sizes 3/5, 7/11, goal edge cases)

## Fix Tracking
- ⏳ [Fix: Implement measure()](fix_two_bucket.md) — BFS state-search; 11/11 canonical + 1408-case differential pass

## Key Dependencies & Conventions
- `two_bucket.measure(bucket_one, bucket_two, goal, start_bucket)` returns `(moves, goal_bucket, other_bucket)`; raises `ValueError` when impossible
