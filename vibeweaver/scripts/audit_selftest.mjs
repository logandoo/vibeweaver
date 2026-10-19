// vibeweaver-audit self-test + calibration harness.
// Usage: node scripts/audit_selftest.mjs [--calib /tmp/vibeweaver-audit-calib]
// Runs the fixture triage suite (T1-T20) against the pure core of
// vibeweaver-audit.js,
// then (optionally) replays real session transcripts from a directory of
// {sessionID}.json files exported from the opencode event table.
// Exit 0 only when every fixture expectation holds; calibration is
// informational (printed, not failed) — it exists to tune regexes.

import { execFileSync } from "node:child_process"
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, utimesSync, writeFileSync } from "node:fs"
import os from "node:os"
import { pathToFileURL } from "node:url"
import path from "node:path"

const AUDIT_MODULE = path.resolve(import.meta.dirname, "..", "vibeweaver-audit.js")
const CORE_MODULE = path.resolve(import.meta.dirname, "vibeweaver-audit-core.js")
const { auditProject, buildReport, mergeReleaseLines, hashSession, isForbiddenCommand, isNoopBashCommand, noopBashFinding, stopEuphemism, stopAwaitingUser, stopReadOnlyInstruction, stopGuardDecision, stopGuardPrompt, currentLogBlock, currentEvidenceBlock, finalRunEvidence, pausedPacketValid, pausedDeclaration, classERecordValid, classEUserApproval, classEDeclaration, identicalToolRunFinding, toolIdentity, canonicalJson, toolFrequencyFinding } = await import(pathToFileURL(CORE_MODULE))
// Dual-compat module surface: current plugin default-exports { id, server, setup };
// fall back to the legacy named export when testing an older copy.
const auditModule = await import(pathToFileURL(AUDIT_MODULE))
const VibeweaverAudit = auditModule.VibeweaverAudit || (auditModule.default && auditModule.default.server)

const TMP = path.join(os.tmpdir(), "vibeweaver-audit-test")
const results = []
let failures = 0
let skips = 0

