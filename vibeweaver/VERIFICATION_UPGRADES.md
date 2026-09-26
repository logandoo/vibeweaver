# VERIFICATION_UPGRADES.md — Lane Router · Test Integrity · FCV · Coverage Honesty · Adversarial Review · A/B Runbook

R10 companion. Binding full text for the compact rules added to SKILL.md
(COV-1 integrity clause · COV-4 FCV clause · §3.0 lanes · A4.9 adversarial
option). Everything here is ADDITIVE: no existing covenant, gate, or literal
token is relaxed. Sections:

- §V1 Fresh-Context Verify (FCV) — independent re-verification
- §V2 Test Integrity & Spec-Test Conflict Flag (canonical text)
- §V3 Coverage Honesty (`[Coverage]` line + `UNVERIFIED` semantics)
- §V4 Adversarial Review (A4.9 option, default for Lane L)
- §V5 Task Lanes S/M/L (eligibility + per-lane obligations)
- §V6 Per-Iteration Snapshot & Revert Discipline
- §V7 Coverage Matrix (Lane L)
- §V8 A/B Evaluation Runbook (skill self-eval)
- §V9 Budget Reserve · Ship Order · Load Map (ceremony economy)
- §V10 Action Triage & State Revision (contamination guards)

---

## §V1 Fresh-Context Verify (FCV) ★

**Purpose.** The author of a change is the worst judge of its evidence
(self-grading). FCV re-runs the verification with a context that never saw the
implementation reasoning, then reports per-criterion verdicts.

**Trigger — FCV is REQUIRED when either holds:**
1. Lane L; or
2. the strongest green evidence for a runtime-affecting change is
   `oracle: self-tests (weak)` (tests written by the same session and no
   project/external acceptance test certifies the change).

Otherwise `Fresh-verify: N/A (<reason>)` in the gate line is legitimate
(e.g. `N/A (Lane M — project tests are the oracle)`).

**Protocol (dispatch BEFORE the completion table):**
1. Write `tests/fcv_brief.md`: the numbered acceptance criteria, the exact
   verification commands to re-run (the same ones that produced your green
   evidence), and the file list from `git diff --stat`. Do NOT include your
   reasoning, your diagnosis lines, or the expected answers.
2. Dispatch a `task` (read-only) subagent with exactly that brief and these
   instructions: re-run each command fresh; for each acceptance criterion
   answer pass/fail with the observed output as evidence; flag any mismatch
   between claimed and observed; do not edit any file.
3. Save its verdict to `tests/fcv_report.md`. ALL criteria pass →
   `Fresh-verify: pass`. Any fail → back to the loop (this is a FAIL iteration;
   log it with `diagnosis:` like any other).
4. The FCV subagent's FAIL verdicts are evidence, not opinions — do not argue
   them away without re-running the command yourself and pasting the output.

**Hard rule.** `Fresh-verify: pass` may only be claimed when the FCV report
exists on disk and says so. A missing report = `N/A` is a lie = gate failure.

## §V2 Test Integrity & Spec-Test Conflict Flag ★

Canonical text of the COV-1 integrity clause:

1. **Tests are READ-ONLY during implementation.** Never edit, delete, skip,
   or weaken a failing test to make it pass. Fix the CODE. (A `# skip`,
   `xfail`, narrowed assertion, deleted case, or relaxed timeout is a weakened
   test.)
