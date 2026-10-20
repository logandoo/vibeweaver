// mini_gate_test.mjs — executable acceptance for vibeweaver-mini-gate.
//
// RED-first harness: run before the plugin exists; it must fail with
// "plugin module missing". After implementation, it exercises the real v1
// and v2 hooks against a fake project whose vw_check.py toggles pass/fail.
//
// Usage: node tests/mini_gate_test.mjs
// Exit 0 only when every check passes.

import { execFileSync } from "node:child_process"
import { appendFileSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import { pathToFileURL } from "node:url"
import path from "node:path"

const PLUGIN = path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "vibeweaver-mini-gate.js")
const FAKE_CHECKER = `# mini checker contract: vw_test_hashes
import pathlib, sys
state = pathlib.Path(".state").read_text().strip()
if state == "pass":
    print("ALL CHECKS PASS")
    sys.exit(0)
if state == "silent":
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

async function v1Write(hooks, dir, rel = "solution.py") {
  const output = { output: "" }
  try {
    await hooks["tool.execute.after"](
      { tool: "write", args: { filePath: path.join(dir, rel) } },
      output
    )
    return { threw: false, output: output.output }
  } catch (e) {
    return { threw: true, message: String((e && e.message) || e), output: output.output }
  }
}

async function v1Feed(hooks, sessionID, text, messageID = "m1") {
  await hooks.event({
    event: { type: "message.updated", properties: { sessionID, info: { id: messageID, role: "assistant" } } },
  })
  await hooks.event({
    event: {
      type: "message.part.updated",
      properties: { sessionID, part: { type: "text", messageID, text } },
    },
  })
}
async function v1Before(hooks, tool, args) {
  try {
    await hooks["tool.execute.before"]({ tool, args })
    return null
  } catch (e) {
    return String((e && e.message) || e)
  }
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

async function v2Setup(mod, dir, prompts, withSession = true) {
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
  }
  if (withSession) {
    ctx.session = {
      prompt: async (args) => {
        prompts.push(args)
        return {}
      },
    }
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

// ---- v1: oracle guard (before hook) ----
{
  const dir = project({ state: "fail" })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const fullMarker = await v1Before(hooks, "write", { filePath: path.join(dir, "tests", "verification_log.md") })
  rec("v1 before blocks tests/verification_log.md", !!fullMarker && /disable the mini gate/.test(fullMarker), fullMarker || "no block")
  const checkerWrite = await v1Before(hooks, "edit", { filePath: path.join(dir, "vw_check.py") })
  rec("v1 before blocks checker writes", !!checkerWrite && /read-only/.test(checkerWrite), checkerWrite || "no block")
  const bashWrite = await v1Before(hooks, "bash", { command: "echo x > vw_check.py" })
  rec("v1 before blocks bash redirection into the checker", !!bashWrite && /read-only/.test(bashWrite), bashWrite || "no block")
  const bashRun = await v1Before(hooks, "bash", { command: "python3 vw_check.py" })
  rec("v1 before allows running the checker", bashRun === null, bashRun || "")
  const outside = await v1Before(hooks, "write", { filePath: path.join(os.tmpdir(), "outside.py") })
  rec("v1 outside-project write is a no-op", outside === null, outside || "")
  const quoted = await v1Before(hooks, "bash", { command: 'echo x > "vw_check.py"' })
  rec("v1 before blocks quoted bash redirection", !!quoted && /read-only/.test(quoted), quoted || "no block")
  const upperBash = await v1Before(hooks, "bash", { command: "echo x > VW_CHECK.PY" })
  rec("v1 before blocks case-variant bash redirection", !!upperBash && /read-only/.test(upperBash), upperBash || "no block")
  const globBash = await v1Before(hooks, "bash", { command: "rm -f .vw_*" })
  rec("v1 before blocks .vw_* glob deletion", !!globBash && /read-only/.test(globBash), globBash || "no block")
  const globWide = await v1Before(hooks, "bash", { command: "rm -f .vw*" })
  rec("v1 before blocks .vw* glob deletion", !!globWide && /read-only/.test(globWide), globWide || "no block")
  const runRedirect = await v1Before(hooks, "bash", { command: "python3 vw_check.py 2>&1" })
  rec("v1 before allows a checker run with 2>&1", runRedirect === null, runRedirect || "")
  for (const [label, cmd] of [
    ["tee", "printf x | tee vw_check.py"],
    ["1>", "printf x 1> vw_check.py"],
    ["2>", "printf x 2> vw_check.py"],
    [">&file", "printf x >& vw_check.py"],
  ]) {
    const blocked = await v1Before(hooks, "bash", { command: cmd })
    rec(`v1 before blocks ${label} into the checker`, !!blocked && /read-only/.test(blocked), blocked || "no block")
  }
  if (process.platform === "darwin" || process.platform === "win32") {
    const upperChecker = await v1Before(hooks, "write", { filePath: path.join(dir, "VW_CHECK.PY") })
    rec("v1 case-insensitive checker path is protected", !!upperChecker && /read-only/.test(upperChecker), upperChecker || "no block")
    const upperFull = await v1Before(hooks, "write", { filePath: path.join(dir, "TESTS", "VERIFICATION_LOG.MD") })
    rec("v1 case-insensitive full marker is protected", !!upperFull && /disable the mini gate/.test(upperFull), upperFull || "no block")
  }
}

// ---- v1: missing/silent checker, edit, and no-state ----
{
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-miss-"))
  cleanups.push(dir)
  writeFileSync(path.join(dir, ".vw_test_hashes.json"), "{}")
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const r = await v1Write(hooks, dir)
  rec("missing checker fails closed", r.threw && /CHECKER MISSING/.test(r.message), r.message)
}
{
  const dir = project({ state: "silent" })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const r = await v1Write(hooks, dir)
  rec("exit 0 without ALL CHECKS PASS is blocked", r.threw && /WITHOUT ALL CHECKS PASS/.test(r.message), r.message)
}
{
  const dir = project({ state: "fail" })
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  let threw = false
  let msg = ""
  try {
    await hooks["tool.execute.after"]({ tool: "edit", args: { filePath: path.join(dir, "solution.py") } }, { output: "" })
  } catch (e) {
    threw = true
    msg = String((e && e.message) || e)
  }
  rec("edit is gated like write", threw && /CHECKER FAILED/.test(msg), msg)
}
{
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-timeout-"))
  cleanups.push(dir)
  writeFileSync(
    path.join(dir, "vw_check.py"),
    "# vw_test_hashes\nimport time\ntime.sleep(5)\nprint('ALL CHECKS PASS')\n"
  )
  process.env.VIBEWEAVER_MINI_TIMEOUT_MS = "200"
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const r = await v1Write(hooks, dir)
  delete process.env.VIBEWEAVER_MINI_TIMEOUT_MS
  rec("checker timeout is reported distinctly", r.threw && /TIMEOUT/.test(r.message), r.message)
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
  await v1Idle(hooks, "s-fail")
  rec("repeat idle does not re-fire on consumed text", prompts.length === 1, `prompts=${prompts.length}`)

  await hooks.event({ event: { type: "message.updated", properties: { sessionID: "s-user", info: { id: "u1", role: "user" } } } })
  await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "s-user", part: { type: "text", messageID: "u1", text: "Please complete the login page." } } } })
  await v1Idle(hooks, "s-user")
  rec("first-turn user text is not a completion claim", prompts.length === 1, `prompts=${prompts.length}`)

  await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "s-rev", part: { type: "text", messageID: "m9", text: "Done." } } } })
  await hooks.event({ event: { type: "message.updated", properties: { sessionID: "s-rev", info: { id: "m9", role: "assistant" } } } })
  await v1Idle(hooks, "s-rev")
  rec("part-before-role order is buffered and claims", prompts.length === 2, `prompts=${prompts.length}`)

  setState(dir, "pass")
  await v1Feed(hooks, "s-pass", "All done.")
  await v1Idle(hooks, "s-pass")
  rec("v1 idle/done + green checker stays silent", prompts.length === 2, `prompts=${prompts.length}`)

  await v1Feed(hooks, "s-nodone", "Still fixing the second assertion.")
  await v1Idle(hooks, "s-nodone")
  rec("v1 idle/non-done stays silent", prompts.length === 2, `prompts=${prompts.length}`)

  setState(dir, "fail")
  for (let i = 0; i < 3; i++) {
    await v1Feed(hooks, "s-budget", "Done.")
    await v1Idle(hooks, "s-budget")
  }
  rec("v1 prompt budget = 2/session", prompts.length === 4, `prompts=${prompts.length} (2 earlier + 2 budget)`)
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

  mkdirSync(path.join(full, "sub"), { recursive: true })
  writeFileSync(path.join(full, "sub", "vw_check.py"), FAKE_CHECKER)
  const r3 = await v1Write(hooks2, full, "sub/x.py")
  rec("nested mini marker does not capture a full project", !r3.threw, r3.message || "")
}

// ---- v1: script/check.sh fallback (Unix) ----
if (process.platform !== "win32") {
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-sh-"))
  cleanups.push(dir)
  mkdirSync(path.join(dir, "script"))
  mkdirSync(path.join(dir, "scripts"))
  writeFileSync(path.join(dir, "script", "check.sh"), "#!/bin/sh\n# vw_check wrapper\necho 'ALL CHECKS PASS'\n")
  writeFileSync(path.join(dir, "scripts", "vw_check.py"), FAKE_CHECKER)
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const r = await v1Write(hooks, dir)
  rec("script/check.sh fallback runs when vw_check.py is absent", !r.threw && /ALL CHECKS PASS/.test(r.output), r.output || r.message)
  const protectedCheck = await v1Before(hooks, "write", { filePath: path.join(dir, "scripts", "vw_check.py") })
  rec("fallback checker path is read-only", !!protectedCheck && /read-only/.test(protectedCheck), protectedCheck || "no block")
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
  rec("v2 registers execute.before/after", typeof handlers["execute.before"] === "function" && typeof handlers["execute.after"] === "function", "")

  let beforeMsg = null
  try {
    await handlers["execute.before"]({ tool: "write", input: { filePath: path.join(dir, "vw_check.py") } })
  } catch (e) {
    beforeMsg = String((e && e.message) || e)
  }
  rec("v2 before blocks checker writes", !!beforeMsg && /read-only/.test(beforeMsg), beforeMsg || "no block")

  let threw = false
  let msg = ""
  try {
    await handlers["execute.after"]({
      tool: "write",
      status: "completed",
      input: { filePath: path.join(dir, "solution.py") },
      result: { content: "wrote file" },
    })
  } catch (e) {
    threw = true
    msg = String((e && e.message) || e)
  }
  rec("v2 write/fail throws", threw && /CHECKER FAILED/.test(msg), msg)

  setState(dir, "pass")
  let ok = true
  msg = ""
  const passResult = { content: "wrote file" }
  try {
    await handlers["execute.after"]({
      tool: "write",
      status: "completed",
      input: { filePath: path.join(dir, "solution.py") },
      result: passResult,
    })
  } catch (e) {
    ok = false
    msg = String((e && e.message) || e)
  }
  rec("v2 write/pass does not throw", ok, msg)
  rec("v2 pass appends the checker line to content", /ALL CHECKS PASS/.test(String(passResult.content)) && /wrote file/.test(String(passResult.content)), String(passResult.content))

  setState(dir, "fail")
  bus.push({ type: "session.text.delta", data: { sessionID: "v2s", assistantMessageID: "m1", delta: "Done." } })
  bus.push({ type: "session.status", data: { sessionID: "v2s", status: { type: "idle" } } })
  await sleep(250)
  rec("v2 idle/done + red checker prompts", prompts.length === 1, `prompts=${prompts.length}`)
  if (typeof dispose === "function") await dispose()
}

// ---- v2: no session.prompt means the idle challenge is inert, write gate still works ----
{
  const dir = project({ state: "fail" })
  const { handlers, bus, dispose } = await v2Setup(mod, dir, [], false)
  bus.push({ type: "session.text.delta", data: { sessionID: "v2n", assistantMessageID: "m1", delta: "Done." } })
  bus.push({ type: "session.status", data: { sessionID: "v2n", status: { type: "idle" } } })
  await sleep(250)
  rec("v2 without session.prompt: no crash, no prompt", typeof handlers["execute.after"] === "function", "write gate only")
  if (typeof dispose === "function") await dispose()
}

// ---- real vw_check.py integration (project's own pytest is the oracle) ----
{
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-real-"))
  cleanups.push(dir)
  copyFileSync(path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "scripts", "vw_check.py"), path.join(dir, "vw_check.py"))
  writeFileSync(path.join(dir, "calc.py"), "def add(a, b):\n    return 5\n")
  writeFileSync(path.join(dir, "test_calc.py"), "from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n")
  writeFileSync(path.join(dir, "conftest.py"), "def pytest_configure(config):\n    pass\n")
  const prevPy = process.env.VIBEWEAVER_MINI_PYTHON
  process.env.VIBEWEAVER_MINI_PYTHON = process.platform === "win32" ? "python" : "python3"
  const { client } = v1Client()
  const hooks = await mod.default.server({ client, directory: dir })
  const bad = await v1Write(hooks, dir)
  rec("real vw_check.py: failing pytest blocks with the repair packet", bad.threw && /FAILED|assert/i.test(bad.message), bad.message)
  const stPath = path.join(dir, ".vw_loop_state.json")
  const st = existsSync(stPath) ? JSON.parse(readFileSync(stPath, "utf8")) : {}
  rec("gate run marks seen without cap/stall", st.seen === true && !st.runs && !st.same_fail, JSON.stringify(st))
  writeFileSync(stPath, JSON.stringify({ runs: 2, same_fail: 2, sig: "seed" }))
  writeFileSync(path.join(dir, "calc.py"), "def add(a, b):\n    return 4  # fixed\n")
  const good = await v1Write(hooks, dir)
  rec("real vw_check.py: fixed code reaches ALL CHECKS PASS", !good.threw && /ALL CHECKS PASS/.test(good.output), good.output || good.message)
  const stPass = JSON.parse(readFileSync(stPath, "utf8"))
  rec("gate pass resets cap/stall but keeps seen", stPass.seen === true && (stPass.runs || 0) === 0 && (stPass.same_fail || 0) === 0, JSON.stringify(stPass))
  appendFileSync(path.join(dir, "conftest.py"), "\n# changed pytest config\n")
  const tampered = await v1Write(hooks, dir)
  rec("real vw_check.py: conftest change hits the hash guard", tampered.threw && /TEST SET CHANGED/.test(tampered.message), tampered.message)
  rec("test-change hint is followable", /--test-change/.test(tampered.message) && !/tests\/verification_log\.md/.test(tampered.message), tampered.message)
  if (prevPy === undefined) delete process.env.VIBEWEAVER_MINI_PYTHON
  else process.env.VIBEWEAVER_MINI_PYTHON = prevPy
}

// ---- nested pytest config is part of the hash set ----
{
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-nested-"))
  cleanups.push(dir)
  copyFileSync(path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "scripts", "vw_check.py"), path.join(dir, "vw_check.py"))
  mkdirSync(path.join(dir, "tests"))
  writeFileSync(path.join(dir, "tests", "test_calc.py"), "def test_add():\n    assert 5 == 4\n")
  writeFileSync(path.join(dir, "tests", "conftest.py"), "def pytest_configure(config):\n    pass\n")
  const py = process.platform === "win32" ? "python" : "python3"
  const run = () => {
    try {
      return { status: 0, out: execFileSync(py, ["vw_check.py"], { cwd: dir, encoding: "utf8", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } }) }
    } catch (e) {
      return { status: e.status ?? -1, out: `${e.stdout || ""}${e.stderr || ""}` }
    }
  }
  run()
  const h = JSON.parse(readFileSync(path.join(dir, ".vw_test_hashes.json"), "utf8"))
  rec("nested tests/conftest.py is hashed", Object.prototype.hasOwnProperty.call(h, "tests/conftest.py"), Object.keys(h).join(", "))
  appendFileSync(path.join(dir, "tests", "conftest.py"), "\n# changed\n")
  const second = run()
  rec("nested conftest change refuses to run", second.status !== 0 && /TEST SET CHANGED/.test(second.out), second.out.slice(-300))
}

// ---- npm runner: the tests it runs are hashed (Unix) ----
if (process.platform !== "win32") {
  const dir = mkdtempSync(path.join(os.tmpdir(), "vw-mini-npm-"))
  cleanups.push(dir)
  copyFileSync(path.resolve(import.meta.dirname, "..", "vibeweaver-mini", "scripts", "vw_check.py"), path.join(dir, "vw_check.py"))
  writeFileSync(path.join(dir, "package.json"), JSON.stringify({ scripts: { test: "node --test" } }, null, 1))
  mkdirSync(path.join(dir, "test"))
  writeFileSync(path.join(dir, "test", "foo.js"), "const assert = require('node:assert')\nassert.equal(1, 2)\n")
  const py = "python3"
  const run = () => {
    try {
      return { status: 0, out: execFileSync(py, ["vw_check.py"], { cwd: dir, encoding: "utf8", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } }) }
    } catch (e) {
      return { status: e.status ?? -1, out: `${e.stdout || ""}${e.stderr || ""}` }
    }
  }
  run()
  const h = JSON.parse(readFileSync(path.join(dir, ".vw_test_hashes.json"), "utf8"))
  rec("npm test files are hashed", Object.prototype.hasOwnProperty.call(h, "test/foo.js"), Object.keys(h).join(", "))
  writeFileSync(path.join(dir, "test", "foo.js"), "const assert = require('node:assert')\nassert.equal(1, 1)\n")
  const second = run()
  rec("npm test edit refuses to run", second.status !== 0 && /TEST SET CHANGED/.test(second.out), second.out.slice(-300))
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

  const badProj = mkdtempSync(path.join(os.tmpdir(), "vw-mini-bad-"))
  cleanups.push(badProj)
  writeFileSync(path.join(badProj, "vw_check.py"), "print('ALL CHECKS PASS')\n")
  let refused = false
  try {
    execFileSync("sh", [path.join(miniDir, "scripts", "setup_project.sh"), badProj], { stdio: "pipe" })
  } catch {
    refused = true
  }
  rec("setup_project.sh refuses an unrelated vw_check.py", refused, "exit non-zero")
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
