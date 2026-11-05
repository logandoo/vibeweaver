import { execFile, execFileSync } from "node:child_process"
import { createHash } from "node:crypto"
import { closeSync, existsSync, fsyncSync, fstatSync, lstatSync, mkdirSync, openSync, readdirSync, readFileSync, readlinkSync, readSync, realpathSync, renameSync, rmSync, statSync, unlinkSync, writeFileSync, writeSync } from "node:fs"
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
// W19 (graduated gate / alarm-flood control): the blocking banner is LATCHED
// per project — an unchanged failure list is dumped IN FULL only once, then a
// one-line summary points at tests/gate_result.json (the details are always on
// disk). Warnings already dedupe via LENIENT_NOTED; blocking had no such latch,
// so a persistent vendored-secret wave re-emitted 60+ lines on EVERY edit.
const LAST_BLOCK = new Map()
const LAST_COMPLETION = new Map()
// W23: a write resolves its scope from the target file (nearest git project
// boundary). Session-scoped hooks without a file path (compaction/idle/cue)
// must follow the same root, not fall back to the umbrella workspace root.
const SESSION_ROOT = new Map()
// Review B4 (A4.9): a verdict that only passed under a lenient flag combo
// (--existing / --backend-only) is surfaced ONCE per project+flags — the
// combo sweep is how the gate copes with unknown task type (strict is tried
// first), but a lenient-only pass must be visible, never silent.
const LENIENT_NOTED = new Set()

function depFingerprint(root) {
  LOSSY_FINGERPRINT.delete(root)
  // W23/O2: a non-git tree has no trustworthy whole-tree content key here.
  // Do not cache its verdict at all (the old path only keyed evidence/secret
  // files, so an ordinary source edit could reuse a stale PASS).
  if (!existsSync(path.join(root, ".git"))) LOSSY_FINGERPRINT.add(root)
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
        } else if (f !== "gate_result.json") {
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
    "tests/debt_baseline.json"]) {
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
      // A cache-key read must not mutate .git/index (which would invalidate
      // the very key it is computing and turn every write into a cache miss).
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
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
  // Filter gate-owned noise from the STATUS STRING too: `parts=[out]` made
  // skipping the per-path stat useless because the porcelain line itself
  // changed the cache key (tracked tests/gate_result.json case).
  const stableStatus = out.split("\n").filter((line) => {
    const p = line.slice(3).trim().replace(/^"|"$/g, "")
    return p !== "tests/gate_result.json"
      && p !== ".vibeweaver" && !p.startsWith(".vibeweaver/")
  }).join("\n")
  const parts = [stableStatus]
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
    // The gate writes this itself; tracking it must not invalidate the cache
    // key on every write (the previous workaround was fixture-only ignore).
    if (p === "tests/gate_result.json") continue
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
// ---------- W25 run-aware helpers (MULTI_AGENT.md §MA1/§MA2/§MA9) ----------
// Self-contained (no cross-imports): vibeweaver-audit.js carries its own copy.
// The seams hang off the server function below so the module export shape
// stays exactly { id, server, setup } (see the dual-compat contract).

const RUN_CONTEXT_SCHEMA = "vibeweaver-run-context/1"
const RUN_ID_RE = /^(run)-[0-9a-f]{32}$/
const ATTEMPT_ID_RE = /^attempt-[0-9a-f]{32}$/
const RUN_CONTEXT_WARNED = new Set()

// One-time RUN-CONTEXT WARNING per bad file/reason — a missing file is plain
// legacy and warns nothing (byte-identical legacy behavior).
function runContextWarning(msg) {
  try {
    if (RUN_CONTEXT_WARNED.has(msg)) return
    RUN_CONTEXT_WARNED.add(msg)
    if (RUN_CONTEXT_WARNED.size > 64) RUN_CONTEXT_WARNED.clear()
    console.warn("RUN-CONTEXT WARNING: " + msg)
  } catch {
    /* never crash on a warning */
  }
}

// W25 RunContext detection (Hub "JS RunContext 探测"): read
// <root>/.vibeweaver/run_context.json (VIBEWEAVER_RUN_CONTEXT overrides the
// path when the default file is absent). A valid object requires schema
// "vibeweaver-run-context/1" plus every Hub field (all strings except
// lease_epoch: int >= 1) and canonical run/attempt id shapes. A BAD file
// returns null and surfaces a one-time RUN-CONTEXT WARNING — never crashes.
// A MISSING file returns null silently: that is the legacy single-agent path.
function loadRunContext(root) {
  try {
    if (!root || typeof root !== "string") return null
    let file = path.join(root, STATE_DIR, "run_context.json")
    if (!existsSync(file)) {
      const env = process.env.VIBEWEAVER_RUN_CONTEXT
      if (!env || typeof env !== "string") return null // legacy: no run context
      file = env
    }
    const raw = safeRead(file)
    if (!raw) {
      runContextWarning(`${file}: run context unreadable or empty — falling back to legacy scope`)
      return null
    }
    let j = null
    try {
      j = JSON.parse(raw)
    } catch {
      j = null
    }
    if (!j || typeof j !== "object" || Array.isArray(j)) {
      runContextWarning(`${file}: run context is not a JSON object — falling back to legacy scope`)
      return null
    }
    if (j.schema !== RUN_CONTEXT_SCHEMA) {
      runContextWarning(`${file}: schema ${JSON.stringify(j.schema)} != ${RUN_CONTEXT_SCHEMA} — falling back to legacy scope`)
      return null
    }
    for (const f of ["repo_id", "task_id", "run_id", "attempt_id", "wave_id", "session_id", "worktree_root", "artifact_root", "state_root", "base_sha", "spec_hash", "skill_version", "checker_digest"]) {
      if (typeof j[f] !== "string" || !j[f]) {
        runContextWarning(`${file}: missing/empty field ${f} — falling back to legacy scope`)
        return null
      }
    }
    if (!Number.isInteger(j.lease_epoch) || j.lease_epoch < 1) {
      runContextWarning(`${file}: lease_epoch must be an integer >= 1 — falling back to legacy scope`)
      return null
    }
    if (!RUN_ID_RE.test(j.run_id)) {
      runContextWarning(`${file}: run_id ${JSON.stringify(j.run_id)} is not run-<32hex> — falling back to legacy scope`)
      return null
    }
    if (!ATTEMPT_ID_RE.test(j.attempt_id)) {
      runContextWarning(`${file}: attempt_id ${JSON.stringify(j.attempt_id)} is not attempt-<32hex> — falling back to legacy scope`)
      return null
    }
    // J2 (W25 review): path-bound validation — worktree_root/artifact_root/
    // state_root must be the run root itself or a path contained UNDER it
    // (path.resolve + containment). A context pointing elsewhere claims
    // ANOTHER run's evidence (forged attribution) — rejected like any forged
    // context, fail-closed with a one-time RUN-CONTEXT WARNING.
    const runRootResolved = path.resolve(root)
    for (const f of ["worktree_root", "artifact_root", "state_root"]) {
      const p = path.resolve(j[f])
      if (p !== runRootResolved && !p.startsWith(runRootResolved + path.sep)) {
        runContextWarning(`${file}: ${f} ${JSON.stringify(j[f])} escapes the run root ${runRootResolved} — falling back to legacy scope`)
        return null
      }
    }
    return j
  } catch (err) {
    runContextWarning(`${root}: run context probe failed (${String((err && err.message) || err)}) — falling back to legacy scope`)
    return null
  }
}

// W25 atomic state write (Hub "JS 原子写"): unique tmp
// (<p>.<pid>.<Date.now()>.<rand>.tmp) + fsync + rename. On ANY failure THROW —
// the caller decides critical fail-closed vs. observation-only swallow. The
// unique tmp name removes the fixed-<p>.tmp rename race between writers.
function atomicWriteUnique(p, body) {
  const tmp = p + "." + process.pid + "." + Date.now() + "." + Math.random().toString(36).slice(2) + ".tmp"
  let fd = null
  try {
    fd = openSync(tmp, "w")
    const buf = Buffer.from(body)
    let off = 0
    while (off < buf.length) off += writeSync(fd, buf, off, buf.length - off)
    fsyncSync(fd)
    closeSync(fd)
    fd = null
    renameSync(tmp, p)
  } catch (err) {
    if (fd !== null) {
      try {
        closeSync(fd)
      } catch {
        /* keep the original error */
      }
    }
    try {
      unlinkSync(tmp)
    } catch {
      /* best-effort tmp cleanup */
    }
    throw err
  }
}

// W25 state scope key (Hub): with a RunContext the state block is keyed by run
// and attempt identity ("run:<run_id>/attempt:<attempt_id>"); without one the
// legacy key derivation (the root path) is unchanged.
function stateScopeKey(root) {
  const rc = loadRunContext(root)
  return rc ? "run:" + rc.run_id + "/attempt:" + rc.attempt_id : root
}

// W25: observation-only state failures keep the historical swallow but set
// this flag; the NEXT emitted message surfaces it (then it clears). The
// CRITICAL paths (the --final enforcement record) throw GATE-CHECK-UNAVAILABLE
// instead — see writeGateResult.
let PERSIST_ERROR = null
function takePersistError() {
  if (!PERSIST_ERROR) return null
  const msg = "[GATE-WARNING (vibeweaver)] persist-error: " + PERSIST_ERROR
  PERSIST_ERROR = null
  return msg
}

// W25 §MA9 worktree git metadata: a linked WORKTREE checkout has a `.git` FILE
// pointer into its owning repo's .git/worktrees/<name> (or a git worktree
// split: --git-dir != --git-common-dir). The WORKTREE root owns its
// .vibeweaver state — never the shared common repository dir. Ordinary repos
// (`.git` dir with git-dir == git-common-dir) and submodules (pointer into
// .git/modules/) are NOT worktrees: their behavior is unchanged.
function gitWorktreeSplit(dir) {
  try {
    const opts = { cwd: dir, encoding: "utf8", timeout: 5000, stdio: ["ignore", "pipe", "pipe"] }
    const gd = execFileSync("git", ["rev-parse", "--git-dir"], opts).trim()
    const gcd = execFileSync("git", ["rev-parse", "--git-common-dir"], opts).trim()
    return Boolean(gd && gcd) && !samePath(path.resolve(dir, gd), path.resolve(dir, gcd))
  } catch {
    return false
  }
}

function worktreeTopLevel(start) {
  if (!start) return null
  for (let d = path.resolve(start); ; d = path.dirname(d)) {
    let st = null
    try {
      st = lstatSync(path.join(d, ".git"))
    } catch {
      st = null
    }
    if (st) {
      if (!st.isFile()) return null // ordinary repo boundary (`.git` dir)
      const m = /^gitdir:\s*(.+)\s*$/.exec(safeRead(path.join(d, ".git")).trim())
      if (m && /[\\/]\.git[\\/]worktrees[\\/]/.test(m[1])) return d // worktree pointer
      return gitWorktreeSplit(d) ? d : null // submodules split false → unchanged
    }
    if (d === path.dirname(d)) break
  }
  return gitWorktreeSplit(path.resolve(start)) ? gitTopLevel(start) : null
}

// W25 session→run mapping (persisted in the plugin's own state file): the
// idle/compaction/resume hooks carry no file path — they resolve their root
// from sessionID → run/attempt/root recorded on the session's first
// RunContext hook, instead of last-write guessing. An absent mapping keeps
// the legacy SESSION_ROOT fallback unchanged.
let SESSION_RUN_CACHE = { key: "", at: 0, val: null }

function hostStatePath(directory) {
  return path.join(directory, STATE_DIR, STATE_FILE)
}

function hostSessionRuns(directory) {
  try {
    const p = hostStatePath(directory)
    const now = Date.now()
    if (SESSION_RUN_CACHE.key === p && now - SESSION_RUN_CACHE.at < 1000) return SESSION_RUN_CACHE.val || {}
    let val = {}
    try {
      const j = JSON.parse(safeRead(p) || "null")
      if (j && typeof j.sessionRuns === "object" && j.sessionRuns) val = j.sessionRuns
    } catch {
      val = {}
    }
    SESSION_RUN_CACHE = { key: p, at: now, val }
    return val
  } catch {
    return {}
  }
}

function recordSessionRun(directory, sessionID, root, rc) {
  if (!directory || !sessionID || !root || !rc) return
  try {
    const p = hostStatePath(directory)
    let st = {}
    try {
      st = JSON.parse(safeRead(p) || "null")
    } catch {
      st = {}
    }
    if (!st || typeof st !== "object" || Array.isArray(st)) st = {}
    if (!st.sessionRuns || typeof st.sessionRuns !== "object") st.sessionRuns = {}
    const prev = st.sessionRuns[sessionID]
    if (prev && prev.runID === rc.run_id) {
      // same run: keep the first root, follow attempt takeover
      if (prev.attemptID !== rc.attempt_id) {
        prev.attemptID = rc.attempt_id
        prev.at = Date.now()
        if (!existsSync(path.join(directory, STATE_DIR))) mkdirSync(path.join(directory, STATE_DIR), { recursive: true })
        atomicWriteUnique(p, JSON.stringify(st))
        SESSION_RUN_CACHE = { key: "", at: 0, val: null }
      }
      return
    }
    if (prev) return // first-hook wins across runs (no last-write guessing)
    st.sessionRuns[sessionID] = { root, runID: rc.run_id, attemptID: rc.attempt_id, at: Date.now() }
    const keys = Object.keys(st.sessionRuns)
    if (keys.length > 50) for (const k of keys.slice(0, keys.length - 50)) delete st.sessionRuns[k]
    if (!existsSync(path.join(directory, STATE_DIR))) mkdirSync(path.join(directory, STATE_DIR), { recursive: true })
    atomicWriteUnique(p, JSON.stringify(st))
    SESSION_RUN_CACHE = { key: "", at: 0, val: null }
  } catch (err) {
    PERSIST_ERROR = "persist failed: " + String((err && err.message) || err)
    /* mapping is best-effort: never break a write */
  }
}

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
  if (!rel || isOutsideRel(rel)) return ""
  return rel.split(path.sep).join("/")
}

