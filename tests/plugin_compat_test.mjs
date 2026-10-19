// plugin_compat_test.mjs — dual-loader compatibility harness for the vibeweaver
// plugin pair (opencode v1 ↔ v2).
//
// Simulates BOTH plugin contracts against the real plugin files:
//   - v1.18.32 semantics: readV1Plugin("detect") + getLegacyPlugins fallback
//     + resolvePluginId (file-source plugins must export `id`), then
//     server(input, options) -> hooks object; hook invocation
//     ("tool.execute.before"/"tool.execute.after"/"event").
//   - v2.0.16 semantics: PluginModule schema (default export must be
//     {id, setup} or {id, effect}; excess keys tolerated), then setup(ctx)
//     with a fake Promise-plugin context (tool.hook / event.subscribe /
//     location / app / options), hook invocation with v2 event shapes.
//
// Usage: node tests/plugin_compat_test.mjs
// Exit 0 only when every check passes.

import { execFileSync } from "node:child_process"
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import { pathToFileURL } from "node:url"
import path from "node:path"

const GATE_MODULE = (() => {
  const local = path.resolve(import.meta.dirname, "..", "vibeweaver-gate.js")
  const nested = path.resolve(import.meta.dirname, "..", "vibeweaver", "vibeweaver-gate.js")
  return existsSync(local) ? local : nested
})()
const AUDIT_MODULE = (() => {
  const local = path.resolve(import.meta.dirname, "..", "vibeweaver-audit.js")
  const nested = path.resolve(import.meta.dirname, "..", "vibeweaver", "vibeweaver-audit.js")
  return existsSync(local) ? local : nested
})()
const AUDIT_CORE = (() => {
  const local = path.resolve(import.meta.dirname, "..", "scripts", "vibeweaver-audit-core.js")
  const nested = path.resolve(import.meta.dirname, "..", "vibeweaver", "scripts", "vibeweaver-audit-core.js")
  return existsSync(local) ? local : nested
})()
const TMP = path.join(os.tmpdir(), "vw-compat-test")

let failures = 0
let count = 0
function rec(name, ok, detail) {
  count++
  if (!ok) failures++
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

// ---------- v1 loader simulation (v1.18.32: packages/opencode/src/plugin/{index,shared}.ts) ----------
function isRecord(v) {
  return (typeof v === "object" && v !== null) || typeof v === "function"
}
function readV1Plugin(mod, mode = "detect") {
  const value = mod.default
  if (!isRecord(value)) {
    if (mode === "detect") return undefined
    throw new TypeError("Plugin must default export an object with server()")
  }
  if (mode === "detect" && !("id" in value) && !("server" in value) && !("tui" in value)) return undefined
  const server = "server" in value ? value.server : undefined
  const tui = "tui" in value ? value.tui : undefined
  if (server !== undefined && typeof server !== "function") throw new TypeError("invalid server export")
  if (tui !== undefined && typeof tui !== "function") throw new TypeError("invalid tui export")
  if (server !== undefined && tui !== undefined) throw new TypeError("either server() or tui(), not both")
  if (server === undefined) throw new TypeError("must default export an object with server()")
  return value
}
function getLegacyPlugins(mod) {
  const seen = new Set()
  const result = []
  for (const entry of Object.values(mod)) {
    if (seen.has(entry)) continue
    seen.add(entry)
    let plugin
    if (typeof entry === "function") plugin = entry
    else if (entry && typeof entry === "object" && "server" in entry && typeof entry.server === "function") plugin = entry.server
    if (!plugin) throw new TypeError("Plugin export is not a function")
    result.push(plugin)
  }
  return result
}
// Returns the array of hook objects the v1.18.32 loader would register.
async function loadAsV1(mod, input, spec = "file-plugin") {
  const plugin = readV1Plugin(mod, "detect")
  if (plugin) {
    // resolvePluginId: file-source plugins MUST export a non-empty id
    if (typeof plugin.id !== "string" || !plugin.id.trim()) throw new TypeError(`Path plugin ${spec} must export id`)
    return { via: "detect", hooks: [await plugin.server(input, {})] }
  }
  const out = []
  for (const server of getLegacyPlugins(mod)) out.push(await server(input, {}))
  return { via: "legacy", hooks: out }
}

// ---------- v2 loader simulation (v2.0.16: packages/core/src/config/plugin/external.ts) ----------
function decodeV2PluginModule(mod) {
  const d = mod.default
  if (!isRecord(d)) throw new Error("SchemaError: Missing key at [\"default\"]")
  if (typeof d.id !== "string" || !d.id) throw new Error("SchemaError: default.id must be a non-empty string")
  if (typeof d.setup === "function") return { kind: "promise", value: d }
  if (typeof d.effect === "function") return { kind: "effect", value: d }
  throw new Error("SchemaError: Missing key at [\"default\"][\"effect\"] / [\"default\"][\"setup\"]")
}

// ---------- fake v2 Promise-plugin context ----------
function makeEventBus() {
  const subs = []
  return {
    subscribe(opts) {
      const q = []
      let notify = null
      const sub = {
        [Symbol.asyncIterator]() {
          return this
        },
        next() {
          if (opts && opts.signal && opts.signal.aborted) return Promise.resolve({ done: true })
          if (q.length) return Promise.resolve({ value: q.shift(), done: false })
          return new Promise((res) => {
            notify = () => {
              notify = null
              if (opts && opts.signal && opts.signal.aborted) res({ done: true })
              else res({ value: q.shift(), done: false })
            }
          })
        },
        return() {
          return Promise.resolve({ done: true })
        },
        _push(e) {
          q.push(e)
          if (notify) notify()
        },
      }
      if (opts && opts.signal) opts.signal.addEventListener("abort", () => sub._push(null), { once: true })
      subs.push(sub)
      return sub
    },
    emit(e) {
      for (const s of subs) s._push(e)
    },
  }
}
function makeV2Ctx(directory) {
  const bus = makeEventBus()
  const toolHooks = { before: [], after: [] }
  const sessionCalls = { interrupt: [], prompt: [] }
  const ctx = {
    location: { directory, workspaceID: undefined, project: { id: "p1", directory, canonical: directory } },
    options: {},
    app: { name: "opencode", version: "2.0.16", channel: "stable" },
    session: {
      interrupt: async (input) => sessionCalls.interrupt.push(input),
      prompt: async (input) => sessionCalls.prompt.push(input),
    },
    tool: {
      hook: async (name, cb) => {
        if (name === "execute.before") toolHooks.before.push(cb)
        else if (name === "execute.after") toolHooks.after.push(cb)
        else throw new Error("unexpected hook " + name)
        return { dispose: async () => {} }
      },
    },
    event: { subscribe: (opts) => bus.subscribe(opts) },
  }
  return { ctx, toolHooks, bus, sessionCalls }
}

// ---------- fixtures ----------
function rmrf(p) {
  rmSync(p, { recursive: true, force: true })
}
function writeProject(root, { acceptance, log }) {
  rmrf(root)
  mkdirSync(path.join(root, "tests"), { recursive: true })
  writeFileSync(path.join(root, "tests", "acceptance.md"), acceptance)
  writeFileSync(path.join(root, "tests", "verification_log.md"), log)
}
function redProject(name) {
  const root = path.join(TMP, name)
  writeProject(root, { acceptance: "# no cap line\n", log: "# no iter entries\n" })
  return root
}
function greenProject(name) {
  const root = path.join(TMP, name)
  writeProject(root, {
    acceptance: "> cap=5  stall=3×\n\n# Acceptance\n1. criterion one\n",
    log: "# log\n\n- iter 1 PASS: all criteria (evidence: inline floor, 1/1)\n",
  })
  return root
}
function auditLatchedProject(name, latchSession) {
  const root = redProject(name)
  mkdirSync(path.join(root, ".vibeweaver"), { recursive: true })
  writeFileSync(
    path.join(root, ".vibeweaver", "audit-state.json"),
    JSON.stringify({ sessions: {}, roots: { [root]: { red: { sessionID: latchSession, ts: Date.now(), bad: 2 } } } })
  )
  return root
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ==================================================================
const gateMod = await import(pathToFileURL(GATE_MODULE))
const auditMod = await import(pathToFileURL(AUDIT_MODULE))

// ---------- A. module surface ----------
for (const [label, mod] of [["gate", gateMod], ["audit", auditMod]]) {
  const keys = Object.keys(mod)
  rec(`A1-${label}: exactly one default export`, keys.length === 1 && keys[0] === "default", `exports=[${keys.join(",")}]`)
  const d = mod.default
  rec(
    `A2-${label}: default = {id:string, server:fn, setup:fn}`,
    !!d && typeof d.id === "string" && d.id.length > 0 && typeof d.server === "function" && typeof d.setup === "function",
    d ? `id=${d.id}` : "no default"
  )
}

// ---------- B. loader decoding ----------
let gateV1, auditV1
try {
  gateV1 = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: TMP }, "vibeweaver-gate")
  rec("B1-gate: v1 loader (readV1Plugin detect + resolvePluginId) accepts module", true, `via=${gateV1.via} hooks=${gateV1.hooks.length}`)
} catch (e) {
  rec("B1-gate: v1 loader (readV1Plugin detect + resolvePluginId) accepts module", false, String(e.message || e))
}
try {
  auditV1 = await loadAsV1(auditMod, { client: { app: { log: async () => {} } }, directory: TMP }, "vibeweaver-audit")
  rec("B1-audit: v1 loader accepts module", true, `via=${auditV1.via} hooks=${auditV1.hooks.length}`)
} catch (e) {
  rec("B1-audit: v1 loader accepts module", false, String(e.message || e))
}
let gateV2def, auditV2def
try {
  gateV2def = decodeV2PluginModule(gateMod)
  rec("B2-gate: v2 PluginModule schema decodes default export", true, `kind=${gateV2def.kind}`)
} catch (e) {
  rec("B2-gate: v2 PluginModule schema decodes default export", false, String(e.message || e))
}
try {
  auditV2def = decodeV2PluginModule(auditMod)
  rec("B2-audit: v2 PluginModule schema decodes default export", true, `kind=${auditV2def.kind}`)
} catch (e) {
  rec("B2-audit: v2 PluginModule schema decodes default export", false, String(e.message || e))
}
if (gateV1) rec("B3-gate: single registration under v1 (no double fire)", gateV1.hooks.length === 1, `hooks=${gateV1.hooks.length}`)
if (auditV1) rec("B3-audit: single registration under v1 (no double fire)", auditV1.hooks.length === 1, `hooks=${auditV1.hooks.length}`)

