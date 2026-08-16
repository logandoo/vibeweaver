---
name: vibeweaver-mini
description: |
  ★ ALWAYS LOAD THIS SKILL BEFORE WRITING ANY CODE. MANDATORY for every coding task:
  implementing a feature, fixing a bug, writing a function, debugging, writing/running tests,
  building a frontend, starting a service, scaffolding a project, or modifying any codebase.
  If the task involves writing or changing code, load this skill FIRST and follow its workflow.
  Without it you will skip mandatory verification and the task is NOT complete.
---

# Vibeweaver Mini — Core Rules

Follow this workflow for EVERY coding task:

## 0. Decompose & Research (before code)
- Break the request into clear sub-tasks.
- If internet is available, search for existing solutions/patterns BEFORE writing code. State what you found and which approach you chose.

## 1. Understand the project first
- Existing project: read the config, scripts, README, and git status BEFORE changing anything. Match existing patterns and style.

## 2. TDD — Test-First for ALL Logic ★ (backend AND frontend)

The core principle: **if you didn't watch the test fail, you don't know if it tests the right thing.** A test written after passing code proves nothing — it may test the wrong thing or miss the edge case.

| Layer | Rule |
|---|---|
| **Logic-bearing code** — utils, state/business logic, data transforms, validation, API endpoints, frontend business logic | **Test-first (this section)** |
| **UI rendering** — pages, components, layout | Test-after via the screenshot loop (§3); component behavior that is specifiable is test-first |
| **Exempt** — pure config files, markup/copy, docs | No test required |

The cycle (RED → GREEN):
1. **RED** — write ONE failing test for the next small behavior. One behavior per test.
2. **Verify RED** — run it and WATCH it fail (the failure message must be about the missing feature, not a typo). Paste the failing output into `tests/verification_log.md` — this is your evidence.
3. **GREEN** — write the minimal code to make it pass. Nothing beyond what the test demands.
4. **Verify GREEN** — run it and watch it pass; full suite still passes. Commit, then next test.

If you wrote code before the test: **delete it and start over from the test.** Keeping it as "reference" is test-after in disguise.

**Regression fixes:** test → run (passes with fix) → revert the fix → run (MUST fail) → restore the fix. A regression test never watched failing on the buggy code is unproven.

Red flags — STOP and restart test-first:
- Test passes on first run and you can't name what production change would break it
- "Too simple to test" / "I'll test after" / "I already verified manually"

## 3. Frontend testing standard ★ (UI projects)

UI work needs THREE layers — do not skip any:

**Layer 1 — Logic tests:** extract business logic (filtering, transforms, state updates) into pure functions/modules; test them per §2. Logic in JSX/effects that can't be tested is a design smell.

**Layer 2 — Component tests:** render components with the project's test runner (Vitest/Jest + Testing Library) and assert user interaction updates the DOM. Specifiable behaviors are test-first; visual layout is verified in Layer 3.

**Layer 3 — E2E + screenshots (the running app must be SEEN):**
1. **BEFORE coding**, write pass/fail acceptance criteria to `tests/acceptance.md` — one numbered line per criterion, each a yes/no question a verifier can answer (e.g. "4. Completed todos are greyed out"). Vague request → confirm the criteria with the user first.
2. Implement, then launch via `script/` (§5) and drive the running app with Playwright (Python): screenshot every key state (initial, after add, after toggle, after filter, error states) to `tests/*.png`.
3. **Verify every screenshot against the criteria.** If `mm-sensor` is in `available_skills`, announce `Verifier: mm-sensor` at task start and grade every screenshot via `python3 {SKILL_DIR}/vision.py --detail high <png>` — never self-read screenshots while it is installed. If it is NOT installed, announce `Verifier: direct read` and inspect the image directly.
4. Any criterion failing → fix the code → re-screenshot → re-verify. Log each iteration to `tests/verification_log.md`.

"Tests passed but I never looked at the page" is NOT done for UI work.

## 4. NO TEST, NO DONE ★ (hard gate)

- A task is complete ONLY when tests actually ran and produced evidence on disk (log files, screenshots, or test output). "It compiles" / "looks correct" is NOT evidence.
- Backend change: call the API (httpx/requests) and verify the responses; save the output to a log file.
- Multi-endpoint backend task: besides per-endpoint checks, write and run ONE workflow test for the task's main flow — sequence the endpoints with state-transition assertions (register → login → create → verify-persisted), starting from a clean state.

## 5. Script-only lifecycle

- If the project has `script/` (build/start/stop): use those scripts. Never run raw `npm run build`, `vite`, `npm start`, `uvicorn` directly. Create `script/` if missing and needed.

## 6. Fix loop

- On failure: read the FULL error, diagnose the root cause, make ONE change, re-test.
- Max 5 iterations per problem. If the same failure repeats 3 times, change approach — do not keep retrying the same fix.

## 7. Finish & report

- `tests/acceptance.md` (your pass/fail criteria) and `tests/verification_log.md` (each iteration: result + what changed) must exist.
- Commit with a descriptive message.
- Report: what you changed, how you verified it (with evidence — test log excerpts / screenshot filenames), and the final test results.
