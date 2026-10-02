// Mutation sweep — for every check the audit claims, break exactly that one
// thing in the clean fixture and assert the audit flags it BAD.
// Usage: node scripts/mutation_sweep.mjs   (deterministic, no LLM, no network)
import { execFileSync } from "node:child_process"
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { pathToFileURL } from "node:url"
import path from "node:path"

const CORE = path.resolve(import.meta.dirname, "vibeweaver-audit-core.js")
const { auditProject } = await import(pathToFileURL(CORE))

const TMP = "/tmp/vibeweaver-mutation-sweep"
let pass = 0
let fail = 0

const GATE =
  "[Verification Gate] Verifier: mm-sensor [image] | direct-read | Class: CODE | Loop executed: yes | Media graded externally: 3/3 (video 0 · audio 0 · screenshots 3) | Iterations: 2 | Tests executed with artifacts: yes | E2E depth: real-HTTP | Script-only build/lifecycle: yes | Fresh-run on final tree: yes | TDD RED evidence: yes | Code review: N/A | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass"

const TEXT = [
  "Verifier: mm-sensor [image]",
  "A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit",
  GATE,
  "[Covenant Recall] checked: all 13 covenants hold for this completion",
  "[Memory Gate] Passed: ok",
  "[Convergence] x: 2 iters | 6/6 pass | 0 stalls | 0 cap-hits",
  "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
  "| 1 | fix | none | A | src/a.ts | fixed | tests/shot.png -> ok | abc |",
].join("\n")

// Class DOC lite path (COV-13 / §V11.6) — 3-column table + memory_gate: na.
const LITE_DOC_TEXT = [
  "Class: DOC — CHANGELOG.md prose only",
  "[Verification Gate] Verifier: direct read (non-web) | direct-read | Class: DOC | Loop executed: no (Class: DOC — read-back verify) | Media graded externally: 0/0 (video 0 · audio 0 · screenshots 0) | Iterations: 1 | Tests executed with artifacts: no | E2E depth: unit-only | Script-only build/lifecycle: no | Fresh-run on final tree: yes | Fresh-verify: N/A (Class: DOC) | TDD RED evidence: N/A | Code review: N/A | assert_artifacts.py: pass=8/fail=0 | covenant_recall: pass | memory_gate: na | HARD-GATE-1: NO-TEST-NO-DONE=na | HARD-GATE-2: SCRIPT-ONLY=na",
  "[Covenant Recall] checked: all 13 covenants hold for this completion",
  "[Memory Gate] na (Class: DOC — no lesson to persist)",
  "[Convergence] doc: 1 iter | 1/1 pass | 0 stalls | 0 cap-hits",
  "A4.9 not triggered — verified via git diff --stat: 1 file, documentation-only change",
  "docs-drift: none (README does not describe the edited changelog entry)",
  "| # | Problem | What Changed & Evidence |",
  "| 1 | stale entry | CHANGELOG.md — entry added; read-back confirms |",
].join("\n")

const TOOLS = () => [
  { tool: "skill", name: "vibeweaver", t: 1000 },
  { tool: "read", filePath: "/x/.config/opencode/skills/vibeweaver/TESTING_PROTOCOLS.md", t: 1001 },
  { tool: "read", filePath: "/x/.config/opencode/skills/vibeweaver/COMPLETION_GATE.md", t: 1002 },
  { tool: "read", filePath: "/x/.config/opencode/skills/vibeweaver/REFERENCE.md", t: 1003 },
  { tool: "bash", command: "bash script/linux/start.sh", t: 1004 },
  { tool: "write", filePath: "/x/src/a.ts", t: 1005 },
]

