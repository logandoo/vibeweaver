import { execFileSync } from "node:child_process"
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs"
import path from "node:path"

// vibeweaver physical gate — https://opencode.ai
// Enforces the vibeweaver skill's evidence rules mechanically:
// after every write/edit, if the project is vibeweaver-active
// (has tests/verification_log.md), run the project's
// tests/assert_artifacts.py and block the tool result with a
// GATE-BLOCKED error while verification evidence is missing or
// falsified. Also runs a stateful stall observer: same file edited
// 3x with no new "iter N PASS" entry between -> GATE-WARNING pointing
// at TESTING_PROTOCOLS.md §A4.10 (warnings only, state in
// .vibeweaver/state.json, atomic writes). Disable with
// VIBEWEAVER_GATE=off.
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2):
// This module default-exports ONE object { id, server, setup }.
//   - opencode v1 (>= 1.18.29): the loader's readV1Plugin detects the
//     default object and calls server(input, options) -> the v1 hooks
//     map ("tool.execute.after" / "event"). Older v1 releases fall back
//     to iterating exports and also accept an object with a function
//     `server` property — one export means one registration either way.
//   - opencode v2 (>= 2.0.0): the loader's PluginModule schema decodes
//     ONLY the default export against { id, setup } (excess keys like
//     `server` are tolerated) and calls setup(ctx); hooks are registered
//     via ctx.tool.hook("execute.after") and ctx.event.subscribe().
// Both adapters delegate to the SAME logic so behavior is identical
// across versions. Keep exactly this one export: any extra non-function
// export breaks the legacy v1 iterator, any extra plugin-function export
// risks double registration.

const GATED_TOOLS = new Set(["write", "edit"])
const FLAG_COMBOS = [[], ["--existing"], ["--backend-only"], ["--existing", "--backend-only"]]
const BLOCKING_HINTS = ["verification_log", "acceptance", "cap=5", "screenshot", "iter ", "script/linux", "workflows"]
const STATE_DIR = ".vibeweaver"
const STATE_FILE = "state.json"
const STALL_RUN = 3        // consecutive same-file ops before a stall is worth reporting
const MAX_OPS = 20         // history kept per project

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

function runAssert(root) {
  const attempts = []
  for (const flags of FLAG_COMBOS) {
    try {
      const out = execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), ...flags], {
        cwd: root,
        encoding: "utf8",
        timeout: 15000,
        stdio: ["ignore", "pipe", "pipe"],
      })
      return { ok: true, flags, output: out.trim() }
    } catch (err) {
      const output = `${err.stdout || ""}${err.stderr || ""}`.trim() || `exit ${err.status ?? err.code}`
      attempts.push({ flags: flags.join(" ") || "(none)", output })
    }
  }
  return { ok: false, attempts }
}

function failureMessages(attempts) {
  const seen = new Set()
  const messages = []
  for (const a of attempts) {
    for (const line of a.output.split("\n")) {
      const m = line.trim()
      if (!m.startsWith("- ")) continue
      const msg = m.slice(2)
      if (!seen.has(msg)) {
        seen.add(msg)
        messages.push(msg)
      }
    }
  }
  if (!messages.length) messages.push(attempts[attempts.length - 1].output.slice(0, 400))
  return messages
}

function classify(messages) {
  const blocking = []
  const warnings = []
  for (const msg of messages) {
    if (BLOCKING_HINTS.some((h) => msg.includes(h))) blocking.push(msg)
    else warnings.push(msg)
  }
  return { blocking, warnings }
}

function inlineCheck(root) {
  const failures = []
  const testsDir = path.join(root, "tests")
  const log = safeRead(path.join(testsDir, "verification_log.md"))
  const acc = safeRead(path.join(testsDir, "acceptance.md"))
  if (!/- iter \d+ (PASS|FAIL):/.test(log)) {
    failures.push("tests/verification_log.md has no `- iter N PASS/FAIL:` entries (COV-1)")
  }
  if (!/^>\s*cap=5\s+stall=3/m.test(acc)) {
    failures.push("tests/acceptance.md missing first line `> cap=5  stall=3x` (COV-7)")
  }
  for (const m of (log + "\n" + acc).matchAll(/tests\/(\S+\.png)/g)) {
    const p = path.join(testsDir, m[1])
    if (sizeOf(p) <= 0) failures.push(`screenshot claimed but missing/empty: tests/${m[1]} (A4.4)`)
  }
  return failures
}

