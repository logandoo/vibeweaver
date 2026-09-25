import { existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs"
import path from "node:path"
import os from "node:os"
import { fileURLToPath, pathToFileURL } from "node:url"

// vibeweaver-audit — Tier-0/1/2 session auditor for the vibeweaver skill.
//
// Tier 0 (passive): observes assistant text parts + tool calls. Under
//   opencode v1 this uses the generic `event` hook (message.part.updated
//   events carry {type, properties:{sessionID, part}}); under opencode v2
//   it uses ctx.event.subscribe() (session.text.delta /
//   session.message.content.updated / session.skill.activated events) plus
//   ctx.tool.hook() for tool observations. No model cooperation needed.
// Tier 1 (mechanical, OK/BAD/UNCERTAIN): artifact checks, narration
//   markers, and claim<->artifact cross-checks of the [Verification Gate]
//   line (pure logic in scripts/vibeweaver-audit-core.js). A BAD final audit
//   latches RED at the project root and blocks the latching session's next
//   non-test write until it self-corrects (fix evidence + corrected gate
//   line, re-checked at every session idle).
//   The latch is SESSION-SCOPED: a truncated/aborted session must not be
//   able to hold the next task hostage, so the latch auto-releases on the
//   first write/idle of a DIFFERENT session, or after redTtlHours (default
//   24, audit.json), or immediately for legacy boolean state. Every release
//   is recorded in state (bounded) + app log + a "## Stale RED releases"
//   section of tests/gate_audit.md — never silently dropped.
//   Any test/tests directory in the project (tests/, dev/tests/, src/test/…)
//   stays writable while RED so the evidence-fix path never deadlocks.
// Tier 2 (escalation): UNCERTAIN / sampling / high-risk -> escalate=true in
//   tests/gate_audit.md; skill protocol then requires a fresh-brain review.
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2):
// This module default-exports ONE object { id, server, setup }.
//   - opencode v1 (>= 1.18.29): the loader's readV1Plugin detects the
//     default object and calls server(input, options) -> the v1 hooks map
//     ("tool.execute.before" / "event"). Older v1 releases fall back to
//     iterating exports and also accept an object with a function `server`
//     property — one export means one registration either way.
//   - opencode v2 (>= 2.0.0): the loader's PluginModule schema decodes ONLY
//     the default export against { id, setup } (excess keys like `server`
//     are tolerated) and calls setup(ctx); hooks are registered via
//     ctx.tool.hook(...) and events via ctx.event.subscribe().
// Both adapters drive the SAME audit machine (createAuditMachine), so latch
// state (.vibeweaver/audit-state.json) and behavior are identical across
// versions. Keep exactly this one export: any extra non-function export
// breaks the legacy v1 iterator, any extra plugin-function export risks
// double registration.
//
// Only sessions that loaded the vibeweaver skill are audited.
// Disable: VIBEWEAVER_AUDIT=off. Core path override: VIBEWEAVER_AUDIT_CORE.

const STATE_DIR = ".vibeweaver"
const STATE_FILE = "audit-state.json"
const AUDIT_FILE = "gate_audit.md"
const TEXT_CAP_HEAD = 20_000
const TEXT_CAP_TAIL = 150_000
const TOOL_CAP = 400
const IN_CAP = 400
const OUT_CAP = 300
const RED_TTL_HOURS_DEFAULT = 24
const RELEASES_CAP = 5

// ---------- helpers (never throw) ----------

function sizeOf(p) {
  try {
    return statSync(p).size
  } catch {
    return 0
  }
}

function safeRead(p) {
  try {
    return statSync(p).size > 0 ? readFileSync(p, "utf8") : ""
  } catch {
    return ""
  }
}

function findProjectRoot(startDirs) {
  for (const start of startDirs) {
    if (!start) continue
    for (let d = path.resolve(start); ; d = path.dirname(d)) {
      if (existsSync(path.join(d, "tests", "verification_log.md"))) return d
      if (d === path.dirname(d)) break
    }
  }
  return null
}

// A path is exempt from RED blocking when it lies inside the project root
// and any segment of its project-relative path is a test directory —
// covers tests/, dev/tests/, src/test/, … (the evidence-fix path must
// never deadlock, per §A4.4.2 "tests/** stays writable").
function isTestDirPath(root, filePath) {
  if (typeof filePath !== "string" || !filePath) return false
  const rel = filePath.startsWith(root + path.sep)
    ? filePath.slice(root.length + path.sep.length)
    : null
  if (rel == null) return false
  return rel.split(/[\\/]/).some((seg) => {
    const s = seg.toLowerCase()
    return s === "test" || s === "tests"
  })
}