function scaffold(root) {
  rmSync(root, { recursive: true, force: true })
  for (const d of ["tests/workflows", "memory", "script/linux", "src"]) mkdirSync(path.join(root, d), { recursive: true })
  const log = [
    "## Task: mutation | 2026-08-19",
    "- Baseline verified GREEN",
    "- iter 1 FAIL: criterion #1 | diagnosis: hydration order | changed: src/a.ts",
    "- iter 2 PASS: all criteria (evidence: tests/shot.png, 6/6)",
    "- [Convergence] x: 2 iters | 6/6 pass",
    "workflow: tests/workflows/wf.trace.log — green",
  ].join("\n")
  writeFileSync(path.join(root, "tests/verification_log.md"), log)
  writeFileSync(path.join(root, "tests/acceptance.md"), "> cap=5  stall=3×\n1. a\n2. b\n")
  writeFileSync(path.join(root, "tests/shot.png"), "x")
  writeFileSync(path.join(root, "tests/flow.mp4"), "x")
  writeFileSync(path.join(root, "tests/flow_audio.wav"), "x")
  writeFileSync(path.join(root, "tests/workflows/wf.trace.log"), "ok")
  writeFileSync(path.join(root, "memory/MEMORY.md"), "# Index\n- [fix](fix.md)\n")
  writeFileSync(path.join(root, "memory/fix.md"), "# Fix\n")
  for (const s of ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]) {
    const p = path.join(root, "script/linux", s)
    writeFileSync(p, "#!/bin/sh\nexit 0\n")
    chmodSync(p, 0o755)
  }
  writeFileSync(path.join(root, "src/a.ts"), "export const a = 1\n")
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["config", "user.email", "m@t"], { cwd: root })
  execFileSync("git", ["config", "user.name", "m"], { cwd: root })
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "baseline"], { cwd: root })
}

function run(label, mutate, expectBadIds, opts = {}) {
  const root = path.join(TMP, label)
  scaffold(root)
  const m = mutate(root)
  const text = (m && m.text) || TEXT
  const tools = (m && m.tools) || TOOLS()
  const audit = auditProject({ root, sessionID: "ses_" + label, sessionText: text, tools, skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const bad = audit.checks.filter((c) => c.verdict === "BAD").map((c) => c.id)
  const ok = expectBadIds.every((id) => bad.includes(id))
  if (ok) {
    pass++
    console.log(`PASS  ${label} -> BAD=[${bad.join(",")}]`)
  } else {
    fail++
    console.log(`FAIL  ${label} -> BAD=[${bad.join(",")}] expected ${expectBadIds.join(",")}`)
  }
}

// --- per-check mutations ---
run("A1-no-iters", (r) => writeFileSync(path.join(r, "tests/verification_log.md"), "## Task\nno iterations\n"), ["A1"])
run("A2-no-cap", (r) => writeFileSync(path.join(r, "tests/acceptance.md"), "1. a\n"), ["A2"])
run("A3-missing-png", (r) => { writeFileSync(path.join(r, "tests/shot.png"), "") }, ["A3"])
for (let i = 1; i <= 11; i++) {
  const id = "B" + i
  const token = {
    B1: "[Verification Gate]", B2: "HARD-GATE-1: NO-TEST-NO-DONE", B3: "HARD-GATE-2: SCRIPT-ONLY",
    B4: "[Covenant Recall]", B5: "[Memory Gate]", B6: "[Convergence]",
    B7: "| # | Problem | Research Sources", B8: "assert_artifacts.py: pass=13/fail=0",
    B9: "covenant_recall: pass", B10: "memory_gate: pass", B11: "Class:",
  }[id]
  run("B" + i + "-marker-removed", (r, m) => {
    const lines = TEXT.split("\n").filter((l) => !l.includes(token))
    return { text: lines.join("\n") }
  }, [id])
}
// COV-13 class gating: the lite path is licensed ONLY by a filled Class field.
run("B7-lite-table-unlicensed", () => ({
  text: LITE_DOC_TEXT.replace(/Class: DOC/g, "Class: CODE"),
}), ["B7"])
run("B10-memory-na-unlicensed", () => ({
  text: LITE_DOC_TEXT.replace(/Class: DOC/g, "Class: CODE")
    .replace(/documentation-only change/g, "routine release note")
    .replace(/no lesson to persist/g, "gate field only"),
}), ["B10"])
run("B11-template-unfilled", () => ({
  text: TEXT.replace("Class: CODE", "Class: DOC|CONFIG|CODE"),
}), ["B11"])
run("C18-doc-class-code-write", () => ({
  text: LITE_DOC_TEXT,
  tools: [...TOOLS(), { tool: "write", filePath: "/x/src/sneaky.ts", t: Date.now() + 500 }],
}), ["C18"])

// class-licensed lite path is CLEAN: a DOC-shaped fixture (class basis line,
// COV-9 skipped, no memory/ no script/) must audit with ZERO BAD and
// assert_artifacts.py must exit 0 via its class-NA groups.
{
  const root = path.join(TMP, "lite-doc-clean")
  rmSync(root, { recursive: true, force: true })
  mkdirSync(path.join(root, "tests"), { recursive: true })
  writeFileSync(path.join(root, "tests/verification_log.md"), [
    "## Task: changelog entry | 2026-09-28",
    "- class: DOC — CHANGELOG.md prose only",
    "- COV-9 skipped — reason: documentation-only change (no runtime to baseline-test)",
    "- iter 1 PASS: criterion #1 — entry added (evidence: read-back of CHANGELOG.md)",
  ].join("\n"))
  writeFileSync(path.join(root, "tests/acceptance.md"), "> cap=5  stall=3×\n1. Entry added in the release-notes format\n")
  const assertSrc = path.resolve(import.meta.dirname, "assert_artifacts.py")
  if (existsSync(assertSrc)) writeFileSync(path.join(root, "tests/assert_artifacts.py"), readFileSync(assertSrc, "utf8"))
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["config", "user.email", "m@t"], { cwd: root })
  execFileSync("git", ["config", "user.name", "m"], { cwd: root })
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "docs: changelog entry"], { cwd: root })
  const audit = auditProject({
    root,
    sessionID: "ses_lite_doc",
    sessionText: LITE_DOC_TEXT,
    tools: [{ tool: "write", filePath: "/x/CHANGELOG.md", t: Date.now() - 1000 }],
    skillLoaded: true,
    phase: "final",
    config: { samplingRate: 0 },
  })
  const bad = audit.checks.filter((c) => c.verdict === "BAD").map((c) => c.id)
  let assertOk = false
  try {
    execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), "--class", "DOC"], { cwd: root, stdio: "pipe", timeout: 15000 })
    assertOk = true
  } catch {
    try {
      execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), "--existing", "--class", "DOC"], { cwd: root, stdio: "pipe", timeout: 15000 })
      assertOk = true
    } catch { assertOk = false }
  }
  const ok = bad.length === 0 && assertOk
  if (ok) {
    pass++
    console.log(`PASS  lite-doc-clean -> BAD=[] assert_artifacts(class DOC)=exit 0`)
  } else {
    fail++
    console.log(`FAIL  lite-doc-clean -> BAD=[${bad.join(",")}] assert=${assertOk}`)
  }
}

