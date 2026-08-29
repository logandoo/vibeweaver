# two_bucket kata — implementation notes

## Problem contract
`measure(bucket_one, bucket_two, goal, start_bucket) -> (moves, "one"|"two", other_liters)`
- First move always fills the start bucket (counts as 1 action).
- Each action = fill / empty / pour (single operation), counts as 1 move.
- Never arrive at a state where the start bucket is empty AND the other bucket is full.
- `ValueError` when goal unreachable.

## Algorithm (chosen in ZERO — D-1)
Breadth-first search over state `(liters in one, liters in two)`.
- Start state: `(bucket_one, 0)` for start "one", else `(0, bucket_two)`; moves = 1.
- Goal check on a state: either amount == goal → return `(moves, bucket, other_amount)`.
- Forbidden state (start empty ∧ other full) is skipped before the goal check so it is never
  entered and never counted as a goal.
- Neighbors: fill one, fill two, empty one, empty two, pour one→two, pour two→one
  (self-loop pours guarded by `pour > 0` to guarantee termination).
- Frontier exhaustion → `ValueError("No more moves!")`.

## Why BFS (alternatives rejected)
- BFS provably yields minimum moves — canonical suite asserts exact counts
  (e.g. (4,"one",5), (14,"one",11), (18,"two",7)).
- Closed-form modular-arithmetic pour sequence is correct but must special-case
  which bucket ends with the goal + the forbidden state + start-bucket semantics (error-prone).
- Greedy fixed pour sequence is not optimal in general.

## Verification evidence (2026-08-29)
- `tests/verify_green.run.log` — 9 canonical value + 2 ValueError cases, ALL PASS.
- `tests/diff_sweep.run.log` — 1152 inputs (b1 1..8 × b2 1..8 × both starts × goals 1..b1+b2),
  0 mismatches vs an independently-written reference BFS (reference self-checked against the
  11 canonical cases first).
- `tests/consumer_smoke.run.log` — downstream import works.
- `py_compile two_bucket.py` — OK.
- Independent reviewer verdict: APPROVE (`tests/review_package.md`).

## Key canonical expectations to remember
- (3,15,9,"one") → (6,"two",0) but (6,15,9,"one") → (10,"two",0): same buckets/goal,
  different start → different move count and goal bucket.
- (5,1,2,"one") → (6,"one",1): the "obvious" path to (2,0) is blocked by the forbidden
  state (0,1); the solution runs through (2,1) at move 6 — the forbidden rule changes path
  viability, not just entry legality.
- (6,15,5,"one") raises (5 not a multiple of gcd(6,15)=3); (5,7,8,"one") raises (goal > both caps).

## Out-of-scope robustness (accepted)
- `start_bucket` not validated (anything ≠ "one" treated as "two").
- goal 0 / capacity 0 not handled (not part of the exercise).