function protectedEvidencePath(root, filePath) {
  return PROTECTED_EVIDENCE.has(relativeUnderRoot(root, filePath))
}

// A scope-denied nested project may only bootstrap the two files that make it
// trusted. Protected evidence (acceptance/profile/debt/lock) must never ride
// this activation path without its lock check.
function isActivationPath(root, filePath) {
  const rel = relativeUnderRoot(root, filePath)
  return rel === "tests/verification_log.md" || rel === "tests/assert_artifacts.py"
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

function projectMarkerAt(dir) {
  return existsSync(path.join(dir, "tests", "verification_log.md"))
    || existsSync(path.join(dir, ".vibeweaver", "project.json"))
}

// Git top-level is the trusted project boundary for a nested write. A marker
// that an agent can create in an arbitrary nested directory must not be able
// to shrink the gate scope away from an active workspace root.
function gitTopLevel(start) {
  if (!start) return null
  try {
    const out = execFileSync("git", ["rev-parse", "--show-toplevel"], {
      cwd: path.resolve(start),
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "pipe", "pipe"],
    }).trim()
    if (out) return path.resolve(out)
  } catch {
    /* fall through to the pure-FS probe below */
  }
  // W25b Windows hardening: when the subprocess probe fails or is unavailable,
  // the `.git` dir / worktree-pointer layout answers the same question without
  // leaving the filesystem (spelling-stable across platforms).
  try {
    for (let d = path.resolve(start); ; d = path.dirname(d)) {
      let st = null
      try { st = lstatSync(path.join(d, ".git")) } catch { st = null }
      if (st) {
        if (!st.isFile()) return d
        const m = /^gitdir:\s*(.+)\s*$/.exec(safeRead(path.join(d, ".git")).trim())
        if (m) {
          const gd = path.resolve(d, m[1])
          const w = gd.indexOf(`${path.sep}.git${path.sep}worktrees${path.sep}`) >= 0
            ? gd.split(`${path.sep}.git${path.sep}worktrees${path.sep}`)[0]
            : gd.replace(/[\\/]\.git$/, "")
          return w || d
        }
        return d
      }
      if (d === path.dirname(d)) break
    }
  } catch {
    /* never throw */
  }
  return null
}

function nearestExistingDir(start) {
  let d = path.resolve(start)
  for (;;) {
    if (existsSync(d)) return d
    const up = path.dirname(d)
    if (up === d) return d
    d = up
  }
}

function canonicalPath(p) {
  try {
    return realpathSync(path.resolve(p))
  } catch {
    return path.resolve(p)
  }
}

