# Project Memory Index

## Project Context
- [project_two_bucket.md](project_two_bucket.md) — Two Bucket exercise: `measure()` implemented via BFS over `(bucket_one, bucket_two)` state graph; semantics and verification approach

## Fix Tracking
- ⏳ [Fix: Two Bucket measure() — implement BFS solution](fix_two_bucket_measure.md) — Stub → working `measure()`; BFS shortest-path; `ValueError` on unreachable; canonical + differential sweep GREEN

## Key Dependencies & Conventions
- Task forbids test files inside the workspace — the verification harness lives in the temp dir (`/var/folders/.../T/opencode/tb_verify/`); `tests/` holds only evidence artifacts.
- Exercism canonical-data is the ground truth for expected values (fetched via webfetch, treated as data).