function rec(name, ok, detail) {
  results.push({ name, ok, detail })
  if (!ok) failures++
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

function skip(name, detail) {
  results.push({ name, ok: true, detail, skipped: true })
  skips++
  console.log(`SKIP  ${name}${detail ? " — " + detail : ""}`)
}

// ---------- fixture builders ----------

function newFixture(name) {
  const root = path.join(TMP, name)
  rmSync(root, { recursive: true, force: true })
  for (const d of ["tests/workflows", "memory", "script/linux"]) mkdirSync(path.join(root, d), { recursive: true })
  // D1 project gate (2026-10-15): fixtures are vibeweaver-ACTIVE projects —
  // the loop-guard runs only with tests/acceptance.md present or the skill
  // activated. Tests probing the inactive state build their own fixture.
  write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. fixture\n")
  write(root, ".gitignore", ".DS_Store\n__pycache__/\n.venv/\nnode_modules/\n.pnpm-store/\n.env\n")
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
    "- working-note: created → distilled → deleted (fixture lifecycle)",
    "- [Convergence] fixture: 2 iters | 6/6 pass | 0 stalls | 0 cap-hits",
    "workflow trace: tests/workflows/login.trace.log — 3 steps, all asserts green",
    "- assert-run: assert_artifacts.py: all 30 checks pass (exit 0)",
    "- final-run: --final — pass=19/fail=0",
  ].join("\n")
  write(root, "tests/verification_log.md", log)
  write(root, "tests/acceptance.md", "> cap=5  stall=3×\n\n# Acceptance — Fixture\n1. Username field exists\n2. No error banner\n")
  // C2 (P1) media fixtures must be FORMAT-VALID (magic bytes) — the checks
  // now reject 1-byte pseudo-screenshots by design
  write(root, "tests/shot.png", Buffer.from("89504e470d0a1a0a0000000d4948445200000280000001900806000000" + "00".repeat(32), "hex"))
  write(root, "tests/flow.mp4", Buffer.from("00000018667479706d703432" + "00".repeat(24), "hex"))
  write(root, "tests/flow_audio.wav", Buffer.from("524946462400000057415645666d7420" + "00".repeat(24), "hex"))
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
  "[Verification Gate] Verifier: mm-sensor [image] | direct-read | Class: CODE | Loop executed: yes | Media graded externally: 3/3 (video 0 · audio 0 · screenshots 3) | Iterations: 2 | Tests executed with artifacts: yes | E2E depth: real-HTTP | Script-only build/lifecycle: yes | Fresh-run on final tree: yes | TDD RED evidence: yes | Code review: N/A | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass"

function cleanSessionText() {
  return [
    "Verifier: mm-sensor [image]",
    "Baseline verified GREEN — proceed",
    GATE_LINE,
    "[Covenant Recall] checked: all 13 covenants hold for this completion",
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
  const a4ev = (audit.checks.find((c) => c.id === "A4") || {}).evidence || ""
  rec("T1 no BAD checks", badIds.length === 0, (badIds.join(",") || "none") + (badIds.includes("A4") && a4ev ? ` | A4 evidence: ${a4ev}` : ""))
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
  const calibIdx = process.argv.indexOf("--calib")
  const calibValue = calibIdx >= 0 ? process.argv[calibIdx + 1] : null
  const calibArg = calibValue && !calibValue.startsWith("--") ? calibValue : "/tmp/vibeweaver-audit-calib"
  const calibFile = path.join(calibArg, "ses_fe8cc60c4fferlxQcjoA1mYGUf.json")
  let realSession = null
  if (existsSync(calibFile)) {
    try {
      realSession = JSON.parse(readFileSync(calibFile, "utf8"))
    } catch {
      realSession = null // unreadable calibration data → skip, never crash the suite
    }
  }

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
    skip("T6 event replay → gate_audit.md written",
         `calibration session not found at ${calibFile} — pass --calib <dir> with the exported session JSON for the full replay; not a code regression`)
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
    "Class:", "Loop executed:", "Iterations:", "Media graded externally:", "E2E depth:", "TDD RED evidence:",
    "Fresh-run on final tree:", "Code review:", "assert_artifacts.py: pass=", "covenant_recall:",
    "memory_gate:", "repo-hygiene:", "HARD-GATE-1:", "HARD-GATE-2:",
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
// T21 — C8 dedup: the same forbidden command flags ONCE per root
// (a latch must be self-clearable; immutable history cannot pin a session)
// =====================================================================
{
  const root = newFixture("t21-c8dedup")
  scaffoldComplete(root)
  initGit(root, false)
  write(root, "tests/verification_log.md", readFileSyncSafe(path.join(root, "tests/verification_log.md")) + "\n")
  const tools21 = [...baseTools(), { tool: "bash", command: "pkill -f uvicorn" }]
  const a1 = auditProject({ root, sessionID: "ses_t21", sessionText: cleanSessionText(), tools: tools21, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c8a = a1.checks.find((c) => c.id === "C8")
  rec("T21 first forbidden command flags BAD", c8a && c8a.verdict === "BAD" && a1.red, c8a ? `${c8a.verdict} red=${a1.red}` : "missing")
  rec("T21 newlyFlagged returned for persistence", Array.isArray(a1.newlyFlagged) && a1.newlyFlagged.length === 1, `n=${a1.newlyFlagged ? a1.newlyFlagged.length : "?"}`)
  const a2 = auditProject({ root, sessionID: "ses_t21", sessionText: cleanSessionText(), tools: tools21, skillLoaded: true, phase: "final", config: { samplingRate: 0 }, priorFlagged: a1.newlyFlagged })
  const c8b = a2.checks.find((c) => c.id === "C8")
  rec("T21 same history does NOT re-flag (self-clearable)", c8b && c8b.verdict === "OK" && a2.bad === 0 && !a2.red, c8b ? `${c8b.verdict} bad=${a2.bad} red=${a2.red}` : "missing")
  const a3 = auditProject({ root, sessionID: "ses_t21", sessionText: cleanSessionText(), tools: [...tools21, { tool: "bash", command: "npm run build" }], skillLoaded: true, phase: "final", config: { samplingRate: 0 }, priorFlagged: a1.newlyFlagged })
  const c8c = a3.checks.find((c) => c.id === "C8")
  rec("T21 a different forbidden command still flags", c8c && c8c.verdict === "BAD" && Array.isArray(a3.newlyFlagged) && a3.newlyFlagged.length === 1, c8c ? `${c8c.verdict} new=${a3.newlyFlagged ? a3.newlyFlagged.length : "?"}` : "missing")
}

// ---- T22: a C8 latch self-clears on the next GREEN audit (dedup e2e) ----
{
  const root = newFixture("t22-c8selfclear")
  scaffoldComplete(root)
  initGit(root, false)
  write(root, "tests/verification_log.md", readFileSyncSafe(path.join(root, "tests/verification_log.md")) + "\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  await emit("message.part.updated", { sessionID: "ses_t22", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit("message.part.updated", { sessionID: "ses_t22", part: { id: "t1", type: "text", text: cleanSessionText() } })
  await emit("message.part.updated", { sessionID: "ses_t22", part: { id: "b1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "pkill -f uvicorn" }, output: "" } } })
  await emit("session.idle", { sessionID: "ses_t22" })
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const latched = JSON.parse(readFileSync(sp, "utf8")).roots[root].red
  const blocked = await tryWrite(plugin, root, "src/x.ts", "ses_t22")
  rec("T22 fresh forbidden command latches RED", !!latched && typeof blocked === "string" && /GATE-BLOCKED/.test(blocked), latched ? `latched bad=${latched.bad}` : "no latch: " + blocked)
  await emit("session.idle", { sessionID: "ses_t22" })
  const st2 = JSON.parse(readFileSync(sp, "utf8")).roots[root]
  const cleared = st2.red == null
  const writeAfter = cleared ? await tryWrite(plugin, root, "src/y.ts", "ses_t22") : "still latched"
  rec("T22 latch self-clears on the next GREEN audit (no env-off, no state surgery)", cleared && writeAfter === true, cleared ? `cleared; c8Flagged=${(st2.c8Flagged || []).length}` : "still latched — dedup broken")
}

// =====================================================================


// ---- T23: a forbidden command run MID-TASK (before the completion marker)
// must still latch at the final audit — the mid-phase warn must NOT consume
// the C8 one-shot (wave9 review Critical regression fixture)
{
  const root = newFixture("t23-midthenfinal")
  scaffoldComplete(root)
  initGit(root, false)
  write(root, "tests/verification_log.md", readFileSyncSafe(path.join(root, "tests/verification_log.md")) + "\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  await emit("message.part.updated", { sessionID: "ses_t23", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit("message.part.updated", { sessionID: "ses_t23", part: { id: "t0", type: "text", text: "working on it, no completion marker yet" } })
  await emit("message.part.updated", { sessionID: "ses_t23", part: { id: "b1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "pkill -f uvicorn" }, output: "" } } })
  await emit("session.idle", { sessionID: "ses_t23" })
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const st1 = JSON.parse(readFileSync(sp, "utf8")).roots[root] || {}
  rec("T23 mid-phase warns but neither latches nor persists dedup", st1.red == null && !(Array.isArray(st1.c8Flagged) && st1.c8Flagged.length), `red=${JSON.stringify(st1.red)} flagged=${(st1.c8Flagged || []).length}`)
  await emit("message.part.updated", { sessionID: "ses_t23", part: { id: "t1", type: "text", text: cleanSessionText() } })
  await emit("session.idle", { sessionID: "ses_t23" })
  const st2 = JSON.parse(readFileSync(sp, "utf8")).roots[root] || {}
  rec("T23 the final audit still latches the mid-task forbidden command", !!st2.red && Array.isArray(st2.c8Flagged) && st2.c8Flagged.length === 1, `red=${JSON.stringify(st2.red)} flagged=${(st2.c8Flagged || []).length}`)
}

// =====================================================================
// T16-T19 — RED latch is SESSION-SCOPED (deadlock regression, 2026-08-21)
// =====================================================================

async function latchRed(plugin, sessionId, root) {
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  await emit("message.part.updated", { sessionID: sessionId, part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit("message.part.updated", { sessionID: sessionId, part: { id: "t1", type: "text", text: "Verifier: mm-sensor [image]\n[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  await emit("session.idle", { sessionID: sessionId })
}

// Returns true when the write passed, or the error message when blocked —
// callers asserting a block must check for GATE-BLOCKED, so an unexpected
// error (test bug) can never masquerade as a pass.
async function tryWrite(plugin, root, relPath, sessionId) {
  // "RAW:" prefix bypasses path.join normalization — the adversarial path
  // (tests/../src/a.js) must reach the plugin exactly as a hostile tool arg.
  const filePath = relPath.startsWith("RAW:") ? root + "/" + relPath.slice(4) : path.join(root, relPath)
  try {
    await plugin["tool.execute.before"]({ tool: "write", sessionID: sessionId, args: { filePath } })
    return true
  } catch (e) {
    return e.message
  }
}

// ---- T16: a DIFFERENT session's write auto-releases an inherited RED ----
{
  const root = newFixture("t16-takeover")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  await latchRed(plugin, "ses_t16_a", root)
  const aResult = await tryWrite(plugin, root, "src/a.ts", "ses_t16_a")
  const aBlocked = typeof aResult === "string" && /GATE-BLOCKED/.test(aResult)
  rec("T16 latching session stays blocked (in-session teeth)", aBlocked, aBlocked ? "A blocked" : "A NOT blocked — teeth lost: " + aResult)
  const bResult = await tryWrite(plugin, root, "src/b.ts", "ses_t16_b")
  const bBlocked = typeof bResult === "string" && /GATE-BLOCKED/.test(bResult)
  rec("T16 different session write does NOT release latch (D3: stale-session release removed)", bBlocked, bBlocked ? "takeover blocked — lock survives foreign writes" : "LATCH LOST on foreign write: " + bResult)
}

// ---- T17: nested test dir (dev/tests/) stays writable while self-RED ----
{
  const root = newFixture("t17-nested-tests")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  mkdirSync(path.join(root, "dev/tests"), { recursive: true })
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  await latchRed(plugin, "ses_t17", root)
  const codeResult = await tryWrite(plugin, root, "src/code.ts", "ses_t17")
  const codeBlocked = typeof codeResult === "string" && /GATE-BLOCKED/.test(codeResult)
  rec("T17 code write blocked while self-RED", codeBlocked, codeBlocked ? "blocked" : "NOT blocked: " + codeResult)
  const goldenOk = (await tryWrite(plugin, root, "dev/tests/golden.json", "ses_t17")) === true
  rec("T17 nested dev/tests/ golden file stays writable while RED", goldenOk, goldenOk ? "evidence fix path open" : "deadlocked nested test dir")
}

// ---- T18: TTL backstop releases a stale latch of the SAME session ----
{
  const root = newFixture("t18-ttl")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  await latchRed(plugin, "ses_t18", root)
  // Age the latched state past the 24h TTL to mimic a parked session.
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const st = JSON.parse(readFileSync(sp, "utf8"))
  st.roots[root].red = { sessionID: "ses_t18", ts: Date.now() - 48 * 3600 * 1000, bad: st.roots[root].red.bad }
  writeFileSync(sp, JSON.stringify(st))
  // Fresh plugin instance reparses the aged state from disk.
  const plugin2 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const ttlReleased = (await tryWrite(plugin2, root, "src/ttl.ts", "ses_t18")) === true
  rec("T18 TTL-expired latch auto-releases without human action", ttlReleased, ttlReleased ? "48h-old latch cleared" : "stale latch persisted")
}

// ---- T19: every release is recorded (state) and surfaced (report) ----
{
  const root = newFixture("t19-trail")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  write(root, "t19-config.json", JSON.stringify({ redTtlHours: -1 })) // force-expire (age > -1h): avoids the age=0 ms race of 0
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  // A latches RED.
  await emit("message.part.updated", { sessionID: "ses_t19_a", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit("message.part.updated", { sessionID: "ses_t19_a", part: { id: "t1", type: "text", text: "Verifier: mm-sensor [image]\n[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1" } })
  await emit("session.idle", { sessionID: "ses_t19_a" })
  // D3: a foreign write alone no longer releases (T16 pins that). Exercise the
  // release JOURNAL through a legitimate reason — redTtlHours:0 expires the
  // latch at B's write (ttl-expiry), and B's report surfaces the trail.
  await emit("message.part.updated", { sessionID: "ses_t19_b", part: { id: "k2", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root, "t19-config.json")
  const bAllowed = (await tryWrite(plugin, root, "src/b.ts", "ses_t19_b")) === true
  delete process.env.VIBEWEAVER_AUDIT_CONFIG
  await emit("message.part.updated", { sessionID: "ses_t19_b", part: { id: "t2", type: "text", text: "[Verification Gate] Verifier: direct read | Loop executed: no | Iterations: 0" } })
  await emit("session.idle", { sessionID: "ses_t19_b" })
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const st = JSON.parse(readFileSync(sp, "utf8"))
  const rel = st.roots[root] && st.roots[root].redReleases
  rec("T19 release recorded in state (redReleases)", bAllowed && Array.isArray(rel) && rel.length >= 1 && rel[rel.length - 1].reason === "ttl-expiry", `releases=${rel ? rel.length : 0} last=${rel && rel.length ? rel[rel.length - 1].reason : "none"}`)
  const report = existsSync(path.join(root, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root, "tests", "gate_audit.md")) : ""
  rec("T19 release trail surfaced in report footer", /## Stale RED releases/.test(report), /## Stale RED releases/.test(report) ? "footer present" : "footer missing")
}

// ---- T20: legacy boolean RED state (pre session-scoping form) self-heals ----
{
  const root = newFixture("t20-legacy")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  // Seed the exact legacy shape pre-fix sessions persisted: bare boolean red.
  write(root, ".vibeweaver/audit-state.json", JSON.stringify({ roots: { [root]: { red: true } }, sessions: {} }))
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const healed = (await tryWrite(plugin, root, "src/legacy.ts", "ses_t20_a")) === true
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const st = JSON.parse(readFileSync(sp, "utf8"))
  const rel = st.roots[root] && st.roots[root].redReleases
  rec(
    "T20 legacy boolean red:true self-heals on first session write (journal: legacy-state)",
    healed && st.roots[root].red == null && Array.isArray(rel) && rel.length >= 1 && rel[0].reason === "legacy-state",
    healed
      ? `red=${JSON.stringify(st.roots[root].red)} reason=${rel && rel[0] ? rel[0].reason : "?"}`
      : "legacy latch deadlocked the next session (takeover path broken)"
  )
}

// =====================================================================
// T24 — loop-guard noop-bash detection (echo-narration stop, 2026-09-28)
// The reported failure mode: intent-narration loops where the model
// announces a tool call ("use Read now", "final", "grading") via bare
// `echo` bash calls instead of emitting the tool call. Every echo
// succeeds, strings vary, so byte-repeat and failure detectors stay
// silent. Detector contract: >=4 trailing no-op bash calls (literal
// echo/printf/true/:, no side effects) -> one corrective intervention.
// =====================================================================
{
  const mkTools = (cmds) => cmds.map((c, i) => ({ tool: "bash", command: c, t: i + 1 }))
  const hasNoop = typeof noopBashFinding === "function" && typeof isNoopBashCommand === "function"

  // ---- T24a — threshold: 4 trailing literal echoes (varying strings) -> finding ----
  const four = ['echo "use read tool now"', "echo final", "echo grading", "echo read"]
  const f4 = hasNoop ? noopBashFinding(mkTools(four)) : undefined
  rec("T24a 4 consecutive literal echoes -> noop-bash finding", !!f4 && f4.kind === "noop-bash", hasNoop ? (f4 ? `kind=${f4.kind}` : "null") : "detector missing (RED)")
  const f3 = hasNoop ? noopBashFinding(mkTools(four.slice(0, 3))) : undefined
  rec("T24a 3 consecutive echoes -> no finding", f3 === null, hasNoop ? (f3 ? `kind=${f3.kind}` : "null") : "detector missing (RED)")

  // ---- T24b — classifier: literal no-op vs real command ----
  const noopYes = [
    'echo "use read tool now"', "echo done", "echo 'final'", 'printf "x"', "true", ":", "echo -n done", 'echo "1"',
    "echo attempting Read tool on screenshot",
    'printf "final\\n"',        // escape in double quotes = stdout formatting, still no-op (F1)
    "printf 'a\\nb'",           // escape in single quotes = literal, no-op
    "echo final;",             // trailing lone `;` (F2)
    "echo a # note",           // trailing comment (F2)
    "/bin/echo final",         // absolute path (F2)
    "echo",                    // bare echo
    'echo ""',                 // empty-arg echo
  ]
  const noopNo = [
    'echo "x" > f',            // redirect
    "echo a | wc",             // pipe
    'echo "$(date)"',          // command substitution
    "echo a && echo b",        // chain
    "echo hi; ls",             // chain
    "ls -la",                  // non-echo
    "cat f.txt",               // non-echo
    "bash script/linux/start.sh", // non-echo
    "echo `date`",             // backtick substitution
    "echo $HOME",              // expansion
    "echo a\nls",              // newline-chained second command
    "true extra",              // bare true with args
    ": extra",                 // bare : with args
    'echo "unterminated',      // unclosed double quote
    "echo 'unterminated",      // unclosed single quote
    "echo a; ls;",             // inner chain survives trailing-; strip
  ]
  const misNoop = noopYes.filter((c) => !hasNoop || !isNoopBashCommand(c))
  const misReal = noopNo.filter((c) => !hasNoop || isNoopBashCommand(c))
  rec("T24b literal echo/printf/true/: classified no-op", misNoop.length === 0, misNoop.join(" | ") || "all 16 correct")
  rec("T24b redirect/pipe/subst/chain/escape-quote/non-echo classified real", misReal.length === 0, misReal.join(" | ") || "all 16 correct")

  // ---- T24c — reset semantics: interleaved real action breaks the run ----
  const dispersed = [...mkTools(["echo a", "echo b"]), { tool: "bash", command: "ls", t: 3 }, ...mkTools(["echo c", "echo d"])]
  const fd = hasNoop ? noopBashFinding(dispersed) : undefined
  rec("T24c real command interleaved resets run (4 dispersed echoes -> null)", fd === null, hasNoop ? (fd ? `kind=${fd.kind}` : "null") : "detector missing (RED)")
  const viaRead = [...mkTools(["echo a", "echo b"]), { tool: "read", filePath: "/x.png", t: 3 }, ...mkTools(["echo c", "echo d"])]
  const fr = hasNoop ? noopBashFinding(viaRead) : undefined
  rec("T24c non-bash tool interleaved resets run", fr === null, hasNoop ? (fr ? `kind=${fr.kind}` : "null") : "detector missing (RED)")

  // ---- T24d — streaming re-observations of the same tool part never inflate the run ----
  const reobs = [1, 2, 3, 4].map((i) => ({ tool: "bash", command: 'echo "final"', pid: "p1", t: i }))
  const fDup = hasNoop ? noopBashFinding(reobs) : undefined
  rec("T24d same part id re-observed 4x -> no finding (dedup)", fDup === null, hasNoop ? (fDup ? `kind=${fDup.kind}` : "null") : "detector missing (RED)")
  const twoDistinct = [...reobs, { tool: "bash", command: 'echo "done"', pid: "p2", t: 5 }]
  const fTwo = hasNoop ? noopBashFinding(twoDistinct) : undefined
  rec("T24d 2 distinct calls + re-observations -> no finding", fTwo === null, hasNoop ? (fTwo ? `kind=${fTwo.kind}` : "null") : "detector missing (RED)")
  const fourDistinct = [1, 2, 3, 4].map((i) => ({ tool: "bash", command: `echo "n${i}"`, pid: `p${i}`, t: i }))
  const f4d = hasNoop ? noopBashFinding(fourDistinct) : undefined
  rec("T24d 4 distinct part ids -> finding", !!f4d && f4d.kind === "noop-bash", hasNoop ? (f4d ? `kind=${f4d.kind}` : "null") : "detector missing (RED)")

  // ---- T24e — v1 adapter integration: exactly one intervention per episode, budget 2 ----
  {
    const root24 = newFixture("t24-noop")
    write(root24, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin24 = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root24,
    })
    const emitBash = (sid, id, command) =>
      plugin24.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "bash", state: { status: "completed", input: { command } } } },
        },
      })
    const sid = "ses_t24"
    for (let i = 0; i < 4; i++) await emitBash(sid, `k${i}`, `echo "final ${i}"`)
    rec(
      "T24e 4 echoes through adapter -> exactly one intervention (abort+prompt)",
      calls.abort === 1 && calls.prompts.length === 1,
      `abort=${calls.abort} prompts=${calls.prompts.length}`
    )
    const ptext = calls.prompts[0] || ""
    rec(
      "T24e corrective text: echo narration is not an action + demands real tool call or completion output",
      /echo/i.test(ptext) && /(tool call|real action)/i.test(ptext) && /(completion output|final completion)/i.test(ptext),
      ptext.slice(0, 140)
    )
    rec("T24e corrective text mandates the stall declaration (F7 contract)", /- stall: noop-bash/i.test(ptext) && /verification_log/i.test(ptext), ptext.slice(0, 140))
    for (let i = 4; i < 6; i++) await emitBash(sid, `k${i}`, `echo "still ${i}"`)
    rec("T24e continued degeneration -> no thrash (still 1 intervention)", calls.abort === 1, `abort=${calls.abort}`)
    await emitBash(sid, "k_real", "ls -la")
    for (let i = 0; i < 4; i++) await emitBash(sid, `q${i}`, `echo "second ${i}"`)
    rec("T24e re-arms on real action -> 2nd intervention (budget 2)", calls.abort === 2, `abort=${calls.abort}`)
    await emitBash(sid, "k_real2", "ls -la")
    for (let i = 0; i < 4; i++) await emitBash(sid, `r${i}`, `echo "third ${i}"`)
    const budgetLog = calls.logs.some((m) => /budget exhausted/i.test(m))
    rec("T24e 3rd episode beyond budget -> log-only, no abort", calls.abort === 2 && budgetLog, `abort=${calls.abort} budgetLog=${budgetLog}`)
  }

  // ---- T24f — adapter-level part re-observation (state updates) never triggers ----
  {
    const root24f = newFixture("t24-reobs")
    write(root24f, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: 0 }
    const plugin24f = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {
            calls.prompts++
          },
        },
      },
      directory: root24f,
    })
    const sid = "ses_t24f"
    // the SAME tool part observed 4x (running -> completed state transitions)
    for (const status of ["pending", "running", "running", "completed"]) {
      await plugin24f.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: "part1", type: "tool", tool: "bash", state: { status, input: { command: 'echo "final"' } } } },
        },
      })
    }
    rec("T24f same part re-observed 4x through adapter -> no intervention", calls.abort === 0 && calls.prompts === 0, `abort=${calls.abort} prompts=${calls.prompts}`)
    // 4 DISTINCT parts do trigger
    for (let i = 0; i < 4; i++) {
      await plugin24f.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `d${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: `echo "go ${i}"` } } } },
        },
      })
    }
    rec("T24f 4 distinct parts through adapter -> intervention fires", calls.abort === 1, `abort=${calls.abort}`)
  }

  // ---- T24g — VIBEWEAVER_LOOPGUARD=off disables the tool-channel guard ----
  {
    const root24g = newFixture("t24-off")
    write(root24g, "tests/verification_log.md", "placeholder — no iter entries\n")
    const prev = process.env.VIBEWEAVER_LOOPGUARD
    process.env.VIBEWEAVER_LOOPGUARD = "off"
    const calls = { abort: 0, prompts: 0 }
    const plugin24g = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {
            calls.prompts++
          },
        },
      },
      directory: root24g,
    })
    for (let i = 0; i < 5; i++) {
      await plugin24g.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t24g", part: { id: `x${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: `echo "off ${i}"` } } } },
        },
      })
    }
    if (prev === undefined) delete process.env.VIBEWEAVER_LOOPGUARD
    else process.env.VIBEWEAVER_LOOPGUARD = prev
    rec("T24g VIBEWEAVER_LOOPGUARD=off -> guard silent", calls.abort === 0 && calls.prompts === 0, `abort=${calls.abort}`)
  }

  // ---- T24h — text channel regression + per-channel budget isolation ----
  {
    const root24h = newFixture("t24-mixed")
    write(root24h, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin24h = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root24h,
    })
    const emitText = (sid, id, text) =>
      plugin24h.event({ event: { type: "message.part.updated", properties: { sessionID: sid, part: { id, type: "text", text } } } })
    const emitBash = (sid, id, command) =>
      plugin24h.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "bash", state: { status: "completed", input: { command } } } },
        },
      })
    const sid = "ses_t24h"
    // text-channel episode: 4 identical trailing lines (p=1 repeat bar met)
    await emitText(sid, "t0", "degenerate line text here\n".repeat(4))
    rec("T24h text channel still fires after refactor (regression)", calls.abort === 1, `abort=${calls.abort}`)
    // text channel exhausts its OWN budget (2) — tool channel must NOT be starved
    await emitText(sid, "t1", "ok single line\n")
    await emitText(sid, "t2", "second degenerate line\n".repeat(4))
    rec("T24h text budget 2nd episode fires", calls.abort === 2, `abort=${calls.abort}`)
    await emitText(sid, "t3", "ok again\n")
    await emitText(sid, "t4", "third degenerate line\n".repeat(4))
    const textBudgetLog = calls.logs.some((m) => /budget exhausted/i.test(m) && /\/text\)/.test(m))
    rec("T24h text 3rd episode -> log-only (budget 2/channel)", calls.abort === 2 && textBudgetLog, `abort=${calls.abort} log=${textBudgetLog}`)
    // tool channel unaffected by exhausted text budget
    for (let i = 0; i < 4; i++) await emitBash(sid, `b${i}`, `echo "iso ${i}"`)
    rec("T24h tool channel not starved by text budget (per-channel)", calls.abort === 3, `abort=${calls.abort}`)
  }

  // ---- T24i — trailing status-only re-observation never masks the run (R1#4) ----
  {
    const root24i = newFixture("t24-mask")
    write(root24i, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: 0 }
    const plugin24i = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {
            calls.prompts++
          },
        },
      },
      directory: root24i,
    })
    const sid = "ses_t24i"
    for (let i = 0; i < 4; i++) {
      await plugin24i.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `m${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: `echo "mask ${i}"` } } } },
        },
      })
    }
    // status-only re-observation of the LAST part (no input at all)
    await plugin24i.event({
      event: {
        type: "message.part.updated",
        properties: { sessionID: sid, part: { id: "m3", type: "tool", tool: "bash", state: { status: "running" } } },
      },
    })
    rec("T24i unknown trailing observation does not mask the run", calls.abort === 1 && calls.prompts === 1, `abort=${calls.abort}`)
  }

  // ---- T24j — truncated recorded command can never forge a literal (F10) ----
  {
    const root24j = newFixture("t24-trunc")
    write(root24j, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0 }
    const plugin24j = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {},
        },
      },
      directory: root24j,
    })
    const sid = "ses_t24j"
    // each command exceeds IN_CAP(400): raw is `echo "x" && ls …padding`;
    // naive truncation would cut after the closing quote and forge a literal
    const long = 'echo "x" && ls ' + "p".repeat(420)
    for (let i = 0; i < 4; i++) {
      await plugin24j.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `j${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: long } } } },
        },
      })
    }
    rec("T24j truncated commands never count as no-op", calls.abort === 0, `abort=${calls.abort}`)
    if (hasNoop) {
      const forged = [1, 2, 3, 4].map((i) => ({ tool: "bash", command: 'echo "x"', truncated: true, pid: `f${i}`, t: i }))
      rec("T24j unit: truncated flag breaks the run", noopBashFinding(forged) === null, "null expected")
    } else {
      rec("T24j unit: truncated flag breaks the run", false, "detector missing (RED)")
    }
  }

  // ---- T24k — text tail-noise + turn-boundary episode ("Stop it." wall, 2026-10-10) ----
  // Reported failure: a model streaming "Stop it. " forever produced a full
  // wall despite the loop-guard. Three holes (probe-reproduced):
  //   G1 trailing whitespace/newline after a single-line runaway breaks the
  //      end-anchored period seed (the noisy end is the seed's only
  //      occurrence) -> MISS;
  //   G2 the char-path gate's 512-monster-line threshold hides inline
  //      runaways <=512 chars in newline-rich context -> MISS;
  //   G3 the episode latch only re-arms on CLEAN text, so a model that
  //      degenerates again in a fresh turn gets no further intervention.
  // Bars unchanged: block x3 / 2x repeat / short-unit runs stay clean.
  {
    const mkT24k = async (name) => {
      const root = newFixture(name)
      write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
      const calls = { abort: 0, prompts: [], logs: [] }
      const plugin = await VibeweaverAudit({
        client: {
          app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
          session: {
            abort: async () => {
              calls.abort++
            },
            prompt: async (args) => {
              const parts = args && args.body && args.body.parts
              calls.prompts.push((parts && parts[0] && parts[0].text) || "")
            },
          },
        },
        directory: root,
      })
      const emitText = (sid, id, text, mid) =>
        plugin.event({
          event: {
            type: "message.part.updated",
            properties: { sessionID: sid, part: mid ? { id, type: "text", text, messageID: mid } : { id, type: "text", text } },
          },
        })
      const emitBash = (sid, id, command, mid) =>
        plugin.event({
          event: {
            type: "message.part.updated",
            properties: { sessionID: sid, part: mid ? { id, type: "tool", tool: "bash", messageID: mid, state: { status: "completed", input: { command } } } : { id, type: "tool", tool: "bash", state: { status: "completed", input: { command } } } },
          },
        })
      return { calls, emitText, emitBash }
    }
    const wall = (n) => "Stop it. ".repeat(n)

    {
      const { calls, emitText } = await mkT24k("t24k-nl")
      await emitText("s_nl", "t1", wall(300) + "\n")
      rec("T24k single-line runaway ending in \\n -> intervention (G1 tail-noise)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-sp")
      await emitText("s_sp", "t1", wall(300) + " ")
      rec("T24k single-line runaway ending in extra space -> intervention (G1 tail-noise)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-dnl")
      await emitText("s_dnl", "t1", wall(300) + "\n\n")
      rec("T24k runaway ending in blank line -> intervention (G1 tail-noise)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-inline")
      await emitText("s_in", "t1", "a line here\nb line there\nc line x\nd line y\n" + wall(50) + "\n")
      rec("T24k prose + 450-char inline runaway + newline -> intervention (G2 gate)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-inline-blank")
      await emitText("s_ib", "t1", "a line here\nb line there\nc line x\nd line y\n" + wall(50) + "\n\n")
      rec("T24k prose + inline runaway + trailing BLANK line -> intervention (review C1 gate/trim)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-inline-ws")
      await emitText("s_iw", "t1", "a line here\nb line there\nc line x\nd line y\n" + wall(50) + "\n   ")
      rec("T24k prose + inline runaway + whitespace-only last line -> intervention (review C1)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-crlf")
      await emitText("s_cr", "t1", wall(300) + "\r\n")
      rec("T24k runaway ending in \\r\\n -> intervention (review M2 trim class)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-nbsp")
      await emitText("s_nb", "t1", wall(300) + "\u00a0")
      rec("T24k runaway ending in NBSP -> intervention (review M2 trim class)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-thresh")
      await emitText("s_lo", "t1", "a line here\nb line there\nc line x\nd line y\n" + wall(28) + "\n")
      rec("T24k 252-char inline run below the 256 context gate -> stays clean (review I3 pin)", calls.abort === 0, `abort=${calls.abort}`)
      await emitText("s_lo", "t2", "a line here\nb line there\nc line x\nd line y\n" + wall(29) + "\n")
      rec("T24k 261-char inline run at/above the 256 context gate -> intervention (review I3 pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-thresh-exact")
      await emitText("s_te", "t1", "a line here\nb line there\nc line x\nd line y\n" + "abcde".repeat(51) + "\n")
      rec("T24k 255-char last line below the 256 gate -> clean (review N5 exact pin)", calls.abort === 0, `abort=${calls.abort}`)
      await emitText("s_te", "t2", "a line here\nb line there\nc line x\nd line y\n" + "abcdefgh".repeat(32) + "\n")
      rec("T24k 256-char last line at the 256 gate -> intervention (review N5 exact pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-part")
      await emitText("s_pt", "t1", wall(300) + "Stop it")
      rec("T24k runaway truncated mid-unit -> intervention (pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-fp3")
      await emitText("s_fp3", "t1", '<div className="foo">bar</div>\n'.repeat(3))
      rec("T24k repeated JSX line x3 stays clean (FP bar)", calls.abort === 0, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-fp2")
      await emitText("s_fp2", "t1", "the same trailing line repeated twice only\n".repeat(2))
      rec("T24k 2x line repetition stays clean (below bar)", calls.abort === 0, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-fpx")
      await emitText("s_fpx", "t1", "xylo. ".repeat(15))
      rec("T24k short-unit inline run below x4-of-32 floor stays clean", calls.abort === 0, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-turn")
      await emitText("s_tr", "t1", wall(300), "m1")
      rec("T24k wall in turn m1 -> 1 intervention", calls.abort === 1, `abort=${calls.abort}`)
      await emitText("s_tr", "t2", wall(300), "m1")
      rec("T24k same-turn continuation never re-fires (no-thrash)", calls.abort === 1, `abort=${calls.abort}`)
      await emitText("s_tr", "t3", wall(300), "m2")
      rec("T24k wall recurring in NEW turn m2 -> 2nd intervention (G3)", calls.abort === 2, `abort=${calls.abort}`)
      await emitText("s_tr", "t4", wall(300), "m3")
      const budgetLog = calls.logs.some((m) => /budget exhausted/i.test(m) && /\/text\)/.test(m))
      rec("T24k 3rd turn beyond budget -> log-only (budget 2/channel)", calls.abort === 2 && budgetLog, `abort=${calls.abort} budgetLog=${budgetLog}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-zwsp")
      await emitText("s_zw", "t1", wall(300) + "\u200b")
      rec("T24k runaway ending in ZWSP -> intervention (review M2 trim class)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText, emitBash } = await mkT24k("t24k-xchan")
      await emitText("s_x", "t1", wall(300), "m1")
      for (let i = 0; i < 4; i++) await emitBash("s_x", `k${i}`, `echo "xchan ${i}"`, "m2")
      rec("T24k cross-channel: text fire(m1) then tool fire(m2) both intervene", calls.abort === 2, `abort=${calls.abort}`)
      await emitText("s_x", "t2", wall(300), "m2")
      rec("T24k cross-channel turn re-arm not masked by tool-channel fire (review I1 fireMsgID)", calls.abort === 3, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-hardbreak")
      await emitText("s_hb", "t1", "Note: the request failed.  \n".repeat(60))
      rec("T24k markdown hard-break wall (uniform trailing spaces x60) -> intervention (review N1 line-align pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-padlog")
      await emitText("s_pl", "t1", "WARN retry scheduled for job id=42  \n".repeat(50))
      rec("T24k padded log wall (uniform trailing spaces x50) -> intervention (review N1 line-align pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-blankblk")
      await emitText("s_bb", "t1", "## Summary\n\nThe same summary text here.\n\n".repeat(3))
      rec("T24k blank-terminated block x3 -> intervention (multi-line >=3x bar, review N1 pin)", calls.abort === 1, `abort=${calls.abort}`)
    }
    {
      const { calls, emitText } = await mkT24k("t24k-dup")
      await emitText("d1", "t1", wall(300), "m1")
      rec("T24k dup setup: wall fires once", calls.abort === 1, `abort=${calls.abort}`)
      await emitText("d1", "t1", wall(300), "u1")
      rec("T24k duplicate re-emission with flipped messageID never re-fires (review C2 unchanged-state)", calls.abort === 1, `abort=${calls.abort}`)
    }
  }
}

// =====================================================================
// T24l — loop-guard blind-spot wave (2026-10-10): reasoning channel,
// counter-bearing walls, per-turn ceiling, punctuation walls.
// Blind-spot research: hermes #97630 (reasoning-only "!!!!" wall), hermes
// #127234 (unit+counter loops answer "not yet" forever; the safe fix is an
// absolute per-turn ceiling), SpecRA taxonomy (incremental-variation
// structural repetition = 46% of 813 real degenerate samples), claude-code
// #82803 (single-char walls). FP bars from the same sources: digit-strip
// normalization false-flags legit numeric batch output (hermes) — hence
// strict +1 on EVERY digit run; timestamp logs tick only the last field.
// =====================================================================
{
  const mkT24l = async (name, cfg) => {
    const root = newFixture(name)
    write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
    if (cfg) {
      write(root, "audit-config.json", JSON.stringify(cfg))
      process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root, "audit-config.json")
    }
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root,
    })
    const emit = (sid, part) => plugin.event({ event: { type: "message.part.updated", properties: { sessionID: sid, part } } })
    const event = (type, properties) => plugin.event({ event: { type, properties } })
    const emitText = (sid, id, text, mid) => emit(sid, mid ? { id, type: "text", text, messageID: mid } : { id, type: "text", text })
    const emitReasoning = (sid, id, text, mid) => emit(sid, mid ? { id, type: "reasoning", text, messageID: mid } : { id, type: "reasoning", text })
    return { calls, emit, event, emitText, emitReasoning }
  }
  const wall = (n) => "Stop it. ".repeat(n)
  const letters26 = (n) => {
    let s = ""
    do {
      s = String.fromCharCode(97 + (n % 26)) + s
      n = Math.floor(n / 26)
    } while (n > 0)
    return s
  }
  const proseLine = (i) => "prose line " + letters26(i) + " assorted words and more filler tail"
  const prose = (n) => Array.from({ length: n }, (_, i) => proseLine(i)).join("\n")
  const proseRange = (start, n) => Array.from({ length: n }, (_, i) => proseLine(start + i)).join("\n")

  {
    const { calls, emitReasoning, emitText } = await mkT24l("t24l-reason")
    await emitReasoning("s_r", "r1", wall(300), "m1")
    rec("T24l reasoning-channel wall -> intervention (P0-a, hermes #97630 shape)", calls.abort === 1, `abort=${calls.abort}`)
    await emitText("s_r", "t1", wall(300), "m2")
    rec("T24l reasoning budget independent of text channel (per-channel 2/session)", calls.abort === 2, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-counter")
    await emitText("s_c", "t1", Array.from({ length: 200 }, (_, i) => `The backlog item ${i} is pending review.`).join("\n"), "m1")
    rec("T24l unit+counter wall x200 -> intervention (P0-b, SpecRA 46% class)", calls.abort === 1, `abort=${calls.abort}`)
    await emitText("s_c", "t2", Array.from({ length: 20 }, (_, i) => `queue entry ${i} awaits triage`).join("\n") + "\nDone.", "m2")
    rec("T24l counter wall + trailing status line -> intervention (review I1 trailing-tolerance)", calls.abort === 2, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-shapebound")
    await emitText("s_sb", "t1", Array.from({ length: 15 }, (_, i) => `case ${i + 1} executed`).join("\n"), "m1")
    rec("T24l same-shape counter run x15 stays clean (LOOP_SHAPE_MIN boundary)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_sb", "t2", Array.from({ length: 16 }, (_, i) => `case ${i + 1} executed`).join("\n"), "m2")
    rec("T24l same-shape counter run x16 -> intervention (LOOP_SHAPE_MIN boundary)", calls.abort === 1, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-counterfp")
    await emitText("s_cf", "t1", Array.from({ length: 30 }, (_, i) => `2026-10-10 12:00:${String(i).padStart(2, "0")} INFO job completed`).join("\n"), "m1")
    rec("T24l timestamp log x30 stays clean (only last field ticks — strict +1 FP bar)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_cf", "t2", Array.from({ length: 30 }, (_, i) => `page ${i + 1} of 30 rendered`).join("\n"), "m2")
    rec("T24l page N of M x30 stays clean (M constant breaks strict +1)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_cf", "t3", Array.from({ length: 5 }, (_, i) => `test${i + 1} passed`).join("\n"), "m3")
    rec("T24l short same-shape index list x5 stays clean (below LOOP_SHAPE_MIN)", calls.abort === 0, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-ceiling")
    await emitText("s_u", "t1", prose(1600), "m1")
    rec("T24l 80KB non-degenerate visible turn output stays clean (W10 ceiling is 256KB)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_u", "t2", prose(7000), "m2")
    rec("T24l >256KB non-degenerate visible turn output -> runaway intervention", calls.abort === 1, `abort=${calls.abort}`)
    rec("T24l runaway corrective prompt names the 256KB ceiling", /runaway|exceeded|262144|256KB/i.test(calls.prompts[0] || ""), (calls.prompts[0] || "").slice(0, 120))
  }
  {
    const { calls, emitText, emitReasoning } = await mkT24l("t24l-reason-volume")
    await emitReasoning("s_rv", "r1", prose(1600), "m1")
    rec("T24l 80KB reasoning-only volume does NOT trip the visible-output ceiling", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_rv", "t1", prose(1600), "m2")
    rec("T24l 80KB visible text stays clean (W10 ceiling raised)", calls.abort === 0, `abort=${calls.abort}`)
    await emitReasoning("s_rv", "r2", prose(25000), "m3")
    rec("T24l >1MB non-periodic reasoning hits the high reasoning backstop", calls.abort === 1, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-ceiling2")
    await emitText("s_u2", "t1", prose(900), "m1")
    rec("T24l 45KB non-degenerate turn output stays clean (below 256KB ceiling)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_u2", "t2", prose(900), "m2")
    rec("T24l two sub-ceiling turns stay clean (review M3 — kills session-total mutant)", calls.abort === 0, `abort=${calls.abort}`)
  }
  {
    // W11 P1-3: a host that changes messageID per delta/part must not reset
    // the ceiling on every chunk.
    const { calls, emitText } = await mkT24l("t24l-churn-visible")
    for (let i = 0; i < 220; i++) {
      await emitText("s_churn", `t${i}`, proseRange(i * 60, 60), `m${i}`)
      if (calls.abort) break
    }
    rec("T24l >600KB visible text with per-chunk messageID churn -> ceiling fires",
      calls.abort >= 1 && calls.logs.some((m) => /runaway|ceiling/i.test(m)),
      `abort=${calls.abort} logs=${calls.logs.length}`)
  }
  {
    const { calls, emitReasoning } = await mkT24l("t24l-churn-reasoning")
    for (let i = 0; i < 700; i++) {
      await emitReasoning("s_churn_r", `r${i}`, proseRange(15000 + i * 60, 60), `mr${i}`)
      if (calls.abort) break
    }
    rec("T24l >2MB reasoning with per-chunk messageID churn -> reasoning backstop fires",
      calls.abort >= 1 && calls.logs.some((m) => /reasoning|ceiling|runaway/i.test(m)),
      `abort=${calls.abort} logs=${calls.logs.length}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-ceiling-cfg", { loopGuardTurnCeilingBytes: 65536 })
    await emitText("s_uc", "t1", prose(1600), "m1")
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    rec("T24l loopGuardTurnCeilingBytes=65536 lowers the visible ceiling (80KB fires)", calls.abort === 1, `abort=${calls.abort}`)
  }
  {
    const { calls, event, emitText } = await mkT24l("t24l-ceiling3")
    await emitText("s_u3", "t1", prose(1600))
    await event("message.updated", { sessionID: "s_u3", info: { id: "u-reset", role: "user" } })
    await emitText("s_u3", "t2", prose(1600))
    rec("T24l id-less host resets the ceiling at a user turn", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_u3", "t3", prose(7000))
    rec("T24l runaway WITHOUT messageIDs -> intervention (review Critical id-less dead ceiling)", calls.abort === 1, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-ceiling4")
    await emitText("s_u4", "t1", wall(300), "m1")
    rec("T24l setup: organic wall fires once in turn m1", calls.abort === 1, `abort=${calls.abort}`)
    await emitText("s_u4", "t2", prose(7000), "m1")
    rec("T24l same turn exceeds ceiling after an organic fire -> runaway still intervenes (review I2a latch bypass)", calls.abort === 2, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-ceiling5")
    await emitText("s_u5", "t1", wall(300), "m1")
    await emitText("s_u5", "t2", wall(30000), "m1")
    rec("T24l latched wall re-run past the ceiling -> runaway rescue (re-review N1)", calls.abort === 2, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-punct")
    await emitText("s_p", "t1", "!".repeat(4000), "m1")
    rec("T24l punctuation wall '!'x4000 -> intervention (P2, claude-code char-spam class)", calls.abort === 1, `abort=${calls.abort}`)
    await emitText("s_p", "t2", "!".repeat(2100), "m2")
    rec("T24l 2.1KB punct wall alone -> intervention (LOOP_PUNCT_WALL_MIN boundary)", calls.abort === 2, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-punct2")
    await emitText("s_p2", "t1", "!!! ".repeat(800), "m1")
    rec("T24l punctuation wall '!!! 'x800 -> intervention (P2)", calls.abort === 1, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-punct3")
    await emitText("s_p3", "t1", "report data " + "x".repeat(2500) + " " + "=".repeat(128), "m1")
    rec("T24l big doc + 128-char punct burst stays clean (review I4 — wall-size not tail-size bar)", calls.abort === 0, `abort=${calls.abort}`)
  }
  {
    const { calls, emitText } = await mkT24l("t24l-punct4")
    await emitText("s_p4", "t1", "----------\n".repeat(3), "m1")
    rec("T24l short punct separator x3 stays clean (below LOOP_PUNCT_WALL_MIN)", calls.abort === 0, `abort=${calls.abort}`)
    await emitText("s_p4", "t2", "!".repeat(2048), "m2")
    rec("T24l exact 2048-char punct wall -> intervention (LOOP_PUNCT_WALL_MIN exact pin, re-review N6)", calls.abort === 1, `abort=${calls.abort}`)
  }
}

// ---- T24m — v2 dual-path ingestion (review C1): the same reasoning content
// arriving via session.reasoning.delta AND session.message.content.updated
// must reconcile into ONE buffer entry and count ONCE in turnChars. The "#r"
// pid suffix double-counted (45KB real output looked like 90KB -> runaway
// aborted a healthy turn at half the ceiling).
{
  const mkBus = () => {
    const q = []
    let waiting = null
    return {
      subscribe() {
        return {
          [Symbol.asyncIterator]() {
            return this
          },
          next() {
            if (q.length) return Promise.resolve({ done: false, value: q.shift() })
            return new Promise((res) => {
              waiting = () => res(q.length ? { done: false, value: q.shift() } : { done: true })
            })
          },
          return() {
            return Promise.resolve({ done: true })
          },
        }
      },
      emit(e) {
        q.push(e)
        if (waiting) {
          const w = waiting
          waiting = null
          w()
        }
      },
    }
  }
  const mod = auditModule && auditModule.default
  if (mod && typeof mod.setup === "function") {
    const root = newFixture("t24m-v2dual")
    write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
    const bus = mkBus()
    const calls = { abort: 0 }
    const ctx = {
      location: { directory: root },
      tool: { hook: async () => ({ dispose: async () => {} }) },
      event: { subscribe: () => bus.subscribe() },
      session: {
        interrupt: async () => {
          calls.abort++
        },
        prompt: async () => {},
      },
    }
    await mod.setup(ctx)
    let acc = ""
    for (let i = 0; i < 650; i++) {
      const frag = "reasoning step " + "abcdefghij".split("")[(i * 7) % 10] + String.fromCharCode(97 + (i % 26)) + " considers assorted angles of the problem and notes details "
      acc += frag
      bus.emit({ type: "session.reasoning.delta", data: { sessionID: "s_v2", assistantMessageID: "m1", delta: frag } })
      bus.emit({
        type: "session.message.content.updated",
        data: { sessionID: "s_v2", messageID: "m1", content: [{ type: "reasoning", text: acc, content: acc }] },
      })
    }
    await new Promise((r) => setTimeout(r, 80))
    rec("T24m dual-path reasoning ingestion counts once (review C1) — 45KB stays clean", calls.abort === 0, `abort=${calls.abort}`)
    bus.emit({ type: "session.reasoning.delta", data: { sessionID: "s_v2", assistantMessageID: "m2", delta: "Stop it. ".repeat(300) } })
    await new Promise((r) => setTimeout(r, 80))
    rec("T24m sanity: the v2 reasoning-delta channel is actually wired (wall -> intervention)", calls.abort === 1, `abort=${calls.abort}`)
  } else {
    rec("T24m dual-path reasoning ingestion counts once (review C1)", false, "default.setup missing")
  }
}

// T29-T31 — same-session latch escape (multi-wave DOC→CODE deadlock,
// 2026-10-02). A latch must keep in-session teeth mid-wave, but it must
// never force the next task to wait for ANOTHER session, a 24h TTL, or
// an env-off restart. Two in-session semantics:
//   new-task key — rewriting tests/acceptance.md AFTER the latch (the
//     protocol's own first action of a new task; tests/ stays writable)
//     releases the latch, journaled as "new-task";
//   BAD-signature guard — a final re-audit whose BAD set is unchanged
//     (stale-buffer residue) neither refreshes a live latch's ts nor
//     resurrects a released one (the takeover/TTL release stays durable).
// =====================================================================

// ---- T29: the new-task release key (and its pre-latch control) ----
{
  const root = newFixture("t29-newtask")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  write(root, "tests/acceptance.md", "wave1 criteria\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  await latchRed(plugin, "ses_t29", root)
  const blocked = await tryWrite(plugin, root, "src/a.ts", "ses_t29")
  rec(
    "T29a pre-latch acceptance does NOT release (in-session teeth intact)",
    typeof blocked === "string" && /GATE-BLOCKED/.test(blocked),
    blocked === true ? "TEETH LOST — write landed" : "blocked"
  )
  // The session starts a NEW task per protocol: Step 1 rewrites the
  // acceptance criteria (tests/ is writable under the latch). The 5ms gap
  // models a real model-turn boundary: same-millisecond rewrites are a
  // designed conservative boundary (floor(mtime) > latch.ts is strict, so
  // a same-ms rewrite resolves to "no release" — teeth win the tie).
  await new Promise((r) => setTimeout(r, 5))
  write(root, "tests/acceptance.md", "wave2 criteria — new task begins\n")
  const allowed = (await tryWrite(plugin, root, "src/b.ts", "ses_t29")) === true
  const st25 = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8")).roots[root]
  const rel = (st25.redReleases || []).find((r) => r.reason === "new-task")
  rec(
    "T29b post-latch acceptance rewrite releases the latch in-session (journal: new-task)",
    allowed && st25.red == null && !!rel,
    allowed ? (rel ? `released, journaled by ${rel.by}` : "released but journal MISSING") : "deadlocked: " + JSON.stringify(st25.red)
  )
}

// ---- T30: same-signature final re-audits never refresh/resurrect ----
{
  const root = newFixture("t30-samesig")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  await latchRed(plugin, "ses_t30", root)
  // Age the latch 1h on disk and reload it into a fresh machine instance,
  // so a ts refresh (Date.now()) is unambiguous even within one millisecond.
  // The acceptance.md is backdated BEFORE the aged latch ts: this scenario is
  // "same task still open" — a pre-latch acceptance must never look like the
  // new-task release key (its mtime is compared against latch.ts).
  const sp = path.join(root, ".vibeweaver", "audit-state.json")
  const st0 = JSON.parse(readFileSync(sp, "utf8"))
  st0.roots[root].red.ts = Date.now() - 3_600_000
  writeFileSync(sp, JSON.stringify(st0))
  const old = new Date(Date.now() - 2 * 3600 * 1000)
  utimesSync(path.join(root, "tests", "acceptance.md"), old, old)
  const plugin2 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const ts0 = JSON.parse(readFileSync(sp, "utf8")).roots[root].red.ts
  // idle on the RELOADED machine (it holds the aged latch); plugin1's
  // in-memory state still has the fresh ts and would poison the comparison.
  const emit2 = (type, props) => plugin2.event({ event: { type, properties: props } })
  await emit2("session.idle", { sessionID: "ses_t30" })
  const st1 = JSON.parse(readFileSync(sp, "utf8")).roots[root]
  rec(
    "T30a same-sig idle final audit does not refresh a live latch's ts (TTL not starved)",
    !!st1.red && st1.red.ts === ts0,
    st1.red ? (st1.red.ts === ts0 ? "ts preserved" : `ts refreshed ${ts0} -> ${st1.red.ts}`) : "latch vanished"
  )
  // A different session takes over after a legal release (D3: foreign writes
  // don't release — redTtlHours:-1 force-expires the latch); then the original
  // session idles again — the released latch must NOT resurrect.
  write(root, "t30-config.json", JSON.stringify({ redTtlHours: -1 }))
  process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root, "t30-config.json")
  await tryWrite(plugin2, root, "src/b.ts", "ses_t30_b")
  delete process.env.VIBEWEAVER_AUDIT_CONFIG
  await emit2("session.idle", { sessionID: "ses_t30" })
  const st2 = JSON.parse(readFileSync(sp, "utf8")).roots[root]
  rec(
    "T30b same-sig idle final audit does not resurrect a released latch (treadmill dead)",
    st2.red == null,
    st2.red ? `RESURRECTED ts=${st2.red.ts}` : "release stayed durable"
  )
}

// ---- T31: same-session DOC→CODE wave transition e2e ----
{
  const root = newFixture("t31-wavetransition")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  // wave1 completes (badly) -> final RED latch.
  await latchRed(plugin, "ses_t31", root)
  const blocked1 = await tryWrite(plugin, root, "src/conv.ts", "ses_t31")
  rec("T31 wave1 latch blocks the next wave's source write", typeof blocked1 === "string" && /GATE-BLOCKED/.test(blocked1), blocked1 === true ? "TEETH LOST" : "blocked")
  // wave2 starts per protocol: fresh acceptance.md (real-turn gap, see T29b),
  // then the evidence wave.
  await new Promise((r) => setTimeout(r, 5))
  write(root, "tests/acceptance.md", "wave2 criteria\n")
  const allowed = (await tryWrite(plugin, root, "src/conv.ts", "ses_t31")) === true
  rec("T31 wave2 new-task key opens the source-write path in-session", allowed, allowed ? "DOC->CODE unblocked without takeover" : "deadlocked: " + blocked1)
  // wave2 lands better evidence (A1/A2 clear) and re-emits the gate line:
  // the signature CHANGES, so the final audit must honestly re-latch.
  write(root, "tests/verification_log.md", "- iter 1 PASS: wave2 fix landed (evidence: tests/x.log)\n")
  await emit("message.part.updated", { sessionID: "ses_t31", part: { id: "t2", type: "text", text: "[Verification Gate] Verifier: direct read | Loop executed: yes | Iterations: 1 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  await emit("session.idle", { sessionID: "ses_t31" })
  const st27 = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8")).roots[root]
  const blocked2 = await tryWrite(plugin, root, "src/more.ts", "ses_t31")
  rec(
    "T31 wave2 final audit re-latches on a CHANGED bad signature (teeth return)",
    !!st27.red && typeof blocked2 === "string" && /GATE-BLOCKED/.test(blocked2),
    st27.red ? "re-latched on new signature" : "no re-latch: " + JSON.stringify(st27.red)
  )
}

// ---- T32: review-round regressions (adversarial r1 PoCs, 2026-10-02) ----
{
  const root = newFixture("t32-crosssession")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  // A latches RED; B takes over after a LEGAL release (redTtlHours:0 expires
  // the latch — D3 removed the foreign-write release, T16 pins that); then B
  // emits ITS OWN completion claim and fails the same template checks. The
  // signature is identical (template-driven BAD set) but it belongs to a
  // DIFFERENT session's genuine fresh audit — it must re-latch.
  await latchRed(plugin, "ses_t32_a", root)
  write(root, "t32-config.json", JSON.stringify({ redTtlHours: -1 }))
  process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root, "t32-config.json")
  await tryWrite(plugin, root, "src/b.ts", "ses_t32_b")
  delete process.env.VIBEWEAVER_AUDIT_CONFIG
  await emit("message.part.updated", { sessionID: "ses_t32_b", part: { id: "k2", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit("message.part.updated", { sessionID: "ses_t32_b", part: { id: "t9", type: "text", text: "[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  await emit("session.idle", { sessionID: "ses_t32_b" })
  const st28 = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8")).roots[root]
  rec(
    "T32a a DIFFERENT session's same-signature fresh RED re-latches (no cross-session amnesty)",
    !!st28.red && st28.red.sessionID === "ses_t32_b",
    st28.red ? `latched for ${st28.red.sessionID}` : "SUPPRESSED — signature amnesty leaked across sessions: " + JSON.stringify(st28.red)
  )
}
{
  const root = newFixture("t32-rearm")
  write(root, "tests/verification_log.md", "placeholder — no iter entries\n")
  const plugin = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root })
  const emit = (type, props) => plugin.event({ event: { type, properties: props } })
  // A latches; new-task key releases; then A emits a NEW gate line (a fresh
  // completion claim — closer to the buffer tail than the latched marker)
  // and fails again with the SAME signature. The teeth must re-arm at the
  // new claim: same-sig suppression only covers re-audits of the SAME claim.
  await latchRed(plugin, "ses_t28c", root)
  await new Promise((r) => setTimeout(r, 5))
  write(root, "tests/acceptance.md", "wave2 criteria\n")
  const open = (await tryWrite(plugin, root, "src/w2.ts", "ses_t28c")) === true
  await emit("message.part.updated", { sessionID: "ses_t28c", part: { id: "t2", type: "text", text: "[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 2 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass" } })
  await emit("session.idle", { sessionID: "ses_t28c" })
  const st28c = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8")).roots[root]
  const blocked = await tryWrite(plugin, root, "src/w3.ts", "ses_t28c")
  rec(
    "T32b new-task release re-arms the teeth at the NEXT completion claim (same signature)",
    open && !!st28c.red && typeof blocked === "string" && /GATE-BLOCKED/.test(blocked),
    open ? (st28c.red ? "re-armed at new claim" : "TEETH STILL DISARMED — backstop missing") : "new-task key broken"
  )
}

// =====================================================================
// T33 — release journal: append-only render (2026-10-13)
// A release line, once rendered into tests/gate_audit.md, must never leave
// the report just because the bounded state journal (RELEASES_CAP) dropped
// it — the section is an audit trail ("never delete"); the cap only bounds
// state. The report writer merges the prior render with the current state.
// =====================================================================
{
  const oldLine = "- 2026-10-09T11:16:08.184Z released: latched RED (BAD=11, session ses_old) → cleared via new-task (via write, by ses_old)"
  const midLine = "- 2026-10-12T01:02:03.456Z released: latched RED (BAD=2, session ses_mid) → cleared via stale-session (via write, by ses_alt)"
  const newLine = "- 2026-10-13T09:00:00.000Z released: latched RED (BAD=1, session ses_new) → cleared via ttl-expiry (via idle, by ses_new)"
  const existing = [
    "# Gate Audit — ses_x | 2026-10-13T00:00:00.000Z",
    "AUDIT: BAD=0 UNCERTAIN=0 escalate=false",
    "",
    "## Stale RED releases (auto-cleared latches — audit trail, never delete)",
    "",
    midLine,
    oldLine,
    "",
    "## Stop-debt (§V12 false-stop journal — advisory, Tier-2 adjudicates)",
    "",
    "- 2026-10-13T08:00:00.000Z stop-debt: claimed-stop \"done here\" — why (session ses_x) — §V12 false-stop; adjudicate in Tier-2 review",
    "",
  ].join("\n")

  const m1 = mergeReleaseLines(existing, [newLine])
  rec("T33a prior-render release line survives the state cap (union)", m1.includes(oldLine) && m1.includes(midLine) && m1.includes(newLine), `n=${m1.length}`)
  const m2 = mergeReleaseLines(existing, [oldLine, newLine])
  rec("T33b duplicate line is rendered once (dedupe)", m2.filter((l) => l === oldLine).length === 1 && m2.length === 3, `n=${m2.length}`)
  const m3 = mergeReleaseLines(existing, [newLine])
  rec(
    "T33c union sorted by timestamp (oldest → newest)",
    JSON.stringify(m3) === JSON.stringify([oldLine, midLine, newLine]),
    m3.map((l) => l.slice(2, 12)).join(" ")
  )
  const m4 = mergeReleaseLines(existing, [])
  rec("T33d non-release sections never leak into the journal", m4.length === 2 && m4.every((l) => /released:/.test(l)), `n=${m4.length}`)

  // T33f — a packet quoting the section header before the real section must
  // not shadow it: every matching segment is scanned; only release-shaped
  // lines count, so the decoy contributes nothing.
  const decoy = existing.replace(
    "## Stale RED releases (auto-cleared latches — audit trail, never delete)",
    '<packet id="C9">\nclaim absent\ntail of session text: reading tests/gate_audit.md now\n## Stale RED releases …\nsee above\n</packet>\n\n## Stale RED releases (auto-cleared latches — audit trail, never delete)'
  )
  const m5 = mergeReleaseLines(decoy, [newLine])
  rec("T33f packet-quoted section header does not shadow the real section", m5.includes(oldLine) && m5.includes(midLine) && m5.includes(newLine), `n=${m5.length}`)

  // T33e — integration: a real release cycle over a planted prior render
  const root33 = newFixture("t33-append-only")
  write(root33, "tests/verification_log.md", "placeholder — no iter entries\n")
  write(root33, "tests/gate_audit.md", existing)
  const plugin33 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root33 })
  const emit33 = (type, props) => plugin33.event({ event: { type, properties: props } })
  await emit33("message.part.updated", { sessionID: "ses_t33_a", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit33("message.part.updated", { sessionID: "ses_t33_a", part: { id: "t1", type: "text", text: "Verifier: mm-sensor [image]\n[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1" } })
  await emit33("session.idle", { sessionID: "ses_t33_a" })
  await emit33("message.part.updated", { sessionID: "ses_t33_b", part: { id: "k2", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  // legal release (D3: foreign writes don't release) — redTtlHours:0
  write(root33, "t33-config.json", JSON.stringify({ redTtlHours: -1 }))
  process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root33, "t33-config.json")
  const released33 = (await tryWrite(plugin33, root33, "src/b.ts", "ses_t33_b")) === true
  delete process.env.VIBEWEAVER_AUDIT_CONFIG
  await emit33("message.part.updated", { sessionID: "ses_t33_b", part: { id: "t2", type: "text", text: "[Verification Gate] Verifier: direct read | Loop executed: no | Iterations: 0" } })
  await emit33("session.idle", { sessionID: "ses_t33_b" })
  const report33 = existsSync(path.join(root33, "tests", "gate_audit.md")) ? readFileSyncSafe(path.join(root33, "tests", "gate_audit.md")) : ""
  rec(
    "T33e integration: after a real release cycle the prior render's line is still in gate_audit.md",
    released33 &&
      report33.split(oldLine).length - 1 === 1 &&
      /released: latched RED \(BAD=\d+, session ses_t33_a\) → cleared via ttl-expiry/.test(report33),
    released33 ? (report33.includes(oldLine) ? "preserved once + state line present" : "LOST — the state cap dropped it from the render") : "release flow broke"
  )
}

// =====================================================================
// Calibration — real session transcripts (informational)
// =====================================================================
const calibIdx2 = process.argv.indexOf("--calib")
const calibValue2 = calibIdx2 >= 0 ? process.argv[calibIdx2 + 1] : null
const calibDir = calibValue2 && !calibValue2.startsWith("--") ? calibValue2 : "/tmp/vibeweaver-audit-calib"
if (existsSync(calibDir)) {
  console.log("\n=== CALIBRATION (real sessions) ===")
  const { readdirSync, readFileSync } = await import("node:fs")
  for (const f of readdirSync(calibDir).filter((x) => x.endsWith(".json")).sort()) {
    let sess
    try {
      sess = JSON.parse(readFileSync(path.join(calibDir, f), "utf8"))
    } catch {
      console.log(`${f}: unparseable JSON — skipped`)
      continue
    }
    if (!sess || !Array.isArray(sess.texts) || !Array.isArray(sess.tools)) {
      console.log(`${f}: not a session export (no texts/tools) — skipped`)
      continue
    }
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

// =====================================================================
// T25 — COV-13 task class: lite path licensing + misreport guard
// =====================================================================
{
  const docGate =
    "[Verification Gate] Verifier: direct read (non-web) | direct-read | Class: DOC | Loop executed: no (Class: DOC — read-back verify) | Media graded externally: 0/0 (video 0 · audio 0 · screenshots 0) | Iterations: 1 | Tests executed with artifacts: no | E2E depth: unit-only | Script-only build/lifecycle: no | Fresh-run on final tree: yes | Fresh-verify: N/A (Class: DOC) | TDD RED evidence: N/A | Code review: N/A | assert_artifacts.py: pass=8/fail=0 | covenant_recall: pass | memory_gate: na | HARD-GATE-1: NO-TEST-NO-DONE=na | HARD-GATE-2: SCRIPT-ONLY=na"
  const docText = [
    "Class: DOC — CHANGELOG.md prose only",
    docGate,
    "[Covenant Recall] checked: all 13 covenants hold for this completion",
    "[Memory Gate] na (Class: DOC — no lesson to persist)",
    "[Convergence] doc: 1 iter | 1/1 pass | 0 stalls | 0 cap-hits",
    "A4.9 not triggered — verified via git diff --stat: 1 file, documentation-only change",
    "docs-drift: none (README does not describe the edited changelog entry)",
    "| # | Problem | What Changed & Evidence |",
    "| 1 | stale entry | CHANGELOG.md — entry added; read-back confirms |",
  ].join("\n")
  const root25 = newFixture("t25-class-doc")
  write(root25, "tests/verification_log.md", [
    "## Task: changelog entry | 2026-09-28",
    "- class: DOC — CHANGELOG.md prose only",
    "- COV-9 skipped — reason: documentation-only change (no runtime to baseline-test)",
    "- iter 1 PASS: criterion #1 — entry added (evidence: read-back of CHANGELOG.md)",
    "- assert-run: assert_artifacts.py: all 30 checks pass (exit 0)",
    "- final-run: --final — pass=19/fail=0",
  ].join("\n"))
  write(root25, "tests/acceptance.md", "> cap=5  stall=3×\n1. Entry added\n")
  const docTools = [{ tool: "write", filePath: "/x/CHANGELOG.md", t: Date.now() - 2000 }]
  const a25 = auditProject({ root: root25, sessionID: "ses_t29a", sessionText: docText, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const bBad25 = a25.checks.filter((c) => c.id.startsWith("B") && c.verdict === "BAD").map((c) => c.id)
  rec("T25a Class DOC lite path accepted (B-group clean)", bBad25.length === 0, `B-BAD=[${bBad25.join(",")}]`)
  const b11 = a25.checks.find((c) => c.id === "B11")
  rec("T25b filled Class field OK", b11 && b11.verdict === "OK", b11 ? b11.verdict + " — " + b11.evidence : "missing")
  const c18 = a25.checks.find((c) => c.id === "C18")
  rec("T25c Class DOC + prose-only change set → C18 OK", c18 && c18.verdict === "OK", c18 ? c18.verdict : "missing")

  const unlicensed = docText.replace(/Class: DOC/g, "Class: CODE")
  const root25b = newFixture("t25-class-unlicensed")
  write(root25b, "tests/verification_log.md", "## Task\n- iter 1 PASS: all\n")
  write(root25b, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  const a25b = auditProject({ root: root25b, sessionID: "ses_t29d", sessionText: unlicensed, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b7 = a25b.checks.find((c) => c.id === "B7")
  rec("T25d lite table WITHOUT Class DOC → B7 BAD", b7 && b7.verdict === "BAD", b7 ? b7.verdict : "missing")
  const noLicense = unlicensed
    .replace(/documentation-only change/g, "routine release note")
    .replace(/no lesson to persist/g, "gate field only")
  const a25b2 = auditProject({ root: root25b, sessionID: "ses_t29e", sessionText: noLicense, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b10b = a25b2.checks.find((c) => c.id === "B10")
  rec("T25e memory_gate: na WITHOUT Class DOC and WITHOUT reason → B10 BAD", b10b && b10b.verdict === "BAD", b10b ? b10b.verdict : "missing")

  const tpl = docText.replace(/Class: DOC(?!\|)/g, "Class: DOC|CONFIG|CODE").replace(/\| # \| Problem \| What Changed & Evidence \|/, "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |")
  const a25c = auditProject({ root: root25, sessionID: "ses_t29f", sessionText: tpl, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b11t = a25c.checks.find((c) => c.id === "B11")
  rec("T25f template-unfilled Class field → B11 BAD", b11t && b11t.verdict === "BAD", b11t ? b11t.verdict + " — " + b11t.evidence : "missing")

  const root25d = newFixture("t25-class-misreport")
  write(root25d, "tests/verification_log.md", [
    "## Task: doc claim, code write",
    "- class: DOC — prose only",
    "- COV-9 skipped — reason: documentation-only change",
    "- iter 1 PASS: all",
  ].join("\n"))
  write(root25d, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  const a25d = auditProject({
    root: root25d, sessionID: "ses_t29g", sessionText: docText,
    tools: [...docTools, { tool: "write", filePath: "/x/src/sneaky.ts", t: Date.now() + 500 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18m = a25d.checks.find((c) => c.id === "C18")
  rec("T25g Class DOC + code write → C18 BAD (misreport)", c18m && c18m.verdict === "BAD", c18m ? c18m.verdict + " — " + c18m.evidence : "missing")

  // misfiring class tokens are NOT a filled field (R2: DOCS / DOC|CONFIG / spaced template)
  for (const [label, token] of [["T25h1", "Class: DOCS"], ["T25h2", "Class: DOC/CONFIG"], ["T25h3", "Class: DOC | CONFIG | CODE"]]) {
    const t = docText.replace(/Class: DOC(?!\|)/g, token)
    const a = auditProject({ root: root25, sessionID: "ses_" + label, sessionText: t, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
    const b11m = a.checks.find((c) => c.id === "B11")
    rec(`${label} misfiring token "${token}" → B11 BAD`, b11m && b11m.verdict === "BAD", b11m ? b11m.verdict : "missing")
  }

  // tests/-hidden code write + untimed write both count (R2: BENIGN_RE / t-filter holes)
  const a25h = auditProject({
    root: root25d, sessionID: "ses_t29i", sessionText: docText,
    tools: [{ tool: "write", filePath: "/x/tests/conftest.py" }], // no t — previously invisible
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18h = a25h.checks.find((c) => c.id === "C18")
  rec("T25i Class DOC + untimed tests/conftest.py → C18 BAD", c18h && c18h.verdict === "BAD", c18h ? c18h.verdict : "missing")

  const cfgText = docText.replace(/Class: DOC/g, "Class: CONFIG").replace(/CHANGELOG\.md prose only/, "config.toml only")
  const a25i = auditProject({
    root: root25d, sessionID: "ses_t29j", sessionText: cfgText,
    tools: [{ tool: "write", filePath: "/x/config.toml", t: Date.now() - 1000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18i = a25i.checks.find((c) => c.id === "C18")
  rec("T25j Class CONFIG + .toml write → C18 OK", c18i && c18i.verdict === "OK", c18i ? c18i.verdict : "missing")
  const a25j = auditProject({
    root: root25d, sessionID: "ses_t29k", sessionText: cfgText,
    tools: [{ tool: "write", filePath: "/x/src/logic.py", t: Date.now() - 1000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18j = a25j.checks.find((c) => c.id === "C18")
  rec("T25k Class CONFIG + logic-source write → C18 BAD", c18j && c18j.verdict === "BAD", c18j ? c18j.verdict : "missing")

  // gate-line class vs log basis-line class must agree
  const root25e = newFixture("t25-class-mismatch")
  write(root25e, "tests/verification_log.md", [
    "## Task: mixed claims",
    "- class: CODE — logic changed",
    "- COV-9 skipped — reason: documentation-only change",
    "- iter 1 PASS: all",
  ].join("\n"))
  write(root25e, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  const a25l = auditProject({ root: root25e, sessionID: "ses_t29l", sessionText: docText, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b11mm = a25l.checks.find((c) => c.id === "B11")
  rec("T25l gate Class DOC vs log `- class: CODE` → B11 BAD (mismatch)", b11mm && b11mm.verdict === "BAD", b11mm ? b11mm.verdict + " — " + b11mm.evidence : "missing")

  // N1: unfilled template in the Class FIELD with the V11.6 na-prose INTACT must
  // NOT license a class (the prose `(Class: DOC — read-back verify)` lives in
  // another gate field and is not a class declaration)
  const tplWithProse = docText.replace("| Class: DOC |", "| Class: DOC|CONFIG|CODE |")
    .replace(/\| # \| Problem \| What Changed & Evidence \|/, "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |")
    .replace("| 1 | stale entry | CHANGELOG.md — entry added; read-back confirms |", "| 1 | stale entry | none | A | CHANGELOG.md | entry added | read-back ok | N/A |")
  const a25m = auditProject({ root: root25, sessionID: "ses_t29m", sessionText: tplWithProse, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b11p = a25m.checks.find((c) => c.id === "B11")
  rec("T25m unfilled template + intact na-prose → B11 BAD (no prose fallback)", b11p && b11p.verdict === "BAD", b11p ? b11p.verdict : "missing")
  const noReasonTpl = tplWithProse
    .replace(/documentation-only change/g, "routine entry")
    .replace(/no lesson to persist/g, "gate field only")
  const a25m2 = auditProject({ root: root25b, sessionID: "ses_t29m2", sessionText: noReasonTpl, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b10p = a25m2.checks.find((c) => c.id === "B10")
  rec("T25m2 na-prose mention is not a license → B10 BAD (reason-line required)", b10p && b10p.verdict === "BAD", b10p ? b10p.verdict : "missing")

  // N5: the documented no-lesson form for Class CODE is legitimate
  const codeNoLesson = GATE_LINE.replace("memory_gate: pass", "memory_gate: na (no lesson — nothing persistable)")
  const a25n = auditProject({
    root: root25b, sessionID: "ses_t29n", sessionText: [
      codeNoLesson,
      "[Covenant Recall] checked: all 13 covenants hold for this completion",
      "[Memory Gate] na (no lesson — nothing persistable)",
      "[Convergence] x: 1 iter | 1/1 pass | 0 stalls | 0 cap-hits",
      "A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit",
      "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
      "| 1 | fix | none | A | src/a.ts | fixed | tests/shot.png -> ok | abc |",
    ].join("\n"),
    tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const b10n = a25n.checks.find((c) => c.id === "B10")
  rec("T25n Class CODE + `memory_gate: na (no lesson …)` → B10 OK (documented form)", b10n && b10n.verdict === "OK", b10n ? b10n.verdict + " — " + b10n.evidence : "missing")

  // N4: a checklist echo is NOT a reason line — bare na stays unlicensed for CODE
  const echoText = [
    GATE_LINE.replace("HARD-GATE-1: NO-TEST-NO-DONE=pass", "HARD-GATE-1: NO-TEST-NO-DONE=na"),
    "- [ ] Pure-doc/config edits state-skip with `COV-9 skipped — documentation-only change`",
    "[Covenant Recall] checked: all 13 covenants hold for this completion",
    "[Memory Gate] Passed: ok",
    "[Convergence] x: 1 iter | 1/1 pass | 0 stalls | 0 cap-hits",
    "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
    "| 1 | fix | none | A | src/a.ts | fixed | tests/shot.png -> ok | abc |",
  ].join("\n")
  const a25o = auditProject({ root: root25b, sessionID: "ses_t29o", sessionText: echoText, tools: docTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c14o = a25o.checks.find((c) => c.id === "C14")
  rec("T25o checklist-echo + bare HARD-GATE-1=na (Class CODE) → C14 UNCERTAIN", c14o && c14o.verdict === "UNCERTAIN", c14o ? c14o.verdict + " — " + c14o.evidence : "missing")

  // N3: an OLD block's `- class: DOC` must not license the CURRENT task block
  const root25f = newFixture("t25-class-oldblock")
  write(root25f, "tests/verification_log.md", [
    "## Task: old doc task | 2026-09-01",
    "- class: DOC — README prose",
    "- COV-9 skipped — reason: documentation-only change",
    "- iter 1 PASS: all",
    "",
    "## Task: current code task | 2026-09-28",
    "- Baseline verified GREEN",
    "- iter 1 PASS: all",
  ].join("\n"))
  write(root25f, "tests/acceptance.md", "> cap=5  stall=3×\n1. ok\n")
  write(root25f, "memory/MEMORY.md", "# Index\n- [fix](fix.md)\n")
  write(root25f, "memory/fix.md", "# Fix\n")
  write(root25f, "script/linux/start.sh", "#!/bin/sh\nexit 0\n")
  write(root25f, "script/linux/stop.sh", "#!/bin/sh\nexit 0\n")
  write(root25f, "script/linux/restart.sh", "#!/bin/sh\nexit 0\n")
  write(root25f, "script/linux/project_build.sh", "#!/bin/sh\nexit 0\n")
  for (const s of ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]) chmodSync(path.join(root25f, "script/linux", s), 0o755)
  const a25p = auditProject({ root: root25f, sessionID: "ses_t29p", sessionText: GATE_LINE.replace("Class: CODE", "Class: CODE") , tools: baseTools(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b11q = a25p.checks.find((c) => c.id === "B11")
  rec("T25p current block without class line ≠ old DOC block → B11 OK on Class CODE", b11q && b11q.verdict === "OK" && b11q.evidence === "CODE", b11q ? b11q.verdict + " — " + b11q.evidence : "missing")

  // §V11.9 DOC-asset render gate: office deliverables stay Class DOC but require
  // rendered-page evidence (or a flagged toolchain N/A) — never a bare claim.
  const docAssetTools = [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() - 1000 }]
  const a25q = auditProject({ root: root25b, sessionID: "ses_t29q", sessionText: docText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18q = a25q.checks.find((c) => c.id === "C18")
  rec("T25q Class DOC + report.docx WITHOUT render evidence → C18 BAD (NO RENDER, NO DONE)", c18q && c18q.verdict === "BAD" && /render/i.test(c18q.evidence), c18q ? c18q.verdict + " — " + c18q.evidence : "missing")
  // evidence binding: per-asset `render:` line, page image EXISTS on disk
  const ghostText = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — tests/ghost_page.png verified")
  const a25t = auditProject({ root: root25b, sessionID: "ses_t29t", sessionText: ghostText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18t = a25t.checks.find((c) => c.id === "C18")
  rec("T25t fabricated page-image path (not on disk) → C18 BAD", c18t && c18t.verdict === "BAD", c18t ? c18t.verdict + " — " + c18t.evidence : "missing")
  // COV-5 probe output is tooling, never a document page
  write(root25b, "tests/probe_vision.png", "png-bytes")
  const probeText = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — tests/probe_vision.png verified")
  const a25t2 = auditProject({ root: root25b, sessionID: "ses_t29t2", sessionText: probeText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18t2 = a25t2.checks.find((c) => c.id === "C18")
  rec("T25t2 probe_vision.png cited as render evidence → C18 BAD", c18t2 && c18t2.verdict === "BAD", c18t2 ? c18t2.verdict : "missing")
  // cross-block citation: the current task block must carry its own evidence
  write(root25b, "tests/report_p1.png", "png-bytes")
  write(root25b, "tests/verification_log.md", [
    "## Task: old | 2026-09-01",
    "- class: DOC — prose",
    "- iter 1 PASS: all (evidence: tests/report_p1.png)",
    "",
    "## Task: new asset | 2026-09-28",
    "- class: DOC — report",
    "- Baseline verified GREEN",
    "- iter 1 PASS: all",
  ].join("\n"))
  const staleBlock = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "see tests/report_p1.png in the earlier task")
  const a25t3 = auditProject({ root: root25b, sessionID: "ses_t29t3", sessionText: staleBlock, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18t3 = a25t3.checks.find((c) => c.id === "C18")
  rec("T25t3 prior-block citation only → C18 BAD (current block must bind)", c18t3 && c18t3.verdict === "BAD", c18t3 ? c18t3.verdict : "missing")
  const renderedText = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — tests/report_p1.png rendered page verified")
  const a25r = auditProject({ root: root25b, sessionID: "ses_t29r", sessionText: renderedText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18r = a25r.checks.find((c) => c.id === "C18")
  rec("T25r per-asset render line + existing page image → C18 OK", c18r && c18r.verdict === "OK", c18r ? c18r.verdict + " — " + c18r.evidence : "missing")
  const naToolText = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — N/A (soffice missing; layout risk flagged to user)")
  const a25s = auditProject({ root: root25b, sessionID: "ses_t29s", sessionText: naToolText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18s = a25s.checks.find((c) => c.id === "C18")
  rec("T25s toolchain-named `render: N/A` → C18 OK", c18s && c18s.verdict === "OK", c18s ? c18s.verdict + " — " + c18s.evidence : "missing")
  const bareNa = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — N/A (fine, checked manually)")
  const a25u = auditProject({ root: root25b, sessionID: "ses_t29u", sessionText: bareNa, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18u = a25u.checks.find((c) => c.id === "C18")
  rec("T25u bare `N/A (fine, checked)` ≠ reason → C18 BAD", c18u && c18u.verdict === "BAD", c18u ? c18u.verdict : "missing")
  const phNa = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — N/A (<missing toolchain>)")
  const a25u2 = auditProject({ root: root25b, sessionID: "ses_t29u2", sessionText: phNa, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18u2 = a25u2.checks.find((c) => c.id === "C18")
  rec("T25u2 placeholder `<missing toolchain>` copied literally → C18 BAD", c18u2 && c18u2.verdict === "BAD", c18u2 ? c18u2.verdict : "missing")
  // CONFIG + asset is NOT a misreport (assets are render-gated in every class) —
  // it must hit the render gate, and pass once evidence is bound (no deadlock).
  const a25v = auditProject({ root: root25b, sessionID: "ses_t29v", sessionText: cfgText, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18v = a25v.checks.find((c) => c.id === "C18")
  rec("T25v Class CONFIG + unrendered report.docx → render-gate BAD (not misreport)", c18v && c18v.verdict === "BAD" && /NO RENDER/.test(c18v.evidence), c18v ? c18v.verdict + " — " + c18v.evidence : "missing")
  const cfgRendered = cfgText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — tests/report_p1.png rendered page verified")
  const a25v2 = auditProject({ root: root25b, sessionID: "ses_t29v2", sessionText: cfgRendered, tools: docAssetTools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18v2 = a25v2.checks.find((c) => c.id === "C18")
  rec("T25v2 Class CONFIG + rendered asset → C18 OK (escalation path not deadlocked)", c18v2 && c18v2.verdict === "OK", c18v2 ? c18v2.verdict : "missing")
  // mixed wave: Class CODE shipping an asset owes the same render (file-kind gate)
  const codeWithAsset = GATE_LINE.replace("memory_gate: pass", "memory_gate: pass") // CODE gate line
    .replace("code review", "code review")
  const codeText = [
    "Verifier: direct read (non-web)",
    GATE_LINE,
    "[Covenant Recall] checked: all 13 covenants hold for this completion",
    "[Memory Gate] Passed: memory written",
    "[Convergence] x: 1 iter | 1/1 pass | 0 stalls | 0 cap-hits",
    "A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit",
    "render: report.docx — tests/report_p1.png rendered page verified",
    "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
    "| 1 | fix | none | A | src/a.ts | fixed + sample report.docx | tests/report_p1.png -> ok | abc |",
  ].join("\n")
  const a25y = auditProject({ root: root25b, sessionID: "ses_t29y", sessionText: codeText, tools: [...docAssetTools, { tool: "write", filePath: "/x/src/a.ts", t: Date.now() - 2000 }], skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18y = a25y.checks.find((c) => c.id === "C18")
  rec("T25y Class CODE wave shipping report.docx + bound render → C18 OK", c18y && c18y.verdict === "OK", c18y ? c18y.verdict + " — " + c18y.evidence : "missing")
  const a25y2 = auditProject({ root: root25b, sessionID: "ses_t29y2", sessionText: codeText.replace("render: report.docx — tests/report_p1.png rendered page verified", "docs-drift: none (nothing stale)"), tools: [...docAssetTools, { tool: "write", filePath: "/x/src/a.ts", t: Date.now() - 2000 }], skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18y2 = a25y2.checks.find((c) => c.id === "C18")
  rec("T25y2 Class CODE wave shipping UNrendered report.docx → render-gate BAD", c18y2 && c18y2.verdict === "BAD" && /NO RENDER/.test(c18y2.evidence), c18y2 ? c18y2.verdict : "missing")
  // multi-asset: one page image cannot cover two deliverables
  const twoAssets = docText.replace("docs-drift: none (README does not describe the edited changelog entry)", "render: report.docx — tests/report_p1.png verified")
  const a25z = auditProject({ root: root25b, sessionID: "ses_t29z", sessionText: twoAssets, tools: [...docAssetTools, { tool: "write", filePath: "/x/output/appendix.pdf", t: Date.now() - 1000 }], skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18z = a25z.checks.find((c) => c.id === "C18")
  rec("T25z two assets, one render line → C18 BAD (per-asset binding)", c18z && c18z.verdict === "BAD" && /appendix/.test(c18z.evidence), c18z ? c18z.verdict + " — " + c18z.evidence : "missing")

  // C16-1: an office asset is a deliverable, not a code write — post-log asset
  // writes must not trip the code-after-log ordering check.
  const a25w = auditProject({
    root: root25b, sessionID: "ses_t29w", sessionText: renderedText,
    tools: [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() + 60000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c16w = a25w.checks.find((c) => c.id === "C16")
  rec("T25w post-log .docx write + render evidence → C16 NOT code-ordering BAD", c16w && c16w.verdict !== "BAD", c16w ? c16w.verdict + " — " + c16w.evidence : "missing")

  // DEL-1: a deleted asset is not a delivery — the render gate must stay silent.
  const root25g = newFixture("t25-class-deleted-asset")
  write(root25g, "tests/verification_log.md", [
    "## Task: cleanup | 2026-09-28",
    "- class: DOC — stale draft removed",
    "- COV-9 skipped — reason: documentation-only change",
    "- iter 1 PASS: criterion #1 (evidence: git status clean)",
  ].join("\n"))
  write(root25g, "tests/acceptance.md", "> cap=5  stall=3×\n1. Stale draft removed\n")
  write(root25g, "output/old_report.docx", "stale")
  execFileSync("git", ["init", "-q"], { cwd: root25g })
  execFileSync("git", ["config", "user.email", "m@t"], { cwd: root25g })
  execFileSync("git", ["config", "user.name", "m"], { cwd: root25g })
  execFileSync("git", ["add", "-A"], { cwd: root25g })
  execFileSync("git", ["commit", "-qm", "baseline"], { cwd: root25g })
  execFileSync("git", ["rm", "-q", "output/old_report.docx"], { cwd: root25g })
  const a25x = auditProject({ root: root25g, sessionID: "ses_t29x", sessionText: docText, tools: [{ tool: "bash", command: "git rm output/old_report.docx" }], skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const c18x = a25x.checks.find((c) => c.id === "C18")
  rec("T25x deleted-only .docx → render gate silent (not a delivery)", c18x && c18x.verdict === "OK", c18x ? c18x.verdict + " — " + c18x.evidence : "missing")
}

// =====================================================================
// T26 — B12 final-run evidence: completion claim requires the
// `- final-run: --final …` line in the CURRENT task block (§A4.4.1)
// =====================================================================
{
  // T26a: completion text + log WITHOUT final-run → B12 BAD
  const root26 = newFixture("t26-b12-no-finalrun")
  scaffoldComplete(root26)
  write(root26, "tests/verification_log.md", [
    "## Task: fixture | 2026-08-19",
    "- Baseline verified GREEN",
    "- iter 1 PASS: all criteria (evidence: tests/shot.png, 6/6)",
  ].join("\n"))
  const a26a = auditProject({ root: root26, sessionID: "ses_t30a", sessionText: cleanSessionText(), tools: baseTools(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b12a = a26a.checks.find((c) => c.id === "B12")
  rec("T26a completion claim WITHOUT final-run line → B12 BAD", b12a && b12a.verdict === "BAD", b12a ? b12a.verdict : "missing")

  // T26b: scaffoldComplete carries the line → B12 OK
  const root26b = newFixture("t26-b12-with-finalrun")
  scaffoldComplete(root26b)
  const a26b = auditProject({ root: root26b, sessionID: "ses_t30b", sessionText: cleanSessionText(), tools: baseTools(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b12b = a26b.checks.find((c) => c.id === "B12")
  rec("T26b final-run line in current block → B12 OK", b12b && b12b.verdict === "OK", b12b ? b12b.verdict : "missing")

  // W11 P0-1: B12 must reject a typed final-run unless it is bound.
  const b12Case = (name, log, extra) => {
    const root = newFixture(name)
    write(root, "tests/verification_log.md", log)
    write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. fixture\n")
    if (extra) extra(root)
    const a = auditProject({ root, sessionID: "ses_" + name, sessionText: cleanSessionText(), tools: baseTools(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
    return a.checks.find((c) => c.id === "B12")
  }
  const LOG_HEAD = "## Task: fixture\n- iter 1 PASS: all\n"
  const FR = "- final-run: --final — pass=19/fail=0\n"
  const b12u = b12Case("t26-b12-unbound", LOG_HEAD + FR)
  rec("T26b2 typed final-run without assert output → B12 BAD", b12u && b12u.verdict === "BAD", b12u ? b12u.verdict : "missing")
  const b12s = b12Case("t26-b12-fake-seal", LOG_HEAD + "- seal: fabricated\n" + FR)
  rec("T26b3 `- seal:` without a valid manifest → B12 BAD", b12s && b12s.verdict === "BAD", b12s ? b12s.verdict : "missing")
  const b12o = b12Case("t26-b12-one-line", LOG_HEAD + "- final-run: --final — pass=19/fail=0 assert_artifacts.py: all 30 checks pass\n")
  rec("T26b4 one-line final-run + assert text → B12 BAD (forged shape)", b12o && b12o.verdict === "BAD", b12o ? b12o.verdict : "missing")
  const b12z = b12Case("t26-b12-zero-checks", LOG_HEAD + "- assert-run: assert_artifacts.py: all 0 checks pass\n" + FR)
  rec("T26b5 `all 0 checks pass` is not evidence → B12 BAD", b12z && b12z.verdict === "BAD", b12z ? b12z.verdict : "missing")
  const b12l = b12Case("t26-b12-bound-log", LOG_HEAD + "- final-run: --final — pass=19/fail=0 log=tests/run.log\n", (root) => write(root, "tests/run.log", "assert_artifacts.py: all 19 checks pass (exit 0)\n"))
  rec("T26b6 final-run bound to a fresh assert log → B12 OK", b12l && b12l.verdict === "OK", b12l ? b12l.verdict : "missing")
  const b12dir = b12Case("t26-b12-dir-log", LOG_HEAD + "- final-run: --final — pass=19/fail=0 log=tests\n")
  rec("T26b7 final-run bound to a directory → B12 BAD", b12dir && b12dir.verdict === "BAD", b12dir ? b12dir.verdict : "missing")
  const b12last = b12Case("t26-b12-last-fail", LOG_HEAD + "- assert-run: assert_artifacts.py: all 19 checks pass\n" + FR + "- final-run: --final — pass=0/fail=2\n")
  rec("T26b8 later failing final-run wins over an earlier bound one → B12 BAD", b12last && b12last.verdict === "BAD", b12last ? b12last.verdict : "missing")
  const b12old = b12Case("t26-b12-old-log", LOG_HEAD + "- final-run: --final — pass=19/fail=0 log=tests/run.log\n", (root) => {
    write(root, "tests/run.log", "assert_artifacts.py: all 19 checks pass (exit 0)\n")
    const old = new Date(500)
    utimesSync(path.join(root, "tests", "run.log"), old, old)
  })
  rec("T26b9 artifact older than the session → B12 BAD", b12old && b12old.verdict === "BAD", b12old ? b12old.verdict : "missing")
  const b12fake = b12Case("t26-b12-fake-manifest", LOG_HEAD + "- seal: fabricated\n" + FR, (root) => {
    write(root, "tests/evidence_manifest.json", JSON.stringify({ version: 1, files: { "tests/x.log": { sha256: "a".repeat(64), size: 1 } }, code_fingerprint: "b".repeat(64) }))
  })
  rec("T26b10 manifest with unverifiable hashes → B12 BAD", b12fake && b12fake.verdict === "BAD", b12fake ? b12fake.verdict : "missing")

  // T26c: final-run only in a PRIOR task block ≠ current-block evidence (scoping)
  const root26c = newFixture("t26-b12-stale-block")
  scaffoldComplete(root26c)
  write(root26c, "tests/verification_log.md", [
    "## Task: old | 2026-09-01",
    "- iter 1 PASS: all",
    "- final-run: --final — pass=19/fail=0",
    "",
    "## Task: new | 2026-09-28",
    "- Baseline verified GREEN",
    "- iter 1 PASS: all",
  ].join("\n"))
  const a26c = auditProject({ root: root26c, sessionID: "ses_t30c", sessionText: cleanSessionText(), tools: baseTools(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const b12c = a26c.checks.find((c) => c.id === "B12")
  rec("T26c final-run only in prior block → B12 BAD (current block must bind)", b12c && b12c.verdict === "BAD", b12c ? b12c.verdict : "missing")

  // T26d: no gate line (mid-task / no completion claim) → B12 does not fire
  const a26d = auditProject({ root: root26b, sessionID: "ses_t30d", sessionText: "Verifier: direct read\nworking on it, no completion claim here", tools: baseTools(), skillLoaded: true, phase: "mid", config: { samplingRate: 0 } })
  const b12d = a26d.checks.find((c) => c.id === "B12")
  rec("T26d mid-phase without gate line → B12 silent (no mid-task interference)", b12d === undefined, b12d ? b12d.verdict : "absent")
}

// =====================================================================
// T27 — stop-guard (§V12): false-stop detector + whitelist + budget + debt
// =====================================================================
const hasStopGuard = typeof stopEuphemism === "function" && typeof stopGuardDecision === "function" && typeof stopGuardPrompt === "function"
{
  const eu = (t) => (hasStopGuard ? stopEuphemism(t) : undefined)
  const det = (label, text, want) =>
    rec(label, hasStopGuard ? !!eu(text) === want : false, hasStopGuard ? (eu(text) ? `match=${eu(text).match}` : "null") : "detector missing (RED)")

  // ---- core detector: exhaustion vocabulary × context proximity ----
  det("T27a1 zh claim 上下文快耗尽 → hit", "工作量太大了，上下文快耗尽了，我们先到这里吧。", true)
  det("T27a2 zh claim 上下文已耗尽 → hit", "由于上下文已耗尽，我无法继续编码。", true)
  det("T27a3 en claim running out of context → hit", "I'm running out of context — stopping here.", true)
  det("T27a4 en claim window almost full → hit", "The context window is almost full, let me wrap up.", true)
  det("T27a5 en claim hit the context limit → hit", "We've hit the context limit, so I'll stop here.", true)
  det("T27b1 normal work narration → miss", "接下来修改 form.ts 并跑测试。", false)
  det("T27b2 'context' without exhaustion → miss", "The context of this function is complex.", false)
  det("T27b3 'out of context' idiom → miss", "That quote is out of context — it means something else.", false)
  det("T27b4 'full of' idiom → miss", "The context is full of useful details.", false)
  det("T27b5 meta-discussion multi-hit → miss (review F2)", "Added detector tests: T27a1 上下文快耗尽 → hit; covered running out of context too.", false)
  det("T27b6 quoted claim → miss (review F2)", '用户说"上下文快耗尽了"，但我们会继续。', false)
  det("T27b7 mid-text single mention, no cessation, far from end → miss (review F2)", "注意：上下文快耗尽是重点监控对象。接下来还有三件事要做：第一……第二……第三……我们还要继续验证很多内容。", false)
  det("T27a6 zh 满了 → hit", "上下文满了，只能先到这里。", true)
  det("T27a7 en % full + terminal → hit", "The context is 95% full, stopping.", true)
  det("T27b8 'wrap up the component' is work, not cessation → miss (review N1)", "注意：上下文快耗尽是误报重点。接下来 wrap up the component refactor，还有很多工作。", false)
  det("T27b9 label-colon prefixed terminal mention → miss (review N2)", "重点监控模式：上下文快耗尽", false)

  // ---- decision: whitelist priority + telemetry modes ----
  const dec = (o) => (hasStopGuard ? stopGuardDecision(o) : undefined)
  const trig = { kind: "euphemism", match: "上下文快耗尽" }
  const base = { trigger: trig, taskActive: true, pausedState: false, classE: false, gateMarker: false, tailQuestion: false, userStop: false, telemetry: true }
  const dExpect = (label, opts, action) => {
    const d = dec(opts)
    rec(label, hasStopGuard ? d && d.action === action : false, hasStopGuard ? `action=${d && d.action} why=${d && d.why}` : "decision missing (RED)")
  }
  dExpect("T27c1 no trigger → ignore", { ...base, trigger: null }, "ignore")
  dExpect("T27c2 no active task → ignore", { ...base, taskActive: false }, "ignore")
  dExpect("T27c3 paused_state whitelist → ignore", { ...base, pausedState: true }, "ignore")
  dExpect("T27c4 Class-E whitelist → ignore", { ...base, classE: true }, "ignore")
  dExpect("T27c5 gate-marker whitelist → ignore", { ...base, gateMarker: true }, "ignore")
  dExpect("T27c6 user-stop whitelist → ignore", { ...base, userStop: true }, "ignore")
  dExpect("T27c7 tail-question whitelist → ignore", { ...base, tailQuestion: true }, "ignore")
  dExpect("T27c8 clean trigger on v1 → prompt", base, "prompt")
  dExpect("T27c9 clean trigger on v2 (no telemetry) → debt, never prompt", { ...base, telemetry: false }, "debt")
  dExpect("T27c10 truncation trigger → prompt", { ...base, trigger: { kind: "truncation", match: "length" } }, "prompt")
  // Positive completion predicate: no euphemism is needed when the on-disk
  // task is incomplete. This is the silent-stop gap (§V12).
  dExpect("T27c11 on-disk incomplete, no euphemism → prompt",
    { ...base, trigger: null, positiveIncomplete: true }, "prompt")
  dExpect("T27c12 on-disk incomplete on v2 → debt, never prompt",
    { ...base, trigger: null, positiveIncomplete: true, telemetry: false }, "debt")
  dExpect("T27c13 on-disk incomplete + paused_state → ignore",
    { ...base, trigger: null, positiveIncomplete: true, pausedState: true }, "ignore")
  dExpect("T27c14 on-disk incomplete + gate marker → ignore",
    { ...base, trigger: null, positiveIncomplete: true, gateMarker: true }, "ignore")
  const blk = typeof currentLogBlock === "function"
    ? currentLogBlock("## Task: x\n- iter 1 PASS: x\n- final-run: --final — pass=1/fail=0\n## Notes\ntrailing prose\n")
    : ""
  rec("T27c15 currentLogBlock picks the last iter-bearing block (trailing heading safe)",
    /final-run/.test(blk) && !/Notes/.test(blk), blk.slice(0, 100))
  const blk2 = typeof currentLogBlock === "function"
    ? currentLogBlock("## Task: old\n- iter 1 PASS: x\n- final-run: --final — pass=1/fail=0\n## Task: new\n- Baseline verified GREEN\n")
    : ""
  rec("T27c16 currentLogBlock prefers a new Task block over the old final-run",
    /Baseline verified GREEN/.test(blk2) && !/final-run/.test(blk2), blk2.slice(0, 100))
  const blk3 = typeof currentLogBlock === "function"
    ? currentLogBlock("## Task: old\n- iter 1 PASS: x\n- final-run: --final — pass=1/fail=0\n## Verification Log — new wave\n- iter 2 PASS: y\n")
    : ""
  rec("T27c17 newer non-Task iter block beats an older completed Task",
    /iter 2 PASS/.test(blk3) && !/final-run/.test(blk3), blk3.slice(0, 100))
  const eb1 = typeof currentEvidenceBlock === "function"
    ? currentEvidenceBlock("- assert-run: assert_artifacts.py: all 3 checks pass\n- final-run: --final — pass=3/fail=0\n## Notes\ntrailing prose\n")
    : ""
  rec("T27c17b mid-block final-run survives a trailing Notes heading",
    /final-run/.test(eb1) && !/Notes/.test(eb1), eb1.slice(0, 100))
  const eb2 = typeof currentEvidenceBlock === "function"
    ? currentEvidenceBlock("## Task: one\n- assert-run: assert_artifacts.py: all 3 checks pass\n- final-run: --final — pass=3/fail=0\n## Task: two\n- iter 1 FAIL: x | diagnosis: d\n")
    : ""
  rec("T27c17c a later Task block displaces the earlier completed one",
    /Task: two/.test(eb2) && !/final-run/.test(eb2), eb2.slice(0, 100))
  const eb3 = typeof currentEvidenceBlock === "function"
    ? currentEvidenceBlock("## Task: t\n- class: CODE — logic\n- iter 1 PASS: x\n## Notes\n- assert-run: assert_artifacts.py: all 3 checks pass\n- final-run: --final — pass=3/fail=0\n")
    : ""
  rec("T27c17d a trailing Notes final-run is NOT completion evidence for a Task block",
    /Task: t/.test(eb3) && !/final-run/.test(eb3), eb3.slice(0, 120))
  const eb4 = typeof currentEvidenceBlock === "function"
    ? currentEvidenceBlock("## Task: t\n- assert-run: assert_artifacts.py: all 3 checks pass\n## Notes\n- final-run: --final — pass=3/fail=0\n")
    : ""
  rec("T27c17e a Notes final-run cannot complete a Task block with only assert-run",
    /Task: t/.test(eb4) && !/final-run/.test(eb4), eb4.slice(0, 120))
  // W10: positive predicate must not fire for read-only / awaiting-user turns.
  dExpect("T27c18 read-only task + positive → ignore",
    { ...base, trigger: null, positiveIncomplete: true, readOnlyTask: true }, "ignore")
  dExpect("T27c19 awaiting-user turn + positive → ignore",
    { ...base, trigger: null, positiveIncomplete: true, awaitingUser: true }, "ignore")
  dExpect("T27c20 CODE positive still prompts",
    { ...base, trigger: null, positiveIncomplete: true }, "prompt")
  const au = typeof stopAwaitingUser === "function" ? stopAwaitingUser : () => false
  rec("T27c21 awaiting detector: trailing question", au("Should I proceed?") === true, String(au("Should I proceed?")))
  rec("T27c22 awaiting detector: period-terminated approval request", au("Please confirm before I proceed.") === true, String(au("Please confirm before I proceed.")))
  rec("T27c23 awaiting detector: let-me-know phrase", au("Let me know if you want me to continue.") === true, String(au("Let me know if you want me to continue.")))
  rec("T27c24 awaiting detector: normal work narration stays false", au("Updated src/a.ts and ran the tests.") === false, String(au("Updated src/a.ts and ran the tests.")))
  const ro = typeof stopReadOnlyInstruction === "function" ? stopReadOnlyInstruction : () => false
  rec("T27c25 read-only detector: 仅评估，不修改", ro("仅评估，不修改。") === true, String(ro("仅评估，不修改。")))
  rec("T27c26 read-only detector: audit only", ro("Do a read-only audit; do not change code.") === true, String(ro("Do a read-only audit; do not change code.")))
  rec("T27c27 read-only detector: implement the fix stays false", ro("Implement the fix and run the tests.") === false, String(ro("Implement the fix and run the tests.")))
  rec("T27c28 read-only detector: 'do not change the tests' is not read-only", ro("Fix the failing test but do not change the tests.") === false, String(ro("Fix the failing test but do not change the tests.")))
  rec("T27c29 read-only detector: 'read-only mode' feature is not a read-only task", ro("Implement read-only mode for the config API.") === false, String(ro("Implement read-only mode for the config API.")))
  rec("T27c30 read-only detector: 'no changes in behavior' is not read-only", ro("Refactor the parser; make sure there are no changes in behavior.") === false, String(ro("Refactor the parser; make sure there are no changes in behavior.")))
  rec("T27c31 read-only detector: 请勿修改任何代码 is read-only", ro("请勿修改任何代码，只输出评审意见。") === true, String(ro("请勿修改任何代码，只输出评审意见。")))
  rec("T27c32 read-only detector: review only + don't touch code is read-only", ro("This is review only; don't touch the code.") === true, String(ro("This is review only; don't touch the code.")))
  rec("T27c39 read-only detector: bare 只读任务 is read-only", ro("这是一个只读任务。") === true, String(ro("这是一个只读任务。")))
  rec("T27c40 read-only detector: bare 请勿修改 is read-only", ro("请勿修改，只输出评审意见。") === true, String(ro("请勿修改，只输出评审意见。")))
  // W11 P1-1: quoted history / long brief / implementation override.
  rec("T27c41 read-only detector: quoted historical read-only does not exempt an implement turn",
    ro('上一版说“仅评估，不修改”，但现在实现 X。') === false, String(ro('上一版说“仅评估，不修改”，但现在实现 X。')))
  rec("T27c42 read-only detector: long brief with read-only first sentence still exempts",
    ro("仅评估，不修改。\n" + "背景说明。".repeat(900)) === true, "long-brief")
  rec("T27c43 read-only detector: review-then-implement is not read-only",
    ro("Review only the current implementation, then implement the requested fix.") === false, String(ro("Review only the current implementation, then implement the requested fix.")))
  rec("T27c44 awaiting detector: bare 'Done. Continue?' is not awaiting",
    au("Done. Continue?") === false, String(au("Done. Continue?")))
  rec("T27c45 awaiting detector: 'Should I proceed?' is awaiting",
    au("Should I proceed?") === true, String(au("Should I proceed?")))
  rec("T27c46 awaiting detector: narrative question without a request cue is not awaiting",
    au("The parser follows the nested import path?") === false, String(au("The parser follows the nested import path?")))
  rec("T27c47 awaiting detector: 'Would you like me to continue?' is awaiting",
    au("Would you like me to continue?") === true, String(au("Would you like me to continue?")))
  rec("T27c48 awaiting detector: '需要我继续吗？' is awaiting",
    au("需要我继续吗？") === true, String(au("需要我继续吗？")))
  rec("T27c49 awaiting detector: quoted question is not a request",
    au('You asked "Should I proceed?" — I proceeded with the migration.') === false, String(au('You asked "Should I proceed?" — I proceeded with the migration.')))
  rec("T27c50 awaiting detector: 'Ready to proceed?' is awaiting", au("Ready to proceed?") === true, String(au("Ready to proceed?")))
  rec("T27c51 awaiting detector: bare 'Proceed?' is awaiting", au("Proceed?") === true, String(au("Proceed?")))
  rec("T27c52 awaiting detector: '可以继续吗？' is awaiting", au("可以继续吗？") === true, String(au("可以继续吗？")))
  rec("T27c53 awaiting detector: 'Done. 继续吗？' is a nudge, not a pause", au("Done. 继续吗？") === false, String(au("Done. 继续吗？")))
  rec("T27c54 read-only detector: 'afterwards rewrite the parser' overrides read-only",
    ro("This is a read-only review; afterwards rewrite the parser.") === false, String(ro("This is a read-only review; afterwards rewrite the parser.")))
  rec("T27c55 read-only detector: 'Fix nothing.' stays read-only",
    ro("Review only. Fix nothing.") === true, String(ro("Review only. Fix nothing.")))
  rec("T27c56 read-only detector: 修复不在范围内 stays read-only",
    ro("仅评估。修复不在范围内。") === true, String(ro("仅评估。修复不在范围内。")))
  rec("T27c57 read-only detector: adding findings to a report is not implementation",
    ro("Only review the diff; add your findings to the report.") === true, String(ro("Only review the diff; add your findings to the report.")))
  rec("T27c58 read-only detector: modal 'you should implement' overrides read-only",
    ro("Do not modify code; you should implement the fix in src/cache.ts.") === false, String(ro("Do not modify code; you should implement the fix in src/cache.ts.")))
  rec("T27c59 read-only detector: long brief beyond 8KB still exempts",
    ro("仅评估，不修改。\n" + "背景说明。".repeat(2000)) === true, "long-brief-10k")
  rec("T27c60 read-only detector: a later affirmative verb defeats a negated first match",
    ro("Fix nothing. Implement the parser.") === false, String(ro("Fix nothing. Implement the parser.")))
  rec("T27c61 read-only detector: negated 'do not add code' stays read-only",
    ro("Only review; do not add code.") === true, String(ro("Only review; do not add code.")))
  rec("T27c62 read-only detector: 'update the report' is a document action",
    ro("Only review; update the report.") === true, String(ro("Only review; update the report.")))
  rec("T27c63 read-only detector: 'afterwards apply the patch' overrides",
    ro("Only review; afterwards apply the patch.") === false, String(ro("Only review; afterwards apply the patch.")))
  rec("T27c64 read-only detector: 不要修改现有代码 is read-only",
    ro("不要修改现有代码。") === true, String(ro("不要修改现有代码。")))
  rec("T27c65 awaiting detector: single-quoted question is not a request",
    au("The log says 'Should I proceed?' — I did.") === false, String(au("The log says 'Should I proceed?' — I did.")))
  rec("T27c66 awaiting detector: 'All done. Continue?' is a nudge",
    au("All done. Continue?") === false, String(au("All done. Continue?")))
  rec("T27c67 awaiting detector: 'The work is complete. Proceed?' is a nudge",
    au("The work is complete. Proceed?") === false, String(au("The work is complete. Proceed?")))
  rec("T27c68 awaiting detector: 工作完成。继续吗？ is a nudge",
    au("工作完成。继续吗？") === false, String(au("工作完成。继续吗？")))
  rec("T27c69 awaiting detector: 'Proceed with the fix?' is not a bare request",
    au("Proceed with the fix?") === false, String(au("Proceed with the fix?")))
  rec("T27c70 awaiting detector: 'Can we proceed?' is awaiting",
    au("Can we proceed?") === true, String(au("Can we proceed?")))
  rec("T27c71 read-only detector: 'Do not modify the code.' is read-only",
    ro("Do not modify the code.") === true, String(ro("Do not modify the code.")))
  rec("T27c72 read-only detector: 'update the file' is a document action",
    ro("Only review; update the file.") === true, String(ro("Only review; update the file.")))
  rec("T27c73 read-only detector: 'build a report table' is a document action",
    ro("Only review; build a report table.") === true, String(ro("Only review; build a report table.")))
  rec("T27c74 awaiting detector: \"It's done. Continue?\" is a nudge",
    au("It's done. Continue?") === false, String(au("It's done. Continue?")))
  rec("T27c75 awaiting detector: '\"Done.\" Continue?' is a nudge",
    au('"Done." Continue?') === false, String(au('"Done." Continue?')))
  rec("T27c76 awaiting detector: 'Can we do better?' is not a proceed request",
    au("Can we do better?") === false, String(au("Can we do better?")))
  rec("T27c77 read-only detector: 'Do not touch the code.' is read-only",
    ro("Do not touch the code.") === true, String(ro("Do not touch the code.")))
  rec("T27c78 read-only detector: 'Do not modify files.' is read-only",
    ro("Do not modify files.") === true, String(ro("Do not modify files.")))
  rec("T27c79 read-only detector: 'build the project' is a verification action",
    ro("Only review; build the project.") === true, String(ro("Only review; build the project.")))
  rec("T27c80 awaiting detector: 'It is done. Continue?' is a nudge",
    au("It is done. Continue?") === false, String(au("It is done. Continue?")))
  rec("T27c81 awaiting detector: mid-sentence quoted Done is a nudge",
    au('You said "Done." Continue?') === false, String(au('You said "Done." Continue?')))
  rec("T27c82 awaiting detector: 'Could we proceed?' is awaiting",
    au("Could we proceed?") === true, String(au("Could we proceed?")))
  rec("T27c83 awaiting detector: 'The test will proceed?' is narrative",
    au("The test will proceed?") === false, String(au("The test will proceed?")))
  rec("T27c84 awaiting detector: 'I cannot proceed?' is narrative",
    au("I cannot proceed?") === false, String(au("I cannot proceed?")))
  rec("T27c85 awaiting detector: 'This should proceed?' is narrative",
    au("This should proceed?") === false, String(au("This should proceed?")))
  rec("T27c86 awaiting detector: 'The build will continue?' is narrative",
    au("The build will continue?") === false, String(au("The build will continue?")))
  rec("T27c87 read-only detector: 'Do not alter the code.' is read-only",
    ro("Do not alter the code.") === true, String(ro("Do not alter the code.")))
  rec("T27c88 awaiting detector: '这个流程可以继续吗？' is awaiting",
    au("这个流程可以继续吗？") === true, String(au("这个流程可以继续吗？")))
  rec("T27c89 read-only detector: 'Do not update the code.' is read-only",
    ro("Do not update the code.") === true, String(ro("Do not update the code.")))
  const PAUSE_OK = "# PAUSED — fixture\ngate: schema\necho: q\nquestion: choose one\noptions:\n  (a) one\n  (b) two\ndefault-if-continue: (a)\nstate: fixture\n"
  rec("T27c90 paused packet: schema-valid packet is valid", pausedPacketValid(PAUSE_OK) === true, "fixture")
  rec("T27c91 paused packet: missing state is invalid", pausedPacketValid(PAUSE_OK.replace("state: fixture", "note: fixture")) === false, "missing-state")
  rec("T27c92 paused packet: one option is invalid", pausedPacketValid(PAUSE_OK.replace("  (b) two\n", "")) === false, "one-option")
  rec("T27c93 paused declaration: [PAUSED] is visible", pausedDeclaration("[PAUSED] gate=schema | question=q") === true, "visible")
  rec("T27c94 paused declaration: bare file text is not a declaration", pausedDeclaration("gate: schema") === false, "hidden")
  rec("T27c95 Class-E record: approved line is valid", classERecordValid("D-1 | Class-E | approved by user | deploy") === true, "approved")
  rec("T27c96 Class-E record: 'unapproved' line is invalid", classERecordValid("D-1 | Class-E | unapproved | deploy") === false, "unapproved")
  rec("T27c97 Class-E user approval: 批准 Class-E is accepted", classEUserApproval("批准 Class-E 部署") === true, "approved-text")
  rec("T27c98 Class-E user approval: 不同意 is rejected", classEUserApproval("不同意 Class-E 部署。") === false, "denied")
  rec("T27c99 Class-E user approval: 'approved plan' mention is not a grant", classEUserApproval("Please implement the approved plan.") === false, "mention")
  rec("T27c100 Class-E user approval: 'I approve' is a grant", classEUserApproval("I approve the Class-E deployment.") === true, "grant")
  rec("T27c101 Class-E declaration: 'not approved' is rejected", classEDeclaration("Class-E is not approved.") === false, "negated")
  rec("T27c102 paused packet: documented one-liner is valid",
    pausedPacketValid("[PAUSED] gate=x | question=q | options=(a),(b) | default-if-continue=(a) | state=s") === true, "one-liner")
  rec("T27c103 paused declaration: negated [PAUSED] is not a declaration",
    pausedDeclaration("No [PAUSED] packet is needed") === false, "negated")
  rec("T27c104 Class-E user approval: 'I will not approve Class-E' is rejected",
    classEUserApproval("I will not approve Class-E deployment", "Class-E") === false, "denied")
  rec("T27c105 Class-E user approval: generic 'I approve the plan' is rejected",
    classEUserApproval("I approve the plan", "Class-E") === false, "generic")
  rec("T27c106 Class-E user approval: 'go ahead and implement' is rejected",
    classEUserApproval("go ahead and implement the fix", "Class-E") === false, "generic")
  rec("T27c107 Class-E user approval: '我批准 Class-E 部署' is accepted",
    classEUserApproval("我批准 Class-E 部署", "Class-E") === true, "cn-approve")
  rec("T27c108 Class-E user approval: 'I approved the Class-E deployment' is accepted",
    classEUserApproval("I approved the Class-E deployment", "Class-E") === true, "en-past")
  rec("T27c109 Class-E user approval: bare '批准' without Class-E mention is NOT accepted",
    classEUserApproval("批准。") === false, "bare-no-context")
  rec("T27c110 Class-E declaration: 'No Class-E action taken' is rejected",
    classEDeclaration("No Class-E action taken.") === false, "negated")
  rec("T27c111 paused one-liner: a single option is invalid",
    pausedPacketValid("[PAUSED] gate=x | question=q | options=(a) | default-if-continue=(a) | state=s") === false, "one-option")
  rec("T27c112 Class-E user approval: \"I haven't approved Class-E\" is rejected",
    classEUserApproval("I haven't approved Class-E") === false, "denied")
  rec("T27c113 Class-E user approval: 'I would not approve Class-E' is rejected",
    classEUserApproval("I would not approve Class-E") === false, "denied")
  rec("T27c114 Class-E record: 不允许 is invalid", classERecordValid("D-1 | Class-E | 不允许 | deploy") === false, "denied-record")
  rec("T27c115 Class-E declaration: 'Class-E approved; nothing pending' is valid",
    classEDeclaration("Class-E approved; nothing pending.") === true, "positive-nothing")
  rec("T27c116 Class-E declaration: 'Class-E approved; unblocked' is valid",
    classEDeclaration("Class-E approved; unblocked.") === true, "positive-unblocked")
  rec("T27c33 awaiting detector: 'let me know' sign-off is not awaiting", au("Implementation complete. Let me know if you need anything else.") === false, String(au("Implementation complete. Let me know if you need anything else.")))
  rec("T27c34 awaiting detector: 'which path' narrative is not awaiting", au("The parser decides which path to follow for nested imports.") === false, String(au("The parser decides which path to follow for nested imports.")))
  rec("T27c35 awaiting detector: waiting on your decision is awaiting", au("Waiting on your decision about the schema.") === true, String(au("Waiting on your decision about the schema."))
  )
  rec("T27c36 awaiting detector: 麻烦确认 is awaiting", au("麻烦确认一下是否可以覆盖现有配置。") === true, String(au("麻烦确认一下是否可以覆盖现有配置。")))
  dExpect("T27c37 DOC euphemism is still a false stop → prompt",
    { ...base, trigger: trig, readOnlyTask: true }, "prompt")
  dExpect("T27c38 awaiting euphemism is still a false stop → prompt",
    { ...base, trigger: trig, awaitingUser: true }, "prompt")
  dExpect("T27c117 v2 explicit trigger + promptable → prompt",
    { ...base, telemetry: false, promptable: true, trigger: trig, taskActive: true }, "prompt")
  dExpect("T27c118 v2 explicit trigger + model-authored gate still prompts",
    { ...base, telemetry: false, promptable: true, trigger: trig, gateMarker: true, taskActive: true }, "prompt")
  dExpect("T27c119 v2 positive silent stop → debt (not ignore)",
    { ...base, telemetry: false, promptable: true, trigger: null, positiveIncomplete: true, taskActive: true }, "debt")
  dExpect("T27c120 v2 positive + readOnly still journals debt",
    { ...base, telemetry: false, promptable: true, trigger: null, positiveIncomplete: true, readOnlyTask: true, taskActive: true }, "debt")
  dExpect("T27c121 v2 positive + gate marker still journals debt",
    { ...base, telemetry: false, promptable: true, trigger: null, positiveIncomplete: true, gateMarker: true, taskActive: true }, "debt")

  // ---- corrective prompt contract ----
  const pt = hasStopGuard ? stopGuardPrompt({ kind: "euphemism", fill: 0.15, fillKnown: true }) : ""
  rec("T27d1 prompt names the four legal stops", hasStopGuard ? /ALL-PASS/.test(pt) && /PAUSED/.test(pt) && /Coverage/.test(pt) && /stall/i.test(pt) : false, pt.slice(0, 120))
  rec("T27d2 prompt quotes measured fill when known", hasStopGuard ? /15%/.test(pt) : false, pt.slice(0, 120))
  const pt2 = hasStopGuard ? stopGuardPrompt({ kind: "euphemism", fillKnown: false }) : ""
  rec("T27d3 prompt without telemetry never fabricates a fill number", hasStopGuard ? !/%/.test(pt2) : false, pt2.slice(0, 120))
  rec("T27d4 prompt points at working_note for resume", hasStopGuard ? /working_note/.test(pt) : false, "")
  const pt3 = hasStopGuard ? stopGuardPrompt({ kind: "truncation", fillKnown: false }) : ""
  rec("T27d5 truncation prompt names output-limit truncation ≠ complete", hasStopGuard ? /truncat|length|output.limit/i.test(pt3) : false, pt3.slice(0, 120))
  const pt4 = hasStopGuard ? stopGuardPrompt({ kind: "incomplete", fillKnown: false }) : ""
  rec("T27d6 incomplete prompt names on-disk final-run gap",
    hasStopGuard ? /final-run/.test(pt4) && /acceptance\.md/.test(pt4) : false, pt4.slice(0, 140))
  const pt5 = hasStopGuard ? stopGuardPrompt({ kind: "incomplete", fill: 0.2, fillKnown: true }) : ""
  rec("T27d7 incomplete prompt never carries an exhaustion fill accusation",
    hasStopGuard ? !/20%|no basis/.test(pt5) : false, pt5.slice(0, 140))
  rec("T27d8 incomplete prompt offers an already-complete exit (gate line, no fabrication)",
    hasStopGuard ? /(already complete|if the task is complete|emit the \[Verification Gate\]|gate line)/i.test(pt5) : false, pt5.slice(0, 220))

  // ---- v1 adapter integration: idle-triggered prompt, budget, arming, debt ----
  {
    const root27 = newFixture("t27-stopguard")
    write(root27, "tests/verification_log.md", "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n")
    write(root27, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin27 = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root27,
    })
    const sid = "ses_t27"
    const ev = (type, properties) => plugin27.event({ event: { type, properties } })
    const emitMsg = (info) => ev("message.updated", { sessionID: sid, info })
    const emitText = (pid, mid, text) => ev("message.part.updated", { sessionID: sid, part: { id: pid, messageID: mid, type: "text", text } })
    const emitTool = (pid, tool, input) => ev("message.part.updated", { sessionID: sid, part: { id: pid, type: "tool", tool, state: { status: "completed", input } } })
    const idle = () => ev("session.idle", { sessionID: sid })
    const asst = (id, finish, tokens) => ({ id, role: "assistant", modelID: "m", finish, tokens: tokens || { input: 1500, output: 100, reasoning: 0, cache: { read: 1000, write: 0 } } })

    await emitTool("sk", "skill", { name: "vibeweaver" })
    await emitTool("t1", "bash", { command: "ls" })
    await emitMsg(asst("m1", "stop"))
    await emitText("p1", "m1", "试了几次都不行，上下文快耗尽了，先到这里吧。")
    await idle()
    rec("T27e1 euphemism + incomplete + idle → exactly one corrective prompt (no abort)", calls.prompts.length === 1 && calls.abort === 0, `prompts=${calls.prompts.length} abort=${calls.abort}`)
    rec("T27e2 prompt contains four legal stops + working_note", /ALL-PASS/.test(calls.prompts[0] || "") && /working_note/.test(calls.prompts[0] || ""), (calls.prompts[0] || "").slice(0, 120))
    await idle()
    rec("T27e3 same tail second idle → no thrash (episode disarmed)", calls.prompts.length === 1, `prompts=${calls.prompts.length}`)
    // review F1 regression: the plugin's own corrective prompt returns as a
    // USER-role message containing "stop" — it must NOT whitelist episode 2
    await ev("message.updated", { sessionID: sid, info: { id: "inj1", role: "user" } })
    await emitText("pinj1", "inj1", calls.prompts[0] || "")
    await emitMsg(asst("m2", "stop"))
    await emitText("p2", "m2", "好，继续修改 src/a.ts。")
    await emitMsg(asst("m3", "stop"))
    await emitText("p3", "m3", "还是不行，上下文真的快耗尽了。")
    await idle()
    rec("T27e4 plugin-prompt echo must NOT self-whitelist → 2nd intervention (budget 2, review F1)", calls.prompts.length === 2, `prompts=${calls.prompts.length}`)
    await emitMsg(asst("m4", "stop"))
    await emitText("p4", "m4", "上下文耗尽了。")
    await idle()
    const budgetLog = calls.logs.some((m) => /budget exhausted/i.test(m) && /stop/i.test(m))
    rec("T27e5 3rd episode beyond budget → log-only + debt journaled", calls.prompts.length === 2 && budgetLog, `prompts=${calls.prompts.length} budgetLog=${budgetLog}`)
    const st = JSON.parse(readFileSync(path.join(root27, ".vibeweaver", "audit-state.json"), "utf8"))
    const debt = st.roots && st.roots[root27] && st.roots[root27].stopDebt
    rec("T27e6 stop-debt persisted in state (cap-bounded)", Array.isArray(debt) && debt.length >= 1, JSON.stringify(debt || null).slice(0, 140))
    // episode dedup: a NEW distinct match journals once; a repeat idle does not re-journal
    await emitMsg(asst("m5", "stop"))
    await emitText("p5", "m5", "I'm running out of context — stopping here.")
    await idle()
    await idle()
    const st2 = JSON.parse(readFileSync(path.join(root27, ".vibeweaver", "audit-state.json"), "utf8"))
    const debt2 = st2.roots[root27].stopDebt
    rec("T27e7 debt dedup: distinct episode +1, repeat idle +0", Array.isArray(debt2) && debt2.length === 2, `len=${debt2 && debt2.length}`)
    await idle()
    const report = readFileSync(path.join(root27, "tests", "gate_audit.md"), "utf8")
    rec("T27e8 debt replayed into gate_audit.md stop-debt section", /## Stop-debt/.test(report) && /stop-debt:/.test(report), report.split("\n").filter((l) => /stop-debt/i.test(l)).join(" | ").slice(0, 140))
  }

  // ---- positive on-disk incomplete: silent stop (no euphemism) must prompt ----
  {
    const root27p = newFixture("t27-positive")
    write(root27p, "tests/verification_log.md", "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n")
    write(root27p, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const calls = { prompts: [] }
    const plugin27p = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
      },
      directory: root27p,
    })
    const sid = "ses_t27p"
    const ev = (type, properties) => plugin27p.event({ event: { type, properties } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await ev("message.updated", { sessionID: sid, info: { id: "u1", role: "user" } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "pu1", messageID: "u1", type: "text", text: "Implement the fix." } })
    await ev("message.updated", { sessionID: sid, info: { id: "m0", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "write", state: { status: "running", input: { filePath: path.join(root27p, "src", "a.ts") } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "write", state: { status: "completed", input: { filePath: path.join(root27p, "src", "a.ts") } } } })
    await ev("message.updated", { sessionID: sid, info: { id: "m1", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "p1", messageID: "m1", type: "text", text: "Done." } })
    await ev("session.idle", { sessionID: sid })
    rec("T27e9 silent stop + on-disk incomplete → positive corrective prompt",
      calls.prompts.length === 1 && /final-run/.test(calls.prompts[0] || ""),
      `prompts=${calls.prompts.length} ${(calls.prompts[0] || "").slice(0, 140)}`)
    // Turn scoping: a user Q&A turn after the write must NOT be auto-resumed.
    await ev("message.updated", { sessionID: sid, info: { id: "u2", role: "user" } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "pu2", messageID: "u2", type: "text", text: "What changed?" } })
    await ev("message.updated", { sessionID: sid, info: { id: "m2", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "p2", messageID: "m2", type: "text", text: "Only the validation order." } })
    await ev("session.idle", { sessionID: sid })
    rec("T27e10 user Q&A after a write is not auto-resumed (turn-scoped)",
      calls.prompts.length === 1, `prompts=${calls.prompts.length}`)
    // Host error/abort fence: a later error after the write suppresses the
    // positive leg (don't auto-resume a cancelled/broken turn).
    await ev("message.part.updated", { sessionID: sid, part: { id: "t2", type: "tool", tool: "write", state: { status: "completed", input: { filePath: path.join(root27p, "src", "b.ts") } } } })
    await ev("session.error", { sessionID: sid })
    await ev("message.updated", { sessionID: sid, info: { id: "m3", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "p3", messageID: "m3", type: "text", text: "上下文快耗尽了，先到这里。" } })
    await ev("session.idle", { sessionID: sid })
    rec("T27e11 host error fences BOTH euphemism and positive triggers (no auto-resume)",
      calls.prompts.length === 1, `prompts=${calls.prompts.length}`)
  }

  // ---- W10: positive predicate is scoped to CODE task-file writes and
  // honest exits (read-only / DOC / awaiting-user / split gate / pass=0). ----
  {
    const LOG_CODE = "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n"
    const LOG_DOC = "## Task: fixture\n- class: DOC — prose\n- iter 1 PASS: report read-back (fixture)\n"
    const ASSERT_OK = "- assert-run: assert_artifacts.py: all 3 checks pass (exit 0)\n"
    const runStopCase = async (name, log, userText, asstText, opts = {}) => {
      const root = newFixture(name)
      write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
      if (opts.classEPreUser) write(root, "tests/decisions.md", opts.classEPreUser)
      // `preUserLog` / `staleLog` model evidence written by an EARLIER turn or
      // session; the normal path writes the task log AFTER the user message,
      // as a real turn does (the guard reads only the post-user log slice).
      if (opts.preUserLog || opts.staleLog) {
        write(root, "tests/verification_log.md", log)
        if (opts.staleLog) {
          const old = new Date(Date.now() - 60_000)
          utimesSync(path.join(root, "tests", "verification_log.md"), old, old)
        }
      }
      const calls = { prompts: [] }
      const plugin = await VibeweaverAudit({
        client: {
          app: { log: async () => {} },
          session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
        },
        directory: root,
      })
      const sid = `ses_${name}`
      const ev = (type, properties) => plugin.event({ event: { type, properties } })
      await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
      if (userText != null) {
        await ev("message.updated", { sessionID: sid, info: { id: "u1", role: "user" } })
        await ev("message.part.updated", { sessionID: sid, part: { id: "pu1", messageID: "u1", type: "text", text: userText } })
      }
      if (!opts.preUserLog && !opts.staleLog) write(root, "tests/verification_log.md", log)
      if (opts.rewriteLog !== undefined) write(root, "tests/verification_log.md", opts.rewriteLog)
      if (opts.pausedFile) write(root, "tests/paused_state.md", opts.pausedFile)
      if (opts.classEFile) write(root, "tests/decisions.md", opts.classEFile)
      if (opts.classEAppend) write(root, "tests/decisions.md", (opts.classEPreUser || "") + opts.classEAppend)
      const asst = (id) => ({ id, role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } })
      if (opts.gateFirst) {
        await ev("message.updated", { sessionID: sid, info: asst("m0") })
        await ev("message.part.updated", { sessionID: sid, part: { id: "p0", messageID: "m0", type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" } })
      } else {
        await ev("message.updated", { sessionID: sid, info: asst("m0") })
      }
      const writePath = path.join(root, opts.file || "src/a.ts")
      if (opts.statusOnlyWrite) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "t1", type: "tool", tool: "write", state: { status: "completed" } } })
      } else if (opts.bashWrite) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "bash", state: { status: "completed", input: { command: `cat > ${writePath} <<'EOF'\nexport const x = 1\nEOF` } } } })
      } else if (opts.bashOnlyCommand) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "bash", state: { status: "completed", input: { command: opts.bashOnlyCommand } } } })
      } else {
        if (opts.pendingWrite) await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "write", state: { status: "running", input: { filePath: writePath } } } })
        await ev("message.part.updated", { sessionID: sid, part: { id: "t1", messageID: "m0", type: "tool", tool: "write", state: { status: "completed", input: { filePath: writePath } } } })
      }
      if (opts.fillerWrites) {
        for (let i = 0; i < opts.fillerWrites; i++) {
          await ev("message.part.updated", { sessionID: sid, part: { id: `f${i}`, messageID: "m0", type: "tool", tool: "write", state: { status: "completed", input: { filePath: path.join(root, "docs", `f${i}.md`) } } } })
        }
      }
      if (opts.growGate) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "p0", messageID: "m0", type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0\nDone." } })
      }
      if (opts.gateDeltaAfterWrite) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "p0", messageID: "m0", type: "text", text: " Done." } })
      }
      if (opts.gateSameMsgAfterWrite) {
        await ev("message.part.updated", { sessionID: sid, part: { id: "pg", messageID: "m0", type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" } })
      }
      if (opts.reemitUser) await ev("message.updated", { sessionID: sid, info: { id: "u1", role: "user" } })
      await ev("message.updated", { sessionID: sid, info: asst("m1") })
      if (opts.gateLast) await ev("message.part.updated", { sessionID: sid, part: { id: "pg", messageID: "m1", type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" } })
      await ev("message.part.updated", { sessionID: sid, part: { id: "p1", messageID: "m1", type: "text", text: asstText } })
      await ev("session.idle", { sessionID: sid })
      return calls
    }
    const doc = await runStopCase("t27-w11-doc", LOG_DOC, "Only evaluate; do not modify code.", "Evaluation complete.", { file: "docs/report.md" })
    rec("T27e12 Class DOC + report write + stop → no prompt", doc.prompts.length === 0, `prompts=${doc.prompts.length}`)
    const docHtml = await runStopCase("t27-w11-doc-html", LOG_DOC, "Only evaluate; do not modify code.", "Evaluation complete.", { file: "README.html" })
    rec("T27e12b Class DOC + README.html write → no prompt", docHtml.prompts.length === 0, `prompts=${docHtml.prompts.length}`)
    const ro = await runStopCase("t27-w11-readonly", LOG_CODE, "仅评估，不修改。", "The audit report is ready.", { file: "docs/report.md" })
    rec("T27e13 read-only user instruction + report write → no prompt", ro.prompts.length === 0, `prompts=${ro.prompts.length}`)
    const roCode = await runStopCase("t27-w11-readonly-code", LOG_CODE, "仅评估，不修改。", "Done.", { file: "src/a.ts" })
    rec("T27e13b read-only instruction invalidated by a code write → prompt", roCode.prompts.length === 1, `prompts=${roCode.prompts.length}`)
    const wait = await runStopCase("t27-w11-wait", LOG_CODE, "Implement the fix.", "Please confirm before I proceed.")
    rec("T27e14 period-terminated approval request → no prompt", wait.prompts.length === 0, `prompts=${wait.prompts.length}`)
    const split = await runStopCase("t27-w11-early-gate", LOG_CODE, "Implement the fix.", "Done.", { gateFirst: true })
    rec("T27e15 gate marker BEFORE a later task-file write does NOT whitelist the turn", split.prompts.length === 1, `prompts=${split.prompts.length}`)
    const zero = await runStopCase("t27-w11-zero", LOG_CODE + "- final-run: --final — pass=0/fail=0\n", "Implement the fix.", "Done.")
    rec("T27e16 pass=0/fail=0 final-run is NOT completion → positive prompt", zero.prompts.length === 1, `prompts=${zero.prompts.length}`)
    const code = await runStopCase("t27-w11-code", LOG_CODE, "Implement the fix.", "Done.")
    rec("T27e17 CODE task-file write + silent Stop → positive prompt", code.prompts.length === 1 && /final-run/.test(code.prompts[0] || ""), `prompts=${code.prompts.length}`)
    const pending = await runStopCase("t27-w11-pending", LOG_CODE, "Implement the fix.", "Done.", { pendingWrite: true })
    rec("T27e18 pending→completed write is still task-write evidence", pending.prompts.length === 1, `prompts=${pending.prompts.length}`)
    const reemit = await runStopCase("t27-w11-reemit", LOG_CODE, "Implement the fix.", "Done.", { reemitUser: true })
    rec("T27e19 re-emitted user message does not move the turn boundary", reemit.prompts.length === 1, `prompts=${reemit.prompts.length}`)
    const stale = await runStopCase("t27-w11-stale-doc", LOG_DOC, "Implement the deferred feature.", "Done.", { staleLog: true })
    rec("T27e20 previous session's Class DOC cannot exempt a new CODE task", stale.prompts.length === 1, `prompts=${stale.prompts.length}`)
    // W11 P0-1: final-run must be bound to real assert output.
    const forged = await runStopCase("t27-w11-forged-final", LOG_CODE + "- final-run: --final — pass=3/fail=0\n", "Implement the fix.", "Done.")
    rec("T27e22 forged final-run without assert output → positive prompt", forged.prompts.length === 1, `prompts=${forged.prompts.length}`)
    const trusted = await runStopCase("t27-w11-trusted-final", LOG_CODE + "- final-run: --final — pass=3/fail=0\n" + ASSERT_OK, "Implement the fix.", "Done.")
    rec("T27e23 final-run + adjacent assert output → no prompt", trusted.prompts.length === 0, `prompts=${trusted.prompts.length}`)
    // W11 P0-2: an old final-run in the same session does not exempt a new turn.
    const staleFinal = await runStopCase("t27-w11-stale-final", LOG_CODE + "- final-run: --final — pass=3/fail=0\n" + ASSERT_OK, "Implement B.", "Done.", { preUserLog: true, file: "src/b.ts" })
    rec("T27e24 stale final-run + new user + code write → positive prompt", staleFinal.prompts.length === 1, `prompts=${staleFinal.prompts.length}`)
    // W11 P0-3/P0-5: a DOC claim is cross-checked against current-turn writes.
    const forgedDoc = await runStopCase("t27-w11-forged-doc", LOG_DOC, "Implement the deferred feature.", "Done.", { file: "src/a.ts" })
    rec("T27e25 forged Class DOC + current-turn code write → positive prompt", forgedDoc.prompts.length === 1, `prompts=${forgedDoc.prompts.length}`)
    const docStatusOnly = await runStopCase("t27-w11-doc-status-only", LOG_DOC, "Only evaluate; do not modify code.", "Evaluation complete.", { statusOnlyWrite: true })
    rec("T27e28 Class DOC + status-only write is not treated as code → no prompt", docStatusOnly.prompts.length === 0, `prompts=${docStatusOnly.prompts.length}`)
    // W11 P0-4 control: gate AFTER the last task write (final message) still whitelists.
    const gateAfter = await runStopCase("t27-w11-gate-last", LOG_CODE, "Implement the fix.", "Done.", { gateLast: true })
    rec("T27e26 gate marker AFTER the last task write → no prompt", gateAfter.prompts.length === 0, `prompts=${gateAfter.prompts.length}`)
    // W11 P0-4: a cumulative text update must not re-stamp an earlier gate.
    const gateGrow = await runStopCase("t27-w11-gate-grow", LOG_CODE, "Implement the fix.", "Done.", { gateFirst: true, growGate: true })
    rec("T27e27 cumulative update after write does not resurrect an early gate → prompt", gateGrow.prompts.length === 1, `prompts=${gateGrow.prompts.length}`)
    // W11 P1-4: status-only completed write is still task evidence.
    const statusOnly = await runStopCase("t27-w11-status-only", LOG_CODE, "Implement the fix.", "Done.", { statusOnlyWrite: true })
    rec("T27e29 status-only completed write (no input) → positive prompt", statusOnly.prompts.length === 1, `prompts=${statusOnly.prompts.length}`)
    // W11: bash redirects count as writes.
    const bashWrite = await runStopCase("t27-w11-bash-write", LOG_CODE, "Implement the fix.", "Done.", { bashWrite: true })
    rec("T27e34 bash redirect write + silent stop → positive prompt", bashWrite.prompts.length === 1, `prompts=${bashWrite.prompts.length}`)
    // W11: sticky code-write flag survives >50 prose writes.
    const filler = await runStopCase("t27-w11-filler", LOG_DOC, "Implement the deferred feature.", "Done.", { file: "src/a.ts", fillerWrites: 55 })
    rec("T27e35 code write + 55 prose writes still trips the DOC cross-check", filler.prompts.length === 1, `prompts=${filler.prompts.length}`)
    // W11 P0-2: a shorter log rewrite must not resurrect an old final-run.
    const oldLog = LOG_CODE + "- assert-run: assert_artifacts.py: all 3 checks pass (exit 0)\n" + "- final-run: --final — pass=3/fail=0\n" + "- padding: " + "x".repeat(200) + "\n"
    const rewrite = await runStopCase("t27-w11-log-rewrite", oldLog, "Implement B.", "Done.", {
      preUserLog: true, file: "src/b.ts",
      rewriteLog: "## Task: old\n- assert-run: assert_artifacts.py: all 3 checks pass (exit 0)\n- final-run: --final — pass=3/fail=0\n",
    })
    rec("T27e36 shorter log rewrite does not resurrect the old final-run → prompt", rewrite.prompts.length === 1, `prompts=${rewrite.prompts.length}`)
    // W11 re-review: a same-turn prior Task block must not authenticate a later one.
    const twoTasks = await runStopCase("t27-w11-two-tasks", LOG_CODE + ASSERT_OK + "- final-run: --final — pass=3/fail=0\n## Task: second\n", "Implement B.", "Done.", { file: "src/b.ts" })
    rec("T27e38 prior same-turn Task final-run does not exempt a later Task → prompt", twoTasks.prompts.length === 1, `prompts=${twoTasks.prompts.length}`)
    const classOrder = await runStopCase("t27-w11-class-order", "## Task: docs\n- class: DOC — prose\n## Task: code\n- class: CODE — logic\n", "Implement the fix.", "Done.", { statusOnlyWrite: true })
    rec("T27e39 class comes from the LAST task block (DOC→CODE) → prompt", classOrder.prompts.length === 1, `prompts=${classOrder.prompts.length}`)
    // W11 re-review: shell comparisons/quoted '>' and /tmp targets are not writes.
    const awk = await runStopCase("t27-w11-bash-awk", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "awk '$1 > 2 {print}' tests/data.txt" })
    rec("T27e40 awk comparison is not a bash write → no prompt", awk.prompts.length === 0, `prompts=${awk.prompts.length}`)
    const cpTmp = await runStopCase("t27-w11-bash-cp", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp -r src /tmp/backup" })
    rec("T27e41 cp to /tmp is not a project write → no prompt", cpTmp.prompts.length === 0, `prompts=${cpTmp.prompts.length}`)
    const htmlDoc = await runStopCase("t27-w11-doc-src-html", LOG_DOC, "Implement the UI.", "Done.", { file: "src/app.html" })
    rec("T27e42 DOC claim + src/app.html write → prompt", htmlDoc.prompts.length === 1, `prompts=${htmlDoc.prompts.length}`)
    const dataReport = await runStopCase("t27-w11-readonly-csv", LOG_CODE, "仅评估，不修改。", "The audit table is ready.", { file: "findings.csv" })
    rec("T27e43 read-only audit + csv report → no prompt", dataReport.prompts.length === 0, `prompts=${dataReport.prompts.length}`)
    const deltaGate = await runStopCase("t27-w11-delta-gate", LOG_CODE, "Implement the fix.", "Done.", { gateFirst: true, gateDeltaAfterWrite: true })
    rec("T27e47 an unrelated delta after the write does not re-stamp the early gate", deltaGate.prompts.length === 1, `prompts=${deltaGate.prompts.length}`)
    const sameBlockClass = await runStopCase("t27-w11-same-block-class", "## Task: fixture\n- class: CODE — logic\n- class: DOC — forged\n", "Implement the fix.", "Done.", { statusOnlyWrite: true })
    rec("T27e48 a later class line in the SAME block cannot relicense CODE", sameBlockClass.prompts.length === 1, `prompts=${sameBlockClass.prompts.length}`)
    const configDoc = await runStopCase("t27-w11-doc-config", LOG_DOC, "Implement the config change.", "Done.", { file: "src/config.json" })
    rec("T27e49 DOC claim + src/config.json → prompt", configDoc.prompts.length === 1, `prompts=${configDoc.prompts.length}`)
    const sqlDoc = await runStopCase("t27-w11-doc-sql", LOG_DOC, "Implement the migration.", "Done.", { file: "db/migrate.sql" })
    rec("T27e50 DOC claim + db/migrate.sql → prompt", sqlDoc.prompts.length === 1, `prompts=${sqlDoc.prompts.length}`)
    const findingsJson = await runStopCase("t27-w11-readonly-json", LOG_CODE, "仅评估，不修改。", "The findings are ready.", { file: "findings.json" })
    rec("T27e51 read-only audit + findings.json report → no prompt", findingsJson.prompts.length === 0, `prompts=${findingsJson.prompts.length}`)
    const heredocAfter = await runStopCase("t27-w11-heredoc-after", LOG_CODE, "Implement the fix.", "Done.", { bashOnlyCommand: "cat <<'EOF' > src/a.ts\nexport const x = 1\nEOF" })
    rec("T27e52 redirect AFTER the heredoc marker is observed", heredocAfter.prompts.length === 1, `prompts=${heredocAfter.prompts.length}`)
    const noSpace = await runStopCase("t27-w11-no-space", LOG_CODE, "Implement the fix.", "Done.", { bashOnlyCommand: "echo foo2> src/a.ts" })
    rec("T27e53 no-space redirect is observed", noSpace.prompts.length === 1, `prompts=${noSpace.prompts.length}`)
    const outputHtml = await runStopCase("t27-w11-output-html", LOG_DOC, "Only evaluate; do not modify code.", "Report ready.", { file: "output/report.html" })
    rec("T27e54 DOC + output/report.html → no prompt", outputHtml.prompts.length === 0, `prompts=${outputHtml.prompts.length}`)
    const cpMulti = await runStopCase("t27-w11-cp-multi", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp a.ts b.ts /tmp/backup" })
    rec("T27e55 multi-source cp to /tmp is not a project write", cpMulti.prompts.length === 0, `prompts=${cpMulti.prompts.length}`)
    const outputTs = await runStopCase("t27-w11-output-ts", LOG_DOC, "Implement the exporter.", "Done.", { file: "output/app.ts" })
    rec("T27e57 DOC claim + output/app.ts → prompt (report path does not hide code)", outputTs.prompts.length === 1, `prompts=${outputTs.prompts.length}`)
    const reportsPy = await runStopCase("t27-w11-reports-py", LOG_DOC, "Implement the parser.", "Done.", { file: "reports/parser.py" })
    rec("T27e58 DOC claim + reports/parser.py → prompt", reportsPy.prompts.length === 1, `prompts=${reportsPy.prompts.length}`)
    const outputReadOnly = await runStopCase("t27-w11-output-ro", LOG_CODE, "仅评估，不修改。", "Done.", { file: "output/app.ts" })
    rec("T27e59 read-only instruction + output/app.ts → prompt", outputReadOnly.prompts.length === 1, `prompts=${outputReadOnly.prompts.length}`)
    const dataJson = await runStopCase("t27-w11-data-json", LOG_CODE, "仅评估，不修改。", "Metrics ready.", { file: "data.json" })
    rec("T27e60 read-only audit + data.json report → no prompt", dataJson.prompts.length === 0, `prompts=${dataJson.prompts.length}`)
    const cpTarget = await runStopCase("t27-w11-cp-target", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp -t /tmp/backup a.ts b.ts" })
    rec("T27e61 cp -t directory target is outside the project → no prompt", cpTarget.prompts.length === 0, `prompts=${cpTarget.prompts.length}`)
    // W11 P1-1/P1-2 integration controls.
    const quotedRo = await runStopCase("t27-w11-quoted-ro", LOG_CODE, '上一版说“仅评估，不修改”，但现在实现 X。', "Done.")
    rec("T27e30 quoted historical read-only does not exempt a current implement turn", quotedRo.prompts.length === 1, `prompts=${quotedRo.prompts.length}`)
    const continueQ = await runStopCase("t27-w11-continue-q", LOG_CODE, "Implement the fix.", "Done. Continue?")
    rec("T27e31 'Done. Continue?' does not whitelist an incomplete CODE turn", continueQ.prompts.length === 1, `prompts=${continueQ.prompts.length}`)
    const shouldQ = await runStopCase("t27-w11-should-q", LOG_CODE, "Implement the fix.", "Should I proceed?")
    rec("T27e32 'Should I proceed?' whitelists an awaiting-user turn", shouldQ.prompts.length === 0, `prompts=${shouldQ.prompts.length}`)
    const noUserEarly = await runStopCase("t27-w11-no-user-early", LOG_CODE, null, "Done.", { gateFirst: true })
    rec("T27e62 no-user host: early gate + write → prompt", noUserEarly.prompts.length === 1, `prompts=${noUserEarly.prompts.length}`)
    const noUserLate = await runStopCase("t27-w11-no-user-late", LOG_CODE, null, "Done.", { gateLast: true })
    rec("T27e63 no-user host: gate after the write (last message) → no prompt", noUserLate.prompts.length === 0, `prompts=${noUserLate.prompts.length}`)
    const noUserSameMsg = await runStopCase("t27-w11-no-user-same-msg", LOG_CODE, null, "Done.", { gateSameMsgAfterWrite: true })
    rec("T27e64 no-user host: gate after the write, then a final Done message → no prompt", noUserSameMsg.prompts.length === 0, `prompts=${noUserSameMsg.prompts.length}`)
    const outHtml = await runStopCase("t27-w11-output-html-app", LOG_DOC, "Implement the UI.", "Done.", { file: "output/app.html" })
    rec("T27e65 DOC claim + output/app.html → prompt", outHtml.prompts.length === 1, `prompts=${outHtml.prompts.length}`)
    const outConfig = await runStopCase("t27-w11-output-config", LOG_DOC, "Implement the config.", "Done.", { file: "output/config.json" })
    rec("T27e66 DOC claim + output/config.json → prompt", outConfig.prompts.length === 1, `prompts=${outConfig.prompts.length}`)
    const reportsSchema = await runStopCase("t27-w11-reports-schema", LOG_DOC, "Implement the schema.", "Done.", { file: "reports/schema.json" })
    rec("T27e67 DOC claim + reports/schema.json → prompt", reportsSchema.prompts.length === 1, `prompts=${reportsSchema.prompts.length}`)
    const srcData = await runStopCase("t27-w11-src-data", LOG_DOC, "Implement the data layer.", "Done.", { file: "src/data.json" })
    rec("T27e68 DOC claim + src/data.json → prompt", srcData.prompts.length === 1, `prompts=${srcData.prompts.length}`)
    const cpTdSpace = await runStopCase("t27-w11-cp-td-space", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp --target-directory /tmp/backup a.ts b.ts" })
    rec("T27e69 cp --target-directory space form is outside the project → no prompt", cpTdSpace.prompts.length === 0, `prompts=${cpTdSpace.prompts.length}`)
    const cpRt = await runStopCase("t27-w11-cp-rt", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp -rt /tmp/backup a.ts b.ts" })
    rec("T27e70 cp -rt directory target is outside the project → no prompt", cpRt.prompts.length === 0, `prompts=${cpRt.prompts.length}`)
    const srcReport = await runStopCase("t27-w11-src-report", LOG_DOC, "Implement the report config.", "Done.", { file: "src/report.json" })
    rec("T27e71 DOC claim + src/report.json → prompt (report name inside code dir)", srcReport.prompts.length === 1, `prompts=${srcReport.prompts.length}`)
    const makefile = await runStopCase("t27-w11-makefile", LOG_DOC, "Implement the build.", "Done.", { file: "Makefile" })
    rec("T27e72 DOC claim + Makefile → prompt", makefile.prompts.length === 1, `prompts=${makefile.prompts.length}`)
    const dockerfile = await runStopCase("t27-w11-dockerfile", LOG_DOC, "Implement the image.", "Done.", { file: "Dockerfile" })
    rec("T27e73 DOC claim + Dockerfile → prompt", dockerfile.prompts.length === 1, `prompts=${dockerfile.prompts.length}`)
    const tableJson = await runStopCase("t27-w11-table-json", LOG_CODE, "仅评估，不修改。", "Table ready.", { file: "table.json" })
    rec("T27e74 read-only audit + table.json report → no prompt", tableJson.prompts.length === 0, `prompts=${tableJson.prompts.length}`)
    const cpAttached = await runStopCase("t27-w11-cp-attached", LOG_CODE, "仅评估，不修改。", "Done.", { bashOnlyCommand: "cp -t/tmp/backup a.ts b.ts" })
    rec("T27e75 cp attached -t target is outside the project → no prompt", cpAttached.prompts.length === 0, `prompts=${cpAttached.prompts.length}`)
    const pauseHidden = await runStopCase("t27-w12-pause-hidden", LOG_CODE, "Implement the fix.", "Evaluation complete.", { pausedFile: PAUSE_OK })
    rec("T27e76 hidden paused file (no [PAUSED] declaration) → prompt", pauseHidden.prompts.length === 1, `prompts=${pauseHidden.prompts.length}`)
    const pauseVisible = await runStopCase("t27-w12-pause-visible", LOG_CODE, "Implement the fix.", "[PAUSED] gate=schema | question=choose one | default-if-continue=(a)", { pausedFile: PAUSE_OK })
    rec("T27e77 valid paused packet + visible [PAUSED] → no prompt", pauseVisible.prompts.length === 0, `prompts=${pauseVisible.prompts.length}`)
    const pauseBad = await runStopCase("t27-w12-pause-bad", LOG_CODE, "Implement the fix.", "[PAUSED] gate=schema", { pausedFile: PAUSE_OK.replace("state: fixture", "note: fixture") })
    rec("T27e78 malformed paused packet → prompt", pauseBad.prompts.length === 1, `prompts=${pauseBad.prompts.length}`)
    const classEForge = await runStopCase("t27-w12-classe-forge", LOG_CODE, "Implement the fix.", "Class-E approved. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e79 Class-E file without user approval text → prompt", classEForge.prompts.length === 1, `prompts=${classEForge.prompts.length}`)
    const classEOk = await runStopCase("t27-w12-classe-ok", LOG_CODE, "批准 Class-E 部署。", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e80 Class-E file + user approval + assistant declaration → no prompt", classEOk.prompts.length === 0, `prompts=${classEOk.prompts.length}`)
    const classEDenied = await runStopCase("t27-w12-classe-denied", LOG_CODE, "不同意 Class-E 部署。", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e81 Class-E record + user denial → prompt", classEDenied.prompts.length === 1, `prompts=${classEDenied.prompts.length}`)
    const classEMention = await runStopCase("t27-w12-classe-mention", LOG_CODE, "Please implement the approved plan.", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e82 'approved plan' mention is not a Class-E grant → prompt", classEMention.prompts.length === 1, `prompts=${classEMention.prompts.length}`)
    const classEHistoric = await runStopCase("t27-w12-classe-historic", LOG_CODE, "批准 Class-E 部署。", "Class-E approved by user. Awaiting deploy.", { classEPreUser: "D-1 | Class-E | approved by user | old task\n", classEAppend: "\n- note: unrelated follow-up\n" })
    rec("T27e83 historical Class-E line + unrelated append is not current approval → prompt", classEHistoric.prompts.length === 1, `prompts=${classEHistoric.prompts.length}`)
    const quotedHeredoc = await runStopCase("t27-w12-quoted-heredoc", LOG_CODE, "Implement the fix.", "Done.", { bashOnlyCommand: 'echo "a << b"\ncat > src/a.ts <<\'EOF\'\nexport const x = 1\nEOF' })
    rec("T27e84 quoted << does not blind the later real write → prompt", quotedHeredoc.prompts.length === 1, `prompts=${quotedHeredoc.prompts.length}`)
    const reportIndex = await runStopCase("t27-w12-report-index", LOG_DOC, "Only evaluate; do not modify code.", "Report ready.", { file: "reports/index.html" })
    rec("T27e85 DOC + reports/index.html → no prompt", reportIndex.prompts.length === 0, `prompts=${reportIndex.prompts.length}`)
    const appYaml = await runStopCase("t27-w12-app-yaml", LOG_DOC, "Implement the deploy config.", "Done.", { file: "output/app.yaml" })
    rec("T27e86 DOC + output/app.yaml → prompt", appYaml.prompts.length === 1, `prompts=${appYaml.prompts.length}`)
    const compose = await runStopCase("t27-w12-compose", LOG_DOC, "Implement the deploy config.", "Done.", { file: "output/docker-compose.yml" })
    rec("T27e87 DOC + output/docker-compose.yml → prompt", compose.prompts.length === 1, `prompts=${compose.prompts.length}`)
    const scriptsReport = await runStopCase("t27-w12-scripts-report", LOG_DOC, "Implement the report generator.", "Done.", { file: "scripts/report.json" })
    rec("T27e88 DOC + scripts/report.json → prompt", scriptsReport.prompts.length === 1, `prompts=${scriptsReport.prompts.length}`)
    const commentHeredoc = await runStopCase("t27-w12-comment-heredoc", LOG_CODE, "Implement the fix.", "Done.", { bashOnlyCommand: 'echo start\n# note << not a heredoc\ncat > src/a.ts <<\'EOF\'\nexport const x = 1\nEOF' })
    rec("T27e89 comment << does not blind a later write → prompt", commentHeredoc.prompts.length === 1, `prompts=${commentHeredoc.prompts.length}`)
    const dashHeredoc = await runStopCase("t27-w12-dash-heredoc", LOG_CODE, "Implement the fix.", "Done.", { bashOnlyCommand: "cat <<-EOF\n\texport const x = 1\n\tEOF\ncat > src/a.ts <<'EOF'\nexport const x = 2\nEOF" })
    rec("T27e90 <<- tab terminator does not blind a later write → prompt", dashHeredoc.prompts.length === 1, `prompts=${dashHeredoc.prompts.length}`)
    const outputIndex = await runStopCase("t27-w12-output-index", LOG_DOC, "Implement the UI.", "Done.", { file: "output/index.html" })
    rec("T27e91 DOC + output/index.html → prompt", outputIndex.prompts.length === 1, `prompts=${outputIndex.prompts.length}`)
    const deployYaml = await runStopCase("t27-w12-deploy-yaml", LOG_DOC, "Implement the deployment.", "Done.", { file: "output/deployment.yaml" })
    rec("T27e92 DOC + output/deployment.yaml → prompt", deployYaml.prompts.length === 1, `prompts=${deployYaml.prompts.length}`)
    const appendixJson = await runStopCase("t27-w12-appendix-json", LOG_CODE, "仅评估，不修改。", "Appendix ready.", { file: "output/appendix.json" })
    rec("T27e93 read-only audit + output/appendix.json report → no prompt", appendixJson.prompts.length === 0, `prompts=${appendixJson.prompts.length}`)
    const notesJson = await runStopCase("t27-w12-notes-json", LOG_CODE, "仅评估，不修改。", "Notes ready.", { file: "output/notes.json" })
    rec("T27e101 read-only audit + output/notes.json report → no prompt", notesJson.prompts.length === 0, `prompts=${notesJson.prompts.length}`)
    const outputsIndex = await runStopCase("t27-w12-outputs-index", LOG_DOC, "Only evaluate; do not modify code.", "Report ready.", { file: "outputs/index.html" })
    rec("T27e102 DOC + outputs/index.html report → no prompt", outputsIndex.prompts.length === 0, `prompts=${outputsIndex.prompts.length}`)
    const appendixHtml = await runStopCase("t27-w12-appendix-html", LOG_DOC, "Only evaluate; do not modify code.", "Appendix ready.", { file: "output/appendix.html" })
    rec("T27e103 DOC + output/appendix.html report → no prompt", appendixHtml.prompts.length === 0, `prompts=${appendixHtml.prompts.length}`)
    const classECn = await runStopCase("t27-w12-classe-cn", LOG_CODE, "我批准 Class-E 部署。", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e94 natural Chinese Class-E approval → no prompt", classECn.prompts.length === 0, `prompts=${classECn.prompts.length}`)
    const classEDeny = await runStopCase("t27-w12-classe-deny", LOG_CODE, "I will not approve Class-E deployment.", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e95 English Class-E denial → prompt", classEDeny.prompts.length === 1, `prompts=${classEDeny.prompts.length}`)
    const classEGeneric = await runStopCase("t27-w12-classe-generic", LOG_CODE, "I approve the plan.", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e96 generic 'I approve the plan' is not a Class-E grant → prompt", classEGeneric.prompts.length === 1, `prompts=${classEGeneric.prompts.length}`)
    const classEGo = await runStopCase("t27-w12-classe-go", LOG_CODE, "go ahead and implement the fix", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e97 generic 'go ahead' is not a Class-E grant → prompt", classEGo.prompts.length === 1, `prompts=${classEGo.prompts.length}`)
    const classEHavent = await runStopCase("t27-w12-classe-havent", LOG_CODE, "I haven't approved Class-E deployment.", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e98 \"haven't approved\" is a denial → prompt", classEHavent.prompts.length === 1, `prompts=${classEHavent.prompts.length}`)
    const classEClause = await runStopCase("t27-w12-classe-clause", LOG_CODE, "Class-E is pending; I approve the plan.", "Class-E approved by user. Awaiting deploy.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e99 approval in a different clause is not a Class-E grant → prompt", classEClause.prompts.length === 1, `prompts=${classEClause.prompts.length}`)
    const classENothing = await runStopCase("t27-w12-classe-nothing", LOG_CODE, "我批准 Class-E 部署。", "Class-E approved; nothing pending.", { classEFile: "D-1 | Class-E | approved by user | deploy\n" })
    rec("T27e100 'nothing pending' does not negate a Class-E declaration → no prompt", classENothing.prompts.length === 0, `prompts=${classENothing.prompts.length}`)
  }

  // ---- W10: v2 has no message roles; the positive leg must still journal
  // stop-debt (debt-only mode, never a prompt). ----
  {
    const rootV2 = newFixture("t27-w10-v2")
    write(rootV2, "tests/verification_log.md", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
    write(rootV2, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const q = []
    let waiting = null
    const bus = {
      subscribe() {
        return {
          [Symbol.asyncIterator]() { return this },
          next() {
            if (q.length) return Promise.resolve({ done: false, value: q.shift() })
            return new Promise((res) => { waiting = () => res(q.length ? { done: false, value: q.shift() } : { done: true }) })
          },
          return() { return Promise.resolve({ done: true }) },
        }
      },
      emit(e) { q.push(e); if (waiting) { const w = waiting; waiting = null; w() } },
    }
    const hooks = {}
    const prompts = []
    const ctx = {
      location: { directory: rootV2 },
      tool: { hook: async (name, fn) => { hooks[name] = fn; return { dispose: async () => {} } } },
      event: { subscribe: () => bus.subscribe() },
      session: { interrupt: async () => {}, prompt: async () => { prompts.push("prompt") } },
    }
    await auditModule.default.setup(ctx)
    bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2stop", name: "vibeweaver" } })
    await hooks["execute.before"]({ tool: "write", sessionID: "ses_v2stop", messageID: "m1", id: "t1", input: { filePath: path.join(rootV2, "src", "a.ts") } })
    await hooks["execute.after"]({ tool: "write", sessionID: "ses_v2stop", status: "completed", id: "t1", result: { output: "ok" } })
    bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2stop", messageID: "m1", content: [{ type: "text", text: "Done." }] } })
    bus.emit({ type: "session.status", data: { sessionID: "ses_v2stop", status: { type: "idle" } } })
    await new Promise((r) => setTimeout(r, 80))
    let debt = []
    try {
      const st = JSON.parse(readFileSync(path.join(rootV2, ".vibeweaver", "audit-state.json"), "utf8"))
      debt = (st.roots && st.roots[rootV2] && st.roots[rootV2].stopDebt) || []
    } catch {
      /* no state */
    }
    rec("T27e21 v2 positive leg journals incomplete stop-debt (no prompt)", debt.some((d) => d.kind === "incomplete") && prompts.length === 0, `debt=${JSON.stringify(debt).slice(0, 120)} prompts=${prompts.length}`)
  }

  // ---- W11 P1-4: a v2 write that never reaches execute.after (blocked or
  // failed) must NOT count as task-write evidence, even though execute.before
  // observed its input.
  {
    const rootV2b = newFixture("t27-w11-v2-blocked")
    write(rootV2b, "tests/verification_log.md", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
    write(rootV2b, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const q = []
    let waiting = null
    const bus = {
      subscribe() {
        return {
          [Symbol.asyncIterator]() { return this },
          next() {
            if (q.length) return Promise.resolve({ done: false, value: q.shift() })
            return new Promise((res) => { waiting = () => res(q.length ? { done: false, value: q.shift() } : { done: true }) })
          },
          return() { return Promise.resolve({ done: true }) },
        }
      },
      emit(e) { q.push(e); if (waiting) { const w = waiting; waiting = null; w() } },
    }
    const hooks = {}
    const prompts = []
    const ctx = {
      location: { directory: rootV2b },
      tool: { hook: async (name, fn) => { hooks[name] = fn; return { dispose: async () => {} } } },
      event: { subscribe: () => bus.subscribe() },
      session: { interrupt: async () => {}, prompt: async () => { prompts.push("prompt") } },
    }
    await auditModule.default.setup(ctx)
    bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2block", name: "vibeweaver" } })
    await hooks["execute.before"]({ tool: "write", sessionID: "ses_v2block", messageID: "m1", id: "t1", input: { filePath: path.join(rootV2b, "src", "a.ts") } })
    // The hook fires on every execute.after; a failed status must be ignored.
    await hooks["execute.after"]({ tool: "write", sessionID: "ses_v2block", status: "error", id: "t1", result: { output: "permission denied" } })
    // No completed execute.after either.
    bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2block", messageID: "m1", content: [{ type: "text", text: "Done." }] } })
    bus.emit({ type: "session.status", data: { sessionID: "ses_v2block", status: { type: "idle" } } })
    await new Promise((r) => setTimeout(r, 80))
    let debt = []
    try {
      const st = JSON.parse(readFileSync(path.join(rootV2b, ".vibeweaver", "audit-state.json"), "utf8"))
      debt = (st.roots && st.roots[rootV2b] && st.roots[rootV2b].stopDebt) || []
    } catch {
      /* no state */
    }
    rec("T27e33 v2 blocked/failed write does NOT journal task-write debt", debt.length === 0, `debt=${JSON.stringify(debt).slice(0, 120)}`)
  }

  // ---- W11: v2 has no roles; a gate in the last content update must still
  // whitelist a completed turn instead of journaling debt.
  {
    const rootV2g = newFixture("t27-w11-v2-gate")
    write(rootV2g, "tests/verification_log.md", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
    write(rootV2g, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const q = []
    let waiting = null
    const bus = {
      subscribe() {
        return {
          [Symbol.asyncIterator]() { return this },
          next() {
            if (q.length) return Promise.resolve({ done: false, value: q.shift() })
            return new Promise((res) => { waiting = () => res(q.length ? { done: false, value: q.shift() } : { done: true }) })
          },
          return() { return Promise.resolve({ done: true }) },
        }
      },
      emit(e) { q.push(e); if (waiting) { const w = waiting; waiting = null; w() } },
    }
    const hooks = {}
    const ctx = {
      location: { directory: rootV2g },
      tool: { hook: async (name, fn) => { hooks[name] = fn; return { dispose: async () => {} } } },
      event: { subscribe: () => bus.subscribe() },
      session: { interrupt: async () => {}, prompt: async () => {} },
    }
    await auditModule.default.setup(ctx)
    bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2gate", name: "vibeweaver" } })
    await hooks["execute.before"]({ tool: "write", sessionID: "ses_v2gate", messageID: "m1", id: "t1", input: { filePath: path.join(rootV2g, "src", "a.ts") } })
    await hooks["execute.after"]({ tool: "write", sessionID: "ses_v2gate", status: "completed", id: "t1", result: { output: "ok" } })
    bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gate", messageID: "m1", content: [{ type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" }] } })
    bus.emit({ type: "session.status", data: { sessionID: "ses_v2gate", status: { type: "idle" } } })
    await new Promise((r) => setTimeout(r, 80))
    let debt = []
    try {
      const st = JSON.parse(readFileSync(path.join(rootV2g, ".vibeweaver", "audit-state.json"), "utf8"))
      debt = (st.roots && st.roots[rootV2g] && st.roots[rootV2g].stopDebt) || []
    } catch {
      /* no state */
    }
    rec("T27e37 v2 gate-only completion journals debt (positive is always debt-only)", debt.some((x) => x.kind === "incomplete"), `debt=${JSON.stringify(debt).slice(0, 120)}`)
  }

  // ---- W11 re-review: v2 boundaries — an old completed block, an old gate,
  // and a bash redirect must not suppress the current turn's debt. ----
  {
    const mkV2 = async (name, log, opts = {}) => {
      const root = newFixture(name)
      write(root, "tests/verification_log.md", log)
      write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
      const q = []
      let waiting = null
      const bus = {
        subscribe() {
          return {
            [Symbol.asyncIterator]() { return this },
            next() {
              if (q.length) return Promise.resolve({ done: false, value: q.shift() })
              return new Promise((res) => { waiting = () => res(q.length ? { done: false, value: q.shift() } : { done: true }) })
            },
            return() { return Promise.resolve({ done: true }) },
          }
        },
        emit(e) { q.push(e); if (waiting) { const w = waiting; waiting = null; w() } },
      }
      const hooks = {}
      const prompts = []
      const ctx = {
        location: { directory: root },
        tool: { hook: async (name, fn) => { hooks[name] = fn; return { dispose: async () => {} } } },
        event: { subscribe: () => bus.subscribe() },
        session: { interrupt: async () => {}, prompt: async (args) => { if (opts.promptThrows) throw new Error("prompt unavailable"); prompts.push((args && args.text) || "") } },
      }
      await auditModule.default.setup(ctx)
      const debt = async () => {
        try {
          const st = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8"))
          return (st.roots && st.roots[root] && st.roots[root].stopDebt) || []
        } catch { return [] }
      }
      return { root, bus, hooks, debt, prompts }
    }
    const oldBlock = "## Task: old\n- class: CODE — logic\n- assert-run: assert_artifacts.py: all 3 checks pass (exit 0)\n- final-run: --final — pass=3/fail=0\n"
    {
      const h = await mkV2("t27-w11-v2-stale-block", oldBlock)
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2old", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "write", sessionID: "ses_v2old", messageID: "m1", id: "t1", input: { filePath: path.join(h.root, "src", "a.ts") } })
      await h.hooks["execute.after"]({ tool: "write", sessionID: "ses_v2old", status: "completed", id: "t1", result: { output: "ok" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2old", messageID: "m1", content: [{ type: "text", text: "Done." }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2old", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      const d = await h.debt()
      rec("T27e44 v2 old completed block does not exempt a new task → debt", d.some((x) => x.kind === "incomplete"), `debt=${JSON.stringify(d).slice(0, 120)}`)
    }
    {
      const h = await mkV2("t27-w11-v2-bash", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2bash", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "bash", sessionID: "ses_v2bash", messageID: "m1", id: "t1", input: { command: `cat > ${path.join(h.root, "src", "a.ts")} <<'EOF'\nexport const x = 1\nEOF` } })
      await h.hooks["execute.after"]({ tool: "bash", sessionID: "ses_v2bash", status: "completed", id: "t1", result: { output: "" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2bash", messageID: "m1", content: [{ type: "text", text: "Done." }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2bash", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      const d = await h.debt()
      rec("T27e45 v2 bash redirect write → debt", d.some((x) => x.kind === "incomplete"), `debt=${JSON.stringify(d).slice(0, 120)}`)
    }
    {
      const h = await mkV2("t27-w11-v2-old-gate", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2gateold", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "bash", sessionID: "ses_v2gateold", messageID: "m0", id: "t0", input: { command: "ls" } })
      await h.hooks["execute.after"]({ tool: "bash", sessionID: "ses_v2gateold", status: "completed", id: "t0", result: { output: "" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gateold", messageID: "m1", content: [{ type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2gateold", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gateold", messageID: "m2", content: [{ type: "text", text: "上下文快耗尽了，先到这里。" }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2gateold", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      const d = await h.debt()
      rec("T27e46 old v2 gate does not suppress a later euphemism prompt", h.prompts.length === 1, `prompts=${h.prompts.length}`)
    }
    {
      const h = await mkV2("t27-w11-v2-gate-done", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2gatedone", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "write", sessionID: "ses_v2gatedone", messageID: "m1", id: "t1", input: { filePath: path.join(h.root, "src", "a.ts") } })
      await h.hooks["execute.after"]({ tool: "write", sessionID: "ses_v2gatedone", status: "completed", id: "t1", result: { output: "ok" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gatedone", messageID: "m1", content: [{ type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" }] } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gatedone", messageID: "m2", content: [{ type: "text", text: "Done." }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2gatedone", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      const d = await h.debt()
      rec("T27e56 v2 gate + Done journals debt (positive is always debt-only)", d.some((x) => x.kind === "incomplete"), `debt=${JSON.stringify(d).slice(0, 120)}`)
    }
    {
      const h = await mkV2("t27-w13-v2-positive-doc", "## Task: fixture\n- class: DOC — prose\n- iter 1 PASS: report\n")
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2doc", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "write", sessionID: "ses_v2doc", messageID: "m1", id: "t1", input: { filePath: path.join(h.root, "src", "a.ts") } })
      await h.hooks["execute.after"]({ tool: "write", sessionID: "ses_v2doc", status: "completed", id: "t1", result: { output: "ok" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2doc", messageID: "m1", content: [{ type: "text", text: "Done." }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2doc", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      const d = await h.debt()
      rec("T27e104 v2 positive + DOC claim journals debt (never silently ignores)", d.some((x) => x.kind === "incomplete"), `debt=${JSON.stringify(d).slice(0, 120)}`)
    }
    {
      const h = await mkV2("t27-w13-v2-gate-euphemism", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n")
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2gateex", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "write", sessionID: "ses_v2gateex", messageID: "m1", id: "t1", input: { filePath: path.join(h.root, "src", "a.ts") } })
      await h.hooks["execute.after"]({ tool: "write", sessionID: "ses_v2gateex", status: "completed", id: "t1", result: { output: "ok" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gateex", messageID: "m1", content: [{ type: "text", text: "[Verification Gate] Verifier: direct-read | Class: CODE | assert_artifacts.py: pass=3/fail=0" }] } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2gateex", messageID: "m2", content: [{ type: "text", text: "上下文快耗尽了，先到这里。" }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2gateex", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 80))
      rec("T27e105 v2 explicit euphemism + model-authored gate still prompts", h.prompts.length === 1, `prompts=${h.prompts.length}`)
    }
    {
      const h = await mkV2("t27-w13-v2-prompt-fail", "## Task: fixture\n- class: CODE — logic\n- iter 1 FAIL: x | diagnosis: d | changed: src/a.ts\n", { promptThrows: true })
      h.bus.emit({ type: "session.skill.activated", data: { sessionID: "ses_v2pfail", name: "vibeweaver" } })
      await h.hooks["execute.before"]({ tool: "bash", sessionID: "ses_v2pfail", messageID: "m1", id: "t0", input: { command: "ls" } })
      await h.hooks["execute.after"]({ tool: "bash", sessionID: "ses_v2pfail", status: "completed", id: "t0", result: { output: "" } })
      h.bus.emit({ type: "session.message.content.updated", data: { sessionID: "ses_v2pfail", messageID: "m1", content: [{ type: "text", text: "上下文快耗尽了，先到这里。" }] } })
      h.bus.emit({ type: "session.status", data: { sessionID: "ses_v2pfail", status: { type: "idle" } } })
      await new Promise((r) => setTimeout(r, 120))
      const d = await h.debt()
      rec("T27e106 v2 prompt rejection journals debt instead of burning budget", d.some((x) => x.why === "prompt-failed"), `debt=${JSON.stringify(d).slice(0, 160)}`)
    }
  }

  // ---- user stop directive → whitelisted, no prompt ----
  {
    const root27b = newFixture("t27-userstop")
    write(root27b, "tests/verification_log.md", "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n")
    write(root27b, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const calls = { prompts: [] }
    const plugin27b = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
      },
      directory: root27b,
    })
    const sid = "ses_t27b"
    const ev = (type, properties) => plugin27b.event({ event: { type, properties } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "t1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } })
    await ev("message.updated", { sessionID: sid, info: { id: "u1", role: "user" } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "pu1", messageID: "u1", type: "text", text: "停下来吧，今天到此为止，明天继续。" } })
    await ev("message.updated", { sessionID: sid, info: { id: "m1", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "p1", messageID: "m1", type: "text", text: "好的，上下文快耗尽了，先停在这里。" } })
    await ev("session.idle", { sessionID: sid })
    rec("T27f user stop directive before claim → whitelisted, no prompt", calls.prompts.length === 0, `prompts=${calls.prompts.length}`)
  }

  // ---- truncation (finish:"length") fires the same channel ----
  {
    const root27c = newFixture("t27-trunc")
    write(root27c, "tests/verification_log.md", "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n")
    write(root27c, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    const calls = { prompts: [] }
    const plugin27c = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
      },
      directory: root27c,
    })
    const sid = "ses_t27c"
    const ev = (type, properties) => plugin27c.event({ event: { type, properties } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "t1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } })
    await ev("message.updated", { sessionID: sid, info: { id: "m1", role: "assistant", modelID: "m", finish: "length", tokens: { input: 100, output: 16384, reasoning: 0, cache: { read: 0, write: 0 } } } })
    await ev("session.idle", { sessionID: sid })
    rec("T27g finish:length + incomplete → corrective prompt (truncation ≠ complete)", calls.prompts.length === 1 && /truncat|length|output.limit/i.test(calls.prompts[0] || ""), `prompts=${calls.prompts.length} ${(calls.prompts[0] || "").slice(0, 100)}`)
  }

  // ---- measured fill quoted when audit.json configures contextLimitTokens ----
  {
    const root27d = newFixture("t27-fill")
    write(root27d, "tests/verification_log.md", "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n")
    write(root27d, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
    write(root27d, "audit-config.json", JSON.stringify({ contextLimitTokens: 10000 }))
    process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root27d, "audit-config.json")
    const calls = { prompts: [] }
    const plugin27d = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
      },
      directory: root27d,
    })
    const sid = "ses_t27d"
    const ev = (type, properties) => plugin27d.event({ event: { type, properties } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "t1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } })
    await ev("message.updated", { sessionID: sid, info: { id: "m1", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 1000, output: 100, reasoning: 0, cache: { read: 500, write: 0 } } } })
    await ev("message.part.updated", { sessionID: sid, part: { id: "p1", messageID: "m1", type: "text", text: "上下文快耗尽了，先到这里。" } })
    await ev("session.idle", { sessionID: sid })
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    rec("T27h fill 15% quoted in corrective (input 1000 + cache.read 500 / 10000)", calls.prompts.length === 1 && /15%/.test(calls.prompts[0] || ""), `prompts=${calls.prompts.length} ${(calls.prompts[0] || "").slice(0, 160)}`)
  }

  // ---- userStop negation/directive shape (review F6) + final-run wave scope (R1#3) + gate-marker message scope (F4) + env off (R1#10) + high-fill phrasing (R1#8) ----
  {
    const mk = async (name, log) => {
      const root = newFixture(name)
      write(root, "tests/verification_log.md", log)
      write(root, "tests/acceptance.md", "> cap=5  stall=3×\n1. done\n")
      const calls = { prompts: [] }
      const plugin = await VibeweaverAudit({
        client: {
          app: { log: async () => {} },
          session: { abort: async () => {}, prompt: async (a) => calls.prompts.push((a && a.body && a.body.parts && a.body.parts[0] && a.body.parts[0].text) || "") },
        },
        directory: root,
      })
      return { root, calls, plugin }
    }
    const ACTIVE_LOG = "## Task: fixture\n- iter 1 FAIL: x | diagnosis: d | changed: a.ts\n- working-note: created (fixture — active task)\n"
    const drive = async (plugin, sid, userText, asstText, tokens) => {
      const ev = (type, properties) => plugin.event({ event: { type, properties } })
      await ev("message.part.updated", { sessionID: sid, part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
      await ev("message.part.updated", { sessionID: sid, part: { id: "t1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } })
      if (userText != null) {
        await ev("message.updated", { sessionID: sid, info: { id: "u1", role: "user" } })
        await ev("message.part.updated", { sessionID: sid, part: { id: "pu1", messageID: "u1", type: "text", text: userText } })
      }
      await ev("message.updated", { sessionID: sid, info: { id: "m1", role: "assistant", modelID: "m", finish: "stop", tokens: tokens || { input: 100, output: 10, reasoning: 0, cache: { read: 0, write: 0 } } } })
      await ev("message.part.updated", { sessionID: sid, part: { id: "p1", messageID: "m1", type: "text", text: asstText } })
      await ev("session.idle", { sessionID: sid })
    }

    const n1 = await mk("t27-neg-stop", ACTIVE_LOG)
    await drive(n1.plugin, "ses_n1", "Don't stop until all criteria pass.", "上下文快耗尽了，先到这里。")
    rec("T27i1 negated 'don't stop' is NOT a stop directive → prompt fires (review F6)", n1.calls.prompts.length === 1, `prompts=${n1.calls.prompts.length}`)
    const n2 = await mk("t27-cancel-button", ACTIVE_LOG)
    await drive(n2.plugin, "ses_n2", "The cancel button should rollback the form.", "上下文快耗尽了，先到这里。")
    rec("T27i2 'cancel button' non-directive → prompt fires (review F6)", n2.calls.prompts.length === 1, `prompts=${n2.calls.prompts.length}`)
    const n2b = await mk("t27-quit-server", ACTIVE_LOG)
    await drive(n2b.plugin, "ses_n2b", "quit the dev server and restart it with pm2", "上下文快耗尽了，先到这里。")
    rec("T27i2b 'quit the dev server' process instruction → prompt fires (review N3)", n2b.calls.prompts.length === 1, `prompts=${n2b.calls.prompts.length}`)
    const n3 = await mk("t27-user-quit", ACTIVE_LOG)
    await drive(n3.plugin, "ses_n3", "stop here please, we continue tomorrow.", "上下文快耗尽了，先到这里。")
    rec("T27i3 explicit 'stop here please' → whitelisted, no prompt", n3.calls.prompts.length === 0, `prompts=${n3.calls.prompts.length}`)

    const c1 = await mk("t27-wave-complete", "## Task: fixture\n- iter 1 PASS: all\n- assert-run: assert_artifacts.py: all 30 checks pass (exit 0)\n- final-run: --final — pass=19/fail=0\n")
    await drive(c1.plugin, "ses_c1", "继续", "上次误判过上下文快耗尽的问题，复盘一下。")
    rec("T27i4 wave completed on disk (final-run) → taskActive false, no prompt (R1#3)", c1.calls.prompts.length === 0, `prompts=${c1.calls.prompts.length}`)

    const g1 = await mk("t27-gatemarker-scope", ACTIVE_LOG)
    {
      const ev = (type, properties) => g1.plugin.event({ event: { type, properties } })
      await ev("message.part.updated", { sessionID: "ses_g1", part: { id: "sk", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
      await ev("message.part.updated", { sessionID: "ses_g1", part: { id: "t1", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } })
      await ev("message.updated", { sessionID: "ses_g1", info: { id: "m0", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 1, output: 1, cache: { read: 0 } } } })
      await ev("message.part.updated", { sessionID: "ses_g1", part: { id: "p0", messageID: "m0", type: "text", text: "[Verification Gate] … earlier wave completion …" } })
      await ev("message.updated", { sessionID: "ses_g1", info: { id: "m1", role: "assistant", modelID: "m", finish: "stop", tokens: { input: 1, output: 1, cache: { read: 0 } } } })
      await ev("message.part.updated", { sessionID: "ses_g1", part: { id: "p1", messageID: "m1", type: "text", text: "上下文快耗尽了，先到这里。" } })
      await ev("session.idle", { sessionID: "ses_g1" })
      rec("T27i5 gate marker in an OLDER message does NOT whitelist the new wave (review F4)", g1.calls.prompts.length === 1, `prompts=${g1.calls.prompts.length}`)
    }

    const e1 = await mk("t27-env-off", ACTIVE_LOG)
    process.env.VIBEWEAVER_STOPGUARD = "off"
    await drive(e1.plugin, "ses_e1", null, "上下文快耗尽了，先到这里。")
    delete process.env.VIBEWEAVER_STOPGUARD
    rec("T27i6 VIBEWEAVER_STOPGUARD=off → fully silent (R1#10)", e1.calls.prompts.length === 0, `prompts=${e1.calls.prompts.length}`)

    const f1 = await mk("t27-highfill", ACTIVE_LOG)
    write(f1.root, "audit-config.json", JSON.stringify({ contextLimitTokens: 10000 }))
    process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(f1.root, "audit-config.json")
    await drive(f1.plugin, "ses_f1", null, "上下文快耗尽了，先到这里。", { input: 9000, output: 100, cache: { read: 500 } })
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    const ftext = f1.calls.prompts[0] || ""
    rec("T27i7 fill 95% → softened phrasing, no 'has no basis' accusation (R1#8)", f1.calls.prompts.length === 1 && /95%/.test(ftext) && !/has no basis/.test(ftext), ftext.slice(0, 160))
  }
}

// =====================================================================
// T34 — loop-guard identical-tool-run (same tool + identical args ×N,
// 2026-10-14). The reported failure mode: a ~450-deep run of identical
// MCP calls (`weave-connector_ssh_shell_open [profile=newsrv, name=p01c]`)
// with zero intervening text — invisible to the text byte detectors and to
// noop-bash (non-bash tool, `t.tool !== "bash"` breaks its run). Contract:
// >=IDENTICAL_RUN_MIN trailing observations with DISTINCT part ids sharing
// ONE (tool, canonical-args) fingerprint -> one corrective intervention.
// D-5 boundary: distinct calls only (pid re-observations deduped), the
// detector NEVER collapses observations into fewer calls.
// =====================================================================
{
  const hasItr = typeof identicalToolRunFinding === "function"
  const hasCj = typeof canonicalJson === "function"
  const cj = hasCj ? canonicalJson : (v) => JSON.stringify(v)
  const mkMcp = (pid, input) => ({ tool: "weave-connector_ssh_shell_open", args: cj(input), pid, t: 1 })
  const OPEN_INPUT = { profile: "newsrv", name: "p01c", record: true }

  // ---- T34a — threshold: 4 distinct-pid identical MCP calls -> finding ----
  const four = ["p1", "p2", "p3", "p4"].map((p) => mkMcp(p, OPEN_INPUT))
  const f4 = hasItr ? identicalToolRunFinding(four) : undefined
  rec("T34a 4 consecutive identical MCP calls (distinct pids) -> identical-tool-run finding", !!f4 && f4.kind === "identical-tool-run", hasItr ? (f4 ? `kind=${f4.kind} pattern=${f4.pattern.slice(0, 90)}` : "null") : "detector missing (RED)")
  rec("T34a pattern names tool + count + values-free args shape (keyCount + length, NO names/values)", !!f4 && /weave-connector_ssh_shell_open/.test(f4.pattern) && /4 consecutive identical/.test(f4.pattern) && /keys=3 /.test(f4.pattern) && /argsLen=\d+/.test(f4.pattern) && !/p01c/.test(f4.pattern) && !/profile/.test(f4.pattern) && !/name/.test(f4.pattern), hasItr && f4 ? f4.pattern.slice(0, 120) : "detector missing (RED)")
  const f3 = hasItr ? identicalToolRunFinding(four.slice(0, 3)) : undefined
  rec("T34a 3 identical calls -> no finding (threshold 4)", f3 === null, hasItr ? (f3 ? `kind=${f3.kind}` : "null") : "detector missing (RED)")

  // ---- T34b — a different tool or different args breaks the run ----
  const toolBreak = [mkMcp("a1", OPEN_INPUT), mkMcp("a2", OPEN_INPUT), { tool: "bash", command: "ls", pid: "b1", t: 3 }, mkMcp("a3", OPEN_INPUT), mkMcp("a4", OPEN_INPUT)]
  rec("T34b different tool interleaved -> no finding", hasItr ? identicalToolRunFinding(toolBreak) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  const argsBreak = [mkMcp("a1", OPEN_INPUT), mkMcp("a2", OPEN_INPUT), mkMcp("a3", { profile: "other", name: "p01c", record: true }), mkMcp("a4", OPEN_INPUT), mkMcp("a5", OPEN_INPUT)]
  rec("T34b different args breaks the run -> no finding", hasItr ? identicalToolRunFinding(argsBreak) === null : false, hasItr ? "null expected" : "detector missing (RED)")

  // ---- T34c — pid-dedup: re-observations of one call never inflate the run ----
  const reobs = ["p1", "p1", "p1", "p1"].map((p) => mkMcp(p, OPEN_INPUT))
  rec("T34c same pid re-observed 4x -> no finding (dedup)", hasItr ? identicalToolRunFinding(reobs) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  const twoDistinct = ["p1", "p1", "p2", "p2"].map((p) => mkMcp(p, OPEN_INPUT))
  rec("T34c 2 distinct calls + re-observations -> no finding", hasItr ? identicalToolRunFinding(twoDistinct) === null : false, hasItr ? "null expected" : "detector missing (RED)")

  // ---- T34d — unknown-args (status-only re-obs) neither start nor mask a run ----
  const masked = [mkMcp("p1", OPEN_INPUT), mkMcp("p2", OPEN_INPUT), { tool: "weave-connector_ssh_shell_open", pid: "px", t: 3 }, mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT)]
  rec("T34d unknown-args entry cannot mask the run (skipped, 4 counted)", hasItr ? !!identicalToolRunFinding(masked) : false, hasItr ? "finding expected" : "detector missing (RED)")
  const onlyUnknown = [1, 2, 3, 4].map((i) => ({ tool: "weave-connector_ssh_shell_open", pid: `u${i}`, t: i }))
  rec("T34d unknown-args entries can never start a run", hasItr ? identicalToolRunFinding(onlyUnknown) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  const foreign = [mkMcp("p1", OPEN_INPUT), mkMcp("p2", OPEN_INPUT), { tool: "bash", pid: "b1", t: 3 }, mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT)]
  rec("T34d different tool with unobserved args BREAKS the run (no false finding)", hasItr ? identicalToolRunFinding(foreign) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  const malformed = [mkMcp("p1", OPEN_INPUT), mkMcp("p2", OPEN_INPUT), { pid: "q", t: 3 }, mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT)]
  rec("T34d malformed observation (non-string tool) BREAKS the run conservatively", hasItr ? identicalToolRunFinding(malformed) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  // review A1 probe: a malformed RE-observation of an already-counted pid must
  // break too — pid-dedup may never mask it
  const dupMal = [mkMcp("p1", OPEN_INPUT), { pid: "p2", t: 2 }, mkMcp("p2", OPEN_INPUT), mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT)]
  rec("T34d malformed re-observation (dup pid) can NEVER be masked by dedup", hasItr ? identicalToolRunFinding(dupMal) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  // review A2 probe: a FOREIGN tool with unobserved args at the tail anchors
  // the run's tool — it can never be skipped as "unknown"
  const tailForeign = [mkMcp("p1", OPEN_INPUT), mkMcp("p2", OPEN_INPUT), mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT), { tool: "bash", pid: "pb", t: 5 }]
  rec("T34d foreign tool with unobserved args at the TAIL breaks the run", hasItr ? identicalToolRunFinding(tailForeign) === null : false, hasItr ? "null expected" : "detector missing (RED)")
  const tailSame = [mkMcp("p1", OPEN_INPUT), mkMcp("p2", OPEN_INPUT), mkMcp("p3", OPEN_INPUT), mkMcp("p4", OPEN_INPUT), { tool: "weave-connector_ssh_shell_open", pid: "pu", t: 5 }]
  rec("T34d unknown-args SAME-tool tail still cannot mask the run (R1#4)", hasItr ? !!identicalToolRunFinding(tailSame) : false, hasItr ? "finding expected" : "detector missing (RED)")
  const six = ["p1", "p2", "p3", "p4", "p5", "p6"].map((p) => mkMcp(p, OPEN_INPUT))
  const f6 = hasItr ? identicalToolRunFinding(six) : undefined
  rec("T34d pattern reports the FULL run length (6 calls -> '6 consecutive', not minRun floor)", !!f6 && /^6 consecutive identical/.test(f6.pattern), hasItr && f6 ? f6.pattern.slice(0, 60) : "detector missing (RED)")

  // ---- T34e — truncated args break the run (F10 shape: truncation can forge identity) ----
  const forged = ["p1", "p2", "p3", "p4"].map((p) => mkMcp(p, { profile: "newsrv".repeat(50) }))
  forged.forEach((t) => (t.truncated = true))
  rec("T34e truncated observations break the run", hasItr ? identicalToolRunFinding(forged) === null : false, hasItr ? "null expected" : "detector missing (RED)")

  // ---- T34f — identity is canonical: argument key order never matters ----
  const idA = hasItr && typeof toolIdentity === "function" ? toolIdentity(mkMcp("p1", { a: 1, b: 2 })) : "missing"
  const idB = hasItr && typeof toolIdentity === "function" ? toolIdentity(mkMcp("p2", { b: 2, a: 1 })) : "missing"
  rec("T34f toolIdentity canonicalizes key order (deep key-sort)", idA === idB && idA !== "missing" && idA !== null, `idA=${String(idA).slice(0, 60)} idB=${String(idB).slice(0, 60)}`)
  const mixedOrder = [
    { tool: "weave-connector_ssh_shell_open", args: '{"record":true,"name":"p01c","profile":"newsrv"}', pid: "p1", t: 1 },
    { tool: "weave-connector_ssh_shell_open", args: '{"name":"p01c","profile":"newsrv","record":true}', pid: "p2", t: 2 },
    { tool: "weave-connector_ssh_shell_open", args: '{"profile":"newsrv","record":true,"name":"p01c"}', pid: "p3", t: 3 },
    { tool: "weave-connector_ssh_shell_open", args: '{"record":true,"profile":"newsrv","name":"p01c"}', pid: "p4", t: 4 },
  ]
  rec("T34f mixed key-order args are ONE identity -> finding", hasItr ? !!identicalToolRunFinding(mixedOrder) : false, hasItr ? "finding expected" : "detector missing (RED)")

  // ---- T34g — legacy observation shapes: command/filePath/name fallbacks ----
  const legacyName = [1, 2, 3, 4].map((i) => ({ tool: "skill", name: "vibeweaver", pid: `s${i}`, t: i }))
  rec("T34g legacy {tool,name} fallback x4 -> finding", hasItr ? !!identicalToolRunFinding(legacyName) : false, hasItr ? "finding expected" : "detector missing (RED)")
  const legacyBash = [1, 2, 3, 4].map((i) => ({ tool: "bash", command: "ls", pid: `l${i}`, t: i }))
  const fb = hasItr ? identicalToolRunFinding(legacyBash) : undefined
  rec("T34g bash {command} fallback x4 real command -> finding (noop-bash stays silent)", !!fb && fb.kind === "identical-tool-run" && (typeof isNoopBashCommand !== "function" || !isNoopBashCommand("ls")), hasItr ? (fb ? `kind=${fb.kind}` : "null") : "detector missing (RED)")

  // ---- T34h — minRun parameter respected ----
  const two = ["p1", "p2"].map((p) => mkMcp(p, OPEN_INPUT))
  rec("T34h minRun=2 fires on 2 identical calls", hasItr ? !!identicalToolRunFinding(two, 2) : false, hasItr ? "finding expected" : "detector missing (RED)")
  rec("T34h default threshold constant >= 4 (polling FP bar)", hasItr ? identicalToolRunFinding(two) === null : false, hasItr ? "null expected" : "detector missing (RED)")

  // ---- T34i — adapter: 4 identical MCP tool parts -> one budgeted intervention ----
  {
    const root32 = newFixture("t32-itr")
    write(root32, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin32 = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root32,
    })
    const sid = "ses_t32"
    const emitOpen = (id) =>
      plugin32.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "weave-connector_ssh_shell_open", state: { status: "completed", input: OPEN_INPUT } } },
        },
      })
    for (let i = 1; i <= 4; i++) await emitOpen(`p${i}`)
    rec("T34i 4 identical MCP calls through adapter -> exactly one intervention", calls.abort === 1 && calls.prompts.length === 1, `abort=${calls.abort} prompts=${calls.prompts.length}`)
    const ptext = calls.prompts[0] || ""
    rec("T34i corrective text names the loop kind + demands varied args/diagnosis or progress", /identical-tool-run/.test(ptext) && /(- stall: identical-tool-run)/.test(ptext) && /verification_log/i.test(ptext), ptext.slice(0, 160))
    rec("T34i corrective text carries the legal exits (vary · next step · completion-if-all-pass)", /(chang|var(y|ied)|different) (arguments|args|tool)/i.test(ptext) && /(next (real )?step|proceed)/i.test(ptext) && /completion output/i.test(ptext), ptext.slice(0, 200))
    for (let i = 5; i <= 8; i++) await emitOpen(`p${i}`)
    rec("T34i continued identical calls -> no thrash (still 1 intervention)", calls.abort === 1, `abort=${calls.abort}`)
    // status-only re-observations must not fabricate identity or mask the run
    await plugin32.event({
      event: { type: "message.part.updated", properties: { sessionID: sid, part: { id: "p9", type: "tool", tool: "weave-connector_ssh_shell_open", state: { status: "running" } } } },
    })
    await plugin32.event({
      event: { type: "message.part.updated", properties: { sessionID: sid, part: { id: "p10", type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } } },
    })
    rec("T34i status-only re-obs + real call leave budget/latch state sane", calls.abort === 1 && calls.prompts.length === 1, `abort=${calls.abort}`)
  }

  // ---- T34j — tool-channel budget SHARED across noop-bash and identical-tool-run ----
  {
    const root32b = newFixture("t32-budget")
    write(root32b, "tests/verification_log.md", "placeholder — no iter entries\n")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin32b = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root32b,
    })
    const sid = "ses_t32b"
    const emitOpen = (id) =>
      plugin32b.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "weave-connector_ssh_shell_open", state: { status: "completed", input: OPEN_INPUT } } },
        },
      })
    const emitEcho = (id) =>
      plugin32b.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "bash", state: { status: "completed", input: { command: 'echo "final"' } } } },
        },
      })
    const emitBreak = async (id) =>
      plugin32b.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id, type: "tool", tool: "bash", state: { status: "completed", input: { command: "ls" } } } },
        },
      })
    // episode 1: identical echo x4 -> noop-bash (checked first) consumes budget slot 1
    for (let i = 1; i <= 4; i++) await emitEcho(`e${i}`)
    rec("T34j noop-bash episode consumes shared tool-channel budget slot 1", calls.abort === 1 && /noop-bash/.test(calls.prompts[0] || ""), `abort=${calls.abort}`)
    await emitBreak("b1")
    for (let i = 1; i <= 4; i++) await emitOpen(`a${i}`)
    rec("T34j identical-tool-run episode shares the budget (2nd intervention)", calls.abort === 2 && /identical-tool-run/.test(calls.prompts[1] || ""), `abort=${calls.abort}`)
    await emitBreak("b2")
    for (let i = 1; i <= 4; i++) await emitOpen(`c${i}`)
    const budgetLog = calls.logs.some((m) => /budget exhausted/i.test(m))
    rec("T34j episode 3 beyond shared budget -> log-only, no abort", calls.abort === 2 && budgetLog, `abort=${calls.abort} budgetLog=${budgetLog}`)
  }

  // ---- T34k — VIBEWEAVER_LOOPGUARD=off keeps the new detector silent too ----
  {
    const root32c = newFixture("t32-off")
    write(root32c, "tests/verification_log.md", "placeholder — no iter entries\n")
    const prev = process.env.VIBEWEAVER_LOOPGUARD
    process.env.VIBEWEAVER_LOOPGUARD = "off"
    const calls = { abort: 0, prompts: 0 }
    const plugin32c = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {
            calls.prompts++
          },
        },
      },
      directory: root32c,
    })
    for (let i = 1; i <= 6; i++) {
      await plugin32c.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t32c", part: { id: `x${i}`, type: "tool", tool: "weave-connector_ssh_shell_open", state: { status: "completed", input: OPEN_INPUT } } },
        },
      })
    }
    if (prev === undefined) delete process.env.VIBEWEAVER_LOOPGUARD
    else process.env.VIBEWEAVER_LOOPGUARD = prev
    rec("T34k VIBEWEAVER_LOOPGUARD=off -> identical-tool-run silent", calls.abort === 0 && calls.prompts === 0, `abort=${calls.abort}`)
  }

  // ---- T34l — `__proto__` input key must never forge identity (review B) ----
  {
    const aProto = JSON.parse('{"__proto__":{"i":1},"cmd":"a"}')
    const aPlain = JSON.parse('{"cmd":"a"}')
    rec("T34l canonicalJson keeps __proto__ as an own key (distinct identities)", hasCj ? cj(aProto) !== cj(aPlain) && cj(aProto).includes("__proto__") : false, hasCj ? `proto=${cj(aProto)} plain=${cj(aPlain)}` : "canonicalJson missing (RED)")
    const mixed = [
      { tool: "w", args: cj(aProto), pid: "m1", t: 1 },
      { tool: "w", args: cj(aProto), pid: "m2", t: 2 },
      { tool: "w", args: cj(aPlain), pid: "m3", t: 3 },
      { tool: "w", args: cj(aProto), pid: "m4", t: 4 },
      { tool: "w", args: cj(aProto), pid: "m5", t: 5 },
    ]
    rec("T34l __proto__ vs plain input interleave breaks the run (no false finding)", hasItr ? identicalToolRunFinding(mixed) === null : false, hasItr ? "null expected" : "detector missing (RED)")
    rec("T34l 4 identical __proto__-bearing calls still fire (identity intact)", hasItr ? !!identicalToolRunFinding(mixed.slice(0, 2).concat(mixed.slice(3))) : false, hasItr ? "finding expected" : "detector missing (RED)")
  }

  // ---- T34m — v2 execute.before path: real input records args+pid; missing
  //      input fabricates nothing; truncation breaks; zero-arg calls DO fire ----
  {
    const root34m = newFixture("t34-v2obs")
    write(root34m, "tests/verification_log.md", "placeholder — no iter entries\n")
    const toolHooks = { before: [] }
    const sessCalls = { interrupt: [], prompt: [] }
    const ctx = {
      location: { directory: root34m, workspaceID: undefined, project: { id: "p1", directory: root34m, canonical: root34m } },
      options: {},
      app: { name: "opencode", version: "2.0.16", channel: "stable" },
      session: {
        interrupt: async (i) => sessCalls.interrupt.push(i),
        prompt: async (i) => sessCalls.prompt.push(i),
      },
      tool: {
        hook: async (name, cb) => {
          if (name === "execute.before") toolHooks.before.push(cb)
          return { dispose: async () => {} }
        },
      },
      event: { subscribe: () => ({ dispose: async () => {} }) },
    }
    const cleanup = await auditModule.default.setup(ctx)
    const before = toolHooks.before[0]
    const fire = (sid, id, input) =>
      before({ tool: "weave-connector_ssh_shell_open", sessionID: sid, agent: "a", messageID: "m1", id, input })
    for (let i = 1; i <= 4; i++) await fire("ses_v1", `c${i}`, OPEN_INPUT)
    const ptext = (sessCalls.prompt[0] && JSON.stringify(sessCalls.prompt[0])) || ""
    rec("T34m v2 execute.before path -> identical run fires (args+pid recorded)", sessCalls.interrupt.length === 1 && sessCalls.prompt.length === 1 && /identical-tool-run/.test(ptext), `interrupt=${sessCalls.interrupt.length} prompts=${sessCalls.prompt.length}`)
    for (let i = 1; i <= 4; i++) await before({ tool: "weave-connector_ssh_shell_open", sessionID: "ses_v2", agent: "a", messageID: "m1", id: `n${i}` })
    rec("T34m calls observed WITHOUT input never fabricate identity (no finding)", sessCalls.interrupt.length === 1, `interrupt=${sessCalls.interrupt.length}`)
    await fire("ses_v3", "k1", OPEN_INPUT)
    await fire("ses_v3", "k2", OPEN_INPUT)
    await before({ tool: "bash", sessionID: "ses_v3", agent: "a", messageID: "m1", id: "kb" })
    await fire("ses_v3", "k3", OPEN_INPUT)
    await fire("ses_v3", "k4", OPEN_INPUT)
    rec("T34m different tool with no input breaks the v2 run", sessCalls.interrupt.length === 1, `interrupt=${sessCalls.interrupt.length}`)
    const longInput = { profile: "newsrv", name: "p01c", record: true, blob: "x".repeat(500) }
    for (let i = 1; i <= 4; i++) await fire("ses_v4", `t${i}`, longInput)
    rec("T34m over-cap args marked truncated break the run (F10, no finding)", sessCalls.interrupt.length === 1, `interrupt=${sessCalls.interrupt.length}`)
    for (let i = 1; i <= 4; i++) await fire("ses_v5", `z${i}`, {})
    rec("T34m zero-arg identical calls (input {} observed) DO fire (incident class)", sessCalls.interrupt.length === 2, `interrupt=${sessCalls.interrupt.length}`)
    if (typeof cleanup === "function") await cleanup()
  }
}

// =====================================================================
// T35 — loop-guard tool-frequency (single-tool storm, deer-flow Layer 2,
// 2026-10-14 residuals wave). Same-tool calls with VARYING args (read
// ×N different files) evade identical-tool-run; a trailing run of
// same-tool DISTINCT-pid observations >= TOOL_FREQ_MIN -> one corrective
// intervention. Values-free pattern by construction (tool name + count).
// =====================================================================
{
  const hasTf = typeof toolFrequencyFinding === "function"
  const OPEN_INPUT = { profile: "newsrv", name: "p01c", record: true }
  const mkRead = (pid, i) => ({ tool: "read", filePath: `/tmp/f${i}.txt`, pid, t: i })
  const storm = Array.from({ length: 20 }, (_, i) => mkRead(`r${i}`, i))
  const tf20 = hasTf ? toolFrequencyFinding(storm) : undefined
  rec("T35a 20 same-tool varied-args calls (distinct pids) -> tool-frequency finding", !!tf20 && tf20.kind === "tool-frequency", hasTf ? (tf20 ? `kind=${tf20.kind} pattern=${tf20.pattern.slice(0, 80)}` : "null") : "detector missing (RED)")
  rec("T35a pattern values-free (tool + count only)", !!tf20 && /^20 consecutive read calls/.test(tf20.pattern) && !/f0\.txt/.test(tf20.pattern), hasTf && tf20 ? tf20.pattern.slice(0, 100) : "detector missing (RED)")
  rec("T35a 19 same-tool calls -> no finding (threshold 20)", hasTf ? toolFrequencyFinding(storm.slice(0, 19)) === null : false, hasTf ? "null expected" : "detector missing (RED)")

  const toolBreak = [...Array.from({ length: 11 }, (_, i) => mkRead(`a${i}`, i)), { tool: "bash", command: "ls", pid: "b", t: 12 }, ...Array.from({ length: 11 }, (_, i) => mkRead(`c${i}`, i + 20))]
  rec("T35b foreign tool interleaved (22 reads) -> no finding (skip-mutant would fire)", hasTf ? toolFrequencyFinding(toolBreak) === null : false, hasTf ? "null expected" : "detector missing (RED)")
  const reobs = Array.from({ length: 20 }, (_, i) => mkRead("same", i))
  rec("T35b same-pid re-observations never inflate the storm", hasTf ? toolFrequencyFinding(reobs) === null : false, hasTf ? "null expected" : "detector missing (RED)")
  rec("T35c minRun parameter respected (4 varied reads)", hasTf ? !!toolFrequencyFinding(storm.slice(0, 4), 4) : false, hasTf ? "finding expected" : "detector missing (RED)")

  // ---- T35d — adapter: tool-frequency is OPT-IN (W10); default off ----
  {
    const root35 = newFixture("t35-freq-off")
    write(root35, "tests/verification_log.md", "placeholder — no iter entries\n")
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    const calls = { abort: 0, prompts: 0, logs: [] }
    const plugin35 = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: { abort: async () => { calls.abort++ }, prompt: async () => { calls.prompts++ } },
      },
      directory: root35,
    })
    for (let i = 0; i < 25; i++) {
      await plugin35.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t35", part: { id: `r${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/f${i}.txt` } } } },
        },
      })
    }
    rec("T35d 25 varied reads with no config -> NO intervention (opt-in default off)", calls.abort === 0 && calls.prompts === 0, `abort=${calls.abort} prompts=${calls.prompts}`)
  }
  // ---- T35d3 — W12: default high-threshold WARN-ONLY layer ----
  {
    const root35w = newFixture("t35-freq-warn")
    write(root35w, "tests/verification_log.md", "placeholder — no iter entries\n")
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    const calls = { abort: 0, prompts: 0, logs: [] }
    const plugin35w = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: { abort: async () => { calls.abort++ }, prompt: async () => { calls.prompts++ } },
      },
      directory: root35w,
    })
    for (let i = 0; i < 130; i++) {
      await plugin35w.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t35w", part: { id: `w${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/w${i}.txt` } } } },
        },
      })
    }
    rec("T35d3 130 varied reads default -> warn-only (no abort, no prompt)",
      calls.abort === 0 && calls.prompts === 0 && calls.logs.filter((m) => /tool-frequency warning \(warn-only/i.test(m)).length === 1,
      `abort=${calls.abort} prompts=${calls.prompts} warnings=${calls.logs.filter((m) => /tool-frequency warning/i.test(m)).length}`)
    await plugin35w.event({ event: { type: "message.updated", properties: { sessionID: "ses_t35w", info: { id: "u35w", role: "user" } } } })
    await plugin35w.event({
      event: {
        type: "message.part.updated",
        properties: { sessionID: "ses_t35w", part: { id: "w130", type: "tool", tool: "read", state: { status: "completed", input: { filePath: "/tmp/w130.txt" } } } },
      },
    })
    rec("T35d4 warning is once per SESSION, not once per user turn",
      calls.logs.filter((m) => /tool-frequency warning \(warn-only/i.test(m)).length === 1,
      `warnings=${calls.logs.filter((m) => /tool-frequency warning/i.test(m)).length}`)
  }
  // ---- T35d2 — adapter: explicit opt-in restores the storm intervention ----
  {
    const root35 = newFixture("t35-freq-on")
    write(root35, "tests/verification_log.md", "placeholder — no iter entries\n")
    write(root35, "audit-config.json", JSON.stringify({ loopGuardToolFrequencyMin: 20 }))
    process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root35, "audit-config.json")
    const calls = { abort: 0, prompts: [], logs: [] }
    const plugin35 = await VibeweaverAudit({
      client: {
        app: { log: async (e) => calls.logs.push((e && e.body && e.body.message) || "") },
        session: {
          abort: async () => { calls.abort++ },
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root35,
    })
    const sid = "ses_t35"
    for (let i = 0; i < 45; i++) {
      await plugin35.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `r${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/f${i}.txt` } } } },
        },
      })
    }
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    rec("T35d2 opt-in loopGuardToolFrequencyMin=20 -> 45-call incident shape gets one intervention", calls.abort === 1 && calls.prompts.length === 1, `abort=${calls.abort} prompts=${calls.prompts.length}`)
    const ptext = calls.prompts[0] || ""
    rec("T35d2 corrective text: stall declaration + consolidate/switch/next/completion exits", /tool-frequency/.test(ptext) && /- stall: tool-frequency/.test(ptext) && /(consolidat|batch|summar)/i.test(ptext) && /(switch|different tool|different approach)/i.test(ptext) && /completion output/i.test(ptext), ptext.slice(0, 200))
    for (let i = 20; i < 26; i++) {
      await plugin35.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `r${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/f${i}.txt` } } } },
        },
      })
    }
    rec("T35d2 continued storm -> no thrash (still 1 intervention)", calls.abort === 1, `abort=${calls.abort}`)
  }

  // ---- T35e — precedence: noop-bash and identical-tool-run win over frequency ----
  {
    const root35b = newFixture("t35-prec")
    write(root35b, "tests/verification_log.md", "placeholder — no iter entries\n")
    write(root35b, "audit-config.json", JSON.stringify({ loopGuardToolFrequencyMin: 20 }))
    process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root35b, "audit-config.json")
    const calls = { prompts: [] }
    const plugin35b = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {},
          prompt: async (args) => {
            const parts = args && args.body && args.body.parts
            calls.prompts.push((parts && parts[0] && parts[0].text) || "")
          },
        },
      },
      directory: root35b,
    })
    const sid = "ses_t35e"
    for (let i = 0; i < 20; i++) {
      await plugin35b.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: sid, part: { id: `x${i}`, type: "tool", tool: "weave-connector_ssh_shell_open", state: { status: "completed", input: OPEN_INPUT } } },
        },
      })
    }
    rec("T35e identical run of 20 -> identical-tool-run wins (not tool-frequency)", calls.prompts.length === 1 && /identical-tool-run/.test(calls.prompts[0] || "") && !/tool-frequency/.test(calls.prompts[0] || ""), (calls.prompts[0] || "").slice(0, 80))
    // noop-bash over frequency (review B minor: title claim now fully pinned)
    for (let i = 0; i < 20; i++) {
      await plugin35b.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t35e2", part: { id: `e${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: `echo "varied ${i}"` } } } },
        },
      })
    }
    rec("T35e varied echo no-op storm -> noop-bash wins (not tool-frequency)", calls.prompts.length === 2 && /noop-bash/.test(calls.prompts[1] || "") && !/tool-frequency/.test(calls.prompts[1] || ""), (calls.prompts[1] || "").slice(0, 80))
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
  }

  // ---- T35f — config override loopGuardToolFrequencyMin (integer >= 4) ----
  {
    const root35c = newFixture("t35-cfg")
    write(root35c, "tests/verification_log.md", "placeholder — no iter entries\n")
    write(root35c, "audit-config.json", JSON.stringify({ loopGuardToolFrequencyMin: 4 }))
    process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root35c, "audit-config.json")
    const calls = { abort: 0 }
    const plugin35c = await VibeweaverAudit({
      client: {
        app: { log: async () => {} },
        session: {
          abort: async () => {
            calls.abort++
          },
          prompt: async () => {},
        },
      },
      directory: root35c,
    })
    for (let i = 0; i < 4; i++) {
      await plugin35c.event({
        event: {
          type: "message.part.updated",
          properties: { sessionID: "ses_t35f", part: { id: `c${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/g${i}.txt` } } } },
        },
      })
    }
    delete process.env.VIBEWEAVER_AUDIT_CONFIG
    rec("T35f loopGuardToolFrequencyMin=4 -> storm fires at 4 varied reads", calls.abort === 1, `abort=${calls.abort}`)
  }
}

// =====================================================================
// T36 — D2 self-lock (PLAN §2 D2, BLINDSPOTS BL-9): corrective prompts
// carry NO completion-marker literals; completion analysis is
// assistant-only + plugin-injected-message-excluded.
// =====================================================================
{
  const markerFree = (s) => !/\[Verification Gate\]/.test(s) && !/\|\s*#\s*\|\s*Problem\s*\|/.test(s) && !/HARD-GATE-[12]/.test(s)
  const root36 = newFixture("t36-selflock")
  write(root36, "tests/verification_log.md", "placeholder — no iter entries\n")
  write(root36, "audit-config.json", JSON.stringify({ loopGuardToolFrequencyMin: 20 }))
  process.env.VIBEWEAVER_AUDIT_CONFIG = path.join(root36, "audit-config.json")
  const calls = { abort: 0, prompts: [] }
  const plugin36 = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: {
        abort: async () => {
          calls.abort++
        },
        prompt: async (args) => {
          const parts = args && args.body && args.body.parts
          calls.prompts.push((parts && parts[0] && parts[0].text) || "")
        },
      },
    },
    directory: root36,
  })
  const emitPart = (sid, part) => plugin36.event({ event: { type: "message.part.updated", properties: { sessionID: sid, part } } })
  // branch 1: noop-bash
  for (let i = 0; i < 4; i++) await emitPart("ses_t36a", { id: `n${i}`, type: "tool", tool: "bash", state: { status: "completed", input: { command: `echo "n${i}"` } } })
  // branch 2: identical-tool-run
  for (let i = 0; i < 4; i++) await emitPart("ses_t36b", { id: `i${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: "/tmp/same.txt" } } })
  // branch 3: tool-frequency
  for (let i = 0; i < 20; i++) await emitPart("ses_t36c", { id: `f${i}`, type: "tool", tool: "read", state: { status: "completed", input: { filePath: `/tmp/f${i}.txt` } } })
  // branch 4 (default): sequence wall
  await emitPart("ses_t36d", { id: "sq", type: "text", text: Array.from({ length: 14 }, (_, i) => String(100 + i)).join("\n") + "\n" })
  const kinds = ["noop-bash", "identical-tool-run", "tool-frequency", "default/sequence"]
  rec("T36a corrective prompts captured for 4 finding kinds", calls.prompts.length === 4, `prompts=${calls.prompts.length} abort=${calls.abort}`)
  calls.prompts.forEach((p, i) => {
    rec(`T36b ${kinds[i]} prompt carries NO completion-marker literal`, markerFree(p), p.slice(0, 120))
    rec(`T36b ${kinds[i]} prompt still demands the completion output`, /completion output|final completion/i.test(p), p.slice(0, 120))
  })
  // branch 5: runaway (turn ceiling) — >256KB of non-periodic assistant text
  {
    const WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
    const blob = Array.from({ length: 22000 }, (_, i) => `${WORDS[i % 8]}-${i} payload`).join("\n")
    await emitPart("ses_t36e", { id: "run", type: "text", text: blob })
    const p = calls.prompts[calls.prompts.length - 1] || ""
    rec("T36c runaway prompt captured and marker-free", calls.prompts.length === 5 && markerFree(p), `prompts=${calls.prompts.length} head=${p.slice(0, 80)}`)
    rec("T36c runaway prompt still demands the completion output", /completion output|final completion/i.test(p), p.slice(0, 120))
  }

  // ---- T36d/e: fed-back marker text must NOT enter completion analysis ----
  const gateText = [
    "Verifier: mm-sensor [image]",
    "[Verification Gate] Verifier: mm-sensor [image] | Loop executed: yes | Iterations: 1 | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass",
  ].join("\n")
  {
    const root36f = newFixture("t36-fb-user")
    write(root36f, "tests/verification_log.md", "placeholder — no iter entries\n")
    const plugin36f = await VibeweaverAudit({ client: { app: { log: async () => {} }, session: { abort: async () => {}, prompt: async () => {} } }, directory: root36f })
    const emit = (type, props) => plugin36f.event({ event: { type, properties: props } })
    await emit("message.part.updated", { sessionID: "ses_t36f", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await emit("message.updated", { sessionID: "ses_t36f", info: { id: "m_u", role: "user" } })
    await emit("message.part.updated", { sessionID: "ses_t36f", part: { id: "p_u", type: "text", messageID: "m_u", text: gateText } })
    await emit("session.idle", { sessionID: "ses_t36f" })
    const st = JSON.parse(readFileSync(path.join(root36f, ".vibeweaver", "audit-state.json"), "utf8")).roots[root36f] || {}
    rec("T36d user-fed gate-line text does NOT trigger the completion audit (no latch)", st.red == null, `red=${JSON.stringify(st.red)}`)
  }
  {
    const root36g = newFixture("t36-fb-inj")
    write(root36g, "tests/verification_log.md", "placeholder — no iter entries\n")
    const plugin36g = await VibeweaverAudit({ client: { app: { log: async () => {} }, session: { abort: async () => {}, prompt: async () => {} } }, directory: root36g })
    const emit = (type, props) => plugin36g.event({ event: { type, properties: props } })
    await emit("message.part.updated", { sessionID: "ses_t36g", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await emit("message.part.updated", { sessionID: "ses_t36g", part: { id: "p_i", type: "text", text: "[loop-guard] " + gateText } })
    await emit("session.idle", { sessionID: "ses_t36g" })
    const st = JSON.parse(readFileSync(path.join(root36g, ".vibeweaver", "audit-state.json"), "utf8")).roots[root36g] || {}
    rec("T36e plugin-injected [loop-guard] marker text does NOT trigger the completion audit", st.red == null, `red=${JSON.stringify(st.red)}`)
  }
  {
    const root36h = newFixture("t36-fb-ctrl")
    write(root36h, "tests/verification_log.md", "placeholder — no iter entries\n")
    const plugin36h = await VibeweaverAudit({ client: { app: { log: async () => {} }, session: { abort: async () => {}, prompt: async () => {} } }, directory: root36h })
    const emit = (type, props) => plugin36h.event({ event: { type, properties: props } })
    await emit("message.part.updated", { sessionID: "ses_t36h", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
    await emit("message.part.updated", { sessionID: "ses_t36h", part: { id: "p_a", type: "text", text: gateText } })
    await emit("session.idle", { sessionID: "ses_t36h" })
    const st = JSON.parse(readFileSync(path.join(root36h, ".vibeweaver", "audit-state.json"), "utf8")).roots[root36h] || {}
    rec("T36f genuine assistant gate-line STILL triggers the completion audit (control)", !!st.red, `red=${JSON.stringify(st.red)}`)
  }
  delete process.env.VIBEWEAVER_AUDIT_CONFIG
}

// =====================================================================
// T37 — D3 lock bypass (PLAN §2 D3, BLINDSPOTS BL-5/6/7): path
// normalization before the tests/-prefix check + write-target realpath.
// =====================================================================
{
  const root37 = newFixture("t37-traversal")
  write(root37, "tests/verification_log.md", "placeholder — no iter entries\n")
  mkdirSync(path.join(root37, "src"), { recursive: true })
  const plugin37 = await VibeweaverAudit({ client: { app: { log: async () => {} } }, directory: root37 })
  await latchRed(plugin37, "ses_t37", root37)
  const esc = await tryWrite(plugin37, root37, "RAW:tests/../src/a.js", "ses_t37")
  const escBlocked = typeof esc === "string" && /GATE-BLOCKED/.test(esc)
  rec("T37a tests/../src/a.js escape write is BLOCKED under RED (PoC)", escBlocked, escBlocked ? "traversal blocked" : "ESCAPED: " + esc)
  const newEv = await tryWrite(plugin37, root37, "tests/evidence_new/shot.png", "ses_t37")
  rec("T37b new-file write under tests/ stays allowed (evidence path, PoC-safe)", newEv === true, newEv === true ? "evidence path open" : "deadlocked: " + newEv)
  try {
    rmSync(path.join(root37, "src", "linktarget"), { force: true })
    mkdirSync(path.join(root37, "src", "linktarget"), { recursive: true })
    rmSync(path.join(root37, "tests", "lnk"), { force: true })
    execFileSync("ln", ["-s", path.join(root37, "src", "linktarget"), path.join(root37, "tests", "lnk")])
    const sym = await tryWrite(plugin37, root37, "tests/lnk/evil.js", "ses_t37")
    const symBlocked = typeof sym === "string" && /GATE-BLOCKED/.test(sym)
    rec("T37c symlinked tests/ dir pointing at src/ is NOT an evidence path", symBlocked, symBlocked ? "symlink escape blocked" : "ESCAPED via symlink: " + sym)
  } catch (e) {
    rec("T37c symlinked tests/ dir pointing at src/ is NOT an evidence path", false, "fixture error: " + e.message)
  }
  // Review A2/B2: a symlinked FILE (tests/app.js -> ../src/app.js) used to
  // keep the tests/ segment and escape — the whole path must be realpath'd.
  try {
    writeFileSync(path.join(root37, "src", "app.js"), "export const x = 1\n")
    rmSync(path.join(root37, "tests", "app.js"), { force: true })
    execFileSync("ln", ["-s", path.join(root37, "src", "app.js"), path.join(root37, "tests", "app.js")])
    const fsym = await tryWrite(plugin37, root37, "tests/app.js", "ses_t37")
    const fsymBlocked = typeof fsym === "string" && /GATE-BLOCKED/.test(fsym)
    rec("T37d symlinked FILE tests/app.js -> src/app.js is NOT an evidence path", fsymBlocked, fsymBlocked ? "file-symlink escape blocked" : "ESCAPED via file symlink: " + fsym)
  } catch (e) {
    rec("T37d symlinked FILE tests/app.js -> src/app.js is NOT an evidence path", false, "fixture error: " + e.message)
  }
  // re-review R2#1: a DANGLING file symlink (target not yet created) must
  // also resolve outside the evidence exemption — the OS write follows it.
  try {
    rmSync(path.join(root37, "tests", "dangle.js"), { force: true })
    execFileSync("ln", ["-s", path.join(root37, "src", "notyet.js"), path.join(root37, "tests", "dangle.js")])
    const dsym = await tryWrite(plugin37, root37, "tests/dangle.js", "ses_t37")
    const dsymBlocked = typeof dsym === "string" && /GATE-BLOCKED/.test(dsym)
    rec("T37e dangling symlink tests/dangle.js -> src/notyet.js is NOT an evidence path", dsymBlocked, dsymBlocked ? "dangling-symlink escape blocked" : "ESCAPED via dangling symlink: " + dsym)
  } catch (e) {
    rec("T37e dangling symlink tests/dangle.js -> src/notyet.js is NOT an evidence path", false, "fixture error: " + e.message)
  }
}

// =====================================================================
// T38 — D1 loop-guard scope + corpus gate (PLAN §2 D1, BLINDSPOTS BL-8):
// project gate (acceptance.md or skill activated), assistant-only corpus
// (user messages / code fences excluded), tool result-summary identity.
// =====================================================================
{
  // T38a — ordinary directory: zero behavior, zero writes.
  // The fixture lives under the OS tmpdir with a CLEAN ancestor chain: findProjectRoot
  // walks upwards, and a stray tests/verification_log.md in a shared /tmp parent
  // (left by other harnesses) would make every child look vibeweaver-active.
  const root38 = path.join(os.tmpdir(), "t38-ordinary-" + process.pid)
  rmSync(root38, { recursive: true, force: true })
  mkdirSync(path.join(root38, "src"), { recursive: true })
  const calls38 = { abort: 0, prompts: 0 }
  const plugin38 = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: { abort: async () => { calls38.abort++ }, prompt: async () => { calls38.prompts++ } },
    },
    directory: root38,
  })
  await plugin38.event({ event: { type: "message.part.updated", properties: { sessionID: "ses_t38", part: { id: "t0", type: "text", text: "degenerate line text here\n".repeat(4) } } } })
  await plugin38.event({ event: { type: "session.idle", properties: { sessionID: "ses_t38" } } })
  rec("T38a ordinary dir (no acceptance.md, no skill) -> loop-guard silent", calls38.abort === 0 && calls38.prompts === 0, `abort=${calls38.abort} prompts=${calls38.prompts}`)
  rec("T38a ordinary dir -> no .vibeweaver/ state written (zero behavior)", !existsSync(path.join(root38, ".vibeweaver")), existsSync(path.join(root38, ".vibeweaver")) ? "state dir created" : "no writes")

  // T38b — same degeneration with the vibeweaver skill activated: fires
  const root38b = newFixture("t38-skillgate")
  rmSync(path.join(root38b, "tests", "acceptance.md"), { force: true }) // skill-only gate: no acceptance.md yet
  write(root38b, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls38b = { abort: 0 }
  const plugin38b = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: { abort: async () => { calls38b.abort++ }, prompt: async () => {} },
    },
    directory: root38b,
  })
  await plugin38b.event({ event: { type: "message.part.updated", properties: { sessionID: "ses_t38b", part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } } } })
  await plugin38b.event({ event: { type: "message.part.updated", properties: { sessionID: "ses_t38b", part: { id: "t0", type: "text", text: "degenerate line text here\n".repeat(4) } } } })
  rec("T38b skill-activated session (no acceptance.md yet) -> guard fires", calls38b.abort === 1, `abort=${calls38b.abort}`)

  // T38c-f — corpus gate on the text channel
  const root38c = newFixture("t38-corpus")
  write(root38c, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls38c = { abort: 0, prompts: [] }
  const plugin38c = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: { abort: async () => { calls38c.abort++ }, prompt: async (a) => { const p = a && a.body && a.body.parts; calls38c.prompts.push((p && p[0] && p[0].text) || "") } },
    },
    directory: root38c,
  })
  const emit38 = (type, props) => plugin38c.event({ event: { type, properties: props } })
  const sid38 = "ses_t38c"
  await emit38("message.part.updated", { sessionID: sid38, part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit38("message.updated", { sessionID: sid38, info: { id: "m_u1", role: "user" } })
  await emit38("message.part.updated", { sessionID: sid38, part: { id: "p_u1", type: "text", messageID: "m_u1", text: "quoted block from the user\n".repeat(6) } })
  rec("T38c user-role message with repeated lines -> NO finding (user corpus excluded)", calls38c.abort === 0, `abort=${calls38c.abort}`)
  await emit38("message.part.updated", { sessionID: sid38, part: { id: "p_c1", type: "text", text: "here is the generated code:\n```\nrepeated code line here\nrepeated code line here\nrepeated code line here\nrepeated code line here\n```\ndone\n" } })
  rec("T38d assistant code fence with repeated lines -> NO finding (fences stripped)", calls38c.abort === 0, `abort=${calls38c.abort}`)
  await emit38("message.part.updated", { sessionID: sid38, part: { id: "p_a1", type: "text", text: "degenerate line text here\n".repeat(4) } })
  rec("T38e assistant plain repeated lines -> finding fires (control)", calls38c.abort === 1, `abort=${calls38c.abort}`)

  // T38f/g — tool channel result-summary identity
  const root38d = newFixture("t38-toolres")
  write(root38d, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls38d = { abort: 0 }
  const plugin38d = await VibeweaverAudit({
    client: { app: { log: async () => {} }, session: { abort: async () => { calls38d.abort++ }, prompt: async () => {} } },
    directory: root38d,
  })
  const emitTool = (sid, id, output) =>
    plugin38d.event({ event: { type: "message.part.updated", properties: { sessionID: sid, part: { id, type: "tool", tool: "bash", state: { status: "completed", input: { command: "git status" }, output } } } } })
  for (let i = 0; i < 4; i++) await emitTool("ses_t38f", `g${i}`, `working tree state line ${i} DIFFERS`)
  rec("T38f identical args but DIFFERENT results -> NO finding (polling is progress)", calls38d.abort === 0, `abort=${calls38d.abort}`)
  for (let i = 0; i < 4; i++) await emitTool("ses_t38g", `h${i}`, "working tree clean\n")
  rec("T38g identical args and identical results -> finding fires (true loop)", calls38d.abort === 1, `abort=${calls38d.abort}`)

  // T38h — divergent KNOWN results must not bridge across unknowns (review A6)
  for (let i = 0; i < 4; i++) await emitTool("ses_t38h", `b${i}`, i === 1 || i === 3 ? undefined : i < 2 ? "state A" : "state B")
  rec("T38h known-A, unknown, known-B, unknown -> NO finding (no bridge across unknowns)", calls38d.abort === 1, `abort=${calls38d.abort}`)

  // T38i — genuine user input decays the intervention budget (D1-④)
  const root38e = newFixture("t38-decay")
  write(root38e, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls38e = { abort: 0, logs: [] }
  const plugin38e = await VibeweaverAudit({
    client: {
      app: { log: async (e) => calls38e.logs.push((e && e.body && e.body.message) || "") },
      session: { abort: async () => { calls38e.abort++ }, prompt: async () => {} },
    },
    directory: root38e,
  })
  const emit38e = (type, props) => plugin38e.event({ event: { type, properties: props } })
  const sid38e = "ses_t38i"
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "k1", type: "tool", tool: "skill", state: { status: "completed", input: { name: "vibeweaver" } } } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "d0", type: "text", text: "degenerate line text here\n".repeat(4) } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "ok0", type: "text", text: "moving on\n" } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "d1", type: "text", text: "degenerate line text here\n".repeat(4) } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "ok1", type: "text", text: "moving on again\n" } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "d2", type: "text", text: "degenerate line text here\n".repeat(4) } })
  const budgetLog = calls38e.logs.some((m) => /budget exhausted/i.test(m))
  rec("T38i budget 2 spent -> 3rd episode log-only", calls38e.abort === 2 && budgetLog, `abort=${calls38e.abort} log=${budgetLog}`)
  await emit38e("message.updated", { sessionID: sid38e, info: { id: "m_u", role: "user" } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "p_u", type: "text", messageID: "m_u", text: "human interjection — try a different angle\n" } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "ok2", type: "text", text: "understood\n" } })
  await emit38e("message.part.updated", { sessionID: sid38e, part: { id: "d3", type: "text", text: "degenerate line text here\n".repeat(4) } })
  rec("T38i genuine user input decays the budget (next episode fires again)", calls38e.abort === 3, `abort=${calls38e.abort}`)
}

// =====================================================================
// T39 — source hygiene (PLAN §2 D5): plugin/core sources contain no
// control characters (NUL/0x01 sentinels make rg treat files as binary);
// companions stay within the one-Read 45KB budget (BL-17).
// =====================================================================
{
  for (const f of ["vibeweaver-audit.js", "vibeweaver-gate.js", "scripts/vibeweaver-audit-core.js"]) {
    const src = readFileSync(path.resolve(import.meta.dirname, "..", f), "utf8")
    const bad = /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(src)
    rec(`T39 ${f} contains no control characters (rg-searchable)`, !bad, bad ? "control byte present" : "clean")
  }
  const root39 = path.resolve(import.meta.dirname, "..")
  const companions = ["COMPLETION_GATE.md", "TESTING_PROTOCOLS.md", "VERIFICATION_UPGRADES.md", "APPENDIX.md", "REFERENCE.md", "WORKFLOWS_EXTENDED.md", "MEMORY_RULES.md", "MEMORY_TEMPLATES.md", "ENGINEERING_STD.md", "CODING_PRINCIPLES.md"]
  for (const f of companions) {
    const n = readFileSync(path.join(root39, f)).length
    rec(`T39 ${f} within the 45000B companion budget`, n <= 45000, `${n}B`)
  }
  const skillBytes = readFileSync(path.join(root39, "SKILL.md")).length
  rec("T39 SKILL.md within the 49000B budget (T11 parity)", skillBytes < 49000, `${skillBytes}B`)
  // E2 single source (BL-17): the complete gate-line TEMPLATE lives in
  // SKILL.md §A4.4 exactly once across the payload — a second copy rots
  // silently (the COMPLETION_GATE one lost Lane/Class/Fresh-verify) and an
  // agent copying it emits a gate line the audit rejects.
  const payloadMds = ["SKILL.md", "COMPLETION_GATE.md", "TESTING_PROTOCOLS.md", "VERIFICATION_UPGRADES.md", "REFERENCE.md", "APPENDIX.md", "WORKFLOWS_EXTENDED.md", "MEMORY_RULES.md", "MEMORY_TEMPLATES.md", "ENGINEERING_STD.md", "CODING_PRINCIPLES.md"]
  const templateHead = /\[Verification Gate\] Verifier: mm-sensor/g
  let templateCopies = 0
  const copyWhere = []
  for (const f of payloadMds) {
    const n = (readFileSync(path.join(root39, f), "utf8").match(templateHead) || []).length
    if (n) copyWhere.push(`${f}×${n}`)
    templateCopies += n
  }
  rec("T39 gate-line template exists exactly once (SKILL.md §A4.4 single source)", templateCopies === 1 && copyWhere.length === 1 && copyWhere[0].startsWith("SKILL.md"), `copies=${templateCopies} at ${copyWhere.join(",") || "none"}`)
  // E2 numbering uniqueness: §A7 = memory ONLY (MEMORY_RULES A7.x), §A8 =
  // communication (ENGINEERING_STD), the plan template hangs under C3 (no
  // §A7 number) — the old three-way collision must not return.
  const headingOf = (f) => readFileSync(path.join(root39, f), "utf8").split("\n").filter((l) => /^#{2,3} /.test(l)).join("\n")
  const engHead = headingOf("ENGINEERING_STD.md")
  const appHead = headingOf("APPENDIX.md")
  const skillHead = headingOf("SKILL.md")
  const memHead = headingOf("MEMORY_RULES.md")
  rec("T39 §A7 is uniquely the memory family (no §A7 heading in ENG/APPENDIX/SKILL)",
    /A7\.1 /.test(memHead) && !/§A7/.test(engHead) && !/§A7/.test(appHead) && !/A7\. Project Memory/.test(skillHead.replace("### A7. Project Memory (memory/memdir)", "")) && /### A7\. Project Memory/.test(skillHead),
    `eng=${/§A7/.test(engHead)} appendix=${/§A7/.test(appHead)} skillA7=${/### A7\. Project Memory/.test(skillHead)}`)
  const oldShadows = ["§A1.", "§A5.", "§A6.", "§A8.", "§A9.", "§A10.", "§A11.", "§A12."]
  const shadowLeft = oldShadows.filter((h) => appHead.includes(h))
  rec("T39 §A8 is uniquely communication; APPENDIX old shadow headings are gone",
    /§A8\. Communication/.test(engHead) && shadowLeft.length === 0,
    `eng=${/§A8\. Communication/.test(engHead)} shadows=${shadowLeft.join(",") || "none"}`)
  rec("T39 plan template hangs under C3 (no bare §A7 template heading)",
    /C3 Plan Template/.test(appHead) && !/§A7\. Large-Task/.test(appHead),
    appHead.split("\n").filter((l) => /C3|§A7/.test(l)).join(" | "))
}

// ---------- T40/T41 — effectiveness guards for the SIGTRAP hardening ----------
{
  // T40: oversized tool inputs keep a deterministic sampled identity — an
  // identical big-args storm must still trip identical-tool-run (F10
  // refinement: a truncated identity breaks runs, a fingerprint does not).
  const root40 = newFixture("t40-bigargs")
  write(root40, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls = { abort: 0 }
  const plugin40 = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: { abort: async () => { calls.abort++ }, prompt: async () => {} },
    },
    directory: root40,
  })
  const emitBig = (sid, id, content) =>
    plugin40.event({
      event: {
        type: "message.part.updated",
        properties: { sessionID: sid, part: { id, type: "tool", tool: "write", state: { status: "running", input: { filePath: "/x/big.txt", content } } } },
      },
    })
  const big = "x".repeat(20000)
  for (let i = 0; i < 4; i++) await emitBig("ses_t40a", `b${i}`, big)
  rec("T40 identical oversized-args storm -> identical-tool-run fires", calls.abort === 1, `abort=${calls.abort}`)
  for (let i = 0; i < 4; i++) await emitBig("ses_t40b", `c${i}`, big + i) // differ only in tail
  rec("T40 differing oversized args -> no identical-run at 4", calls.abort === 1, `abort=${calls.abort}`)
}
{
  // T41: the session-head anchor survives corpus bounding — a gate line in
  // the FIRST part must still be visible to the audit after 600 filler parts
  // (the count-based 64-part cut evicted it: false BAD B1 -> false RED).
  const root41 = newFixture("t41-anchor")
  write(root41, "tests/verification_log.md", "placeholder — no iter entries\n")
  const logs = []
  const plugin41 = await VibeweaverAudit({
    client: { app: { log: async (e) => logs.push((e && e.body && e.body.message) || "") }, session: {} },
    directory: root41,
  })
  await plugin41.event({
    event: {
      type: "message.part.updated",
      properties: { sessionID: "ses_t41", part: { id: "head", type: "text", text: "anchor [Verification Gate] Verifier: direct read | Class: CODE | Loop executed: yes", messageID: "m0" } },
    },
  })
  for (let i = 0; i < 600; i++) {
    await plugin41.event({
      event: {
        type: "message.part.updated",
        properties: { sessionID: "ses_t41", part: { id: `f${i}`, type: "text", text: `filler ${i} ` + "y".repeat(4000), messageID: `m${i + 1}` } },
      },
    })
  }
  await plugin41.event({ event: { type: "session.idle", properties: { sessionID: "ses_t41" } } })
  const auditLine = logs.find((m) => /Audit (RED|GREEN|ESCALATE)/.test(m)) || ""
  rec("T41 head-anchor gate line survives corpus bounding", /Audit (GREEN|ESCALATE)/.test(auditLine) || !/B1/.test(logs.join(" ")), auditLine || "no audit line (B1 not BAD)")
}

{
  // T42: delta chunks must never be eaten by the duplicate heuristic — a
  // stream of small UNIQUE chunks accumulates fully, and the runaway ceiling
  // fires at the 256KB visible-text bound (2026-10-17: the old
  // `buf.includes(chunk)` dropped ordinary deltas, starved turnChars and
  // left the ceiling dark while runaway turns kept streaming).
  const root42 = newFixture("t42-deltas")
  write(root42, "tests/verification_log.md", "placeholder — no iter entries\n")
  const calls = { abort: 0 }
  const plugin42 = await VibeweaverAudit({
    client: {
      app: { log: async () => {} },
      session: { abort: async () => { calls.abort++ }, prompt: async () => {} },
    },
    directory: root42,
  })
  for (let i = 0; i < 15000; i++) {
    const chunk = "delta-" + String(i).padStart(8, "0") + " payload "
    await plugin42.event({
      event: {
        type: "message.part.updated",
        properties: { sessionID: "ses_t42", part: { id: "d1", type: "text", text: chunk, messageID: "m1" } },
      },
    })
  }
  rec("T42 delta stream accumulates (no substring-eating) and runaway ceiling fires", calls.abort >= 1, `abort=${calls.abort} (expect >=1 above 256KB of unique chunks)`)
}

{
  // T43 — class bound (A4.8 RED first): NO string constructor in the plugin
  // stack may receive a ≥2GB input. Bun #26323 / PR #37216: `readFileSync(p,
  // "utf-8")` on a >2GB file is an UNCATCATCHABLE SIGTRAP in the runtime
  // opencode bundles (create_external* lets 2^31..2^32-1 lengths into WTF);
  // chatbot's tree carries a 3.03GB .git pack and the five crashes share
  // exactly that assert. The reader must refuse by SIZE, before any read.
  const coreMod = await import(pathToFileURL(path.resolve(import.meta.dirname, "vibeweaver-audit-core.js")).href)
  const big = path.join(TMP, "t43-3gb.bin")
  rmSync(big, { force: true })
  writeFileSync(big, "")
  execFileSync("truncate", ["-s", "3G", big])
  const t0 = Date.now()
  const got = typeof coreMod.safeReadBounded === "function" ? await coreMod.safeReadBounded(big) : undefined
  const ms = Date.now() - t0
  const small = path.join(TMP, "t43-small.txt")
  writeFileSync(small, "hello-bounded-read")
  const okSmall = typeof coreMod.safeReadBounded === "function" ? await coreMod.safeReadBounded(small) : undefined
  rec("T43 >=2GB file refused by size before any string constructor", got === "" && ms < 2000,
    `got=${JSON.stringify(String(got).slice(0, 24))} ms=${ms} (expect "" fast)`)
  rec("T43 bounded read still returns content under the cap", okSmall === "hello-bounded-read",
    `got=${JSON.stringify(String(okSmall).slice(0, 24))}`)
  rmSync(big, { force: true })
}

// ---------- summary ----------
console.log("\n=== SUMMARY ===")
console.log(`fixture checks: ${results.length}, failures: ${failures}${skips ? `, skipped: ${skips}` : ""}`)
if (failures > 0) {
  for (const r of results.filter((r) => !r.ok)) console.log("FAILED:", r.name, "—", r.detail)
}
process.exit(failures ? 1 : 0)
