# MEMORY_RULES.md — Project Memory Subsystem Rules

Companion file for the `vibeweaver` skill. This file is referenced by `SKILL.md`
§A7 and holds the **detailed operational rules** for the `memory/MEMORY.md`
index, topic files, trust tiers, state flow, pre-change guardrails,
post-session writing, the Final Memory Gate, migration, multi-level merge,
consolidation rules, and retrospective backtracking.

Templates (frontmatter / topic file skeletons) live in
[MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md).

---

## A7.1 MEMORY.md — The Index

`memory/MEMORY.md` is the **entrypoint**. It is loaded into context at the
start of every session. It acts as a table of contents — not the memory content
itself.

**Format:**
```markdown
# Project Memory Index

## User Context
- [User Role & Preferences](user_role_prefs.md) — Senior backend engineer, prefers explicit error handling
- [Code Style Preferences](user_code_style.md) — Always use TypeScript strict mode, no any

## Feedback — Validated Approaches
- [Keep Using Test DB](feedback_testing.md) — Use test containers, never mock DB in integration tests
- [Bundled PRs for Auth](feedback_auth_prs.md) — Single PR for tightly coupled auth refactors

## Feedback — Corrections
- [Don't Use Raw SQL in Routes](feedback_no_raw_sql.md) — Always go through repository layer

## Project Context
- [Q4 Deadlines](project_q4_deadlines.md) — Merge freeze 2026-03-05, release cutoff 2026-03-12

## External References
- [Grafana Dashboard](reference_grafana.md) — Production metrics at grafana.example.com/d/abc123

## Fix Tracking
- ⛔ [Forbidden: Direct DB Access from Routes](fix_forbidden_db_routes.md) — Never query DB from route handlers
- ✅ [Fix: Login Timeout](fix_login_timeout.md) — Session TTL mismatch between auth service and gateway
- ⏳ [Fix: Search Pagination](fix_search_pagination.md) — Pending user confirmation

## Key Dependencies & Conventions
- `auth/` module must be loaded before `routes/` (circular dependency resolved via lazy import)
- WebSocket connections require explicit heartbeat every 30s
```

**Caps:**
- **Loading cap:** **200 lines** or **25,000 bytes** (25KB) — whichever comes first. If the index is larger, **truncate on load** and append a warning:
  ```
  > WARNING: MEMORY.md is over the limit. Only part was loaded. Consolidate entries or move detail into topic files.
  ```
- **Consolidation trigger:** When the index grows beyond **150 lines** or **20KB**, run consolidation at the end of the session (see A7.13).
- Keep each index line to one line under ~150 characters

---

## A7.2 Topic Files — One Per Memory Entry

Each memory entry is a **separate `.md` file** with YAML frontmatter. This enables on-demand loading — only the most relevant topic files are loaded per session.

**Frontmatter format:**
```yaml
---
name: Short descriptive title
description: One-line description used to decide relevance in future sessions — be specific
type: user | feedback | project | reference | fix
date: 2026-06-28
status: ⛔ | ✅ | ⏳   # Required for fix type only
commit: abc1234      # Required for fix type only — short hash of the change this memory describes
file_refs:          # Optional — for fix entries that cite specific files; enables stale-ref auto-detection (A7.6 rule 8)
  - path: backend/app/auth/config.py
    range: "40-50"         # approx line range cited
    sha_at_time: 8f3a2c1   # git blob sha at fix time: git rev-parse <commit>:<path>
last_validated: 2026-06-28 # Optional — last session that re-verified this entry
---
```

**Body structure (feedback/project types):**
- Lead with the **rule or fact** itself
- **Why:** — the reason (past incident, constraint, strong preference)
- **How to apply:** — when/where this guidance kicks in, edge cases