// W25b Windows hardening: spelling-insensitive path equality (8.3 short vs
// long via realpathSync, drive-letter case on win32). COMPARISONS ONLY —
// key text and path building never normalize.
function samePath(a, b) {
  if (!a || !b) return false
  if (a === b) return true
  try {
    const x = canonicalPath(a), y = canonicalPath(b)
    if (process.platform === "win32" ? x.toLowerCase() === y.toLowerCase() : x === y) return true
  } catch {
    /* fall through to file-identity compare */
  }
  // File identity (dev/ino) is spelling-proof across 8.3 short/long names,
  // case, and symlinked temp roots (Windows realpathSync does not always
  // expand short names).
  try {
    const sa = statSync(a), sb = statSync(b)
    if (sa.ino && sb.ino && sa.ino === sb.ino && sa.dev === sb.dev) return true
  } catch {
    /* fall through */
  }
  return canonicalPath(a) === canonicalPath(b)
}

function isOutsideRel(rel) {
  return rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)
}

function isOutside(base, target) {
  // New write targets may not exist yet; resolve the nearest existing ancestor
  // (same normalization used by the tests/evidence exemption) so a `/var` ↔
  // `/private/var` symlink does not masquerade as an out-of-tree write.
  return isOutsideRel(path.relative(canonicalPath(base), resolveWritePath(path.resolve(target))))
}

function trustedNestedProject(dir) {
  return projectMarkerAt(dir)
    && existsSync(path.join(dir, "tests", "verification_log.md"))
    && existsSync(path.join(dir, "tests", "assert_artifacts.py"))
}

function findProjectRootForWrite(directory, filePath) {
  const host = directory ? canonicalPath(directory) : null
  if (typeof filePath !== "string" || !filePath) {
    const root = findProjectRoot([host])
    return root ? { root, via: "workspace" } : null
  }
  const abs = path.resolve(host || ".", filePath)
  const fileDir = path.dirname(abs)
  // A write target may not exist yet; resolve git from its nearest existing
  // ancestor or a new subdirectory would silently fall back to the host.
  const fileGit = gitTopLevel(nearestExistingDir(fileDir))
  const hostGit = host ? gitTopLevel(host) : null
  const outsideHost = host ? isOutside(host, abs) : true
  const activeHere = host && projectMarkerAt(host) ? host : null
  const hostTrusted = activeHere ? trustedNestedProject(host) : false
  const activeAbove = host && path.dirname(host) !== host ? findProjectRoot([path.dirname(host)]) : null
  const activeFallback = activeHere || activeAbove
  const scopeBlock = (root, target, why, evidenceRoot) => ({
    root, via: "untrusted-scope", evidenceRoot, block:
      `GATE-BLOCKED (vibeweaver scope): ${target} ${why} Activate it as a trusted vibeweaver project by writing ONLY tests/verification_log.md + tests/assert_artifacts.py; protected evidence stays gated.`,
  })

  // A nested git repo owns scope only when it is actually set up (log +
  // checker). An empty marker / unpinned inline-only repo is not enough to
  // shrink away an active umbrella's security teeth.
  // W25b: the pure-FS worktree detection (`.git` FILE pointers) is
  // authoritative for linked worktrees and platform-robust — prefer it before
  // the subprocess-derived identity branches (Windows probe/spelling variance).
  {
    const wtTop = worktreeTopLevel(nearestExistingDir(fileDir))
    if (wtTop && !samePath(wtTop, activeAbove)) return { root: wtTop, via: "worktree" }
  }
  if (fileGit && !samePath(fileGit, hostGit)) {
    if (trustedNestedProject(fileGit)) return { root: fileGit, via: outsideHost ? "external-git" : "nested-git" }
    // W25 §MA9: a linked WORKTREE checkout (`.git` file pointer into
    // .git/worktrees/, or --git-dir != --git-common-dir) is a checkout of its
    // owning repository, not an untrusted nested repo — the WORKTREE root
    // owns its .vibeweaver state (never the shared common dir). Independent
    // nested repos keep the untrusted-scope block below.
    if (samePath(worktreeTopLevel(fileGit), fileGit)) return { root: fileGit, via: "worktree" }
    const why = `is in git repository ${fileGit} that is not a trusted vibeweaver project.`
    return scopeBlock(activeFallback || fileGit, path.relative(activeFallback || fileGit, resolveWritePath(abs)), why, fileGit)
  }

  // The host itself is a nested repo inside a different active project.
  if (hostGit && activeAbove && !samePath(activeAbove, fileGit)) {
    if (hostTrusted) return { root: host, via: "trusted-workspace-git" }
    // W25 §MA9: a fresh WORKTREE root is its own project root for .vibeweaver
    // state (never the shared common dir above it).
    if (samePath(worktreeTopLevel(hostGit), hostGit)) return { root: hostGit, via: "worktree" }
    return scopeBlock(activeAbove, host,
      `is a nested git repo inside active project ${activeAbove} and is not a trusted vibeweaver project.`, host)
  }
  if (activeHere) return { root: host, via: "workspace" }
  if (activeFallback) return { root: activeFallback, via: "ancestor" }
  if (outsideHost) return null
  // No active umbrella and no nested git boundary: a nested non-git project
  // may own scope (there is no active host to shrink away from).
  for (let d = fileDir; ; d = path.dirname(d)) {
    if (projectMarkerAt(d)) return { root: d, via: "nested-marker" }
    if (!host || d === host || d === path.dirname(d)) break
  }
  return null
}

function rememberSessionRoot(sessionID, root, host = null) {
  if (!sessionID || typeof sessionID !== "string" || !root) return
  const hostAbs = host ? canonicalPath(host) : null
  root = canonicalPath(root)
  // A write into another workspace must not re-bind this session's memory /
  // idle / compaction root to that foreign project.
  if (hostAbs && isOutside(hostAbs, root)) return
  SESSION_ROOT.delete(sessionID)
  SESSION_ROOT.set(sessionID, { root, host: hostAbs })
  if (SESSION_ROOT.size > 500) {
    const firstKey = SESSION_ROOT.keys().next().value
    SESSION_ROOT.delete(firstKey)
  }
}

