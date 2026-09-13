# Verification Log — robot_name

Verifier: direct read (non-web) — no browser-rendered output; no `mm_probe.py`/`mm-sensor` available.
E2E depth: service-direct (in-process library invocation).
COV-9 skipped — reason: new single-file exercise, no pre-existing runtime to baseline-test.

## Wave 1 — implement `Robot` (lazy name + shared registry)

- iter 1 PASS: criteria #1–#5 | evidence: `tests/acceptance.md`; inline harness run on final tree
  (canonical `name_re = ^[A-Z]{2}\d{3}$`, seeded reset test, 5000-robot uniqueness stress, 1000 resets)
  → stdout `total unique names generated: 6000` / `ALL CHECKS PASSED` / `exit=0`.
  diagnosis: n/a (first pass, no failures).

[Convergence] robot_name: 1 iter | 5/5 pass | 0 stalls | 0 cap-hits
