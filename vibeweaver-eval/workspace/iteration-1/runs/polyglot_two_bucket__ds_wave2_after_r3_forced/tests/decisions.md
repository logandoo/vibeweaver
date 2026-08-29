# AUTO-mode decisions — two_bucket.measure

## D-1 | 2026-08-29 | ZERO
trigger: I3 — approach selection (≥2 evaluated per §2 ZERO)
options: (a) BFS over states from filled-start state (b) closed-form modular-arithmetic pour sequence (c) greedy fixed pour sequence
chosen: (a) BFS
why: BFS provably returns the minimum action count (the canonical test set asserts exact counts, e.g. (4,"one",5) and (14,"one",11)); the forbidden-state rule ("start bucket empty + other full" unreachable) is enforced by a single exclusion check; stdlib-only (deque). Closed-form (b) risks non-minimal paths and special-casing the "goal in start bucket = 1 action" and forbidden-state edges; greedy (c) is not optimal in general.
revisit-if: any canonical case yields a non-minimal count, or a reachable goal raises ValueError

## D-2 | 2026-08-29 | ZERO
trigger: I3 — verification/evidence mode for a non-web library task (C7)
options: (a) Playwright/screenshot capture (b) API-doc loop (A4.7) (c) CLI-transcript evidence (C7)
chosen: (c) CLI-transcript + exit-code + differential-sweep evidence
why: the change has no browser UI and no HTTP API surface — C7's observable-output evidence is the structurally correct channel; screenshots/mm-sensor are N/A
revisit-if: the deliverable gains a UI or HTTP surface

## D-3 | 2026-08-29 | ZERO
trigger: I2 — acceptance-criteria strictness (canonical expected values were confirmed from the official exercism spec, not invented)
options: (a) assert only "matches spec" (b) pin each canonical expected tuple as an independent criterion + an exhaustive differential sweep
chosen: (b) pin canonical tuples AND run an independent-reference differential sweep
why: the hidden grader runs the canonical test file; pinning exact tuples + sweeping against an independently-written BFS guards against shared-assumption bugs (A4.8 red flag / §A4.10 TRUST-AND-VERIFY)
revisit-if: a canonical expected value differs from the official spec