function rootForSession(directory, sessionID) {
  // W25: the persisted session→run mapping first — idle/compaction/resume
  // hooks carry no file path and must follow the mapped run root (survives
  // restarts, immune to last-write guessing). Absent mapping → unchanged.
  if (sessionID && directory) {
    const runs = hostSessionRuns(directory)
    const mapped = runs && runs[sessionID]
    if (mapped && typeof mapped.root === "string" && mapped.root) return mapped.root
  }
  const rec = sessionID ? SESSION_ROOT.get(sessionID) : null
  if (rec && rec.host && directory && rec.host === canonicalPath(directory)) return rec.root
  // A session moved to another workspace must not reuse the old workspace's
  // root. The next gated write re-binds it; until then use the local root.
  return findProjectRoot([directory])
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

function writeGateResult(root, flags, cls, blocking, warnings, kinds) {
  try {
    const p = path.join(root, "tests", "gate_result.json")
    const split = splitGateResult({ blocking: blocking || [], kinds: kinds || [] })
    const body = JSON.stringify({
      flags: flags || "(none)", class: cls || "", at: new Date().toISOString(),
      scope: root,
      blocking: blocking || [], warnings: warnings || [],
      violations: split.violations,
      completion: split.completion,
      kinds: kinds || [],
    })
    atomicWriteUnique(p, body)
  } catch (err) {
    // W25: the enforcement record is CRITICAL — a failed persist must fail
    // closed (GATE-CHECK-UNAVAILABLE), never silently claim a final pass (or
    // lose the enforcement record). J6: this is NOT conditional on the
    // agent-controlled VIBEWEAVER_GATE_FINAL env — that switch may only ADD
    // hardening (completion debt becomes blocking), never gate the fail-closed
    // behavior itself (an agent could otherwise silence the critical path by
    // unsetting it). Observation-only paths keep the historical swallow and
    // flag persistError for the next emitted message (see takePersistError).
    throw new Error("GATE-CHECK-UNAVAILABLE (persist failed: " + String((err && err.message) || err) + ")")
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
    let argv = jsonSupported ? ["--json", ...rootArgs, ...flags] : [...rootArgs, ...flags]
    let { err, stdout, stderr } = await runPython(script, argv, root)
    let out = `${stdout}${stderr ? "\n" + stderr : ""}`.trim()
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
        // W23: retry the SAME flag combo in prose mode. The old `continue`
        // consumed the only combo and turned a prose failure into warnings
        // (a fail-open; pinned by D4-5).
        argv = [...rootArgs, ...flags]
        ;({ err, stdout, stderr } = await runPython(script, argv, root))
        out = `${stdout}${stderr ? "\n" + stderr : ""}`.trim()
      } else {
        attempts.push({ flags: label, output: out, terminal: "placeholder" })
        continue
      }
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

const VIOLATION_CODES = new Set(["14", "15", "18", "22", "evidence-lock", "checker-pin"])
const COMPLETION_CODES = new Set([
  "1", "2", "3", "4", "5", "5b", "6", "7", "8", "9", "10", "11",
  "12", "12b", "13", "16", "17", "17a", "17b", "19", "20", "21", "23", "24",
])
function classifyGateFinding(finding) {
  const kind = finding && typeof finding === "object" ? String(finding.kind || "") : ""
  if (kind === "violation" || kind === "unavailable" || kind === "completion") return kind
  const code = finding && typeof finding === "object" ? String(finding.code || "") : ""
  const detail = String(finding && typeof finding === "object" ? finding.detail ?? "" : finding || "")
  const low = detail.toLowerCase()
  if (code === "15b") {
    if (/tamper|hash mismatch|sealed evidence missing|manifest\.json missing|partial seal/.test(low)) return "violation"
    return "completion"
  }
  if (VIOLATION_CODES.has(code)) return "violation"
  if (code === "21" && /cannot verify|could not run|failed inside an existing \.git|timed out|overflowed|fail-closed/.test(low)) return "unavailable"
  if (["3", "10", "11"].includes(code) && /not a real png|wrong format|magic|is not a real/.test(low)) return "violation"
  if (/secret scan:|evidence-lock fail|checker was modified|class contradiction|test-change guard:/.test(low)) return "violation"
  if (COMPLETION_CODES.has(code)) return "completion"
  // Unknown structured findings are not safely classifiable as debt.
  return "unavailable"
}

function collectMessages(attempts) {
  const blocking = []
  const kinds = []
  const warnings = []
  const seen = new Set()
  const push = (arr, msg, kind = "completion") => {
    if (!msg || seen.has(msg)) return
    seen.add(msg)
    arr.push(msg)
    if (arr === blocking) kinds.push(kind)
  }
  for (const a of attempts) {
    if (a.terminal) {
      // "legacy" is an upgrade hint (the check still ran in prose mode below);
      // every other terminal means the check could NOT run → hard block.
      if (a.terminal === "legacy") push(warnings, TERMINAL_MESSAGES.legacy)
      else push(blocking, TERMINAL_MESSAGES[a.terminal] || `verification check unavailable (${a.terminal})`, "unavailable")
      continue
    }
    if (Array.isArray(a.fails) && a.fails.length) {
      for (const f of a.fails) {
        const detail = f && typeof f === "object" ? String(f.detail ?? f.code ?? f) : String(f)
        if (f && typeof f === "object" && f.severity === "warn") push(warnings, detail)
        else push(blocking, detail, classifyGateFinding(f))
      }
      continue
    }
    for (const line of String(a.output || "").split("\n")) {
      const m = line.trim()
      if (m.startsWith("WARN ")) push(warnings, m.slice(5))
      else if (m.startsWith("- ")) {
        const detail = m.slice(2)
        // Prose-only checkers cannot carry the structured completion/violation
        // kind. Fail closed as "unavailable"; never guess this debt is safe.
        push(blocking, detail, "unavailable")
      }
    }
  }
  if (!blocking.length && !warnings.length && attempts.length) {
    push(blocking, attempts[attempts.length - 1].output.slice(0, 400), "unavailable")
  }
  return { blocking, warnings, kinds }
}

function splitGateResult(result) {
  const violations = []
  const completion = []
  const violationKinds = []
  const completionKinds = []
  for (let i = 0; i < (result.blocking || []).length; i++) {
    const msg = result.blocking[i]
    const kind = (result.kinds && result.kinds[i]) || classifyGateFinding(msg)
    if (kind === "completion") {
      completion.push(msg)
      completionKinds.push(kind)
    } else {
      violations.push(msg)
      violationKinds.push(kind)
    }
  }
  return { violations, completion, violationKinds, completionKinds }
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

async function checkGate(root, force = false) {
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
      return { blocking: [pin.reason], kinds: ["violation"], warnings: pinWarnings, attempts: ["(checker-pin)"] }
    }
    const key = depFingerprint(root)
    const lossy = LOSSY_DIGEST.has(root) || LOSSY_FINGERPRINT.has(root)
    if (!force && !lossy && RESULT_CACHE.has(key)) {
      const cached = RESULT_CACHE.get(key) // may be null = cached PASS
      if (cached === null && pinWarnings.length) return { blocking: [], warnings: pinWarnings }
      return cached
    }
    const r = await runAssert(root)
    let result
    if (r.ok) {
      if (!force && !lossy) {
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
      const { blocking, warnings, kinds } = collectMessages(r.attempts)
      const allWarn = [...pinWarnings, ...warnings]
      result = { scope: root, blocking, kinds, warnings: allWarn, attempts: r.attempts.map((a) => `[${a.flags}]`) }
      // W19: details always on disk; the de-dup latch is computed at DISPLAY
      // time in blockMessage (a cached result must not replay a stale `repeat`).
      writeGateResult(root, (r.attempts && r.attempts.length ? "(failed)" : "(none)"), "", blocking, allWarn, kinds)
    }
    if (!force && !lossy) {
      if (RESULT_CACHE.size >= RESULT_CACHE_MAX) RESULT_CACHE.clear()
      RESULT_CACHE.set(key, result)
    }
    return result
  }
  const failures = inlineCheck(root)
  if (failures.length) return {
    scope: root, blocking: failures, kinds: failures.map(() => "completion"),
    warnings: [], attempts: [], inline: true,
  }
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
    // W25: the persisted block carries its run scope key (legacy: unchanged keys)
    const stallScope = stateScopeKey(root)
    if (stallScope !== root) st.scope = stallScope
    atomicWriteUnique(p, JSON.stringify(st))
    return msg
  } catch (err) {
    PERSIST_ERROR = "persist failed: " + String((err && err.message) || err)
    return null
  }
}

function blockMessage(root, result) {
  // W19 latch at DISPLAY time (not cached): hash the current failure list and
  // only re-dump the full banner when it CHANGED. Details are always on disk.
  const hash = createHash("sha256").update(JSON.stringify(result.blocking)).digest("hex")
  const repeat = LAST_BLOCK.get(root) === hash
  LAST_BLOCK.set(root, hash)
  const unavailable = (result.kinds || []).length > 0
    && (result.kinds || []).every((k) => k === "unavailable")
  const prefix = unavailable
    ? "GATE-CHECK-UNAVAILABLE (vibeweaver physical gate)"
    : "GATE-BLOCKED (vibeweaver integrity)"
  if (repeat) {
    return `${prefix}: WRITE SUCCEEDED — ${result.blocking.length} hard blocking item(s) UNCHANGED since last edit. Full list: tests/gate_result.json. THE WRITE LANDED; this is an integrity/unavailable error, not a completion-debt note.`
  }
  const lines = [
    `${prefix}: WRITE SUCCEEDED — a hard violation or unavailable check was found; this is NOT completion debt and NOT an execution stop. The task cannot be completed until these are fixed:`,
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
  lines.push("This gate is re-checkable: fix the violation, then your next write/edit re-runs it automatically. If the finding is a false positive, record the evidence and escalate to the user; bypassing via bash or disabling the gate is not a repair.")
  return lines.join("\n")
}

function completionLatchKey(root, sessionID) {
  // W25: completion debt is scoped per run/attempt when a RunContext exists
  // (legacy: the exact pre-W25 key).
  return [stateScopeKey(root), sessionID || "(none)", taskKeyOf(root)].join("\n")
}

function clearCompletionLatch(root, sessionID) {
  for (const [key, rec] of LAST_COMPLETION) {
    if (rec.root === root && (!sessionID || rec.sessionID === sessionID)) LAST_COMPLETION.delete(key)
  }
}

function clearCompletionLatchForSession(sessionID) {
  if (!sessionID) return
  for (const [key, rec] of LAST_COMPLETION) {
    if (rec.sessionID === sessionID) LAST_COMPLETION.delete(key)
  }
}

function completionNotice(root, items, sessionID = null) {
  if (!items.length) return null
  const hash = createHash("sha256").update(JSON.stringify(items)).digest("hex")
  const key = completionLatchKey(root, sessionID)
  const prev = LAST_COMPLETION.get(key)
  if (prev && prev.hash === hash) return null
  const newItems = prev ? items.filter((m) => !prev.items.includes(m)) : []
  const shown = (newItems.length ? newItems : items).slice(0, 3).map((m) => "- " + m)
  LAST_COMPLETION.set(key, { hash, items, root, sessionID: sessionID || "(none)" })
  if (LAST_COMPLETION.size > 64) LAST_COMPLETION.delete(LAST_COMPLETION.keys().next().value)
  return [
    `[VIBEWEAVER COMPLETION-NOT-READY] WRITE SUCCEEDED — scope=${root} | completion=BLOCKED | ${items.length} completion item(s)${newItems.length ? ` (${newItems.length} new/changed)` : ""} — editing may continue; DECLARING DONE is blocked until \`--final\` exits 0.`,
    ...shown,
    `details: ${path.join(root, "tests", "gate_result.json")}`,
  ].join("\n")
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
  if (!rel || isOutsideRel(rel)) return false
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
    atomicWriteUnique(p, JSON.stringify(stats))
  } catch (err) {
    PERSIST_ERROR = "persist failed: " + String((err && err.message) || err)
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
    if (!rel || isOutsideRel(rel)) return []
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
// Snapshot storage is allowed to be larger than the delivery budget: the
// structured state is rendered/trimmed at delivery time, so the snapshot must
// not pre-truncate the tail before the renderer can see it.
const SNAPSHOT_MAX = 64 * 1024
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
const BOOTSTRAP_VERSION = "2"
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

function readWorkingNote(root) {
  const p = path.join(root, "tests", "working_note.md")
  let fd = null
  try {
    const lst = lstatSync(p)
    // Symlinks are not task state: reject them so an external file can never be
    // snapshotted/delivered as authoritative (dsh guards this the same way).
    if (!lst.isFile()) return { exists: true, ok: false, text: "", truncated: false }
    fd = openSync(p, "r")
    const st = fstatSync(fd)
    if (!(st.size >= 0) || st.size > READ_CAP) {
      return { exists: true, ok: false, text: "", truncated: false }
    }
    if (st.size === 0) return { exists: true, ok: true, text: "", truncated: false }
    // Notes are ≤50 lines; 1MB is already 20x the contract. Read via the fd so
    // a stat→read replacement cannot bypass the size bound (TOCTOU). For a
    // pathological >1MB note, keep a head + tail window so a freeform action
    // at the end is still deliverable.
    const HEAD = 1 << 20
    const TAIL = 256 * 1024
    if (st.size > HEAD) {
      const headBuf = Buffer.alloc(HEAD)
      const headN = readSync(fd, headBuf, 0, HEAD, 0)
      const tailSize = Math.min(st.size - HEAD, TAIL)
      const tailBuf = Buffer.alloc(tailSize)
      const tailN = readSync(fd, tailBuf, 0, tailSize, st.size - tailSize)
      return {
        exists: true, ok: true,
        text: headBuf.subarray(0, headN).toString("utf8") + "\n…[middle omitted]…\n" + tailBuf.subarray(0, tailN).toString("utf8"),
        truncated: true,
      }
    }
    const buf = Buffer.alloc(st.size)
    const n = readSync(fd, buf, 0, st.size, 0)
    return {
      exists: true, ok: true,
      text: buf.subarray(0, n).toString("utf8").replace(/\r\n/g, "\n"),
      truncated: n < st.size,
    }
  } catch {
    return { exists: existsSync(p), ok: false, text: "", truncated: false }
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

function workingNoteOf(root) {
  return readWorkingNote(root).text
}

function utf8Len(s) {
  return Buffer.byteLength(String(s || ""), "utf8")
}

function clipUtf8(s, maxBytes) {
  const buf = Buffer.from(String(s || ""), "utf8")
  if (buf.length <= maxBytes) return buf.toString("utf8")
  let end = Math.max(0, maxBytes)
  while (end > 0 && (buf[end] & 0xc0) === 0x80) end--
  return buf.subarray(0, end).toString("utf8")
}

function clipUtf8End(s, maxBytes) {
  const buf = Buffer.from(String(s || ""), "utf8")
  if (buf.length <= maxBytes) return buf.toString("utf8")
  let start = Math.max(0, buf.length - maxBytes)
  while (start < buf.length && (buf[start] & 0xc0) === 0x80) start++
  return buf.subarray(start).toString("utf8")
}

// Snapshot storage keeps BOTH ends of a long note: structured state lives at
// the head, a freeform `## Next action` often lives at the tail. A plain
// prefix would silently lose the most important part.
function clipUtf8HeadTail(s, maxBytes) {
  if (utf8Len(s) <= maxBytes) return String(s || "")
  const marker = "\n…[snapshot truncated; middle omitted]…\n"
  const markerLen = utf8Len(marker)
  const headBudget = Math.max(0, Math.floor((maxBytes - markerLen) * 0.6))
  const tailBudget = Math.max(0, maxBytes - markerLen - headBudget)
  return clipUtf8(s, headBudget) + marker + clipUtf8End(s, tailBudget)
}

function stateStr(v, max = 480) {
  return typeof v === "string" ? clipUtf8(v.replace(/\s+/g, " ").trim(), max) : ""
}

function stateList(v, maxItems = 200, maxItem = 260) {
  if (!Array.isArray(v)) return { items: [], total: 0 }
  const valid = v.filter((x) => typeof x === "string" && x.trim())
  return {
    items: valid.slice(0, maxItems).map((x) => clipUtf8(x.replace(/\s+/g, " ").trim(), maxItem)),
    total: valid.length,
  }
}

function parseWorkingState(note) {
  const m = String(note || "").match(/```\s*vibeweaver-state\s*\n([\s\S]*?)\n```/i)
  if (!m) return { ok: false, found: false, reason: "no vibeweaver-state block" }
  try {
    const raw = JSON.parse(m[1])
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return { ok: false, found: true, reason: "state block is not a JSON object" }
    }
    const version = raw.version == null ? 1 : raw.version
    if (version !== 1) {
      return { ok: false, found: true, reason: "unsupported schema version: " + String(raw.version).slice(0, 40) }
    }
    for (const key of ["confirmed", "open", "excluded", "key_files", "blocked"]) {
      if (raw[key] != null && !Array.isArray(raw[key])) {
        return { ok: false, found: true, reason: `${key} must be an array` }
      }
      if (Array.isArray(raw[key]) && raw[key].some((x) => typeof x !== "string")) {
        return { ok: false, found: true, reason: `${key} must contain only strings` }
      }
    }
    const state = {
      version,
      task: stateStr(raw.task, 300),
      updated: stateStr(raw.updated, 120),
      current_criterion: stateStr(raw.current_criterion, 180),
      next_action: stateStr(raw.next_action, 900),
      assumption: stateStr(raw.assumption, 420),
      falsifier: stateStr(raw.falsifier, 420),
      confirmed: stateList(raw.confirmed),
      open: stateList(raw.open),
      excluded: stateList(raw.excluded),
      key_files: stateList(raw.key_files, 200, 220),
      blocked: stateList(raw.blocked),
    }
    if (!state.task || !state.next_action) {
      return { ok: false, found: true, reason: "required task/next_action missing or empty" }
    }
    return { ok: true, found: true, state }
  } catch (e) {
    return { ok: false, found: true, reason: "invalid JSON: " + String(e.message || e).slice(0, 120) }
  }
}

function renderWorkingState(state, maxBytes = 3600) {
  const lines = [
    "VIBEWEAVER WORKING-STATE v1 (structured; prioritize next_action over narrative):",
    "task: " + state.task,
  ]
  if (state.current_criterion) lines.push("criterion: " + state.current_criterion)
  lines.push("next_action: " + state.next_action)
  const append = (label, value) => {
    if (!value) return
    if (utf8Len(lines.join("\n") + "\n" + label + " " + value) <= maxBytes) lines.push(label + " " + value)
  }
  append("updated:", state.updated)
  append("assumption:", state.assumption)
  append("falsifier:", state.falsifier)
  const lists = [
    ["open", state.open],
    ["confirmed", state.confirmed],
    ["excluded", state.excluded],
    ["key_files", state.key_files],
    ["blocked", state.blocked],
  ].filter(([, list]) => list && list.total > 0)
  lists.forEach(([label, list], idx) => {
    const remaining = lists.length - idx - 1
    const reserveForLater = remaining * 64
    const header = label + ":"
    if (utf8Len(lines.join("\n") + "\n" + header) > maxBytes - reserveForLater) return
    lines.push(header)
    let shown = 0
    for (const item of list.items) {
      const line = "- " + item
      if (utf8Len(lines.join("\n") + "\n" + line) > maxBytes - reserveForLater - 64) break
      lines.push(line)
      shown++
    }
    const omitted = list.total - shown
    if (omitted > 0) {
      const marker = `- … (+${omitted} more ${label})`
      const shortMarker = `- … +${omitted} ${label}`
      const chosen = utf8Len(lines.join("\n") + "\n" + marker) <= maxBytes - reserveForLater ? marker : shortMarker
      if (utf8Len(lines.join("\n") + "\n" + chosen) <= maxBytes - reserveForLater) lines.push(chosen)
    }
  })
  return clipUtf8(lines.join("\n"), maxBytes)
}

// Legacy freeform notes may contain several "## Next action" sections. The
// LAST non-empty one is the current state; earlier sections are superseded.
// A lazy `$` in a multiline regex would stop at the first line, so use an
// explicit end-of-string lookahead.
function nextActionSections(note) {
  const re = /^##\s+Next action\s*\n([\s\S]*?)(?=^##\s|(?![\s\S]))/gim
  const sections = []
  let m
  while ((m = re.exec(note))) sections.push({ start: m.index, end: re.lastIndex, body: m[1].trim() })
  return sections
}

function extractNextAction(note) {
  const sections = nextActionSections(note)
  for (let i = sections.length - 1; i >= 0; i--) {
    if (sections[i].body) return "## Next action\n" + sections[i].body
  }
  return ""
}

function stripNextActionSections(note, sections) {
  if (!sections.length) return note
  let out = ""
  let cursor = 0
  for (const s of sections) {
    out += note.slice(cursor, s.start)
    cursor = s.end
  }
  return out + note.slice(cursor)
}

function shortenFreeformNote(note, maxBytes = 3600, { fromSnapshot = false, snapshotTruncated = false } = {}) {
  if (utf8Len(note) <= maxBytes) return note
  const sections = nextActionSections(note)
  let current = ""
  for (let i = sections.length - 1; i >= 0; i--) {
    if (sections[i].body) { current = "## Next action\n" + sections[i].body; break }
  }
  const actionText = current ? clipUtf8(current, 1000) : ""
  // Remove ALL Next-action sections from the narrative, so stale sections
  // cannot reappear and content after the current section is preserved.
  const cleaned = stripNextActionSections(note, sections)
  if (actionText && utf8Len(actionText) + utf8Len(cleaned) + 1 <= maxBytes) {
    return actionText + "\n" + cleaned
  }
  const tailBudget = actionText ? 350 : 900
  const tail = clipUtf8End(cleaned, tailBudget)
  const headBudget = Math.max(300, maxBytes - utf8Len(actionText) - utf8Len(tail) - 160)
  const head = clipUtf8(cleaned, headBudget)
  const parts = []
  // Put the extracted action FIRST: any later end-clipping (debt) can only
  // remove narrative/tail, never the next action.
  if (actionText) parts.push(actionText)
  parts.push(head)
  if (utf8Len(cleaned) > utf8Len(head) + utf8Len(tail) + 20) {
    parts.push(fromSnapshot
      ? (snapshotTruncated
        ? "…[working note truncated; the harness snapshot was stored truncated at 64KB]…"
        : "…[working note truncated; the harness snapshot is the authoritative copy]…")
      : "…[working note truncated; full source remains tests/working_note.md]…")
  }
  if (tail && !parts.join("\n").includes(tail)) parts.push(tail)
  return clipUtf8(parts.filter(Boolean).join("\n"), maxBytes)
}

function renderWorkingNote(note, { fromSnapshot = false, snapshotTruncated = false, maxBytes = 3600 } = {}) {
  const parsed = parseWorkingState(note)
  if (parsed.ok) return renderWorkingState(parsed.state, maxBytes)
  const warning = parsed.found
    ? `[WORKING-STATE SCHEMA WARNING] ${parsed.reason}; using freeform fallback.`
    : ""
  const bodyBudget = Math.max(400, maxBytes - utf8Len(warning) - (warning ? 1 : 0))
  const body = shortenFreeformNote(note, bodyBudget, { fromSnapshot, snapshotTruncated })
  return [warning, body].filter(Boolean).join("\n")
}

const SNAPSHOT_FILE = "memory-snapshot.json"

// Harness-owned copy of the working note (wave24): delivery must survive the
// source file disappearing. Snapshot is refreshed whenever the source exists;
// once the source is gone the snapshot IS the memory (the paper's
// deleted-fixture regime made locally testable).
function taskIdentity(root) {
  const log = safeRead(path.join(root, "tests", "verification_log.md")).replace(/\r\n/g, "\n")
  const blocks = log.split(/^(?=## )/m).filter(Boolean)
  let chosen = ""
  const nonTask = /^## (?:Notes|Verification Log|Stop-debt)\b/i
  for (const b of blocks) {
    const h = ((b.match(/^## .+$/m) || [""])[0]).trim()
    if ((h && !nonTask.test(h))
        || /^- iter \d+ (?:PASS|FAIL|PARTIAL|PENDING|POST-HOC)\b/m.test(b)) chosen = b
  }
  if (!chosen) return { heading: "", occurrence: 0, block: "", key: "" }
  const heading = ((chosen.match(/^## .+$/m) || [""])[0]).trim()
  // Same heading reused by a later task still gets a distinct generation.
  let occurrence = 0
  for (const b of blocks) {
    if ((((b.match(/^## .+$/m) || [""])[0]).trim()) === heading) occurrence++
  }
  const acceptance = createHash("sha256").update(safeRead(path.join(root, "tests", "acceptance.md"))).digest("hex")
  return { heading, occurrence, block: chosen, key: `${heading}\n#${occurrence}\n${acceptance}` }
}

function taskKeyOf(root) {
  return taskIdentity(root).key
}

function taskFinalized(root) {
  const block = taskIdentity(root).block
  if (!block) return false
  // A failed final run must not close the task. Only a green, unfenced
  // `- final-run: --final … pass>=1/fail=0` is a completion marker.
  let inFence = false
  const finals = []
  for (const line of block.split("\n")) {
    if (/^\s*```/.test(line)) { inFence = !inFence; continue }
    if (!inFence && /^- final-run:\s*--final\b/.test(line)) finals.push(line)
  }
  if (!finals.length) return false
  // The LAST final run decides; an earlier green followed by a failed run is
  // not a completion. `pass=0` is never green.
  return /\bpass=[1-9]\d*\s*\/\s*fail=0\b/.test(finals[finals.length - 1])
}

function snapshotWorkingNote(root) {
  try {
    const rel = path.join("tests", "working_note.md")
    const dir = path.join(root, STATE_DIR)
    // `.vibeweaver` itself may be a symlink to an external directory; never
    // write task state outside the project (dsh guards both sides the same way).
    if (!relativeUnderRoot(root, resolveWritePath(dir))) return
    const p = path.join(dir, SNAPSHOT_FILE)
    if (!relativeUnderRoot(root, resolveWritePath(p))) return
    // Distinguish "the file is genuinely empty" from "the read failed".
    // A transient EACCES/EISDIR/symlink read must NEVER delete a valid
    // snapshot: the snapshot is the only recovery path when the source is
    // gone. Oversize-but-readable notes still refresh the snapshot with a
    // flagged head+tail, so an older task state cannot resurrect.
    const read = readWorkingNote(root)
    if (!read.ok) return
    if (!read.text.trim()) {
      // A genuinely empty note is a deliberate reset. Do not let an older
      // snapshot become authoritative when the file is later deleted.
      rmSync(p, { force: true })
      return
    }
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
    atomicWriteUnique(p, JSON.stringify({
      rel, text: clipUtf8HeadTail(read.text, SNAPSHOT_MAX), truncated: read.truncated || utf8Len(read.text) > SNAPSHOT_MAX,
      t: Date.now(), taskKey: taskKeyOf(root), finalized: taskFinalized(root),
    }))
  } catch (err) {
    PERSIST_ERROR = "persist failed: " + String((err && err.message) || err)
    /* snapshot is best-effort: delivery still works while the file lives */
  }
}

function snapshotTextOf(root) {
  try {
    const dir = path.join(root, STATE_DIR)
    if (!relativeUnderRoot(root, resolveWritePath(dir))) return { text: "", truncated: false }
    const p = path.join(dir, SNAPSHOT_FILE)
    if (!relativeUnderRoot(root, resolveWritePath(p))) return { text: "", truncated: false }
    if (!existsSync(p)) return { text: "", truncated: false }
    const d = JSON.parse(safeRead(p) || "null")
    if (!d || typeof d.text !== "string") return { text: "", truncated: false }
    // F4/W23: a deleted note is restorable ONLY for the same active task.
    // Legacy snapshots without taskKey, a finalized task, or a new task key
    // must never be resurrected as authoritative.
    if (d.finalized || taskFinalized(root)) return { text: "", truncated: false }
    if (!d.taskKey || d.taskKey !== taskKeyOf(root)) return { text: "", truncated: false }
    // Legacy snapshots (no `truncated` field) were capped at 4KB; flag the
    // exact-cap case conservatively. New snapshots carry the explicit flag, so
    // an exactly-64KB note is NOT falsely labelled truncated.
    const legacyTruncated = d.truncated == null && utf8Len(d.text) === MEMORY_BUNDLE_MAX
    return { text: d.text, truncated: !!d.truncated || legacyTruncated }
  } catch {
    return { text: "", truncated: false }
  }
}

// The delivered bundle: working note verbatim (bounded) + resume rule. With
// no note, deliver the create instruction instead — the boundary is exactly
// the moment the ledger matters most.
function gateDebtBrief(root) {
  try {
    const d = JSON.parse(safeRead(path.join(root, "tests", "gate_result.json")) || "{}")
    const items = Array.isArray(d.completion) ? d.completion : []
    if (!items.length) return ""
    const concise = items.slice(0, 3).map((m) => clipUtf8(String(m).replace(/\s+/g, " ").trim(), 100))
    return "COMPLETION DEBT (current checker): " + concise.map((m) => "- " + m).join(" ") + (items.length > 3 ? ` … (+${items.length - 3})` : "")
  } catch {
    return ""
  }
}

function gateDebtPart(root) {
  const debt = gateDebtBrief(root)
  return debt ? clipUtf8(debt, 430) : ""
}

function withGateDebt(bundle, root, debtPart = gateDebtPart(root)) {
  if (!debtPart) return clipUtf8(bundle, MEMORY_BUNDLE_MAX)
  const body = clipUtf8(bundle, MEMORY_BUNDLE_MAX - utf8Len(debtPart) - 1)
  return body + "\n" + debtPart
}

function compactStateBundle(root) {
  const read = readWorkingNote(root)
  const noteExists = read.exists
  let note = read.text.trim()
  let fromSnapshot = false
  let snapshotTruncated = false
  let snapshotUnreadable = false
  if (read.ok) {
    // Also clears an older snapshot when the file is genuinely empty.
    if (note || noteExists) snapshotWorkingNote(root)
  } else {
    const snap = snapshotTextOf(root)
    note = snap.text.trim()
    fromSnapshot = !!note
    snapshotTruncated = snap.truncated
    snapshotUnreadable = read.exists && !!note
  }
  const debtPart = gateDebtPart(root)
  const debtReserve = debtPart ? utf8Len(debtPart) + 1 : 0
  const budgetFor = (header, footer) =>
    Math.max(600, MEMORY_BUNDLE_MAX - debtReserve - utf8Len(header) - utf8Len(footer) - 2)
  if (note && fromSnapshot) {
    const sourceState = snapshotUnreadable
      ? "is unreadable (permissions or a non-regular file)"
      : "is no longer present"
    const header = "VIBEWEAVER WORKING-STATE (harness snapshot — the source tests/working_note.md " + sourceState + "; this copy is authoritative" +
      (snapshotTruncated ? "; the stored copy was truncated at 64KB, so the tail may be missing" : "") + "):"
    const footer = "Resume rule: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md BEFORE the next edit; the working note lives in this harness snapshot now."
    return withGateDebt([
      header,
      renderWorkingNote(note, { fromSnapshot: true, snapshotTruncated, maxBytes: budgetFor(header, footer) }),
      footer,
    ].join("\n"), root, debtPart)
  }
  if (!note) {
    const acc = safeRead(path.join(root, "tests", "acceptance.md"))
    const capLine = (acc.split("\n").find((l) => l.includes("cap=5")) || "").trim()
    let header
    let instruction
    if (!noteExists) {
      header = "VIBEWEAVER COMPACT-RESUME (machine-delivered by vibeweaver-gate — no tests/working_note.md exists):"
      instruction = "After this compaction, BEFORE the next edit: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md, and CREATE tests/working_note.md (preferred: a fenced `vibeweaver-state` JSON v1 block with task + next_action; a freeform confirmed/doubted/excluded/open ledger + key locations + dead ends + next action is also accepted; <=50 lines). The gate re-delivers this note at every compaction boundary."
    } else if (!read.ok) {
      header = "VIBEWEAVER COMPACT-RESUME (machine-delivered by vibeweaver-gate — tests/working_note.md exists but is unreadable):"
      instruction = "After this compaction, BEFORE the next edit: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md, fix tests/working_note.md permissions/type (symlinks and non-regular files are not task state), then REWRITE it (preferred: a fenced `vibeweaver-state` JSON v1 block with task + next_action; <=50 lines). The gate re-delivers this note at every compaction boundary."
    } else {
      header = "VIBEWEAVER COMPACT-RESUME (machine-delivered by vibeweaver-gate — tests/working_note.md exists but is empty):"
      instruction = "After this compaction, BEFORE the next edit: re-read tests/acceptance.md and the last 20 lines of tests/verification_log.md, and REWRITE tests/working_note.md (preferred: a fenced `vibeweaver-state` JSON v1 block with task + next_action; a freeform confirmed/doubted/excluded/open ledger + key locations + dead ends + next action is also accepted; <=50 lines). The gate re-delivers this note at every compaction boundary."
    }
    return withGateDebt([
      header,
      instruction,
      capLine ? `Acceptance first line: ${capLine}` : "",
    ]
      .filter(Boolean)
      .join("\n")
      .slice(0, MEMORY_BUNDLE_MAX - debtReserve), root, debtPart)
  }
  const header = "VIBEWEAVER WORKING-STATE (machine-delivered by vibeweaver-gate; this ledger is task state and takes precedence over the compacted summary — preserve its essentials):"
  const footer = "Resume rule: after compaction re-read tests/working_note.md, tests/acceptance.md, and the last 20 lines of tests/verification_log.md BEFORE the next edit."
  return withGateDebt([
    header,
    renderWorkingNote(note, { maxBytes: budgetFor(header, footer) }),
    footer,
  ].join("\n"), root, debtPart)
}

function resumeCueNote(root) {
  const notePath = path.join(root, "tests", "working_note.md")
  const read = readWorkingNote(root)
  if (read.ok && read.text.trim()) {
    return "[vibeweaver] tests/working_note.md exists (task state ledger) — read it first (§3.3 re-entry); the gate re-delivers it at every compaction boundary."
  }
  if (read.exists && !read.ok) {
    return "[vibeweaver] tests/working_note.md exists but is unreadable (permissions or non-regular file) — fix it and rewrite before the next edit (§A7.15); the gate re-delivers it at every compaction boundary."
  }
  if (read.exists) {
    return "[vibeweaver] tests/working_note.md exists but is empty — rewrite it before the next edit (§A7.15); the gate re-delivers it at every compaction boundary."
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
    // W25: the persisted block carries its run scope key (legacy: unchanged keys)
    const memScope = stateScopeKey(root)
    if (memScope !== root) st.scope = memScope
    atomicWriteUnique(p, JSON.stringify(st))
  } catch (err) {
    PERSIST_ERROR = "persist failed: " + String((err && err.message) || err)
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

const DESTRUCTIVE_ALLOW = /(^|\/)(node_modules|\.venv|venv|dist|build|target|coverage|\.next|\.pytest_cache|__pycache__)(\/|$)|^(\$[A-Za-z0-9_]*(\/|$)|\/tmp(\/|$))/

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
  const m = c.match(/(?:^|[;&|]\s*)(?:sudo\s+)?rm\s+(?:-[a-zA-Z]*r[a-zA-Z]*\s+)+([^;&|]+)/)
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
  const scope = findProjectRootForWrite(directory, abs)
  if (!scope) return null
  if (scope.block) {
    // Bootstrap-only allowlist: log + checker. Protected evidence and source
    // stay denied.
    if (scope.evidenceRoot && isActivationPath(scope.evidenceRoot, abs)) return null
    return scope.block
  }
  const risk = riskPathBlock(scope.root, abs)
  if (risk) return risk
  return null
}

function gateCheckWrite(directory, filePath, sessionID = null) {
  if (process.env.VIBEWEAVER_GATE === "off") return Promise.resolve(null)
  // relative args.path resolves against the host directory (review A: cwd
  // resolution made a tests/ write look like a non-evidence write)
  if (filePath && !path.isAbsolute(filePath) && directory) filePath = path.resolve(directory, filePath)
  const scope = findProjectRootForWrite(directory, filePath)
  const root = scope && scope.root
  if (!root) return Promise.resolve(null)
  if (scope.block) {
    if (scope.evidenceRoot && isActivationPath(scope.evidenceRoot, filePath)) {
      const cues = cueNotes(scope.evidenceRoot, filePath)
      return Promise.resolve(cues.length ? { notes: cues } : null)
    }
    return Promise.resolve({ block: scope.block })
  }
  rememberSessionRoot(sessionID, root, directory)
  // W25: first-hook session→run binding (no-op without a RunContext)
  recordSessionRun(directory, sessionID, root, loadRunContext(root))
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
      clearCompletionLatch(root, sessionID) // repairs happen on protected evidence too
      const notes = [...cues, ...((r && r.notes) || [])]
      return notes.length ? { notes } : null
    })
  }
  // evidence-fix path must never be gated (same rule as the audit
  // plugin): writes under tests/ or memory/ ARE the evidence repair
  // itself — gating them creates the first-log catch-22 deadlock. A repair
  // write also re-arms completion debt so an evidence-only fix cannot leave
  // a stale latch hiding a regression.
  if (isEvidencePath(root, filePath)) {
    clearCompletionLatch(root, sessionID)
    return Promise.resolve(cues.length ? { notes: cues } : null)
  }
  // `tests/gate_result.json` is agent-writable but excluded from the cache
  // digest as gate-owned noise. Force one fresh checker run for that target
  // so a secret written there cannot ride a cached PASS.
  const force = relativeUnderRoot(root, filePath) === "tests/gate_result.json"
  return checkGate(root, force).then((result) => {
    // O1/W23: RED must not blind the stall observer. Record EVERY gated
    // source edit before deciding whether to throw.
    const stall = stallObservation(root, filePath || "(unknown file)")
    const split = result
      ? splitGateResult(result)
      : { violations: [], completion: [], violationKinds: [], completionKinds: [] }
    if (process.env.VIBEWEAVER_GATE_FINAL === "1" && split.completion.length) {
      // Completion mode is the second line of defense: debt cannot remain a
      // note once the host explicitly requests --final semantics.
      split.violations.push(...split.completion)
      split.violationKinds.push(...split.completion.map(() => "violation"))
      split.completion = []
    }
    if (split.violations.length) {
      let msg = blockMessage(root, {
        ...result,
        blocking: split.violations,
        kinds: split.violationKinds,
      })
      if (cues.length) msg += "\n" + cues.join("\n")
      if (stall) msg += "\n[GATE-WARNING (vibeweaver-stall)] " + stall
      // W25: a swallowed observation-only persist failure is surfaced in the
      // next emitted message (then cleared) — never silently dropped.
      const peBlock = takePersistError()
      if (peBlock) msg += "\n" + peBlock
      return { block: msg }
    }
    const notes = [...cues]
    if (result && result.warnings.length) {
      notes.push("[GATE-WARNING (vibeweaver)] non-blocking: " + result.warnings.join("; ") + " — fix before the final [Verification Gate] line.")
    }
    if (split.completion.length) {
      const notice = completionNotice(root, split.completion, sessionID)
      if (notice) notes.push(notice)
    } else {
      clearCompletionLatch(root, sessionID)
    }
    if (stall) notes.push("[GATE-WARNING (vibeweaver-stall)] " + stall)
    const peNote = takePersistError()
    if (peNote) notes.push(peNote)
    return notes.length ? { notes } : null
  })
}

// Session-idle re-check: returns { blocking } when the gate is RED.
function gateIdleCheck(directory, sessionID = null) {
  if (process.env.VIBEWEAVER_GATE === "off") return Promise.resolve(null)
  const root = rootForSession(directory, sessionID)
  if (!root) return Promise.resolve(null)
  return checkGate(root).then((result) => {
    if (!result || !result.blocking.length) return null
    const split = splitGateResult(result)
    if (!split.violations.length && !split.completion.length) return null
    return { root, hard: split.violations, completion: split.completion }
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
  if (!result || typeof result !== "object") return false
  try {
    if (typeof result.content === "string") {
      result.content = result.content + "\n" + text
      return true
    }
    if (Array.isArray(result.content)) {
      result.content.push({ type: "text", text })
      return true
    }
    if (result.metadata && typeof result.metadata === "object") {
      result.metadata.vibeweaverGate = text
      return true
    }
    result.metadata = { vibeweaverGate: text }
    return true
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
    return true
  } catch {
    /* fully-frozen event — a cue note must never break a landed write */
    return false
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
    const root = rootForSession(directory, sessionID)
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
      if (input.tool === "bash" || input.tool === "shell") {
        // Host without a pre-hook: the guard cannot stop execution, but it
        // must not disappear silently — surface a post-hoc GATE-WARNING.
        const cmd = input.args && typeof input.args.command === "string" ? input.args.command : ""
        const root = rootForSession(directory, input.sessionID)
        if (root && cmd) {
          const warn = riskCommandBlock(root, cmd) || destructiveBlock(root, cmd)
          if (warn) {
            output.output = (output.output ? output.output + "\n" : "") +
              "[GATE-WARNING (vibeweaver)] post-hoc (host has no pre-execution hook): " + warn
          }
        }
        return
      }
      if (!GATED_TOOLS.has(input.tool)) return
      const filePath = writePathFromArgs(input.args)
      const r = await gateCheckWrite(directory, filePath, input.sessionID)
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
      const root = rootForSession(directory, input && input.sessionID)
      if (!root) return
      clearCompletionLatchForSession(input && input.sessionID) // result is about to leave context
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
      const root = rootForSession(directory, sid)
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
          clearCompletionLatchForSession(sid) // the tool result carrying the note is gone
        }
        return
      }
      if (!event || event.type !== "session.idle") return
      const payload = (event.data || event.properties) || {}
      const r = await gateIdleCheck(directory, payload.sessionID)
      if (r && r.hard.length) {
        await logToHost(client && client.app, {
          service: "vibeweaver-gate",
          level: "warn",
          message: "Session idle with hard verification gate",
          extra: { blocking: r.hard.slice(0, 20), scope: r.root },
        })
      } else if (r && r.completion.length) {
        await logToHost(client && client.app, {
          service: "vibeweaver-gate",
          level: "info",
          message: `Session idle with completion debt (${r.completion.length})`,
          extra: { completion: r.completion.slice(0, 3), scope: r.root },
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
    const r = await gateCheckWrite(directory, filePath, event.sessionID)
    if (r && r.block) throw new Error(r.block)
    if (r && r.notes) {
      const delivered = appendNotesToV2Result(event, r.notes)
      if (!delivered && r.notes.some((n) => n.includes("COMPLETION-NOT-READY"))) {
        clearCompletionLatchForSession(event.sessionID)
      }
    }
    const cue = firstTouchCue(directory, event.sessionID)
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
              clearCompletionLatchForSession(sid2)
            }
          }
          if (!v2EventIsIdle(event)) continue
          const payloadIdle = (event.data || event.properties) || {}
          const r = await gateIdleCheck(directory, payloadIdle.sessionID)
          if (r && r.hard.length) {
            await logToHost(null, {
              service: "vibeweaver-gate",
              level: "warn",
              message: "Session idle with hard verification gate",
              extra: { blocking: r.hard.slice(0, 20), scope: r.root },
            })
          } else if (r && r.completion.length) {
            await logToHost(null, {
              service: "vibeweaver-gate",
              level: "info",
              message: `Session idle with completion debt (${r.completion.length})`,
              extra: { completion: r.completion.slice(0, 3), scope: r.root },
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

// W25 test seams (properties on the server function — the module export
// shape stays exactly { id, server, setup }; loaders only read the default
// object's keys and named exports, never function properties). The selftest
// exercises the run-aware helpers through these; hosts never see them.
server.loadRunContext = loadRunContext
server.atomicWriteUnique = atomicWriteUnique
server.stateScopeKey = stateScopeKey

export default {
  id: "vibeweaver-gate",
  server,
  setup,
}
