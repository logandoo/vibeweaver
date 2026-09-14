# Decisions — Two Bucket

## D-1 BFS over the full state space (chosen)
Model each state as the ordered pair `(amount_in_one, amount_in_two)`, seed the
queue with the mandated first fill of the starting bucket at cost 1, and expand
the six actions (fill/empty either bucket, pour either direction). BFS returns
the minimum action count on the first goal hit. Rejected alternative: a
closed-form gcd/arithmetic path — correct only for the reachable-liter count and
hard to reconcile with the "starting bucket empty and other full" forbidden
state, which the oracle exercises. BFS maps the rules directly and is small.

## D-2 Forbidden-state filter applied before the goal check
Rule 3 forbids arriving at a state where the start bucket is empty and the other
is full. The filter is applied to every generated state *before* the goal test,
so a goal that coincides with that forbidden state is never returned.

## D-3 Impossible goals raise `ValueError`
`prompt.md` does not name an error type; the trusted oracle requires
`ValueError` with a non-empty message (regex `.+`). BFS exhaustion plus an
up-front `goal > max(bucket_one, bucket_two)` guard both raise `ValueError`.

## D-4 COV-9 baseline recorded as skipped
The starter is an unimplemented `pass` stub, so a GREEN pre-change baseline is
structurally impossible. The honest record is a pre-change RED baseline plus a
`COV-9 skipped` entry (see verification_log.md).

## D-5 Project profile = library
No service/UI lifecycle exists. `tests/project_profile.json` declares `library`,
which declaratively skips the service-lifecycle group rather than weakening any
applicable check.