// Normalize the stored red latch to { sessionID, ts, bad } | null.
// Legacy boolean `true` (pre session-scoping) → unknown latcher, born stale:
// it releases on the first observed session write/idle or via TTL.
function readLatch(rootEntry) {
  const r = rootEntry && rootEntry.red
  if (!r) return null
  if (typeof r === "object")
    return {
      sessionID: typeof r.sessionID === "string" ? r.sessionID : null,
      ts: typeof r.ts === "number" ? r.ts : 0,
      bad: Number.isFinite(r.bad) ? r.bad : null,
    }
  return { sessionID: null, ts: 0, bad: null }
}

// Core module resolution: env override → installed skill dir (sibling of the
// plugins dir) → repo-relative scripts/ (dev + selftest). Fail-safe: if the
// core cannot be loaded the plugin disables itself instead of crashing.
async function loadCore() {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const candidates = []
  if (process.env.VIBEWEAVER_AUDIT_CORE) candidates.push(process.env.VIBEWEAVER_AUDIT_CORE)
  candidates.push(path.join(here, "..", "skills", "vibeweaver", "scripts", "vibeweaver-audit-core.js"))
  candidates.push(path.join(here, "scripts", "vibeweaver-audit-core.js"))
  for (const c of candidates) {
    if (!existsSync(c)) continue
    try {
      return await import(pathToFileURL(c).href)
    } catch (err) {
      // fall through to next candidate
    }
  }
  return null
}

// Host logging: v1 offers client.app.log({ body }); v2's ctx.app is
// {name, version, channel} (no log API) — fall back to stderr. Never
// throws: logging must never crash the auditor.
async function logToHost(appLike, entry) {
  try {
    if (appLike && typeof appLike.log === "function") {
      await appLike.log({ body: entry })
      return
    }
  } catch {
    /* fall through to stderr */
  }
  try {
    console.error(`[${entry.service}] ${entry.level}: ${entry.message}`)
  } catch {
    /* never crash */
  }
}

// ---------- loop-guard: degenerate-generation detection ----------
// Three degeneration shapes, detected incrementally from the assistant text
// stream (same channel the audit already observes — no model cooperation):
//   (a) identical line-group repeated at the tail — period derived from the
//       data, any block period up to LOOP_MAX_LINE_PERIOD lines (bounded by
//       the LOOP_TAIL_SCAN window);
//   (b) a trailing run of >= LOOP_SEQ_MIN bare tokens stepping +1 —
//       integers (1,2,…,179) or bijective base-26 letters (a,b,…,kf);
//   (c) line-sparse (no-newline) tails — a char-level suffix period: the
//       same >=32-char string (with a letter/digit) repeated >=4x.
// On trigger the host adapter interrupts the session and posts a corrective
// prompt (budgeted per session; exhausted = log-only, never thrash).
// Disable: VIBEWEAVER_LOOPGUARD=off. Budget override: audit.json
// loopGuardMaxInterventions (config stays outside the agent's write scope).
const LOOP_SEQ_MIN = 12
const LOOP_TAIL_SCAN = 98304
const LOOP_MAX_INTERVENTIONS_DEFAULT = 2
const LOOP_CHAR_SEED = 32
const LOOP_CHAR_MIN_PERIOD = 32
const LOOP_CHAR_MAX_CANDIDATES = 16
const LOOP_MAX_LINE_PERIOD = 640

function lettersToIndex(s) {
  let n = 0
  for (const ch of s) n = n * 26 + (ch.charCodeAt(0) - 96)
  return n
}

// Char-level suffix period for line-sparse tails (generation WITHOUT
// newlines — the line-aligned scan has no structure to key on). Candidate
// periods come from re-occurrences of the last 32 chars (native lastIndexOf,
// ≤16 candidates); a seed that is itself short-periodic ("very very…")
// probes its ≥32-char super-period multiples instead of walking off empty.
// Same bar as the line path: a single repeated unit needs ≥4 copies and
// real letter/digit content — repeated JSX/HTML elements ×3 are legitimate
// codegen and stay clean.
function charPeriodRepeat(tail) {
  const minP = LOOP_CHAR_MIN_PERIOD
  if (tail.length < minP * 4) return null
  const seed = tail.slice(-LOOP_CHAR_SEED)
  if (!/[\p{L}\p{N}]/u.test(seed)) return null
  const maxP = Math.min(1024, Math.floor(tail.length / 4))
  let idx = tail.length - LOOP_CHAR_SEED
  for (let n = 0; n < LOOP_CHAR_MAX_CANDIDATES; n++) {
    const j = tail.lastIndexOf(seed, idx - 1)
    if (j < 0) return null
    const base = idx - j
    idx = j
    const starts = []
    if (base >= minP) starts.push(base)
    else for (let m = Math.ceil(minP / base); m * base <= maxP && starts.length < 4; m++) starts.push(m * base)
    for (const p of starts) {
      if (p > maxP) continue
      const last = tail.slice(-p)
      if (tail.slice(-2 * p, -p) !== last || tail.slice(-3 * p, -2 * p) !== last || tail.slice(-4 * p, -3 * p) !== last) continue
      const flat = last.trim()
      if (flat.length < 16 || !/[\p{L}\p{N}]/u.test(flat)) continue
      return { kind: "repeat", pattern: flat.replace(/\s+/g, " ").slice(0, 80) }
    }
  }
  return null
}

