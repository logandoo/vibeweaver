# MULTI_AGENT.md — RunContext · Dual Gate · Lease/Fencing · Immutable Integration · Evidence Chain

R11 companion. Canonical protocol for MULTIPLE AGENTS developing in one
project concurrently. Read IN FULL when a RunContext is present, when the
task is one of several concurrent tasks, or when SKILL.md routes here.

**Legacy rule (non-negotiable):** with NO RunContext (no
`.vibeweaver/run_context.json`, no `VIBEWEAVER_RUN_CONTEXT` file), the
single-agent behavior of every existing contract is unchanged. Nothing in
this file relaxes any existing hard gate — multi-agent concurrency is never
a reason to verify less (§MA2 invariant two cuts BOTH ways: new
interactions need MORE verification, marked `UNVERIFIED` where unproven).

Sections: §MA1 identity & RunContext · §MA2 three invariants · §MA3 Task
Gate · §MA4 lease/fencing/takeover/cleanup · §MA5 immutable candidate &
Integration Gate · §MA6 evidence chain & archive · §MA7 memory/backlog/ADR
publication · §MA8 state machine & recovery · §MA9 trust tiers, worktree
limits, resource ownership.

---

## §MA1 Identity model & RunContext

<!-- verified-by: tests/test_run_control.py::test_claim_*, tests/audit_selftest W25 SECTION -->

**Identity fields (distinguish ALL of these — never collapse):**

| Field | Meaning |
|---|---|
| `task_id` | stable user/backlog task identity, `[A-Za-z0-9._-]{1,64}` |
| `run_id` | one task execution context; may span several change-waves |
| `attempt_id` | one execution/takeover attempt; a retry NEVER reuses an old attempt |
| `wave_id` | one change-wave inside a run (not 1:1 with tasks) |
| `lease_epoch` | monotonic int ≥ 1 — lease/fencing version |
| `review_id` | one independent review bound to an exact SHA |
| `integration_run_id` | one system integration + final acceptance |
| `session_id` | host-session attribute only — NEVER a substitute for run identity |

**RunContext** (controller-issued, schema `"vibeweaver-run-context/1"`,
written to `<state_root>/run_context.json`):

```json
{
  "schema": "vibeweaver-run-context/1",
  "repo_id": "controller-assigned-repository-id",
  "task_id": "task-123",
  "run_id": "run-<32hex>",
  "attempt_id": "attempt-<32hex>",
  "wave_id": "wave-<32hex>",
  "session_id": "ses-...",
  "lease_epoch": 1,
  "worktree_root": "/path/to/isolated-worktree",
  "artifact_root": "/path/to/isolated-artifacts",
  "state_root": "/path/to/isolated-state",
  "base_sha": "controller-recorded-base",
  "spec_hash": "immutable-specification-hash",
  "skill_version": "pinned-skill-version",
  "checker_digest": "pinned-checker-digest"
}
```

**Binding rules:**
1. RunContext is generated and validated by the controller
   (`scripts/run_control.py claim`) — NEVER trust an agent's own
   declaration; a forged/incomplete context is rejected and the session
   falls back to legacy mode with a recorded warning.
2. Bind at session creation, not guessed at first file write.
3. write · idle · compaction · resume · review · FCV · integration all use
   the SAME context.
4. The worktree path is not identity — paths move, `run_id` does not.
5. Process environment alone is not binding (one host process may carry
   several sessions) — the file + `session_id → run` mapping is.

## §MA2 Three architecture invariants ★

<!-- verified-by: scripts/mutation_sweep.mjs W25 SECTION -->

**Invariant one — candidate content consistency.** What is reviewed, tested,
archived, and pushed MUST be the same candidate tree/commit. If the platform
produces a different commit, record the full SHA mapping and re-satisfy the
verification requirements for the FINAL delivered tree.

