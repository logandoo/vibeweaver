# VERIFICATION_UPGRADES.md — Lane Router · Test Integrity · FCV · Coverage Honesty · Adversarial Review · A/B Runbook

R10 companion. Binding full text for the compact rules added to SKILL.md
(COV-1 integrity clause · COV-4 FCV clause · §3.0 lanes · A4.9 adversarial
option). Everything here is ADDITIVE: no existing covenant, gate, or literal
token is relaxed — §V11 formalizes the `=na` clauses COV-1/COV-4/COV-9
already carry (documentation-only / no-runtime) into a decision table; it
never drops evidence for a class whose risks are live. Sections:

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
- §V11 Task Class — proportional verification path (DOC/CONFIG/CODE)

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

**Class exception (§V11.8#3):** for `Class: DOC`-prose whose evidence is
the diff + read-back, FCV is `na` (`N/A (Class: DOC — diff + read-back)`) —
there is no self-graded runtime claim to re-verify. A DOC-asset re-renders
under FCV when layout is critical (the verifier grades fresh pages); a class
escalation (V11.4) brings FCV back. Class CONFIG/`CODE` follow the trigger
above.

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

**Lane S obligations** — every covenant (COV-1..13) and every hard gate holds
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

How to measure whether a SKILL.md revision actually changes agent behavior.
Harnesses: `scripts/ab/run.mjs` (compliance/convention checks) and
`scripts/ab/obj_eval.mjs` (objective grading). Method follows established eval
practice: fresh isolated context per cell · paired old/new arms · deterministic
assertions (no LLM judge) · honest small-sample reporting.

**Objective metrics hierarchy (use these as the verdict axes).** Compliance
tokens (gate line, `[Coverage]`, `Lane:`) measure whether the skill's own
conventions appear — they are circular and NEVER the outcome verdict. The
verdict axes are, in order:
1. **Hidden fail-to-pass tests** (SWE-bench style): gold behavioral tests
   embedded in the harness and injected only at grading time; the agent never
   sees the grading assertions. Score = fraction passed on the DELIVERED code.
   Hidden tests must stick to spec-stated behavior only.
2. **Integrity** (anti-cheat): sha256 of visible grading/test files unchanged;
   on spec↔test conflict tasks, silent test rewriting counts as a violation
   even if the suite goes green.
3. **Effective Mutation Score `EffMS = MS × SPR`** (delivered-suite quality,
   SecMutBench validity gate): SPR = the delivered suite must pass on the GOLD
   implementation (the suite certifies the spec, not its own implementation);
   MS = fraction of semantic gold-mutants the delivered suite kills. Only
   interpretable when the spec determines the gold uniquely and the fixture
   contains no poisoned tests (see pitfalls).
4. **COST** (wall seconds, output bytes): reported beside the rates, never a
   pass/fail axis.

**Experimental identity.** The ONLY variable between arms is the skill
content. Controls:
- same skill name + byte-identical frontmatter (trigger surface constant);
- arm content installed at the same path between runs;
- sibling skills that could dominate behavior (e.g. vibeweaver-mini) parked
  for the duration and restored after;
- fresh task directory per trial (fixtures are template copies);
- neutral prompt that points at the skill path without naming any new
  mechanism (no "use Lane S", no "flag conflicts").

**Measurement pitfalls (all observed in real runs — each cost a void round).**
1. **Poisoned fixture tests**: if the fixture ships a deliberately wrong test
   (conflict tasks), it must be EXCLUDED from the delivered suite when scoring
   SPR/MS — otherwise honest arms (which leave it failing) score 0 while
   silent rewriters score high. Keep such fixtures; grade around them.
2. **Gold over-specification**: if the spec under-determines behavior (e.g.
   non-ASCII policy), SPR measures agreement with the gold's arbitrary choice,
   not suite quality. Either pin the graded behavior in the spec/hidden tests,
   or declare the axis uninterpretable for that task.
3. **Equivalent mutants**: a mutant masked by another layer of the
   implementation survives even a perfect suite (observed: removing an explicit
   combining-mark strip where a later regex strips it anyway). Validate the
   battery against a perfect suite (hidden tests + spec edge cases) BEFORE the
   run; every mutant must be killable.
4. **Stale bytecode**: same-size/same-second mutant edits are masked by
   `__pycache__` (.pyc mtime+size invalidation). Purge caches and run pytest
   with `PYTHONDONTWRITEBYTECODE=1` in the grader.
5. **Fixture dispatch**: task ids arriving from CLI filters are strings; loose
   identity comparison silently serves every cell the same fixture. Dry-run
   the fixture writer and inspect one cell dir before trusting a run.
6. **Truncation ≠ failure**: timed-out cells are budget-invalid (excluded
   from rates, reported as completion); speed is never a verdict.

**Statistics.** Per-cell N trials; per-arm counts + Fisher exact on 2×2
tables; paired sign counts at (task,trial) level for graded scores. **N<5 per
cell = `LOW` confidence, directional only.** Report scoped claims: "on this
suite, model M, harness H: arm B passed X/Y vs A's W/Y" — never "the skill is
N% better".

**Calibration (mandatory before interpreting any run).** (1) Run each task
with NO skill pointer first: if the bare model cannot finish the fixture
inside the budget, shrink it or raise the budget. (2) Size the per-cell
timeout so that ~all control cells COMPLETE — 3× observed p99 is a sane floor
(600–1200s on mid-tier models); **TDD/new-feature fixtures carry the full
ceremony — budget 2h (7200s) per cell** (`--timeout-tdd`). (3) Run the
grader's machinery self-test (gold suite must kill 100% of the mutant
battery; hidden tests must pass on gold) before launching agents. (4) A skill
arm that still truncates at the calibrated budget is a first-class ceremony-tax
finding (§V9) — report it, never hide it inside a pass rate.

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