**Example — feedback type:**
```markdown
---
name: Don't Mock DB in Integration Tests
description: Never use in-memory SQLite or mocked repositories in tests that touch the database
type: feedback
date: 2026-06-28
---

# Don't Mock the Database in Integration Tests

**Why:** Prior incident where mock/prod divergence masked a broken migration. The mock SQLite accepted NULL in a NOT NULL column that PostgreSQL rejected.

**How to apply:** When writing tests for DB-touching code, use test containers or a real test database. Mocking is acceptable only for pure unit tests that don't exercise SQL.
```

**Example — project type:**
```markdown
---
name: Q4 Merge Freeze
description: Team release schedule with merge freeze and cutoff dates for Q4 2026
type: project
date: 2026-03-01
---

# Q4 Merge Freeze

Merge freeze begins **2026-03-05**. Mobile team is cutting a release branch.

**How to apply:** Flag any non-critical PR work scheduled after that date. Critical bugfixes still allowed with release-manager approval.
```

**Example — fix type (unverified):**
```markdown
---
name: Fix Login Timeout
description: Session TTL mismatch causing premature logout on the login page
type: fix
date: 2026-06-28
status: ⏳
commit: a1b2c3d
---

# Fix Login Timeout

**Problem:** Users reported being logged out after ~5 minutes of inactivity on the login page.

**Root Cause:** Session TTL was set to 300s in auth service but 3600s in API gateway. The gateway's longer TTL masked the issue until the auth service expired the session first.

**Correct Fix:** Aligned both TTLs to 1800s in `backend/app/auth/config.py:42` and `gateway/nginx.conf:15`.

**Failed Approaches (DO NOT retry):**
- Increasing only the auth service TTL without checking gateway — still caused mismatch
- Adding a client-side refresh timer — papered over the issue, didn't fix root cause

**Files:** `backend/app/auth/config.py`, `gateway/nginx.conf`
**Status:** ⏳ Pending — awaiting user confirmation
```

Full templates in [MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md).

---

## A7.3 Memory Types

Memories are constrained to types capturing context NOT derivable from the current project state:

| Type | What to Save | When to Save |
|------|-------------|--------------|
| **user** | User's role, goals, skill level, preferences | When you learn any detail about the user's perspective or expertise |
| **feedback** | Corrections AND confirmations on approach | When user says "don't do X", OR confirms "yes exactly, keep doing that" |
| **project** | Ongoing work, goals, deadlines, team context | When you learn who is doing what, why, or by when. Convert relative dates to absolute |
| **reference** | Pointers to external resources (issue tracker, dashboards, docs) | When you learn where to find up-to-date information outside the project |
| **fix** | Bug fixes and modifications — root cause, correct fix, failed attempts | After every code change (see State Flow Rules below) |

**Critical: Record from both failure AND success.** If you only save corrections, you will drift away from approaches the user has already validated.

---

## A7.4 What NOT to Save

- Code patterns, conventions, architecture, file paths, or project structure — derivable by reading the project
- Git history, recent changes, or who-changed-what — `git log` / `git blame` are authoritative
- Debugging solutions or fix recipes — the fix is in the code; the commit message has the context
- Anything already documented in README or other project docs
- Ephemeral task details: in-progress work, temporary state, current conversation context

---

## A7.5 Trust Tiers (for fix entries)

| Tier | Trust Level | Purpose |
|------|-------------|---------|
| ⛔ **Forbidden** | Highest — hard constraints | Methods proven to fail. Agent MUST NOT retry. |
| ✅ **Verified** | High — confirmed by user | Root cause, correct fix, failed approaches. Primary reference. |
| ⏳ **Unverified** | Low — may be wrong | Agent's modifications awaiting user validation. Informational only. |
| ❌ **Failed**    | Negation of ⏳       | An ⏳ that failed a later check or got reimplemented badly. Same hard constraints as permissibility. |

**Core principle: unverified modifications are NOT facts. Never treat ⏳ entries as proven solutions.**

---

## A7.6 On Every Skill Invocation — Memory Loading

When the skill triggers, load project memory in this order:

