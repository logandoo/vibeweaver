# workflow_run_decisions.md — vibeweaver decisions for this run

## Run facts
- Run dir: `vibeweaver-eval/workspace/iteration-1/runs/polyglot_two_bucket__ds_wave2_after_r4_forced`
- Task kind: Modify-Existing, single-file library (C7 non-web); Mode: AUTO; Verifier: direct read (non-web).
- Profile: library → service lifecycle (group 5), UI, and new-project design docs (groups 6-8) are N/A.

## ADR D-1 — approach (BFS)
Chosen over closed-form modular arithmetic and greedy pour. See memory/two_bucket_kata.md.

## ADR D-2 — evidence mode (CLI transcript + differential sweep)
No browser UI, no HTTP surface → Playwright screenshots and API-doc loop are N/A.
C7 observable-output evidence = CLI invocations with exit codes + differential sweep
vs an independently-written reference.

## ADR D-3 — acceptance strictness
Pinned each canonical expected tuple as its own criterion (tests/acceptance.md) AND added an
exhaustive differential sweep to guard against shared-assumption bugs (independent reference
self-checked against the canonical cases before being trusted).

## ADR D-4 — no design docs
COV-10 skipped: single-function kata, contract fully pinned by canonical test data; no new
project, no schema, no multi-module interdependencies. Design docs disproportionate.

## Evidence files (tests/)
- acceptance.md (12 criteria, first line `> cap=5  stall=3×`)
- verification_log.md (baseline GREEN, RED iter 1, GREEN iters 2-5)
- decisions.md (D-1..D-4), project_profile.json ({"profile":"library"})
- verify_red.run.log, verify_green.run.log, diff_sweep.run.log, consumer_smoke.run.log
- review_package.md (independent reviewer APPROVE)
- assert_artifacts.py (canonical copy from vibeweaver/scripts/)
