import { execFile, execFileSync } from "node:child_process"
import { createHash } from "node:crypto"
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
// 2026-10-18 incident: a pnpm store committed by `git add -A` left 45k
// untracked paths; the old recursive digest stat'ed them on every write and
// the 15s assert timeout turned each write into GATE-BLOCKED. The digest is
// a cache key, not a scan: bound paths/time and return a lossy (uncached) key
// (never `no-git`, which silently disabled the gate).
const GIT_DIGEST_MAX_PATHS = 2000
const GIT_DIGEST_MAX_MS = 1500
const GIT_DIGEST_MAX_DEPTH = 12
const GIT_DIGEST_MAX_BUFFER = 8 << 20
// A lossy digest MUST NOT feed the result cache: overflow/timeout/depth
// truncation would otherwise freeze a green verdict while content changes.
const LOSSY_DIGEST = new Set()
const LOSSY_FINGERPRINT = new Set()
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
  LOSSY_FINGERPRINT.delete(root)
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
  // Group 14 now scans ignored secret-named files; the cache key MUST see
  // their content churn or a clean .env can freeze a PASS (and clearing a
  // leaked .env can freeze the BLOCK). Bounded: depth 4, 200 entries.
  const secretRe = /(^\.env($|\.)|\.(pem|key|crt)$|^config\.local\.)/i
  const secretSkip = new Set([".git", ".vibeweaver", "node_modules", ".pnpm-store",
    ".venv", "venv", "site-packages", "__pycache__", "dist", "build", "target",
    "coverage", ".next", ".nuxt", ".cache", "Library", "ms-playwright",
    "playwright-report", "test-results"])
  let secretSeen = 0
  const addSecretStats = (dir, depth) => {
    if (depth > 4 || secretSeen > 200) {
      LOSSY_FINGERPRINT.add(root)
      return
    }
    let entries
    try {
      entries = readdirSync(dir, { withFileTypes: true })
    } catch {
      parts.push("secret:~")
      LOSSY_FINGERPRINT.add(root)
      return
    }
    for (const e of entries) {
      if (secretSeen++ > 200) {
        LOSSY_FINGERPRINT.add(root)
        return
      }
      const p = path.join(dir, e.name)
      if (e.isDirectory()) {
        if (depth >= 4) {
          LOSSY_FINGERPRINT.add(root)
        } else if (!secretSkip.has(e.name)) {
          addSecretStats(p, depth + 1)
        }
      } else if (secretRe.test(e.name)) {
        try {
          const st = statSync(p)
          parts.push(`secret:${path.relative(root, p)}:${st.size}@${st.mtimeMs}`)
        } catch {
          parts.push(`secret:${path.relative(root, p)}:-`)
        }
      }
    }
  }
  addSecretStats(root, 0)
  add(path.join(root, ".git", "HEAD"))
  add(path.join(root, ".git", "index"))
  // Content hashes for the verdict inputs: size@mtime can collide on a
  // same-size rewrite within one mtime tick, and cache invalidation is a
  // security boundary (W0 Task 2.5/2 step 6).
  for (const rel of ["tests/verification_log.md", "tests/acceptance.md",
    "tests/project_profile.json", "tests/working_note.md", "tests/.evidence.lock",
    "tests/gate_result.json", "tests/debt_baseline.json"]) {
    const p = path.join(root, rel)
    try {
      parts.push(`sha:${rel}:${createHash("sha256").update(readFileSync(p)).digest("hex")}`)
    } catch {
      parts.push(`sha:${rel}:-`)
    }
  }
  parts.push(`checker:${checkerDigest(root)}`)
  // --final and mid-task verdicts are different contracts: a lenient mid-task
  // pass must never satisfy the completion gate (W0 Task 2 step 6).
  parts.push(`mode:${process.env.VIBEWEAVER_GATE_FINAL === "1" ? "final" : "mid"}`)
  return parts.join("|") + "\n" + gitDigest(root)
}