**Invariant two — invalidation propagation.** Each of these INVALIDATES old
tests, old reviews, and old final gates: rebase/cherry-pick · conflict
resolution · lockfile regeneration · test/interface/contract changes ·
global ADR changes to affected constraints · skill, plugin, checker, hook or
effective-config updates · target-branch or queue-predecessor changes.

**Invariant three — expiry is not stop.** A lease expiring means the holder
lost scheduling eligibility — NOT that the old agent stopped writing. All
shared writes carry `attempt_id + lease_epoch` and the STORAGE side rejects
stale epochs (`StaleEpochError`). Cleanup only after the old attempt is
actually isolated — never on TTL alone.

## §MA3 Task Gate (author run)

<!-- verified-by: tests/acceptance.md W25 criteria 7 -->

Inside its own run, the author completes everything the single-agent
contract already requires: COV-9 baseline · tests + loop discipline · task
acceptance · applicable A4.9 review and FCV · run-level memory + final gate
· immediate archival of original evidence. Process files use the RUN's
artifact root (`<artifact_root>/acceptance.md`,
`<artifact_root>/verification_log.md`, …) — run-scoped, never shared fixed
paths across tasks.

The Task Gate proves only what that run covered. It never proves the
integration works.

## §MA4 Lease, fencing, takeover, cleanup

<!-- verified-by: tests/test_run_control.py::test_fencing_*, test_can_clean -->

- **Atomic claim** (`ControlPlane.claim`): transactional; returns
  `attempt_id + lease_epoch`; a second claim on an active lease raises
  `LeaseConflict`. `heartbeat` renews the lease but is NOT itself write
  authorization — every write is fenced by `lease_epoch`.
- **Fencing:** every shared write carries `attempt_id + lease_epoch` and the
  STORAGE side rejects stale epochs with `StaleEpochError`. State, latch,
  event, and leader-acquisition writes are always fenced; outbox,
  session-map, final-ref, and flag/child writes accept fencing kwargs and
  reject stale epochs when supplied (controller single-writer paths fence via
  the leader lease instead). Queue writes are integrator-side under
  `acquire_leader`. Client-side lease checks alone are insufficient.
- **Expiry & takeover (order matters):** ① stop scheduling new writes ②
  isolate + stop supervised processes (exact pgid, never pattern-kill) ③
  revoke credentials/ref-write access ④ confirm the old attempt is silent
  ⑤ preserve the scene + evidence ⑥ only then `takeover()` issues a NEW
  attempt with a HIGHER epoch.
- **PAUSED / Class-E / user confirmation carry `run_id/attempt_id`.** A
  user "continue" resumes ONLY the recorded default of the named run —
  never a broadcast resume of all paused tasks.
- **Cleanup preconditions (`ControlPlane.can_clean`, all seven):** code
  commit/ref reachable and handed off · handoff + integration evidence
  archived AND read back · untracked evidence included in the archive ·
  external side effects completed or reconciled · no live sub-agents/hooks/
  background processes · old attempt isolated · retention/approval
  satisfied. Any miss → cleanup blocked, resources retained.

## §MA5 Immutable candidate & Integration Gate

<!-- verified-by: tests/test_integrate.py -->

**Queue items freeze SHAs** (`IntegrationQueue.enqueue` — 40-hex only,
branch names rejected): `source_head_sha · target_base_sha · run_id ·
attempt_id · integration dependencies · spec_hash · verification bundle
hash`. A moving branch name is never queued.

**Integration steps:** ① author finishes product commit + task verification
+ run review ② original evidence archived immediately, run enters `ready`
③ queue selects by dependency + order ④ integrator builds a candidate
commit ON the latest target branch + prior queued changes
(`build_candidate`; stale/invalidated rows are never rebuildable) ⑤ conflicts
→ resolver per §MA5.1, new change-wave ⑥ full tests + Integration Gate on
the candidate — commands run in a detached worktree materialized at the exact
candidate SHA, results bound to that tree ⑦ archive candidate-bound
integration evidence ⑧ publish via expected-old-SHA conditional ref update
(`publish` — CAS; only a gate-passed candidate bound to the current queue
entry is publishable; a changed target raises `TargetChangedError`,
invalidates the verification, re-queues) ⑨ post-publish outbox updates
memory/backlog/ADR ⑩ reconcile, THEN clean. Force-push is never a normal
integration method.

