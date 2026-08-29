# Auto-Decisions — Two Bucket (polyglot_two_bucket__ds_wave2_before_r4_forced)

Mode: AUTO (COV-12). Every auto-decision below was taken without an explicit
user confirmation; each is recorded per §A4.4 (6).

## ADR-001 — Algorithm: BFS over the (bucket_one, bucket_two) state graph

- Context: `measure()` must return the minimum action count, the goal bucket,
  and the other bucket's liters, honoring the forbidden after-action state.
- Decision: Breadth-first search from the initial state (fill of the start
  bucket = action 1), first hit is minimal by construction.
- Alternatives rejected: gcd/number-theory closed form (error-prone around
  forbidden-state rule and goal-bucket determination); classic
  fill/pour/empty alternating loop (not optimal in general, e.g.
  `(2,3,3,"one")` yields 8 actions vs the true optimum 2).

## ADR-002 — Verification harness lives in the temp dir, not the workspace

- Context: the task forbids creating/modifying any test files in the
  workspace (`tests/` in the workspace holds only evidence artifacts:
  acceptance.md, verification_log.md, decisions.md, assert_artifacts.py).
- Decision: the executable harness (canonical cases + differential sweep)
  lives in `/var/folders/.../T/opencode/tb_verify/` and imports the workspace
  module via `sys.path`.

## ADR-003 — Differential reference: independent label-correcting solver, set-based

- Context: BFS vs BFS would not be independent; a naive single-answer
  reference produced false mismatches when multiple optimal solutions exist
  with different "other" values (e.g. `(1,2,1,"two")`: `(1,1)` vs `(1,2)`).
- Decision: reference = Bellman-Ford-style relaxation over the full state
  set; comparison accepts the set of all optimal outcomes
  `(min_actions, goal_bucket, other)`; plus a rule-level legal-path
  simulation of the reconstructed path.

## ADR-004 — assert_artifacts.py run profile

- Context: this is a modify-existing (stub → implementation), library-style,
  UI-less exercise; no `script/` service lifecycle exists.
- Decision: run `python3 tests/assert_artifacts.py --existing --backend-only
  --profile library` — `--profile library` declaratively skips the
  structurally-N/A service-lifecycle group; `--existing` skips new-project
  design-doc/git-init gates; `--backend-only` skips PAGE design checks.