## §V11 Task Class — proportional verification path ★

**Problem this solves.** Unclassified, every task walks the full
verification path — including README/CHANGELOG-only edits — and the path
drags doc updates along with it. Both are *process inflation*: a gate that
names no risk. The fix is a classification, not a lighter conscience: one
derived variable, decided BEFORE any action, routes the task to a path
card; a lighter estimate that turns out wrong is recovered upward
(Estimate → Execute → Expand — misclassification is recovered, never
pre-empted).

### V11.1 Declaration
In ZERO, on the line after `Mode:`/`Lane:`: `Class: DOC` | `Class: CONFIG`
| `Class: CODE`. The class appears in the gate line as
`Class: DOC|CONFIG|CODE` (field after `Lane:`). Misreporting a class is a
compliance violation exactly like a misreported lane — when in doubt, the
HIGHER class.

### V11.2 Decision table (objective · first match wins)
Basis = the change set's file kinds (`git diff --stat` + untracked files —
never self-recollection; same evidentiary standard as COV-8) and whether
runtime behavior changes.

| Class | Primary deliverable is… | Named risk its gates mitigate |
|---|---|---|
| **CODE** | any logic-bearing source file — **logic-bearing = contains control flow: branch · loop · state · validation · transform** (`.py/.js/.ts/.go/.rs/.java/.c/.cpp/.rb/.php…`; test files with behavior assertions count) | behavior regression |
| **CONFIG** | config · scripts · markup · CI · lockfiles · dep pins · formatting — machine-read or executed, but no control flow of their own: a script that only sequences commands is CONFIG; one with branch/loop/state is CODE (uncertain → CODE) (`.toml/.yaml/.ini/.sh/.bat/Dockerfile/Makefile` · template `.html` · `package.json`/`requirements.txt` pins) | wrong-config · broken-script |
| **DOC** | prose only — `*.md/*.txt/*.rst` · comments · README · CHANGELOG · LICENSE · release notes · `docs/` · `memory/` · this skill's own contract text — **or office document assets** (`.docx/.doc/.xlsx/.xls/.pptx/.ppt/.pdf/.odt/.ods/.odp`, deliverable-is-the-file kind), whose evidence mode differs (V11.3 row · V11.9 render gate) | doc-drift (prose) · layout/corruption (asset) |