1. **Check if `memory/MEMORY.md` exists**
   - YES → Read it (first 200 lines / 25KB automatically loaded via truncation)
   - NO → Check if old `MODIFY.html` exists. If yes, **migrate it** to the `memory/` directory structure (see A7.11). If neither exists, this is a fresh project — create `memory/MEMORY.md` with template from [MEMORY_TEMPLATES.md](MEMORY_TEMPLATES.md).

2. **Scan the index** — For each section (User Context, Feedback, Project Context, External References, Fix Tracking), note the entries relevant to the current task.

3. **Search before selecting** — Extract keywords from the user's request (problem symptom, feature name, file/module names, error messages). Use the `grep` tool to search `memory/*.md` for topic files whose names, descriptions, or bodies mention those keywords. This catches relevant memories whose index descriptions may not be obvious.

4. **Select top 3-5 most relevant topic files** — Combine index scan + search results. Prioritize in this order:
   - ⛔ **Forbidden** entries touching the same area
   - ❌ **Failed** attempts with the same symptom
   - ✅ **Verified** fixes for the same files or problem
   - ⏳ **Unverified** attempts for the same problem
   - **Feedback** entries about the relevant approach or file
   Load only those files.

5. **Verify references before trusting** — For any loaded memory that names specific files, functions, classes, configs, or line numbers, read the current code to confirm they still exist and mean the same thing. If a reference is stale, update or remove the memory entry and note the staleness.

6. **Check for staleness** — For any loaded topic file with a `date` older than 14 days from today, display:
   ```
   > ⚠️ This memory is N days old. Memories are point-in-time observations — claims about code behavior or file:line citations may be outdated. Verify against current code before acting.
   ```

7. **Check ⏳ Unverified entries** — If the user's current request overlaps an ⏳ fix entry in problem, symptom, affected file, or attempted solution, treat it as a failure signal. Mark that entry ❌ before attempting a new direction (see A7.7 Implicit Failure Detection).

8. **✅ Verified staleness rule** — a ✅ entry is NOT immune to staleness; it only means it was verified at the commit recorded. When loading a ✅ fix entry:
   - If its `last_validated` is absent or >14 days old → mark it ⏳ again with a `stale: needs re-verification` note and re-verify before trusting.
   - If it has `file_refs[*].sha_at_time` and that ≠ current `git rev-parse HEAD:<path>` (or the ref is absent and the file moved) → same treatment: demote to ⏳ with a stale-refs note; re-verify code references against current code before acting on it.
   - A stale ✅ provides context but MUST NOT be relied on for downstream decisions until re-verified this session.

---

## A7.7 State Flow Rules (for fix-tracking entries)

```
Agent modifies code
  ↓
Agent runs Playwright / automated tests
  ├─ Tests FAIL → create fix topic file with status ❌, try different direction
  └─ Tests PASS → create fix topic file with status ⏳ (NOT as ✅)
        ↓
  Next session begins:
    ├─ User gives same/similar prompt → auto-mark ⏳ as ❌, try different direction
    ├─ User explicitly says "still broken" → mark ⏳ as ❌, try different direction
    └─ User confirms "works" / no further complaint → promote to ✅ Verified
```

**Implicit Failure Detection: if the user's current request overlaps an ⏳ fix entry in problem, symptom, affected file, or attempted solution, treat it as a failure signal. Mark that entry ❌ before attempting a new direction.**

**≥3 failures on same problem → escalate all failed methods to a ⛔ Forbidden topic file.**

---

## A7.8 Pre-Change Guardrails

Before implementing any change:
1. Check ⛔ **Forbidden** entries — do NOT use any listed method
2. Scan ✅ **Verified** fix entries for files you are about to touch — learn from confirmed solutions
3. Scan ⏳ **Unverified** fix entries for the current problem — if a pending entry exists, acknowledge it and explain why this attempt takes a different direction
4. Check **Feedback** entries for relevant guidance on approach
5. When touching a ⛔ flagged area, explicitly state why your approach avoids the forbidden pattern

---

## A7.9 Post-Session Memory Writing ★ NON-NEGOTIABLE

