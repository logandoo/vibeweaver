# AUDIT — vibeweaver-audit plugin (Tier-0/1/2) ★ MANDATORY

> Split from [COMPLETION_GATE.md](COMPLETION_GATE.md) §AUDIT (W20c) — the
> vibeweaver-audit plugin's full spec. Read per the Read Contract (R1b).

The `vibeweaver-audit` plugin (installed beside vibeweaver-gate.js in
`~/.config/opencode/plugins/`) mechanically audits every session that loaded
the vibeweaver skill. It runs no LLM, needs no prompt, and requires ZERO
cooperation from the agent — it observes passively (message parts + tool
calls). Full architecture notes: the vibeweaver-audit plugin source.

**What it checks (three-state OK / BAD / UNCERTAIN):**
- **Group A — on-disk artifacts:** verification_log has ≥1 `- iter` entry ·
  acceptance.md first line `> cap=5  stall=3×` · every cited media/screenshot
  exists >0 bytes · assert_artifacts.py actually runs and exits 0.
- **Group B — narration markers in your text:** `[Verification Gate]` ·
  `HARD-GATE-1: NO-TEST-NO-DONE` · `HARD-GATE-2: SCRIPT-ONLY` ·
  `[Covenant Recall]` · `[Memory Gate]` · `[Convergence]` · 8-column table
  header · `assert_artifacts.py: pass=N/fail=0` · `covenant_recall: pass` ·
  `memory_gate: pass`.
- **Group C — claim↔artifact cross-checks of the gate line (triage):**
  `Loop executed` ↔ iter entries · `Iterations` ↔ log count · `Media graded` ↔
  files on disk · `E2E depth` ↔ `tests/workflows/*.trace.log` · `TDD RED` ↔
  `- iter N FAIL:` · `Fresh-run` ↔ commit time vs log write · `Code review`
  ↔ dispatch/reason · script-only ↔ bash (raw `npm run build`/`vite`/`npm
  start`/`uvicorn`/`pkill -f` forbidden) · R1/R1b reads ↔ read tool calls ·
  verifier announcement · COV-9 entry · HARD-GATE-1/2 values.

