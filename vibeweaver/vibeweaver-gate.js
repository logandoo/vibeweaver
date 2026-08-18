import { execFileSync } from "node:child_process"
import { existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs"
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
    if (!existsSync(path.join(root, STATE_DIR))) mkdirSync(path.join(root, STATE_DIR), { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(st))
    renameSync(tmp, p)
    const run = st.ops.slice(-STALL_RUN)
    if (run.length < STALL_RUN) return null
    const sameFile = run.every((o) => o.f === run[0].f)
    const noNewPass = run[0].p === run[run.length - 1].p
    if (sameFile && noNewPass) {
      return `STALL observed (machine-counted): "${run[0].f}" modified ${STALL_RUN}x with no new "iter N PASS" entry in tests/verification_log.md in between — COV-7 stall=3x is likely reached. Do not retry the same direction: parameterize (finite candidate set + cheapest refuting test) or shift the abstraction/strategy — TESTING_PROTOCOLS.md §A4.10.`
    }
    return null
  } catch {
    return null
  }
}

function blockMessage(root, result) {
  const lines = [
    "GATE-BLOCKED (vibeweaver physical gate): the task cannot be declared complete — verification evidence is missing or falsified:",
    ...result.blocking.map((m) => "- " + m),
  ]
  if (result.warnings.length) {
    lines.push("Non-blocking structure warnings (fix before the final [Verification Gate] line):")
    lines.push(...result.warnings.map((m) => "- " + m))
  } else {
    lines.push("No structure warnings.")
  }
  if (result.inline) {
    lines.push("tests/assert_artifacts.py is missing — create it from the canonical block in vibeweaver SKILL.md (A4.4.1).")
  } else if (result.attempts) {
    lines.push("assert_artifacts.py flag attempts: " + result.attempts.join(" "))
  }
  lines.push("This gate is re-checkable, not a dead stop: fix the artifacts, then your next write/edit re-runs it automatically. If the failure is legitimately out of scope, set VIBEWEAVER_GATE=off or escalate to the user.")
  return lines.join("\n")
}

export const VibeweaverGate = async ({ client, directory }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (!GATED_TOOLS.has(input.tool)) return
      if (process.env.VIBEWEAVER_GATE === "off") return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
      if (!root) return
      const result = checkGate(root)
      if (result && result.blocking.length) {
        throw new Error(blockMessage(root, result))
      }
      if (result && result.warnings.length) {
        const note = "[GATE-WARNING (vibeweaver)] non-blocking: " + result.warnings.join("; ") + " — fix before the final [Verification Gate] line."
        output.output = (output.output ? output.output + "\n" : "") + note
      }
      const stall = stallObservation(root, filePath || "(unknown file)")
      if (stall) {
        output.output = (output.output ? output.output + "\n" : "") + "[GATE-WARNING (vibeweaver-stall)] " + stall
      }
    },
    event: async ({ event }) => {
      if (!event || event.type !== "session.idle") return
      if (process.env.VIBEWEAVER_GATE === "off") return
      const root = findProjectRoot([directory])
      if (!root) return
      const result = checkGate(root)
      if (result && result.blocking.length) {
        try {
          await client.app.log({
            body: {
              service: "vibeweaver-gate",
              level: "warn",
              message: "Session idle with RED verification gate",
              extra: { blocking: result.blocking },
            },
          })
        } catch {
          // logging must never crash the plugin
        }
      }
    },
  }
}