- Classification is by FILE KIND up front (the optimistic estimate); a
  behavior risk the file kind could not express is an ESCALATION trigger
  (V11.4#2), never a reason to stall the classification. A deliverable that
  IS a behavior change with no code file (deleting a runtime asset) is CODE.
- First match wins in the order CODE > CONFIG > DOC: one logic-bearing file
  inside a 40-file docs PR makes the task CODE.
- **Uncertain → one class UP.** An empty or failed classification is never
  "accept" (asymmetry: disagreement escalates).
- Evidence artifacts (`tests/*.png`, `*.log`, videos) count as DOC; test
  files that encode behavior assertions count as CODE.

### V11.3 Path card — obligations per class (gate ↔ named risk)
An obligation runs when its risk belongs to the class's risk column; else it
is emitted `na (<reason>)`. `na` without a stated reason is UNCERTAIN (the
HARD-GATE `=na` rule, audit C14/C15 semantics) — unchanged.

| Obligation (risk it mitigates) | DOC | CONFIG | CODE |
|---|---|---|---|
| COV-3 web research + ≥2 approaches (wrong approach) | na — no stack choice open | only when a config/stack choice is open | required |
| COV-5 verifier probe (silent wrong output) | prose: preset `direct read (non-web)` — no probe; **asset: full §A4.1 Step 0 probe** (page images ARE graded media — grade via the announced verifier, never blind Read) | same as DOC-prose | full probe tree (§A4.1 Step 0) |
| COV-1 tests (behavior regression) | `HARD-GATE-1=na` — prose evidence = the diff + read-back of every edited file (README-class work adds the readme-weaver audit criteria: 永不编造逐条核对 · 读者漏斗); office-asset evidence = render-and-verify (V11.9 — **NO RENDER, NO DONE**) | smoke check: config parses / script `--help` or dry-run | full: §A4.8 TDD for logic-bearing · §A4.1 loop for UI/runtime |
| COV-4 capture loop (undetected bug) | na — read-back verify replaces Act→Capture | smoke capture | full loop |
| COV-9 baseline run (unattributable regression) | state-skip (`documentation-only change`) | required | required |
| COV-8 review (major change) | not triggered on file-count/new-feature legs — cite `git diff --stat` (§V11.8) | per triggers | per triggers |
| `acceptance.md` + `verification_log.md` (stop condition) | required — 1-3 criteria, ≥1 log entry | required | required |
| 8-column completion table (unaccounted change) | **lite table** (V11.6) | lite table | full 8-column |
| Memory Gate (forgotten lesson) | lesson-triggered: `na (Class: DOC — no lesson)` ONLY when the task block has no FAIL/stall/cap-hit entry (a wave that fought the layout or the prose HAS a lesson — COV-7 ❌-entry rules bind) | lesson-triggered: write when one exists, else `na (<why>)` | A7.9/A7.10 as written — lesson-triggered: write the topic when a lesson exists, else `na (<why>)` (A7.1 "what NOT to save") |
| README/CHANGELOG/API-doc updates (doc drift) | only on named drift (V11.5) | only on named drift | only on named drift |

Class-INDEPENDENT (holds in every class): the Mode line (COV-12) · COV-7
bound (`cap=5  stall=3×`) · the `[Coverage]` line (§V3) · ADR/PAUSED
protocol · secret scan (assert group 14) · test-change guard (group 15) ·
risk-tier review (group 16) · `assert_artifacts.py` exit 0 · fresh-run on
the delivered tree · the gate line itself. Class decides **which gates
run**, never **whether evidence exists**. Class × Lane interaction:
§V11.8.

### V11.4 Escalation (expand on evidence — never pre-empt, never de-escalate)
1. **Scope growth** past the class's file-kind boundary (a DOC task must
   edit a script; a CONFIG task starts changing logic) → reclassify UP and
   retro-run the obligations the higher class adds (tests · full table ·
   review — a COV-9 baseline cannot be run retroactively: run it at the
   escalation point against the pre-escalation tree, or state
   `COV-9 skipped — reason: escalated from Class DOC mid-task, no pre-state
   to baseline`). The lane escalates too (§V5).
2. **Evidence disagreement** — a lighter path's check fails naming a higher
   class's risk (a "doc" edit breaks a build; a config change alters an API
   response) → reclassify UP and run the loop from there.
3. **Never de-escalate.** A lighter path that held is evidence the estimate
   was right, not a discount coupon; completed work stays, added
   obligations run on top.
4. Failed probe · empty result · unclassifiable deliverable → UP. DOC is
   never the destination of doubt.

### V11.5 Doc-drift trigger (README/CHANGELOG/API docs)
Docs update only when the change makes them stale, and the drift is NAMED:
- drift → update the file + log `docs-drift: <file> — <what went stale>`
  (in `tests/verification_log.md` AND in the final answer);