// Pure detector (also unit-tested directly). Returns { kind, pattern } | null.
// Runs on every text observation: the scan is bounded to the tail, so
// per-delta cost stays flat — an echo is caught the moment its 12th token /
// 3rd copy lands.
function loopFinding(text) {
  if (!text || text.length < 48) return null
  const tail = text.slice(-LOOP_TAIL_SCAN)
  const lines = tail.split("\n")
  // a trailing newline yields a spurious empty final element that would
  // break line-group alignment — strip at most that one artifact
  if (lines.length && lines[lines.length - 1] === "") lines.pop()
  // A) suffix-period repeat: the last 3p lines are ONE line-group repeated
  // ×3 — period p derived from the data (any block period ≤640 lines, as
  // bounded by the tail window), not from a fixed size list. The last line
  // must re-occur at −p and −2p for a period-p repeat, so nearly every
  // candidate early-exits on one compare.
  if (lines.length >= 3) {
    const last = lines[lines.length - 1]
    const pMax = Math.min(LOOP_MAX_LINE_PERIOD, Math.floor(lines.length / 3))
    for (let p = 1; p <= pMax; p++) {
      if (lines[lines.length - 1 - p] !== last || lines[lines.length - 1 - 2 * p] !== last) continue
      let ok = true
      for (let i = lines.length - p; i < lines.length; i++) {
        if (lines[i] !== lines[i - p] || lines[i] !== lines[i - 2 * p]) {
          ok = false
          break
        }
      }
      if (!ok) continue
      const group = lines.slice(-p)
      const flat = group.join("\n").trim()
      if (flat.length < 16) continue
      if (p === 1) {
        // single-line echo: bar raised — require a 4th copy AND real content
        // (identical separator/log lines ×3 are legitimate codegen).
        if (!/[\p{L}\p{N}]/u.test(last)) continue
        if (lines.length < 4 || lines[lines.length - 4] !== last) continue
      }
      return { kind: "repeat", pattern: flat.replace(/\s+/g, " ").slice(0, 80) }
    }
  }
  // line-sparse tail (generation without newlines): char-level suffix
  // period. Gated on the RECENT window so newline-rich history further back
  // cannot mask a no-newline runaway happening right now.
  const recent = tail.slice(-2048)
  if ((recent.match(/\n/g) || []).length < 4 || lines[lines.length - 1].length > 512) {
    const hit = charPeriodRepeat(tail)
    if (hit) return hit
  }
  const tokens = lines.map((l) => l.trim()).filter((l) => l.length > 0)
  if (tokens.length >= LOOP_SEQ_MIN) {
    const run = tokens.slice(-LOOP_SEQ_MIN)
    if (run.every((l) => /^-?\d{1,10}$/.test(l))) {
      const nums = run.map((l) => parseInt(l, 10))
      let ok = true
      for (let i = 1; i < nums.length; i++)
        if (nums[i] - nums[i - 1] !== 1) {
          ok = false
          break
        }
      if (ok) return { kind: "sequence", pattern: `${nums[0]}…${nums[nums.length - 1]}` }
    } else if (run.every((l) => /^[a-z]{1,3}$/.test(l))) {
      const nums = run.map(lettersToIndex)
      let ok = true
      for (let i = 1; i < nums.length; i++)
        if (nums[i] - nums[i - 1] !== 1) {
          ok = false
          break
        }
      if (ok) return { kind: "sequence", pattern: `${run[0]}…${run[run.length - 1]}` }
    }
  }
  return null
}

function loopRecoveryText(finding) {
  return `[loop-guard] Your output degenerated into meaningless repetition (${finding.kind}: ${finding.pattern}). STOP repeating. Reply with (1) the task you are solving in ONE line, (2) the single next concrete step, then continue normally — no sequences, no filler. If the task is actually complete, emit the final completion output instead.`
}

// ---------- audit machine (shared by the v1 + v2 adapters) ----------

