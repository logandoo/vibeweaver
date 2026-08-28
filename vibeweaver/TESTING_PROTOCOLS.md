# TESTING_PROTOCOLS.md — Canonical Loop / Debug / Test / TDD / Review / Stall-Escape Protocols

> Companion rulebook for [SKILL.md](SKILL.md). **Read IN FULL (Read Contract R1
> in SKILL.md) on any task that touches code, BEFORE the first code action** —
> it holds the full protocol text behind the SKILL.md binding stubs: §A4.1
> (capture-driven verification loop), §A4.6 (systematic debugging), and the
> canonical text of §A4.7 (COV-6), §A4.7b, §A4.8, §A4.9 (COV-8), plus
> §A4.10 (stall escape). If in conflict with §1 covenants in SKILL.md, the
> covenants prevail. Section numbers are preserved so cross-references
> (`A4.1`, `A4.6`, `A4.8`, …) keep resolving.

## Contents

- **§A4.1 Capture-Driven Verification Loop** — full protocol: verifier probe
  (model-native self-probe → mm-sensor → direct read), acceptance gate,
  capture + grading call tables, runtime degradation, decision rules,
  convergence
- **§A4.1.1 Visual Verification Protocol** — mandatory grading chain for the
  model-native verifier (observation-first · per-criterion verdicts · DOM
  cross-check · UNCERTAIN=FAIL)
- **§A4.6 Systematic Debugging — Four Phases** + escalation
- **§A4.7 Backend-Only Task: API Doc-Driven Test Loop** (COV-6 canonical)
- **§A4.7b Workflow Scenario Tests** (task-level backend verification)
- **§A4.8 TDD for Logic-Bearing Code**
- **§A4.9 Independent Code Review (Major Changes)** (COV-8 canonical)
- **§A4.10 Stall Escape: Parameterize, Differential-Test, Dual-Path**
  (companion to COV-7)

---

## A4.1 Capture-Driven Verification Loop (UI/runtime-visible changes)

A **convergent** loop: verifiable stop condition · independent verifier
(maker/checker split) · iteration cap · stall detection. REQUIRED for every
frontend/UI/runtime-affecting change — no exceptions.

**Step 0 — Detect + announce the media verifier (AT TASK START, before any code, in ZERO):**
Three verifier modes exist — `model-native [image]` (the current model is
image-perceptive, PROBED not assumed), `mm-sensor [video+audio|video|image]`
(external media verifier), `direct read` (neither available). Probe IN THIS
ORDER; the announced mode is fixed for the task (one probe per task; the
probe is the single source of truth, not a filesystem/config guess).

- **Step 0a — Self-multimodality probe (the model probes ITS OWN perception).
  Behavioral, never declarative** — self-declaration ("I support images") is
  NOT evidence; capability is established by reading generated pixels.
  `VW_DIR` = this skill's installation directory.
  ★ **Precedence:** this probe runs BEFORE any mm-sensor invocation. When it
  PASSES, mm-sensor's blanket "never use your own vision / Read tool on
  media" mandate does NOT apply to screenshot grading in this task — the
  §A4.1.1 protocol governs instead (mm-sensor still grades video/audio
  evidence per the hybrid rule below, and remains the verifier whenever the
  probe fails). Do NOT let mm-sensor's description trigger before this
  probe runs.
  1. Run `python3 {VW_DIR}/scripts/mm_probe.py --generate` → writes
     `tests/probe_vision.png` (random 6-char token + one of 5 palette
     colors) and `tests/probe_vision.expected` (ground truth).
  2. Read `tests/probe_vision.png` with the Read tool. **Media-Read is
     ALLOWED for this probe artifact only** — it is a vibeweaver probe
     artifact, not media being graded; the mm-sensor Read-ban applies to
     grading captured media, not to the probe. Read the PNG BEFORE running
     `--check` (the token is random per run — nothing to recall).
  3. Report what you actually perceive: exact token + color name. If the
     Read errors (`Cannot read image …`) or you genuinely cannot extract the
     token/color, report that honestly — a failed probe is a valid result.
   4. Validate: `python3 {VW_DIR}/scripts/mm_probe.py --check <token> <color>`.
      - **exit 0 (PASS)** → the model IS image-perceptive → announce
        `Verifier: model-native [image]`. PASS criterion: color exact AND
        >= 5 of 6 token chars in exact positions (the 5x7 font is
        ambiguity-pruned; a blind guesser scores ~0-1/6, so the gate is
        unpassable without real perception, while one isolated slip no
        longer disqualifies a vision-capable model).
        Screenshots are graded via the
        Read tool under **§A4.1.1 Visual Verification Protocol**
        (observation-first · per-criterion verdicts · DOM/log cross-check ·
        UNCERTAIN=FAIL). The §A4.1.1 chain is the countermeasure to
        self-grading bias (the maker is the checker in this mode).
     - **exit 1 (FAIL)** → the model is NOT image-perceptive → Step 0b.
     - **exit 2 / error** → fix the probe invocation, re-run; on repeat
       failure treat as FAIL (0b).
  5. Record the result in `tests/verification_log.md`:
     `- probe: model-native PASS (probe_vision.png)` or
     `- probe: model-native FAIL → mm-sensor`.
