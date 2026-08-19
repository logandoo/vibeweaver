// vibeweaver-audit self-test + calibration harness.
// Usage: node scripts/audit_selftest.mjs [--calib /tmp/vibeweaver-audit-calib]
// Runs 5 fixture triage tests against the pure core of vibeweaver-audit.js,
// then (optionally) replays real session transcripts from a directory of
// {sessionID}.json files exported from the opencode event table.
// Exit 0 only when every fixture expectation holds; calibration is
// informational (printed, not failed) — it exists to tune regexes.

import { execFileSync } from "node:child_process"
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { pathToFileURL } from "node:url"
import path from "node:path"

const AUDIT_MODULE = path.resolve(import.meta.dirname, "..", "vibeweaver-audit.js")
const CORE_MODULE = path.resolve(import.meta.dirname, "vibeweaver-audit-core.js")
const { auditProject, buildReport, hashSession, isForbiddenCommand } = await import(pathToFileURL(CORE_MODULE))
const { VibeweaverAudit } = await import(pathToFileURL(AUDIT_MODULE))

const TMP = "/tmp/vibeweaver-audit-test"
const results = []
let failures = 0

function rec(name, ok, detail) {
  results.push({ name, ok, detail })
  if (!ok) failures++
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

// ---------- fixture builders ----------

function newFixture(name) {
  const root = path.join(TMP, name)
  rmSync(root, { recursive: true, force: true })
  for (const d of ["tests/workflows", "memory", "script/linux"]) mkdirSync(path.join(root, d), { recursive: true })
  return root
}

function write(root, rel, content) {
  const p = path.join(root, rel)
  mkdirSync(path.dirname(p), { recursive: true })
  writeFileSync(p, content)
}

function writeSh(root, rel) {
  write(root, rel, "#!/bin/sh\nexit 0\n")
  chmodSync(path.join(root, rel), 0o755)
}

function initGit(root, commitAfterLog) {
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["config", "user.email", "audit@test"], { cwd: root })
  execFileSync("git", ["config", "user.name", "audit"], { cwd: root })
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "baseline"], { cwd: root })
  if (commitAfterLog) {
    // change a CODE file after the log write, then commit -> real violation
    write(root, "tests/verification_log.md", readFileSyncSafe(path.join(root, "tests/verification_log.md")) + "\nchanged after baseline\n")
    write(root, "src/code.ts", "export const x = 1\n")
    execFileSync("sleep", ["3.5"])
    execFileSync("git", ["add", "-A"], { cwd: root })
    execFileSync("git", ["commit", "-qm", "after"], { cwd: root })
  }
}

// Complete project scaffold that passes assert_artifacts.py --existing
function scaffoldComplete(root) {
  const log = [
    "## Task: fixture | 2026-08-19",
    "- Baseline verified GREEN",
    "- iter 1 FAIL: criterion #2 (field missing) | diagnosis: validator ran before state hydrat | changed: src/form.ts",
    "- iter 2 PASS: all criteria (evidence: tests/shot.png, 6/6)",
    "- [Convergence] fixture: 2 iters | 6/6 pass | 0 stalls | 0 cap-hits",
    "workflow trace: tests/workflows/login.trace.log — 3 steps, all asserts green",
  ].join("\n")
  write(root, "tests/verification_log.md", log)
  write(root, "tests/acceptance.md", "> cap=5  stall=3×\n\n# Acceptance — Fixture\n1. Username field exists\n2. No error banner\n")
  write(root, "tests/shot.png", "png-bytes")
  write(root, "tests/flow.mp4", "mp4-bytes")
  write(root, "tests/flow_audio.wav", "wav-bytes")
  write(root, "tests/workflows/login.trace.log", "step1 201 ok\nstep2 201 ok\nstep3 200 ok\n")
  write(root, "memory/MEMORY.md", "# Project Memory Index\n- [fix fixture](fix_fixture.md)\n")
  write(root, "memory/fix_fixture.md", "# Fix Fixture\nstatus: ⏳\n")
  writeSh(root, "script/linux/start.sh")
  writeSh(root, "script/linux/stop.sh")
  writeSh(root, "script/linux/restart.sh")
  writeSh(root, "script/linux/project_build.sh")
  const assertSrc = path.resolve(import.meta.dirname, "assert_artifacts.py")
  if (existsSync(assertSrc)) write(root, "tests/assert_artifacts.py", readFileSyncSafe(assertSrc))
}