function createAuditMachine({ directory, core, log, onDegenerate }) {
  const { auditProject, buildReport } = core

  let state = { sessions: {}, roots: {} }
  const statePath = path.join(directory, STATE_DIR, STATE_FILE)
  try {
    const raw = safeRead(statePath)
    if (raw) state = JSON.parse(raw)
    if (!state || typeof state.sessions !== "object") state = { sessions: {}, roots: {} }
  } catch {
    state = { sessions: {}, roots: {} }
  }

  const flush = () => {
    try {
      // prune: keep only the most recent sessions so the state file stays bounded
      const ids = Object.keys(state.sessions)
      if (ids.length > 20) {
        const keep = new Set(ids.slice(-20))
        for (const id of ids) if (!keep.has(id)) delete state.sessions[id]
      }
      if (!existsSync(path.join(directory, STATE_DIR))) mkdirSync(path.join(directory, STATE_DIR), { recursive: true })
      const tmp = statePath + ".tmp"
      writeFileSync(tmp, JSON.stringify(state))
      renameSync(tmp, statePath)
    } catch {
      /* never crash on persistence */
    }
  }

  const touchSession = (sessionID) => {
    if (!state.sessions[sessionID]) state.sessions[sessionID] = { text: "", textParts: {}, tools: [], skillLoaded: false }
    return state.sessions[sessionID]
  }

  const capText = (s) =>
    s.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL ? s.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + s.slice(-TEXT_CAP_TAIL) : s

  const skillLoaded = (sess) => sess.skillLoaded || sess.tools.some((t) => t.tool === "skill" && typeof t.name === "string" && t.name.startsWith("vibeweaver"))

  // Config lives OUTSIDE the agent's write scope — the agent could otherwise
  // weaken its own auditor (optimizer must never own its objective function).
  const readConfig = () => {
    try {
      const p = process.env.VIBEWEAVER_AUDIT_CONFIG || path.join(os.homedir(), ".config", "opencode", "vibeweaver", "audit.json")
      if (existsSync(p)) return JSON.parse(readFileSync(p, "utf8"))
    } catch {
      /* defaults */
    }
    return {}
  }

  // Release a stale RED latch. Rules (latch = { sessionID, ts, bad }):
  //   1. legacy boolean state (ts===0, never session-scoped at birth) →
  //      legacy-state release on first contact, labeled for its true origin
  //      (also reachable for object latches that lost their ts);
  //   2. a known DIFFERENT session touches the project → stale-session
  //      release (a latch must never outlive the session that earned it);
  //   3. TTL expiry (redTtlHours, default 24; audit.json) as a backstop when
  //      the same session keeps holding a live latch.
  // Never releases a fresh latch of the CURRENT session (in-session teeth).
  // Returns the release record or null. Never throws.
  const releaseStale = (root, currentSessionID, via) => {
    try {
      const entry = state.roots[root]
      const latch = readLatch(entry)
      if (!entry || !latch) return null
      const cfg = readConfig()
      const ttlHours = Number.isFinite(cfg.redTtlHours) ? cfg.redTtlHours : RED_TTL_HOURS_DEFAULT
      const age = Date.now() - latch.ts
      const cur = typeof currentSessionID === "string" && currentSessionID ? currentSessionID : null
      // ts===0 identifies a latch that was never session-scoped at birth
      // (legacy boolean form) — label it as such, not as a fleet of unknowns.
      const reason = latch.ts === 0
        ? "legacy-state"
        : cur && latch.sessionID !== cur
          ? "stale-session"
          : age > ttlHours * 3_600_000
            ? "ttl-expiry"
            : null
      if (!reason) return null
      const rec = { ts: Date.now(), from: latch.sessionID || "unknown", bad: latch.bad, reason, via, by: cur || via }
      entry.red = null
      if (!Array.isArray(entry.redReleases)) entry.redReleases = []
      entry.redReleases.push(rec)
      if (entry.redReleases.length > RELEASES_CAP) entry.redReleases = entry.redReleases.slice(-RELEASES_CAP)
      flush()
      void log({
        service: "vibeweaver-audit",
        level: "info",
        message: `Stale RED latch released (${reason}) — latched by ${rec.from} (BAD=${rec.bad == null ? "?" : rec.bad}), via ${via}`,
        extra: { root, release: rec },
      })
      return rec
    } catch {
      return null
    }
  }

  const makePackets = (audit, sess) => {
    const packets = []
    for (const c of audit.checks) {
      if (c.verdict !== "UNCERTAIN") continue
      let body = c.evidence
      if (/^(C9|C10|C11)/.test(c.id)) {
        const reads = sess.tools.filter((t) => t.tool === "read").map((t) => t.filePath).slice(-5)
        body += "\nrecent reads: " + (reads.join(" | ") || "(none)")
      } else {
        body += "\ntail of session text: " + sess.text.slice(-400)
      }
      packets.push({ id: c.id, body: body.slice(0, 1600) })
    }
    return packets
  }

  // "final" phase only when the session actually completed a task; session.idle
  // fires after EVERY turn — final checks mid-task would deadlock the loop.
  const completionHeuristic = (sess) =>
    /\[Verification Gate\]/.test(sess.text) || /^\s*\| # \| Problem \| Research Sources/m.test(sess.text)

  const runAudit = async (sessionID, phase) => {
    const sess = state.sessions[sessionID]
    if (!sess) return null
    const root = findProjectRoot([directory])
    if (!root) return null
    if (process.env.VIBEWEAVER_AUDIT === "off") return null
    const loaded = skillLoaded(sess)
    const priorFlagged = state.roots[root] && Array.isArray(state.roots[root].c8Flagged) ? state.roots[root].c8Flagged : []
    const audit = auditProject({
      root,
      sessionID,
      sessionText: sess.text,
      tools: sess.tools,
      skillLoaded: loaded,
      phase,
      config: readConfig(),
      priorFlagged,
    })
    if (audit.skipped) return null
    if (!state.roots[root]) state.roots[root] = {}
    if (phase === "final" && Array.isArray(audit.newlyFlagged) && audit.newlyFlagged.length) {
      // C8 dedup persistence — the same forbidden command never flags twice
      // for this root, so a latch stays self-clearable on later GREEN audits.
      // FINAL phase only: a mid-phase warn must NOT consume the one-shot —
      // otherwise a forbidden command run mid-task would be persisted before
      // the latching final audit ever sees it, and the latch never engages.
      state.roots[root].c8Flagged = [...new Set([...priorFlagged, ...audit.newlyFlagged])].slice(-100)
    }
    const packets = makePackets(audit, sess)
    const releases = Array.isArray(state.roots[root].redReleases) ? state.roots[root].redReleases : []
    const footer = releases.map(
      (r) =>
        `- ${new Date(r.ts).toISOString()} released: latched RED (BAD=${r.bad == null ? "?" : r.bad}, session ${r.from}) → cleared via ${r.reason} (via ${r.via}, by ${r.by})`
    )
    const report = buildReport(audit, sessionID, packets, footer)
    try {
      if (!existsSync(path.join(root, "tests"))) mkdirSync(path.join(root, "tests"), { recursive: true })
      writeFileSync(path.join(root, "tests", AUDIT_FILE), report)
    } catch {
      /* report best-effort */
    }
    if (phase === "final")
      state.roots[root].red = audit.red
        ? { sessionID, ts: Date.now(), bad: audit.bad }
        : null
    state.roots[root].lastSession = sessionID
    flush()
    return { audit, report }
  }

  // Degenerate-generation check (loop-guard) — runs on every text
  // observation once the buffer grew enough; detection is a bounded tail
  // scan, never on the whole buffer. Never throws.
  const maybeLoopCheck = (sessionID) => {
    try {
      if (process.env.VIBEWEAVER_LOOPGUARD === "off") return
      if (typeof onDegenerate !== "function") return
      const sess = state.sessions[sessionID]
      if (!sess) return
      if (!sess.loopGuard) sess.loopGuard = { interventions: 0, armed: true }
      const lg = sess.loopGuard
      const finding = loopFinding(sess.text)
      // one intervention per degeneration EPISODE: after firing, stay
      // disarmed while the same pattern still sits at the tail (the
      // interrupt stops generation; the remaining history must not
      // re-trigger). Re-arm only after a clean observation.
      if (!finding) {
        lg.armed = true
        return
      }
      if (!lg.armed) return
      lg.armed = false
      const cfg = readConfig()
      const maxInterventions = Number.isFinite(cfg.loopGuardMaxInterventions) ? cfg.loopGuardMaxInterventions : LOOP_MAX_INTERVENTIONS_DEFAULT
      if (lg.interventions >= maxInterventions) {
        // budget exhausted: never interrupt again, but log every NEW episode
        // (armed semantics guarantee this is a distinct episode, not the
        // same tail re-flagged)
        void log({
          service: "vibeweaver-loopguard",
          level: "info",
          message: `degenerate generation detected (${finding.kind}: ${finding.pattern}) — intervention budget exhausted (${maxInterventions}/session), not interrupting`,
          extra: { sessionID, finding },
        })
        return
      }
      lg.interventions++
      void log({
        service: "vibeweaver-loopguard",
        level: "warn",
        message: `degenerate generation detected (${finding.kind}: ${finding.pattern}) — interrupting and posting a corrective prompt (${lg.interventions}/${maxInterventions})`,
        extra: { sessionID, finding },
      })
      void Promise.resolve(onDegenerate(sessionID, finding, lg.interventions, maxInterventions)).catch(() => {})
    } catch {
      /* loop-guard must never break observation */
    }
  }

  // ---- v1 observation: message.part.updated parts ----
  const observePart = (sessionID, part) => {
    if (!part || typeof part !== "object") return
    const sess = touchSession(sessionID)
    if (part.type === "text" && typeof part.text === "string" && part.text) {
      // Robust against three streaming shapes: cumulative full-text updates,
      // delta chunks, and duplicate re-emissions. Inclusion heuristics:
      //   newText inside buffer  -> duplicate, skip
      //   buffer inside newText  -> cumulative update, replace
      //   neither                -> delta chunk, append
      const pid = part.id || "text"
      const buf = sess.textParts[pid] || ""
      if (buf.includes(part.text)) {
        // duplicate/partial re-emission — nothing to do
      } else if (part.text.includes(buf)) {
        sess.textParts[pid] = part.text
        sess.text = capText(Object.values(sess.textParts).join("\n"))
      } else {
        sess.textParts[pid] = buf + part.text
        sess.text = capText(Object.values(sess.textParts).join("\n"))
      }
      maybeLoopCheck(sessionID)
    } else if (part.type === "tool" && part.tool) {
      const st = part.state || {}
      const t = { tool: part.tool, t: Date.now() }
      const inp = st.input || {}
      if (typeof inp.filePath === "string") t.filePath = inp.filePath
      if (typeof inp.command === "string") t.command = inp.command.slice(0, IN_CAP)
      if (typeof inp.name === "string") t.name = inp.name
      if (part.tool === "bash" && typeof st.output === "string") t.output = st.output.slice(0, OUT_CAP)
      sess.tools.push(t)
      if (sess.tools.length > TOOL_CAP) sess.tools = sess.tools.slice(-TOOL_CAP)
      if (part.tool === "skill" && typeof inp.name === "string" && inp.name.startsWith("vibeweaver")) sess.skillLoaded = true
    }
  }

  // ---- v2 observation: tool hooks + session.* events ----
  const observeToolStart = (sessionID, tool, input) => {
    if (typeof sessionID !== "string" || !sessionID || typeof tool !== "string" || !tool) return
    const sess = touchSession(sessionID)
    const t = { tool, t: Date.now() }
    const inp = input && typeof input === "object" ? input : {}
    if (typeof inp.filePath === "string") t.filePath = inp.filePath
    if (typeof inp.command === "string") t.command = inp.command.slice(0, IN_CAP)
    if (typeof inp.name === "string") t.name = inp.name
    sess.tools.push(t)
    if (sess.tools.length > TOOL_CAP) sess.tools = sess.tools.slice(-TOOL_CAP)
    if (tool === "skill" && typeof inp.name === "string" && inp.name.startsWith("vibeweaver")) sess.skillLoaded = true
  }

  const observeToolEnd = (sessionID, tool, result) => {
    if (tool !== "bash" || typeof sessionID !== "string" || !sessionID) return
    // Tool.Result = { output?, content?: string | Content[], metadata? } —
    // content is the model-visible channel; output is the structured value.
    const content = result && typeof result === "object" ? result.content : result
    let text =
      typeof content === "string"
        ? content
        : Array.isArray(content)
          ? content.filter((c) => c && c.type === "text" && typeof c.text === "string").map((c) => c.text).join("\n")
          : ""
    if (!text && result && typeof result === "object" && typeof result.output === "string") text = result.output
    if (!text) return
    const sess = touchSession(sessionID)
    for (let i = sess.tools.length - 1; i >= 0; i--) {
      if (sess.tools[i].tool === "bash" && !sess.tools[i].output) {
        sess.tools[i].output = text.slice(0, OUT_CAP)
        break
      }
    }
  }

  const observeTextDelta = (sessionID, messageID, delta) => {
    if (typeof sessionID !== "string" || !sessionID || typeof delta !== "string" || !delta) return
    const sess = touchSession(sessionID)
    const pid = typeof messageID === "string" && messageID ? messageID : "text"
    // session.text.delta events are pure increments in emission order
    sess.textParts[pid] = (sess.textParts[pid] || "") + delta
    sess.text = capText(Object.values(sess.textParts).join("\n"))
    maybeLoopCheck(sessionID)
  }

  const observeFullContent = (sessionID, messageID, content) => {
    if (typeof sessionID !== "string" || !sessionID || !Array.isArray(content)) return
    const text = content
      .filter((c) => c && c.type === "text" && typeof c.text === "string")
      .map((c) => c.text)
      .join("\n")
    if (!text) return
    const sess = touchSession(sessionID)
    const pid = typeof messageID === "string" && messageID ? messageID : "text"
    const buf = sess.textParts[pid] || ""
    // same three-shape robustness as the v1 cumulative-update branch
    if (buf.includes(text)) return
    sess.textParts[pid] = text.includes(buf) ? text : buf + text
    sess.text = capText(Object.values(sess.textParts).join("\n"))
    maybeLoopCheck(sessionID)
  }

  const observeSkill = (sessionID, name) => {
    if (typeof sessionID !== "string" || !sessionID) return
    const sess = touchSession(sessionID)
    if (typeof name === "string" && name.startsWith("vibeweaver")) sess.skillLoaded = true
  }

  // RED-latch write gate (shared by both execute.before adapters).
  // Returns the block message to throw, or null.
  const beforeWrite = ({ tool, sessionID, filePath }) => {
    if (tool !== "write" && tool !== "edit") return null
    if (process.env.VIBEWEAVER_AUDIT === "off") return null
    const cur = typeof sessionID === "string" && sessionID ? sessionID : null
    const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
    if (!root || !state.roots[root]) return null
    releaseStale(root, cur, "write")
    const latch = readLatch(state.roots[root])
    if (!latch) return null
    if (filePath && isTestDirPath(root, filePath)) return null
    const selfLatched = cur === latch.sessionID
    return selfLatched
      ? "GATE-BLOCKED (vibeweaver-audit): YOUR session's mechanical audit is RED — read tests/gate_audit.md. To unblock: fix each [BAD] item (any test directory — tests/, dev/tests/, … — stays writable: repair the missing evidence and append `- audit-fix: …` entries to tests/verification_log.md), then re-emit a corrected [Verification Gate] line in your reply. The audit re-runs at every session idle and re-checks on every write; no human action is needed. Escalate via VIBEWEAVER_AUDIT=off only with user consent."
      : "GATE-BLOCKED (vibeweaver-audit): a mechanical RED latch for this project is still pending — read tests/gate_audit.md. Latches are scoped to the session that earned them and auto-release on a different session's first write/idle or after the red TTL (default 24h) — continuing your turn (any idle) will clear a stale latch automatically. Any test directory (tests/, dev/tests/, …) is writable right now. Escalate via VIBEWEAVER_AUDIT=off only with user consent."
  }

  // Session-idle driver (v1 "session.idle"; v2 "session.status" idle).
  const handleIdle = async (sessionID) => {
    if (typeof sessionID !== "string" || !sessionID) return
    if (process.env.VIBEWEAVER_AUDIT === "off") return
    // A stale latch (other session / TTL / legacy) must not survive this
    // session's turn — release BEFORE the audit so the takeover write
    // path is open immediately. A fresh latch of THIS session survives
    // (releaseStale refuses it) and its own final audit decides.
    const idleRoot = findProjectRoot([directory])
    if (idleRoot) releaseStale(idleRoot, sessionID, "idle")
    flush()
    const sess = state.sessions[sessionID]
    // mid-task idle (no completion marker yet) -> warn-only audit, no red.
    // Skill-absent sessions have no gate line by definition: their final
    // audit is always meaningful (C17 skill-absent detection).
    const phase = sess && (completionHeuristic(sess) || !skillLoaded(sess)) ? "final" : "mid"
    const result = await runAudit(sessionID, phase)
    if (result && result.audit) {
      await log({
        service: "vibeweaver-audit",
        level: result.audit.red ? "warn" : result.audit.escalate ? "info" : "debug",
        message: `Audit ${result.audit.red ? "RED" : result.audit.escalate ? "ESCALATE" : "GREEN"} (BAD=${result.audit.bad} UNCERTAIN=${result.audit.uncertain})`,
        extra: { escalateReasons: result.audit.escalateReasons },
      })
    }
  }

  return {
    observePart,
    observeToolStart,
    observeToolEnd,
    observeTextDelta,
    observeFullContent,
    observeSkill,
    beforeWrite,
    handleIdle,
  }
}