- **Step 0b — mm-sensor probe (only when 0a FAILED):** check `available_skills`
  for `mm-sensor` (opencode injects this list; it is authoritative — not a
  filesystem guess).
  - **`mm-sensor` IS in available_skills** → MANDATORY independent verifier.
    - Derive `SKILL_DIR` from the `<location>` in available_skills.
    - Run the capability probe (cheap, no tokens):
      `python3 {SKILL_DIR}/vision.py --probe` and parse the JSON:
      `media_capabilities` (absent/empty = all three) and `error` (non-null =
      config broken → fix the config, then re-probe).
    - Announce the verifier WITH its modality mode (COV-5):
      `Verifier: mm-sensor [video+audio]` · `Verifier: mm-sensor [video]` ·
      `Verifier: mm-sensor [image]` — the mode decides the capture set in
      Step 2 and the grading set in Step 3.
    - Invoke with `--detail high` for EVERY captured media file (video /
      audio / screenshots alike):
      `python3 {SKILL_DIR}/vision.py --detail high /path/to/file.webm`.
    - NEVER use the model's own vision or the Read tool on media while
      mm-sensor is the verifier — that is self-grading and a violation.
      There is no fallback to self-grading: on call errors, fix the config
      (missing API key etc.) and retry; only after repeated failure escalate
      to the user.
  - **`mm-sensor` NOT in available_skills** → Step 0c.
- **Step 0c — direct read fallback (0a FAILED and no mm-sensor):** announce
  `Verifier: direct read (no multimodal model, no mm-sensor)`. **This is the
  weakest verifier: the model cannot perceive pixels at all** — the
  screenshot is NOT the evidence channel here. Verification must lean on
  DOM queries (`querySelector` / `getComputedStyle` / `textContent` /
  `boundingClientRect`), log inspection, and API responses; screenshots are
  kept as artifacts for human/mm-sensor review later. Be extra strict and
  cross-check everything.
- **Hybrid (model-native + mm-sensor):** when the verifier is `model-native
  [image]` but acceptance criteria require video/audio evidence and mm-sensor
  is installed → grade THOSE files via mm-sensor (`vision.py --detail high`)
  and record the hybrid in the log. Without mm-sensor → record
  `video/audio: not gradeable` in the log and verify the underlying state
  via DOM/API/log instead.

---

## A4.1.1 Visual Verification Protocol — model-native verifier ★

`model-native [image]` means the SAME model that wrote the code grades the
captures with its own vision — the maker/checker split is weakened by
construction, and the chain below is the MANDATORY countermeasure. SOTA
basis (2026): MJ1 grounded verification chain observations → claims →
verification → evaluation (arXiv 2603.07990); WebDevJudge query-grounded
rubric trees + code-as-critical-modality (arXiv 2510.18560); Vision2Web
component-level rubrics (arXiv 2603.26648); IRA environment-state
verification (arXiv 2607.25904); CUAAudit abstention/calibration
(arXiv 2603.10577); MM-JudgeBias compositional bias (ACL 2026).

**A bare judgment is NEVER valid.** "Meets criteria", "looks good", "layout
is fine" — not verdicts. Every verdict is produced by this chain, IN ORDER:

