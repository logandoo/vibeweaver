# Memory Templates

> Copy-paste templates for creating `memory/` files in Vibeweaver-managed projects.
> Full rules: [MEMORY_RULES.md §A7.1–§A7.14](MEMORY_RULES.md)

---

## MEMORY.md — Index (Create for New Projects)

Create `memory/MEMORY.md`:

```markdown
# Project Memory Index

## User Context
<!-- user type entries: role, goals, skill level, preferences -->
<!-- Format: - [Title](file.md) — One-line description (keep under ~150 chars) -->

## Feedback — Validated Approaches
<!-- feedback type: what to keep doing, confirmed by user -->

## Feedback — Corrections
<!-- feedback type: what to avoid, corrections from user -->

## Project Context
<!-- project type: ongoing work, deadlines, team context -->

## External References
<!-- reference type: pointers to external resources (issue tracker, dashboards, docs) -->

## Fix Tracking
<!-- fix type entries, prefixed with trust tier -->
<!-- Format: - ⛔ [Forbidden: Title](file.md) — Short description -->
<!--         - ✅ [Fix: Title](file.md) — Short description -->
<!--         - ⏳ [Fix: Title](file.md) — Short description -->

## Key Dependencies & Conventions
- (non-obvious relationships between files/modules)
```

**Caps reminder:**
- **Loading cap:** 200 lines or 25,000 bytes — whichever comes first
- **Consolidation trigger:** 150 lines or 20,000 bytes — consolidate when exceeded
- Keep each index line to one line under ~150 characters
- Group entries by type section
- Use ⛔/✅/⏳ prefixes on fix tracking entries so trust level is visible without loading the topic file

---

## Topic File — User Type

Save as `memory/user_<topic>.md`:

```markdown
---
name: User Role & Preferences
description: Short description — used to decide relevance in future sessions, so be specific
type: user
date: YYYY-MM-DD
---

# User Role & Preferences

**Role:** (e.g., Senior backend engineer, Frontend lead, Full-stack developer)

**Goals:** (e.g., Building a scalable API for a SaaS product)

**Skill Level:** (e.g., Expert in Python and TypeScript, comfortable with PostgreSQL)

**Preferences:**
- (e.g., Prefers explicit error handling over try-catch)
- (e.g., Always uses TypeScript strict mode)
- (e.g., Favors functional patterns over class-based OOP)
```

---

## Topic File — Feedback Type (Validated Approach)

Save as `memory/feedback_<topic>.md`:

```markdown
---
name: Short Descriptive Title
description: One-line description — used to decide relevance in future sessions, so be specific
type: feedback
date: YYYY-MM-DD
---

# Title (the rule itself)

**Why:** The reason — past incident, strong preference, constraint that led to this rule.

**How to apply:** When/where this guidance kicks in. Include edge cases and exceptions.
```

**Example:**
```markdown
---
name: Always Use Repository Layer for DB Access
description: Never write raw SQL or ORM queries in route handlers — always go through the repository layer
type: feedback
date: 2026-06-28
---

# Always Use Repository Layer for DB Access

**Why:** Prior incident where a route handler contained a raw SQL query with a SQL injection vulnerability. The repository layer provides parameterized queries and input sanitization.

**How to apply:** All database access in `app/routers/` must go through functions in `app/repositories/`. Raw SQL or ORM queries in route handlers are forbidden. Exception: read-only health-check queries that don't accept user input.
```

---

## Topic File — Feedback Type (Correction)

Save as `memory/feedback_<topic>.md`:

```markdown
---
name: Short Descriptive Title (what NOT to do)
description: One-line description — used to decide relevance in future sessions, so be specific
type: feedback
date: YYYY-MM-DD
---

# Don't (the correction itself)

**Why:** The reason — what went wrong when this was tried, why it caused problems.

**How to apply:** What to do instead. When this rule kicks in.
```

---

## Topic File — Project Type

Save as `memory/project_<topic>.md`:

```markdown
---
name: Short Descriptive Title
description: One-line description — used to decide relevance in future sessions, so be specific
type: project
date: YYYY-MM-DD
---

# Fact or Decision

**Why:** The reason this fact or decision matters.

**How to apply:** When this context is relevant. How it affects work.
```

**Example:**
```markdown
---
name: Q4 Merge Freeze 2026
description: Team release schedule with merge freeze and cutoff dates for Q4 2026
type: project
date: 2026-03-01
---

# Merge Freeze Begins 2026-03-05

**Why:** Mobile team is cutting a release branch on that date.

**How to apply:** Flag any non-critical PR work scheduled after 2026-03-05. Critical bugfixes still allowed with release-manager approval. Release cutoff is 2026-03-12 — no changes after that date.
```

---

## Topic File — Reference Type

Save as `memory/reference_<topic>.md`:

```markdown
---
name: Short Descriptive Title
description: One-line description — used to decide relevance in future sessions, so be specific
type: reference
date: YYYY-MM-DD
---

# Resource Name

**Location:** URL or path

**Purpose:** What this resource provides. When to consult it.
```

