# Verification Log — two_bucket.measure

## Task: implement two_bucket.measure (Exercism two-bucket kata) | 2026-08-29

- Baseline verified GREEN — stub `two_bucket.py` imports cleanly and `measure(3,5,1,'one')` executes (returns `None` placeholder, exit 0); no existing test suite/build to run (no script/, no tests/ at baseline)

## Test-first (A4.8) evidence

- probe: Verifier = direct read (non-web) — library task, no UI, no HTTP; evidence = CLI transcripts + exit codes + output diffs under tests/

### RED (tests/verify_red.run.log, exit 0 = correctly 0/11 passing)
- `--red` against the stub: 0/11 canonical cases pass, 11/11 FAIL (all return `None` placeholder) → RED observed on-disk

### GREEN (tests/verify_green.run.log, exit 0)
- `--green` after implementing BFS: 11/11 canonical cases pass:
  - measure(3,5,1,"one")==(4,"one",5) · measure(3,5,1,"two")==(8,"two",3)
  - measure(7,11,2,"one")==(14,"one",11) · measure(7,11,2,"two")==(18,"two",7)
  - measure(1,3,3,"two")==(1,"two",0) · measure(2,3,3,"one")==(2,"two",2)
  - measure(5,1,2,"one")==(6,"one",1) · measure(3,15,9,"one")==(6,"two",0) · measure(6,15,9,"one")==(10,"two",0)
  - measure(6,15,5,"one") and measure(5,7,8,"one") each raise ValueError with non-empty message

### Differential sweep (tests/diff_sweep.run.log, exit 0)
- `--sweep`: 1152 inputs (bucket pairs 1..8 × goals 1..a+b × both start buckets) vs an INDEPENDENT reference BFS (self-checked against all 11 canonical cases first) → **0 mismatches** on action count, goal bucket, and other-amount (incl. ValueError/ValueError agreement)

### C7 downstream check (tests/consumer_smoke.run.log, exit 0)
- throwaway consumer script imports `two_bucket` from the workspace and calls measure(3,5,1,"one") → (4,"one",5)

### Fresh run on final tree (tests/fresh_run.log, exit 0)
- `python3 -m py_compile two_bucket.py` OK · `import two_bucket` OK · `--green` re-run → 11/11 pass

## A4.9 review (COV-8 — new feature, behavior-semantic change)
- review dispatch: independent reader-opinion over the two_bucket.py diff (tests/review_package.md)
- verdict: **APPROVE** — no correctness bugs; all 6 focus points (pour formulas, forbidden-state both starts, 1-action start-goal, BFS minimality/termination/ValueError, edge cases incl. goal==forbidden volume and self-loops, sweep gaps) verified; cross-checked against official canonical-data.json
- adjudication: 1 minor non-blocking note (start_bucket label not validated; spec guarantees "one"/"two", no canonical test exercises it) → accepted as-is, no change required; no REQUEST-CHANGES findings