**1. OBSERVE-FIRST (never judge before describing).** From the screenshot,
enumerate what IS on screen, zone by zone (header / nav / main / sidebar /
footer / modals): every element with position, rendered text, colors, and
state (visible / disabled / empty). Only what is actually visible — no
inference, no "should be"; absence is recorded as absence ("no modal is
open"). Observation extraction comes FIRST because visual attention is
highest then and open-ended judgment later loses pixel detail (MJ1).

**2. CLAIM EXTRACTION (rubric tree).** Decompose every acceptance criterion
into atomic, individually-verifiable claims (WebDevJudge): criterion #2
"password field exists and is empty" → claims "a text input is present in
the form zone" · "it is of type password" · "it renders empty".

**3. CLAIM↔OBSERVATION VERIFICATION.** Match each claim against the
observations. A claim with no matching observation = FAIL for that
criterion — not "close enough", not "probably". An observation that
contradicts a claim = FAIL.

**4. DOM/STATE CROSS-CHECK (MANDATORY for state-dependent criteria).**
Pixels cannot prove state (IRA hidden-state tasks; WebDevJudge: code is the
most critical modality). Every criterion whose truth depends on behavior —
persisted data, navigation, async rendering, computed styles, hidden or
overflowing elements, response codes — MUST additionally be checked via
`page.evaluate` (querySelector / getComputedStyle / textContent /
boundingClientRect), API response, or log inspection. The screenshot is
necessary but never sufficient for state-dependent criteria. Record both
evidence legs in the verdict.

**5. ABSTAIN ON UNCERTAINTY (UNCERTAIN = FAIL).** If the screenshot or DOM
cannot determine a criterion — clipped viewport, resolution, unreadable
text, ambiguous state, animation mid-flight — the verdict is
`UNCERTAIN: <what is missing>` and COUNTS AS FAIL for the loop (CUAAudit
calibration; uijudge-bench abstention). Never guess. An UNCERTAIN verdict
forces the loop to improve the evidence (re-capture, larger viewport, DOM
probe) — a silent guess converts a bad screenshot into a false pass.

**6. PER-CRITERION VERDICT SHEET (the only valid verdict form):**
```
criterion #N: PASS | FAIL | UNCERTAIN — evidence: <quoted observation or DOM fact>
```
A PASS without a quoted observation/DOM fact is invalid — same evidence
discipline as mm-sensor grading. Loop exit requires every criterion PASS
(no UNCERTAIN outstanding).

**7. MAKER/CHECKER HONESTY RULE.** In model-native mode the grader built the
page. Guardrails: (a) observation and verdict are separate passes — never
interleave with "I remember writing X"; (b) when a criterion's verdict is
load-bearing and mm-sensor is installed, run BOTH and reconcile
(DUAL-PATH RECONCILE §A4.10) — disagreement locates the faulty judgment.

**Video/audio in model-native mode:** screenshots are graded natively;
video/audio evidence is graded via mm-sensor if installed (hybrid, recorded
in the log), else recorded `video/audio: not gradeable` and the underlying
state verified via DOM/API/log.

---

**Step 1 — Acceptance Criteria Gate (BEFORE acting — USER-OWNED STOP CONDITION):**
The stop condition is owned by the **user**, not invented by the agent.
Decompose the request into explicit, individually-checkable pass/fail
criteria. ONE criterion = ONE pass/fail sentence a verifier can answer yes/no.

1. Write criteria to `tests/acceptance.md` — first line verbatim `> cap=5  stall=3×`,
   then one numbered line per criterion. Example:
   ```markdown
   > cap=5  stall=3×

   # Acceptance Criteria — Login Page
   1. Username input field exists and is empty on load
   2. Password input field exists and is empty on load
   3. "Sign In" button is visible and enabled
   4. No error/warning banner is shown on initial load
   5. Page title is "Login"
   6. Layout has no horizontal scroll at mobile breakpoint (375px)
   ```
2. Gate on clarity:
   - **Vague/ambiguous** (criteria not derived confidently) → STOP and ask the
     user before any code. Do not guess.
   - **Explicit** → list derived criteria and proceed.
3. **Immutability:** once confirmed these criteria are the **immutable convergence
   contract** for the loop. The agent MUST NOT add, drop, or relax a criterion
   mid-loop without asking the user.

**Step 2 — Act + Capture (modality-aware):** Playwright performs the
operation; capture evidence per the verifier mode announced in Step 0.
Save to `tests/` with descriptive names. Template: [APPENDIX.md §A1](APPENDIX.md).

Capture set per mode (mm-sensor loaded):

| Verifier mode | Captured evidence (per flow) |
|---------------|------------------------------|
| `model-native [image]` | `tests/<flow>.png` screenshots (before / during / after) — graded via Read tool under §A4.1.1 |
| `mm-sensor [video+audio]` | `tests/<flow>.mp4` (Playwright `record_video` → ffmpeg transcode from webm) + `tests/<flow>_audio.wav` (in-page Web Audio capture, injected via `add_init_script`) + `tests/<flow>_final.png` (terminal-state screenshot) |
| `mm-sensor [video]` | `tests/<flow>.mp4` + `tests/<flow>_final.png` (audio capture skipped) |
| `mm-sensor [image]` | `tests/<flow>.png` screenshots (before / during / after) — the original loop, nothing added |
| `direct read` | screenshots only as artifacts — the EVIDENCE channel is DOM/log inspection (Step 0c) |

Capture rules:
- **Video**: `context.record_video` (webm, e.g. 1280×720, ~fps 25-30); one
  video per user flow, recording the WHOLE Act sequence (clicks, fills,
  navigations, animations). Transcode webm → mp4 (ffmpeg) for grading —
  Playwright emits VP8/webm and several gateways (e.g. MiMo) accept mp4
  only; keep the raw webm too. No ffmpeg / transcode failure → grade the
  webm directly (mm-sensor degrades to frame-sampling; usable but lossy).
  Save the final file to a stable name (`tests/<flow>.mp4`) — see
  APPENDIX §A1.
- **Audio**: inject the Web Audio capture script BEFORE page load
  (`add_init_script`), dump via `page.evaluate` at flow end, assemble a WAV
  in Python (`wave` module) — captures Web Audio API + `<audio>`/`<video>`
  element output. Requires Chromium flag
  `--autoplay-policy=no-user-gesture-required`. If the page produced no
  audio (empty buffer / no AudioContext), write no wav and note
  `audio: none produced` in the log — do NOT grade silence as a failure
  unless an acceptance criterion requires sound.
- **Screenshots**: terminal-state `tests/<flow>_final.png` for EVERY mode
  (acceptance.md cites it; assert_artifacts.py checks cited pngs exist).
  For `[image]` mode also before/during shots.

**Step 3 — Observe (modality-aware):**
Grade evidence per mode — the grading set is decided by the Step 0 probe,
NOT by guessing:

| Verifier mode | Grading calls (all `--detail high`) |
|---------------|--------------------------------------|
| `model-native [image]` | Read tool per screenshot under §A4.1.1 (observation-first · per-criterion verdicts · DOM/log cross-check · UNCERTAIN=FAIL); video/audio via mm-sensor if installed (hybrid) |
| `mm-sensor [video+audio]` | `vision.py tests/<flow>.mp4 tests/<flow>_audio.wav` (one call, mixed media), plus `vision.py tests/<flow>_final.png` |
| `mm-sensor [video]` | `vision.py tests/<flow>.mp4` + `vision.py tests/<flow>_final.png` |
| `mm-sensor [image]` | `vision.py tests/<flow>.png` per screenshot (original loop) |
| `direct read` | DOM/log inspection primary (Step 0c); screenshots Read only as artifacts |

Runtime degradation (mm-sensor modes only — model-native/direct read have
no external-media fallback; §A4.1.1 rules 4-5 apply instead):
- Video graded but API returns `model_no_capability` / modality error →
  mm-sensor auto-falls back to frame-sampling (output marked
  `fallback: video→image`); treat the result as image-grade evidence and
  re-grade the terminal screenshot at `--detail high`.
- Audio graded but mm-sensor returns the `skipped` marker
  (`data-skipped="model_no_audio_capability"` in HTML / `skipped` field in
  JSON — audio has no fallback, mm-sensor reports it as a skip-with-
  suggestion, NOT an error) → drop audio from grading for this task,
  record `audio: skipped (model_no_audio_capability)` in
  verification_log.md, continue with video/screenshots. Audio is only
  ever an ADDED signal — its absence never fails a criterion by itself.

Parse the structured description (mm-sensor) or produce the per-criterion
verdict sheet (§A4.1.1 for model-native); check EVERY detail against
`tests/acceptance.md`. The verifier answers ONE specific question: *"Does
this captured evidence satisfy EVERY criterion in `tests/acceptance.md`?
List each criterion number with pass/fail and evidence."*

**Step 4 — Decide + Log convergence:**
Append EVERY iteration to `tests/verification_log.md` (create if absent):
```markdown
## Task: <name> | <ISO date>
- iter 1 FAIL: criterion #2 (password field missing) | diagnosis: onMount sets disabled while form pristine | changed: src/Login.tsx
- iter 2 FAIL: criterion #3 (button disabled)        | diagnosis: disabled state not reset after validation runs  | changed: src/Login.tsx
- iter 3 PASS: all criteria (evidence: tests/shot.png, 6/6)
```
**Diagnosis clause is MANDATORY on every FAIL line** — `| diagnosis: <one
falsifiable clause>` (the §A4.6 Phase 3 hypothesis compressed to one line,
stating what you believe broke and why). A retry that does not carry its
diagnosis is the same attempt again — same cost, buys nothing. Machine-
checked: `assert_artifacts.py` group 12. PASS lines state evidence + scope
(`6/6`, screenshot/log path), because a claim without stated coverage is not
a result (group 13).

Decision rules:
- **ALL criteria PASS** → loop exits. Record screenshot filename + verdict.
- **Any FAIL** → diagnose the specific defect from the verifier's output
  (cite the criterion #). Modify the code. Go to Step 2 (re-screenshot +
  re-verify).
- **Stall** (same criterion fails ≥3 consecutive iterations) → STOP retrying
  that direction. Declare it in the log (`- stall: <signals> — stopping pure
  iteration`). Record the failed approach in `memory/` as ❌, consult ⛔
  Forbidden entries, then generate the next direction by **§A4.10
  PARAMETRIZE** (finite candidate set + the cheapest test that could refute
  each — this file, §A4.10) before choosing: a
  "retry, again but slightly different" is the same spin, not a direction.
  OR **fresh-brain retry** (a fresh subagent/session carrying ONLY
  `tests/acceptance.md` + `tests/verification_log.md` + the relevant ⛔/❌
  memory entries — the memory does the knowledge transfer, that's what it is
  for) OR **escalate to the user** (see §A4.6 — 3+ failed fixes may signal
  an architectural problem).
- **Iteration cap = 5 max per sub-problem** → STOP. Record failure in
  `memory/`, report to user with the last screenshot + verifier output. Do
  not loop forever.

★ **Covenant Recall Check:** before emitting the next iteration, re-read §1
OPERATING COVENANT — confirm all covenants still hold for THIS iteration,
then proceed.

**Step 5 — Convergence summary + Persist state:**
Before the A4.4 completion table, output ONE convergence summary line per task:
```
[Convergence] <task>: <N> iters to converge | <passed>/<total> criteria pass | <stalls> stalls | <cap-hits> cap-hits
```
Example: `[Convergence] Login page: 3 iters | 6/6 pass | 0 stalls | 0 cap-hits`

Then persist state — every iteration is recorded in the fix-tracking memory
topic file so future sessions don't re-derive the same dead ends (A7.14 in
[MEMORY_RULES.md](MEMORY_RULES.md)). If convergence metrics reveal a baseline
(e.g. "this project's UI tasks average 2.3 iters"), record it as a `project`
memory entry for future A/B comparison.

