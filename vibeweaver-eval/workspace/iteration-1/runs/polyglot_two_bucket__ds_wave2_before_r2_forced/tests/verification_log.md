# Verification Log — Two Bucket (two_bucket.py)

## Task: Implement two_bucket.py measure() | 2026-08-29
- Baseline verified GREEN — stub `two_bucket.py` imports cleanly; no pre-existing failures to attribute (backup commit 16cf1b9).
- probe: model-native skipped — backend-only pure function, no media/screenshots to grade (COV-5 N/A per COV-6 analog); verifier = executed test suite with on-disk logs (§A4.8).
- iter 1 FAIL (RED, §A4.8): criteria 1-12 | diagnosis: stub returns None for every input — feature missing, expected failure | changed: (none yet, RED against stub)
  RED evidence (first failing run): "case 1: measure(3,5,1,'one') -> None | expected (4,'one',5) | FAIL ... RESULT: 0/11 passed, 11 failed"
- iter 2 PASS: criteria 1-12 — 11/11 canonical cases pass (evidence: tests/verify_run.log, case-by-case) | changed: two_bucket.py (BFS implementation)
  Scope: canonical test suite (11 cases) covering both start buckets, one-step goal, mid-flow fill, size extremes, unreachable goal, goal > both buckets.
- iter 3 PASS: criterion 13 (forbidden-state rule) + differential sweep — 1408 cases swept, 232 reachable-by-both, 0 mismatches vs independent deterministic reference (evidence: tests/differential_run.log) | changed: (none)