function checkGate(root) {
  const assertsPath = path.join(root, "tests", "assert_artifacts.py")
  if (existsSync(assertsPath)) {
    const r = runAssert(root)
    if (r.ok) return null
    const { blocking, warnings } = classify(failureMessages(r.attempts))
    return { blocking, warnings, attempts: r.attempts.map((a) => `[${a.flags}]`) }
  }
  const failures = inlineCheck(root)
  if (failures.length) return { blocking: failures, warnings: [], attempts: [], inline: true }
  return null
}

function countPasses(root) {
  const log = safeRead(path.join(root, "tests", "verification_log.md"))
  return (log.match(/^- iter \d+ PASS:/gm) || []).length
}

// Facts about recent operations only — the judgement (stall vs. hard
// problem) is the agent's. Never throws: observer problems must not
// break the gate.
function stallObservation(root, file) {
  try {
    const p = path.join(root, STATE_DIR, STATE_FILE)
    let st = { ops: [] }
    if (existsSync(p)) {
      try {
        st = JSON.parse(readFileSync(p, "utf8"))
      } catch {
        st = { ops: [] }
      }
    }
    if (!st || !Array.isArray(st.ops)) st = { ops: [] }
    st.ops.push({ f: file, p: countPasses(root), t: Date.now() })
    if (st.ops.length > MAX_OPS) st.ops = st.ops.slice(-MAX_OPS)
    const run = st.ops.slice(-STALL_RUN)
    let msg = null
    if (run.length >= STALL_RUN) {
      const sameFile = run.every((o) => o.f === run[0].f)
      const noNewPass = run[0].p === run[run.length - 1].p
      if (sameFile && noNewPass) {
        // latch: fire ONCE per (file, pass-count) signature — re-firing on
        // every later edit is alarm flood and trains warning-blindness. A
        // new PASS changes the signature and re-arms the observer.
        const firedKey = `${run[0].f}@${run[0].p}`
        if (st.firedKey !== firedKey) {
          st.firedKey = firedKey
          msg = `STALL observed (machine-counted): "${run[0].f}" modified ${STALL_RUN}x with no new "iter N PASS" entry in tests/verification_log.md in between — COV-7 stall=3x is likely reached. Do not retry the same direction: parameterize (finite candidate set + cheapest refuting test) or shift the abstraction/strategy — TESTING_PROTOCOLS.md §A4.10.`
        }
      }
    }
    if (!existsSync(path.join(root, STATE_DIR))) mkdirSync(path.join(root, STATE_DIR), { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(st))
    renameSync(tmp, p)
    return msg
  } catch {
    return null
  }
}

function blockMessage(root, result) {
  const lines = [
    "GATE-BLOCKED (vibeweaver physical gate): WRITE SUCCEEDED — this is a completion gate, NOT an execution stop. The task cannot be DECLARED complete yet — verification evidence is missing or falsified:",
    ...result.blocking.map((m) => "- " + m),
  ]
  if (result.warnings.length) {
    lines.push("Non-blocking structure warnings (fix before the final [Verification Gate] line):")
    lines.push(...result.warnings.map((m) => "- " + m))
  } else {
    lines.push("No structure warnings.")
  }
  if (result.inline) {
    lines.push("tests/assert_artifacts.py is missing — either copy it from the vibeweaver skill's scripts/assert_artifacts.py, or satisfy the inline evidence floor: >=1 `- iter N PASS/FAIL:` entry in tests/verification_log.md, tests/acceptance.md first line `> cap=5  stall=3x`, and every cited screenshot/media file present and non-empty.")
  } else if (result.attempts) {
    lines.push("assert_artifacts.py flag attempts: " + result.attempts.join(" "))
  }
  lines.push("This gate is re-checkable, not a dead stop: fix the artifacts, then your next write/edit re-runs it automatically. If the failure is legitimately out of scope, set VIBEWEAVER_GATE=off or escalate to the user.")
  return lines.join("\n")
}

function isEvidencePath(root, filePath) {
  if (typeof filePath !== "string" || !filePath) return false
  // resolve first (kills `memory/../src/app.js` traversal), then anchor the
  // exemption to the FIRST path segment under root — a nested `src/tests/`
  // source file is NOT an evidence path.
  const rel = path.relative(path.resolve(root), path.resolve(filePath))
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return false
  const seg = rel.split(path.sep)[0].toLowerCase()
  return seg === "test" || seg === "tests" || seg === "memory"
}

// ---------- cue-anchored memory triggers (§A7.16) ----------

// glob → RegExp: `**/` crosses directories, `*` stays inside a segment,
// `?` matches one non-separator char. Anchored to the project-relative path.
function globToRegExp(glob) {
  let g = String(glob)
  g = g.replace(/[.+^${}()|[\]\\]/g, "\\$&")
  g = g.replace(/\*\*\//g, " ")
  g = g.replace(/\*\*/g, "")
  g = g.replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]")
  g = g.replace(/ /g, "(?:.*/)?").replace(//g, ".*")
  return new RegExp("^" + g + "$")
}

// Parse a memory topic's frontmatter `triggers:` field — inline form
// `triggers: ["a/**", "b/**"]`, list form (any indent):
//   triggers:
//     - "a/**"
// and the scalar form `triggers: src/auth/**`. Returns [] when
// absent/unparseable (a trigger-less topic never cues).
function parseTriggers(fm) {
  const out = []
  const lines = fm.split("\n")
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^triggers:\s*(.*)$/)
    if (!m) continue
    const rest = m[1].trim()
    if (rest.startsWith("[")) {
      const inner = rest.replace(/^\[/, "").replace(/\]\s*$/, "")
      for (const part of inner.split(",")) {
        const v = part.trim().replace(/^["']|["']$/g, "")
        if (v) out.push(v)
      }
    } else if (!rest) {
      for (let j = i + 1; j < lines.length; j++) {
        const li = lines[j].match(/^\s*-\s+["']?([^"']+?)["']?\s*(?:#.*)?$/)
        if (!li) break
        out.push(li[1])
      }
    } else {
      const scalar = rest.replace(/["']/g, "").replace(/\s+#.*$/, "").trim()
      if (scalar) out.push(scalar)
    }
    break
  }
  return out
}

// Delivery-safety caps: memory topics are agent-authored text that gets
// COMPILED TO REGEX and executed synchronously in the write hook — a hostile
// or careless glob (repeated `**/` → combinatorial backtracking) would wedge
// the event loop. Cap `**` groups (≤2 keeps matching polynomial), cap length,
// and reject control chars (they double as internal sentinel bytes).
function safeGlob(t) {
  return (
    typeof t === "string" &&
    t.length > 0 &&
    t.length <= 200 &&
    !/[\x00-\x1f]/.test(t) &&
    (t.match(/\*\*/g) || []).length <= 2
  )
}

// Cue telemetry (wave19): every fire increments .vibeweaver/cue-stats.json
// per topic. Delivery counts are the feedback loop for tuning glob
// precision (a trigger that never fires / fires on everything is noise).
// Best-effort: telemetry must never break delivery.
function recordCueFires(root, notes) {
  try {
    const dir = path.join(root, STATE_DIR)
    const p = path.join(dir, "cue-stats.json")
    let stats = {}
    if (existsSync(p)) {
      try {
        stats = JSON.parse(readFileSync(p, "utf8"))
      } catch {
        stats = {}
      }
    }
    if (!stats || typeof stats !== "object") stats = {}
    for (const n of notes) {
      const m = n.match(/memory\/(\S+\.md)/)
      if (m) stats[m[1]] = (typeof stats[m[1]] === "number" ? stats[m[1]] : 0) + 1
    }
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(stats))
    renameSync(tmp, p)
  } catch {
    /* never throws */
  }
}

// One-line cue notes for memory topics whose triggers match the edited
// path. Delivery, not storage: the cue fires at the edit moment, not at
// task-start grep. Budgeted (max 3), progressive (pointer line, not the
// topic body). Never throws.
function cueNotes(root, filePath) {
  try {
    if (typeof filePath !== "string" || !filePath) return []
    const rel = path.relative(path.resolve(root), path.resolve(filePath))
    if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return []
    if (rel.split(path.sep)[0].toLowerCase() === "memory") return []
    const memDir = path.join(root, "memory")
    if (!existsSync(memDir)) return []
    const relPosix = rel.split(path.sep).join("/")
    const notes = []
    for (const f of readdirSync(memDir).sort()) {
      if (!f.endsWith(".md") || f === "MEMORY.md") continue
      const text = safeRead(path.join(memDir, f)).replace(/\r\n/g, "\n").replace(/^\uFEFF/, "")
      const fm = text.match(/^---\n([\s\S]*?)\n---/)
      if (!fm) continue
      const triggers = parseTriggers(fm[1]).filter(safeGlob)
      if (!triggers.length) continue
      const hit = triggers.some((t) => {
        try {
          return globToRegExp(t).test(relPosix)
        } catch {
          return false
        }
      })
      if (!hit) continue
      const trust = (fm[1].match(/^(?:trust|status):\s*(\S+)/m) || [])[1] || "?"
      const heading = (text.match(/^#\s+(.+)$/m) || [])[1] || f
      notes.push(`[GATE-WARNING (vibeweaver-cue)] memory cue: memory/${f} (${trust}) matches this path — read it before editing: ${heading}`)
      if (notes.length >= 3) break
    }
    if (notes.length) recordCueFires(root, notes)
    return notes
  } catch {
    return []
  }
}

// ---------- version-agnostic gate logic ----------

// Evaluate one completed write/edit. Returns:
//   { block: string }                      — caller must throw Error(block)
//   { notes: [string, ...] }               — caller must surface as warnings
//   null                                   — clean
// Ordering mirrors the legacy v1 hook: a blocking result short-circuits
// BEFORE the stall observer records the op (a blocked write is not a
// landed write).
function gateCheckWrite(directory, filePath) {
  if (process.env.VIBEWEAVER_GATE === "off") return null
  const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
  if (!root) return null
  // Cue delivery is hoisted ABOVE the gate: a RED gate (e.g. the task's
  // first write, empty log) is exactly when "read it before editing" must
  // arrive — delivery must never depend on the gate being green.
  const cues = cueNotes(root, filePath)
  // evidence-fix path must never be gated (same rule as the audit
  // plugin): writes under tests/ or memory/ ARE the evidence repair
  // itself — gating them creates the first-log catch-22 deadlock.
  if (isEvidencePath(root, filePath)) return cues.length ? { notes: cues } : null
  const result = checkGate(root)
  if (result && result.blocking.length) {
    let msg = blockMessage(root, result)
    if (cues.length) msg += "\n" + cues.join("\n")
    return { block: msg }
  }
  const notes = [...cues]
  if (result && result.warnings.length) {
    notes.push("[GATE-WARNING (vibeweaver)] non-blocking: " + result.warnings.join("; ") + " — fix before the final [Verification Gate] line.")
  }
  const stall = stallObservation(root, filePath || "(unknown file)")
  if (stall) notes.push("[GATE-WARNING (vibeweaver-stall)] " + stall)
  return notes.length ? { notes } : null
}

// Session-idle re-check: returns { blocking } when the gate is RED.
function gateIdleCheck(directory) {
  if (process.env.VIBEWEAVER_GATE === "off") return null
  const root = findProjectRoot([directory])
  if (!root) return null
  const result = checkGate(root)
  if (result && result.blocking.length) return { blocking: result.blocking }
  return null
}

// Host logging: v1 offers client.app.log({ body }); v2's ctx.app is
// {name, version, channel} (no log API) — fall back to stderr. Never
// throws: logging must never break the gate.
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

// Append warning notes to a v2 tool result (Tool.Result =
// { output?, content?: string | Content[], metadata? }). Content is the
// model-visible channel; metadata is the fallback. In-place mutation first
// (a host that captured the result reference before dispatch still sees the
// note); reassignment as the fallback for frozen/readonly results.
function appendNotesToV2Result(event, notes) {
  const text = notes.join("\n")
  const result = event.result
  if (!result || typeof result !== "object") return
  try {
    if (typeof result.content === "string") {
      result.content = result.content + "\n" + text
      return
    }
    if (Array.isArray(result.content)) {
      result.content.push({ type: "text", text })
      return
    }
    if (result.metadata && typeof result.metadata === "object") {
      result.metadata.vibeweaverGate = text
      return
    }
    result.metadata = { vibeweaverGate: text }
    return
  } catch {
    /* readonly/frozen result — fall back to reassignment */
  }
  try {
    if (typeof result.content === "string") {
      event.result = { ...result, content: result.content + "\n" + text }
    } else if (Array.isArray(result.content)) {
      event.result = { ...result, content: [...result.content, { type: "text", text }] }
    } else {
      event.result = { ...result, metadata: { ...(result.metadata || {}), vibeweaverGate: text } }
    }
  } catch {
    /* fully-frozen event — a cue note must never break a landed write */
  }
}

// v2 idle detection: v1 emits "session.idle"; v2 emits "session.status"
// with data { sessionID, status: { type: "idle" | "busy" | "retry" } }.
function v2EventIsIdle(event) {
  if (!event || event.type !== "session.status") return false
  const data = event.data
  return !!data && !!data.status && data.status.type === "idle"
}

// ---------- opencode v1 adapter ----------

async function server({ client, directory }) {
  return {
    "tool.execute.after": async (input, output) => {
      if (!GATED_TOOLS.has(input.tool)) return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const r = gateCheckWrite(directory, filePath)
      if (r && r.block) throw new Error(r.block)
      if (r && r.notes) {
        for (const note of r.notes) {
          output.output = (output.output ? output.output + "\n" : "") + note
        }
      }
    },
    event: async ({ event }) => {
      if (!event || event.type !== "session.idle") return
      const r = gateIdleCheck(directory)
      if (r) {
        await logToHost(client && client.app, {
          service: "vibeweaver-gate",
          level: "warn",
          message: "Session idle with RED verification gate",
          extra: { blocking: r.blocking },
        })
      }
    },
  }
}

// ---------- opencode v2 adapter ----------

async function setup(ctx) {
  const directory = ctx && ctx.location && typeof ctx.location.directory === "string" ? ctx.location.directory : null
  const hasV2Apis = !!(ctx && ctx.tool && typeof ctx.tool.hook === "function" && ctx.event && typeof ctx.event.subscribe === "function")
  if (!directory || !hasV2Apis) {
    // opencode v1's hybrid bridge calls setup() with a partial context (no
    // location/tool/event domains) — that is EXPECTED there and the v1 server
    // adapter provides the gate, so stay silent. Warn only when a location IS
    // present (a genuine v2 host missing hook/event APIs — worth surfacing).
    if (directory && !hasV2Apis) {
      console.warn("[vibeweaver-gate] v2 setup: ctx.tool.hook/ctx.event.subscribe unavailable in this host — v2 adapter inactive for this instance")
    }
    return
  }
  const registration = await ctx.tool.hook("execute.after", async (event) => {
    if (!event || !GATED_TOOLS.has(event.tool)) return
    // v1 parity: tool.execute.after fires only for successful executions.
    if (event.status !== "completed") return
    const input = event.input
    const filePath = input && typeof input === "object" && typeof input.filePath === "string" ? input.filePath : null
    const r = gateCheckWrite(directory, filePath)
    if (r && r.block) throw new Error(r.block)
    if (r && r.notes) appendNotesToV2Result(event, r.notes)
  })
  const controller = new AbortController()
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          if (!v2EventIsIdle(event)) continue
          const r = gateIdleCheck(directory)
          if (r) {
            await logToHost(null, {
              service: "vibeweaver-gate",
              level: "warn",
              message: "Session idle with RED verification gate",
              extra: { blocking: r.blocking },
            })
          }
        } catch {
          /* one bad event must not kill the idle re-check */
        }
      }
    } catch {
      /* stream closed/aborted — idle re-check is advisory, never crash */
    }
  })()
  return () => {
    controller.abort()
    try {
      if (registration && typeof registration.dispose === "function") void registration.dispose()
    } catch {
      /* disposal best-effort; the v2 host also scopes registrations to the plugin */
    }
  }
}

export default {
  id: "vibeweaver-gate",
  server,
  setup,
}