- no drift → one line `docs-drift: none (<why nothing went stale>)`, same
  two places.

"The path includes a README step" is not a drift; neither is "keep the
changelog tidy". Exception: §A4.7's API doc is the backend loop's SPEC
(tests are written from it) — it updates because it is the oracle, not on
drift. New-project C1 step 15 still scaffolds README +
requirements.txt + package.json — a deliverable of a new project, not
ceremony; assert group 8 stays scoped to new-project tasks.

### V11.6 Lite completion (Class DOC / CONFIG)
One row per logical change, 3 columns, replacing the 8-column table:

```
| # | Problem | What Changed & Evidence |
```

The gate line keeps its exact shape; class-inapplicable fields carry `na`
with a reason on/near the field — e.g. `Loop executed: no (Class: DOC —
read-back verify)` · `Fresh-verify: N/A (Class: DOC — diff + read-back is
the oracle)` · `HARD-GATE-1: NO-TEST-NO-DONE=na (documentation-only change)`·
`memory_gate: na (Class: DOC — no lesson)`. `[Convergence]` and `[Coverage]`
are still output (`[Coverage] criteria: N/M covered | unchecked: …`) — an
unchecked item is named, never laundered into `na`.
The lite table is a contract shape, not a loophole: the audit accepts it
ONLY when the gate line declares `Class: DOC|CONFIG`.

### V11.7 Enforcement
- `tests/assert_artifacts.py --class DOC|CONFIG|CODE`, or the basis line
  `- class: <X> — <basis>` as the FIRST entry of the CURRENT task block in
  `tests/verification_log.md` (exactly one per block; multi-block logs: the
  LAST task block wins — older blocks are history). Class-NA groups print
  `class: <X> — group N/A …` as gate evidence (DOC structurally N/A's memory
  + service lifecycle groups; a profile never weakens an applicable group;
  groups 12-16 — claim lint · secret scan · test-change · risk-tier —
  NEVER skip).
- audit Group B accepts the lite table header ONLY when the gate line
  declares `Class: DOC|CONFIG` (the field must be a filled single value —
  `Class: DOC|CONFIG|CODE` the template is not a value); a Class DOC/CONFIG
  task may still use the full 8-column table (over-delivery is fine).
  `memory_gate: na` is accepted for `Class: DOC|CONFIG` or with a stated
  skip/no-lesson reason — without either it is BAD.
- The audit cross-checks the two class channels: gate-line `Class: X` vs
  the log's `- class: Y` basis line — a mismatch is BAD (one class per task).
- Class misreport guard (C18): `Class: DOC` + any write/edit to a path that
  is neither prose nor an office asset (V11.9 — including `tests/**` code
  files and untimed/bash-produced files) = BAD; `Class: CONFIG` + any
  logic-source OR office-asset write = BAD (assets belong to DOC). Office
  assets are LEGAL under Class DOC — they are gated by render evidence
  (below), not by the misreport rule.
- The class is a routing input. It never excuses missing evidence inside
  the class's own path card.

### V11.8 Class × Lane — which axis wins
Class decides WHICH gates run (the path card); Lane decides reading depth
and the added layers (§V5). They compose like this:
1. The Lane-L additions — C3 `docs/PLAN.md` · FCV (§V1) · adversarial review
   (§V4) · coverage matrix (§V7) — mitigate IMPLEMENTATION risk. For
   `Class: DOC`-prose they are `na (Class: DOC — no implementation risk)`;
   for `Class: CONFIG` they apply as written; for `Class: CODE` always; for
   a DOC-asset see #3 (FCV = fresh re-render).
2. COV-8's file-count / new-feature legs count non-prose paths only
   (`git diff --stat`, prose paths excluded — a class-NA trigger states this
   count, never bare "N/A"; the COV-8 canonical "EVERY path" wording reads
   as class-adjusted here) and fire per the class's risk column; the
   risk-tier / schema / API-surface / behavior-semantic legs fire in EVERY
   class (they are class-independent, §V11.3).
