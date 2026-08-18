# TESTING_PROTOCOLS.md — Canonical Test / TDD / Review / Stall-Escape Protocols

> Companion file for [SKILL.md](SKILL.md). Holds the **canonical text** of §A4.7 (COV-6),
> §A4.7b, §A4.8, and §A4.9 (COV-8), plus §A4.10 (stall escape). SKILL.md keeps only the
> binding stubs; when executing those loops, THIS file is the authoritative rulebook.
> If in conflict with §1 covenants in SKILL.md, the covenants prevail.
> Section numbers are preserved so cross-references (`A4.8`, `A4.9`, …) keep resolving.

## Contents

- [§A4.7 Backend-Only Task: API Doc-Driven Test Loop](#a47-backend-only-task-api-doc-driven-test-loop--non-negotiable) (COV-6 canonical)
- [§A4.7b Workflow Scenario Tests](#a47b-workflow-scenario-tests-task-level-backend-verification) (task-level backend verification)
- [§A4.8 TDD for Logic-Bearing Code](#a48-tdd-for-logic-bearing-code--non-negotiable)
- [§A4.9 Independent Code Review (Major Changes)](#a49-independent-code-review-major-changes) (COV-8 canonical)
- [§A4.10 Stall Escape: Parameterize, Differential-Test, Dual-Path](#a410-stall-escape-parameterize--differential-test--dual-path) (companion to COV-7)

---

## A4.7 Backend-Only Task: API Doc-Driven Test Loop ★ NON-NEGOTIABLE

This is the canonical text of COV-6. When a task touches ONLY backend code
(no UI, no browser-rendered output), replace the Playwright loop with this.
Any browser-rendered slice keeps §A4.1.

**Step 1 — Choose HTTP client:** `httpx` if installed → else `requests` if
installed → else install and use `requests`. Check via `pip show httpx requests`.

**Step 2 — Update API documentation:** update the project's API doc
(`API.md`, `docs/api/`, OpenAPI spec — match existing format; create
`API.md` if none). Document every changed/new endpoint: method, path,
request params/body schema, response schema, status codes, error cases,
auth requirements.

**Step 3 — Review doc ↔ code consistency (exactly 1 audit pass):** re-read
the doc + the route/handler code side-by-side. Every endpoint in code appears
in the doc; every documented field/param/status code matches the
implementation; no stale endpoints remain in the doc. Fix any mismatch
BEFORE writing test cases.

**Step 4 — Write test cases FROM the API doc** (not from the implementation):
one case per endpoint for happy path + cases for documented error responses,
validation failures, auth failures, boundary inputs. Persist test cases
(e.g. `tests/test_api.py`) so they are re-runnable.

**Step 5 — Run the test→fix→test loop:** start backend via `script/` (COV-2).
All tests MUST produce log files (A4.2). **Any failure** → diagnose root cause
(§A4.6), modify code, re-run the SAME failing test first then the full suite.
Repeat `test → modify → test → modify …` until ALL test cases pass. Log each
iteration to `tests/verification_log.md` (same format as A4.1 Step 4 — every
FAIL line carries its `diagnosis:` clause). Same iteration cap=5 / stall=3×
(COV-7) — on cap/stall apply §A4.10 (parameterize or shift; never retry
"again but slightly different"), record the failure in memory and report to
the user instead of looping forever. If a test failure reveals the doc was
wrong (not the code), update the doc, re-do the Step 3 consistency audit,
then continue the loop.

**Completion evidence for A4.4:** chosen HTTP client, API doc path, test-case
file path, test log file, and convergence line `[Convergence] <task>: N iters
| X/Y test cases pass | stalls | cap-hits`.

**Ordering for NEW endpoints (test-first, links to §A4.8):** when §A4.7 covers
a **new** endpoint, execute Steps 2-4 (doc → consistency audit → test cases
written FROM the doc) **before implementing the endpoint**. The first test
run MUST fail (endpoint missing). Then implement to green — see §A4.8.

### A4.7b Workflow Scenario Tests (Task-Level Backend Verification) ★

**Per-endpoint tests prove each endpoint works alone; they do NOT prove the
task works end-to-end.** Single-endpoint green does not guarantee that
`register → login → create → list → verify-persistence` succeeds as a flow.
After A4.7 Step 5 is green, add workflow tests for backend-only changes.

**Step 1 — Define 1-3 workflow scenarios:** each scenario is ONE business task
the user asked for, expressed as a step sequence across endpoints: entry call
→ each step (request + expected status + expected STATE transition) → final
verification (DB query, side-effect check, or next-call precondition). Cover:
the happy path, one auth-failure path, and one state-transition error
(e.g. unauthorized update, insufficient balance, duplicate key).

**Step 2 — Write them as re-runnable files** under `tests/workflows/*.py`
(httpx/requests, plain asserts, one scenario per file). Template:

```python
# tests/workflows/test_registration_flow.py
def test_register_then_create_then_persist(base_url, clean_state):
    r = httpx.post(f"{base_url}/api/register", json={"user": "u1", "pw": "x"})
    assert r.status_code == 201                       # entry call
    token = r.json()["token"]
    r = httpx.post(f"{base_url}/api/items",
                   headers={"Authorization": f"Bearer {token}"}, json={...})
    assert r.status_code == 201, r.text               # cross-endpoint dependency
    r = httpx.get(f"{base_url}/api/items/1",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.json()["owner"] == "u1"                  # state transition verified
```

**Step 3 — Three hard rules (non-negotiable):**
1. **Clean start state** — each workflow run starts from a known state: reset
   the DB, use unique-namespace fixtures, or restore snapshots. A dirty-state
   failure is a false failure; never debug it as a code bug.
2. **Assert state transitions, not just status codes** — every step checks
   what the call CHANGED (a query, a side effect, or the precondition of the
   next call). Status-code-only workflows miss the actual task contract.
3. **Trace on disk — real HTTP, not service-direct** — each run appends
   per-step request/response/assert results to `tests/workflows/<flow>.trace.log`.
   The trace is the loop's convergence evidence and the A4.9 reviewer's raw
   material. **A service-level direct call (importing the service class and
   calling it in-process) is NOT a workflow trace**: it bypasses routing,
   auth middleware, request parsing, and serialization — the layers where
   integration bugs actually live. If the change flows through the HTTP API
   (request → handler → DB → response), the workflow MUST be a real HTTP
   workflow against the server started via `script/` (COV-2).

**Step 4 — Run the workflow loop:** start backend via `script/` (COV-2), run
the workflow suite, and iterate with the SAME loop discipline as A4.7 Step 5:
any failure → read the failing step's trace + inspect the DB state BEFORE
fixing (§A4.6) → change ONE thing → re-run the full workflow suite → log each
iteration to `tests/verification_log.md` (FAIL lines carry `diagnosis:`).
Same cap=5 / stall=3× (COV-7); on stall apply §A4.10. Per-step timeout 10s,
whole scenario 120s, to prevent async issues from stalling the loop.

**Completion evidence for A4.4:** workflow file paths, trace logs, the
convergence line extended with workflow counts, and the E2E depth value:
`[Convergence] <task>: N iters | X/Y test cases pass | Z/W workflow cases pass | stalls | cap-hits`
plus `E2E depth: real-HTTP` (or `workflow-trace`) in the `[Verification
Gate]` line. Example: `[Convergence] memory recall fix: 6 iters | 15/15
test cases | 2/2 workflow cases pass | 0 stalls | 0 cap-hits` +
`E2E depth: workflow-trace` — and a real-user chat verification qualifies
as `real-HTTP`.

**Skip only if:** the change has no cross-endpoint behavior AND no
state-transition semantics (pure function or single-endpoint tweak) — then
state the skip reason explicitly in the completion table AND report
`E2E depth: service-direct` or `unit-only` with the reason. "I verified the
service layer directly" is NOT a valid E2E substitute for a cross-endpoint
change.

---

## A4.8 TDD for Logic-Bearing Code ★ NON-NEGOTIABLE

**Core principle: If you didn't watch the test fail, you don't know if it
tests the right thing.** A test written after the code passes immediately
proves nothing — it may test the wrong thing, test the implementation instead
of the behavior, or miss the edge case you didn't think of.

**Scope — where test-first applies:**

| Layer | Rule |
|---|---|
| **Logic-bearing code** — backend services/repositories/utils, data transforms, validation, frontend state/business logic | **Test-first (this section)** |
| **UI / E2E rendering** — pages, components, layout | Test-after is correct here: the §A4.1 screenshot loop |
| **Backend API surface** | §A4.7 loop; test-first ordering for NEW endpoints (above) |
| **Exempt** — pure config files, markup/copy, docs, generated code | No test required (state the skip reason) |

**The cycle (RED → GREEN → minimal):**
1. **RED — write ONE failing test** for the next small behavior. One
   behavior per test, clear name, real code (mocks only when unavoidable).
2. **Verify RED — run it and WATCH it fail.** Confirm: it fails (not errors),
   the failure message is the expected one, and it fails because the feature
   is missing (not a typo). A test that passes immediately is testing existing
   behavior — fix the test. **Paste the failing output into
   `tests/verification_log.md`** — this is the RED evidence for COV-1 / Gate 1.
3. **GREEN — write the minimal code to pass.** Nothing beyond what the test
   demands (YAGNI).
4. **Verify GREEN — run it and watch it pass**, and confirm the rest of the
   suite still passes with pristine output (no warnings).
5. **Commit** (or fold into the task's commit), then next failing test.

**Wrote code before the test?** Delete it and start over from the test. Don't
keep it as "reference", don't "adapt" it while writing tests — that's
test-after in disguise.

**Regression tests — the red-green verification method:** a regression test is
only proven if it can catch the bug:
```
Write test → run (PASSES with fix present) → revert the fix → run (MUST FAIL)
→ restore the fix → run (passes)
```
A regression test that was never watched failing on the buggy code is
unproven — complete this cycle before claiming the bug is covered.

**Red flags — STOP and restart test-first:**
- Code before test, or test added "after, just to cover it"
- Test passes on first run and you can't explain what production change would break it
- "Too simple to test" / "I'll test after" / "I already manually verified it"
- Can't name the production change that would make the test fail
- **The verification reference shares the candidate's assumptions** — a
  "brute force" or oracle that inherits the same cleverness inherits the same
  bug and will agree with it beautifully while both are wrong (see §A4.10
  TRUST-AND-VERIFY)

---

## A4.9 Independent Code Review (Major Changes)

This is the canonical text of COV-8. The maker/checker split covers
screenshots — but the CODE itself is otherwise only ever seen by the model
that wrote it. For major changes, dispatch an independent reviewer BEFORE
the A4.4 completion table (and AFTER Gate-1 test evidence exists). For minor
changes: state `A4.9 not triggered — reason: <…>` in the [Verification Gate]
line and proceed.

**Trigger ANY of:** new feature · ≥3 files changed · schema/API-surface change ·
security-sensitive area · **behavior-semantic change** (a runtime pipeline /
write-path / type-distinction semantic is altered — e.g. the v1/v2 dream
dual-write split; a one-line diff can still be a behavior change).
**"Files changed" counts EVERY path in `git diff --stat $BASE..$HEAD`** —
tests, docs, and config included; "only core logic files changed" is NOT a
valid reduction (observed rationalization). **Skip for:** mechanical
single-file bugfixes with NO behavior-semantic change, copy/style tweaks,
config edits — each `A4.9 not triggered` reason in the gate line must cite
`git diff --stat` output, not self-recollection.

**How:**
1. Get the review range: `BASE_SHA` = baseline commit (C2 Step 5), `HEAD_SHA` =
   final commit. Write `git log --oneline $BASE..$HEAD`, `git diff --stat`, and
   `git diff -U10 $BASE..$HEAD` to ONE file (e.g. `tests/review_package.md`) —
   hand the reviewer the FILE, keeping the diff out of your own context.
2. Dispatch a reviewer subagent (opencode `task` tool) with: the file path,
   the acceptance criteria / requirements (or `tests/acceptance.md` path), and
   this verdict contract — **Strengths · Issues (Critical / Important / Minor,
   each with file:line + why it matters) · Assessment (ready / ready-with-fixes
   / not ready)**. The reviewer is READ-ONLY: it inspects, never mutates the
   working tree.
3. Act on the verdict (fix-round loop):
   - **Critical** → fix now; re-run covering tests; scoped re-review (Step 4).
   - **Important** → fix before the completion table; re-run covering tests;
     scoped re-review.
   - **Minor** → record in memory as deferred; point it out in the completion
     table. Minor never enters the fix loop.
   - **Fix-round loop:** one round = one fix dispatch + one scoped re-review
     (Step 4). Max **5 rounds** per review wave. Reuse A4.1's stall rule
     (same finding ≥3 consecutive rounds → STOP retrying that direction;
     apply §A4.10 to generate the genuinely different direction). At the cap,
     **adjudicate each open finding yourself** — you hold the cross-task
     context the reviewer lacks: park with a ruling (`parked — <finding> —
     ruling: <why the code stands>`), or if load-bearing (a later task builds
     on it / it reveals a plan defect) STOP and escalate. Critical/Important
     findings MUST be fixed or parked-with-ruling before the A4.4 completion
     table. A silent discard is forbidden — every ruling is a recorded entry.
4. **Scoped re-review:** regenerate the review package over the fix range —
   `git diff $FIX_BASE..$HEAD` where `$FIX_BASE` = the head the previous
   review saw — and re-dispatch the reviewer with the new package plus the
   open-findings list. The re-review verdicts each finding
   **ADDRESSED / NOT ADDRESSED** and flags NEW breakage in the fix diff only;
   out-of-scope observations become deferred Minors and never extend the loop.
5. **Reviewer disagreement is allowed** — if a finding is technically wrong
   for THIS codebase, push back with reasoning (cite working tests/code)
   instead of complying blindly. Record the ruling. Never silently discard.

**Red flags:** skipping review because "it's simple" · fixing findings without
re-running tests · accepting every suggestion without verifying it against the
codebase.

---

## A4.10 Stall Escape: Parameterize · Differential-Test · Dual-Path

Companion to COV-7 (`cap=5 stall=3×`). COV-7 decides WHEN a loop must stop;
this section decides WHAT TO DO at that stop. A stall followed by
"retry, again but slightly different" is not an escape — it is the same spin
with new vowels. Mechanisms adapted from J-Space Cognition Suite (see repo
README → Attribution).

### DROWNING DETECTION — recognize it early

Stall signals: the same sub-problem re-derived with no new constraint ·
constraints flip-flopping between iterations · the same test failing with a
mobile but related error · three failed fixes on the same problem (see
§A4.6 escalation). **Any two signals → declare the stall explicitly in the
log** (`- stall: <signals> — stopping pure iteration`). An undeclared stall
becomes silent guessing, which looks exactly like reasoning right up until it
is wrong.

### PARAMETRIZE — make the unknown finite (before the next direction is chosen)

1. Name exactly what the failed iterations could not settle. One unknown per
   line, in the log.
2. Enumerate plausible values as a **finite candidate set** (`timeout ∈
   {30s, 60s, 120s}`; `the bug is in {routing, auth middleware, handler,
   serializer}`). If the set will not go finite, discretize the dimension
   that matters and say explicitly what was dropped — an unbounded unknown
   cannot be tested and will not settle by a fourth guessing iteration.
3. Every candidate stays live until evidence kills it. A killed candidate
   gets recorded with the evidence that killed it (→ memory ❌ per
   MEMORY_RULES.md §A7.7). No premature favourites.
4. Name **the cheapest test that could refute each candidate.** A test that
   could not have come out the other way is not a test — it is a ceremony.

### TRUST-AND-VERIFY — differential testing with an independent reference

When the verification itself is in doubt (the candidate "works" but you
cannot trust the check):

1. **Build the reference** — the simplest independent procedure whose
   assumptions are explicit and separately checked: brute force, exhaustive
   enumeration, a second data path, a hand-worked example.
2. **The reference must NOT share the candidate's cleverness.** If it
   inherits the same assumption (same SQL dialect quirk, same off-by-one
   window, same trigger condition), it inherits the same bug and will agree
   with the candidate beautifully while both are wrong. Where they must
   share an assumption, test that assumption separately and say so.
3. **Differential-test:** same inputs to both. Compare outputs. Sweep small
   cases, edge cases (empty, single, maximum, degenerate) and randomized
   cases wherever they are cheap.
4. **Every mismatch is a gift** — it localizes the false assumption better
   than any amount of re-reading. Study the mismatch, refine, re-test.
5. **State the coverage with the conclusion** — what the sweep covered and
   what it did not. "Verified" without a stated scope is not a result.
   (This is machine-checked: `assert_artifacts.py` group 13 flags claimed
   coverage in `verification_log.md` that lacks a scope.)

### DUAL-PATH RECONCILE — two cheap routes, compare, then commit

When two independent, cheap verification routes are available (e.g. read the
state **through the API** AND **directly from the database**; run the build
in `.venv` AND with system python; `git diff` AND `git diff --stat`
cross-check on file count), take BOTH before declaring a conclusion:

- Where they agree → confidence is earned; record both routes in the log.
- Where they disagree → you have located the faulty assumption — the
  disagreement IS the finding. Record it and resolve from the discrepancy,
  not from re-reading.

This is the diagnosis clause's (A4.1 Step 4) source: a retry without a
diagnosis is the same attempt again; a diagnosis earns its cost only when it
is falsifiable by a second path.

### SHIFT — the licensed exit moves

After parametrizing, the next direction MUST be one of:
1. **Shift the abstraction** — the frame is fighting the facts; tighten,
   split, or replace it.
2. **Shift the strategy** — same goal, genuinely different route (different
   layer, different tool, different representation).
3. **Shift to empirics** — stop deriving, start measuring (this section).

Shifting to vagueness, to summarizing the problem, or to "let me try it
again" is not a licensed shift. And: if the same wall returns a **third
time**, the problem is mis-framed, not mis-solved — restate it in different
primitives (→ §A4.6 escalation to the user).
