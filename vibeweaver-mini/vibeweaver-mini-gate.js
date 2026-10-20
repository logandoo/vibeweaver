import { execFile } from "node:child_process"
import { existsSync, readFileSync, realpathSync, statSync } from "node:fs"
import path from "node:path"

// vibeweaver-mini-gate — the mini kit's checker gate.
//
// The full vibeweaver gate activates on tests/verification_log.md. The mini
// kit does not create that file: its contract is the checker's literal
// "ALL CHECKS PASS". This plugin enforces that contract directly.
//
//   - write/edit in a mini project: run vw_check.py (or the mini
//     script/check.sh when vw_check.py is absent); red throws the repair
//     packet, green appends the checker's own output (which contains
//     ALL CHECKS PASS).
//   - the checker, its state files and tests/verification_log.md are
//     protected: writing them is blocked while the mini gate is active.
//   - session idle: if the assistant claimed completion while the checker is
//     red, post a corrective prompt (budget 2/session). Hosts without a
//     prompt API (the shipped v2 context) get the write gate only.
//   - full-skill projects (tests/verification_log.md at the session root)
//     are excluded: the full gate owns them.
//
// Disable with VIBEWEAVER_MINI_GATE=off. Checker timeout:
// VIBEWEAVER_MINI_TIMEOUT_MS (default 900000, matching vw_check.py).
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2): one default export
// { id, server, setup }; no other exports.