function readFileSyncSafe(p) {
  return readFileSync(p, "utf8")
}

// ---------- session text builders ----------

const GATE_LINE =
  "[Verification Gate] Verifier: mm-sensor [image] | direct-read | Loop executed: yes | Media graded externally: 3/3 (video 0 · audio 0 · screenshots 3) | Iterations: 2 | Tests executed with artifacts: yes | E2E depth: real-HTTP | Script-only build/lifecycle: yes | Fresh-run on final tree: yes | TDD RED evidence: yes | Code review: N/A | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass"

function cleanSessionText() {
  return [
    "Verifier: mm-sensor [image]",
    "Baseline verified GREEN — proceed",
    GATE_LINE,
    "[Covenant Recall] checked: all 11 covenants hold for this completion",
    "[Memory Gate] Passed: memory written (A7.9/A7.10)",
    "[Convergence] fixture: 2 iters | 6/6 pass | 0 stalls | 0 cap-hits",
    "A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit",
    "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
    "| 1 | fix | Searched: none | A (reason) | src/form.ts | validation order | tests/shot.png -> verified | abc123 |",
  ].join("\n")
}

const baseTools = () => [
  { tool: "skill", name: "vibeweaver", t: 1000 },
  { tool: "read", filePath: "/Users/x/.config/opencode/skills/vibeweaver/TESTING_PROTOCOLS.md", t: 1001 },
  { tool: "read", filePath: "/Users/x/.config/opencode/skills/vibeweaver/COMPLETION_GATE.md", t: 1002 },
  { tool: "read", filePath: "/Users/x/.config/opencode/skills/vibeweaver/REFERENCE.md", t: 1003 },
  { tool: "bash", command: "bash script/linux/start.sh", t: 1004 },
  { tool: "write", filePath: "/project/src/form.ts", t: 1005 },
]

