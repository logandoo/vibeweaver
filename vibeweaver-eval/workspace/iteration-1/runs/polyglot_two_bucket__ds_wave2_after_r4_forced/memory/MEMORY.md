# MEMORY.md — project memory index

## Topics

- [two_bucket kata — implementation notes](two_bucket_kata.md)
- [Vibeweaver workflow decisions for this run](workflow_run_decisions.md)

## Current state (2026-08-29)

`two_bucket.measure(bucket_one, bucket_two, goal, start_bucket)` implemented via
BFS over (liters_one, liters_two) states; 11/11 canonical Exercism cases pass;
1152-input differential sweep vs independent reference BFS: 0 mismatches;
independent review APPROVED. See memory/two_bucket_kata.md for details.

## Project facts

- Deliverable: single-file Python library module `two_bucket.py` (no UI, no HTTP, no service lifecycle).
- Profile: library — script/ lifecycle, UI, and new-project design docs are N/A.
- Canonical expected values: official Exercism `two_bucket_test.py` (fetched 2026-08-29).
- Gate tokens on completion: `HARD-GATE-1: NO-TEST-NO-DONE=pass`, `HARD-GATE-2: SCRIPT-ONLY=na`.