// ---------- C. gate behavior parity ----------
const gateHooksV1 = gateV1 && gateV1.hooks[0]
if (gateHooksV1) {
  const red = redProject("gate-red-v1")
  const out = { output: "write ok" }
  let blocked = null
  try {
    await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "c1", args: { filePath: path.join(red, "src", "a.js") } }, out)
  } catch (e) {
    blocked = e
  }
  rec("C1-gate-v1: RED project write is GATE-BLOCKED (throws)", !!blocked && String(blocked.message).includes("GATE-BLOCKED"), blocked ? "threw" : "no throw")

  const out2 = { output: "write ok" }
  let blocked2 = null
  try {
    await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "c2", args: { filePath: path.join(red, "tests", "log.md") } }, out2)
  } catch (e) {
    blocked2 = e
  }
  rec("C2-gate-v1: tests/ evidence path is exempt", !blocked2, blocked2 ? String(blocked2.message).slice(0, 60) : "clean")

  const green = greenProject("gate-green-v1")
  let stallNote = ""
  for (let i = 0; i < 3; i++) {
    const o = { output: "ok" }
    await gateHooksV1["tool.execute.after"]({ tool: "edit", sessionID: "s1", callID: "c" + i, args: { filePath: path.join(green, "src", "x.js") } }, o)
    stallNote = o.output
  }
  rec("C3-gate-v1: GREEN project passes + stall observation appended after 3 same-file ops", stallNote.includes("GATE-WARNING (vibeweaver-stall)"), stallNote.slice(0, 60))

  process.env.VIBEWEAVER_GATE = "off"
  const redOff = redProject("gate-red-off-v1")
  let blockedOff = null
  try {
    await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "c9", args: { filePath: path.join(redOff, "src", "a.js") } }, { output: "" })
  } catch (e) {
    blockedOff = e
  }
  delete process.env.VIBEWEAVER_GATE
  rec("C4-gate-v1: VIBEWEAVER_GATE=off disables the gate", !blockedOff, blockedOff ? "still blocked" : "clean")
}