**At the end of every session, before outputting the completion table, you MUST review and write memories:**

1. **Review the conversation** — Identify new information worth persisting across sessions
2. **Write topic files** for each new entry in `memory/` with proper frontmatter
3. **Update MEMORY.md index** — Add pointer lines for new entries. Remove pointers to stale/removed entries
4. **Fix-tracking rules:**
   - Write fix entries as `status: ⏳` if tests passed, `status: ❌` if tests failed
   - **Never write `status: ✅`** — only user confirmation can verify a fix
   - Include the commit short hash in the frontmatter (`commit: abc1234`) for every fix entry
   - Include **Failed Approaches** and **Rejected Alternatives** in fix topic bodies so future sessions do not rediscover the same dead ends
   - If ≥3 failures preceded this fix, create/update a ⛔ Forbidden entry
5. **Record feedback memories** when user corrects or confirms approach during the session
6. **Record project memories** when you learn about goals, deadlines, or team context
7. **Check MEMORY.md caps** — If index exceeds 150 lines or 20KB, consolidate before adding more
8. **Clean up session scratchpad** — If you created `memory/.session-scratchpad.md`, delete it after permanent topic files are written

**The checklist item "Memory topic file written to memory/" is MANDATORY — do not skip it.**

---

## A7.10 Final Memory Gate ★ NON-NEGOTIABLE

Before outputting the completion table, you MUST pass this gate. If any check fails, return to A7.9 and fix it before declaring the task complete.

1. **Memory files exist** — At least one new or updated topic file exists in `memory/` for this session (unless the task was purely informational and produced nothing persistable).
2. **Index updated** — `memory/MEMORY.md` contains a pointer to the new topic file(s), and the index is under 200 lines / 25KB.
3. **Fix entries have commit** — Every `type: fix` topic file written this session includes `commit: <short-hash>` in its frontmatter.
4. **No stale references introduced** — Any file/function/line cited in new memories was verified against current code during this session.
5. **Scratchpad cleaned** — If `memory/.session-scratchpad.md` was created, it is deleted after permanent memories are written.

**Failure response:**
- If a memory should have been written but was not, write it now and re-run this gate.
- If you genuinely have nothing persistable (rare), explicitly state "No memory written — task was informational only" in the completion table's `What Changed` column.

**Explicit reporting:** In the line immediately before the completion table, output a single summary line:
```
[Memory Gate] Passed: N new/updated topic file(s) | Index updated: yes/no | Commit hashes present: yes/no/N/A | Scratchpad cleaned: yes/no/N/A
```
Do not output the completion table until this line is present and all answers are truthful.

---

## A7.11 Promoting to Verified & Migration from Old Format

**Promoting a fix to ✅ Verified:**
When user confirms a fix works (or next session has no complaint about it):
1. Change `status: ⏳` → `status: ✅` in the topic file's frontmatter
2. Fill in **Root Cause**, **Failed Approaches**, and **Rejected Alternatives** in the body
3. Add the verified commit short hash to the frontmatter (`commit: abc1234`)
4. Add `file_refs` (path + range + `sha_at_time` from `git rev-parse <commit>:<path>`) for every file cited, and set `last_validated: <today>` — this makes the ✅ entry self-aging (A7.6 rule 8)
5. Update the index line to show ✅ instead of ⏳
6. If ≥3 failures preceded the fix, also create a ⛔ Forbidden entry

**Migrating from old MODIFY.html / MODIFY_COMPACT.html:**
If an old project has `MODIFY.html` or `MODIFY_COMPACT.html` but no `memory/` directory:
1. Read the old file(s) completely
2. Split each logical entry into a separate `memory/*.md` topic file with proper frontmatter
3. Create `memory/MEMORY.md` with pointer lines for all entries
4. Do NOT delete the old HTML files — they serve as archive
5. This is a one-time migration; subsequent sessions use `memory/`

---

## A7.12 Multi-Level Memory (User-Global + Project-Local)