The loop is only "done" when the **verifier** confirms every criterion passes —
not when the model that wrote the code says so. Mock data, console logs, "it
should work" assumptions are NOT valid substitutes.

---

## A4.6 Systematic Debugging — Four Phases ★

**No fixes without root-cause investigation first.** For ANY bug-fix task,
your narration MUST include a `## Root Cause Investigation (A4.6)` heading
BEFORE the implementation step — even when the user has already named the
cause — confirming root cause + reproduction + recent-changes + multi-layer
boundary diagnostics. Complete each phase before the next.

**Phase 1 — Root Cause Investigation (BEFORE any fix):**
- Read the **full** error message and stack trace — line numbers, paths,
  codes. Don't skip warnings.
- Reproduce the failure **consistently** before modifying code. If not
  reproducible → gather more data, don't guess.
- Check recent changes — `git diff`, recent commits, new deps, config/env
  changes.
- **Multi-component systems** (CI → build → service → database): add diagnostic
  logging at each component boundary, run once, let evidence show which layer
  breaks. Then investigate that layer.
- **Error deep in the stack:** trace the bad value backward — where does it
  originate, who called with it — until the source is found. Fix at the
  source, not at the symptom.

**Phase 2 — Pattern Analysis:**
- Find similar **working** code in the same codebase. Compare broken vs
  working and list **every** difference, however small — never assume "that
  can't matter".