// gate v1 — cue-anchored memory triggers (§A7.16): editing a path that
// matches a memory topic's `triggers:` glob surfaces a one-line cue note.
{
  const cueProj = greenProject("gate-cue-v1")
  mkdirSync(path.join(cueProj, "memory"), { recursive: true })
  writeFileSync(path.join(cueProj, "memory", "fix_auth_trap.md"), [
    "---",
    "type: fix",
    "trust: ❌ Failed",
    "triggers:",
    '  - "src/auth/**"',
    "---",
    "# Fix: auth token refresh trap",
    "Refresh tokens rotate; never cache them module-level.",
  ].join("\n"))
  const outHit = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue1", args: { filePath: path.join(cueProj, "src", "auth", "refresh.ts") } }, outHit)
  rec("C5-gate-v1: trigger-matched path surfaces vibeweaver-cue note", outHit.output.includes("[GATE-WARNING (vibeweaver-cue)]") && outHit.output.includes("fix_auth_trap.md"), outHit.output.slice(0, 80))
  const outMiss = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue2", args: { filePath: path.join(cueProj, "src", "ui", "button.ts") } }, outMiss)
  rec("C5b-gate-v1: non-matching path gets no cue note", !outMiss.output.includes("vibeweaver-cue"), outMiss.output.slice(0, 60))
  const outMem = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue3", args: { filePath: path.join(cueProj, "memory", "fix_auth_trap.md") } }, outMem)
  rec("C5c-gate-v1: editing memory/ itself never self-cues", !outMem.output.includes("vibeweaver-cue"), outMem.output.slice(0, 60))
  const cueProj2 = greenProject("gate-cue-inline-v1")
  mkdirSync(path.join(cueProj2, "memory"), { recursive: true })
  writeFileSync(path.join(cueProj2, "memory", "reference_db.md"), [
    "---",
    "type: reference",
    'triggers: ["db/**", "src/repos/**"]',
    "---",
    "# Reference: db layer conventions",
  ].join("\n"))
  const outInline = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue4", args: { filePath: path.join(cueProj2, "db", "migrate.sql") } }, outInline)
  rec("C5d-gate-v1: inline-list triggers form also fires", outInline.output.includes("reference_db.md"), outInline.output.slice(0, 60))

  // RED gate still delivers the cue (delivery hoisted above the block) —
  // the task's first write, gate almost always RED, is the prime cue moment.
  const cueRed = redProject("gate-cue-red-v1")
  mkdirSync(path.join(cueRed, "memory"), { recursive: true })
  writeFileSync(path.join(cueRed, "memory", "fix_auth_trap.md"), [
    "---",
    "type: fix",
    "status: ❌",
    "triggers:",
    '  - "src/auth/**"',
    "---",
    "# Fix: auth token refresh trap",
  ].join("\n"))
  let redErr = null
  try {
    await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue5", args: { filePath: path.join(cueRed, "src", "auth", "x.ts") } }, { output: "" })
  } catch (e) {
    redErr = e
  }
  rec("C5e-gate-v1: RED gate block message still carries the cue note", !!redErr && String(redErr.message).includes("vibeweaver-cue"), redErr ? String(redErr.message).split("\n").pop().slice(0, 60) : "not blocked")

  // tests/-path writes are gate-exempt but still cue (trigger targets can
  // live under tests/ too — e.g. a trap in test infra).
  const cueTests = greenProject("gate-cue-tests-v1")
  mkdirSync(path.join(cueTests, "memory"), { recursive: true })
  writeFileSync(path.join(cueTests, "memory", "project_harness.md"), [
    "---",
    "type: project",
    'triggers: ["tests/e2e/**"]',
    "---",
    "# Harness: e2e fixtures are stateful",
  ].join("\n"))
  const outTests = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue6", args: { filePath: path.join(cueTests, "tests", "e2e", "login.spec.ts") } }, outTests)
  rec("C5f-gate-v1: tests/-path write still surfaces the cue", outTests.output.includes("project_harness.md"), outTests.output.slice(0, 60))

  // hostile glob: repeated `**/` groups are rejected by the safety cap —
  // the topic simply never cues, and the hook returns promptly.
  const cueBad = greenProject("gate-cue-redos-v1")
  mkdirSync(path.join(cueBad, "memory"), { recursive: true })
  writeFileSync(path.join(cueBad, "memory", "fix_evil.md"), [
    "---",
    "type: fix",
    "triggers:",
    '  - "**/**/**/**/**/**/**/**/**/**/zz"',
    "---",
    "# Evil: ReDoS attempt",
  ].join("\n"))
  const deep = path.join(cueBad, ...Array.from({ length: 12 }, (_, i) => `d${i}`), "x.ts")
  const outBad = { output: "ok" }
  const t0 = Date.now()
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue7", args: { filePath: deep } }, outBad)
  const elapsed = Date.now() - t0
  rec("C5g-gate-v1: >2 `**` groups rejected (no cue, no wedge)", !outBad.output.includes("vibeweaver-cue") && elapsed < 2000, `elapsed=${elapsed}ms`)

  // YAML-subset forms: scalar value, zero-indent list, trailing comment.
  const cueYaml = greenProject("gate-cue-yaml-v1")
  mkdirSync(path.join(cueYaml, "memory"), { recursive: true })
  writeFileSync(path.join(cueYaml, "memory", "reference_scalar.md"), [
    "---",
    "type: reference",
    "triggers: src/scalar/**",
    "---",
    "# Scalar form",
  ].join("\n"))
  writeFileSync(path.join(cueYaml, "memory", "reference_zeroindent.md"), [
    "---",
    "type: reference",
    "triggers:",
    '- "src/zero/**"',
    "---",
    "# Zero-indent list form",
  ].join("\n"))
  writeFileSync(path.join(cueYaml, "memory", "reference_comment.md"), [
    "---",
    "type: reference",
    "triggers:",
    '  - "src/cmt/**"  # hot path',
    '  - "src/cmt2/**"',
    "---",
    "# List item with trailing comment",
  ].join("\n"))
  const outScalar = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue8", args: { filePath: path.join(cueYaml, "src", "scalar", "a.ts") } }, outScalar)
  const outZero = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cue9", args: { filePath: path.join(cueYaml, "src", "zero", "b.ts") } }, outZero)
  const outCmt = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cueA", args: { filePath: path.join(cueYaml, "src", "cmt2", "c.ts") } }, outCmt)
  rec("C5h-gate-v1: scalar + zero-indent + trailing-comment trigger forms all fire", outScalar.output.includes("reference_scalar.md") && outZero.output.includes("reference_zeroindent.md") && outCmt.output.includes("reference_comment.md"), [outScalar.output.slice(3, 40), outZero.output.slice(3, 40), outCmt.output.slice(3, 40)].join(" | "))

  // CRLF + BOM frontmatter still cues (normalized before matching).
  const cueCrlf = greenProject("gate-cue-crlf-v1")
  mkdirSync(path.join(cueCrlf, "memory"), { recursive: true })
  writeFileSync(path.join(cueCrlf, "memory", "fix_crlf.md"), "\uFEFF---\r\ntype: fix\r\ntriggers:\r\n  - \"src/win/**\"\r\n---\r\n# CRLF topic\r\n")
  const outCrlf = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cueB", args: { filePath: path.join(cueCrlf, "src", "win", "w.ts") } }, outCrlf)
  rec("C5i-gate-v1: CRLF+BOM topic file still cues", outCrlf.output.includes("fix_crlf.md"), outCrlf.output.slice(0, 60))

  // unquoted inline list `triggers: [src/uq/**, tests/**]` must also parse
  // (both parsers share the rule; silently parsing to zero = non-delivery).
  writeFileSync(path.join(cueYaml, "memory", "reference_unquoted.md"), [
    "---",
    "type: reference",
    "triggers: [src/uq/**, tests/**]",
    "---",
    "# Unquoted inline list form",
  ].join("\n"))
  const outUq = { output: "ok" }
  await gateHooksV1["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "cueC", args: { filePath: path.join(cueYaml, "src", "uq", "d.ts") } }, outUq)
  rec("C5j-gate-v1: unquoted inline-list triggers also fire", outUq.output.includes("reference_unquoted.md"), outUq.output.slice(0, 60))

  // cue telemetry (wave19): each fire increments .vibeweaver/cue-stats.json —
  // delivery counts are the feedback for tuning glob precision later.
  const statsP = path.join(cueYaml, ".vibeweaver", "cue-stats.json")
  const stats = JSON.parse(readFileSync(statsP, "utf8"))
  rec("C5k-gate-v1: cue fires recorded in .vibeweaver/cue-stats.json", stats["reference_unquoted.md"] >= 1 && typeof stats["reference_unquoted.md"] === "number", JSON.stringify(stats).slice(0, 80))
}

// stall latch: the observer fires ONCE per stall condition (per file, per
// pass-count signature) — re-firing on every subsequent edit is alarm flood
// and trains warning-blindness. A new PASS re-arms it.
{
  const lp = greenProject("gate-stall-latch-v1")
  const outputs = []
  for (let i = 0; i < 5; i++) {
    const o = { output: "ok" }
    await gateHooksV1["tool.execute.after"]({ tool: "edit", sessionID: "s1", callID: "lp" + i, args: { filePath: path.join(lp, "src", "x.js") } }, o)
    outputs.push(o.output)
  }
  const fires = outputs.filter((s) => s.includes("vibeweaver-stall")).length
  rec("C6-gate-v1: stall warning fires ONCE across 5 same-file edits (latch, no flood)", fires === 1, `fires=${fires}`)
  writeFileSync(path.join(lp, "tests", "verification_log.md"), readFileSync(path.join(lp, "tests", "verification_log.md"), "utf8") + "\n- iter 2 PASS: latch reset (evidence: inline)\n")
  let last = { output: "ok" }
  for (let i = 0; i < 3; i++) {
    last = { output: "ok" }
    await gateHooksV1["tool.execute.after"]({ tool: "edit", sessionID: "s1", callID: "lpB" + i, args: { filePath: path.join(lp, "src", "x.js") } }, last)
  }
  rec("C6b-gate-v1: a new PASS re-arms the stall observer", last.output.includes("vibeweaver-stall"), last.output.slice(0, 60))
}

// gate v2
if (gateV2def) {
  const red = redProject("gate-red-v2")
  const { ctx, toolHooks } = makeV2Ctx(red)
  const cleanup = await gateV2def.value.setup(ctx)
  rec("D0-gate-v2: setup(ctx) registers execute.after hook", toolHooks.after.length === 1, `after=${toolHooks.after.length}`)
  rec("D0b-gate-v2: setup returns a cleanup function", typeof cleanup === "function", typeof cleanup)

  const ev = { tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "c1", input: { filePath: path.join(red, "src", "a.js") }, status: "completed", result: { content: "write ok" } }
  let blocked = null
  try {
    await toolHooks.after[0](ev)
  } catch (e) {
    blocked = e
  }
  rec("D1-gate-v2: RED project completed write is GATE-BLOCKED (throws)", !!blocked && String(blocked.message).includes("GATE-BLOCKED"), blocked ? "threw" : "no throw")

  const green = greenProject("gate-green-v2")
  const g2 = makeV2Ctx(green)
  await gateV2def.value.setup(g2.ctx)
  let content = ""
  for (let i = 0; i < 3; i++) {
    const e2 = { tool: "edit", sessionID: "s1", agent: "a", messageID: "m1", id: "c" + i, input: { filePath: path.join(green, "src", "x.js") }, status: "completed", result: { content: "ok" } }
    await g2.toolHooks.after[0](e2)
    content = typeof e2.result.content === "string" ? e2.result.content : JSON.stringify(e2.result.metadata || {})
  }
  rec("D2-gate-v2: GREEN project passes + stall note appended to result", content.includes("GATE-WARNING (vibeweaver-stall)"), content.slice(0, 60))

  // v2 cue delivery: a trigger-matched write surfaces the cue note through
  // appendNotesToV2Result (same channel as the stall note).
  {
    const cueV2 = greenProject("gate-cue-v2")
    mkdirSync(path.join(cueV2, "memory"), { recursive: true })
    writeFileSync(path.join(cueV2, "memory", "fix_v2trap.md"), [
      "---",
      "type: fix",
      "triggers:",
      '  - "src/api/**"',
      "---",
      "# Fix: v2 api trap",
    ].join("\n"))
    const g4 = makeV2Ctx(cueV2)
    await gateV2def.value.setup(g4.ctx)
    const evCue = { tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "cv1", input: { filePath: path.join(cueV2, "src", "api", "route.ts") }, status: "completed", result: { content: "ok" } }
    await g4.toolHooks.after[0](evCue)
    rec("D2b-gate-v2: cue note delivered through the v2 result channel", String(evCue.result.content).includes("vibeweaver-cue") && String(evCue.result.content).includes("fix_v2trap.md"), String(evCue.result.content).slice(0, 60))

    // fully-frozen event/result/metadata: notes are best-effort — the hook
    // must never throw on a landed write (phantom tool error).
    {
      const fz = greenProject("gate-frozen-v2")
      mkdirSync(path.join(fz, "memory"), { recursive: true })
      writeFileSync(path.join(fz, "memory", "fix_fz.md"), "---\ntype: fix\ntriggers:\n  - \"src/**\"\n---\n# Frozen\n")
      const g5 = makeV2Ctx(fz)
      await gateV2def.value.setup(g5.ctx)
      const frozen = Object.freeze({
        tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "fz1",
        input: Object.freeze({ filePath: path.join(fz, "src", "a.ts") }),
        status: "completed",
        result: Object.freeze({ content: "ok", metadata: Object.freeze({}) }),
      })
      let threw = null
      try {
        await g5.toolHooks.after[0](frozen)
      } catch (e) {
        threw = e
      }
      rec("D2c-gate-v2: fully-frozen event/result/metadata — hook never throws", !threw, threw ? String(threw).slice(0, 60) : "no throw")
    }
  }

  const evErr = { tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "c7", input: { filePath: path.join(red, "src", "b.js") }, status: "error", error: { message: "disk full" } }
  let blockedErr = null
  try {
    await toolHooks.after[0](evErr)
  } catch (e) {
    blockedErr = e
  }
  rec("D3-gate-v2: error-status executions are not gated (v1 parity: after fires only on success)", !blockedErr, blockedErr ? "blocked" : "clean")

  process.env.VIBEWEAVER_GATE = "off"
  const redOff = redProject("gate-red-off-v2")
  const g3 = makeV2Ctx(redOff)
  await gateV2def.value.setup(g3.ctx)
  let blockedOff = null
  try {
    await g3.toolHooks.after[0]({ tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "c9", input: { filePath: path.join(redOff, "src", "a.js") }, status: "completed", result: { content: "x" } })
  } catch (e) {
    blockedOff = e
  }
  delete process.env.VIBEWEAVER_GATE
  rec("D4-gate-v2: VIBEWEAVER_GATE=off disables the gate", !blockedOff, blockedOff ? "still blocked" : "clean")
  if (typeof cleanup === "function") await cleanup()
}

// ---------- E. audit behavior parity ----------
// The audit machine loads its latch state at factory creation — build the
// factory per fixture AFTER seeding, like the real loader does per instance.
async function newAuditV1(root) {
  const loaded = await loadAsV1(auditMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-audit")
  return loaded.hooks[0]
}
{
  const root = auditLatchedProject("audit-red-v1", "s-red")
  const auditHooksV1 = await newAuditV1(root)
  let blocked = null
  try {
    await auditHooksV1["tool.execute.before"]({ tool: "write", sessionID: "s-red", callID: "c1" }, { args: { filePath: path.join(root, "src", "a.js") } })
  } catch (e) {
    blocked = e
  }
  rec("E1-audit-v1: RED latch blocks the latching session's non-test write", !!blocked && String(blocked.message).includes("GATE-BLOCKED (vibeweaver-audit)"), blocked ? "threw" : "no throw")

  let blockedTest = null
  try {
    await auditHooksV1["tool.execute.before"]({ tool: "write", sessionID: "s-red", callID: "c2" }, { args: { filePath: path.join(root, "tests", "verification_log.md") } })
  } catch (e) {
    blockedTest = e
  }
  rec("E2-audit-v1: test-dir write stays writable under RED latch", !blockedTest, blockedTest ? "blocked" : "clean")

  const root2 = auditLatchedProject("audit-red-v1b", "s-other")
  const auditHooksV1b = await newAuditV1(root2)
  let blockedOther = null
  try {
    await auditHooksV1b["tool.execute.before"]({ tool: "write", sessionID: "s-new", callID: "c3" }, { args: { filePath: path.join(root2, "src", "a.js") } })
  } catch (e) {
    blockedOther = e
  }
  rec("E3-audit-v1: stale (other-session) latch auto-releases on write", !blockedOther, blockedOther ? "blocked" : "clean")
}

if (auditV2def) {
  const root = auditLatchedProject("audit-red-v2", "s-red")
  const { ctx, toolHooks, bus } = makeV2Ctx(root)
  const cleanup = await auditV2def.value.setup(ctx)
  rec("F0-audit-v2: setup(ctx) registers execute.before hook + cleanup", toolHooks.before.length === 1 && typeof cleanup === "function", `before=${toolHooks.before.length} cleanup=${typeof cleanup}`)

  let blocked = null
  try {
    await toolHooks.before[0]({ tool: "write", sessionID: "s-red", agent: "a", messageID: "m1", id: "c1", input: { filePath: path.join(root, "src", "a.js") } })
  } catch (e) {
    blocked = e
  }
  rec("F1-audit-v2: RED latch blocks the latching session's non-test write", !!blocked && String(blocked.message).includes("GATE-BLOCKED (vibeweaver-audit)"), blocked ? "threw" : "no throw")

  let blockedTest = null
  try {
    await toolHooks.before[0]({ tool: "write", sessionID: "s-red", agent: "a", messageID: "m1", id: "c2", input: { filePath: path.join(root, "tests", "verification_log.md") } })
  } catch (e) {
    blockedTest = e
  }
  rec("F2-audit-v2: test-dir write stays writable under RED latch", !blockedTest, blockedTest ? "blocked" : "clean")

  // v2 observation pipeline: skill + text + tool events feed the machine; idle runs the audit
  const root2 = redProject("audit-observe-v2")
  const o2 = makeV2Ctx(root2)
  await auditV2def.value.setup(o2.ctx)
  await o2.toolHooks.before[0]({ tool: "skill", sessionID: "s1", agent: "a", messageID: "m1", id: "c1", input: { name: "vibeweaver" } })
  o2.bus.emit({ type: "session.text.delta", data: { sessionID: "s1", assistantMessageID: "m1", ordinal: 0, delta: "working…\n[Verification Gate] Verifier: direct read | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  o2.bus.emit({ type: "session.status", data: { sessionID: "s1", status: { type: "idle" } } })
  await sleep(150)
  const auditFile = path.join(root2, "tests", "gate_audit.md")
  const auditState = path.join(root2, ".vibeweaver", "audit-state.json")
  const report = existsSync(auditFile) ? readFileSync(auditFile, "utf8") : ""
  const stText = existsSync(auditState) ? readFileSync(auditState, "utf8") : ""
  let redLatch = false
  try {
    const st = JSON.parse(stText)
    redLatch = !!(st.roots && st.roots[root2] && st.roots[root2].red)
  } catch {}
  rec("F3-audit-v2: v2 events feed observation; idle runs audit and writes tests/gate_audit.md", report.length > 0, `report=${report.length}B`)
  rec("F4-audit-v2: RED final audit latches the project (session-scoped)", redLatch, redLatch ? "latched" : stText.slice(0, 80))

  // Resilience (A4.9 review fix): a malformed event must not kill the v2
  // subscription — a later idle must still drive the audit. Mirror the F3
  // non-skipping setup (skill observed + full gate-line text).
  const root2b = redProject("audit-observe-v2b")
  const o2b = makeV2Ctx(root2b)
  await auditV2def.value.setup(o2b.ctx)
  await o2b.toolHooks.before[0]({ tool: "skill", sessionID: "s1", agent: "a", messageID: "m1", id: "c1", input: { name: "vibeweaver" } })
  o2b.bus.emit(new Proxy({ type: "session.status" }, { get(t, k) { if (k === "data") throw new Error("boom"); return t[k] } }))
  o2b.bus.emit({ type: "session.text.delta", data: { sessionID: "s1", assistantMessageID: "m1", ordinal: 0, delta: "working…\n[Verification Gate] Verifier: direct read | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  o2b.bus.emit({ type: "session.status", data: { sessionID: "s1", status: { type: "idle" } } })
  await sleep(150)
  rec("F4b-audit-v2: subscription survives a malformed event; later idle still audits", existsSync(path.join(root2b, "tests", "gate_audit.md")), existsSync(path.join(root2b, "tests", "gate_audit.md")) ? "audit ran" : "subscription died")

  process.env.VIBEWEAVER_AUDIT = "off"
  const root3 = auditLatchedProject("audit-red-off-v2", "s-red")
  const o3 = makeV2Ctx(root3)
  await auditV2def.value.setup(o3.ctx)
  let blockedOff = null
  try {
    await o3.toolHooks.before[0]({ tool: "write", sessionID: "s-red", agent: "a", messageID: "m1", id: "c9", input: { filePath: path.join(root3, "src", "a.js") } })
  } catch (e) {
    blockedOff = e
  }
  delete process.env.VIBEWEAVER_AUDIT
  rec("F5-audit-v2: VIBEWEAVER_AUDIT=off disables the latch block", !blockedOff, blockedOff ? "still blocked" : "clean")
  if (typeof cleanup === "function") await cleanup()
}

// ---------- G. loop-guard (degenerate-generation detection + intervention) ----------
function makeV1SpyClient() {
  const calls = { abort: [], prompt: [] }
  return {
    calls,
    client: {
      app: { log: async () => {} },
      session: {
        abort: async (opts) => calls.abort.push(opts),
        prompt: async (opts) => calls.prompt.push(opts),
      },
    },
  }
}
async function newAuditV1WithClient(root, client) {
  const loaded = await loadAsV1(auditMod, { client, directory: root }, "vibeweaver-audit")
  return loaded.hooks[0]
}
const INTRO = "Working on the feature now. Let me write the implementation step by step, starting with the module skeleton and the imports.\n"
// Feed one cumulative-updating text part, mirroring real v1 streaming.
// Pass a shared `state` object to keep one continuous buffer across calls.
async function feedCumulative(hooks, sessionID, chunks, state) {
  let text = state ? state.text : INTRO
  for (const c of chunks) {
    text += c
    await hooks.event({ event: { type: "message.part.updated", properties: { sessionID, part: { id: "t1", type: "text", text } } } })
  }
  if (state) state.text = text
}
const seqChunks = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => String(from + i) + "\n")
const letterChunks = (letters) => letters.map((l) => l + "\n")
const BLOCK = "function foo() {\n  return computeValue(x)\n}\n"

{
  // G1 — bare integer echo 1..16 triggers abort + corrective prompt (v1)
  const root = redProject("loop-g1")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", seqChunks(1, 16))
  await sleep(80)
  rec(
    "G1-loopguard-v1: integer echo 1..16 triggers abort + corrective prompt",
    calls.abort.length === 1 && calls.abort[0].path.id === "s1" && calls.prompt.length === 1 && String(calls.prompt[0].body.parts[0].text).includes("degenerated"),
    `abort=${calls.abort.length} prompt=${calls.prompt.length}`
  )
}
{
  // G2 — bijective base-26 letter echo a..n triggers (v1)
  const root = redProject("loop-g2")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", letterChunks("abcdefghijklmn".split("")))
  await sleep(80)
  rec("G2-loopguard-v1: letter echo a..n triggers interrupt", calls.abort.length === 1, `abort=${calls.abort.length}`)
}
{
  // G3 — identical code block repeated 4x triggers (v1)
  const root = redProject("loop-g3")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", [BLOCK, BLOCK, BLOCK, BLOCK])
  await sleep(80)
  rec("G3-loopguard-v1: 4x repeated code block triggers interrupt", calls.abort.length === 1, `abort=${calls.abort.length}`)
}
{
  // G3b — a 5-line stanza repeated 3x (period NOT in any fixed list) triggers (v1)
  const root = redProject("loop-g3b")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  const stanza = "if (x > 0) {\n  const y = compute(x)\n  log(y)\n  return y * 2\n}\n"
  await feedCumulative(hooks, "s1", [stanza, stanza, stanza])
  await sleep(80)
  rec("G3b-loopguard-v1: 3x repeated 5-line stanza triggers interrupt (any period)", calls.abort.length === 1, `abort=${calls.abort.length}`)
}
{
  // G4b — separator/banner lines x3 and a single code line x3 do NOT trigger; x4 of a real code line DOES (v1)
  const root = redProject("loop-g4b")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  const st = { text: "" }
  const sep = "# ============================================================\n"
  await feedCumulative(hooks, "s1", [sep, sep, sep], st)
  await sleep(60)
  const afterSep = calls.abort.length
  await feedCumulative(hooks, "s1", ["const ready = true\n", "const ready = true\n", "const ready = true\n"], st)
  await sleep(60)
  const after3 = calls.abort.length
  await feedCumulative(hooks, "s1", ["const ready = true\n"], st)
  await sleep(60)
  rec(
    "G4b-loopguard-v1: separator x3 + code line x3 clean; code line x4 triggers",
    afterSep === 0 && after3 === 0 && calls.abort.length === 1,
    `sep=${afterSep} x3=${after3} x4=${calls.abort.length}`
  )
}
{
  // G4 — numbered list with content (near-miss) does NOT trigger (v1)
  const root = redProject("loop-g4")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", ["1. alpha\n", "2. beta\n", "3. gamma\n", "4. delta\n", "5. epsilon\n", "6. zeta\n", "7. eta\n", "8. theta\n", "9. iota\n", "10. kappa\n", "11. lambda\n", "12. mu\n", "13. nu\n", "14. xi\n"])
  await sleep(80)
  rec("G4-loopguard-v1: numbered list with content does not interrupt", calls.abort.length === 0, `abort=${calls.abort.length}`)
}
{
  // G5 — a paragraph repeated only 2x does NOT trigger (v1)
  const root = redProject("loop-g5")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", [BLOCK, BLOCK])
  await sleep(80)
  rec("G5-loopguard-v1: block repeated only 2x does not interrupt", calls.abort.length === 0, `abort=${calls.abort.length}`)
}
{
  // G6 — intervention budget: 3 degeneration episodes, only 2 interrupts (v1)
  const root = redProject("loop-g6")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  await feedCumulative(hooks, "s1", seqChunks(1, 14))
  await sleep(60)
  await feedCumulative(hooks, "s1", ["Back to normal prose for a while, discussing the design and the tradeoffs involved in detail here.\n", ...letterChunks("abcdefghijklmn".split(""))])
  await sleep(60)
  await feedCumulative(hooks, "s1", ["More normal prose, enough to separate the episodes by a wide margin of regular text.\n", ...seqChunks(100, 114)])
  await sleep(60)
  rec("G6-loopguard-v1: budget caps interventions at 2 (3rd is log-only)", calls.abort.length === 2 && calls.prompt.length === 2, `abort=${calls.abort.length} prompt=${calls.prompt.length}`)
}
{
  // G7 — VIBEWEAVER_LOOPGUARD=off disables intervention (v1)
  const root = redProject("loop-g7")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  process.env.VIBEWEAVER_LOOPGUARD = "off"
  await feedCumulative(hooks, "s1", seqChunks(1, 16))
  await sleep(60)
  delete process.env.VIBEWEAVER_LOOPGUARD
  rec("G7-loopguard-v1: VIBEWEAVER_LOOPGUARD=off disables the loop-guard", calls.abort.length === 0, `abort=${calls.abort.length}`)
}
{
  // G8 — v2 path: session.text.delta sequence triggers ctx.session.interrupt + prompt
  const root = redProject("loop-g8")
  const o = makeV2Ctx(root)
  await auditV2def.value.setup(o.ctx)
  o.bus.emit({ type: "session.text.delta", data: { sessionID: "s1", assistantMessageID: "m1", ordinal: 0, delta: INTRO } })
  for (const c of seqChunks(1, 16)) {
    o.bus.emit({ type: "session.text.delta", data: { sessionID: "s1", assistantMessageID: "m1", ordinal: 0, delta: c } })
  }
  await sleep(120)
  rec(
    "G8-loopguard-v2: integer echo via text.delta triggers interrupt(continue:false) + corrective prompt",
    o.sessionCalls.interrupt.length === 1 && o.sessionCalls.interrupt[0].sessionID === "s1" && o.sessionCalls.interrupt[0].continue === false && o.sessionCalls.prompt.length === 1 && String(o.sessionCalls.prompt[0].text).includes("degenerated"),
    `interrupt=${o.sessionCalls.interrupt.length} prompt=${o.sessionCalls.prompt.length}`
  )
}

{
  // G9 — no-newline streaming repeat (char-level period): x3 clean (uniform
  // 4-copy bar), x4 fires; short sub-period super-period ("very "x40) fires;
  // JSX element x3 + punctuation-only stay clean (v1)
  const root = redProject("loop-g9")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  const sentence = "The quick brown fox jumps over the lazy dog and keeps running. "
  const st = { text: "" }
  await feedCumulative(hooks, "s1", [sentence, sentence, sentence], st)
  await sleep(60)
  const afterX3 = calls.abort.length
  await feedCumulative(hooks, "s1", [sentence], st)
  await sleep(60)
  const afterX4 = calls.abort.length
  const root2 = redProject("loop-g9b")
  const c2 = makeV1SpyClient()
  const hooks2 = await newAuditV1WithClient(root2, c2.client)
  const st2 = { text: "" }
  await feedCumulative(hooks2, "s1", ["very ".repeat(40)], st2)
  await sleep(60)
  const afterVery = c2.calls.abort.length
  const root3 = redProject("loop-g9c")
  const c3 = makeV1SpyClient()
  const hooks3 = await newAuditV1WithClient(root3, c3.client)
  const st3 = { text: "" }
  const div = `<div class="card"><span>hello world</span></div>`
  await feedCumulative(hooks3, "s1", [div, div, div], st3)
  await sleep(60)
  const punct = "=".repeat(200)
  const root4 = redProject("loop-g9d")
  const c4 = makeV1SpyClient()
  const hooks4 = await newAuditV1WithClient(root4, c4.client)
  const st4 = { text: "" }
  await feedCumulative(hooks4, "s1", [punct, punct, punct, punct], st4)
  await sleep(60)
  rec(
    "G9-loopguard-v1: no-newline x3 clean, x4 fires, short-token super-period fires, JSX x3 + punctuation clean",
    afterX3 === 0 && afterX4 === 1 && afterVery === 1 && c3.calls.abort.length === 0 && c4.calls.abort.length === 0,
    `x3=${afterX3} x4=${afterX4} very=${afterVery} div=${c3.calls.abort.length} punct=${c4.calls.abort.length}`
  )
}
{
  // G10 — a 300-line block repeated 3x (period beyond the old 192-line cap) triggers (v1)
  const root = redProject("loop-g10")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  const bigBlock = Array.from({ length: 300 }, (_, i) => `const step${i} = compute(${i})`).join("\n") + "\n"
  const st = { text: "" }
  await feedCumulative(hooks, "s1", [bigBlock, bigBlock, bigBlock], st)
  await sleep(120)
  rec("G10-loopguard-v1: 300-line block x3 triggers interrupt", calls.abort.length === 1, `abort=${calls.abort.length}`)
}
{
  // G10b — a 640-line block repeated 3x (the new cap) triggers (v1)
  const root = redProject("loop-g10b")
  const { client, calls } = makeV1SpyClient()
  const hooks = await newAuditV1WithClient(root, client)
  const bigBlock = Array.from({ length: 640 }, (_, i) => `const item${i} = transform(${i})`).join("\n") + "\n"
  const st = { text: "" }
  await feedCumulative(hooks, "s1", [bigBlock, bigBlock, bigBlock], st)
  await sleep(150)
  rec("G10b-loopguard-v1: 640-line block x3 triggers interrupt", calls.abort.length === 1, `abort=${calls.abort.length}`)
}

// ---------- D. deterministic memory delivery (wave21) ----------
{
  const root = greenProject("mem-d1")
  writeFileSync(
    path.join(root, "tests", "working_note.md"),
    "# Working Note — t\n## Hypothesis ledger\nconfirmed: x\n## Next action\ndo y\n"
  )
  const hooks = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
  const h = hooks.hooks[0]
  const out = { context: [], prompt: undefined }
  await h["experimental.session.compacting"]({ sessionID: "s1" }, out)
  rec(
    "D1-gate-v1: compacting pushes working-note bundle into output.context",
    out.context.length === 1 && out.context[0].includes("VIBEWEAVER WORKING-STATE") && out.context[0].includes("confirmed: x"),
    `n=${out.context.length}`
  )

  const outMiss = { context: [] }
  const rootMiss = greenProject("mem-d2")
  const hooksMiss = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: rootMiss }, "vibeweaver-gate")
  await hooksMiss.hooks[0]["experimental.session.compacting"]({ sessionID: "s2" }, outMiss)
  rec(
    "D2-gate-v1: missing note delivers create-instruction bundle",
    outMiss.context.length === 1 && outMiss.context[0].includes("no tests/working_note.md exists"),
    outMiss.context[0] ? outMiss.context[0].slice(0, 60) : "none"
  )

  const sys1 = { system: ["base"] }
  await h["experimental.chat.system.transform"]({ sessionID: "s1" }, sys1)
  rec("D3a-gate-v1: system transform before compacted event injects nothing", sys1.system.length === 1, `n=${sys1.system.length}`)
  await h.event({ event: { type: "session.compacted", data: { sessionID: "s1" } } })
  const sysOther = { system: ["base"] }
  await h["experimental.chat.system.transform"]({ sessionID: "s9" }, sysOther)
  rec("D3b-gate-v1: different session does not consume the pending resume", sysOther.system.length === 1, `n=${sysOther.system.length}`)
  const sys2 = { system: ["base"] }
  await h["experimental.chat.system.transform"]({ sessionID: "s1" }, sys2)
  rec(
    "D3c-gate-v1: compacted session's next system transform gets the resume bundle",
    sys2.system.length === 2 && String(sys2.system[1]).includes("VIBEWEAVER WORKING-STATE") && String(sys2.system[1]).includes("confirmed: x"),
    `n=${sys2.system.length}`
  )
  const sys3 = { system: ["base"] }
  await h["experimental.chat.system.transform"]({ sessionID: "s1" }, sys3)
  rec("D3d-gate-v1: second call does not re-inject (fire ledger consumed after delivery)", sys3.system.length === 1, `n=${sys3.system.length}`)
  // D3e — v1 envelope uses `properties`, not `data` (regression: session-keyed arm silently broke)
  await h.event({ event: { type: "session.compacted", properties: { sessionID: "s2" } } })
  const sys4 = { system: ["base"] }
  await h["experimental.chat.system.transform"]({ sessionID: "s2" }, sys4)
  rec("D3e-gate-v1: v1 `properties` envelope arms the resume", sys4.system.length === 2 && String(sys4.system[1]).includes("VIBEWEAVER WORKING-STATE"), `n=${sys4.system.length}`)

  const outW1 = { output: "write ok" }
  await h["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "c1", args: { filePath: path.join(root, "src", "a.js") } }, outW1)
  rec("D4a-gate-v1: first write carries one-line resume cue", String(outW1.output).includes("working_note.md"), String(outW1.output).slice(-70))
  const outW2 = { output: "write ok" }
  await h["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "c2", args: { filePath: path.join(root, "src", "b.js") } }, outW2)
  rec("D4b-gate-v1: same-session second write has no cue (one-shot)", !String(outW2.output).includes("working_note.md"), String(outW2.output).slice(-40))
  const outW3 = { output: "write ok" }
  await h["tool.execute.after"]({ tool: "write", sessionID: "s2", callID: "c3", args: { filePath: path.join(root, "src", "c.js") } }, outW3)
  rec("D4c-gate-v1: a new session gets its own cue", String(outW3.output).includes("working_note.md"), String(outW3.output).slice(-50))

  const plain = path.join(TMP, "mem-d5")
  rmrf(plain)
  mkdirSync(plain, { recursive: true })
  const hooks5 = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: plain }, "vibeweaver-gate")
  const out5 = { context: [] }
  await hooks5.hooks[0]["experimental.session.compacting"]({}, out5)
  rec("D5-gate-v1: inactive project delivers nothing", out5.context.length === 0, `n=${out5.context.length}`)

  let st = {}
  try {
    st = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "state.json"), "utf8"))
  } catch {}
  rec(
    "D6-gate-v1: memoryDeliveries telemetry recorded",
    !!st.memoryDeliveries && st.memoryDeliveries.compactContext >= 1 && st.memoryDeliveries.compactResume >= 1 && st.memoryDeliveries.sessionCue >= 1,
    JSON.stringify(st.memoryDeliveries || {})
  )
}
{
  // D8 — harness snapshot survives source-file deletion (wave24)
  const root8 = greenProject("mem-d8")
  writeFileSync(path.join(root8, "tests", "working_note.md"), "# WN\nSECRET battery code ZULU-9 lives here\n")
  const hooks8 = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root8 }, "vibeweaver-gate")
  const h8 = hooks8.hooks[0]
  const out8a = { context: [] }
  await h8["experimental.session.compacting"]({ sessionID: "s1" }, out8a)
  rmSync(path.join(root8, "tests", "working_note.md"), { force: true })
  const out8b = { context: [] }
  await h8["experimental.session.compacting"]({ sessionID: "s1" }, out8b)
  rec(
    "D8-gate-v1: delivery survives source deletion via harness snapshot",
    out8b.context.length === 1 && out8b.context[0].includes("ZULU-9") && out8b.context[0].includes("harness snapshot"),
    out8b.context[0] ? out8b.context[0].slice(0, 80) : "none"
  )
}

console.log(`\n=== COMPAT HARNESS: ${count - failures}/${count} passed, ${failures} failed ===`)
process.exit(failures ? 1 : 0)