2. **The only legal test change** is ADDING coverage (new cases) or a change
   the user explicitly requested — and a change to an existing assertion is
   legal ONLY under rule 3's flag and the user's (or AUTO ADR's) decision.
3. **Spec-Test Conflict Flag — implement-unambiguous-first (binding order):**
   a. When a test contradicts the specification / acceptance criterion, the
      SPEC is the source of truth for code behavior. FIRST land the part the
      spec determines unambiguously (that is the deliverable: implement it,
      test it, log it). THEN flag the conflict at the boundary — PAUSED
      packet (`gate=spec-test-conflict`) in GUIDED, or an ADR line in AUTO
      (`D-<n> | trigger: spec-test-conflict | test: <file:line> | spec: <criterion>
      | implemented: <what now exists> | unsatisfiable: <what remains>`) —
      and leave the suspect test failing and named in `[Coverage] unchecked`.
   b. **STOP-before-code** (issue PAUSED and implement nothing) is required
      ONLY when the conflict makes even the unambiguous work meaningless —
      e.g. the disputed behavior IS the entire deliverable. State which
      rule fired. Implementing the clear part first and flagging the rest is
      the default, not a violation.
   c. Never satisfy the test by violating the spec; never silently rewrite
      the test. (See §V9 for what to do when a time budget forces triage.)
4. Deleting or rewriting tests is also what reward-hacking looks like from the
   outside: a completion whose tests got easier to pass during the session is
   flagged by review as HIGH-RISK by default.

## §V3 Coverage Honesty (`[Coverage]` line) ★

Every completion output includes, immediately after the `[Convergence]` line
and before `[Covenant Recall]`, the LITERAL line:

```
[Coverage] criteria: N/M covered | unchecked: <comma-separated criterion names or none>
```

Semantics (the `未確認` / unverified principle):
- **covered** = each criterion was checked with evidence in this session.
- **unchecked** = applicable but NOT verified in this session. Name it. An
  unchecked item must never be phrased as done/verified anywhere in the final
  answer.
- The 8-column table's Verification Evidence cell MAY say
  `UNVERIFIED — <why not checked>` for a claim dimension that was not checked;
  every such cell must appear in `[Coverage] unchecked`.
- `na` (not applicable, with reason) is NOT `unchecked`. `na` = the dimension
  does not apply; `unchecked` = it applies and nobody looked. Do not launder
  `unchecked` into `na`.
- MANDATORY when acceptance.md has >1 criterion; with exactly 1 criterion the
  line still appears (`criteria: 1/1 covered | unchecked: none`).

## §V4 Adversarial Review (A4.9 option) ★

Default for Lane L; optional anywhere the user asks or the change is
risk-tier.

1. Dispatch TWO `task` subagents (fresh context, read-only) over the same
   `git diff <baseline>..<head>`, each with the A4.9 verdict contract
   (Strengths · Critical/Important/Minor tagged Bugs/Security/Compliance with
   file:line + why · Assessment) and one extra instruction: "assume the diff
   contains at least one defect; hunt for it; do not comment on style".
2. Merge findings, dedupe by file:line+issue. Findings that only one reviewer
   raised are still adjudicated (a solo finding can be the real bug).
3. **Disagreement between reviewers (one clean, one Critical) = escalate** to
   the user (GUIDED) or record an ADR and take the conservative side (AUTO:
   treat the Critical as real until disproven by a re-run).
4. All existing A4.9 obligations hold unchanged: fix Critical/Important,
   covering tests, scoped re-review, defer Minors to memory.

## §V5 Task Lanes S/M/L ★

Declare exactly one line in ZERO (with `Mode:`): `Lane: S` / `Lane: M` /
`Lane: L`. The lane also appears in the gate line (`Lane: S/M/L` field).
Misreporting a lane is a compliance violation — the eligibility list is
objective; when in doubt, pick the higher lane.

**Eligibility (ALL must hold for Lane S):**
- ≤2 files changed (EVERY path in `git diff --stat`);
- ≤3 acceptance criteria;
- no risk-tier path (auth/security/payment/billing/crypto/migration/
  permission/acl);
- no schema / API-surface change; no new feature / endpoint / page;
- no new dependency;
- no multi-step inter-dependencies (else Lane L / C3).

**Lane S obligations** — every covenant (COV-1..12) and every hard gate holds
identically to Lane M. The ONLY differences:
1. Companion reads (R1/R1b) may be **section-targeted** instead of full-file:
   read TESTING_PROTOCOLS.md §A4.1 (loop steps) + §A4.8 (RED rule) headings and
   COMPLETION_GATE.md §A4.4 (output shape) — the file reads still happen (the
   audit sees them); you may use offset/limit reads. When the task surprises
   you (scope grows, new failure class), escalate to full reads immediately.
2. The 8-column completion table has one row (one logical change) — as usual.
3. FCV is optional (§V1 trigger still applies if oracle is self-tests-weak).
4. Everything else — acceptance.md, verification_log.md, COV-9 baseline,
   A4.9 triggers, memory gate, assert_artifacts.py, gate line — unchanged.

**Lane escalation** fires on SCOPE GROWTH only: new files beyond the lane
cap, new acceptance criteria, new inter-dependencies, a new failure class.
Issuing an ADR, a conflict flag (§V2), or a PAUSED packet does NOT escalate
the lane — those are handled in-lane. (In doubt about scope? Higher lane.)

**Lane M** — the default; the discipline exactly as it exists today, plus
§V1–§V3/§V6 obligations.

**Lane L** (ANY of: ≥3 files · multi-step inter-dependencies · new feature ·
schema/API-surface change · risk-tier paths) — Lane M plus:
- C3 `docs/PLAN.md` + Consistency Hub (per REFERENCE.md C3);
- FCV required (§V1);
- Adversarial review by default (§V4);
- Coverage matrix (§V7);
- per-iteration snapshots (§V6).

## §V6 Per-Iteration Snapshot & Revert Discipline ★

In the capture loop (§A4.1): when an iteration's diagnosis falsifies the
attempt, **revert the attempt's edits for real** (`git restore` / `git
checkout -- <files>`) before applying the next hypothesis. Forward-patching
on top of a failed attempt leaves dead scaffolding that contaminates the next
iteration and hides which change fixed what.

- Lane L: take a cheap snapshot each iteration (`git add -A && git commit -m
  "wip-iter-N"` or equivalent) so revert is one command and the attempt trail
  is auditable. Never squash away the trail before FCV.
- Regression tests complete the revert-and-fail cycle (already binding in
  §A4.8) — the same revert discipline.

## §V7 Coverage Matrix (Lane L) ★

`tests/coverage_matrix.md` — one row per acceptance criterion:

```
| # | Criterion | Check (test/command) | Evidence file | Status |
```

- `Status` ∈ covered / unchecked / na(reason).
- Every PLAN.md task that implements behavior maps to ≥1 row; a criterion with
  no row is a planning gap — fix the plan before implementing.
- The matrix is the machine-greppable spine behind the `[Coverage]` line; the
  counts must agree.

## §V8 A/B Evaluation Runbook ★

How to measure whether a SKILL.md revision actually changes agent behavior
(bundled harness: `scripts/ab/run.mjs`). Method follows the established eval
practice: fresh isolated context per cell · paired old/new arms · deterministic
assertions (no LLM judge) · honest small-sample reporting.

**Experimental identity.** The ONLY variable between arms is the skill
content. Controls:
- same skill name + byte-identical frontmatter (trigger surface constant);
- arm content installed at the same path between runs;
- sibling skills that could dominate behavior (e.g. vibeweaver-mini) parked
  for the duration and restored after;
- fresh task directory per trial (fixtures are template copies);
- neutral prompt that points at the skill path without naming any new
  mechanism (no "use Lane S", no "flag conflicts").

**Assertions are deterministic.** File-sha256 (test files unmodified),
mtime-order (tests created before code), pytest exit codes, and transcript
tokens (`[Verification Gate]`, `HARD-GATE-1: NO-TEST-NO-DONE`, `Lane:`,
`[Coverage]`, `Fresh-verify:`). Assertions must be meaningful on the pristine
fixture (a `--dry-run` check flags assertions that pass before any work).

**Statistics.** Per-cell N trials; report per-arm pass counts and the Fisher
exact p-value on the 2×2 outcome table. **N<5 per cell = `LOW` confidence,
directional only — never claim a conclusive lift from it.** Report deltas as
"on this suite, under model M and harness H, arm B passed X/Y vs A's W/Y",
never "the skill is N% better".

**Failure handling.** Timeout/crash = cell failure (not silently dropped);
record wall time. If both arms fail a task, the task is too hard for the model
under test — downgrade the fixture, do not interpret it as skill failure.

**Calibration (mandatory before interpreting any run).** (1) Run each task
with NO skill pointer first: if the bare model cannot finish the fixture
inside the budget, the fixture is budget-invalid — shrink it or raise the
budget; a suite of budget-invalid fixtures measures ceremony speed, not
behavior. (2) **Timeouts are an environment artifact, not a behavioral
verdict.** Size the per-cell timeout so that ~all control (no-skill or
old-arm) cells COMPLETE — 3× observed p99 is a sane floor (600–1200s for
full-ceremony coding tasks on mid-tier models). **TDD / new-feature fixtures
carry the full ceremony (RED/GREEN + PLAN + review + memory): budget them
2h (7200s) per cell** (harness: `--timeout-tdd`, default 7200). (3) A
timed-out cell is classified **budget-invalid**: it is EXCLUDED from
behavioral assertion rates and reported separately as truncation/completion
rate. (4) Wall time and output bytes are reported as COST metrics beside the
rates — completion correctness is the primary metric; speed is never a
pass/fail axis. (5) A skill arm that still truncates at the calibrated
budget is a first-class finding about that skill's ceremony tax (see §V9) —
report it, do not hide it inside a pass rate.

## §V9 Budget Reserve · Ship Order · Load Map ★

Ceremony is a cost center. The value that must survive any budget cut is:
working code + green tests + an honest gate line. Everything else degrades
LEGALLY through `[Coverage] unchecked` / `UNVERIFIED` / `na (reason)` —
never by faking evidence, and never by blocking a green deliverable on
unfinished ceremony.

**Ship order (binding):**
① minimal implementation + tests green (one line per iteration in
`tests/verification_log.md`) →
② evidence assembly (logs · screenshots · traces) →
③ completion output (`[Coverage]` · gate line · 8-column table) →
④ deferred ceremony (memory topic files · `tests/review_package.md` · ADR
prose · `fcv_brief.md`) — assembled FROM the log at completion time.
Heavy artifacts written mid-loop are a budget leak; the in-loop record is
the one-line log entry. Time-critical ceremonies stay in-loop and are never
deferred: COV-9 baseline (before edits) · acceptance.md (before acting) ·
PAUSED/ADR at the decision moment (a single line) · test runs themselves.

**Budget reserve (self-check at EVERY iteration entry):** ask — "can the
remaining budget still afford minimal code + one test run + the gate line?"
- YES → continue the loop.
- NO → stop expanding; consolidate ①–③ now; name everything unfinished in
  `[Coverage] unchecked`. A partial-but-honest completion beats a timeout
  that lands nothing.
- The budget signal is the wall clock, the turn/conversation cap, a user
  deadline, or a visibly shrinking allowance — pick what is real, state it.

**Narration discipline:** narration is a running index (one line per action
+ verdict), not an essay. Full prose lives in artifacts. Restating
already-settled rules, re-explaining known constraints, and narrating
alternatives you did not take are budget leaks.

**Load Map (hybrid loading — read cost is task cost):**
- **Stable prefix — ALWAYS resident, never lazy:** §1 covenants, hard
  gates, test integrity (§V2), coverage honesty (§V3). Safety rules are
  not just-in-time; a guardrail the agent "decides to load" is not a
  guardrail.
- **R1-core (before first code action; offset reads OK):**
  TESTING_PROTOCOLS §A4.1 loop steps + §A4.8 RED rule (+ §A4.6 heading for
  bugfixes). SKILL.md's A4.1/A4.8 summaries are the fallback core.
- **Lazy blocks (read when the trigger fires, not before):** §A4.6 full
  debugging → at the first hard failure · §A4.7/§A4.7b → backend-only
  tasks · §A4.9 full review contract → at review dispatch · §A4.10 → at
  the first stall · R1b COMPLETION_GATE → before the completion output
  (already point-of-need).
- R2–R9 triggers unchanged. An offset read of the named file satisfies the
  audit's read check; the split saves tokens, not obligations.

## §V10 Action Triage & State Revision ★

(from AEWM-style task-state contamination analysis: unsupported assumptions,
outdated plans, and partial-progress-as-completion persist in history and
poison later decisions. Guard them at three points.)

**1. Pre-action triage (at every iteration entry — ONE letter in the log
line).** Classify the planned action before executing it:
- **C (critical)** — closes a key gap, obtains necessary evidence, or makes
  a required state change on the direct solution path. Execute.
- **E (exploratory)** — meaningfully reduces uncertainty or tests a
  plausible branch. Execute (bounded).
- **N (noisy)** — repetition, re-reading settled rules, restating known
  constraints, ceremony before the deliverable exists, redundant checks,
  speculative edits without a falsifiable hypothesis, work that violates a
  constraint or chases a contradicted direction. **Do not execute.**
Log line shape gains one field: `- iter N FAIL/PASS [C|E|N]: …`.
Roughly a quarter of SWE steps in measured agent corpora are N — trimming
them is the cheapest quality win available.

**2. State Revision beats critique (edit, don't append).** When evidence
kills an assumption or falsifies a plan step, REWRITE the artifact that
carries it — the PLAN row, the acceptance interpretation, the memory topic,
the diagnosis line — in place. A correction note appended beside a stale
artifact does NOT decontaminate history: the stale text keeps getting
re-read and re-trusted. (Code edits still revert per §V6; this rule covers
the belief-carrying artifacts.) When FCV/A4.9 returns findings, the closure
is an edited artifact + re-run evidence — never a rebuttal paragraph.

**3. Local green ≠ task complete.** A passing run verifies only the
criteria it covers; intermediate success is never promoted to completion.
Earlier obligations (acceptance criteria, interface contracts, regression
tests) survive later edits — a new change never overrides them silently;
`[Coverage]` + fresh-run on the delivered tree are the completion proof.

---
End of VERIFICATION_UPGRADES.md. Adding rules here: keep SKILL.md lines
compact (it has a hard size cap asserted by selftest T11); full text lives in
this file.