// =====================================================================
// T1 — clean pass: all markers + complete artifacts + no contradictions
// =====================================================================
{
  const root = newFixture("t1-clean")
  scaffoldComplete(root)
  initGit(root, false)
  // make the log newer than HEAD (fresh-run OK)
  write(root, "tests/verification_log.md", readFileSyncSafe(path.join(root, "tests/verification_log.md")) + "\n")

  const audit = auditProject({
    root,
    sessionID: "ses_t1_clean",
    sessionText: cleanSessionText(),
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  rec("T1 clean pass", audit.bad === 0 && !audit.escalate, `BAD=${audit.bad} UNCERTAIN=${audit.uncertain} escalate=${audit.escalate}`)
  const badIds = audit.checks.filter((c) => c.verdict === "BAD").map((c) => c.id)
  rec("T1 no BAD checks", badIds.length === 0, badIds.join(",") || "none")
}

// =====================================================================
// T2 — missing narration markers (no gate line at all)
// =====================================================================
{
  const root = newFixture("t2-no-markers")
  scaffoldComplete(root)
  const audit = auditProject({
    root,
    sessionID: "ses_t2",
    sessionText: "Verifier: mm-sensor [image]\nI fixed the bug, all good.",
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const bBad = audit.checks.filter((c) => c.id.startsWith("B") && c.verdict === "BAD").length
  rec("T2 B-group markers BAD", bBad >= 9, `B-BAD=${bBad} totalBAD=${audit.bad}`)
  rec("T2 red (blocks writes)", audit.red === true, `red=${audit.red}`)
}

// =====================================================================
// T3 — claim ↔ artifact contradictions
// =====================================================================
{
  const root = newFixture("t3-contradictions")
  // log exists but has ZERO iter lines (claim says 2), no media, no trace
  write(root, "tests/verification_log.md", "## Task: fixture\nno iterations here\n")
  write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  write(root, "tests/shot.png", "x")
  const audit = auditProject({
    root,
    sessionID: "ses_t3",
    sessionText: cleanSessionText(), // claims Loop yes / Iterations 2 / Media 3/3 / E2E real-HTTP / TDD yes / Fresh yes
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const claimed = audit.checks.filter((c) => ["C1", "C2", "C3", "C4", "C5", "C6"].includes(c.id))
  const badClaimed = claimed.filter((c) => c.verdict === "BAD").map((c) => c.id)
  rec("T3 contradictory claims BAD", badClaimed.length >= 3, `BAD among C1-C6: ${badClaimed.join(",")}`)
  rec("T3 red", audit.red === true, `red=${audit.red}`)
}

// =====================================================================
// T4 — UNCERTAIN-only escalation (claims present, evidence unverifiable)
// =====================================================================
{
  const root = newFixture("t4-uncertain")
  scaffoldComplete(root)
  const text = cleanSessionText()
    .replace("Code review: N/A", "Code review: clean") // no task dispatch in tools
    .replace("A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit\n", "")
  const audit = auditProject({
    root,
    sessionID: "ses_t4",
    sessionText: text,
    tools: baseTools().filter((t) => !t.tool.startsWith("read")), // no R1/R1b reads
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  rec("T4 zero BAD", audit.bad === 0, `BAD=${audit.bad}`)
  rec("T4 UNCERTAIN present", audit.uncertain >= 3, `UNCERTAIN=${audit.uncertain}`)
  rec("T4 escalate on UNCERTAIN", audit.escalate === true, `reasons=${audit.escalateReasons.join(",")}`)
}

// =====================================================================
// T5 — forbidden raw command + fresh-run violation
// =====================================================================
{
  const root = newFixture("t5-forbidden")
  scaffoldComplete(root)
  initGit(root, true) // commit AFTER the log write -> fresh-run BAD
  const audit = auditProject({
    root,
    sessionID: "ses_t5",
    sessionText: cleanSessionText(), // claims Fresh-run: yes
    tools: [...baseTools(), { tool: "bash", command: "npm run build" }],
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const c8 = audit.checks.find((c) => c.id === "C8")
  const c6 = audit.checks.find((c) => c.id === "C6")
  rec("T5 forbidden raw command BAD", c8 && c8.verdict === "BAD", c8 ? c8.verdict : "missing")
  rec("T5 fresh-run violation BAD", c6 && c6.verdict === "BAD", c6 ? `${c6.verdict} — ${c6.evidence}` : "missing")
  rec("T5 isForbiddenCommand unit", isForbiddenCommand("npm run build") && isForbiddenCommand("uvicorn app:main") && !isForbiddenCommand("bash script/linux/start.sh"), "")
  rec("T5 hashSession deterministic", hashSession("ses_x", "root") === hashSession("ses_x", "root") && hashSession("ses_x", "root") >= 0 && hashSession("ses_x", "root") < 100, "")
}

// =====================================================================
// T6-T8 — plugin-level integration (event replay → state → report → block)
// =====================================================================
{
  const calibRoot = "/tmp/vibeweaver-audit-calib"
  const realSession = existsSync(calibRoot)
    ? JSON.parse(readFileSync(path.join(calibRoot, "ses_fe8cc60c4fferlxQcjoA1mYGUf.json"), "utf8"))
    : null

  // ---- T6: replay a real session through the plugin; report must land ----
  const root6 = newFixture("t6-integration")
  write(root6, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({
    client: { app: { log: async () => {} } },
    directory: root6,
  })
  const sessID = "ses_t6_replay"
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  if (realSession) {
    let i = 0
    for (const t of realSession.texts) {
      await emit("message.part.updated", { sessionID: sessID, part: { id: `t${i++}`, type: "text", text: t } })
    }
    for (const t of realSession.tools) {
      let inp = {}
      try {
        inp = JSON.parse(t.input || "{}")
      } catch {
        inp = {}
      }
      await emit("message.part.updated", {
        sessionID: sessID,
        part: { id: `k${i++}`, type: "tool", tool: t.tool, state: { status: "completed", input: inp, output: t.output } },
      })
    }
    await emit("session.idle", { sessionID: sessID })
    const report = readFileSyncSafe(path.join(root6, "tests", "gate_audit.md"))
    const audited = report.startsWith("# Gate Audit") && !report.includes("not audited")
    rec("T6 event replay → gate_audit.md written", audited && report.includes("AUDIT:"), `report ${report.split("\n")[1]}`)
  } else {
    rec("T6 event replay → gate_audit.md written", false, "calibration data missing")
  }

  // ---- T7: RED final audit blocks the next write ----
  const root7 = newFixture("t7-block")
  write(root7, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin7 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root7 })
  const emit7 = (type, props) => plugin7.event({ event: { type, properties: props } })
  await emit7("message.part.updated", {
    sessionID: "ses_t7",
    part: { id: "t1", type: "text", text: "Verifier: mm-sensor [image]\n[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" },
  })
  await emit7("message.part.updated", {
    sessionID: "ses_t7",
    part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } },
  })
  await emit7("session.idle", { sessionID: "ses_t7" })
  let threw = false
  try {
    await plugin7["tool.execute.before"]({ tool: "write", args: { filePath: path.join(root7, "src", "a.ts") } })
  } catch (e) {
    threw = /GATE-BLOCKED \(vibeweaver-audit\)/.test(e.message)
  }
  rec("T7 RED blocks write (before hook)", threw, threw ? "GATE-BLOCKED thrown" : "no block")
  let testsWriteOk = true
  try {
    await plugin7["tool.execute.before"]({ tool: "write", args: { filePath: path.join(root7, "tests", "verification_log.md") } })
  } catch {
    testsWriteOk = false
  }
  rec("T7 tests/ stays writable while RED", testsWriteOk, testsWriteOk ? "evidence fix path open" : "unexpectedly blocked")

  // ---- T8: mid-phase forbidden command becomes a warning note ----
  const root8 = newFixture("t8-warn")
  write(root8, "tests/verification_log.md", "## Task: x\n- iter 1 PASS: all (evidence: none)\n")
  write(root8, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  mkdirSync(path.join(root8, "script"), { recursive: true })
  const plugin8 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root8 })
  const emit8 = (type, props) => plugin8.event({ event: { type, properties: props } })
  await emit8("message.part.updated", {
    sessionID: "ses_t8",
    part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } },
  })
  await emit8("message.part.updated", {
    sessionID: "ses_t8",
    part: { id: "k2", type: "tool", tool: "bash", state: { status: "completed", input: { command: "npm run build" }, output: "" } },
  })
  await emit8("session.idle", { sessionID: "ses_t8" })
  const report8 = existsSync(path.join(root8, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root8, "tests", "gate_audit.md")) : ""
  const c8bad = /\[BAD\] C8 script-only/.test(report8)
  rec("T8 forbidden command → BAD in report", c8bad, c8bad ? "C8 flagged" : report8.split("\n")[1] || "(no report)")
}

// ---- T9: mid-task session.idle must NOT set red (multi-turn safety) ----
{
  const root9 = newFixture("t9-mid-idle")
  write(root9, "tests/verification_log.md", "## Task: x\n")
  const plugin9 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root9 })
  const emit9 = (type, props) => plugin9.event({ event: { type, properties: props } })
  await emit9("message.part.updated", {
    sessionID: "ses_t9",
    part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } },
  })
  await emit9("message.part.updated", {
    sessionID: "ses_t9",
    part: { id: "t1", type: "text", text: "Decomposing the task... first step: read the config." },
  })
  await emit9("session.idle", { sessionID: "ses_t9" })
  let blocked = false
  try {
    await plugin9["tool.execute.before"]({ tool: "write", args: { filePath: path.join(root9, "src", "mid.ts") } })
  } catch {
    blocked = true
  }
  const report9 = existsSync(path.join(root9, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root9, "tests", "gate_audit.md")) : ""
  const isMid = /AUDIT: BAD=\d+ UNCERTAIN=\d+ escalate=/.test(report9)
  rec("T9 mid-task idle → no block", !blocked, blocked ? "blocked mid-task!" : "write passed")
  rec("T9 mid-task report written", isMid, "report exists")
}

// ---- T10: project-local audit.json is IGNORED (self-weakening blocked) ----
{
  const root10 = newFixture("t10-hostile-config")
  write(root10, "tests/verification_log.md", "## Task: x\n")
  write(root10, ".vibeweaver/audit.json", JSON.stringify({ samplingRate: 0, escOnUncertain: false, escOnHighRisk: false }))
  const oldEnv = process.env.VIBEWEAVER_AUDIT_CONFIG
  process.env.VIBEWEAVER_AUDIT_CONFIG = "/nonexistent"
  const plugin10 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root10 })
  const emit10 = (type, props) => plugin10.event({ event: { type, properties: props } })
  await emit10("message.part.updated", {
    sessionID: "ses_t10",
    part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } },
  })
  await emit10("message.part.updated", {
    sessionID: "ses_t10",
    part: { id: "t1", type: "text", text: "[Verification Gate] Verifier: mm-sensor [image] | Loop executed: no | Code review: clean | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" },
  })
  await emit10("session.idle", { sessionID: "ses_t10" })
  process.env.VIBEWEAVER_AUDIT_CONFIG = oldEnv || ""
  const report10 = existsSync(path.join(root10, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root10, "tests", "gate_audit.md")) : ""
  const esc = /escalate=true/.test(report10)
  rec("T10 project audit.json ignored → escalation still fires", esc, report10.split("\n")[1] || "(no report)")
}

