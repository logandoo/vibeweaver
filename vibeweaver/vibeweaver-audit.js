import { existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs"
import path from "node:path"
import os from "node:os"
import { fileURLToPath, pathToFileURL } from "node:url"

// vibeweaver-audit — Tier-0/1/2 session auditor for the vibeweaver skill.
//
// Tier 0 (passive): observes assistant text parts + tool calls via the
//   generic `event` hook (message.part.updated events carry
//   {type, properties:{sessionID, part}}). No model cooperation needed.
// Tier 1 (mechanical, OK/BAD/UNCERTAIN): artifact checks, narration
//   markers, and claim<->artifact cross-checks of the [Verification Gate]
//   line (pure logic in scripts/vibeweaver-audit-core.js).
// Tier 2 (escalation): UNCERTAIN / sampling / high-risk -> escalate=true in
//   tests/gate_audit.md; skill protocol then requires a fresh-brain review.
//
// IMPORTANT (opencode plugin contract): this module exports EXACTLY ONE
// value — the plugin factory. The legacy loader iterates every export and
// throws on non-function values, which silently disables the whole plugin.
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

// ---------- plugin ----------

export const VibeweaverAudit = async ({ client, directory }) => {
  const core = await loadCore()
  if (!core) {
    // fail-safe: never crash opencode; the audit just stays silent
    console.error("[vibeweaver-audit] core module not found — audit disabled (set VIBEWEAVER_AUDIT_CORE)")
    return {}
  }
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
    const audit = auditProject({
      root,
      sessionID,
      sessionText: sess.text,
      tools: sess.tools,
      skillLoaded: loaded,
      phase,
      config: readConfig(),
    })
    if (audit.skipped) return null
    const packets = makePackets(audit, sess)
    const report = buildReport(audit, sessionID, packets)
    try {
      if (!existsSync(path.join(root, "tests"))) mkdirSync(path.join(root, "tests"), { recursive: true })
      writeFileSync(path.join(root, "tests", AUDIT_FILE), report)
    } catch {
      /* report best-effort */
    }
    if (!state.roots[root]) state.roots[root] = {}
    if (phase === "final") state.roots[root].red = audit.red
    state.roots[root].lastSession = sessionID
    flush()
    return { audit, report }
  }

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

  return {
    // Block BEFORE the write lands: red is per-project, so no sessionID needed.
    // tests/** stays writable so evidence fixes never deadlock.
    "tool.execute.before": async (input) => {
      if (!input || (input.tool !== "write" && input.tool !== "edit")) return
      if (process.env.VIBEWEAVER_AUDIT === "off") return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
      if (!root || !state.roots[root] || !state.roots[root].red) return
      if (filePath && filePath.startsWith(path.join(root, "tests") + path.sep)) return
      throw new Error(
        "GATE-BLOCKED (vibeweaver-audit): mechanical audit is RED for this project — read tests/gate_audit.md. To clear: fix the BAD claims (tests/ stays writable — append `- audit-fix: ...` entries to tests/verification_log.md and, for narration claims, emit a corrected [Verification Gate] line in your reply), then the audit re-runs at session end and unblocks writes. Escalate via VIBEWEAVER_AUDIT=off only with user consent."
      )
    },
    event: async ({ event }) => {
      if (!event || !event.type || !event.properties) return
      const props = event.properties
      const sessionID = props.sessionID
      if (event.type === "message.part.updated" && sessionID) {
        observePart(sessionID, props.part)
      } else if (event.type === "session.idle" && sessionID) {
        if (process.env.VIBEWEAVER_AUDIT === "off") return
        flush()
        const sess = state.sessions[sessionID]
        // mid-task idle (no completion marker yet) -> warn-only audit, no red.
        // Skill-absent sessions have no gate line by definition: their final
        // audit is always meaningful (C17 skill-absent detection).
        const phase = sess && (completionHeuristic(sess) || !skillLoaded(sess)) ? "final" : "mid"
        const result = await runAudit(sessionID, phase)
        if (result && result.audit) {
          try {
            await client.app.log({
              body: {
                service: "vibeweaver-audit",
                level: result.audit.red ? "warn" : result.audit.escalate ? "info" : "debug",
                message: `Audit ${result.audit.red ? "RED" : result.audit.escalate ? "ESCALATE" : "GREEN"} (BAD=${result.audit.bad} UNCERTAIN=${result.audit.uncertain})`,
                extra: { escalateReasons: result.audit.escalateReasons },
              },
            })
          } catch {
            /* logging must never crash the plugin */
          }
        }
      }
    },
  }
}
