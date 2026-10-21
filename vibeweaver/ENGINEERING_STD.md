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
3. Generate start, stop, restart, and project_build scripts in the `script/` directory. `project_build` must automatically mount the built frontend into the backend. Provide separate scripts for Linux/macOS (`script/linux/`) and Windows (`script/windows/`). See [APPENDIX.md §A2](APPENDIX.md) for templates.
4. If the frontend uses History routing, configure a fallback route in FastAPI. See [APPENDIX.md §A4.7.2](APPENDIX.md).

**Configuration File Requirements:**
1. All configuration should be stored in `config.toml`. See [APPENDIX.md §A3](APPENDIX.md) for a template.
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

## §A8. Communication

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

## §A9. Common Failure Modes — Stop and Reassess

Watch for these predictable mistakes. If you notice yourself doing any of
them, STOP and reassess before continuing.

| Pattern | Warning sign | Correct response |
|---------|--------------|------------------|
| **Kitchen Sink**       | Changing far more files than the task requires            | Roll back unrelated changes; touch only what the request demands |
| **Wrong Abstraction** | Copy-pasting similar code repeatedly; speculative abstraction for single-use code | Keep it concrete; abstract only after the third repetition |
| **Optimistic Path**    | Only handling the happy path; ignoring bad input, network failure, missing data | Add explicit error handling and test the failure cases |
| **Runaway Refactor**   | One change cascades into touching many unrelated files   | Pause, restore baseline, make the smallest surgical change that works |

## §A10. Git Version Control

- Every major change gets a descriptive commit
- Commit before starting work (baseline) and after each significant milestone
- Never commit secrets, `.venv/`, `node_modules/`, or build artifacts
- Production deploys are human-confirmed: the agent prepares (build,
  changelog, rollback path); the user authorizes the production action —
  no autonomous deploy to production targets

### §A10.1 Repository hygiene / VCS budget (COV-9 preflight · assert group 21)

**Why this exists (2026-10-17/18 incident).** An old `git add -A` backup
commit swept a pnpm store, Playwright browser cache, SQL dumps and a zip into
history (~1.3 GiB). `.gitignore` was added afterwards and `git rm --cached`
untracked the files, but the `.git` pack stayed **1.9 GiB / 85,302 objects**;
`git log --all -- .pnpm-store` still reached ~45k paths. The gate then walked
and scanned that tree on every write until it was disabled. **Untrack is not
history cleanup; `.gitignore` is prevention, not a cure.**

Run the preflight BEFORE the baseline commit (C2 Step 5) and before installing
dependencies (C1 Step 1). `assert_artifacts.py` group 21 is the machine check;
it runs in every class/profile and cannot be skipped.

| Check | Warn | Hard fail |
|---|---:|---:|
| `.gitignore` present | — | missing |
| tracked dependency/cache path (`node_modules`, `.pnpm-store`, `.venv`, `site-packages`, `__pycache__`, `.next`, `.nuxt`, `coverage`, Playwright caches) | — | any |
| `.gitignore` covers the detected stack (`node_modules/`; `.pnpm-store/` when pnpm; `.venv/`/`venv/` when Python) | — | missing pattern when the manifest exists |
| untracked, non-ignored files | > 500 | > 2,000 (fail; partial scans refused) |
| `.git` size (`git count-objects -v`) | > 200 MiB | > 1 GiB |
| largest reachable blob (`--final`, `rev-list --all`) | > 10 MiB | > 40 MiB |
| change-wave paths | — | > 2,000 (split the wave) |

**Remediation (index only — safe):**

```bash
# 1) write/extend .gitignore first (APPENDIX §A12), then:
git rm -r --cached --ignore-unmatch node_modules .pnpm-store .venv dist build
git add .gitignore && git commit -m "chore: untrack dependency/build caches"
# 2) verify the index is clean:
git ls-files | rg '(^|/)(node_modules|\.pnpm-store|\.venv|site-packages)/' || echo clean
git count-objects -vH
```

**History rewrite (destructive — Class-E, user approval required).**
W12 runbook gap that lost real data: an uncommitted `verification_log.md`
edit was wiped by the tree reset, and every `memory/**/commit:` /
review-package reference went stale when all hashes changed. The order below
is mandatory — steps 1, 2 and 5 are the incident fixes.

```bash
# 0) USER APPROVAL first (Class-E). Record the decision in tests/decisions.md.
# 1) CLEAN TREE — forced capture (a rewrite resets tracked files and drops
#    every uncommitted change; this is the step that lost the W12 log edits).
#    STOP until `git status --porcelain` is empty — untracked work counts:
git status --porcelain
git add -u                        # tracked modifications
git add <explicit new paths>      # untracked work you keep — NAME them
#   (or `git stash push -u` to keep the work out of the wave entirely;
#    `git add -A` stays forbidden in a mixed workspace — the staging rule)
git commit -m "chore: carry-over <previous wave> work before history rewrite"
test -z "$(git status --porcelain)" || { echo "STOP: tree still dirty"; exit 1; }
# 2) MIRROR BACKUP (keep it; log the path AND commit that log line — step 1's
#    clean-tree rule applies to the log edit itself):
git clone --mirror . ../<repo>-backup-$(date +%Y%m%d-%H%M).git
#    capture the BEFORE measurements NOW (step 4 compares them AFTER):
git count-objects -vH ; git cat-file --batch-all-objects --batch-check | sort -k3 -n | tail -3 ; git rev-list --count --all
# 3) REWRITE — typical offender path set (add the wave's own offenders):
git filter-repo --invert-paths --path .pnpm-store --path node_modules \
  --path .venv --path playwright-cache --path '*.zip' --path '*.sql.gz' \
  --path workspace/<vendor>/opencode.db
# 4) VERIFY the surgery (对照 step 2 的 BEFORE 值记录 all three AFTER):
git count-objects -vH                                   # .git size
git cat-file --batch-all-objects --batch-check \
  | sort -k3 -n | tail -3                               # largest blobs
git rev-list --count --all                              # commit count
# 5) HASH REMAP — every commit id changed; references are rewritten FROM
#    .git/filter-repo/commit-map (copy, never retype a hash by hand; the
#    file is space-separated "old new" pairs under an "old new" header):
#      memory/**/commit:  ·  tests/verification_log.md  ·  review packages
awk 'NR>1{print substr($1,1,12) " -> " substr($2,1,12)}' .git/filter-repo/commit-map
# 6) POST-CLEANUP (git filter-branch checklist legacy):
git for-each-ref --format='%(refname)' | grep refs/original && echo "LEFTOVER" || echo clean
git reflog expire --expire=now --all && git gc --prune=now --aggressive
# coordinate with every collaborator before force-pushing; keep the mirror.
```

Do not run this automatically. A history rewrite changes every commit hash;
the user owns that decision. Record it in `tests/decisions.md` (Class-E) and
verify `git rev-list --objects --all | rg '\.pnpm-store/'` is empty afterward.

**Staging rule:** `git add -u && git add <explicit new paths>` only. Never
`git add -A` / `git add .` in a mixed workspace. A pre-commit hook is useful
but bypassable with `--no-verify`; the authoritative gate is group 21.
