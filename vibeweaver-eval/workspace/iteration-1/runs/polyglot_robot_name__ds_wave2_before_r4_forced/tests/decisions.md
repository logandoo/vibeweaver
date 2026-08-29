# AUTO decisions — polyglot_robot_name (Robot Name)

Mode: AUTO (COV-12). Each auto-decision below is a CLASS-I stop resolved by ADR.

## ADR D-1 — Acceptance criteria derivation
- Class-I trigger: criteria were not pre-listed as a numbered checklist in the
  request.
- Resolution: take criteria 1–4 verbatim from the request's explicit words
  (format, stick, different robots differ, reset yields new name); criterion
  5 adds the request's "random, not predictable" requirement as an empirically
  checkable uniqueness/variation sweep. Recorded in tests/acceptance.md.
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
- Evidence: tests/baseline_stub.run.log (4 failed in 0.03s).

## ADR D-3 — Web research skip
- Class-I trigger: ZERO mandates web research (exa MCP / Context7); the exa MCP
  returned HTTP 429 on both attempts.
- Resolution: state-skip. The task is a fully-specified, canonical Exercism
  kata ("Robot Name") whose contract is fixed by prompt.md AND the authoritative
  hidden test suite on disk; there is no external API, ecosystem, or unknown
  surface to research. Sibling run polyglot_robot_name__ds_wave2_after_r3_forced
  applied the same skip for the same task. Approach evaluation (D-4) still
  documents ≥2 options.
- Evidence: 2x HTTP 429 from mcp.exa.ai (ZERO step); decisions.md this ADR.

## ADR D-4 — Implementation approach
- Options evaluated:
  A) eager name generation in `__init__` + class-level `_used_names` set +
     collision-retry loop (chosen)
  B) lazy `name` property generating on first access
  C) pre-generate the full 676k-name namespace up front
- Why A: simplest correct shape for the hidden suite; name exists immediately
  after construction (`test_has_name` reads `Robot().name`), so a lazy property
  buys nothing here; the collision-retry loop is exactly what makes the seeded
  reset test pass (re-seeded RNG reproduces the already-used candidate → loop
  skips it → new name differs). B is marginally more code for no hidden-test
  benefit. C is YAGNI (676k precomputed strings for no benefit). The `while
  True` loop is bounded on `_NAMESPACE_SIZE` (676k) and raises RuntimeError on
  exhaustion (incorporates the after_r3 A4.9 review finding up front).
- Evidence: implementation in robot_name.py; hidden suite + smoke both green.

## ADR D-5 — Verifier: direct-read (no UI, no mm-probe)
- Class-I trigger (COV-5): verification method must be announced.
- Resolution: this is a backend-only Python library — zero browser-rendered
  output, zero media. Playwright/mm-sensor/multimodal-probe are inapplicable
  (A4.1.1/§A4.7: media grading is for UI-visible changes). Evidence is
  executed-test stdout on disk (baseline/hidden/smoke logs), read directly.
- Evidence: tests/*.run.log; `Verifier: direct-read` in the gate line.
