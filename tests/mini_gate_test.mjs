// mini_gate_test.mjs — executable acceptance for vibeweaver-mini-gate.
//
// RED-first harness: run before the plugin exists; it must fail with
// "plugin module missing". After implementation, it exercises the real v1
// and v2 hooks against a fake project whose vw_check.py toggles pass/fail.
//
// Usage: node tests/mini_gate_test.mjs
// Exit 0 only when every check passes.

import { execFileSync } from "node:child_process"
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import { pathToFileURL } from "node:url"
import path from "node:path"

const PLUGIN = path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "vibeweaver-mini-gate.js")
const FAKE_CHECKER = `import pathlib, sys
state = pathlib.Path(".state").read_text().strip()
if state == "pass":
    print("ALL CHECKS PASS")
    sys.exit(0)
print("FAIL: expected 4, got 3")
sys.exit(1)
`

let count = 0
let failures = 0
const failed = []
function rec(name, ok, detail) {
  count++
  if (!ok) {
    failures++
    failed.push(name)
  }
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const cleanups = []

function project({ state = "fail", mini = true, full = false } = {}) {
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-gate-"))
  cleanups.push(dir)
  if (mini) writeFileSync(path.join(dir, "vw_check.py"), FAKE_CHECKER)
  writeFileSync(path.join(dir, ".state"), state)
  writeFileSync(path.join(dir, "solution.py"), "def solve():\n    return 3\n")
  if (full) {
    mkdirSync(path.join(dir, "tests"), { recursive: true })
    writeFileSync(path.join(dir, "tests", "verification_log.md"), "- iter 1 PASS: fixture\n")
    writeFileSync(path.join(dir, "tests", "acceptance.md"), "> cap=5  stall=3x\n\n1. fixture\n")
  }
  return dir
}

function setState(dir, state) {
  writeFileSync(path.join(dir, ".state"), state)
}

function v1Client() {
  const prompts = []
  const client = {
    session: {
      prompt: async (args) => {
        prompts.push(args)
        return {}
      },
    },
  }
  return { client, prompts }
}

async function v1Write(hooks, dir) {
  const output = { output: "" }
  try {
    await hooks["tool.execute.after"](
      { tool: "write", args: { filePath: path.join(dir, "solution.py") } },
      output
    )
    return { threw: false, output: output.output }
  } catch (e) {
    return { threw: true, message: String((e && e.message) || e), output: output.output }
  }
}

async function v1Feed(hooks, sessionID, text) {
  await hooks.event({
    event: {
      type: "message.part.updated",
      properties: { sessionID, part: { type: "text", text, role: "assistant" } },
    },
  })
}
async function v1Idle(hooks, sessionID) {
  await hooks.event({ event: { type: "session.idle", properties: { sessionID } } })
}

function makeV2Bus() {
  const q = []
  let wake = null
  return {
    push(e) {
      q.push(e)
      if (wake) {
        const w = wake
        wake = null
        w()
      }
    },
    subscribe() {
      return {
        [Symbol.asyncIterator]() {
          return this
        },
        next() {
          if (q.length) return Promise.resolve({ value: q.shift(), done: false })
          return new Promise((resolve) => {
            wake = () => resolve({ value: q.shift(), done: false })
          })
        },
        return() {
          return Promise.resolve({ done: true })
        },
      }
    },
  }
}

async function v2Setup(mod, dir, prompts) {
  const handlers = {}
  const bus = makeV2Bus()
  const ctx = {
    location: { directory: dir },
    tool: {
      hook: async (name, fn) => {
        handlers[name] = fn
        return { dispose() {} }
      },
    },
    event: { subscribe: () => bus.subscribe() },
    session: {
      prompt: async (args) => {
        prompts.push(args)
        return {}
      },
    },
  }
  const dispose = await mod.default.setup(ctx)
  return { handlers, bus, dispose }
}

// ---- load (RED before the plugin exists) ----
const mod = await import(pathToFileURL(PLUGIN).href).catch(() => null)
rec("plugin module loads", !!mod, mod ? PLUGIN : `missing: ${PLUGIN}`)

if (!mod) {
  console.log(`\nRESULT: ${count - failures}/${count} passed, ${failures} failed (expected RED: plugin not written yet)`)
  process.exit(1)
}

rec("default export is { id, server, setup }", !!mod.default && typeof mod.default.server === "function" && typeof mod.default.setup === "function", "")
rec("plugin id", mod.default.id === "vibeweaver-mini-gate", String(mod.default.id))

// ---- v1: write hook ----
{
  const dir = project({ state: "fail" })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const bad = await v1Write(hooks, dir)
  rec("v1 write/fail throws", bad.threw, bad.message || "no throw")
  rec("v1 write/fail carries repair packet", /CHECKER FAILED/.test(bad.message) && /expected 4, got 3/.test(bad.message), bad.message)

  setState(dir, "pass")
  const good = await v1Write(hooks, dir)
  rec("v1 write/pass does not throw", !good.threw, good.message || "")
  rec("v1 write/pass surfaces ALL CHECKS PASS", /ALL CHECKS PASS/.test(good.output), good.output)
}

// ---- v1: completion claims ----
{
  const dir = project({ state: "fail" })
  const { client, prompts } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })

  await v1Feed(hooks, "s-fail", "All done.")
  await v1Idle(hooks, "s-fail")
  rec("v1 idle/done + red checker prompts once", prompts.length === 1, `prompts=${prompts.length}`)
  rec("v1 corrective text names the checker flag", /ALL CHECKS PASS/.test(JSON.stringify(prompts[0] || {})), JSON.stringify(prompts[0] || {}))

  setState(dir, "pass")
  await v1Feed(hooks, "s-pass", "All done.")
  await v1Idle(hooks, "s-pass")
  rec("v1 idle/done + green checker stays silent", prompts.length === 1, `prompts=${prompts.length}`)

  await v1Feed(hooks, "s-nodone", "Still fixing the second assertion.")
  await v1Idle(hooks, "s-nodone")
  rec("v1 idle/non-done stays silent", prompts.length === 1, `prompts=${prompts.length}`)

  setState(dir, "fail")
  for (let i = 0; i < 3; i++) {
    await v1Feed(hooks, "s-budget", "Done.")
    await v1Idle(hooks, "s-budget")
  }
  rec("v1 prompt budget = 2/session", prompts.length === 3, `prompts=${prompts.length} (1 earlier + 2 budget)`)
}

