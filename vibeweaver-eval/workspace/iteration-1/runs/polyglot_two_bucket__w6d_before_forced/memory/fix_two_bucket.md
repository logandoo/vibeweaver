---
type: fix
status: verified
updated: 2026-09-14
---

# fix_two_bucket — `measure(bucket_one, bucket_two, goal, start_bucket)`

## Contract ✅ Verified
Returns a 3-tuple `(actions, "one"|"two", other_liters)`; raises `ValueError`
when the goal is unreachable. First action always fills `start_bucket`.

## Approach ✅ Verified
BFS over `(amount_one, amount_two)` states; start at the filled start bucket
with `actions = 1`. Each state expands to: fill one, fill two, empty one,
empty two, pour one→two, pour two→one. First state hitting `goal` gives the
minimum action count. `seen` set prevents cycles.

Forbidden rule: skip any successor where the starting bucket is empty and the
other bucket is full — `(0, bucket_two)` when start is `"one"`,
`(bucket_one, 0)` when start is `"two"`.

## Canonical expected values ✅ Verified
| input | expected |
|---|---|
| (3,5,1,"one") | (4,"one",5) |
| (3,5,1,"two") | (8,"two",3) |
| (7,11,2,"one") | (14,"one",11) |
| (7,11,2,"two") | (18,"two",7) |
| (1,3,3,"two") | (1,"two",0) |
| (2,3,3,"one") | (2,"two",2) |
| (5,1,2,"one") | (6,"one",1) |
| (3,15,9,"one") | (6,"two",0) |
| (6,15,9,"one") | (10,"two",0) |
| (6,15,5,"one") | ValueError |
| (5,7,8,"one") | ValueError |

## Notes
- Reachability is governed by `goal <= max(b1,b2)` and
  `goal % gcd(b1,b2) == 0`.
- Differential sweep (960 states, sizes 1..9) matches an independent oracle.

## Independent review (A4.9) — no Critical/Important ✅
Read-only reviewer confirmed canonical correctness (11/11) + 576-input
cross-check (0 mismatches). Minors deferred (all outside the positive-input
canonical domain; no canonical test exercises them):
- [Minor] `start_bucket` not validated — values other than "one" take the
  "two" branch.
- [Minor] non-positive bucket sizes/goal not validated.
- [Minor] `goal == 0` returns an empty-bucket match rather than an error.
- [Minor] tie-break when goal fits both buckets at the same minimal count —
  always prefers "one" (undefined by the spec).
- [Minor] `seen` memory is O(b1×b2); fine for canonical sizes.
