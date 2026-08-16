---
name: vibeweaver
description: |
  Enforce disciplined engineering workflows for all coding projects.
  TRIGGER when: user asks to build, modify, debug, or deploy any software project.
  ★ MANDATORY: Before any code — decompose problem, search web via exa MCP + Context7 for best solutions.
  ★ MANDATORY & SELF-STARTING: After any code change — autonomously enter the Playwright
  verification loop (NO user prompting required), and if mm-sensor is installed, use it as the
  verifier for every screenshot (self-grading is FORBIDDEN when mm-sensor is available).
  ★ MODALITY-AWARE: probe mm-sensor model capabilities (`vision.py --probe`) — record page
  operation video (Playwright recordVideo) + in-page audio (Web Audio capture) + screenshots;
  grade video/audio through mm-sensor when the model supports them, else degrade to the
  original image-only loop (no video support → screenshot loop; no audio support → skip audio).
  ★ HARD GATES: (1) NO TEST, NO DONE — every change must be proven by executed tests with log/screenshot
  evidence; (2) SCRIPT-ONLY — frontend builds and service start/stop/restart MUST go through script/
  scripts; raw `npm run build`, `vite`, `npm start`, `uvicorn` etc. are FORBIDDEN.
  ★ MANDATORY: For backend-only changes — update API doc, audit doc↔code consistency once,
  write test cases FROM the doc, then run the httpx/requests test→fix loop until all pass.
  Covers script-driven lifecycle, config management, testing, design docs, and acceptance checklists.
  Supports both new project scaffolding and existing project modification.
---

# Skill: vibeweaver — Core Executable Rules

**When this skill is triggered, you MUST follow this workflow for every task.** The
full procedural detail for some sections lives in companion files (see §By
the end of a task); this file is the binding operational contract.

---

## §1 OPERATING COVENANT — read first, never violate ★ NON-NEGOTIABLE

These are the **HARD GATES** and **SELF-STARTING TRIGGERS** of this skill. They are
repeated below only as canonical pointers; their authoritative text is in §A4
and §PART A. **A weak-model failure mode is to remember only §A4.1+§ZERO.**
So all eight rules below are doubled here at the very top — confirm you
comply with each before declaring done.

`COV-1. NO TEST, NO DONE` — every code change MUST be followed by actually
executed tests producing on-disk evidence (log files and/or screenshots —
plus operation video / page audio when the verifier mode supports them).
"Build passed" / "looks right" / no type errors are NOT evidence. Your
final `[Verification Gate]` line MUST contain the LITERAL token
`HARD-GATE-1: NO-TEST-NO-DONE=pass` (or `=na` for documentation-only
changes), confirming tests were executed with artifacts.

`COV-2. SCRIPT-ONLY lifecycle` — when a project has a `script/` directory,
ALL frontend builds AND service start/stop/restart go through those scripts.
`npm run build` / `vite` / `npm start` / `uvicorn` / `kill` are FORBIDDEN;
if `script/` is missing or broken → CREATE/FIX the scripts first, then use them.
Your final `[Verification Gate]` line MUST contain the LITERAL token
`HARD-GATE-2: SCRIPT-ONLY=pass` (or `=na` for tasks touching no build / no
service lifecycle).

`COV-3. ZERO before any code` — your very FIRST action is Step 0:
decompose the problem, search web via exa MCP + Context7, evaluate ≥2
approaches, then decide. Skip ONLY for trivial typo/config fixes; state the
skip reason explicitly.

`COV-4. SELF-STARTING Playwright loop` — the moment your change touches runtime
behavior (UI / API response / routing / rendered output / etc.), you AUTONOMOUSLY
enter the loop `Act → Capture → Verify → Fix → Log`. Never wait for the user
to ask. Pure config-file edits and documentation-only changes are the only
valid skips; state the skip reason.

`COV-5. Verifier announced at task start` — during ZERO, scan your
`available_skills` list. If `mm-sensor` is listed, the verifier is
MANDATORY: run the capability probe
`python3 {SKILL_DIR}/vision.py --probe`, read its JSON output, then
announce the verifier WITH its modality mode — `Verifier: mm-sensor
[video+audio]` (probe lists video+audio) · `Verifier: mm-sensor [video]` ·
`Verifier: mm-sensor [image]` (video/audio unsupported → original
screenshot-only loop). Grade every captured media file via
`python3 {SKILL_DIR}/vision.py --detail high <file>`; NEVER use the Read tool
on screenshots/videos/audio. If `mm-sensor` is NOT listed, announce
`Verifier: direct read (mm-sensor not installed)`. Skipping this
announcement means you skipped verification — go back.

`COV-6. Backend-only change → use §A4.7` — when the change touches ONLY backend
code (no browser-rendered output), replace the Playwright loop with the
API doc-driven test loop: update API doc → audit doc↔code consistency
ONCE → write test cases FROM the doc → run test→fix→test until ALL pass.

`COV-7. Loop convergence bound` — every loop is bounded by
`iteration cap = 5 per sub-problem` and `stall = same criterion fails 3×
consecutive iterations`. On cap/stall: STOP retrying that direction,
record the failed attempt in `memory/` as ❌, try a genuinely different
direction (or fresh-brain retry / escalate to user). The string
`cap=5  stall=3×` MUST appear as the top-line of every `tests/acceptance.md`
you write so the bound is visible to the user.

`COV-8. Major-change review dispatch (§A4.9)` — for ANY of: new feature ·
≥3 files changed · schema/API-surface change · security-sensitive area ·
**behavior-semantic change** (a runtime pipeline / write-path /
type-distinction semantic is altered — the v1/v2 dream dual-write split
is the canonical case: a one-file diff can still be a behavior change),
you MUST dispatch an independent reviewer (opencode `task` tool) over
`git diff <baseline>..<head>` BEFORE the completion table; receive verdict,
fix Critical/Important, re-run covering tests, record Minor to memory.
"Files changed" counts EVERY path in `git diff --stat` — tests, docs,
config included; "only core logic files changed" is NOT a valid reduction.
For changes meeting none of the triggers, the reason in the gate line MUST
be backed by `git diff --stat` output (actual file count + change kind),
not self-recollection:
`A4.9 not triggered — verified via git diff --stat: <N files, kind> — reason: <copy edit / config edit / …>`.

`COV-9. Baseline-GREEN before any change (Modify-Existing)` — for every
Modify-Existing task, your narration MUST include all three of these
literal tokens IN ORDER, on separate lines after you survey the project:
```
git add -A && git commit -m "backup: before changes"
bash script/linux/<existing-build-or-start-script>.sh  (or existing test runner)  — run-once baseline check
Baseline verified GREEN — proceed  (or: Baseline has N pre-existing failures → reported to user, logged to tests/verification_log.md, awaiting decision)
```
"Build passed earlier" does NOT count — and neither does the previous
change-wave's baseline in the same session: EVERY change-wave gets its own
three lines, even a follow-up fix minutes after the last run. Record the
verdict as the first entry under the task heading in
`tests/verification_log.md`: `- Baseline verified GREEN` (or
`- COV-9 skipped — reason: …`) — the file, not the narration, is what
assert_artifacts.py group 9 machine-checks. If the baseline already has
failures, report them and ask whether to proceed or fix first; record
pre-existing failures in `tests/verification_log.md`. Skipping this turns
every later failure into an unattributable regression — forbidden.
Pure-config fixes and doc-only edits may state-skip with:
`COV-9 skipped — reason: documentation-only change (no runtime to baseline-test)`.

`COV-10. Design Approval Gate (new feature / new project only)` — when
§A5 requires design docs, your narration MUST include a `## Design Gate A`
heading that presents ≥2 approaches + recommendation to the user, and a
`## Design Gate B — Spec Self-Review` heading containing the literal
checklist: *Placeholder scan · Internal consistency · Scope check ·
Ambiguity check* — each with pass/fail stated — followed by the line
`Proceeding (delegation recorded)` or an explicit confirmation request.
Bugfixes / minor tweaks / Modify-Existing 小改动 explicitly state:
`COV-10 skipped — á-bit-fix / minor tweak (no design doc per §A5 table)`.

`MANDATORY OUTPUT ARTIFACTS — every task that touches code MUST produce the
following on disk and in your final answer:`

- `tests/acceptance.md` — one numbered line per criterion; **first line
  verbatim** `> cap=5  stall=3×` (this is the user-owned stop condition).
