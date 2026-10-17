import { execFile, execFileSync } from "node:child_process"
import { closeSync, existsSync, fstatSync, lstatSync, mkdirSync, openSync, readdirSync, readFileSync, readlinkSync, realpathSync, renameSync, statSync, writeFileSync } from "node:fs"
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
// .vibeweaver/state.json, atomic writes). Also delivers task memory
// deterministically (wave21): the working note rides the compaction prompt
// (experimental.session.compacting), a resume bundle is injected on the
// first request after every session.compacted, and a one-line pointer
// rides the first gated write of a session. Disable with
// VIBEWEAVER_GATE=off.
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2):
// This module default-exports ONE object { id, server, setup }.
//   - opencode v1 (>= 1.18.29): the loader's readV1Plugin detects the
//     default object and calls server(input, options) -> the v1 hooks
//     map ("tool.execute.after" / "event"). Older v1 releases fall back
//     to iterating exports and also accept an object with a function
//     `server` property — one export means one registration either way.
//   - opencode v2 (>= 2.0.0): the loader's PluginModule schema decodes
//     ONLY the default export against { id, setup } (excess keys like
//     `server` are tolerated) and calls setup(ctx); hooks are registered
//     via ctx.tool.hook("execute.after") and ctx.event.subscribe().
// Both adapters delegate to the SAME logic so behavior is identical
// across versions. Keep exactly this one export: any extra non-function
// export breaks the legacy v1 iterator, any extra plugin-function export
// risks double registration.

const GATED_TOOLS = new Set(["write", "edit"])
const FLAG_COMBOS = [[], ["--existing"], ["--backend-only"], ["--existing", "--backend-only"]]
const STATE_DIR = ".vibeweaver"
const STATE_FILE = "state.json"
const STALL_RUN = 3        // consecutive same-file ops before a stall is worth reporting
const MAX_OPS = 20         // history kept per project
const ASSERT_TIMEOUT_MS_DEFAULT = 15000
function assertTimeoutMs() {
  const n = Number(process.env.VIBEWEAVER_ASSERT_TIMEOUT_MS)
  return Number.isFinite(n) && n > 0 ? n : ASSERT_TIMEOUT_MS_DEFAULT
}
// D5 (2026-10-15, BLINDSPOTS BL-2): assert results are cached against a
// DEPENDENCY-SET fingerprint — the script, the evidence/log/acceptance/
// working-note files, memory/, and the git anchors. Any input change
// re-keys the cache; nothing else can serve a stale verdict (a script-only
// key would swallow new failures = fail-open).
const RESULT_CACHE = new Map()
const RESULT_CACHE_MAX = 32
// Review B4 (A4.9): a verdict that only passed under a lenient flag combo
// (--existing / --backend-only) is surfaced ONCE per project+flags — the
// combo sweep is how the gate copes with unknown task type (strict is tried
// first), but a lenient-only pass must be visible, never silent.
const LENIENT_NOTED = new Set()

function depFingerprint(root) {
  const parts = [root]
  const add = (p) => {
    try {
      const st = statSync(p)
      parts.push(`${st.size}@${st.mtimeMs}`)
    } catch {
      parts.push("-")
    }
  }
  const addDirRecursive = (dir, depth) => {
    try {
      for (const f of readdirSync(dir).sort()) {
        const p = path.join(dir, f)
        let st
        try {
          st = statSync(p)
        } catch {
          continue
        }
        if (st.isDirectory()) {
          if (depth > 0) addDirRecursive(p, depth - 1)
        } else {
          add(p)
        }
      }
    } catch {
      parts.push("~")
    }
  }
  add(path.join(root, "tests", "assert_artifacts.py"))
  add(path.join(root, "tests", "verification_log.md"))
  add(path.join(root, "tests", "acceptance.md"))
  add(path.join(root, "tests", "working_note.md"))
  add(path.join(root, "tests", "project_profile.json"))
  add(path.join(root, "tests", "review_package.md"))
  addDirRecursive(path.join(root, "tests"), 3)
  addDirRecursive(path.join(root, "memory"), 2)
  addDirRecursive(path.join(root, "script"), 3)
  add(path.join(root, ".git", "HEAD"))
  add(path.join(root, ".git", "index"))
  return parts.join("|") + "\n" + gitDigest(root)
}

// Review A1 (A4.9): the content gates (groups 14/15/16/17) read `git diff
// HEAD` + untracked files — the cache key MUST see that surface or a cached
// green verdict silently outlives a wave-diff change (a newly written source
// file or untracked .env would never re-run the secret scan). Digest = the
// porcelain status listing + a stat of every dirty/untracked path.
function gitDigest(root) {
  try {
    const out = execFileSync("git", ["status", "--porcelain"], { cwd: root, encoding: "utf8", timeout: 2000, stdio: ["ignore", "pipe", "pipe"] })
    const parts = [out]
    const statOne = (p, prefix, depth = 0) => {
      const abs = path.join(root, p)
      let s
      try {
        s = statSync(abs)
      } catch {
        parts.push(`${prefix}${p}:-`)
        return
      }
      if (s.isDirectory()) {
        // re-review R1: porcelain collapses fully-untracked dirs to `?? dir/`
        // — content edits INSIDE the dir never move the dir mtime, yet group
        // 14 scans those files. Walk (bounded) and stat the entries. Depth
        // cap (2026-10-17 SIGTRAP hardening): the cache-key walk must never
        // recurse without a bound — PATH_MAX stops pathological trees in
        // practice, but the contract is the bound, not the OS.
        if (depth >= 24) {
          parts.push(`${prefix}${p}:…`)
          return
        }
        try {
          const entries = readdirSync(abs).sort().slice(0, 200)
          for (const e of entries) statOne(path.join(p, e), prefix, depth + 1)
        } catch {
          parts.push(`${prefix}${p}:~`)
        }
      } else {
        parts.push(`${prefix}${p}:${s.size}@${s.mtimeMs}`)
      }
    }
    for (const line of out.split("\n")) {
      const raw = line.slice(3).trim().replace(/^"|"$/g, "")
      if (!raw) continue
      const p = raw.includes("->") ? raw.split("->").pop().trim() : raw
      // harness state is not evidence — its churn (stall observer rewrites)
      // must not defeat the result cache (re-review R6)
      if (p === ".vibeweaver" || p.startsWith(".vibeweaver/")) continue
      statOne(p, "")
    }
    return parts.join("\n")
  } catch {
    return "no-git"
  }
}