// ---------- opencode v1 adapter ----------

async function server({ client, directory }) {
  const core = await loadCore()
  if (!core) {
    // fail-safe: never crash opencode; the audit just stays silent
    console.error("[vibeweaver-audit] core module not found — audit disabled (set VIBEWEAVER_AUDIT_CORE)")
    return {}
  }
  const m = createAuditMachine({
    directory,
    core,
    log: (entry) => logToHost(client && client.app, entry),
    // loop-guard intervention (v1): stop the runaway generation, then resume
    // with a corrective user message. Provided only when the session APIs
    // exist — otherwise the guard stays fully inactive (no phantom budget).
    // API failures are swallowed — the loop-guard is best-effort and must
    // never break the hook.
    onDegenerate:
      client && client.session && typeof client.session.abort === "function" && typeof client.session.prompt === "function"
        ? async (sessionID, finding) => {
            try {
              await client.session.abort({ path: { id: sessionID } })
            } catch {
              /* best-effort */
            }
            try {
              await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: loopRecoveryText(finding) }] } })
            } catch {
              /* best-effort */
            }
          }
        : undefined,
  })
  return {
    // Block BEFORE the write lands. The RED latch is scoped to the session
    // that earned it: a different session (or TTL/legacy staleness) releases
    // it right here, so a truncated or dead session can never hold the next
    // task hostage. Any test/tests directory stays writable so evidence
    // fixes never deadlock.
    "tool.execute.before": async (input, output) => {
      if (!input || (input.tool !== "write" && input.tool !== "edit")) return
      const args = (input && input.args) || (output && output.args) || {}
      const msg = m.beforeWrite({
        tool: input.tool,
        sessionID: input.sessionID,
        filePath: typeof args.filePath === "string" ? args.filePath : null,
      })
      if (msg) throw new Error(msg)
    },
    event: async ({ event }) => {
      if (!event || !event.type || !event.properties) return
      const props = event.properties
      const sessionID = props.sessionID
      if (event.type === "message.part.updated" && sessionID) {
        m.observePart(sessionID, props.part)
      } else if (event.type === "session.idle" && sessionID) {
        await m.handleIdle(sessionID)
      }
    },
  }
}

