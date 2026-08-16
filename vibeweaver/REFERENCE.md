> This file is the detailed reference for [SKILL.md](SKILL.md). Load when context permits; core rules are in SKILL.md.

# Vibeweaver — Detailed Reference

---

## Project Mode Decision Tree

```
Is there existing code in the project directory?
├── YES → Modify Existing Project workflow (below)
└── NO  → New Project workflow (below)
```

---

## Modify Existing Project Workflow ★

### Step M0: Survey the Project
Before making ANY changes, read:
1. `memory/MEMORY.md` (project memory index) — search `memory/*.md` for keywords from the request, then load top 3-5 relevant topic files. Check ⛔ Forbidden → ❌ Failed → ✅ Verified → ⏳ Unverified. Verify any file/line references against current code. If current request overlaps an ⏳ fix entry, mark it ❌ before proceeding.
2. `config.toml` (or equivalent config file) — note hosts, ports, database type, credentials
3. `README.html` — understand project purpose, dependencies, setup
4. `script/` directory — find existing build/start/stop scripts
5. Project tree — understand tech stack (backend language, frontend framework, database)

### Step M1: Git Baseline + Verify Clean Baseline
```bash
git status
git add -A && git commit -m "backup: before changes"
```
Then run the existing tests/build once. **Per change-wave** (the previous task's baseline in the same session does NOT count — every change-wave gets its own run), then record the verdict as the first log entry: `- Baseline verified GREEN` (or `- COV-9 skipped — reason: …`) — assert_artifacts.py group 9 machine-checks this FILE. Baseline green → proceed. Baseline already failing → report the pre-existing failures to the user and ask whether to proceed; record them in `tests/verification_log.md` so they aren't mistaken for regressions later. See [SKILL.md C2 Step 5](SKILL.md#step-5-git--commit-before-and-after--verify-clean-baseline).

### Step M2: Determine Design Document Needs

| Change Type | Documents Needed |
|-------------|-----------------|
| Bug fix | None |
| Style / copy change | None |
| Single endpoint CRUD change | None |
| New feature / flow | FLOW_DESIGN.html |
| New page / major UI | PAGE_DESIGN.html |
| New table / schema change | DATABASE_DESIGN.html |
| New API surface | BACKEND_DESIGN.html |

### Step M3: Use Existing Scripts
- Build: `bash script/linux/project_build.sh` (or `.bat`)
- Start: `bash script/linux/start.sh`
- Stop: `bash script/linux/stop.sh`
- Restart: `bash script/linux/restart.sh`

**Never bypass scripts with raw `npm run build` or `fastapi run`.**

### Step M4: Implement Changes
- Match existing code style (indentation, naming, imports)
- Read config from config.toml — never hardcode
- Keep existing credentials — don't change them
- Don't introduce new tech stack components

### Step M5: Test
```bash
bash script/linux/project_build.sh && bash script/linux/start.sh
python tests/screenshot_test.py
python tests/api_test.py
```

### Step M6: Verify
- Screenshots show correct pages
- Log files contain expected output
- Database queries return expected results (if applicable)

### Step M7: Acceptance & Git
- Acceptance checklist
- `git add -A && git commit -m "feat: description"`

### Step M8: Log Modification to Project Memory
- Create or update a fix topic file in `memory/` with `status: ⏳` if tests passed, `status: ❌` if tests failed (never directly to ✅)
- Update `memory/MEMORY.md` index with a pointer line for the new entry
- If ≥3 failures preceded this fix, add the failed methods to a ⛔ Forbidden topic file
- Record feedback memories if user corrected or confirmed approach during the session
- Record project memories if you learned about goals, deadlines, or team context
- Full format and state flow rules: [MEMORY_RULES.md §A7.1–§A7.14](MEMORY_RULES.md)

---

## New Project Workflow (Step 0 ~ Step 11)

### Step 0: Understand the Requirement
Decompose user query, ask clarifying questions for ambiguities.
**Also: Create `memory/MEMORY.md` index** (see [MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md) for template).

### Step 1: Initialize Git Repository
```bash
git init
git add .
git commit -m "Initial project setup"
```

### Step 2: Generate Design Documents
- **FLOW_DESIGN.html** — Mermaid flowcharts & sequence diagrams
- **PAGE_DESIGN.html** — Page elements, UI logic, form validation, modals
- **DATABASE_DESIGN.html** — Table structures, fields, types, FK constraints

### Step 3: Design Review & Feasibility Check
1. Read all three documents, find errors/inconsistencies
2. Feasibility assessment
3. If fail, enter **Review -> Fix -> Review** loop until pass

### Step 4: Backend API Design (BACKEND_DESIGN.html)
Based on FLOW_DESIGN.html and DATABASE_DESIGN.html:
- Endpoint names, HTTP methods, inputs, outputs
- Request/response examples for each endpoint

### Step 5: Configuration (config.toml)
All configuration must be stored in `config.toml`. See [SKILL.md A3](SKILL.md#a3-configuration-management) for required sections.

### Step 6: Implementation

#### Backend — Python + FastAPI (default)
```
project/
  backend/
    app/
      main.py              # FastAPI application entry
      config.py            # Configuration loader (TOML)
      auth/                # OAuth2 authentication module
      models/              # SQLAlchemy / database models
      schemas/             # Pydantic request/response schemas
      routers/             # API route modules (feature-first)
      services/            # Business logic layer
      repositories/        # Data access layer
    migrations/            # Alembic database migrations
    tests/                 # Backend tests
```

#### Frontend — React + Vite (default)
```
project/
  frontend/
    src/
      components/          # Reusable UI components
      pages/               # Page components
      hooks/               # Custom React hooks
      services/            # API client layer
      styles/              # Global styles / theme
    public/
    vite.config.ts
```

### Step 7: Deployment Configuration

#### Frontend Mount
- Frontend is served as static files mounted on the FastAPI backend.
- Mount path: `/static`
- If frontend uses **History routing**, configure a **fallback route** in FastAPI to serve `index.html`.

See [APPENDIX.md §A3](APPENDIX.md#a3-fastapi-fallback-route-for-history-routing) for code.

#### Virtual Environment
- Use the project directory's `.venv` as the virtual environment.
- Use `fastapi` CLI for running the server.

#### Scripts
Generate the following scripts in the `script/` directory, with separate versions for Windows and Linux/macOS:

```
script/
  linux/
    start.sh              # Start the application
    stop.sh               # Stop the application
    restart.sh            # Restart the application
    project_build.sh      # Build frontend and mount to backend
  windows/
    start.bat             # Start the application
    stop.bat              # Stop the application
    restart.bat           # Restart the application
    project_build.bat     # Build frontend and mount to backend
```

- `project_build` must: build the frontend, then automatically mount the output to the backend's static directory.
- Script templates in [APPENDIX.md §A6](APPENDIX.md#a6-script-templates).

### Step 8: Testing

#### Test Requirements
1. **ALL tasks must be tested.**
2. Frontend testing: use **Python-based Playwright**.
3. Backend API testing: use **httpx**.
4. WebSocket testing: use Python **websockets** library.
5. All test results must have **log files**.
6. Backend test logs must include: endpoint name, method, input, output.

See [APPENDIX.md](APPENDIX.md) for executable test code templates.

#### Test Verification
- **DO NOT rely on standardized/mocked test results.**
- Verification methods must include one or more of:
  - Taking screenshots of the running system
  - Checking log files
  - Querying the database directly
- Any result that doesn't match expectations is considered a **test failure**.

#### Fix-Verify Loop
1. If tests fail, record the failures and fix them.
2. After fixing, take screenshots to verify.
3. If verification fails, continue fixing and re-verifying.
4. Repeat until all tests pass.

### Step 9: Acceptance Checklist
After all work is complete, perform a final review:
1. Confirm ALL requirements have been met.
2. Create an acceptance checklist containing:
   - The original requirement
   - Completion status
   - Verification screenshot (after final verification)
   - Your interpretation of the screenshot
   - Your assessment of whether the screenshot meets the requirement
3. Based on the acceptance checklist, confirm all work is complete.
4. If any item is not met, **return to fix it** and repeat until the checklist passes.

### Step 10: Write Session Memories
Write session memories to the `memory/` directory (see [MEMORY_RULES.md §A7.9 (Post-Session Memory Writing)](MEMORY_RULES.md)). Create `memory/MEMORY.md` index + topic files. This establishes the baseline for future modification tracking.

### Step 11: Project Wrap-Up
1. **README.html** — Include:
   - Project introduction
   - System dependencies
   - Python version
   - Node.js / npm version
   - Quick start guide
   - Deployment steps
2. **requirements.txt** — Generate Python dependencies.
3. **package.json** — Ensure npm dependencies are properly declared.
4. **Final git commit** — include memory/ directory and all project files.

---

## Quick Reference Checklists

### Universal Checklist (All Projects)
- [ ] memory/MEMORY.md index read — ⛔ Forbidden checked, ❌ Failed reviewed, ✅ Verified scanned, top 3-5 relevant topic files loaded, ⏳ matched against current request, file references verified
- [ ] User query decomposed and clarified
- [ ] Git repository committed after each major change
- [ ] Scripts in `script/` used for build, start, stop, restart
- [ ] Configuration read from config file (never hardcoded, never overwritten)
- [ ] Tests written and passing (Playwright + httpx); logic-bearing code test-first with RED evidence logged (SKILL.md §A4.8)
- [ ] Test results verified (screenshots + logs + database), run FRESH on the final tree
- [ ] (Major changes) Independent code review dispatched; Critical/Important fixed, Minor deferred (SKILL.md §A4.9). Behavior-semantic changes trigger review even in one file; `Code review: N/A` reasons must cite `git diff --stat`, not memory. Cross-endpoint backend changes: real-HTTP workflow trace on disk (`tests/workflows/*.trace.log`).
- [ ] ⏳ Unverified fix topic file written (status: ⏳ or ❌; never directly to ✅) + MEMORY.md index updated
- [ ] Acceptance checklist completed and passed

### New Project Only Checklist
- [ ] FLOW_DESIGN.html created and reviewed
- [ ] PAGE_DESIGN.html created and reviewed
- [ ] DATABASE_DESIGN.html created and reviewed
- [ ] Design feasibility assessment passed
- [ ] BACKEND_DESIGN.html created
- [ ] Backend implemented (Python + FastAPI + OAuth2)
- [ ] Frontend implemented (React + Vite + Responsive)
- [ ] config.toml configured
- [ ] Deployment scripts created (start/stop/restart/build)
- [ ] Frontend mounted to backend /static
- [ ] Fallback route configured (if History routing)
- [ ] README.html written
- [ ] requirements.txt generated
- [ ] npm dependencies declared
- [ ] Final git commit made

### Modify Existing Project Checklist
- [ ] memory/MEMORY.md index read + top 3-5 relevant topic files loaded — ⛔ Forbidden checked, ❌ Failed reviewed, ✅ Verified scanned for target files, ⏳ matched against request, file references verified
- [ ] Project surveyed (config, scripts, structure read)
- [ ] Git baseline committed before changes + baseline tests/build verified GREEN (pre-existing failures reported, not silently inherited)
- [ ] Existing scripts used for build/start/stop
- [ ] Existing config values preserved (credentials unchanged)
- [ ] Design docs created only if needed (new feature/page/schema/API surface)
- [ ] Changes match existing code style
- [ ] No unrelated refactoring
- [ ] Tests verify changes via screenshots/logs/database
- [ ] Acceptance checklist completed
- [ ] Final git commit with descriptive message

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|------------|
| 1 | Start coding without surveying the project | Read config, scripts, structure first |
| 2 | Bypass scripts with raw npm/fastapi commands | Use `script/linux/project_build.sh` etc. |
| 3 | Overwrite config.toml with example values | Read and preserve existing configuration |
| 4 | Force a tech stack change on existing project | Match the project's actual stack |
| 5 | Generate design docs for a minor bugfix | Only create docs for new features/pages/schemas |
| 6 | Write speculative features | Only implement what was requested |
| 7 | Hardcode configuration values | Store all config in config.toml |
| 8 | Skip testing | Test every endpoint, every page |
| 9 | Rely on mocked/standardized test results | Verify with screenshots, logs, or database queries |
| 10 | Leave failing tests | Fix-Verify loop until all pass |
| 11 | Skip acceptance checklist | Create and verify the full checklist |
| 12 | Commit without clear messages | Every significant change gets a descriptive commit |
| 13 | "Improve" unrelated code | Touch only what the task requires |
| 14 | Build abstractions for single-use code | Keep it simple, refactor when needed |
| 15 | Skip loading project memory | Read memory/MEMORY.md index, load top 3-5 relevant topic files before every change |
| 16 | Skip writing project memory | Write memory topic files + update MEMORY.md index after every session |
| 17 | Let memory/ grow unbounded | Consolidate when >15 topic files or MEMORY.md >150 lines or 20KB (see MEMORY_RULES.md §A7.13) |
| 18 | Reintroduce previously fixed bugs | Check ⛔ Forbidden and ✅ Verified entries for target files; never retry a failed approach |
| 19 | Write directly to ✅ Verified fix status | All fix entries start as ⏳; only promote after user confirms |
| 20 | Retry failed approaches silently | If ⏳ entry matches current request, mark ❌ and change direction |