// ---- T11: template coupling + SKILL.md size guard ----
{
  const skillMd = readFileSyncSafe(path.resolve(import.meta.dirname, "..", "SKILL.md"))
  const template = skillMd.match(/\[Verification Gate\] Verifier:[^\n]+/)
  const required = [
    "Loop executed:", "Iterations:", "Media graded externally:", "E2E depth:", "TDD RED evidence:",
    "Fresh-run on final tree:", "Code review:", "assert_artifacts.py: pass=", "covenant_recall:",
    "memory_gate:", "HARD-GATE-1:", "HARD-GATE-2:",
  ]
  const missing = required.filter((f) => !(template && template[0].includes(f)))
  rec("T11 gate-line template ↔ audit field coupling", !missing.length && !!template, missing.length ? `template fields missing: ${missing.join(",")}` : "all audit field regexes match the current SKILL.md template")
  rec("T11 SKILL.md stays under cap", Buffer.byteLength(skillMd) < 49000, `${Buffer.byteLength(skillMd)}B`)
}

// ---- T12: doc-only commits after the run are legitimate (expB regression) ----
{
  const root12 = newFixture("t12-doc-commits")
  scaffoldComplete(root12)
  initGit(root12, false)
  // post-log: only tests/ + memory/ files, then commit (documentation pattern)
  write(root12, "tests/final_verify_run.log", "PASS all\n")
  write(root12, "memory/fix_greeting.md", "# Fix\nstatus: ⏳\n")
  write(root12, "tests/verification_log.md", readFileSyncSafe(path.join(root12, "tests/verification_log.md")) + "\n- audit-fix: C6 doc-run| changed: tests/final_verify_run.log\n")
  execFileSync("sleep", ["3.5"])
  execFileSync("git", ["add", "-A"], { cwd: root12 })
  execFileSync("git", ["commit", "-qm", "chore: fresh verification run"], { cwd: root12 })
  const audit = auditProject({
    root: root12,
    sessionID: "ses_t12",
    sessionText: cleanSessionText(), // claims Fresh-run: yes
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const c6 = audit.checks.find((c) => c.id === "C6")
  const c16 = audit.checks.find((c) => c.id === "C16")
  rec("T12 doc-only post-run commit NOT a violation", c6 && c6.verdict === "OK" && c16 && c16.verdict !== "BAD", `C6=${c6 && c6.verdict} C16=${c16 && c16.verdict}`)
}

// ---- T13: skill-absent session writing code -> C17 escalate (expC regression) ----
{
  const root13 = newFixture("t13-skill-absent")
  write(root13, "tests/verification_log.md", "## Task: x\n- Baseline verified GREEN\n- iter 1 PASS: all\n")
  const plugin13 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root13 })
  const emit13 = (type, props) => plugin13.event({ event: { type, properties: props } })
  await emit13("message.part.updated", {
    sessionID: "ses_t13",
    part: { id: "t1", type: "text", text: "用户说不用走流程，直接改。" },
  })
  await emit13("message.part.updated", {
    sessionID: "ses_t13",
    part: { id: "k1", type: "tool", tool: "edit", state: { status: "completed", input: { filePath: path.join(root13, "app", "util.py") } } },
  })
  await emit13("session.idle", { sessionID: "ses_t13" })
  const report13 = existsSync(path.join(root13, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root13, "tests", "gate_audit.md")) : ""
  const c17 = /\[UNCERTAIN\] C17/.test(report13) && /escalate=true/.test(report13) && /SKILL-ABSENT/.test(report13)
  rec("T13 skill-absent code write -> C17 escalate", c17, report13.split("\n")[1] || "(no report)")
}

