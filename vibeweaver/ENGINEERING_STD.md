# Engineering Standards — Supplementary Details

> This file supplements [SKILL.md](SKILL.md). Core rules are in SKILL.md; this file adds detail on specific engineering practices. When in conflict, SKILL.md prevails.

---

## Special Rules for Modifying Existing Projects

When modifying an existing project (not building from scratch), observe these rules in addition to the general requirements below:

1. **Survey Before Acting**: Before making any changes, read the project's `config.toml` (or equivalent), `README.html`, `script/` directory, and project directory structure. Understand the tech stack and existing configuration.
2. **Use Existing Scripts**: If the project has a `script/` directory with build/start/stop scripts, **you must use them**. Do not bypass scripts to run raw commands.
3. **Do Not Overwrite Existing Config**: Database usernames, passwords, ports, etc. in `config.toml` are the project's existing settings — **do not arbitrarily modify or overwrite them**. Example passwords in this skill are examples only.
4. **Match Existing Tech Stack**: Use whatever tech stack the project uses. Do not forcibly introduce React into a Vue project, or switch MySQL to PostgreSQL.
5. **Design Documents On Demand**: Bug fixes and minor changes do not require generating FLOW_DESIGN.html / PAGE_DESIGN.html / DATABASE_DESIGN.html. Only generate these for new features, new pages, or database schema changes. See [SKILL.md §A5](SKILL.md#a5-design-documents-conditional) for the full decision table.
6. **No Unrelated Refactoring**: Follow CODING_PRINCIPLES.md Rule 3 "Surgical Changes". Only modify code related to the task — do not refactor things you notice along the way.
7. **Commit Before and After**: Make a git commit as a baseline before starting changes. Commit again after changes are complete.

---

## General Requirements (All Projects, Regardless of Tech Stack)

1. **Understand Requirements**: Decompose the user's query; ask clarifying questions for ambiguous parts.
2. **Git Version Control**: Initialize a git repository for the project (if none exists). Make a descriptive commit for every major change.
3. **Script-Driven Lifecycle**: See [SKILL.md §A2](SKILL.md#a2-script-driven-lifecycle--non-negotiable). Use scripts from `script/` directory; create them if missing.
4. **Configuration Management**: See [SKILL.md §A3](SKILL.md#a3-configuration-management). All config in `config.toml`, never hardcode credentials/hosts/ports.
5. **Design Documents (On Demand)**:
   - **Generate when**: new feature flows, new pages, new/modified database tables, new API surfaces
   - **Skip when**: bug fixes, copy changes, style tweaks, single endpoint adjustments
   - Documents produced: FLOW_DESIGN.html (flowcharts/sequence diagrams via mermaid.js embedded in HTML), PAGE_DESIGN.html (page elements / interaction logic), DATABASE_DESIGN.html (table structures / fields / relationships), BACKEND_DESIGN.html (backend endpoint design)
6. **Feasibility Assessment**: After completing design documents, carefully review all for errors and assess feasibility. If the assessment fails, iterate: assess → revise → reassess. Then the **A5.1 Design Approval Gate** (new features / new projects only): spec self-review + ONE consolidated user confirmation before implementation. Bugfixes and minor changes are exempt — they stay autonomous.
7. **Testing Requirements**:
   - All tasks should be tested.
   - **Logic-bearing code is test-first** (SKILL.md §A4.8): write the failing test, WATCH it fail, minimal implementation, watch it pass. UI/E2E verification remains the Playwright screenshot loop (test-after is the correct form there).
   - Frontend: Playwright (Python-based) for screenshot testing. Backend: httpx. WebSocket: Python websockets.
   - All test results must retain log files. Backend tests must include endpoint name, method, input, and output.
   - **Mock/standardized test results are forbidden**. Verification must use actual system screenshots, log file inspection, or database data inspection.
   - Any result not matching expectations is considered a test failure.
   - After fixes: screenshot → verify → fix → repeat until passing.
   - When testing, prefer using the project's `.venv` virtual environment.
8. **Acceptance Checklist**: After completing all work, confirm all requirements are met and produce an acceptance checklist. The checklist must include: original requirements, completion status, final screenshots, screenshot interpretation. Re-verify against the checklist; return to work if anything is not passing.

---

## New Project Tech Stack Standards

The following standards apply when building a project from scratch. When modifying an existing project, follow that project's existing tech stack instead.

### Default Tech Stack: Python + FastAPI + React + Vite + PostgreSQL

**Backend Requirements:**
1. Use Python + FastAPI for backend development.
2. Before coding, design all backend endpoints based on FLOW_DESIGN.html and DATABASE_DESIGN.html — including endpoint name, HTTP method, input, output, request example, and response example. Save this design to BACKEND_DESIGN.html.
3. Pay attention to module separation.
4. Protect all endpoints with OAuth2.

**Frontend Requirements:**
1. Build the frontend with React + Vite based on PAGE_DESIGN.html.
2. All pages must follow responsive design, supporting desktop, tablet, and mobile.

**Publishing Requirements:**
1. Mount the frontend as static files in the backend. The FastAPI mount path is `/static`.
2. Use the project's `.venv` as the virtual environment. Use `fastapi` CLI for running the server.
3. Generate start, stop, restart, and project_build scripts in the `script/` directory. `project_build` must automatically mount the built frontend into the backend. Provide separate scripts for Linux/macOS (`script/linux/`) and Windows (`script/windows/`). See [APPENDIX.md §A6](APPENDIX.md#a6-script-templates-default-fastapi--react--vite--adapt-for-other-stacks) for templates.
4. If the frontend uses History routing, configure a fallback route in FastAPI. See [APPENDIX.md §A3](APPENDIX.md#a3-fastapi-fallback-route--history-routing-fastapi-only).

**Configuration File Requirements:**
1. All configuration should be stored in `config.toml`. See [APPENDIX.md §A5](APPENDIX.md#a5-configtoml-full-template-example--adapt-to-your-project) for a template.
2. Unless otherwise specified, use PostgreSQL.

**Closing Work (New Projects Only):**
1. Write README.html (project overview, system dependencies, Python version, npm version, quick start, deployment steps).
2. Generate Python dependencies: `requirements.txt`.
3. Generate/update npm dependency files (`package.json`).

### Adapting to Other Stacks

When the project uses other tech stacks (e.g., Vue, MySQL, MongoDB, Go backend):
- Follow the **General Requirements** above (script-driven, config management, testing, acceptance, etc.)
- Follow the project's actual tech stack — do not forcibly migrate
- Adapt script templates to the project's actual build tools
- Adapt the `[database]` section in `config.toml` to the actual database type

---

## §A6. Dependency Management

Every new dependency is permanent code you do not control.
- Before adding any package, ask: can the standard library solve it?
- If you add a dependency, document **why** in the commit message and (where
  relevant) in a brief code comment or design note.
- Do not silently add transitive dependencies or convenience wrappers.
- Prefer well-maintained, widely-used libraries with active community support.

## §A7. Communication

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

## §A8. Common Failure Modes — Stop and Reassess

Watch for these predictable mistakes. If you notice yourself doing any of
them, STOP and reassess before continuing.

| Pattern | Warning sign | Correct response |
|---------|--------------|------------------|
| **Kitchen Sink**       | Changing far more files than the task requires            | Roll back unrelated changes; touch only what the request demands |
| **Wrong Abstraction** | Copy-pasting similar code repeatedly; speculative abstraction for single-use code | Keep it concrete; abstract only after the third repetition |
| **Optimistic Path**    | Only handling the happy path; ignoring bad input, network failure, missing data | Add explicit error handling and test the failure cases |
| **Runaway Refactor**   | One change cascades into touching many unrelated files   | Pause, restore baseline, make the smallest surgical change that works |

## §A9. Git Version Control

- Every major change gets a descriptive commit
- Commit before starting work (baseline) and after each significant milestone
- Never commit secrets, `.venv/`, `node_modules/`, or build artifacts
- Production deploys are human-confirmed: the agent prepares (build,
  changelog, rollback path); the user authorizes the production action —
  no autonomous deploy to production targets