**Report:** written to `tests/gate_audit.md` at session idle (refreshed at
every session idle, which fires after EVERY assistant turn). The FULL final
audit runs only when the session text contains the completion markers
(`[Verification Gate]` or the 8-column table header); in-progress turns get
the warn-only mid audit and never set BLOCKING (multi-turn tasks must not
deadlock). First line is the verdict:
```
AUDIT: BAD=n UNCERTAIN=n escalate=true|false reasons=[BAD,UNCERTAIN,HIGH-RISK,SAMPLING] BLOCKING=yes|no
```
- `BLOCKING=yes` latches RED at the project root (persisted per project root in
  `.vibeweaver/audit-state.json`, with the latching session's ID embedded in the
  latch value) and the next
  non-test `write`/`edit` throws GATE-BLOCKED (`tool.execute.before`).
  **The latch is scoped to the session that earned it:**
  - The latching session stays blocked while it continues — self-correct:
    repair each `[BAD]` item (fix the evidence, append `- audit-fix: …` /
    `- audit-ruling: …` entries to `tests/verification_log.md`) and re-emit
    a corrected `[Verification Gate]` line; the audit re-runs at every idle
    and on every write. No human action is needed.
  - Session-scoped, D3 (2026-10-15): a FOREIGN session's writes never clear
    the latch (the old takeover release was a bypass). Releases: the latching
    session's OWN next task (new-task key below), the TTL (`redTtlHours`,
    default 24h), or legacy (pre session-scoping) state. `tests/` stays
    writable throughout. Every release is recorded — `redReleases` (bounded
    to 5), the app log, and the report's `## Stale RED releases` — never
    silently dropped.
  - **Same-session new-task key (2026-10-02, multi-wave DOC→CODE deadlock):**
    the first action of a new task is writing `tests/acceptance.md` (Step 1,
    `tests/` is writable under the latch) — an acceptance rewrite whose
    floor(mtime) is strictly AFTER the latch `ts` releases on the session's
    next gated write/idle, journaled `new-task` (an already-expired latch
    journals `ttl-expiry`; the dominant fact wins). Same-ms ties resolve to
    "no release"; a backward clock step is the remaining skew corner
    (fail-safe: stays blocked). The old wave's debt stays in
    `tests/gate_audit.md`; the new wave's completion claim re-checks
    everything (re-arm leg below).
  - **BAD-signature guard (no re-latch treadmill; r2 hardening):** a final
    audit scores the WHOLE buffer, so re-audits of an unchanged failure must
    not re-latch. Re-latch requires a genuinely new failure: the *session
    signature* (sorted BAD ids, keyed PER SESSION — root keys would amnesty
    a different session's first failure) or the *completion-marker count*
    (grows by one per NEW claim — a new claim re-arms even with an identical
    signature; same-claim re-audits stay suppressed). A live latch is never
    refreshed (TTL backstop stays real); a GREEN final clears the latch,
    signature and count. Boundaries: two claims >150KB apart can trim the
    earlier marker (head 20KB kept) — the count leg misses one re-arm, the
    signature leg still fires; quoted marker mentions count too — fail-closed,
    journaled. Pre-deploy latches carry no signature and may re-latch once
    before the guard records theirs — self-healing in one cycle.
  - Any `test`/`tests` directory in the project (top-level `tests/`,
    `dev/tests/`, `src/test/`, …) stays writable while RED, so the
    evidence-fix path can never deadlock.
- `escalate=true` → the Tier-2 contract below applies.

**Tier-2 escalation contract (escalate=true — YOUR obligation, NOT optional):**
1. Read `tests/gate_audit.md` IN FULL: every `[BAD]` line names the broken
   artifact/claim; every `[UNCERTAIN]` line names what could not be verified
   mechanically, with a review packet (`<packet id="C9">...`) of the evidence.
2. Dispatch a **fresh-brain reviewer** (opencode `task` tool, READ-ONLY,
   per §A4.9 verdict contract — Strengths · Critical/Important/Minor with
   file:line · Assessment) with ONLY: `tests/gate_audit.md` +
   `tests/acceptance.md` + `tests/verification_log.md` + the review packets.
   Ask it to answer, per packet: *did this step genuinely happen, on the
   evidence in the transcript/artifacts?*
3. Fix Critical/Important findings; log every fix as
   `- audit-fix: <finding> | changed: <file>` in `tests/verification_log.md`
   (machine-recognizable prefix, same format discipline as `diagnosis:`).
   A false positive gets `- audit-ruling: <packet> — false positive, reason: …`
   — never silently delete an audit line.
4. Re-run the audit (any write re-checks; or read gate_audit.md after the
   next write) until `BLOCKING=no`. `escalate` may persist on SAMPLING —
   that is by design (asymmetry rule: an all-green mechanical report is NOT
   a clearance; ~10% of sessions are escalated by hash regardless of
   verdicts to catch ritual compliance — reviewer cost is the price).

**Scope discipline:** sessions that never loaded the vibeweaver skill are
not audited (subagent reviewers, unrelated chats) — silent. Doc-only tasks
emit the gate line with `na`/`no` values; the audit accepts those claims at
face value (no artifact demanded). Disable per-run: `VIBEWEAVER_AUDIT=off`.

**Loop-guard (degenerate-generation watchdog):** the same text observation
channel also watches for runaway output, independent of the artifact audit.
Five shapes, detected the moment they emerge from the assistant text stream
(reasoning parts ride the same machinery in their own buffer and episode budget):
(a) an identical line-group repeating at the tail — period derived from the
data (any block period up to 640 lines within the 96KB tail window, i.e.
realistic code up to ~50 chars/line), multi-line groups at ≥3×; a single
repeated line needs ≥4× and punctuation-only separator lines are ignored
(identical banner/log lines ×3 are legitimate codegen); (b) a trailing run of
≥12 bare tokens stepping +1 — integers (`1,2,…,179`) or bijective base-26
letters (`a,b,…,kf`); (c) line-sparse (no-newline) tails — a char-level
suffix period: the same ≥32-char string repeated ≥4× (with a letter/digit;
short sub-period streams are caught at their ≥32-char super-period), e.g. a
sentence streamed back-to-back with no line breaks; trailing whitespace/newline
noise is normalized at scan entry on every detector path, and a ≥256-char last
line enters the scan even under newline-rich context); (d) counter-bearing
line runs — ≥16 consecutive tail lines with identical non-digit shape whose
every digit run steps strictly +1 (`The backlog item {i} …` walls; strict +1
excludes timestamp logs and `page N of M`; a single trailing status line does
not mask the run); (e) punctuation-only walls — a punct-only suffix period
counts only once the wall's own trailing punctuation run is ≥2KB (a big
report ending in a short rule/banner and ASCII-art separators stay clean);
plus a visible-text-only ceiling: >256KB fires `runaway` (re-armed per 256KB;
`loopGuardTurnCeilingBytes`, min 64KB; reasoning excluded, independent 1MB
backstop `loopGuardReasoningCeilingBytes` (min 256KB); id-less hosts reset at
the user boundary — unseen-shape backstop). Repeated JSX/HTML
elements ×3 and pure-punctuation runs stay clean by the same bar. On trigger
the plugin interrupts the session (v1 `session.abort` / v2
`session.interrupt({continue:false})`) and posts a corrective prompt naming
the pattern (restate the task in one line + the single next concrete step).
One intervention per degeneration episode (re-arms after clean text or a NEW
assistant turn — fresh-turn re-degeneration gets its own intervention;
same-turn continuation never re-fires), budget 2 per session per
channel (further episodes are log-only, config
`loopGuardMaxInterventions` in `audit.json`). Near-misses excluded:
numbered lists with content (`1. step`) are not bare tokens;
a 2× repetition is below the bar. Disable per-run:
`VIBEWEAVER_LOOPGUARD=off`.