3. FCV (§V1) is `na` for Class DOC-**prose** (whose oracle is the diff +
   read-back — no self-graded runtime claim to re-verify); for a DOC-asset
   the render evidence IS the oracle and FCV = a fresh re-render graded by
   the announced verifier (layout is the asset's named risk, so
   "layout-critical" is always true for office assets); for Class CONFIG
   the §V1 trigger applies as written (smoke checks are re-runnable), and
   for Class CODE always. A `Fresh-verify` field for a na reads
   `N/A (Class: DOC — diff + read-back)`.
4. Escalation (V11.4) moves BOTH axes: the higher class brings back its
   gates, and the lane re-evaluates on the enlarged change set.

### V11.9 Doc-skill delegation & the DOC-asset render gate ★
The DOC class splits by ARTIFACT KIND (both stay `Class: DOC`; the file
extension decides the evidence mode — no extra class value to misreport):

| Deliverable | Authoring (tool) | Verification (gate) | Evidence on disk |
|---|---|---|---|
| README / CHANGELOG / `*.md` prose | — (prose) | **readme-weaver audit**: 永不编造 — every install command/badge/path/usage example checked against the repo (manifest-derived, never guessed); 读者漏斗 structure; its mechanical checker (`readme_lint.py --compare`) + 逐条核对 + 疲惫开发者测试 | diff + read-back + the lint/audit output |
| `.docx/.doc` | `docx-manipulation` (python-docx) · office-mcp 兜底 | **office-docx render-and-verify** (`render_qa.py` in that skill's dir) | rendered page images + QA output |
| `.xlsx/.xls` | `xlsx-manipulation` (openpyxl) | LibreOffice render is the independent invariant (openpyxl re-reading its own output cannot evaluate formulas); + sheet QA | page images + formula/value spot-checks |
| `.pptx/.ppt` | `pptx-manipulation` / `ppt-visual` | `soffice --convert-to pdf` → pages (pdftoppm/PyMuPDF) + visual QA | slide images |
| `.pdf/.odt/.ods/.odp/.rtf/.odg/.epub` | office-mcp / format tooling | render pages → auto QA + visual QA | page images |
| standalone HTML report/page (deliverable-is-the-page) | — (markup) | browser screenshot = the rendered page (DOC-asset); a template/fragment a build consumes stays CONFIG | screenshots |

**Render gate (openai `doc` + office-docx consensus): NO RENDER, NO DONE.**
The gate is FILE-KIND triggered: any wave that delivers an office asset owes
it, in EVERY class (a mixed CODE wave shipping a sample `report.docx` is
just as bound; assets are never a class misreport — their gate IS the
render, which is also why the macro-escalation path cannot deadlock).
Office layout only exists once rendered — text extraction and the
document-object model LIE about pagination. Pipeline per meaningful change:
`edit → convert (soffice --headless --convert-to pdf) → render pages
(render_qa/PyMuPDF/pdftoppm) → automated QA (blank pages · edge-bleed ·
missing content · page count) → visual QA → fix → re-run the pipeline`.
The render→fix→re-render cycle IS the COV-4 loop for assets — bound by
cap=5 / stall=3× like any loop; on stall the honest exit is
`render: N/A (stall=3× — <criterion>)` + hand the pages to the user (or a
PAUSED packet), never a silent claim of done. Page images land under
`tests/` and are cited in the completion row + `tests/verification_log.md`.

**Per-asset evidence rows (§V11.9 binding form):** one `render:` line per
delivered asset, in THIS task's log block and the final answer:
```
render: report.docx — tests/report_p1.png, tests/report_p2.png | pages: 2
render: appendix.pdf — N/A (soffice missing) · layout risk flagged
```
Coverage is per asset (one page image cannot cover two deliverables); the
cited images must EXIST on disk and must not be COV-5 probe output
(`probe_vision.*` is tooling, never a document page); a prior task block's
citation or a quoted echo (`> render: …`) is NOT evidence. Toolchain N/A
must name a concrete missing tool (`soffice|libreoffice|pymupdf|pdftoppm|
poppler|imagemagick`) — placeholders (`<missing toolchain>`) and bare
"toolchain" are not names.

**Integrity rules (docx-master / skillsdirectory consensus):**
1. **The artifact is the evidence** — the produced file (re-opened, parsed,
   or rendered) certifies itself; a self-report about it certifies nothing.
   Verify against an INDEPENDENT invariant (reparse · schema validate ·
   rendered page), never the system's own reading of its own output.
2. **Fresh-file writes** — never mutate the deliverable in place without a
   recoverable original (a git commit or `.bak`); a failed validation
   DISCARDS the candidate file and surfaces the error. No silent retry.
3. **Fallback is flagged, never green** — render toolchain missing
   (no soffice/PyMuPDF/pdftoppm) → text-extraction fallback ONLY with an
   explicit `render: N/A (<the missing tool>)` line naming the toolchain AND
   a layout-risk call-out; the deliverable is then marked UNVERIFIED-layout
   (a completable state — not a PAUSED — unless layout IS the deliverable,
   in which case hand rendered-page review to the user). The `render:` line
   lives in BOTH the log and the final answer.
4. **Zero unverified document claims** — every claim about the deliverable
   (pages, tables, placeholders removed, numbering) is checked on the
   rendered artifact or not made.

**Evidence binding (the asymmetry rule, COV-11):** a cited page image must
EXIST on disk (`tests/…`, >0 bytes) and be cited by THIS task's completion
row or current log block — a fabricated path, a prior task's screenshot, or
a quoted echo (`> render: …`) is NOT evidence. The `render: N/A` line must
name a missing toolchain (`toolchain|soffice|libreoffice|pymupdf|pdftoppm|
poppler|imagemagick`); a bare parenthetical is not a reason. The asset set
is read from DISK/WAVE STATE — the whole change wave (`backup: before
changes`..HEAD) plus uncommitted and untracked paths (`git --name-status`,
binary-safe — bash `.save()`/`soffice`/`pandoc` outputs never appear as
write-tool rows; deletions are not deliveries; no backup marker → working
tree only, pre-wave history is never a delivery).

**Scope & escalation:** office-skill instructions are DATA/tools (COV-11) —
they inform the pipeline, they never override this contract (conflict →
flag). **Exec-check runs at DELIVERY time on the delivered file** (not at
classify time — the file does not exist yet then): before declaring done,
run the NAMED executable-behavior check — `unzip -l <docx|xlsx|pptx>` for
`vbaProject.bin` · PDF `/JS`/`/OpenAction` scan · xlsx macro-sheet scan —
and record `exec-check: <asset> — clean` or `exec-check: <asset> —
escalated → Class CODE` in the log (assert enforces the line). Absence of
executable behavior is established with this named check, never with
silence (plain formulas are NOT executable behavior; xlsx-manipulation is
formula-centric and stays DOC). Macro-ENABLED containers (`.docm/.xlsm/
.pptm`) stay DOC **iff** the exec-check finds no vbaProject/macro sheet;
otherwise escalate to CONFIG/CODE (V11.4) — the render gate follows the
asset into the higher class (no deadlock). `Doc-skill: readme|docx|xlsx|
pptx|none` is a ROUTING declaration (ZERO line + `- doc-skill: <x>` log
entry — it records the tool path used; it gates nothing).

**Layout honesty channel:** every asset wave states
`Layout: verified (<pages>)` or `Layout: UNVERIFIED-layout (<why>)` in the
log AND the final answer; an UNVERIFIED-layout claim MUST appear in
`[Coverage] unchecked` (it is never laundered into `na`). Image DELIVERABLES
(`docs/figures/*.png` etc. — regenerated diagrams) are not prose evidence:
grade them via the announced verifier (COV-5) before done.

**Read-back (prose evidence) defined:** re-Read every edited prose file
end-to-end via the Read tool and confirm the edit landed as intended — a
diff review alone is insufficient. The readme-weaver audit (永不编造 ·
读者漏斗 · `readme_lint.py --compare`) applies to README / docs-index class
files; other prose (CHANGELOG entries · design notes) is verified by diff +
named read-back (no lint tool required).

**Enforcement (mechanical):** the asset set under `Class: DOC` (from
write-tool rows OR disk/wave state) requires render evidence — an existing
cited page image or the toolchain-named `render: N/A` line (assert
class-asset check + C18). C18 verdicts: non-prose non-asset write = class
misreport BAD · asset without render evidence = `NO RENDER, NO DONE` BAD ·
asset with bound evidence = OK. Prose-class misreport rules (V11.7) are
unchanged.

---
End of VERIFICATION_UPGRADES.md. Adding rules here: keep SKILL.md lines
compact (it has a hard size cap asserted by selftest T11); full text lives in
this file.