// ---- v1: non-mini and full-skill projects are untouched ----
{
  const nonMini = project({ mini: false })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: nonMini })
  const r = await v1Write(hooks, nonMini)
  rec("v1 non-mini project is a no-op", !r.threw, r.message || "")

  const full = project({ full: true })
  const hooks2 = await mod.default.server({ client, directory: full })
  const r2 = await v1Write(hooks2, full)
  rec("v1 full-skill project is a no-op", !r2.threw, r2.message || "")
}

// ---- v1: disable switch ----
{
  const dir = project({ state: "fail" })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  process.env.VIBEWEAVER_MINI_GATE = "off"
  const r = await v1Write(hooks, dir)
  delete process.env.VIBEWEAVER_MINI_GATE
  rec("VIBEWEAVER_MINI_GATE=off disables the hook", !r.threw, r.message || "")
}

// ---- v2: setup + hooks ----
{
  const dir = project({ state: "fail" })
  const prompts = []
  const { handlers, bus, dispose } = await v2Setup(mod, dir, prompts)
  rec("v2 registers execute.after", typeof handlers["execute.after"] === "function", "")

  let threw = false
  let msg = ""
  try {
    await handlers["execute.after"]({
      tool: "write",
      status: "completed",
      input: { filePath: path.join(dir, "solution.py") },
      result: {},
    })
  } catch (e) {
    threw = true
    msg = String((e && e.message) || e)
  }
  rec("v2 write/fail throws", threw && /CHECKER FAILED/.test(msg), msg)

  setState(dir, "pass")
  let ok = true
  msg = ""
  try {
    await handlers["execute.after"]({
      tool: "write",
      status: "completed",
      input: { filePath: path.join(dir, "solution.py") },
      result: {},
    })
  } catch (e) {
    ok = false
    msg = String((e && e.message) || e)
  }
  rec("v2 write/pass does not throw", ok, msg)

  setState(dir, "fail")
  bus.push({ type: "session.text.delta", data: { sessionID: "v2s", assistantMessageID: "m1", delta: "Done." } })
  bus.push({ type: "session.status", data: { sessionID: "v2s", status: { type: "idle" } } })
  await sleep(250)
  rec("v2 idle/done + red checker prompts", prompts.length === 1, `prompts=${prompts.length}`)
  if (typeof dispose === "function") await dispose()
}