- `tests/verification_log.md` — one entry per loop iteration; the format
  is given in §A4.1 Step 4. The file MUST have ≥1 iteration entry.
- `[Convergence] <task>: N iters | X/Y pass | N stalls | N cap-hits`
- `[Verification Gate]` line — see §A4.4 Gate Function preamble.
- `[Memory Gate]` line — see §A10 / A7.10 in [MEMORY_RULES.md](MEMORY_RULES.md).
- **8-column completion table** — see §A4.4. EXACT header order:
  `| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |`.

Skip none of these for any runtime-affecting change. State-skip is valid
ONLY for pure config-only edits and documentation-only edits; even then,
say so explicitly.

---

## §2 ZERO: Decompose & Research — BEFORE ANY CODE ★ NON-NEGOTIABLE

This is the VERY FIRST action after receiving a query. Do NOT read project
files, determine project mode, or make any changes until §2 is complete.

### Step 0.1 — Decompose the Problem
Break the user's query into clear sub-tasks. Identify:
- What is **known** vs **unknown**
- What **needs research** vs what can be done directly
- What **constraints** exist (tech stack, compatibility, deadlines)

If anything is still unclear, ambiguous, or under-specified: STOP and ask
the user (one question at a time, prefer multiple-choice). Do not silently
choose an interpretation and proceed.

### Step 0.2 — Web Research (skip ONLY if no internet or trivial typo/config fix)
When internet is available, search BEFORE writing any code:
1. **exa MCP** (`websearch` tool) — search for existing solutions, libraries,
   patterns, best practices, common pitfalls, official docs.
2. **Context7** (`webfetch` tool) — read GitHub repositories, real-world
   implementations, library source code, verify API signatures.
3. **Evaluate ≥2 approaches** — fit to project's existing stack, simplicity,
   active community support. Pick one; state why; state why not the others.

### Step 0.3 — Only Then Proceed
After research and approach choice, proceed to §3. **If you skip §0.2:**
state explicitly WHY and confirm the answer is unambiguously derivable from
existing code.

---

## §3 FIRST: Determine Project Mode — SECOND: Load Project Memory

### §3.1 Determine which mode you are in
| Mode | When | Apply |
|------|------|------|
| **Modify Existing** | Project already has code, config, scripts | Parts A, C2 |
| **New Project** | No code yet, scaffolding from scratch | Parts A, B, C1 |

When in Modify Existing mode, read the project's existing config, scripts,
and code before ANY changes. Do not apply new-project defaults blindly.

### §3.2 Load Project Memory (memory/MEMORY.md + topic files)
**Before making any changes, load the project's memory. This is the project's
persistent knowledge across sessions — user preferences, validated approaches,
project context, forbidden methods, and unverified fix attempts.**

Operational load rules are in [MEMORY_RULES.md §A7.6](MEMORY_RULES.md) — the
binding-version summary:

1. Check `memory/MEMORY.md` (or migrate from old `MODIFY.html` per A7.11). Also
   check user-global `~/.config/opencode/vibeweaver/memory/MEMORY.md` if it
   exists; merge with project-local (project-local overrides). Loading cap
   200 lines / 25KB.
2. Compute request keywords (problem symptom, feature name, file/module names,
   error messages). Use `grep` to **search** `memory/*.md` — index
   descriptions are not always obvious.
3. Load the top **3-5 most relevant** topic files, prioritized in this order:
   ⛔ Forbidden · ❌ Failed · ✅ Verified · ⏳ Unverified · feedback.
4. **Verify references** — for any loaded memory that names files/functions/
   line numbers, read the current code to confirm they still exist.
5. **Staleness check** — topic files >14 days old → display the age warning
   and verify code references before acting.
6. **⏳ Unverified overlap check** — if the current request overlaps a ⏳ fix
   in problem/symptom/affected file/attempted solution → mark it ❌ before
   attempting a new direction (A7.7 Implicit Failure Detection).

**Staleness caveat always applies:** memories are point-in-time observations;
file/line citations may be outdated. When in conflict, trust current code.

---

## PART A — Core Principles (All Projects, All Stacks)

These rules apply to EVERY project regardless of tech stack.

### A1. Coding Principles
See [CODING_PRINCIPLES.md](CODING_PRINCIPLES.md) — 4 iron rules:
Think Before Coding · Simplicity First · Surgical Changes ·
Goal-Driven Execution. Karpathy's internal CLAUDE.md adds 6 more disciplines
this skill enforces below: Read Before Code, Verification, Debugging,
Dependency Management, Communication, Common Failure Modes.

### A1.5 Problem Decomposition & Web Research ★ NON-NEGOTIABLE
→ See §2 ZERO at the top of this file. If anything is unclear: STOP and ask.

### A2. Script-Driven Lifecycle ★ NON-NEGOTIABLE

When the project has scripts in `script/` for build / start / stop /
restart — you MUST use them; NEVER bypass them with raw commands like
`npm run build`, `fastapi run`, `vite`, `uvicorn` (canonical text of COV-2).

| Action | Linux/macOS | Windows |
|--------|-------------|---------|
| Build & mount frontend | `bash script/linux/project_build.sh` | `script\windows\project_build.bat` |
| Start                 | `bash script/linux/start.sh`         | `script\windows\start.bat`         |
| Stop                  | `bash script/linux/stop.sh`          | `script\windows\stop.bat`          |
| Restart               | `bash script/linux/restart.sh`       | `script\windows\restart.bat`       |

If scripts don't exist yet → CREATE them first (APPENDIX.md §A6 templates),
then use them. If scripts are broken → FIX them, then use them. Never paper
over a broken script with a raw command.

**⚠ HOST-SAFETY (never violate):** stop/restart scripts MUST use the
`.pid`-file + `kill $(cat .pid)` pattern from APPENDIX.md §A6 — NEVER
`pkill -f "uvicorn ..."` / `pkill -f "python ..."` or any pattern-kill.
On shared hosts, `pkill -f "uvicorn app.main"` kills UNRELATED uvicorn
services owned by other sessions. Kill only the PID your start.sh recorded.
(COV-2 compliance includes writing safe stop scripts.)

### A3. Configuration Management
- All config MUST be read from the project's config file (typically `config.toml`).
- Never hardcode: host, port, database credentials, API keys, LLM parameters.
- **Existing projects:** read the existing config FIRST, use its values, do NOT
  overwrite credentials or settings with examples. The example password
  `8i9o0p-[=]` below is **an example only** — real projects have their own.
- **New projects:** create `config.toml` adapted to the actual stack.
- Read pattern:
  ```python
  import tomllib
  with open("config.toml", "rb") as f:
      cfg = tomllib.load(f)
  srv = cfg.get("server", {})
  HOST = srv.get("host", "127.0.0.1")
  PORT = srv.get("port", 8000)
  ```
- Example `[database]` / `[llm]` blocks: see [APPENDIX.md §A5](APPENDIX.md).

### A4. Testing & Verification ★ NON-NEGOTIABLE

This is the canonical text of COV-1, COV-4, COV-6, and COV-7. Required for
every code change—no exceptions.

#### A4.1 Capture-Driven Verification Loop (UI/runtime-visible changes)

A **convergent** loop: verifiable stop condition · independent verifier
(maker/checker split) · iteration cap · stall detection. REQUIRED for every
frontend/UI/runtime-affecting change — no exceptions.

**Step 0 — Detect + announce the media verifier (AT TASK START, before any code, in ZERO):**
Pro-actively check `available_skills` for `mm-sensor` (opencode injects
this list; it is authoritative — not a filesystem guess).

- **`mm-sensor` IS in available_skills** → MANDATORY independent verifier.
  - Derive `SKILL_DIR` from the `<location>` in available_skills.
  - Run the capability probe (cheap, no tokens):
    `python3 {SKILL_DIR}/vision.py --probe` and parse the JSON:
    `media_capabilities` (absent/empty = all three) and `error` (non-null =
    config broken → fix the config, then re-probe).
  - Announce the verifier WITH its modality mode (COV-5):
    `Verifier: mm-sensor [video+audio]` · `Verifier: mm-sensor [video]` ·
    `Verifier: mm-sensor [image]` — the mode decides the capture set in
    Step 2 and the grading set in Step 3. The mode is fixed for the task
    from this probe (one probe per task; the probe is the single source of
    truth, not a filesystem/config guess).
  - Invoke with `--detail high` for EVERY captured media file (video /
    audio / screenshots alike):
    `python3 {SKILL_DIR}/vision.py --detail high /path/to/file.webm`.
  - NEVER use the model's own vision or the Read tool on media while
    mm-sensor is loaded — that is self-grading and a violation. There is
    no fallback to self-grading: on call errors, fix the config (missing API
    key etc.) and retry; only after repeated failure escalate to the user.