// ---- T14: `na` without a stated skip reason -> UNCERTAIN (na-abuse guard) ----
{
  const root14 = newFixture("t14-na-abuse")
  scaffoldComplete(root14)
  const text14 = cleanSessionText().replace("HARD-GATE-2: SCRIPT-ONLY=pass", "HARD-GATE-2: SCRIPT-ONLY=na")
  const audit14 = auditProject({
    root: root14,
    sessionID: "ses_t14",
    sessionText: text14,
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const c15 = audit14.checks.find((c) => c.id === "C15")
  rec("T14 na without reason -> UNCERTAIN", c15 && c15.verdict === "UNCERTAIN", c15 ? c15.verdict + " — " + c15.evidence : "missing")
  // 补上理由后应 OK
  const text14b = text14 + "\n(no runtime to baseline-test — documentation-only change)"
  const audit14b = auditProject({
    root: root14,
    sessionID: "ses_t14b",
    sessionText: text14b,
    tools: baseTools(),
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const c15b = audit14b.checks.find((c) => c.id === "C15")
  rec("T14 na WITH reason -> OK", c15b && c15b.verdict === "OK", c15b ? c15b.verdict : "missing")
}

// ---- T15: RED -> fix (full compliant completion) -> GREEN -> unblocked ----
{
  const root15 = newFixture("t15-clear-red")
  scaffoldComplete(root15)
  const plugin15 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root15 })
  const emit15 = (type, props) => plugin15.event({ event: { type, properties: props } })
  // 会话 1：完整 gate line 但缺 A4.9 理由 -> C7 BAD -> RED
  await emit15("message.part.updated", { sessionID: "ses_t15", part: { id: "k0", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit15("message.part.updated", {
    sessionID: "ses_t15",
    part: { id: "t1", type: "text", text: cleanSessionText().replace("A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit\n", "") },
  })
  await emit15("session.idle", { sessionID: "ses_t15" })
  let blocked = false
  try {
    await plugin15["tool.execute.before"]({ tool: "write", args: { filePath: path.join(root15, "src", "x.ts") } })
  } catch {
    blocked = true
  }
  rec("T15 red state blocks write", blocked, blocked ? "blocked" : "not blocked")
  // 修复：log 追加 audit-fix（tests/ 可写）+ 回复里输出完整合规的 gate line -> idle -> GREEN
  write(root15, "tests/verification_log.md", readFileSyncSafe(path.join(root15, "tests/verification_log.md")) + "\n- audit-fix: C7 missing A4.9 reason | changed: tests/verification_log.md\n")
  await emit15("message.part.updated", {
    sessionID: "ses_t15",
    part: { id: "t2", type: "text", text: cleanSessionText() },
  })
  await emit15("session.idle", { sessionID: "ses_t15" })
  let stillBlocked = false
  try {
    await plugin15["tool.execute.before"]({ tool: "write", args: { filePath: path.join(root15, "src", "y.ts") } })
  } catch {
    stillBlocked = true
  }
  rec("T15 fix + rerun -> unblocked", !stillBlocked, stillBlocked ? "still blocked" : "writes allowed again")
}

// =====================================================================
// Calibration — real session transcripts (informational)
// =====================================================================
const calibDir = process.argv.includes("--calib") ? process.argv[process.argv.indexOf("--calib") + 1] : "/tmp/vibeweaver-audit-calib"
if (existsSync(calibDir)) {
  console.log("\n=== CALIBRATION (real sessions) ===")
  const { readdirSync, readFileSync } = await import("node:fs")
  for (const f of readdirSync(calibDir).filter((x) => x.endsWith(".json")).sort()) {
    const sess = JSON.parse(readFileSync(path.join(calibDir, f), "utf8"))
    const tools = sess.tools.map((t) => {
      const o = { tool: t.tool, t: 1 }
      try {
        const inp = JSON.parse(t.input || "{}")
        if (inp.filePath) o.filePath = inp.filePath
        if (inp.command) o.command = inp.command
        if (inp.name) o.name = inp.name
      } catch {
        /* ignore */
      }
      return o
    })
    const text = sess.texts.join("\n")
    const root = newFixture("calib-" + sess.sessionID.slice(0, 12))
    write(root, "tests/verification_log.md", "placeholder\n")
    const skillToolSeen = tools.some((t) => t.tool === "skill" && t.name === "vibeweaver")
    for (const forced of [false, true]) {
      if (forced && skillToolSeen) continue
      const audit = auditProject({
        root,
        sessionID: sess.sessionID,
        sessionText: text,
        tools,
        skillLoaded: forced ? true : skillToolSeen,
        phase: "final",
        config: { samplingRate: 0, escOnUncertain: false },
      })
      const bs = audit.checks.filter((c) => c.verdict === "BAD").map((c) => c.id)
      const us = audit.checks.filter((c) => c.verdict === "UNCERTAIN").map((c) => c.id)
      const bHit = audit.checks.filter((c) => c.id.startsWith("B") && c.verdict === "OK").map((c) => c.id)
      console.log(
        `${forced ? "[forced] " : ""}${sess.sessionID.slice(0, 16)} tools=${tools.length} text=${text.length} skillLoaded=${skillToolSeen} → BAD=[${bs.join(",")}] UNCERTAIN=[${us.join(",")}] markers-hit=[${bHit.join(",")}]`
      )
    }
  }
} else {
  console.log("\n(no calibration dir — pass --calib <dir>)")
}

// ---------- summary ----------
console.log("\n=== SUMMARY ===")
console.log(`fixture checks: ${results.length}, failures: ${failures}`)
if (failures > 0) {
  for (const r of results.filter((r) => !r.ok)) console.log("FAILED:", r.name, "—", r.detail)
}
process.exit(failures ? 1 : 0)