// ---- real vw_check.py integration (project's own pytest is the oracle) ----
{
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-real-"))
  cleanups.push(dir)
  copyFileSync(path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "scripts", "vw_check.py"), path.join(dir, "vw_check.py"))
  writeFileSync(path.join(dir, "calc.py"), "def add(a, b):\n    return 5\n")
  writeFileSync(path.join(dir, "test_calc.py"), "from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n")
  const prevPy = process.env.VIBEWEAVER_MINI_PYTHON
  process.env.VIBEWEAVER_MINI_PYTHON = process.platform === "win32" ? "python" : "python3"
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const bad = await v1Write(hooks, dir)
  rec("real vw_check.py: failing pytest blocks with the repair packet", bad.threw && /FAILED|assert/i.test(bad.message), bad.message)
  writeFileSync(path.join(dir, "calc.py"), "def add(a, b):\n    return 4\n")
  const good = await v1Write(hooks, dir)
  rec("real vw_check.py: fixed code reaches ALL CHECKS PASS", !good.threw && /ALL CHECKS PASS/.test(good.output), good.output || good.message)
  if (prevPy === undefined) delete process.env.VIBEWEAVER_MINI_PYTHON
  else process.env.VIBEWEAVER_MINI_PYTHON = prevPy
}

// ---- installers (Unix; Windows is covered by the CI matrix's .bat path) ----
if (process.platform !== "win32") {
  const miniDir = path.resolve(import.meta.dirname, "..", "vibeweaver-mini")
  const home = mkdtempSync(path.join(os.tmpdir(), "vw-mini-home-"))
  cleanups.push(home)
  let installed = true
  try {
    execFileSync("bash", [path.join(miniDir, "install.sh")], {
      env: { ...process.env, XDG_CONFIG_HOME: home },
      stdio: "pipe",
    })
  } catch {
    installed = false
  }
  const installedPaths = [
    path.join(home, "opencode", "skills", "vibeweaver-mini", "SKILL.md"),
    path.join(home, "opencode", "skills", "vibeweaver-mini", "scripts", "vw_check.py"),
    path.join(home, "opencode", "skills", "vibeweaver-mini", "scripts", "check.sh"),
    path.join(home, "opencode", "plugins", "vibeweaver-mini-gate.js"),
  ]
  rec("install.sh installs mini skill + gate", installed && installedPaths.every(existsSync), installedPaths.map((p) => (existsSync(p) ? "ok" : p)).join(" · "))

  const proj = mkdtempSync(path.join(os.tmpdir(), "vw-mini-proj-"))
  cleanups.push(proj)
  let setupOk = true
  try {
    execFileSync("sh", [path.join(miniDir, "scripts", "setup_project.sh"), proj], { stdio: "pipe" })
  } catch {
    setupOk = false
  }
  rec("setup_project.sh installs checker markers", setupOk && existsSync(path.join(proj, "vw_check.py")) && existsSync(path.join(proj, "script", "check.sh")), proj)
}

for (const dir of cleanups) {
  try {
    rmSync(dir, { recursive: true, force: true })
  } catch {
    /* temp cleanup is best-effort */
  }
}

console.log(`\nRESULT: ${count - failures}/${count} passed, ${failures} failed`)
if (failures) {
  console.log("FAILED: " + failed.join(" · "))
  process.exit(1)
}
