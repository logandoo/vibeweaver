# MEMORY.md — project memory index

- Last updated: 2026-08-29
- Project: two_bucket exercise (polyglot_two_bucket__ds_wave2_after_r3_forced)
- Stack: Python 3.9 (standard library only)

## Topics
- [fix_two_bucket.md](fix_two_bucket.md) — ✅ Verified: canonical Exercism "Two Bucket" implementation.

## Session notes
- `measure(bucket_one, bucket_two, goal, start_bucket)` returns `(actions, "one"|"two", other_liters)`; start bucket starts FULL (counts as 1 action); forbidden state = start bucket empty while the other is full (must be pruned, never returned); impossible goals → ValueError with non-empty message.
- BFS over `(amount_one, amount_two)` states from the filled-start state with `visited` enqueue-time marking guarantees minimal action count; only 6 actions (fill/empty x2, pour x2 with `amount = min(source, cap_dest - dest)`).
- Verified: 11/11 canonical cases pass (incl. goal==start-capacity → 1 action `(1,3,3,"two")==(1,"two",0)`; unreachable `(6,15,5,"one")` and `(5,7,8,"one")` raise ValueError); 1152-input differential sweep vs independent reference BFS = 0 mismatches. Independent A4.9 review: APPROVE (1 minor non-blocking note: start_bucket label not validated — spec guarantees "one"/"two").
- Exercism test file expects non-empty ValueError message (`assertRaisesWithMessage` / `r".+"`); `"No more moves!"` satisfies it.