// ---------- opencode v2 adapter ----------

async function setup(ctx) {
  const core = await loadCore()
  if (!core) {
    console.error("[vibeweaver-audit] core module not found — audit disabled (set VIBEWEAVER_AUDIT_CORE)")
    return
  }
  const directory = ctx && ctx.location && typeof ctx.location.directory === "string" ? ctx.location.directory : null
  const hasV2Apis = !!(ctx && ctx.tool && typeof ctx.tool.hook === "function" && ctx.event && typeof ctx.event.subscribe === "function")
  if (!directory || !hasV2Apis) {
    // opencode v1's hybrid bridge calls setup() with a partial context (no
    // location/tool/event domains) — that is EXPECTED there and the v1 server
    // adapter provides the audit, so stay silent. Warn only when a location
    // IS present (a genuine v2 host missing hook/event APIs).
    if (directory && !hasV2Apis) {
      console.warn("[vibeweaver-audit] v2 setup: ctx.tool.hook/ctx.event.subscribe unavailable in this host — v2 adapter inactive for this instance")
    }
    return
  }
  const m = createAuditMachine({
    directory,
    core,
    log: (entry) => logToHost(null, entry),
    // loop-guard intervention (v2): interrupt (no auto-continue), then resume
    // with a corrective prompt. Absent session APIs degrade to observation-only.
    onDegenerate:
      ctx.session && typeof ctx.session.interrupt === "function" && typeof ctx.session.prompt === "function"
        ? async (sessionID, finding) => {
            try {
              await ctx.session.interrupt({ sessionID, continue: false })
            } catch {
              /* best-effort */
            }
            try {
              await ctx.session.prompt({ sessionID, text: loopRecoveryText(finding) })
            } catch {
              /* best-effort */
            }
          }
        : undefined,
  })
  const registrations = []

  // Tool observation + RED-latch write gate via the execute.before hook
  // (fires for every tool; the gate only acts on write/edit).
  registrations.push(
    await ctx.tool.hook("execute.before", async (event) => {
      if (!event) return
      const input = event.input && typeof event.input === "object" ? event.input : {}
      if (event.tool === "write" || event.tool === "edit") {
        const msg = m.beforeWrite({
          tool: event.tool,
          sessionID: event.sessionID,
          filePath: typeof input.filePath === "string" ? input.filePath : null,
        })
        if (msg) throw new Error(msg)
      }
      m.observeToolStart(event.sessionID, event.tool, input)
    })
  )
  // Bash output capture (v1 got it from tool-part state.output).
  registrations.push(
    await ctx.tool.hook("execute.after", async (event) => {
      if (!event || event.status !== "completed") return
      m.observeToolEnd(event.sessionID, event.tool, event.result)
    })
  )

  const controller = new AbortController()
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          if (!event || typeof event.type !== "string") continue
          const data = event.data && typeof event.data === "object" ? event.data : {}
          const sessionID = typeof data.sessionID === "string" ? data.sessionID : null
          if (event.type === "session.text.delta" && sessionID) {
            m.observeTextDelta(sessionID, data.assistantMessageID, data.delta)
          } else if (event.type === "session.message.content.updated" && sessionID) {
            m.observeFullContent(sessionID, data.messageID, data.content)
          } else if (event.type === "session.skill.activated" && sessionID) {
            m.observeSkill(sessionID, data.name)
          } else if (event.type === "session.status" && sessionID && data.status && data.status.type === "idle") {
            await m.handleIdle(sessionID)
          }
        } catch {
          /* one bad event must not kill observation — fail-safe is the audit's whole point */
        }
      }
    } catch {
      /* stream closed/aborted — observation is advisory, never crash */
    }
  })()
  return () => {
    controller.abort()
    for (const r of registrations) {
      try {
        if (r && typeof r.dispose === "function") void r.dispose()
      } catch {
        /* disposal best-effort; the v2 host also scopes registrations to the plugin */
      }
    }
  }
}

export default {
  id: "vibeweaver-audit",
  server,
  setup,
}