- If following a reference implementation, read it **completely**.

**Phase 3 — Hypothesis & Minimal Testing:**
- Form ONE explicit hypothesis: "I think X is the root cause because Y".
  Write it down — it is the `diagnosis:` clause that A4.1 Step 4 requires
  on every FAIL log line.
- **Dual-path reconcile:** if two cheap, independent verification routes
  exist (e.g. read the state through the API AND directly from the DB),
  take BOTH before declaring the root cause — agreement earns the
  conclusion; disagreement LOCATES the faulty assumption
  (§A4.10 DUAL-PATH RECONCILE).
- Test with the **smallest possible change** — one variable at a time.
- If it doesn't work: **revert**, form a NEW hypothesis. Never stack a second
  fix on top of a failed one.
- If you don't understand something, say so and research — don't pretend.

**Phase 4 — Implementation:**
- Create a **failing reproduction test first** (per §A4.8) — proves the fix
  and prevents regression.
- Fix the root cause, not the symptom. ONE change — no "while I'm here"
  improvements.
- Verify: reproduction test passes AND no other tests break.
- Do not mask errors with broad `try/except`, retry loops, or silent
  fallbacks until the root cause is understood.

**Escalation — 3+ failed fixes = question the architecture:**
After **3 failed fixes on the same problem** (or each fix reveals a NEW
problem in a different place, or every fix demands "massive refactoring"),
STOP — this signals an **architectural** problem, not a wrong hypothesis. Do
NOT attempt fix #4 in the same direction. Record the failed methods in
memory (❌/⛔ per [MEMORY_RULES.md §A7.7](MEMORY_RULES.md)), then escalate to
the user: is the pattern fundamentally sound, or should the architecture
change? This complements A4.1's stall rule (3× same criterion): stall stops
the loop; this rule escalates the **direction**. The next direction is
generated by §A4.10 PARAMETRIZE (finite candidate set + cheapest refuting
test) — not by trying harder in the same frame.

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
`git diff --stat` output, not self-recollection. **Risk-tier paths —
non-skippable:** when the diff touches a code path matching
`(?i)(^|/)(auth|security|payments?|billing|crypto|migrations?|permissions?|acl)(/|\.|_|$)`
(code extensions only), the trigger fires REGARDLESS of file count —
`A4.9 not triggered` is not a valid gate-line reason for these; assert
group 16 machine-checks `tests/review_package.md` exists on disk.