// CONFIG + `- memory: na (<why>)` N/A's the memory group (group 4) — proven on a
// fixture with NO memory/ dir; without the reasoned line the same fixture must FAIL.
{
  const root = path.join(TMP, "config-mem-na")
  rmSync(root, { recursive: true, force: true })
  for (const d of ["tests", "script/linux"]) mkdirSync(path.join(root, d), { recursive: true })
  const mkLog = (memLine) => [
    "## Task: config tweak | 2026-09-28",
    "- class: CONFIG — config.toml only",
    "- Baseline verified GREEN — script/linux/project_build.sh exit 0 (COV-9: CONFIG runs the baseline, §V11.3)",
    memLine,
    "- iter 1 PASS: criterion #1 (evidence: config parses)",
  ].join("\n")
  writeFileSync(path.join(root, "tests/acceptance.md"), "> cap=5  stall=3×\n1. Config key updated\n")
  const assertSrc = path.resolve(import.meta.dirname, "assert_artifacts.py")
  if (existsSync(assertSrc)) writeFileSync(path.join(root, "tests/assert_artifacts.py"), readFileSync(assertSrc, "utf8"))
  for (const s of ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]) {
    const p = path.join(root, "script/linux", s)
    writeFileSync(p, "#!/bin/sh\nexit 0\n")
    chmodSync(p, 0o755)
  }
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["config", "user.email", "m@t"], { cwd: root })
  execFileSync("git", ["config", "user.name", "m"], { cwd: root })
  const runAssert = () => {
    for (const flags of [["--existing", "--class", "CONFIG"], ["--class", "CONFIG"], ["--existing"]]) {
      try {
        execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), ...flags], { cwd: root, stdio: "pipe", timeout: 15000 })
        return true
      } catch { /* next combo */ }
    }
    return false
  }
  writeFileSync(path.join(root, "tests/verification_log.md"), mkLog("- memory: na (no lesson — value tweak only)"))
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "config"], { cwd: root })
  const withReason = runAssert()
  writeFileSync(path.join(root, "tests/verification_log.md"), mkLog("- memory: na"))
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "config2"], { cwd: root })
  const bare = runAssert()
  const ok = withReason && !bare
  if (ok) {
    pass++
    console.log(`PASS  config-memory-na-reasoned -> exit 0 with reason, exit 1 without`)
  } else {
    fail++
    console.log(`FAIL  config-memory-na-reasoned -> withReason=${withReason} bare=${bare} (expected true/false)`)
  }
}

