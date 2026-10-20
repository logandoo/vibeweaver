import { execFileSync } from "node:child_process"
import { existsSync, readFileSync, statSync } from "node:fs"
import path from "node:path"

// vibeweaver-mini-gate — the mini kit's physical gate.
//
// The full vibeweaver gate activates on tests/verification_log.md. The mini
// kit does not create that file: its contract is the checker's literal
// "ALL CHECKS PASS". This plugin enforces that contract directly.
//
//   - after every write/edit in a mini project: run the checker
//     (script/check.sh first, else vw_check.py); on failure throw the repair
//     packet into the tool result; on success surface ALL CHECKS PASS.
//   - at session idle: if the assistant claimed completion while the checker
//     is not green, post ONE corrective prompt (budget 2/session).
//   - full-skill projects (tests/verification_log.md) are untouched: the
//     full gate owns them.
//
// Disable with VIBEWEAVER_MINI_GATE=off. Checker timeout:
// VIBEWEAVER_MINI_TIMEOUT_MS (default 120000).
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2): one default export
// { id, server, setup }; no other exports (the v1 legacy iterator and the v2
// PluginModule schema both depend on that shape).

const GATED_TOOLS = new Set(["write", "edit"])
const MAX_PROMPTS = 2
const MAX_TEXT = 4000
const DEFAULT_TIMEOUT_MS = 120000
const SKIP_STATE = new Set([".vw_test_hashes.json", ".vw_loop_state.json"])

const SESSIONS = new Map() // sessionID -> { text, prompts }

function disabled() {
  return process.env.VIBEWEAVER_MINI_GATE === "off"
}

function timeoutMs() {
  const n = Number(process.env.VIBEWEAVER_MINI_TIMEOUT_MS)
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_TIMEOUT_MS
}

function stateFor(sessionID) {
  const key = typeof sessionID === "string" && sessionID ? sessionID : "(session)"
  let st = SESSIONS.get(key)
  if (!st) {
    st = { text: "", prompts: 0 }
    SESSIONS.set(key, st)
    if (SESSIONS.size > 128) SESSIONS.delete(SESSIONS.keys().next().value)
  }
  return st
}

function pushText(sessionID, piece) {
  if (typeof piece !== "string" || !piece) return
  const st = stateFor(sessionID)
  st.text = (st.text + piece).slice(-MAX_TEXT)
}

function isCompletionClaim(text) {
  const t = String(text || "").slice(-1200).toLowerCase()
  if (!t) return false
  if (/all checks pass/.test(t)) return true
  if (/(not|isn't|is not|未|还没|尚未)\s*(done|complete|completed|finished|完成|搞定|做好)/.test(t)) return false
  return /\b(done|complete|completed|finished)\b|完成|搞定|做好了|做完了|通过了/.test(t)
}

function isDir(p) {
  try {
    return statSync(p).isDirectory()
  } catch {
    return false
  }
}

// Mini activation: a project with the checker contract; a full-skill project
// (tests/verification_log.md) is excluded so the full gate stays authoritative.
function findMiniRoot(starts) {
  const seen = new Set()
  for (const start of Array.isArray(starts) ? starts : [starts]) {
    if (typeof start !== "string" || !start) continue
    let dir
    try {
      dir = isDir(start) ? start : path.dirname(start)
    } catch {
      dir = start
    }
    dir = path.resolve(dir)
    for (let depth = 0; depth < 10; depth++) {
      if (seen.has(dir)) break
      seen.add(dir)
      if (existsSync(path.join(dir, "tests", "verification_log.md"))) return null
      if (existsSync(path.join(dir, "vw_check.py")) || existsSync(path.join(dir, ".vw_test_hashes.json"))) {
        return dir
      }
      const sh = path.join(dir, "script", "check.sh")
      if (existsSync(sh)) {
        try {
          if (readFileSync(sh, "utf8").includes("vw_check")) return dir
        } catch {
          /* unreadable check.sh is not a marker */
        }
      }
      const parent = path.dirname(dir)
      if (parent === dir) break
      dir = parent
    }
  }
  return null
}

function checkerFor(root) {
  const sh = path.join(root, "script", "check.sh")
  if (existsSync(sh)) return { cmd: "bash", args: ["script/check.sh"], strictLine: true, label: "script/check.sh" }
  if (existsSync(path.join(root, "vw_check.py"))) {
    return { cmd: process.env.VIBEWEAVER_MINI_PYTHON || "python3", args: ["vw_check.py"], strictLine: false, label: "vw_check.py" }
  }
  return null
}

function runChecker(root) {
  const c = checkerFor(root)
  if (!c) return { ok: true, output: "", missing: true, label: "none" }
  try {
    const out = execFileSync(c.cmd, c.args, {
      cwd: root,
      timeout: timeoutMs(),
      encoding: "utf8",
      maxBuffer: 4 << 20,
      stdio: ["ignore", "pipe", "pipe"],
    })
    const ok = c.strictLine ? /ALL CHECKS PASS/.test(out) : true
    return { ok, output: String(out || "").slice(-MAX_TEXT), label: c.label }
  } catch (e) {
    const out = `${(e && e.stdout) || ""}${(e && e.stderr) || ""}` || String((e && e.message) || e)
    return { ok: false, output: String(out).slice(-MAX_TEXT), label: c.label }
  }
}

function blockText(r) {
  return [
    "[vibeweaver-mini-gate] CHECKER FAILED — do not claim done.",
    r.output ? r.output.trim() : `(${r.label} failed with no output)`,
    "Fix the first failure, then run the checker again until it prints ALL CHECKS PASS.",
  ].join("\n")
}

function doneText() {
  return [
    "[vibeweaver-mini-gate] You claimed completion, but the checker did not print ALL CHECKS PASS.",
    "Run `bash script/check.sh` (or `python3 vw_check.py`), fix the first failure, and repeat.",
    "Only the literal line ALL CHECKS PASS counts as done.",
  ].join("\n")
}

function appendPass(output) {
  return (output ? output + "\n" : "") + "[vibeweaver-mini-gate] ALL CHECKS PASS"
}

async function promptV1(client, sessionID, text) {
  if (!client || !client.session || typeof client.session.prompt !== "function") return false
  try {
    await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text }] } })
    return true
  } catch {
    return false
  }
}

