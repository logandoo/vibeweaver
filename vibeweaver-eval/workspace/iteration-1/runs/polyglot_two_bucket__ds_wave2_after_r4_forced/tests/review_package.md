# Review Package — two_bucket.measure (A4.9)

## Change scope
- File: `two_bucket.py` — stub (`def measure(...): pass`) → full BFS implementation.
- Type: new feature (behavior-semantic change). Risk tier: low (pure function, no auth/security/payment paths, stdlib only).

## Reviewer
Independent reviewer agent (fresh context, research-only; executed the full official suite against the file, hand-traced 3 cases).

## Verdict: APPROVE

## Findings
1. All 11 canonical cases pass when executed against the official suite.
2. Hand-traced (3,5,1,"one") → (4,"one",5): (3,0)→fill2 (3,5)→…→(1,5) at move 4; forbidden (0,5) correctly skipped.
3. Hand-traced (2,3,3,"one") → (2,"two",2): fill two from (2,0) → (2,3) at move 2.
4. Hand-traced (1,3,3,"two") → (1,"two",0): start (0,3) already matches goal → 1 move.
5. (5,1,2,"one") → (6,"one",1) confirms the forbidden rule affects path viability, not just entry — the direct path to (2,0) runs through forbidden (0,1) and is correctly excluded.
6. Termination: finite state space (b1+1)(b2+1), `seen` set, self-loop pours guarded by `pour > 0`, ValueError when frontier exhausts.
7. Forbidden rule checked before goal (never entered, never counted as goal), correct for both start buckets.
8. Move counting: start fill = 1; each transition +1; no off-by-one.

## Out-of-scope notes (accepted for this exercise)
- `start_bucket` not validated (anything ≠ "one" treated as "two").
- goal 0 would trivially match an empty bucket; no capacity-0 handling.

## Verifier coverage (independent of reviewer)
- Differential sweep vs independently-written reference BFS: 1152 inputs, 0 mismatches (`tests/diff_sweep.run.log`).
- Canonical verification: ALL PASS (`tests/verify_green.run.log`).
- Consumer smoke import (`tests/consumer_smoke.run.log`); `py_compile` OK.

## Approval
No changes required. Findings 1-8 confirmed by re-running `tests/verify_green.run.log` and `tests/diff_sweep.run.log` after review.