// §V11.9 exec-check row + DOC lesson rule (COV-7: a wave with FAIL/stall HAS a lesson)
{
  const root = path.join(TMP, "exec-check-row")
  rmSync(root, { recursive: true, force: true })
  for (const d of ["tests", "output", "memory"]) mkdirSync(path.join(root, d), { recursive: true })
  const assertSrc = path.resolve(import.meta.dirname, "assert_artifacts.py")
  if (existsSync(assertSrc)) writeFileSync(path.join(root, "tests/assert_artifacts.py"), readFileSync(assertSrc, "utf8"))
  writeFileSync(path.join(root, "tests/acceptance.md"), "> cap=5  stall=3×\n1. Delivered\n")
  writeFileSync(path.join(root, "tests/report_p1.png"), "png")
  writeFileSync(path.join(root, "memory/MEMORY.md"), "# Index\n- [fix](fix.md)\n")
  writeFileSync(path.join(root, "memory/fix.md"), "# Fix\n")
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["config", "user.email", "m@t"], { cwd: root })
  execFileSync("git", ["config", "user.name", "m"], { cwd: root })
  execFileSync("git", ["add", "-A"], { cwd: root })
  execFileSync("git", ["commit", "-qm", "backup: before changes"], { cwd: root }) // wave baseline
  const mkLog = (extra) => [
    "## Task: asset | 2026-09-28",
    "- class: DOC — report delivered",
    "- Baseline verified GREEN",
    extra,
    "- iter 1 PASS: all",
  ].join("\n")
  const runA = () => {
    try {
      execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), "--existing"], { cwd: root, stdio: "pipe", timeout: 15000 })
      return true
    } catch { return false }
  }
  // wave commit 1: deliver the asset WITHOUT the exec-check line -> must FAIL
  writeFileSync(path.join(root, "output/report.docx"), "bin")
  writeFileSync(path.join(root, "tests/verification_log.md"),
    mkLog("render: report.docx — tests/report_p1.png | pages: 1"))
  execFileSync("git", ["add", "-A"], { cwd: root }); execFileSync("git", ["commit", "-qm", "wave1"], { cwd: root })
  const noExec = runA()
  // wave commit 2: record the exec-check -> must PASS
  writeFileSync(path.join(root, "tests/verification_log.md"),
    mkLog("render: report.docx — tests/report_p1.png | pages: 1\n- exec-check: report.docx — clean (no vbaProject.bin)"))
  execFileSync("git", ["add", "-A"], { cwd: root }); execFileSync("git", ["commit", "-qm", "wave2"], { cwd: root })
  const withExec = runA()
  // wave commit 3: FAIL lesson + memory topics removed -> group 4 must FAIL
  writeFileSync(path.join(root, "tests/verification_log.md"), [
    "## Task: hard layout | 2026-09-28",
    "- class: DOC — report",
    "- Baseline verified GREEN",
    "- render: report.docx — tests/report_p1.png | pages: 1",
    "- exec-check: report.docx — clean",
    "- iter 1 FAIL: criterion #1 | diagnosis: edge bleed | changed: report.docx",
    "- iter 2 PASS: all",
  ].join("\n"))
  execFileSync("rm", ["-f", path.join(root, "memory/fix.md")])
  writeFileSync(path.join(root, "memory/MEMORY.md"), "# Index\n")
  execFileSync("git", ["add", "-A"], { cwd: root }); execFileSync("git", ["commit", "-qm", "wave3"], { cwd: root })
  const memMissing = runA()
  const ok = !noExec && withExec && !memMissing
  if (ok) {
    pass++
    console.log(`PASS  exec-check-row+doc-lesson -> noExec=FAIL withExec=PASS memMissing=FAIL`)
  } else {
    fail++
    console.log(`FAIL  exec-check-row+doc-lesson -> noExec=${noExec} withExec=${withExec} memMissing=${memMissing} (expected false/true/false)`)
  }
}
run("C1-loop-yes-no-iters", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), "## Task\nno iter lines\n")
  return { text: TEXT }
}, ["C1"])
run("C2-iters-overclaim", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), "## Task\n- iter 1 PASS: all\n") // 1 entry, claim 2
  return { text: TEXT.replace("Iterations: 2", "Iterations: 5") }
}, ["C2"])
run("C3-media-overclaim", () => ({ text: TEXT.replace("Media graded externally: 3/3", "Media graded externally: 9/9") }), ["C3"])
run("C4-e2e-no-trace", (r) => {
  rmSync(path.join(r, "tests/workflows"), { recursive: true, force: true })
  return { text: TEXT }
}, ["C4"])
run("C5-tdd-no-fail", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), "## Task\n- iter 1 PASS: all\n- iter 2 PASS: all\n")
  return { text: TEXT }
}, ["C5"])
run("C7-na-no-reason", () => ({ text: TEXT.replace("A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit\n", "") }), ["C7"])
run("C8-raw-command", () => ({ tools: [...TOOLS(), { tool: "bash", command: "npm run build" }] }), ["C8"])
run("C13-no-baseline", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), "## Task\n- iter 1 PASS: all\n")
  return { text: TEXT }
}, ["C13"])
run("C14-bad-hard1", () => ({ text: TEXT.replace("HARD-GATE-1: NO-TEST-NO-DONE=pass", "HARD-GATE-1: NO-TEST-NO-DONE=fail") }), ["C14"])
// na-without-reason must be UNCERTAIN, never BAD and never OK (previously
// vacuous: expectBadIds=[] is always true — R2 review finding, now pinned).
{
  const root = path.join(TMP, "na-uncertain")
  scaffold(root)
  const cases = [
    ["C14-na-no-reason-uncertain", TEXT.replace("HARD-GATE-1: NO-TEST-NO-DONE=pass", "HARD-GATE-1: NO-TEST-NO-DONE=na"), "C14"],
    ["C15-na-no-reason-uncertain", TEXT.replace("HARD-GATE-2: SCRIPT-ONLY=pass", "HARD-GATE-2: SCRIPT-ONLY=na"), "C15"],
  ]
  for (const [label, text, id] of cases) {
    const audit = auditProject({ root, sessionID: "ses_" + label, sessionText: text, tools: TOOLS(), skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
    const c = audit.checks.find((x) => x.id === id)
    const ok = c && c.verdict === "UNCERTAIN"
    if (ok) {
      pass++
      console.log(`PASS  ${label} -> ${id}=UNCERTAIN`)
    } else {
      fail++
      console.log(`FAIL  ${label} -> ${id}=${c ? c.verdict : "missing"} expected UNCERTAIN`)
    }
  }
  // Class DOC/CONFIG licenses na without a prose reason (§V11.3) — must be OK
  const lit = auditProject({ root, sessionID: "ses_na_lite", sessionText: LITE_DOC_TEXT, tools: [{ tool: "write", filePath: "/x/CHANGELOG.md", t: Date.now() - 1000 }], skillLoaded: true, phase: "final", config: { samplingRate: 0 } })
  const h1 = lit.checks.find((x) => x.id === "C14")
  const okLite = h1 && h1.verdict === "OK"
  if (okLite) {
    pass++
    console.log(`PASS  C14-na-licensed-by-class -> OK`)
  } else {
    fail++
    console.log(`FAIL  C14-na-licensed-by-class -> ${h1 ? h1.verdict : "missing"} expected OK`)
  }
}
run("C18-doc-tests-hidden-write", () => ({
  text: LITE_DOC_TEXT,
  tools: [{ tool: "write", filePath: "/x/tests/conftest.py" }], // untimed + tests/-hidden
}), ["C18"])
// §V11.9 DOC-asset render gate — both directions pinned (logs rewritten WITHOUT
// any pre-cited png so the license comes only from the claim's own evidence)
run("C18-doc-asset-no-render", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), "## Task: asset | 2026-09-28\n- Baseline verified GREEN\n- iter 1 PASS: all\n")
  return {
    text: LITE_DOC_TEXT,
    tools: [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() - 1000 }],
    expectEvidence: /render/i,
  }
}, ["C18"])
{
  const root = path.join(TMP, "doc-asset-rendered")
  scaffold(root)
  writeFileSync(path.join(root, "tests/verification_log.md"), "## Task: asset | 2026-09-28\n- Baseline verified GREEN\n- iter 1 PASS: all\n")
  writeFileSync(path.join(root, "tests/report_p1.png"), "png-bytes") // evidence binding: must exist on disk
  const rendered = LITE_DOC_TEXT.replace("docs-drift: none (README does not describe the edited changelog entry)",
    "render: report.docx — tests/report_p1.png rendered page verified")
  const okAudit = auditProject({
    root, sessionID: "ses_asset_ok", sessionText: rendered,
    tools: [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() - 1000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18ok = okAudit.checks.find((c) => c.id === "C18")
  const naText = LITE_DOC_TEXT.replace("docs-drift: none (README does not describe the edited changelog entry)",
    "render: report.docx — N/A (soffice missing; layout risk flagged)")
  const naAudit = auditProject({
    root, sessionID: "ses_asset_na", sessionText: naText,
    tools: [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() - 1000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18na = naAudit.checks.find((c) => c.id === "C18")
  // branch discrimination: the no-render verdict must SAY render (not "misreport")
  const bareAudit = auditProject({
    root, sessionID: "ses_asset_bare", sessionText: LITE_DOC_TEXT,
    tools: [{ tool: "write", filePath: "/x/output/report.docx", t: Date.now() - 1000 }],
    skillLoaded: true, phase: "final", config: { samplingRate: 0 },
  })
  const c18bare = bareAudit.checks.find((c) => c.id === "C18")
  const ok = c18ok && c18ok.verdict === "OK" && c18na && c18na.verdict === "OK"
    && c18bare && c18bare.verdict === "BAD" && /render/i.test(c18bare.evidence)
  if (ok) {
    pass++
    console.log(`PASS  C18-doc-asset-rendered-or-flagged -> OK/OK, bare=BAD(render-branch)`)
  } else {
    fail++
    console.log(`FAIL  C18-doc-asset-rendered-or-flagged -> rendered=${c18ok && c18ok.verdict} na=${c18na && c18na.verdict} bare=${c18bare && c18bare.verdict} (expected OK/OK/BAD-render)`)
  }
}
run("C18-config-logic-write", () => ({
  text: LITE_DOC_TEXT.replace(/Class: DOC/g, "Class: CONFIG"),
  tools: [{ tool: "write", filePath: "/x/src/logic.py", t: Date.now() + 500 }],
}), ["C18"])
run("B11-class-mismatch", (r) => {
  writeFileSync(path.join(r, "tests/verification_log.md"), [
    "## Task: mixed claims",
    "- class: CODE — logic changed",
    "- Baseline verified GREEN",
    "- iter 1 PASS: all",
  ].join("\n"))
  return { text: LITE_DOC_TEXT } // gate line claims Class: DOC
}, ["B11"])
run("C15-bad-hard2", () => ({ text: TEXT.replace("HARD-GATE-2: SCRIPT-ONLY=pass", "HARD-GATE-2: SCRIPT-ONLY=invalid") }), ["C15"])
run("C16-code-after-log", (r) => {
  const logM = new Date(readFileSync(path.join(r, "tests/verification_log.md"), "utf8") ? Date.now() : 0)
  const t = Date.now() + 1000 // writes AFTER the fixture creation (log already written)
  return { tools: [...TOOLS(), { tool: "write", filePath: "/x/src/b.ts", t }] }
}, ["C16"])
run("C6-commit-after", (r) => {
  // real violation: code change committed after the log write
  writeFileSync(path.join(r, "tests/verification_log.md"), readFileSync(path.join(r, "tests/verification_log.md"), "utf8") + "\npost\n")
  execFileSync("sleep", ["3.5"])
  writeFileSync(path.join(r, "src/code.ts"), "export const c = 1\n")
  execFileSync("git", ["add", "-A"], { cwd: r })
  execFileSync("git", ["commit", "-qm", "after"], { cwd: r })
  return { text: TEXT }
}, ["C6"])

console.log(`\n=== MUTATION SWEEP: ${pass} passed, ${fail} failed ===`)
process.exit(fail ? 1 : 0)
