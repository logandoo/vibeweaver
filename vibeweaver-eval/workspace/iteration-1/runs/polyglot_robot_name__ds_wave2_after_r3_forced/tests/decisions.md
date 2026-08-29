# AUTO decisions — polyglot_robot_name (Robot Name)

Mode: AUTO (COV-12). Each auto-decision below is a CLASS-I stop resolved by ADR.

## ADR D-1 — Acceptance criteria derivation
- Class-I trigger: criteria were not pre-listed as a numbered checklist in the
  request.
- Resolution: take criteria 1–4 verbatim from the request's explicit words
  (format, stick, different robots differ, reset yields new name); criteria
  5–6 add the request's "random, not predictable" requirement as empirically
  checkable uniqueness/variation sweeps. Recorded in tests/acceptance.md.
- Evidence: tests/acceptance.md criteria table (each criterion names its
  verifiable how).

## ADR D-2 — Baseline RED (stub) is the task, proceed
- Class-I trigger (COV-9 / C2 Step 5): baseline run against the scaffold stub
  FAILED all 4 hidden tests (AttributeError: no attribute 'name').
- Resolution: proceed. The pre-existing failures are the deliverable itself —
  the exercise ships as an unimplemented scaffold whose only defect is that
  the feature is missing; every failure is IN task scope (nothing out-of-scope
  to quarantine). First verification_log entry records the baseline honestly
  with its scope note.
- Evidence: tests/baseline_stub.run.log (4 failed in 0.02s).

## ADR D-3 — Implementation approach
- Options evaluated:
  A) lazy `name` property + class-level `_used_names` set + collision-retry
     loop (chosen)
  B) eager name generation in `__init__`
  C) pre-generate the full 676k-name namespace up front
- Why A: matches Exercism canonical example; only generates on first access
  (cheap for the many tests that never read `name`); the collision-retry loop
  is exactly what makes the seeded reset test pass (re-seeded RNG reproduces
  the already-used candidate → loop skips it → new name differs). B is
  marginally simpler but couples name generation to construction. C is YAGNI
  (67.6k * 10k = 676k precomputed strings for no benefit).
- Evidence: implementation in robot_name.py; hidden suite + smoke both green.