**How:**
1. Get the review range: `BASE_SHA` = baseline commit (C2 Step 5), `HEAD_SHA` =
   final commit. Write `git log --oneline $BASE..$HEAD`, `git diff --stat`, and
   `git diff -U10 $BASE..$HEAD` to ONE file (e.g. `tests/review_package.md`) —
   hand the reviewer the FILE, keeping the diff out of your own context.
2. Dispatch a reviewer subagent (opencode `task` tool) with: the file path,
   the acceptance criteria / requirements (or `tests/acceptance.md` path), and
   this verdict contract — **Strengths · Issues (Critical / Important / Minor,
   each tagged with its dimension — `Bugs` (logic/edge cases) · `Security`
   (injection/authz/secrets/attacker-controlled input) · `Compliance`
   (matches acceptance criteria / plan / design principles) — with file:line +
   why it matters) · Assessment (ready / ready-with-fixes / not ready)**.
   Findings come back ranked by severity; **Minor findings are itemized at
   most 5, the rest summarized as a count** (nit cap — review must not become
   noise); generated paths and anything already mechanically enforced (hooks,
   assert groups) are out of scope for findings. The reviewer is READ-ONLY:
   it inspects, never mutates the working tree.
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
6. **Findings feed the rules (closed loop):** when the SAME mistake is flagged
   a second time — across reviews or sessions — the correction goes into
   project memory (feedback / ⛔ per A7.9), or the project's `CLAUDE.md` /
   `AGENTS.md` when one exists, so the mistake is caught at generation time,
   not at review. Review reads those files; the loop tightens itself.

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