- **`mm-sensor` NOT in available_skills** → Fall back to **loop engineering
  alone**: announce `Verifier: direct read (mm-sensor not installed)`
  and read screenshots via the Read tool. This is a weaker, self-grading
  verifier — be extra strict and cross-check with DOM/log inspection.

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
| `mm-sensor [video+audio]` | `tests/<flow>.mp4` (Playwright `record_video` → ffmpeg transcode from webm) + `tests/<flow>_audio.wav` (in-page Web Audio capture, injected via `add_init_script`) + `tests/<flow>_final.png` (terminal-state screenshot) |
| `mm-sensor [video]` | `tests/<flow>.mp4` + `tests/<flow>_final.png` (audio capture skipped) |
| `mm-sensor [image]` | `tests/<flow>.png` screenshots (before / during / after) — the original loop, nothing added |
| `direct read` (no mm-sensor) | screenshots only, read via Read tool |

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
| `mm-sensor [video+audio]` | `vision.py tests/<flow>.mp4 tests/<flow>_audio.wav` (one call, mixed media), plus `vision.py tests/<flow>_final.png` |
| `mm-sensor [video]` | `vision.py tests/<flow>.mp4` + `vision.py tests/<flow>_final.png` |
| `mm-sensor [image]` | `vision.py tests/<flow>.png` per screenshot (original loop) |
| `direct read` | Read tool on screenshots |