function sizeOf(p) {
  try {
    return statSync(p).size
  } catch {
    return 0
  }
}

// Bounded reader (class contract, 2026-10-17 — Bun #26323: readFileSync on a
// >2GB file is an uncatchable SIGTRAP in the runtime opencode bundles):
// refuse by SIZE before any read; a bigger file is treated as absent.
const READ_CAP = 64 * 1024 * 1024

function safeRead(p, cap = READ_CAP) {
  let fd = null
  try {
    fd = openSync(p, "r")
    const s = fstatSync(fd).size
    if (!(s > 0) || s > cap) return ""
    return readFileSync(fd, "utf8")
  } catch {
    return ""
  } finally {
    if (fd !== null) {
      try {
        closeSync(fd)
      } catch {
        /* never crash on close */
      }
    }
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

// D4 (2026-10-15, PLAN §2 D4): fail-closed — "the check could not run" is
// itself a BLOCK, never a pass (METR Hawk: fail loudly / deny by default).
// The old keyword classifier (BLOCKING_HINTS) let hint-free failures through;
// every real failure line now blocks, and the run itself is validated:
//   python missing · timeout · crash · placeholder/stub -> BLOCK.
// Interpreter resolution (2026-10-17 CI): windows ships `python`, POSIX
// `python3`, and `python3` there can be the Windows-Store stub — probe once
// and cache; VIBEWEAVER_PYTHON overrides.
let _pyExe = null
let _pyProbed = false
function resolvePython() {
  if (_pyProbed) return _pyExe
  _pyProbed = true
  const cands = []
  if (process.env.VIBEWEAVER_PYTHON) cands.push(process.env.VIBEWEAVER_PYTHON)
  if (process.platform === "win32") cands.push("python", "python3", "py")
  else cands.push("python3", "python")
  for (const c of cands) {
    try {
      execFileSync(c, ["--version"], { encoding: "utf8", timeout: 10000, stdio: ["ignore", "pipe", "pipe"] })
      _pyExe = c
      return c
    } catch {
      /* next */
    }
  }
  return "python3"
}

function runPython(script, flags, cwd) {
  return new Promise((resolve) => {
    execFile(resolvePython(), [script, ...flags], { cwd, encoding: "utf8", timeout: assertTimeoutMs(), maxBuffer: 2 << 20 }, (err, stdout, stderr) => {
      resolve({ err: err || null, stdout: stdout || "", stderr: stderr || "" })
    })
  })
}

function parseAssertJson(stdout) {
  const m = /\{[\s\S]*\}/.exec(stdout || "")
  if (!m) return null
  try {
    const j = JSON.parse(m[0])
    if (j && typeof j.ok === "boolean") return j
  } catch {
    /* not our JSON */
  }
  return null
}

async function runAssert(root) {
  const script = path.join(root, "tests", "assert_artifacts.py")
  const attempts = []
  let jsonSupported = true
  for (const flags of FLAG_COMBOS) {
    const argv = jsonSupported ? ["--json", ...flags] : flags
    const { err, stdout, stderr } = await runPython(script, argv, root)
    const out = `${stdout}${stderr ? "\n" + stderr : ""}`.trim()
    const label = argv.join(" ") || "(none)"
    if (/unrecognized arguments/.test(out)) {
      // A copy without --json (BL-3) falls back to prose mode ONCE — still
      // fail-closed on its output. A copy that rejects the OTHER canonical
      // flags is not a usable check at all (placeholder class) → BLOCK.
      if (jsonSupported && /--json/.test(out)) {
        jsonSupported = false
        attempts.push({ flags: label, output: "legacy script without --json — prose mode", terminal: "legacy" })
        continue
      }
      attempts.push({ flags: label, output: out, terminal: "placeholder" })
      continue
    }
    const json = parseAssertJson(stdout)
    if (!err) {
      if (json) {
        if (json.ok) return { ok: true, flags: label, output: out, attempts }
        attempts.push({ flags: label, output: out, fails: Array.isArray(json.fails) ? json.fails : [] })
      } else if (/assert_artifacts\.py: all \d+ checks pass/.test(out)) {
        return { ok: true, flags: label, output: out, attempts }
      } else {
        // exit 0 with no canonical success shape = placeholder/stub script
        attempts.push({ flags: label, output: out || "(no output)", terminal: "placeholder" })
      }
      continue
    }
    const timedOut = Boolean(err.killed) || err.code === "ETIMEDOUT"
    const noPython = err.code === "ENOENT"
    const crashed = /Traceback \(most recent call last\)/.test(out)
    if (json) {
      attempts.push({ flags: label, output: out, fails: Array.isArray(json.fails) ? json.fails : [] })
      continue
    }
    const ranAndFailed = !noPython && !timedOut && !crashed && (/ASSERT FAILURES/.test(out) || /^\s{0,2}- /m.test(out))
    if (ranAndFailed) {
      attempts.push({ flags: label, output: out })
      continue
    }
    attempts.push({
      flags: label,
      output: out || String(err.code || err.signal || "unknown"),
      terminal: noPython ? "python-missing" : timedOut ? "timeout" : crashed ? "crash" : "placeholder",
    })
  }
  return { ok: false, attempts }
}

// Fail-closed message collection: everything the assert script failed on
// BLOCKS; only explicit WARN lines and JSON severity:"warn" items stay
// advisory. Terminal (unrunnable-check) attempts always block.
const TERMINAL_MESSAGES = {
  "python-missing": "verification check could not run — python3 is not available (fail-closed: an unverifiable task is not a passing task)",
  timeout: "verification check timed out (fail-closed) — tests/assert_artifacts.py exceeded the gate timeout; fix or split the check",
  crash: "verification check crashed (fail-closed) — tests/assert_artifacts.py raised; fix the script or the fixtures it reads",
  placeholder: "verification check is a placeholder/stub (fail-closed) — it exited without the canonical result shape; copy the real tests/assert_artifacts.py from the vibeweaver skill's scripts/",
  legacy: "tests/assert_artifacts.py is a legacy copy without --json — upgrade from the skill's scripts/assert_artifacts.py (the gate still fails closed on its prose output)",
}

function collectMessages(attempts) {
  const blocking = []
  const warnings = []
  const seen = new Set()
  const push = (arr, msg) => {
    if (!msg || seen.has(msg)) return
    seen.add(msg)
    arr.push(msg)
  }
  for (const a of attempts) {
    if (a.terminal) {
      // "legacy" is an upgrade hint (the check still ran in prose mode below);
      // every other terminal means the check could NOT run → block.
      if (a.terminal === "legacy") push(warnings, TERMINAL_MESSAGES.legacy)
      else push(blocking, TERMINAL_MESSAGES[a.terminal] || `verification check unavailable (${a.terminal})`)
      continue
    }
    if (Array.isArray(a.fails) && a.fails.length) {
      for (const f of a.fails) {
        const detail = f && typeof f === "object" ? String(f.detail ?? f.code ?? f) : String(f)
        if (f && typeof f === "object" && f.severity === "warn") push(warnings, detail)
        else push(blocking, detail)
      }
      continue
    }
    for (const line of String(a.output || "").split("\n")) {
      const m = line.trim()
      if (m.startsWith("WARN ")) push(warnings, m.slice(5))
      else if (m.startsWith("- ")) push(blocking, m.slice(2))
    }
  }
  if (!blocking.length && !warnings.length && attempts.length) {
    push(blocking, attempts[attempts.length - 1].output.slice(0, 400))
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

async function checkGate(root) {
  const assertsPath = path.join(root, "tests", "assert_artifacts.py")
  if (existsSync(assertsPath)) {
    const key = depFingerprint(root)
    if (RESULT_CACHE.has(key)) return RESULT_CACHE.get(key) // may be null = cached PASS
    const r = await runAssert(root)
    let result
    if (r.ok) {
      if (RESULT_CACHE.size >= RESULT_CACHE_MAX) RESULT_CACHE.clear()
      RESULT_CACHE.set(key, null) // cache the CLEAN verdict (the note is out-of-band)
      const flags = r.flags || ""
      if (flags && flags !== "(none)") {
        const noteKey = root + "|" + flags
        if (!LENIENT_NOTED.has(noteKey)) {
          LENIENT_NOTED.add(noteKey)
          if (LENIENT_NOTED.size > 64) LENIENT_NOTED.clear()
          return {
            blocking: [],
            warnings: [
              `assert_artifacts.py passed only under ${flags} — the strict run reported: ${((r.attempts && r.attempts[0] && String(r.attempts[0].output).split("\n")[0]) || "failures").slice(0, 120)} (expected for Modify-Existing/backend tasks; suspicious for new projects)`,
            ],
          }
        }
      }
      return null
    }
    {
      const { blocking, warnings } = collectMessages(r.attempts)
      result = { blocking, warnings, attempts: r.attempts.map((a) => `[${a.flags}]`) }
    }
    if (RESULT_CACHE.size >= RESULT_CACHE_MAX) RESULT_CACHE.clear()
    RESULT_CACHE.set(key, result)
    return result
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
        st = JSON.parse(safeRead(p) || "null")
      } catch {
        st = { ops: [] }
      }
    }
    if (!st || typeof st !== "object" || Array.isArray(st)) st = {}
    if (!Array.isArray(st.ops)) st.ops = []
    st.ops.push({ f: file, p: countPasses(root), t: Date.now() })
    if (st.ops.length > MAX_OPS) st.ops = st.ops.slice(-MAX_OPS)
    const run = st.ops.slice(-STALL_RUN)
    let msg = null
    if (run.length >= STALL_RUN) {
      const sameFile = run.every((o) => o.f === run[0].f)
      const noNewPass = run[0].p === run[run.length - 1].p
      if (sameFile && noNewPass) {
        // latch: fire ONCE per (file, pass-count) signature — re-firing on
        // every later edit is alarm flood and trains warning-blindness. A
        // new PASS changes the signature and re-arms the observer.
        const firedKey = `${run[0].f}@${run[0].p}`
        if (st.firedKey !== firedKey) {
          st.firedKey = firedKey
          msg = `STALL observed (machine-counted): "${run[0].f}" modified ${STALL_RUN}x with no new "iter N PASS" entry in tests/verification_log.md in between — COV-7 stall=3x is likely reached. Do not retry the same direction: parameterize (finite candidate set + cheapest refuting test) or shift the abstraction/strategy — TESTING_PROTOCOLS.md §A4.10.`
        }
      }
    }
    if (!existsSync(path.join(root, STATE_DIR))) mkdirSync(path.join(root, STATE_DIR), { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(st))
    renameSync(tmp, p)
    return msg
  } catch {
    return null
  }
}

function blockMessage(root, result) {
  const lines = [
    "GATE-BLOCKED (vibeweaver physical gate): WRITE SUCCEEDED — this is a completion gate, NOT an execution stop. The task cannot be DECLARED complete yet — verification evidence is missing or falsified:",
    ...result.blocking.map((m) => "- " + m),
  ]
  if (result.warnings.length) {
    lines.push("Non-blocking structure warnings (fix before the final [Verification Gate] line):")
    lines.push(...result.warnings.map((m) => "- " + m))
  } else {
    lines.push("No structure warnings.")
  }
  if (result.inline) {
    lines.push("tests/assert_artifacts.py is missing — either copy it from the vibeweaver skill's scripts/assert_artifacts.py, or satisfy the inline evidence floor: >=1 `- iter N PASS/FAIL:` entry in tests/verification_log.md, tests/acceptance.md first line `> cap=5  stall=3x`, and every cited screenshot/media file present and non-empty.")
  } else if (result.attempts) {
    lines.push("assert_artifacts.py flag attempts: " + result.attempts.join(" "))
  }
  lines.push("This gate is re-checkable, not a dead stop: fix the artifacts, then your next write/edit re-runs it automatically. If the failure is legitimately out of scope, set VIBEWEAVER_GATE=off or escalate to the user.")
  return lines.join("\n")
}

function isEvidencePath(root, filePath) {
  if (typeof filePath !== "string" || !filePath) return false
  // normalize first (kills `memory/../src/app.js` traversal AND symlinked
  // tests/ dirs pointing outside — realpath of the nearest existing ancestor
  // + lexical basename; D3/BL-7), then anchor the exemption to the FIRST
  // path segment under root — a nested `src/tests/` source file is NOT an
  // evidence path.
  const normRoot = resolveWritePath(root)
  const normFile = resolveWritePath(filePath)
  const rel = path.relative(normRoot, normFile)
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return false
  const seg = rel.split(path.sep)[0].toLowerCase()
  return seg === "test" || seg === "tests" || seg === "memory"
}

// Shared with vibeweaver-audit.js (D3): new write targets may not exist, so
// realpathSync(file) would throw — resolve the nearest EXISTING ancestor
// directory, then re-attach the remaining lexical segments + basename.
function resolveWritePath(filePath, depth = 0) {
  try {
    // Review A2/B2/R2 (A4.9): when the target ITSELF exists and is a symlink
    // (tests/app.js -> ../src/app.js), ancestor-only realpath kept the tests/
    // segment and the write escaped the gate — resolve the whole path.
    if (existsSync(filePath)) {
      try {
        return realpathSync(filePath)
      } catch {
        /* fall through */
      }
    }
    // DANGLING symlink (re-review R2#1): the link exists (lstat) while its
    // target does not yet — the OS write will follow it into the target.
    // Resolve the link target recursively (bounded).
    if (depth < 8) {
      try {
        const st = lstatSync(filePath)
        if (st.isSymbolicLink()) {
          const target = readlinkSync(filePath)
          return resolveWritePath(path.resolve(path.dirname(filePath), target), depth + 1)
        }
      } catch {
        /* not a symlink */
      }
    }
    let rest = []
    let dir = path.dirname(filePath)
    for (;;) {
      if (existsSync(dir)) {
        try {
          dir = realpathSync(dir)
        } catch {
          /* keep lexical dir */
        }
        break
      }
      rest.unshift(path.basename(dir))
      const up = path.dirname(dir)
      if (up === dir) break
      dir = up
    }
    return path.resolve(path.join(dir, ...rest, path.basename(filePath)))
  } catch {
    return path.resolve(filePath)
  }
}

// ---------- cue-anchored memory triggers (§A7.16) ----------

// glob → RegExp: `**/` crosses directories, `*` stays inside a segment,
// `?` matches one non-separator char. Anchored to the project-relative path.
// Sentinels are ESCAPE SEQUENCES, never literal control bytes (D5: the old
// literal NUL/0x01 made ripgrep treat this file as binary).
function globToRegExp(glob) {
  let g = String(glob)
  g = g.replace(/[.+^${}()|[\]\\]/g, "\\$&")
  g = g.replace(/\*\*\//g, "\u0000")
  g = g.replace(/\*\*/g, "\u0001")
  g = g.replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]")
  g = g.replace(/\u0000/g, "(?:.*/)?").replace(/\u0001/g, ".*")
  return new RegExp("^" + g + "$")
}

// Parse a memory topic's frontmatter `triggers:` field — inline form
// `triggers: ["a/**", "b/**"]`, list form (any indent):
//   triggers:
//     - "a/**"
// and the scalar form `triggers: src/auth/**`. Returns [] when
// absent/unparseable (a trigger-less topic never cues).
function parseTriggers(fm) {
  const out = []
  const lines = fm.split("\n")
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^triggers:\s*(.*)$/)
    if (!m) continue
    const rest = m[1].trim()
    if (rest.startsWith("[")) {
      const inner = rest.replace(/^\[/, "").replace(/\]\s*$/, "")
      for (const part of inner.split(",")) {
        const v = part.trim().replace(/^["']|["']$/g, "")
        if (v) out.push(v)
      }
    } else if (!rest) {
      for (let j = i + 1; j < lines.length; j++) {
        const li = lines[j].match(/^\s*-\s+["']?([^"']+?)["']?\s*(?:#.*)?$/)
        if (!li) break
        out.push(li[1])
      }
    } else {
      const scalar = rest.replace(/["']/g, "").replace(/\s+#.*$/, "").trim()
      if (scalar) out.push(scalar)
    }
    break
  }
  return out
}

// Delivery-safety caps: memory topics are agent-authored text that gets
// COMPILED TO REGEX and executed synchronously in the write hook — a hostile
// or careless glob (repeated `**/` → combinatorial backtracking) would wedge
// the event loop. D5 budget (2026-10-15): pattern length ≤64, `*` count ≤2,
// `**` groups ≤2 (redundant with the star cap, kept as the direct ReDoS
// bound), no control chars (they double as internal sentinel bytes). The
// per-call match budget is enforced by the caller (cueNotes).
function safeGlob(t) {
  return (
    typeof t === "string" &&
    t.length > 0 &&
    t.length <= 64 &&
    !/[\x00-\x1f]/.test(t) &&
    (t.match(/\*/g) || []).length <= 2 &&
    (t.match(/\*\*/g) || []).length <= 2
  )
}

// Cue telemetry (wave19): every fire increments .vibeweaver/cue-stats.json
// per topic. Delivery counts are the feedback loop for tuning glob
// precision (a trigger that never fires / fires on everything is noise).
// Best-effort: telemetry must never break delivery.
function recordCueFires(root, notes) {
  try {
    const dir = path.join(root, STATE_DIR)
    const p = path.join(dir, "cue-stats.json")
    let stats = {}
    if (existsSync(p)) {
      try {
        stats = JSON.parse(safeRead(p) || "null")
      } catch {
        stats = {}
      }
    }
    if (!stats || typeof stats !== "object") stats = {}
    for (const n of notes) {
      const m = n.match(/memory\/(\S+\.md)/)
      if (m) stats[m[1]] = (typeof stats[m[1]] === "number" ? stats[m[1]] : 0) + 1
    }
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(stats))
    renameSync(tmp, p)
  } catch {
    /* never throws */
  }
}

// One-line cue notes for memory topics whose triggers match the edited
// path. Delivery, not storage: the cue fires at the edit moment, not at
// task-start grep. Budgeted (max 3), progressive (pointer line, not the
// topic body). Never throws.
function cueNotes(root, filePath) {
  try {
    if (typeof filePath !== "string" || !filePath) return []
    // normalize BOTH sides with the same resolver — a lexical root vs a
    // realpath'd file (macOS /tmp → /private/tmp) yields a `..` relative
    // path and silently dropped every cue (D5 review).
    const rel = path.relative(resolveWritePath(root), resolveWritePath(filePath))
    if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return []
    if (rel.split(path.sep)[0].toLowerCase() === "memory") return []
    const memDir = path.join(root, "memory")
    if (!existsSync(memDir)) return []
    const relPosix = rel.split(path.sep).join("/")
    const notes = []
    // D5 match budget: total regex-matching time per write is capped at 50ms;
    // when it runs out the remaining triggers are skipped and the skip is
    // reported (a dropped cue is visible, never silent).
    const startedAt = Date.now()
    let budgetSkipped = 0
    outer: for (const f of readdirSync(memDir).sort()) {
      if (!f.endsWith(".md") || f === "MEMORY.md") continue
      const text = safeRead(path.join(memDir, f)).replace(/\r\n/g, "\n").replace(/^\uFEFF/, "")
      const fm = text.match(/^---\n([\s\S]*?)\n---/)
      if (!fm) continue
      const triggers = parseTriggers(fm[1]).filter(safeGlob)
      if (!triggers.length) continue
      let hit = false
      for (const t of triggers) {
        if (Date.now() - startedAt > 50) {
          budgetSkipped++
          break outer
        }
        try {
          if (globToRegExp(t).test(relPosix)) {
            hit = true
            break
          }
        } catch {
          /* a bad glob never breaks delivery */
        }
      }
      if (!hit) continue
      const trust = (fm[1].match(/^(?:trust|status):\s*(\S+)/m) || [])[1] || "?"
      const heading = (text.match(/^#\s+(.+)$/m) || [])[1] || f
      notes.push(`[GATE-WARNING (vibeweaver-cue)] memory cue: memory/${f} (${trust}) matches this path — read it before editing: ${heading}`)
      if (notes.length >= 3) break
    }
    if (budgetSkipped) {
      notes.push(`[GATE-WARNING (vibeweaver-cue)] memory-trigger matching hit its 50ms budget — ${budgetSkipped} trigger pattern(s) skipped unexamined (D5 glob budget; tighten the trigger globs)`)
    }
    if (notes.length) recordCueFires(root, notes)
    return notes
  } catch {
    return []
  }
}

// ---------- deterministic memory delivery: compaction-resume (wave21) ----------
//
// Delivery, not storage (2607.20972 + Graepel epistemic-state ledger): the
// working note (§A7.15) is task state, but relying on the model to read it
// back after a compaction is the voluntary channel — measured to round to
// zero. The harness owns the context window, so the harness delivers:
//   1. pre-summary: the working note (+ resume rule) is pushed into the
//      compaction prompt's context, so the summary carries the ledger;
//   2. post-compaction: the first model request after a `session.compacted`
//      event gets a synthetic message with the SAME bundle (fire ledger =
//      one delivery per compaction, re-armed by the next compacted event);
//   3. session start proxy: the first gated write of a session carries a
//      one-line resume pointer (note exists -> read it first; active task
//      without a note -> create it).
// All three are no-ops outside vibeweaver-active projects (no
// tests/verification_log.md) and never throw into the host.

const MEMORY_BUNDLE_MAX = 4096
const MEMORY_STATE_CAP = 500

const SESSION_MEM = {
  pendingResume: new Set(), // sessionIDs: a compaction happened, inject on that session's next system transform
  firstCue: new Set(), // `${root}:${sessionID}`: session-start pointer already delivered
}

function capBounded(set) {
  if (set.size > MEMORY_STATE_CAP) {
    const first = set.values().next().value
    set.delete(first)
  }
}

function workingNoteOf(root) {
  return safeRead(path.join(root, "tests", "working_note.md")).replace(/\r\n/g, "\n")
}

const SNAPSHOT_FILE = "memory-snapshot.json"

// Harness-owned copy of the working note (wave24): delivery must survive the
// source file disappearing. Snapshot is refreshed whenever the source exists;
// once the source is gone the snapshot IS the memory (the paper's
// deleted-fixture regime made locally testable).
function snapshotWorkingNote(root) {
  try {
    const rel = path.join("tests", "working_note.md")
    const text = workingNoteOf(root)
    if (!text.trim()) return
    const p = path.join(root, STATE_DIR, SNAPSHOT_FILE)
    if (!existsSync(path.join(root, STATE_DIR))) mkdirSync(path.join(root, STATE_DIR), { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify({ rel, text: text.slice(0, MEMORY_BUNDLE_MAX), t: Date.now() }))
    renameSync(tmp, p)
  } catch {
    /* snapshot is best-effort; delivery still works while the file lives */
  }
}

function snapshotTextOf(root) {
  try {
    const p = path.join(root, STATE_DIR, SNAPSHOT_FILE)
    if (!existsSync(p)) return ""
    const d = JSON.parse(safeRead(p) || "null")
    return typeof d.text === "string" ? d.text : ""
  } catch {
    return ""
  }
}

// The delivered bundle: working note verbatim (bounded) + resume rule. With
// no note, deliver the create instruction instead — the boundary is exactly
// the moment the ledger matters most.
function compactStateBundle(root) {
  let note = workingNoteOf(root).trim()
  let fromSnapshot = false
  if (note) {
    snapshotWorkingNote(root)
  } else {
    note = snapshotTextOf(root).trim()
    fromSnapshot = !!note
  }
  if (note && fromSnapshot) {
    return [
      "VIBEWEAVER WORKING-STATE (harness snapshot — the source tests/working_note.md is no longer present; this copy is authoritative):",
      note.slice(0, MEMORY_BUNDLE_MAX - 400),
      "Resume rule: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md BEFORE the next edit; the working note lives in this harness snapshot now.",
    ].join("\n")
  }
  if (!note) {
    const acc = safeRead(path.join(root, "tests", "acceptance.md"))
    const capLine = (acc.split("\n").find((l) => l.includes("cap=5")) || "").trim()
    return [
      "VIBEWEAVER COMPACT-RESUME (machine-delivered by vibeweaver-gate — no tests/working_note.md exists):",
      "After this compaction, BEFORE the next edit: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md, and CREATE tests/working_note.md (§A7.15 hypothesis ledger: confirmed/doubted/excluded/open + key locations + dead ends + next action, <=50 lines). The gate re-delivers this note at every compaction boundary.",
      capLine ? `Acceptance first line: ${capLine}` : "",
    ]
      .filter(Boolean)
      .join("\n")
      .slice(0, MEMORY_BUNDLE_MAX)
  }
  return [
    "VIBEWEAVER WORKING-STATE (machine-delivered by vibeweaver-gate; this ledger is task state and takes precedence over the compacted summary — preserve its essentials):",
    note.slice(0, MEMORY_BUNDLE_MAX - 400),
    "Resume rule: after compaction re-read tests/working_note.md, tests/acceptance.md, and the last 20 lines of tests/verification_log.md BEFORE the next edit.",
  ].join("\n")
}

function resumeCueNote(root) {
  const exists = workingNoteOf(root).trim().length > 0
  if (exists) {
    return "[vibeweaver] tests/working_note.md exists (task state ledger) — read it first (§3.3 re-entry); the gate re-delivers it at every compaction boundary."
  }
  if (existsSync(path.join(root, "tests", "acceptance.md"))) {
    return "[vibeweaver] active task detected without tests/working_note.md — create it (§A7.15); the gate delivers it deterministically at every compaction boundary."
  }
  return null
}

// Telemetry (bounded, best-effort): counts of deterministic deliveries into
// .vibeweaver/state.json — the feedback loop for "is the mechanism firing?".
function recordMemoryDelivery(root, kind) {
  try {
    const p = path.join(root, STATE_DIR, STATE_FILE)
    let st = {}
    if (existsSync(p)) {
      try {
        st = JSON.parse(safeRead(p) || "null")
      } catch {
        st = {}
      }
    }
    if (!st || typeof st !== "object") st = {}
    const md = st.memoryDeliveries && typeof st.memoryDeliveries === "object" ? st.memoryDeliveries : {}
    md[kind] = (Number(md[kind]) || 0) + 1
    st.memoryDeliveries = md
    if (!existsSync(path.join(root, STATE_DIR))) mkdirSync(path.join(root, STATE_DIR), { recursive: true })
    const tmp = p + ".tmp"
    writeFileSync(tmp, JSON.stringify(st))
    renameSync(tmp, p)
  } catch {
    /* telemetry must never break delivery */
  }
}

// ---------- version-agnostic gate logic ----------

// Evaluate one completed write/edit. Returns:
//   { block: string }                      — caller must throw Error(block)
//   { notes: [string, ...] }               — caller must surface as warnings
//   null                                   — clean
// Ordering mirrors the legacy v1 hook: a blocking result short-circuits
// BEFORE the stall observer records the op (a blocked write is not a
// landed write).
function gateCheckWrite(directory, filePath) {
  if (process.env.VIBEWEAVER_GATE === "off") return Promise.resolve(null)
  const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
  if (!root) return Promise.resolve(null)
  // Cue delivery is hoisted ABOVE the gate: a RED gate (e.g. the task's
  // first write, empty log) is exactly when "read it before editing" must
  // arrive — delivery must never depend on the gate being green.
  const cues = cueNotes(root, filePath)
  // evidence-fix path must never be gated (same rule as the audit
  // plugin): writes under tests/ or memory/ ARE the evidence repair
  // itself — gating them creates the first-log catch-22 deadlock.
  if (isEvidencePath(root, filePath)) return Promise.resolve(cues.length ? { notes: cues } : null)
  return checkGate(root).then((result) => {
    if (result && result.blocking.length) {
      let msg = blockMessage(root, result)
      if (cues.length) msg += "\n" + cues.join("\n")
      return { block: msg }
    }
    const notes = [...cues]
    if (result && result.warnings.length) {
      notes.push("[GATE-WARNING (vibeweaver)] non-blocking: " + result.warnings.join("; ") + " — fix before the final [Verification Gate] line.")
    }
    const stall = stallObservation(root, filePath || "(unknown file)")
    if (stall) notes.push("[GATE-WARNING (vibeweaver-stall)] " + stall)
    return notes.length ? { notes } : null
  })
}

// Session-idle re-check: returns { blocking } when the gate is RED.
function gateIdleCheck(directory) {
  if (process.env.VIBEWEAVER_GATE === "off") return Promise.resolve(null)
  const root = findProjectRoot([directory])
  if (!root) return Promise.resolve(null)
  return checkGate(root).then((result) => {
    if (result && result.blocking.length) return { blocking: result.blocking }
    return null
  })
}

// Host logging: v1 offers client.app.log({ body }); v2's ctx.app is
// {name, version, channel} (no log API) — fall back to stderr. Never
// throws: logging must never break the gate.
async function logToHost(appLike, entry) {
  try {
    if (appLike && typeof appLike.log === "function") {
      await appLike.log({ body: entry })
      return
    }
  } catch {
    /* fall through to stderr */
  }
  try {
    console.error(`[${entry.service}] ${entry.level}: ${entry.message}`)
  } catch {
    /* never crash */
  }
}

// Append warning notes to a v2 tool result (Tool.Result =
// { output?, content?: string | Content[], metadata? }). Content is the
// model-visible channel; metadata is the fallback. In-place mutation first
// (a host that captured the result reference before dispatch still sees the
// note); reassignment as the fallback for frozen/readonly results.
function appendNotesToV2Result(event, notes) {
  const text = notes.join("\n")
  const result = event.result
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
    if (result.metadata && typeof result.metadata === "object") {
      result.metadata.vibeweaverGate = text
      return
    }
    result.metadata = { vibeweaverGate: text }
    return
  } catch {
    /* readonly/frozen result — fall back to reassignment */
  }
  try {
    if (typeof result.content === "string") {
      event.result = { ...result, content: result.content + "\n" + text }
    } else if (Array.isArray(result.content)) {
      event.result = { ...result, content: [...result.content, { type: "text", text }] }
    } else {
      event.result = { ...result, metadata: { ...(result.metadata || {}), vibeweaverGate: text } }
    }
  } catch {
    /* fully-frozen event — a cue note must never break a landed write */
  }
}

// v2 idle detection: v1 emits "session.idle"; v2 emits "session.status"
// with data { sessionID, status: { type: "idle" | "busy" | "retry" } }.
function v2EventIsIdle(event) {
  if (!event || event.type !== "session.status") return false
  const data = event.data
  return !!data && !!data.status && data.status.type === "idle"
}

// Session-start proxy: exactly one resume pointer per project per process.
function firstTouchCue(directory, sessionID) {
  try {
    const root = findProjectRoot([directory])
    if (!root) return null
    const key = `${root}:${sessionID || "(session)"}`
    if (SESSION_MEM.firstCue.has(key)) return null
    const note = resumeCueNote(root)
    if (!note) return null
    snapshotWorkingNote(root) // capture before any deletion window
    SESSION_MEM.firstCue.add(key)
    capBounded(SESSION_MEM.firstCue)
    recordMemoryDelivery(root, "sessionCue")
    return note
  } catch {
    return null
  }
}

// ---------- opencode v1 adapter ----------

async function server({ client, directory }) {
  return {
    "tool.execute.after": async (input, output) => {
      if (!GATED_TOOLS.has(input.tool)) return
      const filePath = input.args && typeof input.args.filePath === "string" ? input.args.filePath : null
      const r = await gateCheckWrite(directory, filePath)
      if (r && r.block) throw new Error(r.block)
      if (r && r.notes) {
        for (const note of r.notes) {
          output.output = (output.output ? output.output + "\n" : "") + note
        }
      }
      const cue = firstTouchCue(directory, input && input.sessionID)
      if (cue) output.output = (output.output ? output.output + "\n" : "") + cue
    },
    "experimental.session.compacting": async (input, output) => {
      if (process.env.VIBEWEAVER_GATE === "off") return
      const root = findProjectRoot([directory])
      if (!root) return
      try {
        output.context = output.context || []
        output.context.push(compactStateBundle(root))
        recordMemoryDelivery(root, "compactContext")
      } catch {
        /* delivery must never break compaction */
      }
    },
    "experimental.chat.system.transform": async (input, output) => {
      if (process.env.VIBEWEAVER_GATE === "off") return
      const sid = input && typeof input.sessionID === "string" ? input.sessionID : null
      if (!sid || !SESSION_MEM.pendingResume.has(sid)) return
      const root = findProjectRoot([directory])
      if (!root) return
      try {
        if (Array.isArray(output.system)) {
          output.system.push(compactStateBundle(root))
          SESSION_MEM.pendingResume.delete(sid) // consume only after a successful push (I2)
          recordMemoryDelivery(root, "compactResume")
        }
      } catch {
        /* one bad transform must not break the request */
      }
    },
    event: async ({ event }) => {
      if (event && event.type === "session.compacted") {
        // v1 event envelope carries `properties`; v2 uses `data` — accept both
        const payload = (event.data || event.properties) || {}
        const sid = typeof payload.sessionID === "string" ? payload.sessionID : null
        if (sid) {
          SESSION_MEM.pendingResume.add(sid)
          capBounded(SESSION_MEM.pendingResume)
        }
        return
      }
      if (!event || event.type !== "session.idle") return
      const r = await gateIdleCheck(directory)
      if (r) {
        await logToHost(client && client.app, {
          service: "vibeweaver-gate",
          level: "warn",
          message: "Session idle with RED verification gate",
          extra: { blocking: r.blocking },
        })
      }
    },
  }
}

// ---------- opencode v2 adapter ----------

async function setup(ctx) {
  const directory = ctx && ctx.location && typeof ctx.location.directory === "string" ? ctx.location.directory : null
  const hasV2Apis = !!(ctx && ctx.tool && typeof ctx.tool.hook === "function" && ctx.event && typeof ctx.event.subscribe === "function")
  if (!directory || !hasV2Apis) {
    // opencode v1's hybrid bridge calls setup() with a partial context (no
    // location/tool/event domains) — that is EXPECTED there and the v1 server
    // adapter provides the gate, so stay silent. Warn only when a location IS
    // present (a genuine v2 host missing hook/event APIs — worth surfacing).
    if (directory && !hasV2Apis) {
      console.warn("[vibeweaver-gate] v2 setup: ctx.tool.hook/ctx.event.subscribe unavailable in this host — v2 adapter inactive for this instance")
    }
    return
  }
  const registrations = []
  const registration = await ctx.tool.hook("execute.after", async (event) => {
    if (!event || !GATED_TOOLS.has(event.tool)) return
    // v1 parity: tool.execute.after fires only for successful executions.
    if (event.status !== "completed") return
    const input = event.input
    const filePath = input && typeof input === "object" && typeof input.filePath === "string" ? input.filePath : null
    const r = await gateCheckWrite(directory, filePath)
    if (r && r.block) throw new Error(r.block)
    if (r && r.notes) appendNotesToV2Result(event, r.notes)
    const cue = firstTouchCue(directory)
    if (cue) appendNotesToV2Result(event, [cue])
  })
  registrations.push(registration)
  // v2 memory delivery: intentionally NOT registered here. The shipped
  // @opencode-ai/plugin v2 context has no session domain (verified
  // 1.18.35), and 1.18.x's hybrid loader delivers through the v1 hooks
  // above. Register compact/resume hooks in a guarded block only once a
  // real v2 host exposes them (do not ship guessed shapes — wave21 r1).
  const controller = new AbortController()
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          if (event && event.type === "session.compacted") {
            const payload = (event.data || event.properties) || {}
            const sid2 = typeof payload.sessionID === "string" ? payload.sessionID : null
            if (sid2) {
              SESSION_MEM.pendingResume.add(sid2)
              capBounded(SESSION_MEM.pendingResume)
            }
          }
          if (!v2EventIsIdle(event)) continue
          const r = await gateIdleCheck(directory)
          if (r) {
            await logToHost(null, {
              service: "vibeweaver-gate",
              level: "warn",
              message: "Session idle with RED verification gate",
              extra: { blocking: r.blocking },
            })
          }
        } catch {
          /* one bad event must not kill the idle re-check */
        }
      }
    } catch {
      /* stream closed/aborted — idle re-check is advisory, never crash */
    }
  })()
  return () => {
    controller.abort()
    for (const reg of registrations) {
      try {
        if (reg && typeof reg.dispose === "function") void reg.dispose()
      } catch {
        /* disposal best-effort; the v2 host also scopes registrations to the plugin */
      }
    }
  }
}

export default {
  id: "vibeweaver-gate",
  server,
  setup,
}
