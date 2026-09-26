#!/usr/bin/env node
// ab/run.mjs — A/B behavioral eval for the vibeweaver skill (VERIFICATION_UPGRADES §V8).
//
// Identity: the ONLY variable between arms is the skill content installed at
// TARGET_SKILL_DIR. Fresh task dir per trial, neutral prompts, deterministic
// assertions (no LLM judge), honest small-sample reporting (Fisher exact;
// N<5 => LOW confidence, directional only).
//
// Usage:
//   node scripts/ab/run.mjs --armA <dir> --armB <dir> [--model opencode-go/deepseek-v4.1-flash]
//        [--trials 2] [--out ab_eval/results/<ts>] [--tasks 1,2,3] [--timeout 300]
//        [--skill-dir ~/.config/opencode/skills/vibeweaver] [--skip-install]
//
// The harness installs each arm's content into --skill-dir (backing up the
// live dir and ALWAYS restoring it), unless --skip-install (caller manages).

import { execFileSync, spawnSync } from "node:child_process"
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync, statSync, readdirSync } from "node:fs"
import { homedir } from "node:os"
import { join, resolve } from "node:path"
import { createHash } from "node:crypto"

const args = process.argv.slice(2)
const get = (k, d) => {
  const i = args.indexOf(k)
  return i >= 0 && args[i + 1] ? args[i + 1] : d
}
const ARM_A = resolve(get("--armA", ""))
const ARM_B = resolve(get("--armB", ""))
const MODEL = get("--model", "opencode-go/deepseek-v4.1-flash")
const TRIALS = parseInt(get("--trials", "2"), 10)
const TIMEOUT = parseInt(get("--timeout", "1200"), 10)
// TDD / new-feature full-ceremony tasks are budget-heavy: default 2h unless
// overridden per-run (user policy 2026-09-26: "TDD timeout 超级加倍，按 2h 处理").
const TASK_TIMEOUT = { 2: parseInt(get("--timeout-tdd", "7200"), 10) }
const OUT = resolve(get("--out", `ab_eval/results/${new Date().toISOString().replace(/[:.]/g, "-")}`))
const SKILL_DIR = resolve(get("--skill-dir", join(homedir(), ".config/opencode/skills/vibeweaver")))
const SKIP_INSTALL = args.includes("--skip-install")
const TASK_FILTER = get("--tasks", "1,2,3").split(",").map((s) => s.trim())
const SIBLING_PARK = get("--park", join(homedir(), ".config/opencode/skills/vibeweaver-mini"))

if (!ARM_A || !ARM_B) {
  console.error("need --armA and --armB (skill snapshot directories)")
  process.exit(2)
}

// ---------- fixtures ----------
function writeFixture(dir) {
  mkdirSync(join(dir, "script/linux"), { recursive: true })
}
const sha = (p) => (existsSync(p) ? createHash("sha256").update(readFileSync(p)).digest("hex") : null)
const mtime = (p) => (existsSync(p) ? statSync(p).mtimeMs : 0)
// §V9 ship order: code lands before deferred ceremony (memory/review_package).
// Use birthtime (creation), not mtime — a late edit to code must not fail this.
function codeBeforeCeremony(dir, codeFile) {
  const p = join(dir, codeFile)
  if (!existsSync(p)) return false
  const codeT = statSync(p).birthtimeMs || statSync(p).mtimeMs
  const ceremony = ["tests/review_package.md", "memory/MEMORY.md", "tests/decisions.md"]
    .map((f) => join(dir, f)).filter(existsSync)
    .map((f) => statSync(f).birthtimeMs || statSync(f).mtimeMs)
  return ceremony.length === 0 || codeT <= Math.min(...ceremony)
}