**Two scopes are loaded and merged on session start:**

| Scope | Path | Content | Priority |
|-------|------|---------|----------|
| **User-global** | `~/.config/opencode/vibeweaver/memory/` | Cross-project user preferences, coding style, general feedback | Lower |
| **Project-local** | `<project>/memory/` | Project-specific architecture, fix tracking, team context | Higher |

**Loading order:** User-global MEMORY.md first → Project-local MEMORY.md second. If the same topic exists in both, project-local wins.

**What goes in user-global memory:**
- User's preferred languages, frameworks, and tools
- General coding conventions (e.g., "always use TypeScript strict mode")
- Feedback that applies across all projects (e.g., "never use `any` type")
- The user's role and expertise level

**What goes in project-local memory:**
- Everything else — fix tracking, project deadlines, project-specific conventions, external references

**On session start:** Read user-global MEMORY.md first, then project-local MEMORY.md. Select top 3-5 most relevant topic files combined across both scopes.

---

## A7.13 Consolidation Rules

When `memory/` has **>15 topic files** or **MEMORY.md exceeds 150 lines or 20KB**:

1. **Keep all** ⛔ Forbidden entries verbatim — these are hard constraints
2. **Keep all** ✅ Verified fix entries
3. **Keep all** User Context and Feedback entries — these are high-value
4. **Prune ⏳ entries** — Keep only ⏳ entries from the last 14 days. Delete older unverified entries (the code they reference has likely changed)
5. **Merge related entries** — e.g., two feedback entries about testing can become one consolidated topic file
6. **Remove stale references** — If a file or function mentioned in a memory no longer exists, delete or update the entry
7. **Update MEMORY.md** — Remove pointers to deleted entries, add pointers to merged entries
8. **Write a `memory/.consolidation-log.md`** — Record: date, what was merged/removed, old entry filenames
9. **Cross-project ⛔ promotion** — If the same ⛔ Forbidden pattern exists in ≥2 projects' memories, propose to the user promoting it into the skill-level rules (ENGINEERING_STD.md / the skill's rule files). Project memory stays the record; a lesson recurring everywhere belongs one level up. Never edit skill rules silently — the user approves skill-level changes

**Do NOT consolidate mid-session.** Only at session end, after memories are written.

---

## A7.14 Retrospective Memory & Backtracking

The memory system is only effective if previous attempts are actively recalled before new attempts are made. Follow these rules to maximize retrospective value:

1. **Activate memory before fixing** — Before implementing any fix or new approach for a problem, explicitly list all prior attempts found in memory (⛔ Forbidden, ❌ Failed, ✅ Verified, ⏳ Unverified) that relate to the same symptom, file, or feature. State why each is not suitable for the current attempt.

2. **Record every direction, not just failures** — When a fix passes tests, the topic file must still include a **Failed Approaches** or **Rejected Alternatives** section listing directions that were considered and rejected, even if they were not fully implemented. This prevents future sessions from independently rediscovering the same dead ends.

3. **Mid-session backtracking scratchpad** — For tasks involving ≥3 failed attempts or complex multi-step reasoning, create a temporary `memory/.session-scratchpad.md` file. Use it to track:
   - Current hypothesis
   - What was tried and the result
   - Next candidate direction
   - Any memories consulted
   Delete this file at session end after writing the permanent memory topic files.

4. **Link fixes to commits** — Every fix topic file must include the commit hash of the change in its frontmatter (`commit: abc1234`). This allows future retrospective checks to compare the memory against the exact code state.

5. **Escalate early on repeated dead ends** — If you find yourself considering an approach that was already recorded as ❌ Failed or ⛔ Forbidden, stop. Do not retry it without a genuinely new insight. Document the new insight before proceeding.

6. **Promote ⏳ to ❌ on divergence, not just failure** — If a later task contradicts or supersedes an ⏳ fix (e.g., the user changes requirements, or the architecture shifts), mark the old ⏳ entry as ❌ and explain why it no longer applies.