const GATED_TOOLS = new Set(["write", "edit"])
const MAX_PROMPTS = 2
const MAX_TEXT = 4000
const DEFAULT_TIMEOUT_MS = 900000
const CASE_FOLD = process.platform === "darwin" || process.platform === "win32"
const key = (p) => (CASE_FOLD ? String(p).toLowerCase() : String(p))
const PROTECTED = new Set([
  "vw_check.py",
  path.join("script", "check.sh"),
  path.join("script", "vw_check.py"),
  path.join("scripts", "vw_check.py"),
  ".vw_test_hashes.json",
  ".vw_loop_state.json",
].map(key))
const FULL_MARKER = path.join("tests", "verification_log.md")
const MUTATOR = /(?:^|[^<])>{1,2}\s*(?!&[0-9-])|\btee\b|\bsed\s+-i|\bcp\b|\bmv\b|\brm\b|\btouch\b|\btruncate\b|-\s*delete\b/
const PROTECTED_RE = /(^|[\s\/\\"'])(tests[\/\\]verification_log\.md|(?:script|scripts)[\/\\]vw_check\.py|vw_check\.py|check\.sh|\.vw_test_hashes\.json|\.vw_loop_state\.json)(?=$|[\s;|&"'])/i
const VW_GLOB_RE = /(^|[\s\/\\"'])\.vw/

const SESSIONS = new Map() // sessionID -> { text, prompts, assistant:Set }

function disabled() {
  return process.env.VIBEWEAVER_MINI_GATE === "off"
}

function timeoutMs() {
  const n = Number(process.env.VIBEWEAVER_MINI_TIMEOUT_MS)
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_TIMEOUT_MS
}

function pythonCmd() {
  return process.env.VIBEWEAVER_MINI_PYTHON || (process.platform === "win32" ? "python" : "python3")
}

function real(p) {
  try {
    return realpathSync(p)
  } catch {
    return path.resolve(p)
  }
}

// Realpath for a path that may not exist yet (a before-write target). Resolve
// the nearest existing ancestor, then append the missing tail — this is what
// makes /var vs /private/var containment checks correct on macOS.
function realPath(p) {
  let cur = path.resolve(p)
  const tail = []
  for (let i = 0; i < 32; i++) {
    try {
      const r = realpathSync(cur)
      return tail.length ? path.join(r, ...tail.reverse()) : r
    } catch {
      const parent = path.dirname(cur)
      if (parent === cur) return path.resolve(p)
      tail.push(path.basename(cur))
      cur = parent
    }
  }
  return path.resolve(p)
}

function isDir(p) {
  try {
    return statSync(p).isDirectory()
  } catch {
    return false
  }
}

function inside(root, p) {
  const r = key(real(root))
  const x = key(realPath(p))
  return x === r || x.startsWith(r + path.sep)
}

function isMiniChecker(file) {
  try {
    const s = readFileSync(file, "utf8")
    return s.includes("ALL CHECKS PASS") && s.includes("vw_test_hashes")
  } catch {
    return false
  }
}

function isMiniWrapper(file) {
  try {
    const s = readFileSync(file, "utf8")
    return s.includes("vw_check") && s.includes("ALL CHECKS PASS")
  } catch {
    return false
  }
}

function stateFor(sessionID) {
  const key = typeof sessionID === "string" && sessionID ? sessionID : "(session)"
  let st = SESSIONS.get(key)
  if (!st) {
    st = { text: "", prompts: 0, assistant: new Set(), pending: new Map() }
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
  if (/(not|never|isn't|is not|haven't|hasn't|didn't|wasn't|weren't|未|还没|尚未|没有)\s*(yet\s*)?(all checks pass)/.test(t)) return false
  if (/(not|never|isn't|is not|haven't|hasn't|didn't|wasn't|weren't|未|还没|尚未|没有)\s*(yet\s*)?(done|complete|completed|finished|完成|搞定|做好)/.test(t)) return false
  return /all checks pass|\b(done|complete|completed|finished)\b|完成|搞定|做好了|做完了|通过了/.test(t)
}

// The session root is the only activation surface. No ancestor walk: a
// nested vw_check.py inside a full project must never capture the project.
function miniRoot(directory) {
  if (typeof directory !== "string" || !directory) return null
  const root = real(directory)
  if (!isDir(root)) return null
  if (existsSync(path.join(root, FULL_MARKER))) return null
  const py = path.join(root, "vw_check.py")
  if (existsSync(py) && isMiniChecker(py)) return root
  const sh = path.join(root, "script", "check.sh")
  if (existsSync(sh) && isMiniWrapper(sh)) return root
  if (existsSync(path.join(root, ".vw_test_hashes.json"))) return root // fail closed below
  return null
}

function checkerFor(root) {
  const py = path.join(root, "vw_check.py")
  if (existsSync(py) && isMiniChecker(py)) return { cmd: pythonCmd(), args: ["vw_check.py"], label: "vw_check.py" }
  const sh = path.join(root, "script", "check.sh")
  if (!existsSync(py) && existsSync(sh) && isMiniWrapper(sh)) {
    if (process.platform === "win32") return null // no reliable bash; the caller fails closed
    return { cmd: "bash", args: ["script/check.sh"], label: "script/check.sh" }
  }
  return null
}

function runChecker(root) {
  const c = checkerFor(root)
  if (!c) {
    return Promise.resolve({
      ok: false,
      missing: true,
      label: "none",
      output: "CHECKER MISSING — vw_check.py (or the mini script/check.sh) was not found or is not the mini checker. Re-run setup_project.sh.",
    })
  }
  return new Promise((resolve) => {
    execFile(
      c.cmd,
      c.args,
      {
        cwd: root,
        timeout: timeoutMs(),
        maxBuffer: 4 << 20,
        encoding: "utf8",
        env: { ...process.env, VW_CHECK_NO_STATE: "1", PYTHONDONTWRITEBYTECODE: "1" },
      },
      (err, stdout, stderr) => {
        const out = `${stdout || ""}${stderr || ""}`.trim().slice(-MAX_TEXT)
        if (err) {
          const timedOut = !!err.killed || err.signal === "SIGTERM" || err.code === "ETIMEDOUT"
          const missingCmd = err.code === "ENOENT"
          resolve({
            ok: false,
            timedOut,
            missingCmd,
            label: c.label,
            output: out || (timedOut
              ? `CHECKER TIMEOUT after ${timeoutMs()}ms — the suite hung or is too slow.`
              : missingCmd
                ? `CHECKER UNAVAILABLE (${c.cmd}) — install it or set VIBEWEAVER_MINI_PYTHON.`
                : String(err.message || err)),
          })
          return
        }
        const ok = /^\s*ALL CHECKS PASS\s*$/m.test(out)
        resolve({ ok, output: out, noLine: !ok, label: c.label })
      }
    )
  })
}

function blockText(r) {
  const head = r.timedOut
    ? "[vibeweaver-mini-gate] CHECKER TIMEOUT — do not claim done."
    : r.missing
      ? "[vibeweaver-mini-gate] CHECKER MISSING — do not claim done."
      : r.noLine
        ? "[vibeweaver-mini-gate] CHECKER EXITED 0 WITHOUT ALL CHECKS PASS — do not claim done."
        : "[vibeweaver-mini-gate] CHECKER FAILED — do not claim done."
  const tail = r.output ? r.output.trim() : "(no output)"
  const cmd = r.label === "script/check.sh" ? "bash script/check.sh" : `${pythonCmd()} vw_check.py`
  const hint = /TEST SET CHANGED/.test(tail)
    ? `A legitimate test change needs its justification: record \`- test-change: <path> — <reason>\` in your report, then run \`${cmd} --test-change "<same reason>"\`. The mini gate keeps the checker's own state; do not edit tests to pass.`
    : "Fix the first failure, then run the checker again until it prints ALL CHECKS PASS."
  return [head, tail, hint].join("\n")
}

function doneText() {
  return [
    "[vibeweaver-mini-gate] You claimed completion, but the checker did not print ALL CHECKS PASS.",
    `Run \`${pythonCmd()} vw_check.py\` (or \`bash script/check.sh\`), fix the first failure, and repeat.`,
    "Only the literal line ALL CHECKS PASS counts as done.",
  ].join("\n")
}

function appendText(output, text) {
  return (output ? output + "\n" : "") + text
}

function appendV2Result(event, text) {
  const result = event && event.result
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
    if (typeof result.output === "string") {
      result.output = result.output + "\n" + text
      return
    }
    result.metadata = { ...(result.metadata && typeof result.metadata === "object" ? result.metadata : {}), vibeweaverMiniGate: text }
  } catch {
    try {
      event.result = { ...result, content: typeof result.content === "string" ? result.content + "\n" + text : text }
    } catch {
      /* frozen result — the write gate still threw/succeeded; the note is best-effort */
    }
  }
}

function beforeWrite(directory, tool, filePath, command) {
  if (disabled()) return null
  const root = miniRoot(directory)
  if (!root) return null
  if (tool === "bash") {
    if (typeof command === "string" && MUTATOR.test(command) && (PROTECTED_RE.test(command) || VW_GLOB_RE.test(command))) {
      return "[vibeweaver-mini-gate] The checker, its state files and tests/verification_log.md are read-only while the mini gate is active. Fix the code, not the oracle."
    }
    return null
  }
  if (!GATED_TOOLS.has(tool) || typeof filePath !== "string" || !filePath) return null
  if (!inside(root, filePath)) return null
  const rel = key(path.relative(root, realPath(filePath)))
  if (rel === key(FULL_MARKER)) {
    return "[vibeweaver-mini-gate] Creating tests/verification_log.md would disable the mini gate. Install the full vibeweaver skill or set VIBEWEAVER_MINI_GATE=off first."
  }
  if (PROTECTED.has(rel)) {
    return "[vibeweaver-mini-gate] The checker and its state files are read-only while the gate is active. Fix the code, not the oracle."
  }
  return null
}

async function writeCheck(directory, filePath) {
  if (disabled()) return null
  const root = miniRoot(directory)
  if (!root) return null
  if (typeof filePath !== "string" || !filePath || !inside(root, filePath)) return null
  const rel = key(path.relative(root, realPath(filePath)))
  if (PROTECTED.has(rel) || rel === key(FULL_MARKER)) {
    return { pass: false, block: "[vibeweaver-mini-gate] The checker and its state files are read-only while the gate is active." }
  }
  const r = await runChecker(root)
  return r.ok ? { pass: true, output: r.output } : { pass: false, block: blockText(r) }
}

async function onIdle({ directory, sessionID, canPrompt, prompt }) {
  if (disabled() || !canPrompt) return
  const st = stateFor(sessionID)
  const text = st.text
  st.text = "" // consume this turn's text: a later idle must not re-fire on it
  if (!isCompletionClaim(text)) return
  const root = miniRoot(directory)
  if (!root) return
  if (st.prompts >= MAX_PROMPTS) return
  const r = await runChecker(root)
  if (r.ok) return
  if (await prompt(sessionID, doneText())) st.prompts++
}

function observePart(sessionID, part) {
  if (!part || typeof part !== "object" || part.type !== "text") return
  const st = stateFor(sessionID)
  if (typeof part.role === "string" && part.role !== "assistant") return
  // Real v1 parts carry no role and may arrive before message.updated. Buffer
  // them by messageID until the role is known; only assistant text is kept.
  if (typeof part.messageID !== "string") return
  const piece = typeof part.text === "string" ? part.text : typeof part.delta === "string" ? part.delta : ""
  if (!piece) return
  if (!st.assistant.has(part.messageID)) {
    st.pending.set(part.messageID, ((st.pending.get(part.messageID) || "") + piece).slice(-MAX_TEXT))
    return
  }
  pushText(sessionID, piece)
}

async function server({ client, directory }) {
  return {
    "tool.execute.before": async (input) => {
      const args = (input && input.args) || {}
      const msg = beforeWrite(directory, input && input.tool, args.filePath, args.command)
      if (msg) throw new Error(msg)
    },
    "tool.execute.after": async (input, output) => {
      if (!input || !GATED_TOOLS.has(input.tool)) return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const r = await writeCheck(directory, filePath)
      if (!r) return
      if (!r.pass) throw new Error(r.block)
      if (output) output.output = appendText(output.output, r.output)
    },
    event: async ({ event }) => {
      if (!event || typeof event.type !== "string") return
      const props = event.properties || {}
      const sessionID = props.sessionID
      if (!sessionID) return
      if (event.type === "message.updated" && props.info) {
        const st = stateFor(sessionID)
        const id = typeof props.info.id === "string" ? props.info.id : null
        if (props.info.role === "assistant" && id) {
          st.assistant.add(id)
          const queued = st.pending.get(id)
          if (queued) {
            pushText(sessionID, queued)
            st.pending.delete(id)
          }
        } else if (id) {
          st.assistant.delete(id)
          st.pending.delete(id)
        }
      } else if (event.type === "message.part.updated") {
        observePart(sessionID, props.part)
      } else if (event.type === "session.idle") {
        const canPrompt = !!(client && client.session && typeof client.session.prompt === "function")
        await onIdle({
          directory,
          sessionID,
          canPrompt,
          prompt: async (sid, text) => {
            try {
              await client.session.prompt({ path: { id: sid }, body: { parts: [{ type: "text", text }] } })
              return true
            } catch {
              return false
            }
          },
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
    await ctx.tool.hook("execute.before", async (event) => {
      if (!event) return
      const input = event.input && typeof event.input === "object" ? event.input : {}
      const msg = beforeWrite(directory, event.tool, input.filePath, input.command)
      if (msg) throw new Error(msg)
    })
  )
  registrations.push(
    await ctx.tool.hook("execute.after", async (event) => {
      if (!event || !GATED_TOOLS.has(event.tool)) return
      if (event.status !== "completed") return
      const input = event.input
      const filePath = input && typeof input === "object" && typeof input.filePath === "string" ? input.filePath : null
      const r = await writeCheck(directory, filePath)
      if (!r) return
      if (!r.pass) throw new Error(r.block)
      appendV2Result(event, r.output)
    })
  )
  const canPrompt = !!(ctx.session && typeof ctx.session.prompt === "function")
  const controller = new AbortController()
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          if (!event || typeof event.type !== "string") continue
          const data = event.data && typeof event.data === "object" ? event.data : event.properties && typeof event.properties === "object" ? event.properties : {}
          const sessionID = typeof data.sessionID === "string" ? data.sessionID : null
          if (!sessionID) continue
          if ((event.type === "session.text.delta" || event.type === "session.next.text.delta") && typeof data.delta === "string") {
            if (typeof data.assistantMessageID === "string" || typeof data.messageID === "string") pushText(sessionID, data.delta)
          } else if (event.type === "session.status" && data.status && data.status.type === "idle") {
            await onIdle({
              directory,
              sessionID,
              canPrompt,
              prompt: async (sid, text) => {
                try {
                  await ctx.session.prompt({ sessionID: sid, text })
                  return true
                } catch {
                  return false
                }
              },
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
