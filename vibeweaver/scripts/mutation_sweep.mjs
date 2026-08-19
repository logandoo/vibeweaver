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
  "[Verification Gate] Verifier: mm-sensor [image] | direct-read | Loop executed: yes | Media graded externally: 3/3 (video 0 · audio 0 · screenshots 3) | Iterations: 2 | Tests executed with artifacts: yes | E2E depth: real-HTTP | Script-only build/lifecycle: yes | Fresh-run on final tree: yes | TDD RED evidence: yes | Code review: N/A | assert_artifacts.py: pass=13/fail=0 | covenant_recall: pass | memory_gate: pass | HARD-GATE-1: NO-TEST-NO-DONE=pass | HARD-GATE-2: SCRIPT-ONLY=pass"

const TEXT = [
  "Verifier: mm-sensor [image]",
  "A4.9 not triggered — verified via git diff --stat: 1 file, config edit — reason: config edit",
  GATE,
  "[Covenant Recall] checked: all 11 covenants hold for this completion",
  "[Memory Gate] Passed: ok",
  "[Convergence] x: 2 iters | 6/6 pass | 0 stalls | 0 cap-hits",
  "| # | Problem | Research Sources (exa MCP / Context7) | Chosen Approach & Why | Files Changed | What Changed | Verification Evidence (Screenshot / Log) | Commit |",
  "| 1 | fix | none | A | src/a.ts | fixed | tests/shot.png -> ok | abc |",
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
for (let i = 1; i <= 10; i++) {
  const id = "B" + i
  const token = {
    B1: "[Verification Gate]", B2: "HARD-GATE-1: NO-TEST-NO-DONE", B3: "HARD-GATE-2: SCRIPT-ONLY",
    B4: "[Covenant Recall]", B5: "[Memory Gate]", B6: "[Convergence]",
    B7: "| # | Problem | Research Sources", B8: "assert_artifacts.py: pass=13/fail=0",
    B9: "covenant_recall: pass", B10: "memory_gate: pass",
  }[id]
  run("B" + i + "-marker-removed", (r, m) => {
    const lines = TEXT.split("\n").filter((l) => !l.includes(token))
    return { text: lines.join("\n") }
  }, [id])
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
run("C14-na-no-reason", () => ({ text: TEXT.replace("HARD-GATE-1: NO-TEST-NO-DONE=pass", "HARD-GATE-1: NO-TEST-NO-DONE=na") }), []) // na 无理由 -> UNCERTAIN 而非 BAD
run("C15-na-no-reason", () => ({ text: TEXT.replace("HARD-GATE-2: SCRIPT-ONLY=pass", "HARD-GATE-2: SCRIPT-ONLY=na") }), []) // 同上
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