**C8 self-clearing rule:** a forbidden raw command (C8) flags only ONCE per
project root (command-hash dedup, persisted in `.vibeweaver/audit-state.json`
`c8Flagged`). Immutable session history can never pin a session in a
permanent RED latch — the latch clears on the next GREEN audit; every NEW
distinct forbidden command still flags. The dedup is persisted only by the
FINAL audit: a mid-phase warning never consumes the one-shot, so a forbidden
command run mid-task still latches when the completion audit lands.

**Config lives OUTSIDE the agent's write scope:** global only —
`~/.config/opencode/vibeweaver/audit.json` (overrides DEFAULTS:
`samplingRate` · `escOnUncertain` · `escOnHighRisk` · `forbiddenRaw`).
A project-local `.vibeweaver/audit.json` is DELIBERATELY IGNORED — the agent
can write it, and a model under prompt injection would use it to disable its
own auditor (the optimizer must never have write access to its own objective
function).

**Known boundaries (by design, not bugs):** the audit proves tokens, files
and orderings — never intent. `na`/`no` claims are accepted at face value;
A4.9 trigger classification rests on the model's self-assessment; process
compliance is not outcome correctness. Those are the reviewer's (and the
user's) judgments — the audit's job is to make the machine-checkable layer
honest. A truncated/aborted session's buffered text may be incomplete
(head/tail caps), so its final audit can latch RED on partial evidence —
that is the latch being conservative, and it is bounded precisely because
of this: it yields to the session's own next task (new-task key) or expires
with its TTL (D3: a FOREIGN session's writes never clear it); is fully
recorded; its re-audit cannot feed on an unchanged failure signature; and
the evidence path (tests/) stays writable so it can never dead-lock a fix.