async function promptV2(ctx, sessionID, text) {
  if (!ctx || !ctx.session || typeof ctx.session.prompt !== "function") return false
  try {
    await ctx.session.prompt({ sessionID, text })
    return true
  } catch {
    return false
  }
}

async function onIdle({ directory, sessionID, prompt }) {
  if (disabled()) return
  const st = stateFor(sessionID)
  if (!isCompletionClaim(st.text)) return
  const root = findMiniRoot([directory])
  if (!root) return
  const r = runChecker(root)
  if (r.ok) {
    st.prompts = 0
    return
  }
  if (st.prompts >= MAX_PROMPTS) return
  if (await prompt(sessionID, doneText())) st.prompts++
}

function observePart(sessionID, part) {
  if (!part || typeof part !== "object" || part.type !== "text") return
  if (typeof part.role === "string" && part.role !== "assistant") return
  if (typeof part.text === "string") pushText(sessionID, part.text)
  else if (typeof part.delta === "string") pushText(sessionID, part.delta)
}

function writeCheck(directory, filePath) {
  if (disabled()) return null
  if (typeof filePath !== "string" || !filePath) return null
  if (SKIP_STATE.has(path.basename(filePath))) return null
  const root = findMiniRoot([filePath, directory])
  if (!root) return null
  const r = runChecker(root)
  return r.ok ? { pass: true } : { pass: false, block: blockText(r) }
}

async function server({ client, directory }) {
  return {
    "tool.execute.after": async (input, output) => {
      if (!input || !GATED_TOOLS.has(input.tool)) return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const r = writeCheck(directory, filePath)
      if (!r) return
      if (!r.pass) throw new Error(r.block)
      if (output) output.output = appendPass(output.output)
    },
    event: async ({ event }) => {
      if (!event || typeof event.type !== "string") return
      const props = event.properties || {}
      const sessionID = props.sessionID
      if (event.type === "message.part.updated" && sessionID) {
        observePart(sessionID, props.part)
      } else if (event.type === "session.idle" && sessionID) {
        await onIdle({
          directory,
          sessionID,
          prompt: (sid, text) => promptV1(client, sid, text),
        })
      }
    },
  }
}

async function setup(ctx) {
  const directory = ctx && ctx.location && typeof ctx.location.directory === "string" ? ctx.location.directory : null
  const hasV2Apis = !!(ctx && ctx.tool && typeof ctx.tool.hook === "function" && ctx.event && typeof ctx.event.subscribe === "function")
  if (!directory || !hasV2Apis) {
    if (directory && !hasV2Apis) {
      console.warn("[vibeweaver-mini-gate] v2 setup: ctx.tool.hook/ctx.event.subscribe unavailable — v2 adapter inactive for this instance")
    }
    return
  }
  const registrations = []
  registrations.push(
    await ctx.tool.hook("execute.after", async (event) => {
      if (!event || !GATED_TOOLS.has(event.tool)) return
      if (event.status !== "completed") return
      const input = event.input
      const filePath = input && typeof input === "object" && typeof input.filePath === "string" ? input.filePath : null
      const r = writeCheck(directory, filePath)
      if (!r) return
      if (!r.pass) throw new Error(r.block)
      if (event.result && typeof event.result === "object") {
        event.result.output = appendPass(typeof event.result.output === "string" ? event.result.output : "")
      }
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
          if (!sessionID) continue
          if (event.type === "session.text.delta" && typeof data.delta === "string") {
            pushText(sessionID, data.delta)
          } else if (event.type === "session.status" && data.status && data.status.type === "idle") {
            await onIdle({
              directory,
              sessionID,
              prompt: (sid, text) => promptV2(ctx, sid, text),
            })
          }
        } catch {
          /* one bad event must not kill the idle check */
        }
      }
    } catch {
      /* stream closed/aborted — best-effort guard */
    }
  })()
  return () => {
    controller.abort()
    for (const reg of registrations) {
      try {
        if (reg && typeof reg.dispose === "function") void reg.dispose()
      } catch {
        /* disposal best-effort */
      }
    }
  }
}

export default {
  id: "vibeweaver-mini-gate",
  server,
  setup,
}