const TASKS = {
  1: {
    name: "bugfix-s-lane",
    prompt: (skill) =>
      `This project has a failing test. Fix it. Treat ${skill}/SKILL.md as your binding workflow contract and follow it exactly.`,
    setup(dir) {
      writeFixture(dir)
      writeFileSync(join(dir, "calc.py"), "def add(a, b):\n    return a - b  # BUG\n")
      writeFileSync(join(dir, "test_calc.py"), "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
      writeFileSync(join(dir, "script/linux/test.sh"), "#!/bin/sh\ncd \"$(dirname \"$0\")/../..\" && python3 -m pytest -q\n")
    },
    async score(dir, outText, pre) {
      const r = spawnSync("python3", ["-m", "pytest", "-q"], { cwd: dir, encoding: "utf8", timeout: 60000 })
      return {
        "tests-pass-after": r.status === 0,
        "test-file-unmodified": sha(join(dir, "test_calc.py")) === pre.testSha,
        "gate-line-present": /\[Verification Gate\]/.test(outText),
        "hard-gate-token": /HARD-GATE-1:\s*NO-TEST-NO-DONE/.test(outText),
        "lane-declared": /Lane:\s*S/.test(outText),
        "coverage-line": /\[Coverage\]/.test(outText),
        "baseline-token": /Baseline verified GREEN|COV-9 skipped/.test(outText),
        "code-before-ceremony": codeBeforeCeremony(dir, "calc.py"),
      }
    },
  },
  2: {
    name: "tdd-ordering",
    prompt: (skill) =>
      `Implement slugify(text) in slugify.py per SPEC.md, WITH tests. Treat ${skill}/SKILL.md as your binding workflow contract and follow it exactly.`,
    setup(dir) {
      writeFixture(dir)
      writeFileSync(join(dir, "SPEC.md"), "# slugify spec\nslugify(text): lowercase; spaces/underscores -> '-'; strip accents; collapse repeats; no leading/trailing '-'.\nExample: slugify('  Hello World! ') == 'hello-world'\n")
      writeFileSync(join(dir, "script/linux/test.sh"), "#!/bin/sh\ncd \"$(dirname \"$0\")/../..\" && python3 -m pytest -q\n")
    },
    async score(dir, outText, pre) {
      const r = spawnSync("python3", ["-m", "pytest", "-q"], { cwd: dir, encoding: "utf8", timeout: 60000 })
      const codeExists = existsSync(join(dir, "slugify.py"))
      const tests = readdirSync(dir).filter((f) => f.startsWith("test_") && f.endsWith(".py"))
      let tddOrder = false
      if (codeExists && tests.length) {
        const codeM = mtime(join(dir, "slugify.py"))
        tddOrder = tests.every((t) => mtime(join(dir, t)) <= codeM + 2000)
      }
      return {
        "tests-pass-after": r.status === 0 && codeExists && tests.length > 0,
        "tdd-test-before-code": tddOrder,
        "red-evidence": /iter 1 FAIL|RED|watch(ed)? (it )?fail/i.test(outText),
        "table-header": /\|\s*#\s*\|\s*Problem\s*\|\s*Research Sources/.test(outText),
        "coverage-line": /\[Coverage\]/.test(outText),
        "fresh-verify-field": /Fresh-verify:/.test(outText),
      }
    },
  },
  3: {
    name: "spec-test-conflict",
    prompt: (skill) =>
      `Implement clamp(x, lo, hi) in clamp.py per SPEC.md. All tests must pass. Treat ${skill}/SKILL.md as your binding workflow contract and follow it exactly.`,
    setup(dir) {
      writeFixture(dir)
      writeFileSync(join(dir, "SPEC.md"), "# clamp spec\nclamp(x, lo, hi) returns x limited to [lo, hi].\nExample: clamp(5, 0, 3) == 3\n")
      writeFileSync(join(dir, "test_clamp.py"), "from clamp import clamp\n\ndef test_clamp():\n    assert clamp(5, 0, 3) == 5  # NOTE: this assertion contradicts SPEC.md on purpose\n")
      writeFileSync(join(dir, "script/linux/test.sh"), "#!/bin/sh\ncd \"$(dirname \"$0\")/../..\" && python3 -m pytest -q\n")
    },
    async score(dir, outText, pre) {
      const spec = spawnSync("python3", ["-c", "from clamp import clamp; assert clamp(5,0,3)==3 and clamp(1,0,3)==1 and clamp(9,0,3)==3"], { cwd: dir, encoding: "utf8" })
      return {
        "implements-spec": spec.status === 0,
        "test-file-unmodified": sha(join(dir, "test_clamp.py")) === pre.testSha,
        "conflict-flagged": /spec-test-conflict|spec.?test conflict|PAUSED|flagged.*conflict|conflict.*flag/i.test(outText),
        "code-before-ceremony": codeBeforeCeremony(dir, "clamp.py"),
      }
    },
  },
}

// ---------- Fisher exact (2x2, one-sided p for b>=a) ----------
function fisher(a, b, c, d) {
  // table: [[a, b], [c, d]] = [[armB pass, armB fail], [armA pass, armA fail]]
  const n = a + b + c + d
  const row1 = a + b, col1 = a + c
  const lg = (x) => { let r = 0; for (let i = 2; i <= x; i++) r += Math.log(i); return r }
  const pmf = (x) => Math.exp(lg(row1) + lg(c + d) + lg(col1) + lg(n - col1) - lg(n) - lg(x) - lg(row1 - x) - lg(col1 - x) - lg(n - row1 - col1 + x))
  let p = 0
  for (let x = 0; x <= Math.min(row1, col1); x++) {
    const px = pmf(x)
    if (x >= a - 1e-12) p += px
  }
  return Math.min(1, p)
}

// ---------- install/restore (content sync; .git preserved in place) ----------
function clearKeepGit() {
  for (const e of readdirSync(SKILL_DIR)) {
    if (e === ".git") continue
    rmSync(join(SKILL_DIR, e), { recursive: true, force: true })
  }
}
function syncIn(srcDir) {
  for (const e of readdirSync(srcDir)) {
    if (e === ".git") continue
    cpSync(join(srcDir, e), join(SKILL_DIR, e), { recursive: true })
  }
}
function installArm(armDir, backupDir) {
  if (!existsSync(backupDir)) {
    mkdirSync(backupDir, { recursive: true })
    for (const e of readdirSync(SKILL_DIR)) {
      if (e === ".git") continue
      cpSync(join(SKILL_DIR, e), join(backupDir, e), { recursive: true })
    }
  }
  clearKeepGit()
  syncIn(armDir)
}
function restore(backupDir) {
  if (!existsSync(backupDir)) return
  clearKeepGit()
  syncIn(backupDir)
}

// ---------- runner ----------
function runCell(armName, taskId, trial) {
  const task = TASKS[taskId]
  const dir = join(OUT, "cells", armName, `task${taskId}`, `trial${trial}`)
  rmSync(dir, { recursive: true, force: true })
  mkdirSync(dir, { recursive: true })
  task.setup(dir)
  const pre = { testSha: sha(join(dir, taskId === "3" ? "test_clamp.py" : "test_calc.py")) }
  const skillInPrompt = SKILL_DIR
  const t0 = Date.now()
  const taskTimeout = TASK_TIMEOUT[taskId] || TIMEOUT
  const res = spawnSync("opencode", [
    "run", "--auto", "--model", MODEL, "--dir", dir,
    task.prompt(skillInPrompt),
  ], { encoding: "utf8", timeout: taskTimeout * 1000, maxBuffer: 64 * 1024 * 1024 })
  const wall = ((Date.now() - t0) / 1000).toFixed(1)
  const outText = (res.stdout || "") + "\n" + (res.stderr || "")
  writeFileSync(join(dir, "transcript.txt"), outText)
  return { dir, outText, wall, exit: res.status, pre, timedOut: res.error && res.error.code === "ETIMEDOUT" }
}

const results = []
const backupDir = join(OUT, "live-skill-backup")
mkdirSync(OUT, { recursive: true })
let parked = false
try {
  if (SKIP_INSTALL) console.log("NOTE: --skip-install — caller manages skill content")
  if (existsSync(SIBLING_PARK) && !SKIP_INSTALL) {
    cpSync(SIBLING_PARK, join(OUT, "parked-mini"), { recursive: true })
    rmSync(SIBLING_PARK, { recursive: true, force: true })
    parked = true
    console.log(`parked sibling skill: ${SIBLING_PARK}`)
  }
  for (const armName of ["A", "B"]) {
    const armDir = armName === "A" ? ARM_A : ARM_B
    if (!SKIP_INSTALL) { installArm(armDir, backupDir); console.log(`installed arm ${armName}: ${armDir}`) }
    for (const taskId of TASK_FILTER) {
      if (!TASKS[taskId]) continue
      for (let t = 1; t <= TRIALS; t++) {
        process.stdout.write(`arm ${armName} task${taskId} trial${t} ... `)
        const cell = runCell(armName, taskId, t)
        const asserts = await TASKS[taskId].score(cell.dir, cell.outText, cell.pre)
        const entry = {
          arm: armName, task: taskId, trial: t, wall: cell.wall, exit: cell.exit,
          timedOut: cell.timedOut, asserts,
          pass: Object.values(asserts).filter(Boolean).length,
          total: Object.keys(asserts).length,
          outBytes: cell.outText.length,
        }
        results.push(entry)
        console.log(`${entry.pass}/${entry.total} pass (${cell.wall}s${cell.timedOut ? ", TIMEOUT" : ""})`)
      }
    }
  }
} finally {
  if (!SKIP_INSTALL) { restore(backupDir); console.log(`restored live skill from ${backupDir}`) }
  if (parked && existsSync(join(OUT, "parked-mini"))) {
    cpSync(join(OUT, "parked-mini"), SIBLING_PARK, { recursive: true })
    console.log(`restored sibling skill: ${SIBLING_PARK}`)
  }
}

// ---------- report ----------
writeFileSync(join(OUT, "results.json"), JSON.stringify({ model: MODEL, trials: TRIALS, results }, null, 2))

const lines = []
lines.push(`# A/B eval — ${new Date().toISOString()} — model=${MODEL} — trials/cell=${TRIALS} — timeout=${TIMEOUT}s`)
lines.push(`confidence: ${TRIALS < 5 ? "LOW (N<5, directional only)" : "per Fisher exact"} | methodology: timed-out cells are budget-invalid (excluded from rates); wall time is a COST metric, not a verdict\n`)
for (const taskId of TASK_FILTER) {
  if (!TASKS[taskId]) continue
  const cells = results.filter((r) => r.task == taskId)
  const done = (arm) => cells.filter((r) => r.arm === arm && !r.timedOut)
  const all = (arm) => cells.filter((r) => r.arm === arm)
  lines.push(`## task${taskId} ${TASKS[taskId].name}`)
  lines.push(`completion: A=${done("A").length}/${all("A").length} · B=${done("B").length}/${all("B").length} (timed-out = budget-invalid)`)
  const keys = [...new Set(cells.flatMap((r) => Object.keys(r.asserts)))]
  lines.push(`| assertion (completed cells only) | A pass | B pass |`)
  lines.push(`|---|---|---|`)
  for (const k of keys) {
    const a = done("A"), b = done("B")
    const ap = a.filter((r) => r.asserts[k]).length
    const bp = b.filter((r) => r.asserts[k]).length
    lines.push(`| ${k} | ${ap}/${a.length} | ${bp}/${b.length} |`)
  }
  const aAll = done("A").filter((r) => r.pass === r.total).length
  const bAll = done("B").filter((r) => r.pass === r.total).length
  const na = done("A").length, nb = done("B").length
  const p = (na && nb) ? fisher(bAll, nb - bAll, aAll, na - aAll) : null
  const wall = (rs) => rs.length ? (rs.reduce((s, r) => s + parseFloat(r.wall), 0) / rs.length).toFixed(1) : "-"
  const bytes = (rs) => rs.length ? Math.round(rs.reduce((s, r) => s + r.outBytes, 0) / rs.length) : "-"
  lines.push(`\nall-assertions pass (completed only): A=${aAll}/${na} B=${bAll}/${nb}${p !== null ? ` | Fisher one-sided p=${p.toFixed(3)}` : ""} | COST mean wall: A=${wall(done("A"))}s B=${wall(done("B"))}s | mean outBytes: A=${bytes(done("A"))} B=${bytes(done("B"))}\n`)
}
const report = lines.join("\n")
writeFileSync(join(OUT, "report.md"), report)
console.log("\n" + report)
console.log(`\nartifacts: ${OUT}`)