**Example:**
```markdown
---
name: Production Grafana Dashboard
description: CPU, memory, and request latency metrics for the production cluster
type: reference
date: 2026-06-28
---

# Production Grafana Dashboard

**Location:** https://grafana.example.com/d/prod-overview

**Purpose:** Monitor system health — CPU usage, memory pressure, request latency, and error rates. Consult before and after deployments to verify no regression.
```

---

## Topic File — Fix Type (⛔ Forbidden)

Save as `memory/fix_forbidden_<topic>.md`:

```markdown
---
name: Forbidden: Short Title
description: One-line description of the forbidden method — used to decide relevance
type: fix
date: YYYY-MM-DD
status: ⛔
commit: abc1234   # Commit where this method was finally ruled out; N/A if not tied to one commit
---

# ⛔ Forbidden: (Method/Action)

**Area / File:** (where this applies)

**DO NOT:** (the forbidden approach)

**Why:** (what went wrong — 3+ failures proved this method doesn't work)

**DO Instead:** (the correct approach to use)
```

---

## Topic File — Fix Type (✅ Verified)

Save as `memory/fix_<topic>.md`. Created by promoting a ⏳ entry after user confirmation:

```markdown
---
name: Fix: Short Title
description: One-line description of the bug and fix — used to decide relevance
type: fix
date: YYYY-MM-DD
status: ✅
commit: abc1234   # Short hash of the verified fix commit
file_refs:        # Optional but recommended — enables stale-ref auto-detection (MEMORY_RULES.md §A7.6 rule 8)
  - path: backend/app/auth/config.py
    range: "40-50"
    sha_at_time: 8f3a2c1   # git rev-parse <commit>:<path> at fix time
last_validated: YYYY-MM-DD # Last session that re-verified this entry
---

# Fix: (Bug/Issue Title)

**Problem:** What the user reported or what was observed.

**Root Cause:** The underlying cause — not the symptom.

**Correct Fix:** What was changed, with file paths and line references.

**Failed Approaches (DO NOT retry):**
- Approach 1: What was tried and why it didn't work
- Approach 2: What was tried and why it didn't work

**Rejected Alternatives:** Directions considered but not implemented, and why they were rejected. This prevents future sessions from rediscovering the same dead ends.

**Files:** `path/to/file1.ts`, `path/to/file2.ts`
```

---

## Topic File — Fix Type (⏳ Unverified)

Save as `memory/fix_<topic>.md`. ALL new fixes start here:

```markdown
---
name: Fix: Short Title
description: One-line description of the bug and attempted fix — used to decide relevance
type: fix
date: YYYY-MM-DD
status: ⏳
commit: abc1234   # Short hash of the attempted fix commit; N/A if not yet committed
---

# Fix: (Bug/Issue Title)

**Problem:** What the user reported or what was observed.

**Attempted Fix:** What was changed and why this approach was chosen.

**Rejected Alternatives:** Other directions considered before choosing this attempt, and why they were rejected.

**Files:** `path/to/file1.ts`, `path/to/file2.ts`

**Status:** ⏳ Pending — awaiting user confirmation
```

If tests FAIL, use `status: ❌` and add a **Notes** section explaining what went wrong:

```markdown
---
name: Fix: Short Title
description: One-line description
type: fix
date: YYYY-MM-DD
status: ❌
commit: abc1234   # Short hash of the failed attempt commit; N/A if not yet committed
---

# Fix: (Bug/Issue Title)

**Problem:** What was observed.

**Attempted Fix:** What was changed.

**Rejected Alternatives:** Other directions considered and rejected before this attempt.

**Files:** `path/to/file1.ts`

**Status:** ❌ Failed — automated tests did not pass

**Notes:** The test failure indicated that (explain what went wrong). Next attempt should try (different direction).
```

---

## Consolidation Log

Create `memory/.consolidation-log.md` when consolidating (see MEMORY_RULES.md §A7.13):

```markdown
# Consolidation Log

## YYYY-MM-DD
- Merged: `feedback_testing_1.md` + `feedback_testing_2.md` → `feedback_testing.md`
- Removed: `fix_old_ui_bug.md` (referenced files no longer exist)
- Removed: `project_sprint_12.md` (sprint completed, no longer relevant)
- Pruned: 3 ⏳ entries older than 14 days
```

---

## Session Scratchpad (Temporary)

Create `memory/.session-scratchpad.md` only for complex tasks with ≥3 failed attempts or multi-step backtracking. Delete it at session end after writing permanent memory topic files.

```markdown
# Session Scratchpad — YYYY-MM-DD

## Task
(Brief restatement of the current task.)

## Memories Consulted
- `memory/fix_<topic>.md` — (relevance)
- `memory/feedback_<topic>.md` — (relevance)

## Hypothesis Chain
1. **Hypothesis:** (what we think will fix it)
   **Result:** (pass / fail / partial)
   **Next:** (what to try next)
2. **Hypothesis:** ...

## Current Direction
(The approach being tried right now.)

## Blockers
(Anything preventing progress.)
```