Runtime degradation (mm-sensor's own fallbacks still apply):
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

Parse the structured description; check EVERY detail against
`tests/acceptance.md`. The verifier answers ONE specific question: *"Does
this captured evidence satisfy EVERY criterion in `tests/acceptance.md`?
List each criterion number with pass/fail and evidence."*

**Step 4 — Decide + Log convergence:**
Append EVERY iteration to `tests/verification_log.md` (create if absent):
```markdown
## Task: <name> | <ISO date>
- iter 1 FAIL: criterion #2 (password field missing) | changed: src/Login.tsx
- iter 2 FAIL: criterion #3 (button disabled)       | changed: src/Login.tsx
- iter 3 PASS: all criteria
```

Decision rules:
- **ALL criteria PASS** → loop exits. Record screenshot filename + verdict.
- **Any FAIL** → diagnose the specific defect from the verifier's output
  (cite the criterion #). Modify the code. Go to Step 2 (re-screenshot +
  re-verify).
- **Stall** (same criterion fails ≥3 consecutive iterations) → STOP retrying
  that direction. Record the failed approach in `memory/` as ❌, consult ⛔
  Forbidden entries, then **try a genuinely different direction** (see §A4.6
  — 3+ failed fixes may signal an architectural problem) OR **fresh-brain
  retry** (a fresh subagent/session carrying ONLY `tests/acceptance.md` +
  `tests/verification_log.md` + the relevant ⛔/❌ memory entries — the memory
  does the knowledge transfer, that's what it is for) OR **escalate to the user.**
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

#### A4.2 Test Stack
| Tool | When |
|---|---|
| **Playwright** (Python) | screenshots + operation video (`record_video`) + in-page audio capture of running UI (front page, page, component, route) — APPENDIX §A1 |
| mm-sensor via `vision.py --probe` | capability probe: decides verifier mode `[video+audio]` / `[video]` / `[image]` (A4.1 Step 0) |
| mm-sensor via `vision.py --detail high <webm/wav/png>` | media verifier when available (maker/checker); grades video, audio, and screenshots per mode; else direct read (A4.1 Step 0) |
| `tests/acceptance.md` | user-owned stop condition (A4.1 Step 1) |
| `tests/verification_log.md` | per-iteration pass/fail log (A4.1 Step 4) |
| **httpx** preferred, else **requests** | backend API tests (A4.7) |
| Python **websockets** | WebSocket tests |

All tests MUST produce **log files** on disk.

#### A4.3 Verification Rules
- Do NOT rely on standardized/mocked test results
- Verify with: captured evidence of the running system — screenshots /
  operation video / page audio per the A4.1 Step 0 mode (graded via
  mm-sensor if available), log inspection, or DB queries
- Any result not matching an acceptance criterion = test failure
- **Act → Capture → Verify → Fix → Log → Repeat** until ALL criteria pass
  or cap=5/stall=3× stops you (COV-7)

#### A4.4 Completion Output ★ NON-NEGOTIABLE (canonical text of COV-8 final lines)

This is the **SOLE final deliverable**. Do NOT output "done" or "task
complete" without this EXACT table. No exceptions.

★ **Covenant Recall Check:** re-read §1 OPERATING COVENANT now. Every
covenant must hold for THIS completion output — any gap, go back and close
it before the table. Output the LITERAL line
`[Covenant Recall] checked: all 10 covenants hold for this completion`
immediately before the [Verification Gate] audit line, AND state
`covenant_recall: pass` in the [Verification Gate] line itself (the
in-line field is the enforcement channel re-review will check).

**Pre-output self-audit gate (answer these BEFORE the table; any NO = go back).**
Every claim follows the **Gate Function**:
**IDENTIFY** the command that proves the claim → **RUN** it fresh and complete
→ **READ** the full output + exit code → **VERIFY** the output confirms the
claim → **ONLY THEN** make the claim. Skipping a step is lying, not verifying.

1. Did any change affect runtime behavior? If YES → was the Playwright loop
   actually executed (captured evidence on disk under `tests/` per the
   A4.1 Step 0 mode — screenshots always, video/audio when the mode
   supports them — plus ≥1 entry in
   `tests/verification_log.md`)? If skipped → return to A4.1 Step 1 NOW.
2. Is `mm-sensor` in `available_skills`? If YES → was EVERY captured media
   file (video / audio / screenshots per mode) graded
   through `vision.py --detail high`? If self-read → re-grade through
   mm-sensor NOW.
3. Was the verifier announced at task start? If not, state it now and confirm
   rule 2 holds.
4. Were tests actually EXECUTED with artifacts on disk (log files /
   screenshots / verification_log entries)? If not → go run the tests NOW
   (COV-1, HARD GATE).
5. Were all builds and all service start/stop/restart done via `script/`
   scripts — zero raw `npm run build` / `vite` / `npm start` / `uvicorn`?
   If any raw command was used → re-do the operation via the script NOW
   (COV-2).
6. **Was verification run FRESH on the exact tree being delivered?** "Tests
   passed earlier this session" proves nothing — a green run only proves the
   tree it ran on. If any commit landed after the last test run, re-run the
   covering tests NOW.
7. **(Logic-bearing code) Was §A4.8 test-first followed?** Is RED evidence (the
   watched failure output) present in `tests/verification_log.md`, and did every
   regression test complete the revert-and-fail cycle? If code preceded tests
   → return to §A4.8 NOW.
8. **(Modify-Existing) Did COV-9 fire for THIS change-wave?** Is the literal
   `- Baseline verified GREEN` (or `- COV-9 skipped — reason: …`) present in
   `tests/verification_log.md` — not only in narration, not only in a previous
   change-wave? If not → run the baseline NOW and record it (COV-9).
9. **Was COV-8 discharged, not self-attested?** If `Code review:` in the gate
   line says `N/A`, is the reason backed by `git diff --stat` output (actual
   file count + change kind), not memory? Did ANY trigger fire — including
   behavior-semantic change? If yes → dispatch the A4.9 reviewer NOW, before
   the table (COV-8).

**The Gate Function binds every line you write to `tests/verification_log.md`.**
A log entry that says "X done" is a CLAIM about the world, not a marker — write
it only AFTER you have personally confirmed X is on disk (screenshot file
exists and > 0 bytes; the test output shows the pass; the trailing newline's
last byte is `0x0a`; the file moved is at its new path). A re-review will
byte-check your claims; a false "done" entry is a lie and a future reader's
trap — worse than no entry. **If a re-review finds a log claim false:** fix the
artifact AND add an explicit correction line naming what was wrong
(e.g. *"Correction to cycle-N log: claim '…' was false; artifact re-verified
and now matches"*). Never silently edit the old claim to look true-after-fact.

Output this audit line immediately before the completion table (the two
`HARD-GATE` tokens are LITERAL — every `[Verification Gate]` line MUST
contain the strings `HARD-GATE-1: NO-TEST-NO-DONE` and
`HARD-GATE-2: SCRIPT-ONLY`, each marked `pass` / `na`):
```
[Verification Gate] Verifier: mm-sensor [video+audio|video|image] | direct-read | Loop executed: yes/no/N/A | Media graded externally: N/N (video N · audio N · screenshots N) | Iterations: N | Tests executed with artifacts: yes/no | E2E depth: real-HTTP / workflow-trace / service-direct / unit-only | Script-only build/lifecycle: yes/no | Fresh-run on final tree: yes/no | TDD RED evidence: yes/no/N/A | Code review: clean / N-fixed / N/A | assert_artifacts.py: pass=N/fail=0 | covenant_recall: pass/na | memory_gate: pass/na | HARD-GATE-1: NO-TEST-NO-DONE=pass/na | HARD-GATE-2: SCRIPT-ONLY=pass/na
```

**E2E depth ladder (what each value means):** `real-HTTP` = the flow was
exercised through the running server's HTTP API (chat/API request → handler
→ DB → response), e.g. A4.7b workflow trace or a real-user chat ·
`workflow-trace` = A4.7b workflow scenarios with on-disk trace · 
`service-direct` = direct service-layer calls only — **NOT E2E**, only
acceptable for changes with no cross-endpoint behavior · `unit-only` = mock
unit tests only — only acceptable for pure functions / single-endpoint
tweaks (state the reason). Any runtime-affecting backend change with
cross-endpoint behavior MUST report `real-HTTP` or `workflow-trace`.

After ALL work is complete, output ONE summary table with ALL of these EXACT
columns in this EXACT order:

```markdown
| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |
|---|---------|--------------------------------------|------------------------|---------------|--------------|------------------------------------------|--------|
| 1 | ...     | Searched: X, Found: Y                | Approach Z (reason)    | src/a.ts, ... | ...          | screenshot_01.png → verified correct      | abc123 |
```

**FORBIDDEN alternatives — NEVER use these:**
- Do NOT split into multiple tables (e.g. a separate "Verification results" table).
- Do NOT replace columns with `Requirement`, `Implementation`, `Key files`,
  `Test method`, `Result`, or any other headers.
- Do NOT omit the `Research Sources` or `Commit` columns.
- Do NOT output prose summaries, bullet lists, or checklists as a substitute.

**Column requirements (all 8 mandatory):**
`#` sequential · `Problem` sub-problem addressed · `Research Sources` what was
searched, key findings, rejected alternatives · `Chosen Approach & Why` chosen
solution + rationale · `Files Changed` every modified file path · `What
Changed` concise modification description · `Verification Evidence`
screenshot filename+what was confirmed, or log file+key excerpt (not "tests
passed") · `Commit` short hash; `N/A` if no commit made yet.

If multiple changes were made, add one row per logical change.

#### A4.4.1 G-DED Executable Artifact Assertions ★ NON-NEGOTIABLE

Formal compliance is not evidence. Before emitting the `[Verification Gate]`
line, you MUST run the executable assertion script in the project root:

```bash
python3 tests/assert_artifacts.py [--existing] [--backend-only]
```

- Exit code 0 → append the LITERAL field `assert_artifacts.py: pass=N/fail=0`
  to the `[Verification Gate]` line (N = number of assertions executed).
- Exit code 1 → you may NOT declare done. The script output names the false
  claims; fix the ACTUAL artifacts on disk — never edit the script, never
  paste fabricated output, never skip the run — then re-run until exit 0.
- Flags: `--existing` (Modify-Existing task → skips the new-project §A5
  design-doc checks and the git-init expectation) · `--backend-only` (no UI
  → skips `PAGE_DESIGN.html` and `script/linux/project_build.sh`).
  New-project tasks run WITHOUT `--existing`.

**The script MUST check, at minimum (all of these):**

| # | Assertion | Evidence when FAIL |
|---|---|---|
| 1 | `tests/verification_log.md` exists with ≥1 `- iter N PASS/FAIL:` entry | COV-1 / A4.1 Step 4 |
| 2 | `tests/acceptance.md` exists, first line `> cap=5  stall=3×` | COV-7 / A4.1 Step 1 |
| 3 | every `tests/*.png` cited in those two files exists and >0 bytes | A4.4 |
| 4 | `memory/MEMORY.md` exists, has ≥1 topic-file link, and ≥1 topic `.md` besides MEMORY.md exists | A7.9 / A7.10 |
| 5 | `script/linux/start.sh` + `stop.sh` + `restart.sh` exist and are executable (`project_build.sh` too, unless `--backend-only`) | A2 / COV-2 |
| 6 | new-project tasks (no `--existing`): git repo exists with ≥2 commits (`git init` + initial commit + final commit; `git log --oneline` count) | C1 step 1/15, A9 |
| 7 | §A5 design docs exist: `FLOW_DESIGN.html` + `DATABASE_DESIGN.html` + `BACKEND_DESIGN.html` (+ `PAGE_DESIGN.html` unless `--backend-only`) — skipped with `--existing` | A5 / C1 step 2 |
| 8 | new-project tasks (no `--existing`): `README.md` or `README.html` exists, AND `requirements.txt` exists (backend; `package.json` for frontend projects) | C1 step 15 |
| 9 | Modify-Existing (`--existing`): `verification_log.md` contains `Baseline verified GREEN` or `COV-9 skipped` | COV-9 |
| 10 | every `tests/workflows/*.trace.log` cited in `verification_log.md` exists and >0 bytes | A4.7b |
| 11 | every `tests/*.webm` / `tests/*.wav` / `tests/*.mp4` / `tests/*.mp3` cited in `verification_log.md` exists and >0 bytes | A4.1 Step 2/3 |

The script (template: [APPENDIX.md §A8](APPENDIX.md)) byte-checks the
artifacts behind every Gate Function claim — the external verifier for
claims mm-sensor cannot see.

**If `tests/assert_artifacts.py` does not exist → COPY the block below
VERBATIM into `tests/assert_artifacts.py`** (do NOT write your own variant
— self-written variants consistently omit checks from the 10-group table
above; observed in real runs). The block is complete by construction; the
only allowed edit is adding project-specific assertion lines. This same
block is also in APPENDIX.md §A8 — copy from here when in doubt.

```python
"""G-DED artifact assertions — byte-level check of verification claims.
Mirrors SKILL.md §A4.4.1 minimum-check table (all 10 groups)."""
import argparse, pathlib, re, subprocess, sys

FAILS = []
PASSES = 0

def check(ok: bool, msg: str):
    global PASSES
    PASSES += 1
    if not ok:
        FAILS.append(msg)

def read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

def main():
    global PASSES
    ap = argparse.ArgumentParser()
    ap.add_argument("--existing", action="store_true", help="Modify-Existing task: skip new-project §A5 design-doc + git checks")
    ap.add_argument("--backend-only", action="store_true", help="no UI: skip PAGE_DESIGN.html and project_build.sh checks")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    tests = root / "tests"
    vl = read(tests / "verification_log.md")
    acc = read(tests / "acceptance.md")

    # 1) verification_log — exists, has >=1 standard iteration entry (COV-1)
    check(vl and len(vl.strip()) > 0, "tests/verification_log.md missing or empty (COV-1)")
    check(bool(re.search(r"^- iter \d+ (PASS|FAIL):", vl, re.M)),
          "verification_log.md has no `- iter N PASS/FAIL:` entries (A4.1 Step 4)")

    # 2) acceptance.md — exists, first line cap/stall stop-condition (COV-7)
    check(bool(re.search(r"^>\s*cap=5\s+stall=3", acc, re.M)),
          "tests/acceptance.md missing first line `> cap=5  stall=3×` (COV-7)")

    # 3) screenshots cited in the log files must exist >0 bytes (A4.4)
    for png in re.findall(r"tests/(\S+\.png)", vl + "\n" + acc):
        p = tests / png
        check(p.exists() and p.stat().st_size > 0,
              f"screenshot claimed but missing/empty: tests/{png} (A4.4)")

    # 4) memory — MEMORY.md + >=1 topic file + index pointers (A7.9/A7.10)
    mem = root / "memory"
    idx_text = read(mem / "MEMORY.md")
    check(bool(idx_text), "memory/MEMORY.md missing (A7.10)")
    if idx_text:
        topics = sorted(mem.glob("*.md"))
        check(len(topics) >= 2, "memory/: MEMORY.md + >=1 topic file required (A7.9)")
        check(bool(re.search(r"\]\([^)]+\.md\)", idx_text)),
              "memory/MEMORY.md index has no topic-file pointers (A7.9)")
        check(any(p.name != "MEMORY.md" for p in topics),
              "memory/: at least one topic file besides MEMORY.md (A7.9)")

    # 5) scripts — start/stop/restart (+ project_build unless --backend-only) (A2/COV-2)
    for s in ["start.sh", "stop.sh", "restart.sh"]:
        sp = root / "script" / "linux" / s
        check(sp.exists() and (sp.stat().st_mode & 0o111),
              f"script/linux/{s} missing or not executable (A2/COV-2)")
    if not args.backend_only:
        bp = root / "script" / "linux" / "project_build.sh"
        check(bp.exists(), "script/linux/project_build.sh missing (A2; use --backend-only if no UI)")

    # 6) git — new projects: repo exists with >=2 commits (C1 step 1/15, A9)
    if not args.existing:
        try:
            r = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
                               capture_output=True, text=True, timeout=20)
            rc, out = r.returncode, r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            rc, out = -1, ""
        n_commits = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
        check(rc == 0 and n_commits >= 2,
              f"new-project git repo needs >=2 commits (init + final); found {n_commits} (C1 step 1/15)")

    # 7) §A5 design docs — new projects (skipped with --existing) (A5 / C1 step 2)
    if not args.existing:
        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html"]:
            check((root / doc).exists(), f"new-project design doc missing: {doc} (A5 / C1 step 2)")
        if not args.backend_only:
            check((root / "PAGE_DESIGN.html").exists(),
                  "new-project design doc missing: PAGE_DESIGN.html (A5; use --backend-only if no UI)")

    # 8) README + requirements — new projects (skipped with --existing) (C1 step 15)
    if not args.existing:
        check(any((root / n).exists() for n in ["README.md", "README.html"]),
              "new-project README.md/README.html missing (C1 step 15)")
        check(any((root / n).exists() for n in ["requirements.txt", "package.json"]),
              "new-project requirements.txt/package.json missing (C1 step 15)")

    # 9) COV-9 — Modify-Existing tasks: baseline verdict recorded on disk (COV-9)
    if args.existing:
        check(bool(re.search(r"Baseline verified GREEN|COV-9 skipped", vl, re.M)),
              "tests/verification_log.md missing `- Baseline verified GREEN` or `- COV-9 skipped —` entry (COV-9)")

    # 10) A4.7b — workflow traces cited in the log must exist >0 bytes (A4.7b)
    for wf in re.findall(r"tests/workflows/(\S+?\.trace\.log)", vl):
        p = tests / "workflows" / wf
        check(p.exists() and p.stat().st_size > 0,
              f"workflow trace claimed but missing/empty: tests/workflows/{wf} (A4.7b)")

    # 11) A4.1 — video/audio evidence cited in the log must exist >0 bytes (A4.1 Step 2/3)
    for m in re.findall(r"tests/(\S+\.(?:webm|wav|mp4|mp3))", vl):
        p = tests / m
        check(p.exists() and p.stat().st_size > 0,
              f"media evidence claimed but missing/empty: tests/{m} (A4.1)")

    if FAILS:
        print("ASSERT FAILURES (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print(f"assert_artifacts.py: all {PASSES} checks pass (exit 0)")

if __name__ == "__main__":
    main()
```

When running with `--backend-only` and skipping `PAGE_DESIGN.html`, the
completion table MUST state the literal phrase
`Page design skipped — backend-only project (no UI)` in the `What Changed`
column.

**Self-verify the script is complete (MUST do after writing it):** the
script MUST contain each of these 11 markers — `verification_log` · `cap=5`
· `screenshot` · `MEMORY.md` · `start.sh` · `git repo needs` · `FLOW_DESIGN`
· `README` · `Baseline verified GREEN` · `workflow trace` · `media evidence`.
Grep the file for
all 11; ANY missing marker means the script is
an incomplete variant — delete it and copy the block above again (or copy
the missing group from it). A script missing a marker will not catch the
missing artifact; a complete script is what the exit-0 gate verifies.

##### A4.4.2 Physical Gate (plugin enforcement — do not fight it) ★

The `vibeweaver-gate` plugin (`~/.config/opencode/plugins/vibeweaver-gate.js`)
enforces §A4.4.1 mechanically. After every `write`/`edit`, when the project
is vibeweaver-active (has `tests/verification_log.md`), it runs
`tests/assert_artifacts.py` (trying `--existing` / `--backend-only`
variants) and **throws a GATE-BLOCKED error into the tool result** while
verification evidence is missing or falsified. Bash is deliberately NOT
gated (screenshots / server start must be free to produce evidence), and
non-vibeweaver projects are silent.

- **Evidence failures BLOCK** (missing/fake `verification_log.md` entries,
  missing `acceptance.md` cap-stall line, cited media missing/empty —
  screenshots, `.webm` videos, `.wav` audio).
- **Structure failures WARN only** (`memory/`, design docs, README, git
  counts — appended as `[GATE-WARNING]`, not thrown), so the fix loop is
  never spammed.
- `session.idle` with a RED gate writes a `warn` entry to the opencode log
  (tripwire when the agent stops on a red gate).
- Escape hatch: `VIBEWEAVER_GATE=off` disables the plugin.
- If `tests/assert_artifacts.py` does not exist yet, the plugin runs an
  inline evidence check and the GATE-BLOCKED message points to §A4.4.1.

The GATE-BLOCKED message means **keep working — fix the evidence, then the
next write/edit re-checks automatically**. It is a completion gate, not an
execution stop.

#### A4.5 Media Capture Test Template
See [APPENDIX.md §A1](APPENDIX.md) — Playwright video + in-page audio +
screenshot capture. Always read `config.toml` before running.

#### A4.6 Systematic Debugging — Four Phases ★
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
  Write it down.
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
the loop; this rule escalates the **direction**.

#### A4.7 Backend-Only Task: API Doc-Driven Test Loop ★ NON-NEGOTIABLE

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
iteration to `tests/verification_log.md` (same format as A4.1 Step 4). Same
iteration cap=5 / stall=3× (COV-7) — on cap/stall record the failure in
memory and report to the user instead of looping forever. If a test failure
reveals the doc was wrong (not the code), update the doc, re-do the Step 3
consistency audit, then continue the loop.

**Completion evidence for A4.4:** chosen HTTP client, API doc path, test-case
file path, test log file, and convergence line `[Convergence] <task>: N iters
| X/Y test cases pass | stalls | cap-hits`.

**Ordering for NEW endpoints (test-first, links to §A4.8):** when §A4.7 covers
a **new** endpoint, execute Steps 2-4 (doc → consistency audit → test cases
written FROM the doc) **before implementing the endpoint**. The first test
run MUST fail (endpoint missing). Then implement to green — see §A4.8.

#### A4.7b Workflow Scenario Tests (Task-Level Backend Verification) ★

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
iteration to `tests/verification_log.md`. Same cap=5 / stall=3× (COV-7). Per-
step timeout 10s, whole scenario 120s, to prevent async issues from stalling
the loop.

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

#### A4.8 TDD for Logic-Bearing Code ★ NON-NEGOTIABLE

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

#### A4.9 Independent Code Review (Major Changes)

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
     (same finding ≥3 consecutive rounds → STOP retrying that direction; try a
     genuinely different direction or fresh-brain retry). At the cap,
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

### A5. Design Documents (Conditional)

Create only when the task scope warrants it. For new projects / new
features, at least FLOW_DESIGN.html is MANDATORY.

| Document | When to Create | When to Skip |
|----------|---------------|--------------|
| FLOW_DESIGN.html    | New project, new feature, major logic change | Bugfix, minor tweak, single-endpoint mod |
| PAGE_DESIGN.html    | New page, major UI redesign, any UI-bearing new project | Pure backend-only project (state `Page design skipped — backend-only project (no UI)`) |
| DATABASE_DESIGN.html| New tables, schema changes, any new project with data backend | Read-only query change, pure frontend |
| BACKEND_DESIGN.html | New project, new API surface, new endpoints | Pure-UI tweak with no API change |

#### A5.1 Design Approval Gate (New Features / New Projects ONLY)

**Scope discipline — read first:** this gate fires ONLY when the A5 table
requires design docs (or in C1 new projects). Bugfixes, minor tweaks, config
changes, and all other Modify-Existing work keep the DEFAULT autonomous flow
— no approval pause. Do not let this gate expand beyond that scope.

**Gate A — approach confirmation (BEFORE writing design docs):**
- ZERO (Step 0.2) already requires evaluating ≥2 approaches. In gated scope,
  **present them to the user**: recommended option + rationale + tradeoffs,
  rejected alternative + why. The user picks or confirms.
- If requirements are ambiguous, clarify **one question at a time** (prefer
  multiple-choice) — never batch-interrogate, never guess (extends §A1.5).
- If the request was explicit and one approach is clearly correct, state the
  choice briefly and proceed unless the user objects.

**Gate B — design confirmation (BEFORE implementation):**
1. Design docs complete → feasibility assessment passed (C1 Step 3) → run the
   **spec self-review** (fix inline, no re-review loop):
   - *Placeholder scan* — any "TBD"/"TODO"/vague requirement? Fix it.
   - *Internal consistency* — do the docs contradict each other? Does FLOW
     match PAGE and DATABASE?
   - *Scope check* — focused enough for one implementation pass, or must it be
     decomposed?
   - *Ambiguity check* — could any requirement be read two ways? Pick one, make
     it explicit.
2. Present a **concise design summary ONCE** (batched — architecture, key data
   flow, what will be built) and ask for confirmation. Do NOT do
   section-by-section approval — one question, one answer.
3. **Delegation is valid:** if the user says "you decide" / raises no
   objection, proceed autonomously and record the delegation in memory. This
   gate is a confirmation point, not a blocker — never nag, never re-ask.

### A6. Dependency Management
Every new dependency is permanent code you do not control.
- Before adding any package, ask: can the standard library solve this?
- If you add a dependency, document **why** in the commit message and (where
  relevant) in a brief code comment or design note.
- Do not silently add transitive dependencies or convenience wrappers.
- Prefer well-maintained, widely-used libraries with active community support.

### A7. Communication
Describe what you did and why — do not just drop code.
- Be precise about uncertainty: "I am not certain this endpoint supports
  streaming" is acceptable; "this should work" is not.
- Surface assumptions and tradeoffs explicitly.
- If the user corrects you, record it as a feedback memory and adjust.

**Receiving feedback / review comments — verify before implementing:**
- **READ** the complete feedback without reacting → **UNDERSTAND**
  (restate in your own words) → **VERIFY** against the codebase → then act.
- **Unclear items: clarify ALL of them BEFORE implementing anything.** Partial
  understanding = wrong implementation; items may be related.
- **No performative agreement.** Never respond with "You're absolutely
  right!" / "Great point!" / "Thanks for catching that!" — state the fix or
  just fix it. Actions show you heard; gratitude expressions are forbidden
  filler.
- **Push back with technical reasoning** when the suggestion is wrong for this
  codebase: breaks existing functionality, violates YAGNI (unused feature —
  grep for actual callers first), ignores existing constraints, or conflicts
  with user's prior decisions. Technical correctness over social comfort. If
  architectural, involve the user.
- **Implement multi-item feedback one at a time, testing each** — blocking
  issues first, then simple fixes, then complex ones. Never batch-implement
  untested.
- If you pushed back and were wrong: state the correction factually ("I
  checked X — it does Y. Fixing.") and move on. No long apologies.

### A8. Common Failure Modes — Stop and Reassess
Watch for these predictable mistakes. If you notice yourself doing any of
them, STOP and reassess before continuing.

| Pattern | Warning sign | Correct response |
|---------|--------------|------------------|
| **Kitchen Sink**       | Changing far more files than the task requires            | Roll back unrelated changes; touch only what the request demands |
| **Wrong Abstraction** | Copy-pasting similar code repeatedly; speculative abstraction for single-use code | Keep it concrete; abstract only after the third repetition |
| **Optimistic Path**    | Only handling the happy path; ignoring bad input, network failure, missing data | Add explicit error handling and test the failure cases |
| **Runaway Refactor**   | One change cascades into touching many unrelated files   | Pause, restore baseline, make the smallest surgical change that works |

### A9. Git Version Control
- Every major change gets a descriptive commit
- Commit before starting work (baseline) and after each significant milestone
- Never commit secrets, `.venv/`, `node_modules/`, or build artifacts

### A10. Project Memory (memory/memdir)
Project's persistent knowledge across sessions — a **directory of Markdown
topic files** with a **MEMORY.md index**. Captures knowledge NOT derivable
from the current code or git history.

#### Directory Structure
```
project/
  memory/
    MEMORY.md                ← Index (loaded every session, capped 200 lines / 25KB)
    user_role_prefs.md       ← user-type topic
    feedback_testing.md      ← feedback-type topic
    project_q4_deadlines.md  ← project-type topic
    reference_grafana.md     ← reference-type topic
    fix_login_timeout.md     ← fix-tracking entry (one per bug/issue)
    ...
```
Replaces the old `MODIFY.html` / `MODIFY_COMPACT.html` single-file approach.

**The full operational rules for this subsystem are in
[MEMORY_RULES.md](MEMORY_RULES.md)** — §A7.1 through §A7.14 cover:
MEMORY.md index format/caps · topic-file frontmatter/bodies · memory types ·
what NOT to save · trust tiers (⛔ Forbidden / ✅ Verified / ⏳ Unverified /
❌ Failed) · loading order on every invocation · state-flow rules &
implicit-failure detection · pre-change guardrails · post-session writing
(A7.9, NON-NEGOTIABLE) · Final Memory Gate (A7.10, NON-NEGOTIABLE) ·
promotion to Verified + old-format migration · user-global + project-local
merge · consolidation rules · retrospective backtracking.
Templates live in [MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md).

**You still execute these binding obligations from SKILL.md (not deferred):**
- Load memory before any code change (A7 loading order) — see §3.2.
- Write memory topic files at session end and pass the Final Memory Gate
  before the completion table — see [MEMORY_RULES.md §A7.9 / §A7.10](MEMORY_RULES.md).
- Output the `[Memory Gate] Passed: …` line immediately before the
  completion table, AND state `memory_gate: pass` in the `[Verification
  Gate]` line itself (the in-line field is the enforcement channel
  re-review will check).
- ★ **Covenant Recall Check:** immediately before the `[Memory Gate]` line,
  re-read §1 OPERATING COVENANT once and confirm the memory obligations
  (A7.9 write / A7.10 gate) hold for this session.

---

## PART B — Stack-Specific Patterns (Apply Only When Stack Matches)

**Important:** Part B applies ONLY when the project's actual tech stack matches.
For an existing project using Vue instead of React, MySQL instead of
PostgreSQL — apply Part A principles and adapt to existing tools; never force
Part B stack choices onto an existing project.

### B1. Default New Project Stack: FastAPI + React + Vite + PostgreSQL
- **Backend:** Python + FastAPI · OAuth2 auth on all endpoints · frontend
  mounted at `/static` · History routing fallback → [APPENDIX.md §A3](APPENDIX.md).
- **Frontend:** React + Vite · responsive (desktop / tablet / mobile).
- **Directory Structure** and **Script Templates** → [APPENDIX.md §A5](APPENDIX.md),
  [APPENDIX.md §A6](APPENDIX.md).

### B2. Adapting to Other Stacks
When the project uses a different stack (Vue / MySQL / MongoDB / Go backend…):
- Apply ALL Part A core principles — universal.
- Adapt script templates to the project's build tooling.
- Adapt `[database]` config section to the actual database type.
- Always create and use `script/` directory scripts — universal rule.
- Do NOT change the project's tech stack. Match what's there.

---

## PART C — Workflows

### C1. New Project Workflow
```
0.   §2 ZERO: decompose + web research (find best solutions BEFORE designing)
0.5  A5.1 Design Gate A — present ≥2 researched approaches + recommendation (A5.1)
1.   git init + initial commit
2.   **MUST create design documents per §A5 — no skipping:** FLOW_DESIGN.html ·
     PAGE_DESIGN.html (UI-bearing project only — backend-only project explicitly
     skips PAGE with reason) · DATABASE_DESIGN.html (touches data only) ·
     BACKEND_DESIGN.html (touches API only)
3.   Design review & feasibility assessment (loop until pass)
4.   BACKEND_DESIGN.html
4.5  A5.1 Design Gate B — spec self-review, then ONE batched user confirmation
5.   config.toml (before implementation — code reads from it)
6.   Backend implementation
7.   Frontend implementation
8.   Scripts: project_build.sh / start.sh / stop.sh / restart.sh (linux + windows)
9.   Build: bash script/linux/project_build.sh
10.  Start: bash script/linux/start.sh
11.  Test: A4.1 Step 1 — acceptance criteria gate → write tests/acceptance.md
     (first line `> cap=5  stall=3×`); Playwright capture (video + audio +
     screenshots per the §A4.1 Step 0 probe mode) of ALL operations + API
     tests via §A4.7 backend loop; media graded per §A4.1 Step 3
12.  Act → Capture → Verify (mm-sensor) → Fix → Log loop until ALL criteria
     pass or cap=5/stall=3× stops you (COV-7); convergence summary + ★ 8-column
     completion table (A4.4) — no exceptions
13.  Acceptance checklist
14.  ★ Write session memories: create memory/MEMORY.md + topic files + index
     ([MEMORY_RULES.md §A7.9](MEMORY_RULES.md)); record design decisions, user
     preferences, unverified modifications. Pass Final Memory Gate (A7.10).
15.  README.html + requirements.txt + package.json + final commit
```

### C2. Modifying Existing Project ★

#### Step -1: §2 ZERO FIRST
**Execute §2 ZERO Decompose & Research BEFORE surveying any local files.**
Search exa MCP + Context7. Only after ZERO is complete, proceed to Step 0.

#### Step 0: Survey Before Acting
Read these files BEFORE making any changes (in order):
1. **memory/MEMORY.md** (index) per §3.2 (load top 3-5 relevant topic files;
   check ⛔ Forbidden · ❌ Failed · ✅ Verified · ⏳ Unverified · user feedback ·
   project context · verify references against current code).
2. **config.toml** (or equivalent) — actual hosts/ports/credentials.
3. **README.html** — project purpose and setup.
4. **script/** directory — existing build/start/stop scripts.
5. **Project directory tree** — tech stack and structure.

#### Step 1: Use Existing Scripts (COV-2)
Build → `bash script/linux/project_build.sh` · Start/Stop →
`bash script/linux/start.sh` / `stop.sh`. If scripts don't exist but are
needed, create them per §A2, then use them.

#### Step 2: Respect Existing Configuration
Never change config.toml hosts/ports/credentials unless the task explicitly
requires it. Example values in this skill (`8i9o0p-[=]`) are **examples
only**. Read from config, never hardcode in source.

#### Step 3: Match Existing Code Style
Indentation, naming, import conventions of the project. Don't change the
tech stack (e.g. don't introduce React into a Vue project). Don't refactor
unrelated code (see [CODING_PRINCIPLES.md](CODING_PRINCIPLES.md) Rule 3).

#### Step 4: Design Documents — Scoped
Only create FLOW/PAGE/DATABASE/BACKEND_DESIGN.html for significant new
features (§A5 table). Skip design docs for bugfixes / minor changes. When docs
ARE created, the §A5.1 Design Approval Gate applies (Gate A approach, Gate B
design). Everything else stays fully autonomous.

#### Step 5: Git — Commit Before and After + Verify Clean Baseline
```bash
git add -A && git commit -m "backup: before changes"   # baseline
# ... make changes ...
git add -A && git commit -m "feat: description of change"
```
**After the baseline commit, verify the baseline is GREEN before changing
anything.** Run the project's existing tests / build once (via `script/` where
applicable). A dirty baseline makes every later failure unattributable: you
won't know whether you broke it or it was already broken.
- **Every change-wave gets its own baseline** — a follow-up fix minutes after
  the previous task may NOT reuse that baseline (COV-9); the three lines and
  the log entry are per-change-wave, not per-session.
- Record the verdict as the first entry under the task heading in
  `tests/verification_log.md`: `- Baseline verified GREEN` (or
  `- COV-9 skipped — reason: …`) — assert_artifacts.py group 9 machine-checks
  this file, not the narration.
- Baseline green → proceed.
- Baseline has pre-existing failures → report to the user ("baseline already
  has N failures: …") and ask whether to proceed or fix first. Record
  pre-existing failures in `tests/verification_log.md` so they are not later
  mistaken for regressions you caused.

#### Step 6: Test Your Changes ★
- Write tests covering your modifications.
- Build + start via scripts (COV-2), then test.
- Acceptance criteria gate: write `tests/acceptance.md` (first line
  `> cap=5  stall=3×`; confirm with user if vague — A4.1 Step 1).
- **Backend-only change** → §A4.7: pick httpx/requests (installed first, else
  requests), update API doc, audit doc↔code consistency once, write test
  cases from the doc, then loop test → fix → test until all pass. **If the
  change has cross-endpoint behavior** → A4.7b workflow scenarios with REAL
  HTTP traces (`tests/workflows/*.trace.log`); service-level direct calls
  are not E2E (report `E2E depth` in the gate line).
- **UI / runtime-visible change** → Playwright capture of ALL operations +
  results — operation video + in-page audio + terminal screenshot per the
  §A4.1 Step 0 probe mode; grade via **mm-sensor** (`vision.py --detail high`)
  if available, else direct read (§A4.1 Step 0).
- Act → Capture → Verify → Fix → Log to `tests/verification_log.md` →
  Repeat until ALL acceptance criteria pass or cap=5/stall=3× stops you.
- ★ Convergence summary line + 8-column completion table (§A4.4) — final
  deliverable, no exceptions.

**Major change** (≥3 files / new feature / API-surface change) → dispatch the
A4.9 reviewer before the completion table (COV-8). Else state
`A4.9 not triggered — reason: <…>` in the [Verification Gate] line.

#### Step 7: Acceptance Checklist
List what was changed and confirm each change meets the requirement. Include
verification evidence (screenshot, log excerpt).

#### Step 8: Log to Project Memory (memory/)
At session end, before the completion table, you MUST (operational rules in
[MEMORY_RULES.md §A7.9](MEMORY_RULES.md)):
1. Review the conversation for new information worth persisting.
2. Write / update `.md` topic files in `memory/` (frontmatter + body per
   MEMORY_TEMPLATES.md).
3. Update `memory/MEMORY.md` index (≤200 lines / 25KB).
4. Fix tracking: write `memory/fix_<topic>.md` as ⏳ Unverified (never directly
   ✅ Verified). Mark ⏳ if tests passed, ❌ if tests failed.
5. Escalate to ⛔ if ≥3 failures preceded this fix.
6. Record feedback memories if user corrected / confirmed approach.
7. Record project memories for goals / deadlines / team context.
8. Check consolidation need (>15 topic files or index >150 lines / 20KB — see
   [MEMORY_RULES.md §A7.13](MEMORY_RULES.md)).
9. Pass Final Memory Gate (A7.10) and output the `[Memory Gate] Passed: …` line
   immediately before the completion table.

### C3. Large-Task Implementation Plan (Conditional)
**Trigger:** work touching ≥3 files, or multi-step inter-dependencies (new
feature / cross-module change). **Skip for:** single-file fixes and trivial
changes — decompose mentally and proceed.

Write the plan BEFORE implementing (`docs/PLAN.md` or appended to design docs),
assuming the executor has zero project context. Per task block:
- **Files:** Create / Modify (exact paths) / Test (exact path).
- **Interfaces:** *Consumes* — earlier-task outputs (exact signatures);
  *Produces* — what later tasks rely on (exact names, parameter/return types).
  This block is how multi-step work avoids interface drift.
- **Steps:** one action each (2-5 min), each with its verification command.
  Logic-bearing steps are test-first per §A4.8.

**No placeholders — these are plan FAILURES:** "TBD" / "implement later" ·
"add appropriate error handling" / "handle edge cases" · "write tests for the
above" without actual test code · "similar to Task N" (repeat the content —
steps may be read out of order) · references to types/functions defined nowhere
in the plan.

**Plan self-review (fix inline, no loop):**
1. **Coverage** — every requirement maps to a task.
2. **Placeholder scan** — see above.
3. **Type consistency** — names/signatures used in later tasks match earlier
   definitions exactly (`clearLayers()` in Task 3 but `clearFullLayers()` in
   Task 7 is a bug).

Template: [APPENDIX.md §A7](APPENDIX.md). The plan's verification commands
feed the §A4.1 / §A4.7 / §A4.8 loops.

---

## MANDATORY CHECKLIST — Verify Before Outputting

Before declaring any task complete, explicitly list and confirm:

- [ ] **§1 Operating Covenant** — all 10 covenants (COV-1 NO TEST NO DONE ·
      COV-2 SCRIPT-ONLY · COV-3 ZERO · COV-4 Playwright loop self-starting ·
      COV-5 verifier announced · COV-6 backend-only → A4.7 · COV-7 cap=5/stall=3×
      · COV-8 A4.9 reviewer · COV-9 Baseline-GREEN · COV-10 Design Gate) checked.
- [ ] `memory/MEMORY.md` read + top 3-5 relevant topic files loaded + file
      references verified (§3.2, A7.6) — ⛔ Forbidden checked, ✅ Verified
      scanned, ❌ Failed reviewed, ⏳ Unverified matched against current request
- [ ] User query decomposed and clarified
- [ ] §2 **ZERO: Decompose & Web Research executed FIRST (exa MCP + Context7)**
- [ ] Git repo committed after each major change
- [ ] (Modify Existing only) **COV-9 Baseline-GREEN before changes** —
      commit `backup: before changes` THEN run existing build/test/start
      once via `script/`; report pre-existing failures and log to
      `tests/verification_log.md`. **Per change-wave** (previous task's
      baseline does NOT count) and recorded as the first log entry:
      `- Baseline verified GREEN` (assert group 9 machine-checks the FILE).
      Pure-doc/config edits state-skip with `COV-9 skipped — documentation-only
      change`.
- [ ] **Scripts in `script/` used for build, start, stop, restart — NEVER raw
      `npm run build`, `vite`, `npm start`, `uvicorn`, etc. (COV-2)**
- [ ] **Tests actually EXECUTED with concrete evidence on disk (test log files,
      screenshots, `tests/verification_log.md` entries) — "build passed" /
      "looks correct" is NOT evidence (COV-1)**
- [ ] **Verification run FRESH on the exact tree being delivered — no commit
      landed after the last test run (A4.4 gate item 6)**
- [ ] **(Logic-bearing code) §A4.8 test-first followed** — failing test written
      BEFORE implementation, watched failing, RED output logged to
      `tests/verification_log.md`; regression tests completed the revert-and-fail
      cycle
- [ ] Configuration read from project config file — never hardcode
      credentials/hosts/ports
- [ ] (New feature/system only) **MUST create design documents per §A5**
      — `FLOW_DESIGN.html`, `PAGE_DESIGN.html` (UI-bearing only — backend-only
      project skips PAGE with explicit reason), `DATABASE_DESIGN.html` (if data),
      `BACKEND_DESIGN.html` (if API surface). Backend-only todo project still
      creates FLOW_DESIGN+DATABASE_DESIGN+BACKEND_DESIGN; PAGE_DESIGN skipped
      with `Page design skipped — backend-only project (no UI)`.
- [ ] (New feature/system only) Design feasibility assessment passed
- [ ] (New feature/system only) **COV-10 A5.1 Design Approval Gate passed** —
      narration includes `## Design Gate A` (≥2 approaches + recommendation)
      AND `## Design Gate B — Spec Self-Review` (Placeholder scan / Internal
      consistency / Scope check / Ambiguity check each pass/fail) + `Proceeding
      (delegation recorded)` or explicit confirmation request.
- [ ] (Large tasks ≥3 files only) C3 implementation plan written —
      Files/Interfaces/Steps per task, zero placeholders, type consistency
      self-reviewed
- [ ] (New project / new API surface only) BACKEND_DESIGN.html created
- [ ] Tests written, executed, all passed
- [ ] ★ **Verifier announced at task start with modality mode** — if
      mm-sensor is listed: `vision.py --probe` ran and mode announced
      (`mm-sensor [video+audio|video|image]`); else `direct read` fallback.
      If never announced, verification was skipped; go back (COV-5)
- [ ] ★ Acceptance criteria written to `tests/acceptance.md` (first line
      literal `> cap=5  stall=3×`) and confirmed with user if request was vague
- [ ] ★ **Playwright loop ENTERED AUTONOMOUSLY** (no user prompt waited for)
      for every runtime-affecting change — capture set per mode: operation
      video + in-page audio + terminal screenshot (`[video+audio]`), video +
      screenshot (`[video]`), screenshots only (`[image]` / direct read)
      (COV-4)
- [ ] ★ Every captured media file graded via **mm-sensor**
      (`vision.py --detail high`) if listed in `available_skills` —
      self-grading via Read tool is a VIOLATION while mm-sensor is loaded;
      A4.1 Step 3 runtime degradation applied — audio `skipped`
      (`model_no_audio_capability`) dropped, video falls back to
      frame-sampling
- [ ] ★ Captured evidence files actually exist on disk under `tests/`
      (per mode: `tests/*.webm`, `tests/*_audio.wav`, `tests/*.png`) and
      `tests/verification_log.md` has ≥1 iteration entry — if not, the loop
      was never run; go back and run it
- [ ] ★ Each iteration logged to `tests/verification_log.md`; loop repeated
      until ALL criteria pass OR cap=5 / stall=3× hit (COV-7)
- [ ] ★ Convergence summary line output before completion table:
      `[Convergence] <task>: N iters | X/Y pass | stalls | cap-hits` (A4.1 Step 5)
- [ ] ★ **(Backend-only tasks) A4.7 backend loop** — API doc updated, doc↔code
      consistency audited once, test cases written FROM the doc, the test → fix
      loop executed with httpx/requests until ALL cases pass; iterations logged
      to `tests/verification_log.md`; NEW endpoints followed test-first ordering
- [ ] ★ **(Backend cross-endpoint changes) E2E depth — real HTTP workflow
      trace** — `tests/workflows/*.trace.log` exists and >0 bytes (assert
      group 10), run against the server via `script/`; service-level direct
      calls are NOT E2E; `E2E depth: real-HTTP / workflow-trace / service-direct
      / unit-only` reported in the `[Verification Gate]` line (A4.7b)
- [ ] ★ **(Major changes) A4.9 independent code review dispatched** — reviewer
      verdict received, Critical/Important findings fixed + covering tests
      re-run, Minor findings deferred to memory; fix-round loop bounded (≤5
      rounds, stall 3×, cap adjudicated with rulings / escalate), zero findings
      silently discarded; every `verification_log.md` claim personally confirmed
      (A4.4 log-discipline). Trigger includes **behavior-semantic changes**
      (one-file logic changes included); "files changed" counts EVERY path in
      `git diff --stat`.
      **OR** for non-trigger changes: `[Verification Gate]` line states
      `Code review: N/A` with a reason backed by `git diff --stat` (actual
      file count + kind) — not "≤1 file logic" from memory (COV-8).
- [ ] ★ Completion table output with ALL 8 columns filled: Problem, Research
      Sources, Chosen Approach & Why, Files Changed, What Changed, Verification
      Evidence, Commit (A4.4)
- [ ] ★ `python3 tests/assert_artifacts.py` executed and exited 0 before the
      `[Verification Gate]` line; the literal field `assert_artifacts.py:
      pass=N/fail=0` is present (A4.4.1)
- [ ] ★ Covenant Recall Checkpoints performed (§A4.1 Step 4 · §A4.4 · §A10 —
      §1 re-read) and the LITERAL line `[Covenant Recall] checked: all 10
      covenants hold for this completion` output before the [Verification
      Gate] audit line, with `covenant_recall: pass` in the [Verification
      Gate] line — no covenant silently dropped mid-session
- [ ] Memory topic file written to `memory/` + `MEMORY.md` index updated +
      Final Memory Gate (A7.10) passed (`[Memory Gate] Passed: …` line output
      AND `memory_gate: pass` field in the [Verification Gate] line)
      ([MEMORY_RULES.md §A7.9 / §A7.10](MEMORY_RULES.md))
- [ ] Acceptance checklist completed and passed
- [ ] (New project only) README.html / dependencies files updated / final git
      commit

**If any item is unchecked, return to fix it. Do NOT output "done".**

---

## Reference Files (companion files loaded on demand)

- [CODING_PRINCIPLES.md](CODING_PRINCIPLES.md) — 4 iron rules for all code
- [ENGINEERING_STD.md](ENGINEERING_STD.md) — Detailed engineering standards
- [REFERENCE.md](REFERENCE.md) — Full workflow reference
- [APPENDIX.md](APPENDIX.md) — Executable code templates
- [MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md) — Memory topic file + index templates
- [MEMORY_RULES.md](MEMORY_RULES.md) — Full §A7.1–§A7.14 operational rules for the
  project memory subsystem (loaded by §3.2 / §A10 references)

Base directory for this skill: same directory as this file.