**Integration Gate checks:** full tests on the combined result · interface
contract, migration order, global invariants · integration delta, conflict
hunks, cross-run interaction review · applicable FCV · the REAL vibeweaver
final gate (process files may be materialized into the integration worktree
for the unmodified gate to run — they must exist for real, never in product
commits) · an independent integration evidence bundle.

### §MA5.1 Conflict-resolution independence & coverage honesty

- Whoever resolves a conflict may NOT be its only reviewer. An author's
  resolution invalidates the old clean review.
- A new review binds a NEW exact SHA; ANY code change after review voids the
  approval.
- High-risk resolutions get a reviewer uninvolved in the implementation.
- Full tests passing ≠ all interactions proven: uncovered cross-run
  interactions are recorded `UNVERIFIED` — never laundered by "the suite is
  green" (§V3 semantics extend across runs).

## §MA6 Evidence chain & archive

<!-- verified-by: tests/test_run_aware_scripts.py -->

- Original run evidence is IMMUTABLE: base/head + verifier versions recorded
  at the time. After a rebase, append the old→new SHA mapping — never
  rewrite history evidence.
- Integration evidence is a SEPARATE bundle; it never inherits the original
  run's green verdicts.
- **Manifest fields** (evidence_seal): `repo_id · task_id · run_id ·
  attempt_id · wave_id · integration_run_id · spec_hash · acceptance_hash ·
  base_sha · original_head_sha · resolved_head_sha · candidate_sha ·
  final_commit_sha · tree_sha · final_tree_sha · dep_lock_digest ·
  env_digest · skill/plugin/checker/config/hook digests · test commands +
  results · review/FCV identities, scopes, verdicts · artifact hashes +
  archive locations · outbox/publication status`.
- **Integrity files travel TOGETHER:** evidence lock · test/secret/debt
  baselines · project profile · checker pin/digest · manifest/seal · gate
  result/audit · review/FCV files · every referenced media/trace. Run the
  original gate BEFORE archiving; after archiving verify bundle hash +
  readability (`evidence_lock.py --verify-archive`). Copying files is not
  re-passing the gate.
- Large media goes to an external evidence store (access control · content
  hash · conditional write · retention · recoverability checks · index by
  final commit/tree) — not bulk-copied into product git.

## §MA7 memory / backlog / ADR publication

<!-- verified-by: tests/test_run_control.py::test_outbox_* -->

- Run-local project memory is written normally (the current final gate keeps
  working). Shared mainline memory is consolidated by a curator/integrator —
  agents do NOT write it directly.
- User-global memory serves runs as a READ-ONLY snapshot during parallel
  work (no contention, no cross-project pollution).
- Unmerged/failed/aborted run lessons enter candidate/quarantine state —
  they never become project-level verified facts directly.
- Backlog: transactional claim + lease; status updates carry
  run/attempt/evidence refs; failures quarantine; retries create new
  attempts (history preserved).
- ADR: run-local reversible decisions archive as `(run_id, D-n)`; cross-run
  API/schema/security/architecture decisions get identities from a central
  ADR registry with `supersedes/conflicts/affects`. An AUTO agent NEVER
  unilaterally approves a global/irreversible ADR. Global ADR changes
  invalidate acceptance/base/verification of affected queued runs.
- **Transactional outbox (the reconciliation contract):** ① the integration
  transaction writes a pending outbox record ② a publisher consumes with
  retry ③ stable idempotency key (`<type>:<subject>:<intent>`) prevents
  double publication ④ a reconciler diffs git history vs run registry vs
  shared state ⑤ `cleaned` is unreachable while publication is incomplete.