// Review A1 (A4.9): the content gates (groups 14/15/16/17) read `git diff
// HEAD` + untracked files — the cache key MUST see that surface or a cached
// green verdict silently outlives a wave-diff change (a newly written source
// file or untracked .env would never re-run the secret scan). Digest = the
// porcelain status listing + a stat of every dirty/untracked path.
function gitDigest(root) {
  let out
  try {
    out = execFileSync("git", ["status", "--porcelain"], {
      cwd: root,
      encoding: "utf8",
      timeout: 2000,
      maxBuffer: GIT_DIGEST_MAX_BUFFER,
      stdio: ["ignore", "pipe", "pipe"],
    })
  } catch (e) {
    // Only a genuinely absent repo/binary is `no-git`; a timeout/overflow is
    // a LOSSY digest and must never serve a cached verdict.
    if (e && e.code === "ENOENT") return "no-git"
    // A non-repo checkout is legitimately no-git; a 128 from a repo that HAS
    // .git (corrupt index/ownership/config) is lossy and must not be cached.
    if (e && e.status === 128 && !existsSync(path.join(root, ".git"))) return "no-git"
    return lossyKey()
  }
  LOSSY_DIGEST.delete(root)
  const started = Date.now()
  const parts = [out]
  let seen = 0
  let overflow = false
  function lossyKey() {
    LOSSY_DIGEST.add(root)
    // Unique per call: forces a re-run and prevents a stale PASS cache hit.
    return "git-digest-lossy:" + Date.now() + ":" + Math.random().toString(16).slice(2)
  }
  const statOne = (p, prefix, depth = 0) => {
    if (overflow) return
    if (seen++ >= GIT_DIGEST_MAX_PATHS || Date.now() - started > GIT_DIGEST_MAX_MS) {
      overflow = true
      return
    }
    const abs = path.join(root, p)
    let s
    try {
      s = statSync(abs)
    } catch {
      parts.push(`${prefix}${p}:-`)
      overflow = true
      return
    }
    if (s.isDirectory()) {
      // re-review R1: porcelain collapses fully-untracked dirs to `?? dir/`
      // — content edits INSIDE the dir never move the dir mtime, so a small
      // dir must still be walked. The global path/time budget above is the
      // bound: a 45k-file tree returns a lossy (uncached) key after 2k paths.
      if (depth >= GIT_DIGEST_MAX_DEPTH) {
        parts.push(`${prefix}${p}:…`)
        overflow = true
        return
      }
      try {
        const entries = readdirSync(abs).sort()
        for (const e of entries) {
          if (overflow) break
          statOne(path.join(p, e), prefix, depth + 1)
        }
      } catch {
        parts.push(`${prefix}${p}:~`)
        overflow = true
      }
    } else {
      parts.push(`${prefix}${p}:${s.size}@${s.mtimeMs}`)
    }
  }
  for (const line of out.split("\n")) {
    if (overflow) break
    const raw = line.slice(3).trim().replace(/^"|"$/g, "")
    if (!raw) continue
    const p = raw.includes("->") ? raw.split("->").pop().trim() : raw
    // harness state is not evidence — its churn (stall observer rewrites)
    // must not defeat the result cache (re-review R6)
    if (p === ".vibeweaver" || p.startsWith(".vibeweaver/")) continue
    statOne(p, "")
  }
  return overflow ? lossyKey() : parts.join("\n")
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

// ---------- checker pin (PLAN W0 Task 2) ----------
// The project copy of tests/assert_artifacts.py is the judge; without a pin an
// agent can replace it with a three-line stub that prints the success shape.
// The canonical digest ships with the skill (`scripts/assert_artifacts.sha256`)
// and is also covered by release/MANIFEST.json. Missing pin = one-release
// warning (legacy projects); mismatch = fail closed. The override is for the
// human host only and is forbidden in CI.
const CHECKER_DIGEST_FILE = "assert_artifacts.sha256"

function sha256File(p) {
  try {
    return createHash("sha256").update(readFileSync(p)).digest("hex")
  } catch {
    return ""
  }
}

function canonicalHome() {
  if (process.env.VIBEWEAVER_HOME) return process.env.VIBEWEAVER_HOME
  const home = process.env.HOME || process.env.USERPROFILE || ""
  return path.join(home, ".config", "opencode", "skills", "vibeweaver")
}

function canonicalChecker() {
  const p = path.join(canonicalHome(), "scripts", "assert_artifacts.py")
  return existsSync(p) ? p : null
}

function readCheckerPin() {
  const p = path.join(canonicalHome(), "scripts", CHECKER_DIGEST_FILE)
  const raw = safeRead(p).trim()
  const m = raw.match(/\b([0-9a-f]{64})\b/i)
  return { path: p, digest: m ? m[1].toLowerCase() : "" }
}

function checkerDigest(root) {
  return sha256File(path.join(root, "tests", "assert_artifacts.py"))
}

function verifyChecker(root) {
  const project = path.join(root, "tests", "assert_artifacts.py")
  if (!existsSync(project)) return { ok: true, warning: "", digest: "", canonical: canonicalChecker() }
  const digest = checkerDigest(root)
  const pin = readCheckerPin()
  const canonical = canonicalChecker()
  if (!pin.digest) {
    return {
      ok: true,
      warning: `checker pin unavailable (${pin.path}) — the project checker runs unverified; install a release bundle or run scripts/repair_checker.sh (w18.3 will block)`,
      digest,
      canonical,
      expected: "",
    }
  }
  if (digest === pin.digest) return { ok: true, warning: "", digest, canonical, expected: pin.digest }
  if (process.env.VIBEWEAVER_ALLOW_CUSTOM_CHECKER === "1") {
    if (process.env.CI) {
      return {
        ok: false,
        reason: `checker pin mismatch and VIBEWEAVER_ALLOW_CUSTOM_CHECKER is forbidden in CI: ${digest.slice(0, 12)} != ${pin.digest.slice(0, 12)}`,
        digest,
        canonical,
        expected: pin.digest,
      }
    }
    return {
      ok: true,
      warning: `custom checker allowed by VIBEWEAVER_ALLOW_CUSTOM_CHECKER=1 (expected ${pin.digest.slice(0, 12)}, got ${digest.slice(0, 12)})`,
      digest,
      canonical,
      expected: pin.digest,
    }
  }
  return {
    ok: false,
    reason: `tests/assert_artifacts.py digest ${digest.slice(0, 12) || "(missing)"} != pinned ${pin.digest.slice(0, 12)} — the checker was modified or is a stub. Repair: bash ${path.join(canonicalHome(), "scripts", "repair_checker.sh")} .`,
    digest,
    canonical,
    expected: pin.digest,
  }
}

// ---------- evidence lock (PLAN W0 Task 2.5) ----------
const PROTECTED_EVIDENCE = new Set([
  "tests/acceptance.md",
  "tests/project_profile.json",
  "tests/debt_baseline.json",
  "tests/.evidence.lock",
])

function relativeUnderRoot(root, filePath) {
  if (typeof filePath !== "string" || !filePath) return ""
  const normRoot = resolveWritePath(root)
  const normFile = resolveWritePath(filePath)
  const rel = path.relative(normRoot, normFile)
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return ""
  return rel.split(path.sep).join("/")
}

function protectedEvidencePath(root, filePath) {
  return PROTECTED_EVIDENCE.has(relativeUnderRoot(root, filePath))
}

function evidenceLockScript(root) {
  const cands = [
    path.join(canonicalHome(), "scripts", "evidence_lock.py"),
    path.join(root, "scripts", "evidence_lock.py"),
    path.join(root, "tests", "evidence_lock.py"),
  ]
  for (const c of cands) if (existsSync(c)) return c
  return null
}

function runEvidenceLock(script, root, args) {
  return new Promise((resolve) => {
    execFile(resolvePython(), [script, "--root", root, ...args], {
      cwd: root,
      encoding: "utf8",
      timeout: assertTimeoutMs(),
      maxBuffer: 2 << 20,
    }, (err, stdout, stderr) => {
      resolve({ code: err ? (typeof err.code === "number" ? err.code : 1) : 0, out: `${stdout}${stderr}`.trim() })
    })
  })
}

async function checkProtectedEvidence(root, filePath) {
  const rel = relativeUnderRoot(root, filePath)
  if (rel === "tests/.evidence.lock") {
    return {
      block: "GATE-BLOCKED (vibeweaver evidence lock): tests/.evidence.lock is written ONLY by scripts/evidence_lock.py — direct edits are a forgery path. Use `--init` / `--update-acceptance --reason <why> --approved` / `--seal-log`.",
    }
  }
  const script = evidenceLockScript(root)
  if (!script) {
    return { notes: ["[GATE-WARNING (vibeweaver)] evidence lock script not installed — protected evidence unchecked (legacy layout); install the release bundle"] }
  }
  const lockPath = path.join(root, "tests", ".evidence.lock")
  if (!existsSync(lockPath)) {
    // Bootstrap only before evidence exists. A lock that disappeared after a
    // `- iter`/`- final-run` line is a tamper signal, not a fresh project:
    // re-initializing would bless the tampered acceptance/profile/debt.
    const log = safeRead(path.join(root, "tests", "verification_log.md"))
    const hasEvidence = /^- (?:iter \d+ (?:PASS|FAIL)|final-run:|assert-run:)/m.test(log)
    if (hasEvidence) {
      return {
        block: "GATE-BLOCKED (vibeweaver evidence lock): tests/.evidence.lock is missing AFTER task evidence exists — this is a tamper signal, not a bootstrap. Restore it from git, or run `python3 scripts/evidence_lock.py --root . --init --force --approved` (Class-E) to re-baseline.",
      }
    }
    const init = await runEvidenceLock(script, root, ["--init"])
    if (init.code !== 0) {
      return { block: `GATE-BLOCKED (vibeweaver evidence lock): could not initialize ${lockPath}\n${init.out}` }
    }
  }
  const r = await runEvidenceLock(script, root, ["--check", "--rebase-new-task"])
  if (r.code !== 0) {
    return {
      block: `GATE-BLOCKED (vibeweaver evidence lock): protected evidence changed without a licensed update.\n${r.out}\nFix: python3 ${script} --root . --update-acceptance --reason "<why>" --approved (Class-E) for acceptance; restore the file for profile/debt; --seal-log after appending the log.`,
    }
  }
  return null
}

function findProjectRoot(startDirs) {
  for (const start of startDirs) {
    if (!start) continue
    for (let d = path.resolve(start); ; d = path.dirname(d)) {
      if (existsSync(path.join(d, "tests", "verification_log.md"))) return d
      if (existsSync(path.join(d, ".vibeweaver", "project.json"))) return d
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
  // Fail-closed fallback identity: the FIRST unresolved probe returns this
  // string; cache it too, or every later flag attempt passes `null` to
  // execFile (TypeError instead of the intended ENOENT/block).
  _pyExe = "python3"
  return _pyExe
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

function currentTaskBlock(root) {
  const log = safeRead(path.join(root, "tests", "verification_log.md"))
  const blocks = log.split(/^(?=## )/m)
  let cur = ""
  for (const b of blocks) if (/^- iter \d+ (?:PASS|FAIL|PARTIAL)/m.test(b)) cur = b
  return cur
}

function lenientAllowed(root) {
  const block = currentTaskBlock(root)
  const hasClass = /^- class:/m.test(block)
  const hasProfile = /^- profile:/m.test(block)
  const prof = safeRead(path.join(root, "tests", "project_profile.json"))
  let uiFalse = false
  try { const j = JSON.parse(prof || "{}"); uiFalse = j && j.ui === false } catch { uiFalse = false }
  const backendOk = uiFalse || /^- ui:\s*none\b/m.test(block)
  return { existing: hasClass && hasProfile, backend: backendOk }
}

function writeGateResult(root, flags, cls) {
  try {
    const p = path.join(root, "tests", "gate_result.json")
    const body = JSON.stringify({ flags: flags || "(none)", class: cls || "", at: new Date().toISOString() })
    const tmp = p + ".tmp"
    writeFileSync(tmp, body)
    renameSync(tmp, p)
  } catch {
    /* evidence write must never break the gate */
  }
}

async function runAssert(root) {
  const pin = verifyChecker(root)
  const project = path.join(root, "tests", "assert_artifacts.py")
  // Prefer the read-only canonical checker; a project copy is only executed
  // when its digest matches the pin (W0 Task 2 step 4).
  const canonical = pin.canonical
  const canonicalOk = canonical && sha256File(canonical) === (pin.expected || pin.digest)
  const script = canonicalOk ? canonical : project
  const rootArgs = canonicalOk ? ["--root", root] : []
  const attempts = []
  let jsonSupported = true
  const final = process.env.VIBEWEAVER_GATE_FINAL === "1"
  const allowed = lenientAllowed(root)
  const combos = FLAG_COMBOS.filter((c) => {
    if (c.includes("--existing") && !allowed.existing) return false
    if (c.includes("--backend-only") && !allowed.backend) return false
    return true
  })
  for (const combo of combos) {
    const flags = final ? ["--final", ...combo] : combo
    const argv = jsonSupported ? ["--json", ...rootArgs, ...flags] : [...rootArgs, ...flags]
    const { err, stdout, stderr } = await runPython(script, argv, root)
    const out = `${stdout}${stderr ? "\n" + stderr : ""}`.trim()
    // the transport flag (--json) and the gate mode (--final) are NOT
    // leniency flags: label attempts by the real flag combo so a strict pass
    // reads "(none)" and never triggers the "passed only under …" note.
    const label = flags.filter((a) => a !== "--json" && a !== "--final" && a !== "--root" && a !== root).join(" ") || "(none)"
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

// WARN-level findings the assert reported on a PASSING run (G1 three-state:
// `evidence seal: none yet`, partial seal, bootstrap advisories). Advisory —
// surfaced as non-blocking notes so the state is visible without blocking
// the write (W12: the missing seal was rendered as a self-contradictory
// STALE BLOCK; SLSA-style verification is explicitly polymorphic and never
// calls "missing" a "mismatch").
function assertWarnings(outputs) {
  const out = []
  const seen = new Set()
  const push = (msg) => {
    if (!msg || seen.has(msg)) return
    seen.add(msg)
    out.push(msg)
  }
  for (const o of outputs) {
    const json = parseAssertJson(String(o || ""))
    const items = json && Array.isArray(json.fails) ? json.fails : []
    for (const f of items) {
      if (f && typeof f === "object" && f.severity === "warn") push(String(f.detail ?? f.code ?? f))
    }
    // ALWAYS also scan the prose WARN lines (review A Minor): the greedy
    // JSON extraction can fail on stray braces in diagnostics, and a failed
    // parse must not silently drop the advisories.
    for (const line of String(o || "").split("\n")) {
      const m = line.trim()
      if (m.startsWith("WARN ")) push(m.slice(5))
    }
  }
  return out
}

function inlineCheck(root) {
  const failures = []
  const testsDir = path.join(root, "tests")
  const log = safeRead(path.join(testsDir, "verification_log.md"))
  const acc = safeRead(path.join(testsDir, "acceptance.md"))
  if (!/- iter \d+ (PASS|FAIL)\b/.test(log)) {
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
  const logPath = path.join(root, "tests", "verification_log.md")
  if (!existsSync(logPath)) {
    const key = root + "|inactive"
    if (!LENIENT_NOTED.has(key)) {
      LENIENT_NOTED.add(key)
      return { blocking: [], warnings: ["GATE-INACTIVE: marker present but tests/verification_log.md is missing — the gate cannot attribute a task class; create the log or remove the marker"] }
    }
    return null
  }
  const assertsPath = path.join(root, "tests", "assert_artifacts.py")
  if (existsSync(assertsPath)) {
    const pin = verifyChecker(root)
    const pinWarnings = pin.warning ? [pin.warning] : []
    if (!pin.ok) {
      return { blocking: [pin.reason], warnings: pinWarnings, attempts: ["(checker-pin)"] }
    }
    const key = depFingerprint(root)
    const lossy = LOSSY_DIGEST.has(root) || LOSSY_FINGERPRINT.has(root)
    if (!lossy && RESULT_CACHE.has(key)) {
      const cached = RESULT_CACHE.get(key) // may be null = cached PASS
      if (cached === null && pinWarnings.length) return { blocking: [], warnings: pinWarnings }
      return cached
    }
    const r = await runAssert(root)
    let result
    if (r.ok) {
      if (!lossy) {
        if (RESULT_CACHE.size >= RESULT_CACHE_MAX) RESULT_CACHE.clear()
        RESULT_CACHE.set(key, null) // cache the CLEAN verdict (the note is out-of-band)
      }
      const notes = [...pinWarnings]
      for (const w of assertWarnings([r.output, ...(r.attempts || []).map((a) => a.output)])) {
        // once per (root, message) — a repeated advisory is alarm flood and
        // trains warning-blindness (same latch rule as the stall note)
        const k = root + "|" + w
        if (LENIENT_NOTED.has(k)) continue
        LENIENT_NOTED.add(k)
        notes.push(w)
      }
      const flags = r.flags || ""
      if (flags && flags !== "(none)") {
        const noteKey = root + "|" + flags
        if (!LENIENT_NOTED.has(noteKey)) {
          LENIENT_NOTED.add(noteKey)
          notes.push(
            `assert_artifacts.py passed only under ${flags} — the strict run reported: ${((r.attempts && r.attempts[0] && String(r.attempts[0].output).split("\n")[0]) || "failures").slice(0, 120)} (expected for Modify-Existing/backend tasks; suspicious for new projects)`,
          )
        }
      }
      if (LENIENT_NOTED.size > 64) LENIENT_NOTED.clear()
      const cls = (currentTaskBlock(root).match(/^- class:\s*(DOC|CONFIG|CODE)/m) || [])[1] || ""
      writeGateResult(root, r.flags || "(none)", cls)
      return notes.length ? { blocking: [], warnings: notes } : null
    }
    {
      const { blocking, warnings } = collectMessages(r.attempts)
      result = { blocking, warnings: [...pinWarnings, ...warnings], attempts: r.attempts.map((a) => `[${a.flags}]`) }
    }
    if (!lossy) {
      if (RESULT_CACHE.size >= RESULT_CACHE_MAX) RESULT_CACHE.clear()
      RESULT_CACHE.set(key, result)
    }
    writeGateResult(root, (r.attempts && r.attempts.length ? "(failed)" : "(none)"), "")
    return result
  }
  const failures = inlineCheck(root)
  if (failures.length) return { blocking: failures, warnings: [], attempts: [], inline: true }
  return null
}

function countPasses(root) {
  const log = safeRead(path.join(root, "tests", "verification_log.md"))
  // COV-1's grammar (`PASS\b`, colon optional) — a colon-less PASS must still
  // count as progress for the stall observer (W18 review r2 parity fix).
  return (log.match(/^- iter \d+ PASS\b/gm) || []).length
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

// The host's write/edit tools carry the target under `filePath` (v1 sample
// shapes) but the canonical opencode tool args are {path, content} /
// {path, oldString, newString}. Reading only `filePath` left every REAL write
// unattributed, so the tests/-evidence exemption below could never engage —
// W12 saw 30+ false GATE-BLOCKED banners on tests/ writes ("tests/ writes are
// never gated" per COMPLETION_GATE §A4.4.2), reproduced live in W18. Accept
// the known arg spellings; an unknown shape stays fail-closed (full gate).
function writePathFromArgs(args) {
  if (!args || typeof args !== "object") return null
  const seen = []
  for (const key of ["filePath", "path", "file_path"]) {
    const v = args[key]
    if (typeof v === "string" && v) seen.push(v)
  }
  if (!seen.length) return null
  // Two DIFFERENT target spellings in one call is an unknown host shape —
  // fail closed (full gate) rather than let one key smuggle the exemption.
  if (seen.some((v) => v !== seen[0])) return null
  return seen[0]
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
  // EXACT first-segment match (review A Minor): case-folding made `Tests/` /
  // `Memory/` a false exemption on case-sensitive filesystems — fail closed
  // (a mis-cased evidence dir gets gated = noise, never a hole).
  const seg = rel.split(path.sep)[0]
  if (seg !== "test" && seg !== "tests" && seg !== "memory") return false
  // Protected evidence (W0 Task 2 step 3 / Task 2.5 step 3): the checker,
  // pin tables and lock files are NOT evidence — they are the measuring
  // instrument and must stay gated. tests/acceptance.md, project_profile and
  // debt_baseline join this list in Task 2.5.
  const posix = rel.split(path.sep).join("/")
  const base = path.posix.basename(posix)
  if (posix === "tests/assert_artifacts.py") return false
  if (base.endsWith(".sha256") || base.endsWith(".lock")) return false
  if (posix === "tests/gate_result.json") return false
  return true
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
  bootstrapped: new Set(), // sessionIDs: the 1 KB bootstrap pointer was injected
}

// ---------- bootstrap injection (PLAN W0 Task 4) ----------
// A weak model that never opens the 49 KB contract cannot follow it. Inject a
// 1-2 KB pointer at session start (and again after compaction); never stack it
// on top of an already-forced full contract, and never inject into subagent
// sessions. VIBEWEAVER_BOOTSTRAP=off disables the injection.
const BOOTSTRAP_VERSION = "1"
const BOOTSTRAP_MARK = "using-vibeweaver (bootstrap v" + BOOTSTRAP_VERSION + ")"
const FULL_CONTRACT_MARK = "§1 OPERATING COVENANT"
let _bootstrapText = null


// The host's system context is an array of LLM.SystemPart objects
// ({type:"text", text}); a bare string fails provider schema validation.
// Older v1 harnesses used strings, so preserve that shape when present.
function systemTextOf(part) {
  return typeof part === "string" ? part : (part && typeof part.text === "string" ? part.text : "")
}

function pushSystemText(output, text) {
  if (!Array.isArray(output.system)) output.system = []
  const arr = output.system
  const objectShape = arr.length === 0 || arr.some((p) => p && typeof p === "object" && p.type === "text")
  arr.push(objectShape ? { type: "text", text } : text)
}

function bootstrapText() {
  if (_bootstrapText !== null) return _bootstrapText
  const p = path.join(canonicalHome(), "bootstrap.md")
  const raw = safeRead(p).trim()
  const modelClass = process.env.VIBEWEAVER_MODEL_CLASS || "unknown"
  const modelLine = "model_class=" + modelClass + (modelClass === "unknown" ? " (unknown -> core + warning)" : "")
  _bootstrapText = (raw ? raw + "\n\n" : "") + [
    BOOTSTRAP_MARK,
    modelLine,
    "A coding task is active. Read SKILL.md §1 (covenants), then",
    "TESTING_PROTOCOLS.md §A4.1/§A4.8; evidence goes to tests/.",
  ].join("\n") || [
    BOOTSTRAP_MARK,
    "A coding task is active. Read SKILL.md §1 (covenants), then",
    "TESTING_PROTOCOLS.md §A4.1/§A4.8; evidence goes to tests/.",
  ].join("\n")
  return _bootstrapText
}

function isChildSession(input) {
  if (!input || typeof input !== "object") return false
  if (input.parentID || input.parentId || input.parentSessionID) return true
  const s = input.session
  return !!(s && typeof s === "object" && (s.parentID || s.parentId))
}

function injectBootstrap(input, output) {
  if (process.env.VIBEWEAVER_BOOTSTRAP === "off") return null
  if (!output || typeof output !== "object") return null
  if (isChildSession(input)) return null
  const sid = input && (input.sessionID || (input.session && input.session.id))
  if (!sid || typeof sid !== "string") return null
  if (!Array.isArray(output.system)) output.system = []
  const joined = output.system.map(systemTextOf).join("\n")
  if (joined.includes(FULL_CONTRACT_MARK)) return null // host already force-injected full
  if (joined.includes(BOOTSTRAP_MARK)) {
    SESSION_MEM.bootstrapped.add(sid)
    capBounded(SESSION_MEM.bootstrapped)
    return null
  }
  if (SESSION_MEM.bootstrapped.has(sid)) return null
  pushSystemText(output, BOOTSTRAP_MARK + "\n\n" + bootstrapText())
  SESSION_MEM.bootstrapped.add(sid)
  capBounded(SESSION_MEM.bootstrapped)
  return BOOTSTRAP_MARK
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
const RISK_PATH_RE = /(^|\/)(auth|security|payments?|billing|crypto|migrations?|permissions?|acl)(\/|\.|_|$)/i

function approvalsText(root) {
  return safeRead(path.join(root, "tests", "decisions.md"))
}

function riskApproved(root, target) {
  if (!target) return false
  const text = approvalsText(root)
  const rel = target.replace(/\\/g, "/")
  for (const line of text.split("\n")) {
    if (!/risk-approved:|destructive-approved:/i.test(line)) continue
    if (line.includes(rel) || line.includes(path.basename(rel))) return true
  }
  return false
}

function riskPathBlock(root, filePath) {
  if (process.env.VIBEWEAVER_RISK_GATE === "off") return null
  if (!filePath) return null
  const rel = relativeUnderRoot(root, filePath)
  if (!rel || !RISK_PATH_RE.test(rel)) return null
  if (riskApproved(root, rel)) return null
  return `GATE-BLOCKED (vibeweaver risk-path gate): ${rel} matches a risk-tier path (auth/security/payment/billing/crypto/migration/permission/acl). Add a user-approved line to tests/decisions.md: \`- risk-approved: ${rel} — <why>\` (Class-E), or set VIBEWEAVER_RISK_GATE=off with user consent.`
}

function riskCommandBlock(root, command) {
  if (process.env.VIBEWEAVER_RISK_GATE === "off") return null
  if (typeof command !== "string" || !command) return null
  const m = command.match(/(?:^|[;&|]\s*)(?:sudo\s+)?(?:rm|git\s+rm)\s+(?:-[^\s]+\s+)*([^;&|]+)/)
  if (!m) return null
  const targets = m[1].split(/\s+/).filter((x) => x && !x.startsWith("-"))
  for (const target of targets) {
    const rel = target.replace(/^['"]|['"]$/g, "").replace(/\\/g, "/")
    if (RISK_PATH_RE.test(rel) && !riskApproved(root, rel)) {
      return `GATE-BLOCKED (vibeweaver risk-path gate): deleting risk-tier path ${rel} requires a user-approved \`- risk-approved: ${rel} — <why>\` line in tests/decisions.md.`
    }
  }
  return null
}

const DESTRUCTIVE_ALLOW = /(^|\/)(node_modules|\.venv|venv|dist|build|target|coverage|\.next|\.pytest_cache|__pycache__)(\/|$)|^(\$TMPDIR|\/tmp)(\/|$)/

function destructiveApproved(root, command) {
  const text = approvalsText(root)
  for (const line of text.split("\n")) {
    if (!/destructive-approved:|risk-approved:/i.test(line)) continue
    const needle = line.split(/destructive-approved:|risk-approved:/i)[1] || ""
    if (needle.trim() && (command.includes(needle.trim().split(" — ")[0].trim()) || line.includes(command))) return true
  }
  return false
}

function destructiveBlock(root, command) {
  if (process.env.VIBEWEAVER_DESTRUCTIVE_GATE === "off") return null
  if (typeof command !== "string" || !command) return null
  if (destructiveApproved(root, command)) return null
  const c = command.trim()
  if (/git\s+add\s+(?:-A|--all)\b/.test(c)) return "GATE-BLOCKED (destructive guard): `git add -A` stages ignored/vendor trees (45k-path incident). Use `git add -u` + explicit paths, or add `- destructive-approved: git add -A — <why>`."
  if (/git\s+reset\s+--hard\b/.test(c)) return "GATE-BLOCKED (destructive guard): `git reset --hard` discards uncommitted work. Add a Class-E decision line or use a stash."
  if (/git\s+clean\s+-[a-z]*[fd][a-z]*/.test(c)) return "GATE-BLOCKED (destructive guard): `git clean -fdx` deletes untracked files. Add a Class-E decision line first."
  if (/git\s+(?:checkout|restore)\s+--\s+\./.test(c)) return "GATE-BLOCKED (destructive guard): `git checkout/restore -- .` discards the whole worktree. Add a Class-E decision line first."
  if (/\btruncate\s+/.test(c)) return "GATE-BLOCKED (destructive guard): `truncate` destroys file content. Add a Class-E decision line first."
  const m = c.match(/(?:^|[;&|]\s*)(?:sudo\s+)?rm\s+(?:-[^\s]+\s+)+([^;&|]+)/)
  if (m) {
    const targets = m[1].split(/\s+/).map((x) => x.replace(/^['"]|['"]$/g, "")).filter(Boolean)
    const bad = targets.filter((target) => !DESTRUCTIVE_ALLOW.test(target))
    if (bad.length) return "GATE-BLOCKED (destructive guard): recursive delete of non-allowlisted path(s): " + bad.join(", ") + ". Add `- destructive-approved: <command> — <why>` for a Class-E action."
  }
  return null
}

function beforeToolCheck(directory, tool, args) {
  const root0 = findProjectRoot([directory])
  if (tool === "bash" || tool === "shell") {
    if (root0 && args && typeof args.command === "string") {
      return riskCommandBlock(root0, args.command) || destructiveBlock(root0, args.command)
    }
    return null
  }
  const filePath = writePathFromArgs(args)
  if (!filePath) return null
  const abs = path.isAbsolute(filePath) ? filePath : path.resolve(directory || ".", filePath)
  const root = findProjectRoot([directory, path.dirname(abs)])
  if (!root) return null
  const risk = riskPathBlock(root, abs)
  if (risk) return risk
  return null
}

function gateCheckWrite(directory, filePath) {
  if (process.env.VIBEWEAVER_GATE === "off") return Promise.resolve(null)
  // relative args.path resolves against the host directory (review A: cwd
  // resolution made a tests/ write look like a non-evidence write)
  if (filePath && !path.isAbsolute(filePath) && directory) filePath = path.resolve(directory, filePath)
  const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
  if (!root) return Promise.resolve(null)
  // Cue delivery is hoisted ABOVE the gate: a RED gate (e.g. the task's
  // first write, empty log) is exactly when "read it before editing" must
  // arrive — delivery must never depend on the gate being green.
  const block = currentTaskBlock(root)
  const docClaim = /^- class:\s*DOC\b/m.test(block)
  const codeExt = /\.(?:py|js|mjs|ts|tsx|jsx|go|rs|java|c|cc|cpp|h|hpp|rb|php|cs|sh|bash|ps1)$/i
  if (docClaim && filePath && codeExt.test(filePath)) {
    return Promise.resolve({ block: `GATE-BLOCKED (vibeweaver class guard): the current task block declares \`- class: DOC\` but this write targets a code file (${path.basename(filePath)}). DOC is prose/office only; reclassify the task (CODE/CONFIG) before writing code.` })
  }
  const cues = cueNotes(root, filePath)
  // Protected evidence (W0 Task 2.5): acceptance/profile/debt/lock are NOT
  // ordinary evidence — they are the rules of the game. A write runs the
  // evidence lock check; a mismatch blocks completion.
  if (protectedEvidencePath(root, filePath)) {
    return checkProtectedEvidence(root, filePath).then((r) => {
      if (r && r.block) return { block: r.block }
      const notes = [...cues, ...((r && r.notes) || [])]
      return notes.length ? { notes } : null
    })
  }
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
    "tool.execute.before": async (input, output) => {
      if (!input) return
      const risk = beforeToolCheck(directory, input.tool, input.args || (output && output.args) || {})
      if (risk) throw new Error(risk)
    },
    "tool.execute.after": async (input, output) => {
      if (!GATED_TOOLS.has(input.tool)) return
      const filePath = writePathFromArgs(input.args)
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
      try {
        injectBootstrap(input, output)
      } catch {
        /* bootstrap must never break a request */
      }
      const sid = input && typeof input.sessionID === "string" ? input.sessionID : null
      if (!sid || !SESSION_MEM.pendingResume.has(sid)) return
      const root = findProjectRoot([directory])
      if (!root) return
      try {
        if (Array.isArray(output.system)) {
          pushSystemText(output, compactStateBundle(root))
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
          SESSION_MEM.bootstrapped.delete(sid) // compaction may drop the pointer
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
    const filePath = writePathFromArgs(input)
    const r = await gateCheckWrite(directory, filePath)
    if (r && r.block) throw new Error(r.block)
    if (r && r.notes) appendNotesToV2Result(event, r.notes)
    const cue = firstTouchCue(directory)
    if (cue) appendNotesToV2Result(event, [cue])
  })
  registrations.push(registration)
  try {
    const before = await ctx.tool.hook("execute.before", async (event) => {
      if (!event || !event.input) return
      const risk = beforeToolCheck(directory, event.tool, event.input)
      if (risk) throw new Error(risk)
    })
    if (before) registrations.push(before)
  } catch {
    /* host without a pre-hook: risk gate is post-hoc only */
  }
  // v2 bootstrap (PLAN W0 Task 4): use the session context hook when the host
  // exposes it. The shipped 1.18.35 v2 context has no session domain, so this
  // block is feature-detected and stays a no-op there (bootstrap.md is the
  // documented fallback). Do not ship guessed shapes — wave21 r1.
  if (ctx.session && typeof ctx.session.hook === "function") {
    try {
      const reg = await ctx.session.hook("context", async (event, output) => {
        try {
          const input = output ? event : (event && event.input) || event || {}
          const out = output || (event && event.output) || event
          injectBootstrap(input, out)
        } catch {
          /* one bad context hook must not break the request */
        }
      })
      if (reg) registrations.push(reg)
    } catch {
      console.warn("[vibeweaver-gate] v2 session.hook('context') unavailable — bootstrap falls back to bootstrap.md")
    }
  }
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
              SESSION_MEM.bootstrapped.delete(sid2)
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