- Ordering uses server-side versions/hashes — never agent-local clocks,
  mtime, or commit dates.

## §MA8 State machine & recovery

<!-- verified-by: tests/test_run_control.py::test_transition_* -->

Main path: `pending → leased → running → verifying → ready → integrating →
merged → published → cleaned`. Bypass states: `paused · blocked · expired ·
quarantined · stopping · aborted`. Transitions are CAS
(`ControlPlane.transition`); illegal jumps raise `InvalidTransition`.
Abnormal runs enter `quarantined` with a retention period — never force-
cleaned. Crash/recovery resumes from the registry state with the SAME
run/attempt ids (or a fresh attempt after takeover — §MA4).

## §MA9 Trust tiers · worktree limits · resources · git boundaries

<!-- verified-by: docs assertions + tests/test_resource_allocator.py -->

**Trusted agent (default) — worktree prevents accidents, not malice:**
per-attempt worktree + branch, fixed base commit, own index/HEAD, explicit
path staging only, no direct main writes, no force-push/history rewrite, no
shared repo maintenance. Keep worktrees OUTSIDE the main checkout.

**What worktrees do NOT give:** an agent can still escape via absolute
paths, `../`, symlinks, shell, `git -C`, `GIT_DIR`/`GIT_WORK_TREE`, shared
hooks. Add: filesystem/command sandbox, write-permission limits on the main
checkout and other worktrees, per-run ref-push rights, read-only shared git
config/hooks, agents never editing global audit/plugin/skill config.

**Untrusted agent:** independent clone · container/OS identity · per-run
HOME + credentials · no shared writable `.git` · external integrator
receiving patch/bundle · least-privilege network/service accounts.

**fork vs clone:** ordinary code conflicts resolve in the task branch or
integration worktree (never a new fork) · tool incompatibility / complex
submodules / independent git metadata → separate clone · external
contributors / no write access / separate governance → fork.

**Resource ownership (per attempt, `resource_allocator.py`):** ports,
sockets, PID/process groups (exact pgid reclamation — never pattern-kill),
temp dirs, containers/networks/volumes, DBs/schemas/test accounts, queue
topics/buckets, browser profiles, SSH/Docker credential refs, package
caches, CPU/memory/disk quotas. Scarce resources are centrally reserved —
never randomly picked. Non-namespaced resources (GPU, fixed licenses,
production singletons) need their own exclusive lease.

**External side effects:** agents never touch production write interfaces
by default · per-run sandboxes/service accounts/network policy · stable
idempotency keys carrying run/attempt/fencing info · retry must dedupe ·
reconciliation after expiry/crash · non-idempotent irreversible operations
require their own explicit authorization flow · DB migrations use
expand/contract with explicit ordering (git revert does not restore data).

**Git shared state:** worktrees share the object store, refs, and default
config — during active runs: NO `gc/prune/filter-repo` · hooks/shared config
are controller-hosted and version-pinned · repo hygiene and shared debt are
attributed centrally (a repo-level problem from one branch is not another
run's regression).

**submodules:** phase 1 FORBIDS ordinary runs touching submodules.
Recursive support (if ever added) requires per-run submodule branches ·
recursive status/diff/review · submodule SHA reachability · submodule merged
before superproject gitlink · final verification over the full recursive
SHA set.

**Distributed agents:** phase 1 is single-host only (explicitly). If needed:
independent clones · central coordinator for patches/bundles/evidence ·
transactional shared run registry/lease/queue · conditional-write evidence
store · server-side ordering · leader lease + fencing for multi-integrator
HA.

**Version pinning (§MA1 fields `spec_hash`/`skill_version`/`checker_digest`):**
runs pin skill/plugin/checker/hooks/config/global-memory snapshot/dep locks
at start. Verifier updates ship through separate release runs; active runs
keep their snapshot; unversioned in-place replacement is forbidden; old and
new plugins never co-write one state file; skill/checker updates invalidate
related old verification conclusions (§MA2 invariant two).
