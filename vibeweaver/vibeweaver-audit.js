import { closeSync, existsSync, fstatSync, lstatSync, mkdirSync, openSync, readFileSync, readlinkSync, realpathSync, renameSync, statSync, writeFileSync } from "node:fs"
import { createHash } from "node:crypto"
import path from "node:path"
import os from "node:os"
import { fileURLToPath, pathToFileURL } from "node:url"

// vibeweaver-audit — Tier-0/1/2 session auditor for the vibeweaver skill.
//
// Tier 0 (passive): observes assistant text parts + tool calls. Under
//   opencode v1 this uses the generic `event` hook (message.part.updated
//   events carry {type, properties:{sessionID, part}}); under opencode v2
//   it uses ctx.event.subscribe() (session.text.delta /
//   session.message.content.updated / session.skill.activated events) plus
//   ctx.tool.hook() for tool observations. No model cooperation needed.
// Tier 1 (mechanical, OK/BAD/UNCERTAIN): artifact checks, narration
//   markers, and claim<->artifact cross-checks of the [Verification Gate]
//   line (pure logic in scripts/vibeweaver-audit-core.js). A BAD final audit
//   latches RED at the project root and blocks the latching session's next
//   non-test write until it self-corrects (fix evidence + corrected gate
//   line, re-checked at every session idle).
//   The latch is SESSION-SCOPED: a truncated/aborted session must not be
//   able to hold the next task hostage, so the latch releases on the owning
//   session's own new task (tests/acceptance.md rewritten after the latch),
//   after redTtlHours (default 24, audit.json), or for legacy boolean state
//   (D3, 2026-10-15: a FOREIGN session's write releases NOTHING — a subagent
//   write used to clear the latch and bypass the whole gate; foreign writes
//   are blocked too). Every release is recorded in state (bounded) + app log
//   + a "## Stale RED releases" section of tests/gate_audit.md — never
//   silently dropped.
//   Any test/tests directory in the project (tests/, dev/tests/, src/test/…)
//   stays writable while RED so the evidence-fix path never deadlocks.
// Tier 2 (escalation): UNCERTAIN / sampling / high-risk -> escalate=true in
//   tests/gate_audit.md; skill protocol then requires a fresh-brain review.
//
// OPENCODE DUAL-COMPAT CONTRACT (v1 + v2):
// This module default-exports ONE object { id, server, setup }.
//   - opencode v1 (>= 1.18.29): the loader's readV1Plugin detects the
//     default object and calls server(input, options) -> the v1 hooks map
//     ("tool.execute.before" / "event"). Older v1 releases fall back to
//     iterating exports and also accept an object with a function `server`
//     property — one export means one registration either way.
//   - opencode v2 (>= 2.0.0): the loader's PluginModule schema decodes ONLY
//     the default export against { id, setup } (excess keys like `server`
//     are tolerated) and calls setup(ctx); hooks are registered via
//     ctx.tool.hook(...) and events via ctx.event.subscribe().
// Both adapters drive the SAME audit machine (createAuditMachine), so latch
// state (.vibeweaver/audit-state.json) and behavior are identical across
// versions. Keep exactly this one export: any extra non-function export
// breaks the legacy v1 iterator, any extra plugin-function export risks
// double registration.
//
// Only sessions that loaded the vibeweaver skill are audited.
// Disable: VIBEWEAVER_AUDIT=off. Core path override: VIBEWEAVER_AUDIT_CORE.

const STATE_DIR = ".vibeweaver"
const STATE_FILE = "audit-state.json"
const AUDIT_FILE = "gate_audit.md"
const GATE_MARKER = "[Verification Gate]"
const TEXT_CAP_HEAD = 20_000
const TEXT_CAP_TAIL = 150_000
const TOOL_CAP = 400
const IN_CAP = 400
const OUT_CAP = 300
const RED_TTL_HOURS_DEFAULT = 24
const RELEASES_CAP = 5

// Bounded input-size estimate for tool arguments (SIGTRAP hardening round 3,
// 2026-10-17): `canonicalJson(inp)` deep-copies and stringifies the FULL
// argument object — a multi-MB `write`/`ssh_sftp_write` content re-observed
// N times (v1 re-emits the part on every state change) is N full copies of
// the payload (the crashed processes: 58.8GB malloc / 12GB JS heap). Strings
// cost their length (O(1) to read), the walk itself is step-bounded; over
// budget the caller records a truncated identity instead — which is exactly
// the F10 semantics oversized args already had.
function inputTooBig(inp, budget = 8192) {
  let cost = 2
  const stack = [inp]
  let steps = 0
  while (stack.length) {
    if (++steps > 2000) return true
    const v = stack.pop()
    if (typeof v === "string") cost += v.length + 2
    else if (Array.isArray(v)) {
      cost += 2
      for (let i = 0; i < v.length; i++) stack.push(v[i])
    } else if (v && typeof v === "object") {
      cost += 2
      for (const k of Object.keys(v)) {
        cost += k.length + 3
        stack.push(v[k])
      }
    } else cost += 4
    if (cost > budget) return true
  }
  return false
}

// ---------- helpers (never throw) ----------

function sizeOf(p) {
  try {
    return statSync(p).size
  } catch {
    return 0
  }
}

// Bounded reader (class contract, 2026-10-17 — Bun #26323: readFileSync on a
// >2GB file is an uncatchable SIGTRAP in the runtime opencode bundles):
// fd-based size gate (open → fstat → read SAME fd — no stat/read TOCTOU);
// a bigger file is treated as absent. ALL reads go through here.
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

// A path is exempt from RED blocking when it lies inside the project root
// and any segment of its project-relative path is a test directory —
// covers tests/, dev/tests/, src/test/, … (the evidence-fix path must
// never deadlock, per §A4.4.2 "tests/** stays writable").
// D3 (2026-10-15): the check runs on a NORMALIZED path — the raw string
// `"<root>/tests/../src/x.ts"` used to pass the segment test and exempt a
// source write from the RED latch. New write targets may not exist yet, so
// normalization = realpath of the nearest EXISTING ancestor + the remaining
// lexical segments (realpathSync on the file itself would throw ENOENT);
// when nothing exists, lexical path.resolve kills `..` anyway.
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

// Host arg-shape parity (W18 G2, review A Critical #2): the canonical
// opencode write/edit tools carry the target as `args.path` ({path, content} /
// {path, oldString, newString}); `args.filePath` is only one adapter shape.
// Reading `filePath` alone left the RED-latch test-dir exemption (the
// evidence-fix path below) unreachable on the REAL host shape — a latched
// session could not write tests/acceptance.md despite the block message
// promising it. Same contract as vibeweaver-gate.js `writePathFromArgs`.
function writePathFromArgs(args) {
  if (!args || typeof args !== "object") return null
  const seen = []
  for (const key of ["filePath", "path", "file_path"]) {
    const v = args[key]
    if (typeof v === "string" && v) seen.push(v)
  }
  if (!seen.length) return null
  // Two DIFFERENT target spellings in one call is an unknown host shape —
  // fail closed (full gate), same contract as vibeweaver-gate.js.
  if (seen.some((v) => v !== seen[0])) return null
  return seen[0]
}

function isTestDirPath(root, filePath) {
  if (typeof filePath !== "string" || !filePath) return false
  const normRoot = resolveWritePath(root)
  const normFile = resolveWritePath(filePath)
  const rel = normFile.startsWith(normRoot + path.sep) ? normFile.slice(normRoot.length + path.sep.length) : null
  if (rel == null) return false
  return rel.split(/[\\/]/).some((seg) => {
    // EXACT name match (W18 review r2): case-folding made `Tests/` a false
    // exemption on case-sensitive filesystems. Nested test dirs
    // (src/tests/, dev/tests/) stay exempt by design — the RED-latch
    // evidence-fix path must reach ANY test directory.
    return seg === "test" || seg === "tests"
  })
}

// Normalize the stored red latch to { sessionID, ts, bad } | null.
// Legacy boolean `true` (pre session-scoping) → unknown latcher, born stale:
// it releases on the first observed session write/idle or via TTL.
function readLatch(rootEntry) {
  const r = rootEntry && rootEntry.red
  if (!r) return null
  if (typeof r === "object")
    return {
      sessionID: typeof r.sessionID === "string" ? r.sessionID : null,
      ts: typeof r.ts === "number" ? r.ts : 0,
      bad: Number.isFinite(r.bad) ? r.bad : null,
    }
  return { sessionID: null, ts: 0, bad: null }
}

// Core module resolution: env override → installed skill dir (sibling of the
// plugins dir) → repo-relative scripts/ (dev + selftest). Fail-safe: if the
// core cannot be loaded the plugin disables itself instead of crashing.
async function loadCore() {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const candidates = []
  if (process.env.VIBEWEAVER_AUDIT_CORE) candidates.push(process.env.VIBEWEAVER_AUDIT_CORE)
  candidates.push(path.join(here, "..", "skills", "vibeweaver", "scripts", "vibeweaver-audit-core.js"))
  candidates.push(path.join(here, "scripts", "vibeweaver-audit-core.js"))
  for (const c of candidates) {
    if (!existsSync(c)) continue
    try {
      return await import(pathToFileURL(c).href)
    } catch (err) {
      // fall through to next candidate
    }
  }
  return null
}

// Host logging: v1 offers client.app.log({ body }); v2's ctx.app is
// {name, version, channel} (no log API) — fall back to stderr. Never
// throws: logging must never crash the auditor.
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

// ---------- loop-guard: degenerate-generation detection ----------
// Three degeneration shapes, detected incrementally from the assistant text
// stream (same channel the audit already observes — no model cooperation):
//   (a) identical line-group repeated at the tail — period derived from the
//       data, any block period up to LOOP_MAX_LINE_PERIOD lines (bounded by
//       the LOOP_TAIL_SCAN window);
//   (b) a trailing run of >= LOOP_SEQ_MIN bare tokens stepping +1 —
//       integers (1,2,…,179) or bijective base-26 letters (a,b,…,kf);
//   (c) line-sparse (no-newline) tails — a char-level suffix period: the
//       same >=32-char string (with a letter/digit) repeated >=4x.
// On trigger the host adapter interrupts the session and posts a corrective
// prompt (budgeted per session; exhausted = log-only, never thrash).
// Disable: VIBEWEAVER_LOOPGUARD=off. Budget override: audit.json
// loopGuardMaxInterventions (config stays outside the agent's write scope).
const LOOP_SEQ_MIN = 12
const LOOP_TAIL_SCAN = 98304
const LOOP_MAX_INTERVENTIONS_DEFAULT = 2
const LOOP_CHAR_SEED = 32
const LOOP_CHAR_MIN_PERIOD = 32
const LOOP_CHAR_MAX_CANDIDATES = 16
const LOOP_CHAR_GATE_LINE = 256
const LOOP_MAX_LINE_PERIOD = 640
const LOOP_SHAPE_MIN = 16
// W10: 64KB counted hidden reasoning too and killed long legitimate turns.
// The ceiling is now visible-text-only, 256KB, and configurable upward.
const LOOP_TURN_CEILING = 262144
const LOOP_TURN_CEILING_MIN = 65536
// Reasoning is excluded from the visible-output ceiling (long chains of
// thought are legitimate), but it still needs a high absolute backstop for
// non-periodic runaway reasoning. 1MB is ~4x the visible ceiling.
const LOOP_REASONING_CEILING = 1048576
const LOOP_REASONING_CEILING_MIN = 262144
const LOOP_PUNCT_WALL_MIN = 2048

function lettersToIndex(s) {
  let n = 0
  for (const ch of s) n = n * 26 + (ch.charCodeAt(0) - 96)
  return n
}

// Char-level suffix period for line-sparse tails (generation WITHOUT
// newlines — the line-aligned scan has no structure to key on). Candidate
// periods come from re-occurrences of the last 32 chars (native lastIndexOf,
// ≤16 candidates); a seed that is itself short-periodic ("very very…")
// probes its ≥32-char super-period multiples instead of walking off empty.
// Tail-noise tolerance: streams and part joins leave trailing whitespace
// ("\n" message ender, double space) that makes the end-anchored seed its
// own only occurrence — the reported "Stop it." wall ended exactly so and
// was invisible. Normalize trailing whitespace before seed discovery AND
// the 4-copy verification (same normalized tail), so a runaway ending in
// noise is judged on its periodic ground.
// Same bar as the line path: a single repeated unit needs ≥4 copies and
// real letter/digit content — repeated JSX/HTML elements ×3 are legitimate
// codegen and stay clean.
function charPeriodRepeat(tailIn) {
  // Tail-noise tolerance AND phase alignment are BOTH needed: rstrip-ing the
  // tail recovers the periodic ground under stream noise (the "Stop it."-
  // wall case), but when the repeated unit itself ENDS in whitespace
  // ("…running. " ×N) that same rstrip shifts every END-ANCHORED verification
  // window off the true period phase — the 4-copy bar then compares windows
  // of unequal length and can never be met (W18 G9: x4 of a 63-char sentence
  // MISSED while x3 correctly stayed clean). So probe the normalized tail
  // first (existing behavior, bit-for-bit unchanged) and then the RAW tail
  // (exact end-aligned periods). Union semantics: the raw probe can only turn
  // a MISS into a FIRE on an exact >=4-copy suffix period of a >=32-char
  // letter/digit unit — the documented bar, unchanged.
  const norm = tailIn.replace(/[\s\u200B-\u200D]+$/, "")
  return charPeriodProbe(norm) || (norm.length === tailIn.length ? null : charPeriodProbe(tailIn))
}

function charPeriodProbe(tail) {
  const minP = LOOP_CHAR_MIN_PERIOD
  if (tail.length < minP * 4) return null
  const seed = tail.slice(-LOOP_CHAR_SEED)
  // Punctuation-only walls ("!"×4000, "!!! "×800) are real degeneration
  // (claude-code char-spam class) but the letter/digit bar exists to spare
  // separators and ASCII art — length-weighted exemption keyed on the WALL's
  // own trailing punct run (not the tail window: a big report ending in a
  // short rule/banner must stay clean — review I4).
  const punctWall = ((tail.match(/[^\p{L}\p{N}]+$/u) || [""])[0].length || 0) >= LOOP_PUNCT_WALL_MIN
  if (!/[\p{L}\p{N}]/u.test(seed) && !punctWall) return null
  const maxP = Math.min(1024, Math.floor(tail.length / 4))
  let idx = tail.length - LOOP_CHAR_SEED
  for (let n = 0; n < LOOP_CHAR_MAX_CANDIDATES; n++) {
    const j = tail.lastIndexOf(seed, idx - 1)
    if (j < 0) return null
    const base = idx - j
    idx = j
    const starts = []
    if (base >= minP) starts.push(base)
    else for (let m = Math.ceil(minP / base); m * base <= maxP && starts.length < 4; m++) starts.push(m * base)
    for (const p of starts) {
      if (p > maxP) continue
      const last = tail.slice(-p)
      if (tail.slice(-2 * p, -p) !== last || tail.slice(-3 * p, -2 * p) !== last || tail.slice(-4 * p, -3 * p) !== last) continue
      const flat = last.trim()
      if (flat.length < 16) continue
      if (!/[\p{L}\p{N}]/u.test(flat) && !punctWall) continue
      return { kind: "repeat", pattern: flat.replace(/\s+/g, " ").slice(0, 80) }
    }
  }
  return null
}

// Pure detector (also unit-tested directly). Returns { kind, pattern } | null.
// Runs on every text observation: the scan is bounded to the tail, so
// per-delta cost stays flat — an echo is caught the moment its 12th token /
// 3rd copy lands.
function loopFinding(text) {
  if (!text || text.length < 48) return null
  // Line path runs on RAW lines (exact match, trailing spaces included —
  // uniform per-line whitespace is structure and must stay aligned across
  // copies). A whole-tail rtrim is deliberately NOT applied here: it strips
  // only the FINAL copy's trailing whitespace and breaks line-group
  // alignment for hard-break/padded walls and blank-terminated blocks
  // (review N1 — `"Note: …  \n"×60` regressed from FIRE to MISS). Tail
  // noise is normalized INSIDE charPeriodRepeat for the char path; the
  // gate below reads the last CONTENT line so trailing blank/whitespace
  // lines cannot mask an inline runaway (review C1).
  const tail = text.slice(-LOOP_TAIL_SCAN)
  const lines = tail.split("\n")
  // a trailing newline yields a spurious empty final element that would
  // break line-group alignment — strip at most that one artifact
  if (lines.length && lines[lines.length - 1] === "") lines.pop()
  // A) suffix-period repeat: the last 3p lines are ONE line-group repeated
  // ×3 — period p derived from the data (any block period ≤640 lines, as
  // bounded by the tail window), not from a fixed size list. The last line
  // must re-occur at −p and −2p for a period-p repeat, so nearly every
  // candidate early-exits on one compare.
  if (lines.length >= 3) {
    const last = lines[lines.length - 1]
    const pMax = Math.min(LOOP_MAX_LINE_PERIOD, Math.floor(lines.length / 3))
    for (let p = 1; p <= pMax; p++) {
      if (lines[lines.length - 1 - p] !== last || lines[lines.length - 1 - 2 * p] !== last) continue
      let ok = true
      for (let i = lines.length - p; i < lines.length; i++) {
        if (lines[i] !== lines[i - p] || lines[i] !== lines[i - 2 * p]) {
          ok = false
          break
        }
      }
      if (!ok) continue
      const group = lines.slice(-p)
      const flat = group.join("\n").trim()
      if (flat.length < 16) continue
      if (p === 1) {
        // single-line echo: bar raised — require a 4th copy AND real content
        // (identical separator/log lines ×3 are legitimate codegen).
        if (!/[\p{L}\p{N}]/u.test(last)) continue
        if (lines.length < 4 || lines[lines.length - 4] !== last) continue
      }
      return { kind: "repeat", pattern: flat.replace(/\s+/g, " ").slice(0, 80) }
    }
  }
  // line-sparse tail (generation without newlines): char-level suffix
  // period. Gated on the RECENT window so newline-rich history further back
  // cannot mask a no-newline runaway happening right now; a last line at
  // the context gate (≥256 chars) enters the scan even under newline-rich
  // context. The gate trades inline-runaway latency below 256 chars for
  // table-row FP safety: numeric/minified rows of 128..256 chars with an
  // exact period are legitimate output (review I3 — the ×4-of-32-char BAR
  // itself is unchanged).
  const recent = tail.slice(-2048)
  let lastContentLen = 0
  for (let i = lines.length - 1; i >= 0; i--) {
    if (/\S/.test(lines[i])) {
      lastContentLen = lines[i].length
      break
    }
  }
  if ((recent.match(/\n/g) || []).length < 4 || lastContentLen >= LOOP_CHAR_GATE_LINE) {
    const hit = charPeriodRepeat(tail)
    if (hit) return hit
  }
  const tokens = lines.map((l) => l.trim()).filter((l) => l.length > 0)
  if (tokens.length >= LOOP_SEQ_MIN) {
    const run = tokens.slice(-LOOP_SEQ_MIN)
    if (run.every((l) => /^-?\d{1,10}$/.test(l))) {
      const nums = run.map((l) => parseInt(l, 10))
      let ok = true
      for (let i = 1; i < nums.length; i++)
        if (nums[i] - nums[i - 1] !== 1) {
          ok = false
          break
        }
      if (ok) return { kind: "sequence", pattern: `${nums[0]}…${nums[nums.length - 1]}` }
    } else if (run.every((l) => /^[a-z]{1,3}$/.test(l))) {
      const nums = run.map(lettersToIndex)
      let ok = true
      for (let i = 1; i < nums.length; i++)
        if (nums[i] - nums[i - 1] !== 1) {
          ok = false
          break
        }
      if (ok) return { kind: "sequence", pattern: `${run[0]}…${run[run.length - 1]}` }
    }
  }
  // counter-bearing line runs (unit+counter walls — "The backlog item {i} is
  // pending review." ×200): exact-period detectors answer "not yet" forever
  // because every line differs (SpecRA: incremental-variation structural
  // repetition = 46% of real degenerate samples). Bar: ≥LOOP_SHAPE_MIN
  // consecutive tail lines with IDENTICAL non-digit shape whose EVERY digit
  // run steps strictly +1. Strict +1 on every run excludes timestamp logs
  // (only the last field ticks) and "page N of M" (M constant) — the FP
  // class that kills naive digit-normalization (hermes #127234); short
  // same-shape lists (<16) and exact repeats (line path's business) stay
  // clean.
  if (tokens.length >= LOOP_SHAPE_MIN) {
    const shape = (l) => l.replace(/\d+/g, "#")
    // anchor scan over the last 3 lines: a wall followed by one status line
    // ("…×200\nDone.") is still a wall (review I1 — the char path got
    // tail-noise tolerance, this path needs the same).
    for (let a = tokens.length - 1; a >= Math.max(0, tokens.length - 3); a--) {
      const sLast = shape(tokens[a])
      if (sLast === tokens[a]) continue
      let n = 0
      let prev = null
      for (let i = a; i >= 0; i--) {
        const t = tokens[i]
        if (shape(t) !== sLast) break
        const r = (t.match(/\d+/g) || []).map(Number)
        if (prev) {
          if (r.length !== prev.length) break
          let ok = true
          for (let k = 0; k < r.length; k++)
            if (prev[k] - r[k] !== 1) {
              ok = false
              break
            }
          if (!ok) break
        }
        prev = r
        n++
      }
      if (n >= LOOP_SHAPE_MIN) return { kind: "repeat", pattern: sLast.slice(0, 80) + ` ×${n} (counter run)` }
    }
  }
  return null
}

function loopRecoveryText(finding) {
  if (finding && finding.kind === "noop-bash") {
    return `[loop-guard] Your last tool calls degenerated into no-op echo/printf narration (${finding.pattern}) — echoing intent is NOT a tool call. STOP the echo loop. Do exactly ONE of: (1) emit the REAL tool call you kept announcing (e.g. Read/Edit — whatever your narration named) as an actual tool invocation — no echo markers, no narration; or (2) only if every acceptance criterion is verified passing, emit the skill's final completion output (gate line + completion table). BEFORE any completion output, append \`- stall: noop-bash echo narration — <what you were trying to do>\` to tests/verification_log.md and count it in your [Convergence] stalls (TESTING_PROTOCOLS §A4.10 — this interrupt IS the stall declaration; do not resume by echoing again).`
  }
  if (finding && finding.kind === "identical-tool-run") {
    return `[loop-guard] Your last tool calls degenerated into an identical-call loop (${finding.pattern}) — re-issuing the SAME tool call with the SAME arguments is not progress. STOP the repeats. Do exactly ONE of: (1) inspect the last result and re-issue the call with CHANGED arguments or a different tool, carrying a one-line diagnosis of why the previous attempt did not advance the task; or (2) if the repetition is legitimate polling, vary the polling arguments (cursor/timeout) if the tool takes any, or interleave a real action instead of re-issuing an identical call; or (3) proceed to the next real step of the task; or (4) only if every acceptance criterion is verified passing, emit the skill's final completion output (gate line + completion table). BEFORE any completion output, append \`- stall: identical-tool-run — <what you were trying to do>\` to tests/verification_log.md and count it in your [Convergence] stalls (TESTING_PROTOCOLS §A4.10 — this interrupt IS the stall declaration; do not resume by repeating the same call).`
  }
  if (finding && finding.kind === "tool-frequency") {
    return `[loop-guard] Your last tool calls degenerated into a single-tool storm (${finding.pattern}) — hammering ONE tool is not progress by itself. STOP the streak. Do exactly ONE of: (1) consolidate: work with the results you ALREADY have, or replace many narrow queries with one broader/batched call; or (2) switch tools or approach, carrying a one-line diagnosis of what the streak was trying to establish; or (3) proceed to the next real step of the task; or (4) only if every acceptance criterion is verified passing, emit the skill's final completion output (gate line + completion table). Evidence honesty: BEFORE any completion output, IF the streak was a genuine stall, append \`- stall: tool-frequency — <what you were trying to do>\` to tests/verification_log.md and count it in your [Convergence] stalls (TESTING_PROTOCOLS §A4.10); IF the streak was legitimate bulk work, write ONE line saying that instead — never record a stall that did not happen. Do not resume by hammering the same tool.`
  }
  if (finding && finding.kind === "runaway") {
    return `[loop-guard] OUTPUT CEILING: ${finding.pattern} (visible text only; hidden reasoning has its own higher backstop; a host without turn ids resets this at the observed user boundary). This is a budget backstop, not a repetition verdict. Do exactly ONE of: (1) if the task is complete, emit the final completion output now — gate line + completion table, no re-narration; or (2) if work remains, emit ONE short checkpoint (what is done + the single next concrete step) and continue in the next turn with bounded output. Do not repeat or re-narrate the same content.`
  }
  return `[loop-guard] Your output degenerated into meaningless repetition (${finding.kind}: ${finding.pattern}). STOP repeating. Reply with (1) the task you are solving in ONE line, (2) the single next concrete step, then continue normally — no sequences, no filler. If the task is actually complete, emit the final completion output instead.`
}

// ---------- detection/completion corpus gate (D1/D2, 2026-10-15) ----------
// The session buffer mixes user speech, plugin-injected corrective prompts
// and assistant output. Only ASSISTANT output is legitimate evidence of the
// model's own behavior:
//  - completion analysis must never see user-fed or plugin-injected marker
//    text (self-prompt-injection / self-lock — review D2);
//  - loop detection must never see user quotes or code-fence contents
//    (legitimate repetition — review D1's false-positive class).
// Plugin-injected messages are identified by their first-line tag
// ([loop-guard] / [stop-guard]) — same strip the stop-guard whitelist uses.
const PLUGIN_PROMPT_RE = /^\[(?:stop-guard|loop-guard)\]/
// W10: path-shape test usable without a project root (observation hot path).
// Protocol/report paths are evidence, not "the model stopped mid-code".
const EVIDENCE_PATH_RE = /(^|\/)(tests|docs|memory|\.vibeweaver)\//i
const EVIDENCE_FILE_RE = /(^|\/)(acceptance\.md|verification_log\.md|working_note\.md|gate_audit\.md|paused_state\.md|decisions\.md)$/i
// W11: prose/asset writes are legitimate under a Class DOC claim; anything
// else (code/config/binary data) is cross-checked as a code write.
const PROSE_WRITE_RE = /(?:\.(md|txt|rst|log|png|webm|wav|mp4|mp3|docx|doc|xlsx|xls|pptx|ppt|pdf|odt|ods|odp|rtf|odg|epub|mht|docm|xlsm|pptm|html|htm)|(^|\/)(LICENSE|NOTICE|COPYING|README|CHANGELOG|AUTHORS))$/i
// W11 re-review: code-write detection is extension/path based, NOT "not
// prose" — a read-only audit writing findings.csv/report.json is not code.
const CODE_WRITE_RE = /\.(py|js|mjs|ts|tsx|jsx|go|rs|java|c|cc|cpp|h|hpp|rb|php|cs|kt|swift|m|scala|pl|sh|bash|css|scss|sass|less|vue|svelte|astro|sql|json|jsonc|yaml|yml|toml|xml|ini|cfg|conf|properties|gradle|lock|mk|env|proto|graphql)$/i
const REPORT_PATH_RE = /(^|\/)(reports?|output|outputs|artifacts?|findings?|results?|summaries|summary)\//i
const REPORT_NAME_RE = /(^|\/)(report|reports|finding|findings|result|results|summary|analysis|appendix|coverage|notes)[^/]*\.(html?|json|ya?ml|xml|csv|tsv|txt|md)$/i
const DATA_REPORT_NAME_RE = /(^|\/)(data|metrics|audit|stats|coverage|table|tables|numbers|appendix)[^/]*\.(json|ya?ml|csv|tsv|txt)$/i
const CONFIG_NAME_RE = /(^|\/)(config|schema|package|settings|manifest|tsconfig|webpack|vite|rollup|babel|requirements|pnpm-lock|package-lock|yarn\.lock|Cargo\.lock|poetry\.lock|composer\.lock|appsettings|application|angular|docker-compose|compose)[^/]*\.(json|jsonc|ya?ml|toml|xml|ini|cfg|conf|js|ts|txt|lock)$|(^|\/)app\.(json|ya?ml|toml|ini|cfg|conf)$|(^|\/)(chart|values|helm)\.ya?ml$|(^|\/)helmfile[^/]*\.ya?ml$/i
const REPORT_INDEX_RE = /(^|\/)(reports?|outputs|coverage|artifacts?|findings?|results?|summaries|summary)\/index\.html?$/i
const EXTENSIONLESS_CODE_RE = /(^|\/)(Makefile|Dockerfile|Containerfile|go\.mod|go\.sum|Gemfile|Gemfile\.lock|Procfile|CMakeLists\.txt|Rakefile|Justfile|Brewfile)$/i
const inCodeDir = (fp) => /(^|\/)(src|lib|app|apps|packages?|server|internal|core|services?|backend|frontend|cmd|pkg|modules?|daemon|scripts|config|deploy|infra|k8s|helm|charts)\//i.test(fp)
const isCodeWritePath = (fp) => {
  if (typeof fp !== "string" || !fp) return false
  fp = fp.replace(/\\/g, "/")
  if (EXTENSIONLESS_CODE_RE.test(fp)) return true
  if (/(^|\/)README\.html?$/i.test(fp)) return false
  if (/\.(html?|htm)$/i.test(fp)) {
    if (/(^|\/)(docs|tests|memory)\//i.test(fp)) return false
    // Only a report-NAMED html outside a code dir is exempt; a UI app under
    // output/ or src/report.html is code. Generated report sites index.html
    // under a report dir are reports.
    if ((REPORT_NAME_RE.test(fp) || REPORT_INDEX_RE.test(fp)) && !inCodeDir(fp)) return false
    return true
  }
  if (CODE_WRITE_RE.test(fp)) {
    // Report/data artifacts are not code — but ONLY report-shaped extensions,
    // never a code/config file that happens to live under output/reports/.
    if (/(^|\/)(reports?|output|outputs|artifacts?|findings?|results?|summaries|summary)\//i.test(fp)
      && /\.(json|jsonc|ya?ml|xml|csv|tsv|txt|md|html?)$/i.test(fp)
      && !CONFIG_NAME_RE.test(fp)
      && !inCodeDir(fp)
      && (/\.json$/i.test(fp) || REPORT_NAME_RE.test(fp) || DATA_REPORT_NAME_RE.test(fp))) return false
    if (REPORT_NAME_RE.test(fp) && !inCodeDir(fp)) return false
    if (DATA_REPORT_NAME_RE.test(fp) && !inCodeDir(fp)) return false
    return true
  }
  return false
}
function looksEvidencePath(filePath) {
  if (typeof filePath !== "string" || !filePath) return true
  const p = filePath.split(path.sep).join("/")
  return EVIDENCE_PATH_RE.test(p) || EVIDENCE_FILE_RE.test(p)
}

function isPluginInjected(text) {
  return typeof text === "string" && PLUGIN_PROMPT_RE.test(text)
}

const hashText = (s) => createHash("sha1").update(typeof s === "string" ? s : "").digest("hex")

// Assistant-only corpus: text parts whose message is NOT user-role and which
// are not plugin-injected prompts. Parts with no role attribution (v2 deltas,
// early v1 parts) count as assistant — they are the model's own output.
function assistantCorpus(sess) {
  const out = []
  const parts = (sess && sess.textParts) || {}
  const injected = (sess && sess.injectedPrompts) || []
  for (const pid of Object.keys(parts)) {
    const txt = parts[pid]
    if (typeof txt !== "string" || !txt) continue
    const mid = sess.partMsg ? sess.partMsg[pid] : null
    const role = mid && sess.roles ? sess.roles[mid] : null
    if (role === "user") continue
    if (isPluginInjected(txt)) continue
    // identity exclusion (review B5/A3): a part that CARRIES a prompt this
    // plugin sent (exact head match) is our own injection echoed back — the
    // prefix strip only covers the first line, this covers the body.
    if (injected.some((p) => p && txt.includes(p.slice(0, 200)))) continue
    out.push(txt)
  }
  // head+tail bound (2026-10-17 effectiveness fix): the audit's sessionText
  // is capped like the scan corpus — keep the session-head anchors and the
  // completion tail, middle-truncate with a visible marker (codex-rs
  // middle-truncation / "truncate the middle, not the edges").
  const joined = out.join("\n")
  return joined.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL
    ? joined.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + joined.slice(-TEXT_CAP_TAIL)
    : joined
}

// Code fences are legitimate repetition (codegen); an UNCLOSED trailing
// fence (streaming) is treated as code too — false positives cost more than
// missed fence-internal degeneration (the turn ceiling still bounds it).
function stripCodeFences(text) {
  if (typeof text !== "string" || !text) return ""
  return text.replace(/```[\s\S]*?(?:```|$)/g, "\n")
}

function loopCorpus(sess) {
  return stripCodeFences(assistantCorpus(sess))
}

// Genuine user input (a human/user-role text part that is not a plugin
// corrective prompt) re-arms the episode latches and DECAYS the per-channel
// intervention counters by one (floor 0): a human interjection is a natural
// break in whatever the model was repeating, and budget must not starve a
// long interactive session (PLAN §2 D1-④ "用户输入自然衰减计数").
function decayLoopBudget(sess) {
  const lg = sess && sess.loopGuard
  if (!lg || typeof lg !== "object") return
  for (const k of ["armed", "armedNoop", "armedReasoning"]) if (typeof lg[k] === "boolean") lg[k] = true
  for (const k of ["interventions", "interventionsNoop", "interventionsReasoning"]) {
    if (Number.isFinite(lg[k]) && lg[k] > 0) lg[k] = lg[k] - 1
  }
}

// ---------- audit machine (shared by the v1 + v2 adapters) ----------

function createAuditMachine({ directory, core, log, onDegenerate, onStopPrompt, capabilities }) {
  const { auditProject, buildReport, mergeReleaseLines } = core
  const caps = capabilities && typeof capabilities === "object" ? capabilities : {}
  const hasTelemetry = caps.telemetry === true
  const promptable = caps.promptable === true

  let state = { sessions: {}, roots: {} }
  const statePath = path.join(directory, STATE_DIR, STATE_FILE)
  try {
    const raw = safeRead(statePath)
    if (raw) state = JSON.parse(raw)
    if (!state || typeof state.sessions !== "object") state = { sessions: {}, roots: {} }
  } catch {
    state = { sessions: {}, roots: {} }
  }

  // D1 (2026-10-15): state persistence is scoped to vibeweaver work — a
  // project with no tests/verification_log.md AND no skill-activated session
  // must see ZERO filesystem writes (no .vibeweaver/, no session transcript
  // on disk). In-memory observation still runs; nothing is persisted.
  const persistable = () => {
    if (findProjectRoot([directory])) return true
    return Object.values(state.sessions).some((s) => s && s.skillLoaded)
  }
  const flush = () => {
    try {
      if (!persistable()) return
      // prune: keep only the most recent sessions so the state file stays bounded
      const ids = Object.keys(state.sessions)
      if (ids.length > 20) {
        const keep = new Set(ids.slice(-20))
        for (const id of ids) if (!keep.has(id)) delete state.sessions[id]
      }
      if (!existsSync(path.join(directory, STATE_DIR))) mkdirSync(path.join(directory, STATE_DIR), { recursive: true })
      const tmp = statePath + ".tmp"
      writeFileSync(tmp, JSON.stringify(state))
      renameSync(tmp, statePath)
    } catch {
      /* never crash on persistence */
    }
  }

  const touchSession = (sessionID) => {
    if (!state.sessions[sessionID]) state.sessions[sessionID] = { text: "", textParts: {}, tools: [], skillLoaded: false }
    const s = state.sessions[sessionID]
    if (!s.roles) s.roles = {} // messageID → role (stop-guard, bounded)
    if (!s.partMsg) s.partMsg = {} // text-partID → messageID (stop-guard, bounded)
    if (!s.msgAt) s.msgAt = {} // messageID → first observation time (W10 turn scope, bounded)
    if (!s.msgSeqAt) s.msgSeqAt = {} // messageID → monotonic observation order (same-ms safe)
    if (!Number.isFinite(s.msgSeq)) s.msgSeq = 0
    if (!s.partSeqAt) s.partSeqAt = {} // text-partID → monotonic observation order (W11 gate ordering)
    if (!s.gateSeqAt) s.gateSeqAt = {} // text-partID → seq when the gate marker FIRST appeared
    if (!s.gateCountAt) s.gateCountAt = {} // text-partID → gate marker count (id-less part detection)
    if (!Number.isFinite(s.partSeq)) s.partSeq = 0
    if (!Number.isFinite(s.partSeqPruneAt)) s.partSeqPruneAt = 0
    if (!s.msgChurnAt) s.msgChurnAt = [] // messageID change times (W11 churn guard)
    if (!Number.isFinite(s.userLogLen)) s.userLogLen = null // verification_log length at the user turn
    if (typeof s.userLogHash !== "string") s.userLogHash = "" // sha1 of that prefix (rewrite detection)
    if (!Number.isFinite(s.userDecisionsLen)) s.userDecisionsLen = 0 // decisions.md length at the user turn
    if (!Array.isArray(s.turnWritePaths)) s.turnWritePaths = [] // current-turn writes (bounded, audit aid)
    if (!Array.isArray(s.turnMsgIDs)) s.turnMsgIDs = [] // role-less turn text messageIDs (v2 gate scope)
    if (s.turnCodeWrite === undefined) s.turnCodeWrite = false // sticky: a known code write this turn
    if (!Number.isFinite(s.lastTaskWritePartSeq)) s.lastTaskWritePartSeq = NaN
    if (s.lastTaskWriteUnknown === undefined) s.lastTaskWriteUnknown = false
    if (s.toolFreqWarned === undefined) s.toolFreqWarned = false // W12 warn-only layer (once/session)
    if (s.lastUserMid === undefined) s.lastUserMid = null
    if (s.usage === undefined) s.usage = null // last assistant message telemetry
    if (!Number.isFinite(s.createdTs)) s.createdTs = Date.now() // session-scope anchor for stop-guard whitelists (F5)
    // W11 re-review: v2/no-user-event hosts need a session-start log boundary
    // too; otherwise an old completed block satisfies waveComplete for a new
    // task. A v1 user turn overwrites this snapshot.
    if (s.userLogLen === null) {
      try {
        const r = findProjectRoot([directory])
        const txt = r ? safeRead(path.join(r, "tests", "verification_log.md")) : ""
        s.userLogLen = txt.length
        s.userLogHash = hashText(txt)
      } catch {
        s.userLogLen = 0
        s.userLogHash = hashText("")
      }
    }
    return s
  }

  const capText = (s) =>
    s.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL ? s.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + s.slice(-TEXT_CAP_TAIL) : s

  const skillLoaded = (sess) => sess.skillLoaded || sess.tools.some((t) => t.tool === "skill" && typeof t.name === "string" && t.name.startsWith("vibeweaver"))

  // Config lives OUTSIDE the agent's write scope — the agent could otherwise
  // weaken its own auditor (optimizer must never own its objective function).
  // Short TTL cache: the guard reads this on hot paths (tool events, long
  // deltas). Keyed by path so tests/config switches never reuse stale bytes;
  // the config lives outside the agent's write scope, so 1s is safe.
  let cfgCache = { key: "", at: 0, val: null }
  const readConfig = () => {
    try {
      const p = process.env.VIBEWEAVER_AUDIT_CONFIG || path.join(os.homedir(), ".config", "opencode", "vibeweaver", "audit.json")
      const now = Date.now()
      if (cfgCache.key === p && now - cfgCache.at < 1000) return cfgCache.val || {}
      let val = {}
      if (existsSync(p)) val = JSON.parse(safeRead(p) || "null") || {}
      cfgCache = { key: p, at: now, val }
      return val
    } catch {
      /* defaults */
    }
    return {}
  }

  // Release a stale RED latch. Rules (latch = { sessionID, ts, bad }),
  // evaluated in this order:
  //   1. legacy boolean state (ts===0, never session-scoped at birth) →
  //      legacy-state release on first contact, labeled for its true origin
  //      (also reachable for object latches that lost their ts);
  //   2. TTL expiry (redTtlHours, default 24; audit.json);
  //   3. NEW TASK by the latching session itself (2026-10-02, multi-wave
  //      DOC→CODE deadlock): tests/acceptance.md rewritten AFTER the latch
  //      is the protocol's own first action of a new task — and tests/ is
  //      writable under the latch, so the key is always reachable without
  //      another session, a TTL wait, or VIBEWEAVER_AUDIT=off. Journaled
  //      as "new-task"; the old wave's debt stays in tests/gate_audit.md
  //      and the new wave's own completion claim re-checks everything
  //      (marker-count re-arm leg, runAudit final branch).
  // D3 (2026-10-15, PLAN §2): the "stale-session" release is REMOVED — a
  // foreign session's write used to clear the latch, so one subagent write
  // bypassed the whole gate (review PoC). A foreign write now changes
  // nothing; subagent/task-tool writes are foreign writes by definition.
  // Never releases a fresh latch of the CURRENT session without the
  // new-task key (in-session teeth mid-wave).
  // Returns the release record or null. Never throws.
  const acceptanceMtime = (root) => {
    try {
      // Floor to whole ms: mtimeMs carries sub-ms precision while latch.ts
      // is a truncated Date.now() integer — an acceptance.md written in the
      // SAME millisecond as the latch (1000.5 > 1000) must NOT count as
      // post-latch. Same-ms ambiguity resolves to "no release" (teeth).
      return Math.floor(statSync(path.join(root, "tests", "acceptance.md"), { throwIfNoEntry: false })?.mtimeMs ?? 0)
    } catch {
      return 0
    }
  }
  const releaseStale = (root, currentSessionID, via) => {
    try {
      const entry = state.roots[root]
      const latch = readLatch(entry)
      if (!entry || !latch) return null
      const cfg = readConfig()
      const ttlHours = Number.isFinite(cfg.redTtlHours) ? cfg.redTtlHours : RED_TTL_HOURS_DEFAULT
      const age = Date.now() - latch.ts
      const cur = typeof currentSessionID === "string" && currentSessionID ? currentSessionID : null
      // ts===0 identifies a latch that was never session-scoped at birth
      // (legacy boolean form) — label it as such, not as a fleet of unknowns.
      const reason = latch.ts === 0
        ? "legacy-state"
        : age > ttlHours * 3_600_000
          ? "ttl-expiry"
          : cur && latch.sessionID === cur && acceptanceMtime(root) > latch.ts
            ? "new-task"
            : null
      if (!reason) return null
      const rec = { ts: Date.now(), from: latch.sessionID || "unknown", bad: latch.bad, reason, via, by: cur || via }
      entry.red = null
      if (!Array.isArray(entry.redReleases)) entry.redReleases = []
      entry.redReleases.push(rec)
      if (entry.redReleases.length > RELEASES_CAP) entry.redReleases = entry.redReleases.slice(-RELEASES_CAP)
      flush()
      void log({
        service: "vibeweaver-audit",
        level: "info",
        message: `Stale RED latch released (${reason}) — latched by ${rec.from} (BAD=${rec.bad == null ? "?" : rec.bad}), via ${via}`,
        extra: { root, release: rec },
      })
      return rec
    } catch {
      return null
    }
  }

  const makePackets = (audit, sess) => {
    const packets = []
    for (const c of audit.checks) {
      if (c.verdict !== "UNCERTAIN") continue
      let body = c.evidence
      if (/^(C9|C10|C11)/.test(c.id)) {
        const reads = sess.tools.filter((t) => t.tool === "read").map((t) => t.filePath).slice(-5)
        body += "\nrecent reads: " + (reads.join(" | ") || "(none)")
      } else {
        body += "\ntail of session text: " + sess.text.slice(-400)
      }
      packets.push({ id: c.id, body: body.slice(0, 1600) })
    }
    return packets
  }

  // "final" phase only when the session actually completed a task; session.idle
  // fires after EVERY turn — final checks mid-task would deadlock the loop.
  // D2 (2026-10-15): the marker is read from the ASSISTANT corpus only — a
  // user-fed or plugin-injected gate line must never open the completion
  // audit (self-lock / fake-completion), while the assistant's own final
  // answer still does.
  const completionHeuristic = (sess) => {
    const corpus = assistantCorpus(sess)
    return /\[Verification Gate\]/.test(corpus) || /^\s*\| # \| Problem \| Research Sources/m.test(corpus)
  }

  const runAudit = async (sessionID, phase) => {
    const sess = state.sessions[sessionID]
    if (!sess) return null
    const root = findProjectRoot([directory])
    if (!root) return null
    if (process.env.VIBEWEAVER_AUDIT === "off") return null
    const loaded = skillLoaded(sess)
    const priorFlagged = state.roots[root] && Array.isArray(state.roots[root].c8Flagged) ? state.roots[root].c8Flagged : []
    const audit = auditProject({
      root,
      sessionID,
      sessionText: assistantCorpus(sess),
      tools: sess.tools,
      skillLoaded: loaded,
      phase,
      config: readConfig(),
      priorFlagged,
    })
    if (audit.skipped) return null
    if (!state.roots[root]) state.roots[root] = {}
    if (phase === "final" && Array.isArray(audit.newlyFlagged) && audit.newlyFlagged.length) {
      // C8 dedup persistence — the same forbidden command never flags twice
      // for this root, so a latch stays self-clearable on later GREEN audits.
      // FINAL phase only: a mid-phase warn must NOT consume the one-shot —
      // otherwise a forbidden command run mid-task would be persisted before
      // the latching final audit ever sees it, and the latch never engages.
      state.roots[root].c8Flagged = [...new Set([...priorFlagged, ...audit.newlyFlagged])].slice(-100)
    }
    const packets = makePackets(audit, sess)
    const releases = Array.isArray(state.roots[root].redReleases) ? state.roots[root].redReleases : []
    const stopDebts = Array.isArray(state.roots[root].stopDebt) ? state.roots[root].stopDebt : []
    // Append-only render: the state journal is bounded (RELEASES_CAP), but the
    // report's "never delete" section is an audit trail — merge the prior
    // render's release lines with the current state lines (union + dedupe).
    let priorReport = ""
    try {
      priorReport = safeRead(path.join(root, "tests", AUDIT_FILE))
    } catch {
      /* first run — no prior render */
    }
    const footer = mergeReleaseLines(
      priorReport,
      releases.map(
        (r) =>
          `- ${new Date(r.ts).toISOString()} released: latched RED (BAD=${r.bad == null ? "?" : r.bad}, session ${r.from}) → cleared via ${r.reason} (via ${r.via}, by ${r.by})`
      )
    )
    const debtFooter = stopDebts.map(
      (d) => `- ${new Date(d.ts).toISOString()} stop-debt: ${d.kind} "${d.match}" — ${d.why} (session ${d.sessionID}) — §V12 false-stop; adjudicate in Tier-2 review`
    )
    const report = buildReport(audit, sessionID, packets, footer, debtFooter)
    try {
      if (!existsSync(path.join(root, "tests"))) mkdirSync(path.join(root, "tests"), { recursive: true })
      writeFileSync(path.join(root, "tests", AUDIT_FILE), report)
    } catch {
      /* report best-effort */
    }
    if (phase === "final") {
      // BAD-signature guard (2026-10-02, multi-wave re-latch treadmill; r2
      // hardening after adversarial review). A final audit scores the WHOLE
      // session buffer, and a multi-wave buffer keeps the previous wave's
      // residue forever — so every idle re-audit of the SAME unfinished
      // claim lands RED again, re-latching with a FRESH ts (starving the
      // 24h TTL backstop) and resurrecting latches a takeover/TTL release
      // had already cleared. Two legs, and a RED final re-latches only when
      // at least one says "genuinely new failure":
      //   session signature — sorted BAD-check ids, keyed PER SESSION
      //     (root-level amnestied a DIFFERENT session's genuine fresh audit:
      //     template-driven BAD sets are identical across sessions, so a
      //     successor's first failure must never be suppressed);
      //   completion-marker count — the number of `[Verification Gate]`
      //     occurrences in the capped buffer grows by one on every NEW
      //     completion claim (head-trimming only drops markers when >150KB
      //     of text separates two claims — a boundary, see Known gaps).
      //     Same-sig re-audits of the latched claim (mid-wave idles over a
      //     stale marker) stay suppressed; the next claim re-arms honestly.
      const badSig = audit.checks
        .filter((c) => c.verdict === "BAD")
        .map((c) => c.id)
        .sort()
        .join(",")
      const gateCount = (() => {
        const corpus = assistantCorpus(sess)
        return corpus.split(GATE_MARKER).length - 1
      })()
      if (audit.red) {
        if (!readLatch(state.roots[root])) {
          const sigs = state.roots[root].lastRedSigs || {}
          const sameClaimResidue = sigs[sessionID] === badSig && !(gateCount > (state.roots[root].lastLatchGateCount ?? 0))
          if (!sameClaimResidue) {
            state.roots[root].red = { sessionID, ts: Date.now(), bad: audit.bad }
            sigs[sessionID] = badSig
            state.roots[root].lastRedSigs = Object.fromEntries(Object.entries(sigs).slice(-20))
            state.roots[root].lastLatchGateCount = gateCount
          }
        }
        // else: a live latch is already debt-recorded — leave red and its
        // original ts untouched (never refresh; TTL backstop stays real).
      } else {
        state.roots[root].red = null
        if (state.roots[root].lastRedSigs) delete state.roots[root].lastRedSigs[sessionID]
        state.roots[root].lastLatchGateCount = 0
      }
    }
    state.roots[root].lastSession = sessionID
    flush()
    return { audit, report }
  }

  // Degenerate-generation check (loop-guard) — runs on every observation
  // once the buffer grew enough; detection is a bounded tail scan, never on
  // the whole buffer. Two channels, each with its OWN intervention budget
  // (per-channel, so one channel's episode can never starve the other's):
  //   text — periodic/sequence repetition of the assistant stream;
  //   tool — trailing no-op bash narration runs (echo/printf literal markers
  //          standing in for an announced tool call; noopBashFinding) OR a
  //          trailing run of DISTINCT identical tool calls (same tool +
  //          canonical args, MCP included; identicalToolRunFinding) OR a
  //          single-tool storm with varying args (toolFrequencyFinding).
  // Each channel has its own episode-arming flag so one channel's episode
  // never masks the other. Never throws.
  const maybeGuardCheck = (sessionID, channel) => {
    try {
      if (process.env.VIBEWEAVER_LOOPGUARD === "off") return
      if (typeof onDegenerate !== "function") return
      const sess = state.sessions[sessionID]
      if (!sess) return
      // D1 project gate (2026-10-15): the guard only runs inside an ACTIVE
      // vibeweaver task — the project has tests/acceptance.md or this
      // session activated the vibeweaver skill. Ordinary directories get
      // zero behavior (no detection, and flush() below writes nothing).
      if (!skillLoaded(sess)) {
        const gateRoot = findProjectRoot([directory])
        if (!gateRoot || !existsSync(path.join(gateRoot, "tests", "acceptance.md"))) return
      }
      if (!sess.loopGuard || typeof sess.loopGuard !== "object") sess.loopGuard = { interventions: 0, interventionsNoop: 0, armed: true, armedNoop: true }
      const lg = sess.loopGuard
      // Config is read lazily: doing a JSON parse on every streamed delta is
      // a hot-path regression. The ceiling only matters above the minimum;
      // the tool chain needs the opt-in key; budgets read it on a finding.
      let cfg = null
      const getCfg = () => cfg || (cfg = readConfig())
      const cfgCeiling = (sess.turnChars || 0) > LOOP_TURN_CEILING_MIN ? Number(getCfg().loopGuardTurnCeilingBytes) : NaN
      const turnCeiling = Number.isFinite(cfgCeiling) && cfgCeiling >= LOOP_TURN_CEILING_MIN ? cfgCeiling : LOOP_TURN_CEILING
      const cfgReasoningCeiling = channel === "reasoning" ? Number(getCfg().loopGuardReasoningCeilingBytes) : NaN
      const reasoningCeiling = Number.isFinite(cfgReasoningCeiling) && cfgReasoningCeiling >= LOOP_REASONING_CEILING_MIN ? cfgReasoningCeiling : LOOP_REASONING_CEILING
      const cfgFreqMin = channel === "tool" ? Number(getCfg().loopGuardToolFrequencyMin) : NaN
      const freqOptIn = Number.isInteger(cfgFreqMin) && cfgFreqMin >= 4
      // NaN-safe backfill (D-6): corrupt/hand-edited state lacking these
      // fields must never bypass the budget (NaN >= max is always false).
      if (!Number.isFinite(lg.interventions)) lg.interventions = 0
      if (!Number.isFinite(lg.interventionsNoop)) lg.interventionsNoop = 0
      if (!Number.isFinite(lg.interventionsReasoning)) lg.interventionsReasoning = 0
      if (typeof lg.armed !== "boolean") lg.armed = true
      if (typeof lg.armedNoop !== "boolean") lg.armedNoop = true
      if (typeof lg.armedReasoning !== "boolean") lg.armedReasoning = true
      const toolChannel = channel === "tool"
      const reasoningChannel = channel === "reasoning"
      const chanSuffix = toolChannel ? "Noop" : reasoningChannel ? "Reasoning" : ""
      const armedKey = "armed" + chanSuffix
      const usedKey = "interventions" + chanSuffix
      const fireKey = "fireMsgID" + chanSuffix
      let finding = toolChannel
        ? (typeof core.noopBashFinding === "function" ? core.noopBashFinding(sess.tools) : null) ||
          (typeof core.identicalToolRunFinding === "function"
            ? core.identicalToolRunFinding(
                sess.tools,
                (() => {
                  const n = Number(readConfig().loopGuardIdenticalRunMin)
                  return Number.isInteger(n) && n >= 2 ? n : undefined
                })()
              )
            : null) ||
          // W10: tool-name frequency is a low-specificity signal (legitimate
          // bulk work is a same-tool streak). Opt-in only: an explicit
          // integer config restores the detector; default = off.
          (freqOptIn && typeof core.toolFrequencyFinding === "function"
            ? core.toolFrequencyFinding(sess.tools, cfgFreqMin)
            : null)
        : loopFinding(reasoningChannel ? stripCodeFences(sess.reasoning) : loopCorpus(sess))
      // W12 P2-4: a high-threshold WARN-ONLY layer restores coverage for the
      // varied-args single-tool storm (40-450 calls) without aborting. It
      // journals one advisory line per session; the opt-in abort stays above.
      if (!finding && toolChannel && typeof core.toolFrequencyFinding === "function" && !sess.toolFreqWarned) {
        const warnCfg = Number(getCfg().loopGuardToolFrequencyWarnMin)
        const warnMin = Number.isInteger(warnCfg) && warnCfg >= 20 ? warnCfg : 120
        const warn = core.toolFrequencyFinding(sess.tools, warnMin)
        if (warn) {
          sess.toolFreqWarned = true
          void log({
            service: "vibeweaver-loopguard",
            level: "info",
            message: `tool-frequency warning (warn-only, no abort): ${warn.pattern} — consolidate or switch tool`,
            extra: { sessionID },
          })
          flush()
        }
      }
      // per-turn absolute ceiling (hermes #127234: periodic detectors can
      // answer "not yet" forever for shapes they cannot see — the ceiling is
      // the bound that makes runaway output finite). Synthesized once per
      // 64KB growth window (turnCeilingAt advances at synthesis, so a blocked
      // or budget-swallowed attempt does NOT burn the window — review I2;
      // and hosts without messageIDs still fire — review I3) and routed
      // through the same budget as organic findings; the shared marker keeps
      // text/reasoning from double-firing one runaway turn.
      if (
        !finding &&
        !toolChannel &&
        !reasoningChannel &&
        (sess.turnChars || 0) > turnCeiling &&
        (sess.turnChars || 0) >= (sess.turnCeilingAt || 0) + turnCeiling
      ) {
        sess.turnCeilingAt = sess.turnChars
        finding = { kind: "runaway", pattern: `turn output exceeded ${turnCeiling} bytes` }
      }
      // Reasoning has its own high absolute backstop: hidden chains of thought
      // are excluded from the visible 256KB ceiling, but a non-periodic 1MB+
      // reasoning stream must still be bounded (review I4).
      if (
        !finding &&
        reasoningChannel &&
        (sess.reasoningChars || 0) > reasoningCeiling &&
        (sess.reasoningChars || 0) >= (sess.reasoningCeilingAt || 0) + reasoningCeiling
      ) {
        sess.reasoningCeilingAt = sess.reasoningChars
        finding = { kind: "runaway", pattern: `reasoning output exceeded ${reasoningCeiling} bytes` }
      }
      // one intervention per degeneration EPISODE: after firing, stay
      // disarmed while the same pattern still sits at the tail (the
      // interrupt stops generation; the remaining history must not
      // re-trigger). Re-arm after a clean observation OR a NEW turn
      // (message boundary) — a fresh assistant message that degenerates
      // again is a new episode (the stubborn "Stop it." model kept
      // re-degenerating in new turns and the old clean-only latch went
      // silent forever). The per-channel budget still caps interventions,
      // so no-thrash holds absolutely.
      if (!finding) {
        if (!lg[armedKey]) {
          lg[armedKey] = true
          flush() // persist the re-arm (crash symmetry: the fire direction already flushes)
        }
        return
      }
      if (!lg[armedKey]) {
        // runaway is the hard bound: it bypasses the same-turn no-thrash gate
        // (a turn that already consumed its latch slot must still be cut at
        // the ceiling — review I2a); the per-channel budget still caps it.
        const newTurn = Boolean(lg[fireKey]) && Boolean(sess.lastMsgID) && sess.lastMsgID !== lg[fireKey]
        if (!newTurn && finding.kind !== "runaway") {
          // latched organic finding (the stubborn-wall case): the ceiling
          // RESCUES the turn when a growth window has been crossed — without
          // this the turn is cut at most once and then unbounded (re-review N1)
          if (!toolChannel && (sess.turnChars || 0) >= (sess.turnCeilingAt || 0) + turnCeiling) {
            sess.turnCeilingAt = sess.turnChars
            finding = { kind: "runaway", pattern: `turn output exceeded ${turnCeiling} bytes` }
          } else return
        }
      }
      lg[armedKey] = false
      lg[fireKey] = sess.lastMsgID
      const maxInterventions = Number.isFinite(getCfg().loopGuardMaxInterventions) ? getCfg().loopGuardMaxInterventions : LOOP_MAX_INTERVENTIONS_DEFAULT
      if (lg[usedKey] >= maxInterventions) {
        // budget exhausted for THIS channel: never interrupt again on it,
        // but log every NEW episode (armed semantics guarantee this is a
        // distinct episode, not the same tail re-flagged)
        flush()
        void log({
          service: "vibeweaver-loopguard",
          level: "info",
          message: `degenerate generation detected (${finding.kind}: ${finding.pattern}) — intervention budget exhausted (${maxInterventions}/session/${channel}), not interrupting`,
          extra: { sessionID, finding, channel },
        })
        return
      }
      lg[usedKey]++
      flush() // arming + budget must survive a mid-episode restart (F9)
      // record the corrective text as OUR injection (identity exclusion in
      // assistantCorpus — review A3/B5: the prefix strip covers the first
      // line, this covers a quoted/echoed body)
      const injectedText = loopRecoveryText(finding)
      if (!Array.isArray(sess.injectedPrompts)) sess.injectedPrompts = []
      sess.injectedPrompts.push(injectedText)
      if (sess.injectedPrompts.length > 5) sess.injectedPrompts = sess.injectedPrompts.slice(-5)
      void log({
        service: "vibeweaver-loopguard",
        level: "warn",
        message: `degenerate generation detected (${finding.kind}: ${finding.pattern}) — interrupting and posting a corrective prompt (${lg[usedKey]}/${maxInterventions}/${channel})`,
        extra: { sessionID, finding, channel },
      })
      void Promise.resolve(onDegenerate(sessionID, finding, lg[usedKey], maxInterventions)).catch(() => {})
    } catch {
      /* loop-guard must never break observation */
    }
  }
  const maybeLoopCheck = (sessionID) => maybeGuardCheck(sessionID, "text")
  const maybeToolLoopCheck = (sessionID) => maybeGuardCheck(sessionID, "tool")

  // ---- bounded observation buffers (SIGTRAP/OOM hardening, 2026-10-17) ----
  // The corpus rebuild (Object.values(store).join + assistantCorpus +
  // stripCodeFences) is O(corpus) work AND allocations per observation. Over
  // a long streaming turn that is quadratic in turn length — measured ~90GB
  // of allocation churn for a 30k-delta turn under bun; the crashed opencode
  // processes (2026-10-17 DiagnosticReports) died inside libpas' allocator
  // with 59.7GB of malloc virtual (allocation-failure CRASH() = SIGTRAP).
  // Three bounds fix it: (1) every part buffer is capped (same head/tail
  // budget as the corpus), (2) the part maps are pruned to PARTS_MAX, (3)
  // detector scans run on a byte cadence once a TURN is large — small
  // corpora still scan every observation (exact detection timing; the
  // selftest and short turns depend on it), and the detector's own window is
  // only the 98KB tail anyway.
  const PARTS_BUDGET = 2_000_000
  const PARTS_KEEP_NEW = 8
  const PARTS_HARD_MAX = 512
  const SCAN_STEP = 256
  const SCAN_SMALL = 32_768
  const capPart = (s) => (s.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL ? s.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + s.slice(-TEXT_CAP_TAIL) : s)
  // Middle-evicting corpus bound (industry shape: "truncate the middle, not
  // the edges" — Arize; protect_first_n/protect_last_n — Revka; codex-rs
  // middle truncation). The FIRST part is the session-head anchor (baseline
  // narration class — what a count-based 64-part cut used to drop) and the
  // NEWEST parts carry the completion output: both are high-value regions
  // ("Lost in the Middle"). Evict oldest MIDDLE parts first, under a total
  // byte budget; the head anchor and the newest PARTS_KEEP_NEW never go.
  const pruneParts = (store) => {
    const keys = Object.keys(store)
    const n = keys.length
    const evictEnd = n - Math.min(PARTS_KEEP_NEW, n)
    if (evictEnd <= 1) return
    let total = 0
    for (const k of keys) total += (store[k] || "").length
    let count = n
    for (let i = 1; i < evictEnd && (total > PARTS_BUDGET || count > PARTS_HARD_MAX); i++) {
      total -= (store[keys[i]] || "").length
      delete store[keys[i]]
      count--
    }
  }
  const maybeTextScan = (sessionID, sess, channel, added) => {
    if ((sess.turnChars || 0) > SCAN_SMALL) {
      sess.scanBytes = (sess.scanBytes || 0) + (added > 0 ? added : 0)
      if (sess.scanBytes < SCAN_STEP) return
      sess.scanBytes = 0
    }
    if (channel === "reasoning") {
      sess.reasoning = capText(Object.values(sess.reasoningParts || {}).join("\n"))
      maybeGuardCheck(sessionID, "reasoning")
    } else {
      sess.text = capText(Object.values(sess.textParts).join("\n"))
      maybeLoopCheck(sessionID)
    }
  }

  // ---- stop-guard (§V12): false-stop detection at session idle ----
  // Trigger = stop-euphemism in the LAST assistant message's text (or
  // finish:"length" truncation). Whitelist first, budget 2/session, debt
  // journaled when no corrective follows. Never throws.
  const STOP_DEBT_CAP = 5
  const STOP_GUARD_MAX_DEFAULT = 2

  const msgText = (sess, mid) => {
    if (!mid) return ""
    const parts = []
    // iterate partMsg (bounded ≤400), never the uncapped textParts (R2#10)
    for (const pid of Object.keys(sess.partMsg)) {
      if (sess.partMsg[pid] === mid && typeof sess.textParts[pid] === "string") parts.push(sess.textParts[pid])
    }
    return parts.join("\n")
  }

  // W10 helpers: turn-scoped assistant text, task-class read, and an
  // evidence-path filter so writing acceptance/log/report files cannot
  // masquerade as "the model stopped mid-code".
  const isEvidencePath = (root, filePath) => {
    if (typeof filePath !== "string" || !filePath) return true
    const rel = path.relative(root, path.resolve(root, filePath)).split(path.sep).join("/")
    if (rel.startsWith("..")) return true
    return looksEvidencePath(rel)
  }
  const gateInfoSince = (sess, sinceAt, sinceMid) => {
    let seq = 0
    let inLast = false
    if (!sess || !sess.partMsg) return { seq, inLast }
    const roles = sess.roles && Object.keys(sess.roles).length
    if (!roles) {
      // v2/role-less: scan only message ids observed in the CURRENT turn
      // (gate + a later "Done." in the same turn are both accepted); after an
      // idle the set is cleared, so an old gate cannot suppress new debt.
      const ids = Array.isArray(sess.turnMsgIDs) && sess.turnMsgIDs.length ? sess.turnMsgIDs : null
      if (ids) {
        for (const mid of ids) {
          const txt = sess.textParts && sess.textParts[mid]
          if (typeof txt !== "string" || !txt.includes(GATE_MARKER)) continue
          if (mid === sess.lastMsgID || mid === ids[ids.length - 1]) inLast = true
          const gs = sess.gateSeqAt && sess.gateSeqAt[mid]
          const ps = sess.partSeqAt && sess.partSeqAt[mid]
          const order = Number.isFinite(gs) ? gs : Number.isFinite(ps) ? ps : 0
          if (order > seq) seq = order
        }
        return { seq, inLast }
      }
      // Legacy role-less fallback: latest text part only.
      let bestPid = ""
      let bestSeq = -1
      for (const pid of Object.keys(sess.textParts || {})) {
        const ps = sess.partSeqAt && sess.partSeqAt[pid]
        const n = Number.isFinite(ps) ? ps : 0
        if (n > bestSeq) { bestSeq = n; bestPid = pid }
      }
      if (!bestPid) return { seq: 0, inLast: false }
      const txt = sess.textParts[bestPid]
      if (typeof txt !== "string" || !txt.includes(GATE_MARKER)) return { seq: 0, inLast: false }
      const gs = sess.gateSeqAt && sess.gateSeqAt[bestPid]
      return { seq: Number.isFinite(gs) ? gs : bestSeq, inLast: true }
    }
    const userSeq = sinceMid && sess.msgSeqAt ? sess.msgSeqAt[sinceMid] : NaN
    const hasUserBoundary = Number.isFinite(userSeq) || Number.isFinite(sinceAt)
    if (!hasUserBoundary) {
      // No user event: scan the current turn's assistant messages. A gate
      // after the last task write is valid even if a final "Done." follows;
      // an old gate with no write after it is only valid in the last message.
      const ids = Array.isArray(sess.turnMsgIDs) && sess.turnMsgIDs.length
        ? sess.turnMsgIDs
        : sess.lastMsgID ? [sess.lastMsgID] : []
      if (!ids.length) return { seq: 0, inLast: false }
      for (const pid of Object.keys(sess.partMsg)) {
        const mid = sess.partMsg[pid]
        if (!mid || !ids.includes(mid)) continue
        const txt = typeof sess.textParts[pid] === "string" ? sess.textParts[pid] : ""
        if (!txt || !txt.includes(GATE_MARKER)) continue
        if (mid === sess.lastMsgID) inLast = true
        const gs = sess.gateSeqAt && sess.gateSeqAt[pid]
        const ps = sess.partSeqAt && sess.partSeqAt[pid]
        const order = Number.isFinite(gs) ? gs : Number.isFinite(ps) ? ps : 0
        if (order > seq) seq = order
      }
      return { seq, inLast }
    }
    for (const pid of Object.keys(sess.partMsg)) {
      const mid = sess.partMsg[pid]
      if (!mid) continue
      // Unknown roles count as assistant (v1 parts may precede message.updated).
      if (sess.roles[mid] && sess.roles[mid] !== "assistant") continue
      const at = sess.msgAt && sess.msgAt[mid]
      const mseq = sess.msgSeqAt && sess.msgSeqAt[mid]
      const after = Number.isFinite(userSeq) && Number.isFinite(mseq)
        ? mseq >= userSeq
        : Number.isFinite(at) && at >= sinceAt
      if (!after) continue
      const txt = typeof sess.textParts[pid] === "string" ? sess.textParts[pid] : ""
      if (!txt || !txt.includes(GATE_MARKER)) continue
      inLast = true // user turn scopes the whole assistant tail
      // First-seen gate seq (NOT the part's latest cumulative stamp).
      const gs = sess.gateSeqAt && sess.gateSeqAt[pid]
      const ps = sess.partSeqAt && sess.partSeqAt[pid]
      const order = Number.isFinite(gs) ? gs : Number.isFinite(ps) ? ps : 0
      if (order > seq) seq = order
    }
    return { seq, inLast }
  }
  const taskClassOf = (block) => {
    // FIRST class declaration in the selected block: a later `- class: DOC`
    // appended to a CODE block must not relicense it.
    const m = String(block || "").match(/^\s*-\s*class:\s*(DOC|CONFIG|CODE)\b/im)
    return m ? m[1].toUpperCase() : ""
  }

  const journalStopDebt = (root, sessionID, trigger, why) => {
    try {
      if (!state.roots[root]) state.roots[root] = {}
      const entry = state.roots[root]
      if (!Array.isArray(entry.stopDebt)) entry.stopDebt = []
      const last = entry.stopDebt[entry.stopDebt.length - 1]
      if (last && last.kind === trigger.kind && last.match === String(trigger.match || "").slice(0, 80) && last.why === why) return // episode dedup
      entry.stopDebt.push({ ts: Date.now(), sessionID, kind: trigger.kind, match: String(trigger.match || "").slice(0, 80), why })
      if (entry.stopDebt.length > STOP_DEBT_CAP) entry.stopDebt = entry.stopDebt.slice(-STOP_DEBT_CAP)
      flush()
    } catch {
      /* debt is advisory */
    }
  }

  const maybeStopGuard = (sessionID) => {
    try {
      if (process.env.VIBEWEAVER_STOPGUARD === "off") return
      if (typeof core.stopEuphemism !== "function" || typeof core.stopGuardDecision !== "function") return
      const sess = state.sessions[sessionID]
      if (!sess) return
      const root = findProjectRoot([directory])
      if (!root) return
      if (!skillLoaded(sess)) return
      if (!sess.stopGuard) sess.stopGuard = { interventions: 0, armed: true, disarmedKey: null }
      const sg = sess.stopGuard
      if (!Number.isFinite(sg.interventions)) sg.interventions = 0
      const lastMid = sess.usage && typeof sess.usage.messageID === "string" ? sess.usage.messageID : null
      const aTail = lastMid ? msgText(sess, lastMid) : (sess.text || "").slice(-2048) // v2 fallback: assistant-sourced deltas
      const uText = msgText(sess, sess.lastUserMid).replace(/^\[(stop-guard|loop-guard)\][^\n]*/gm, "")
      // episode key: the assistant message id when known, else a tail snapshot
      // (null-lastMid hosts must not re-arm on every idle — review F3)
      const armKey = lastMid || "tail:" + aTail.slice(-256)
      if (sg.disarmedKey && armKey !== sg.disarmedKey) {
        sg.armed = true
        sg.disarmedKey = null
      }
      let trigger = core.stopEuphemism(aTail)
      if (!trigger && sess.usage && sess.usage.finish === "length") trigger = { kind: "truncation", match: "length" }
      // whitelist — every leg scoped so history can never immunize the present:
      // paused/Class-E only count when recorded DURING this session (review F5);
      // the gate marker only counts in the SAME message as the claim (F4).
      const sessionStart = Number.isFinite(sess.createdTs) ? sess.createdTs : 0
      let pausedState = false
      let classE = false
      try {
        const pp = path.join(root, "tests", "paused_state.md")
        const pm = Math.floor(statSync(pp, { throwIfNoEntry: false })?.mtimeMs ?? 0)
        pausedState = pm >= sessionStart && sessionStart > 0
          && typeof core.pausedPacketValid === "function" && core.pausedPacketValid(safeRead(pp))
          && typeof core.pausedDeclaration === "function" && core.pausedDeclaration(aTail)
      } catch {
        /* absent */
      }
      try {
        const dp = path.join(root, "tests", "decisions.md")
        const dm = Math.floor(statSync(dp, { throwIfNoEntry: false })?.mtimeMs ?? 0)
        const decText = safeRead(dp)
        const decLen = Number.isFinite(sess.userDecisionsLen) ? sess.userDecisionsLen : 0
        const decTurn = decText.length >= decLen ? decText.slice(decLen) : decText
        classE = dm >= sessionStart && sessionStart > 0
          && typeof core.classERecordValid === "function" && core.classERecordValid(decTurn)
          && typeof core.classEUserApproval === "function" && core.classEUserApproval(uText, aTail)
          && typeof core.classEDeclaration === "function" && core.classEDeclaration(aTail)
      } catch {
        /* absent */
      }
      // userStop: plugin-authored prompts are stripped first (review F1 — the
      // guard must never whitelist itself), then a DIRECTIVE-shaped match with
      // negation exclusion ("don't stop" is not a stop directive — F6).
      const userStop =
        /(^\s*(?:please\s+)?(?:stop|cancel|quit)\b(?!\s+(?:the|a|an)\s)|\bplease\s+(?:stop|cancel|quit)\b|\b(?:stop|cancel|quit)\s+(?:here|now|it|this|coding|working|for today)\b|停一下|停下来|停止吧|别做了|别再做|取消吧|到此为止|今天到这)/i.test(
          uText
        ) && !/((?:don't|do not|never)\s+(?:stop|cancel|quit)|不要停|别停|不能停)/i.test(uText)
      const logPath = path.join(root, "tests", "verification_log.md")
      const logText = safeRead(logPath)
      const userLogLen = Number.isFinite(sess.userLogLen) ? sess.userLogLen : null
      // W11 P0-2: a length is not an identity. Completion/class evidence is
      // read only from an APPEND-ONLY suffix; any rewrite/prepend/truncation
      // fails closed (no stale final-run resurrection).
      let appendOnly = true
      if (userLogLen !== null) {
        appendOnly = logText.length >= userLogLen
          && typeof sess.userLogHash === "string" && sess.userLogHash
          && hashText(logText.slice(0, userLogLen)) === sess.userLogHash
      }
      const turnLog = userLogLen === null ? logText : appendOnly ? logText.slice(userLogLen) : ""
      // W11 re-review: scan the CURRENT task block, not the whole turn slice —
      // a prior task in the same turn must not authenticate a later one. The
      // selector falls back to an evidence-bearing mid-block when there is no
      // `## Task` heading (trailing `## Notes` must not hide the final-run).
      const curBlock = typeof core.currentEvidenceBlock === "function"
        ? core.currentEvidenceBlock(turnLog)
        : userLogLen === null ? logText : turnLog
      // W11 P0-1/P0-2: the current task block's LAST final-run must be corroborated.
      const finalEv = typeof core.finalRunEvidence === "function"
        ? core.finalRunEvidence(curBlock, { root, sinceMs: Number.isFinite(sess.lastUserAt) ? sess.lastUserAt : sessionStart })
        : { trusted: false, reason: "helper-missing" }
      const waveComplete = !!finalEv.trusted
      const taskActive = existsSync(path.join(root, "tests", "acceptance.md")) && sess.tools.length > 0 && !waveComplete
      // W10 scoping: absence of final-run is not proof of abandonment.
      // - Class DOC / a user-scoped read-only instruction is a legitimate
      //   terminal state (C4 audit, evaluation-only, prose).
      // - Awaiting user approval (period-terminated requests included) is a
      //   legitimate pause; the old trailing-? check missed most of them.
      // - The gate marker is turn-scoped AND write-ordered (W11 P0-4).
      const cls = taskClassOf(curBlock)
      // W11 P0-5: a DOC claim is cross-checked against KNOWN code writes this
      // turn (sticky boolean, not an evictable path list). Unknown paths are
      // NOT treated as code for a DOC claim (status-only hosts would always
      // false-positive); the CODE positive path still uses them.
      const codeWriteThisTurn = !!sess.turnCodeWrite
      const forgedClass = cls === "DOC" && codeWriteThisTurn
      const readOnlyByUser = typeof core.stopReadOnlyInstruction === "function" && core.stopReadOnlyInstruction(uText)
      // A read-only instruction is invalidated by a known code write: the
      // model did the thing the user forbade, then went silent.
      const readOnlyTask = (cls === "DOC" && !forgedClass) || (readOnlyByUser && !codeWriteThisTurn)
      const awaitingUser = typeof core.stopAwaitingUser === "function" ? core.stopAwaitingUser(aTail) : /[?？]\s*$/.test(aTail.trim())
      // W11 P1-2: the legacy `tailQuestion` whitelist is now the refined
      // awaiting detector — a bare trailing `?` is not a decision request.
      const tailQuestion = awaitingUser
      const gateInfo = gateInfoSince(sess, sess.lastUserAt, sess.lastUserMid)
      // Positive task evidence: a write/edit to a NON-evidence path after the
      // last user message. Writing acceptance.md/log/report only is not
      // "stopped mid-code".
      const writeSeq = sess.msgSeqAt && sess.lastTaskWriteMsgID ? sess.msgSeqAt[sess.lastTaskWriteMsgID] : NaN
      const userSeq = sess.msgSeqAt && sess.lastUserMid ? sess.msgSeqAt[sess.lastUserMid] : NaN
      const writeMsgAt = sess.msgAt && sess.lastTaskWriteMsgID ? sess.msgAt[sess.lastTaskWriteMsgID] : NaN
      const userMsgAt = sess.msgAt && sess.lastUserMid ? sess.msgAt[sess.lastUserMid] : NaN
      const writeAfterUser = Number.isFinite(writeSeq) && Number.isFinite(userSeq)
        ? writeSeq > userSeq
        : Number.isFinite(writeMsgAt) && Number.isFinite(userMsgAt)
          ? writeMsgAt >= userMsgAt
          : Number.isFinite(sess.lastUserAt)
          ? sess.lastTaskWriteAt >= sess.lastUserAt
          : sess.lastTaskWriteAt >= (sess.createdTs || 0)
      const wroteTaskAfterUser = Number.isFinite(sess.lastTaskWriteAt) && writeAfterUser
        && (sess.lastTaskWriteUnknown || !looksEvidencePath(sess.lastTaskWritePath))
      const gateMarker = gateInfo.seq > 0 && (wroteTaskAfterUser
        ? (Number.isFinite(sess.lastTaskWritePartSeq) && gateInfo.seq >= sess.lastTaskWritePartSeq)
        : gateInfo.inLast)
      const errorFence = Number.isFinite(sess.lastErrorAt)
        && !(Number.isFinite(sess.lastWriteAt) && sess.lastWriteAt > sess.lastErrorAt)
      // The whitelist is applied in stopGuardDecision: v1 read-only/awaiting/
      // gate/paused shapes ignore, while v2 (no user-role boundary) always
      // journals debt for the positive leg — never silently ignores.
      const positiveIncomplete = !trigger && taskActive && wroteTaskAfterUser && !errorFence
      if (!trigger && !positiveIncomplete) return
      const effectiveTrigger = trigger || { kind: "incomplete", match: finalEv.reason === "unbound-final-run" ? "untrusted-final-run" : "no-final-run" }
      const decision = core.stopGuardDecision({ trigger, positiveIncomplete, taskActive, readOnlyTask, awaitingUser, pausedState, classE, errorFence, gateMarker, tailQuestion, userStop, telemetry: hasTelemetry, promptable })
      if (decision.action === "ignore") return
      if (!sg.armed) return
      sg.armed = false
      sg.disarmedKey = armKey
      const cfg = readConfig()
      const maxI = Number.isFinite(cfg.stopGuardMaxInterventions) ? cfg.stopGuardMaxInterventions : STOP_GUARD_MAX_DEFAULT
      const canPrompt = typeof onStopPrompt === "function"
      if (decision.action === "debt" || sg.interventions >= maxI || !canPrompt) {
        const why = decision.action === "debt" ? decision.why : !canPrompt ? "no-prompt-channel" : "budget-exhausted"
        journalStopDebt(root, sessionID, effectiveTrigger, why)
        void log({
          service: "vibeweaver-stopguard",
          level: "info",
          message: `false-stop episode (${effectiveTrigger.kind}: ${String(effectiveTrigger.match).slice(0, 60)}) — intervention budget exhausted (${maxI}/session/stop) or no prompt channel — journaled as stop-debt (${why})`,
          extra: { sessionID, trigger: effectiveTrigger, why },
        })
        return
      }
      sg.interventions++
      let fill = null
      let fillKnown = false
      if (Number.isFinite(cfg.contextLimitTokens) && cfg.contextLimitTokens > 0 && sess.usage && (sess.usage.input > 0 || sess.usage.cacheRead > 0)) {
        fill = ((sess.usage.input || 0) + (sess.usage.cacheRead || 0)) / cfg.contextLimitTokens
        fillKnown = Number.isFinite(fill)
      }
      flush() // arming + budget must survive a mid-episode restart (loop-guard F9)
      void log({
        service: "vibeweaver-stopguard",
        level: "warn",
        message: `false-stop detected (${effectiveTrigger.kind}: ${String(effectiveTrigger.match).slice(0, 60)}) — posting corrective prompt (${sg.interventions}/${maxI}/stop)`,
        extra: { sessionID, trigger: effectiveTrigger, fillKnown: fillKnown ? fill : undefined },
      })
      const text = core.stopGuardPrompt({ kind: effectiveTrigger.kind, fill, fillKnown })
      // identity exclusion (assistantCorpus) covers OUR injections — record
      // stop-guard prompts the same way loop-guard prompts are recorded
      if (!Array.isArray(sess.injectedPrompts)) sess.injectedPrompts = []
      sess.injectedPrompts.push(text)
      if (sess.injectedPrompts.length > 5) sess.injectedPrompts = sess.injectedPrompts.slice(-5)
      void Promise.resolve(onStopPrompt(sessionID, text)).then((ok) => {
        if (ok === false) {
          sg.interventions = Math.max(0, sg.interventions - 1)
          journalStopDebt(root, sessionID, effectiveTrigger, "prompt-failed")
          void log({ service: "vibeweaver-stopguard", level: "warn", message: "stop-guard prompt failed — intervention not counted, debt journaled", extra: { sessionID } })
        }
      }).catch(() => {
        sg.interventions = Math.max(0, sg.interventions - 1)
        journalStopDebt(root, sessionID, effectiveTrigger, "prompt-failed")
        void log({ service: "vibeweaver-stopguard", level: "warn", message: "stop-guard prompt threw — intervention not counted, debt journaled", extra: { sessionID } })
      })
    } catch {
      /* stop-guard must never break observation */
    }
  }

  // ---- v1 observation: message.updated (roles + telemetry for stop-guard) ----
  const observeMessage = (sessionID, info) => {
    if (!info || typeof info !== "object") return
    const sess = touchSession(sessionID)
    if (typeof info.id === "string" && typeof info.role === "string") {
      sess.roles[info.id] = info.role
      if (!sess.msgAt) sess.msgAt = {}
      if (!Number.isFinite(sess.msgAt[info.id])) sess.msgAt[info.id] = Date.now()
      if (!sess.msgSeqAt) sess.msgSeqAt = {}
      if (!Number.isFinite(sess.msgSeqAt[info.id])) {
        sess.msgSeq = (Number.isFinite(sess.msgSeq) ? sess.msgSeq : 0) + 1
        sess.msgSeqAt[info.id] = sess.msgSeq
      }
      const ids = Object.keys(sess.roles)
      if (ids.length > 400) delete sess.roles[ids[0]]
      const mids = Object.keys(sess.msgAt)
      if (mids.length > 400) delete sess.msgAt[mids[0]]
      const seqs = Object.keys(sess.msgSeqAt)
      if (seqs.length > 400) delete sess.msgSeqAt[seqs[0]]
      if (info.role === "user") {
        // Re-emissions of the SAME user message must not move the turn
        // boundary past this turn's write/gate evidence (review I2).
        if (sess.lastUserMid !== info.id) {
          sess.lastUserMid = info.id
          sess.lastUserAt = Date.now()
          // W10 id-less hosts: a genuine user turn is the reset boundary;
          // otherwise turnChars accumulates for the whole session.
          sess.turnChars = 0
          sess.turnCeilingAt = 0
          sess.reasoningChars = 0
          sess.reasoningCeilingAt = 0
          sess.msgChurnAt = []
          sess.turnMsgIDs = []
          // W11: evidence written BEFORE this user message belongs to an
          // earlier task. Completion/class checks read only the log slice
          // appended after this point.
          sess.turnWritePaths = []
          sess.turnCodeWrite = false
          sess.lastTaskWriteUnknown = false
          sess.lastTaskWritePartSeq = NaN
          try {
            const uRoot = findProjectRoot([directory]) || directory
            const uLog = uRoot ? safeRead(path.join(uRoot, "tests", "verification_log.md")) : ""
            sess.userLogLen = uLog.length
            sess.userLogHash = hashText(uLog)
            sess.userDecisionsLen = uRoot ? safeRead(path.join(uRoot, "tests", "decisions.md")).length : 0
          } catch {
            sess.userLogLen = 0
            sess.userLogHash = hashText("")
            sess.userDecisionsLen = 0
          }
        }
      }
      if (info.role === "assistant") {
        // merge, never overwrite wholesale (review F7): a token-less or
        // finish-less field update must not zero the last real measurement.
        const t = info.tokens && typeof info.tokens === "object" ? info.tokens : null
        const cache = t && typeof t.cache === "object" ? t.cache : {}
        const prev = sess.usage && typeof sess.usage === "object" ? sess.usage : {}
        sess.usage = {
          messageID: info.id,
          input: t && Number.isFinite(t.input) ? t.input : prev.input || 0,
          output: t && Number.isFinite(t.output) ? t.output : prev.output || 0,
          cacheRead: t && Number.isFinite(cache.read) ? cache.read : prev.cacheRead || 0,
          finish: typeof info.finish === "string" && info.finish ? info.finish : prev.finish || "",
          modelID: typeof info.modelID === "string" && info.modelID ? info.modelID : prev.modelID || "",
          t: Date.now(),
        }
      }
    }
  }

  // ---- v1 observation: message.part.updated parts ----
  // Episode clock + per-turn output volume: a USER boundary starts a new turn.
  // W11: messageID changes normally also start a new assistant response, but a
  // host that mints a new id per delta/part must not reset the ceiling on every
  // chunk. >=4 id changes inside 5s is treated as churn: counters keep
  // accumulating across the churn.
  const nextPartSeq = (sess) => {
    sess.partSeq = (Number.isFinite(sess.partSeq) ? sess.partSeq : 0) + 1
    return sess.partSeq
  }
  const stampPart = (sess, pid, text, chunk, cumulative) => {
    if (typeof pid !== "string" || !pid) return
    if (!sess.partSeqAt) sess.partSeqAt = {}
    if (!sess.gateSeqAt) sess.gateSeqAt = {}
    if (!sess.gateCountAt) sess.gateCountAt = {}
    if (!sess.gateTextLenAt) sess.gateTextLenAt = {}
    const seq = nextPartSeq(sess)
    sess.partSeqAt[pid] = seq
    if (typeof text === "string") {
      const prevLen = sess.gateTextLenAt[pid] || 0
      let hay = ""
      if (cumulative) {
        // Only scan the grown tail (+ 18-char overlap for a split marker).
        if (text.length > prevLen) hay = text.slice(Math.max(0, prevLen - 18))
        else if (prevLen === 0) hay = text
      } else {
        const body = typeof chunk === "string" ? chunk : text
        const beforeLen = body.length < text.length ? text.length - body.length : 0
        hay = text.slice(Math.max(0, beforeLen - 18), text.length)
      }
      const hits = (hay.match(/\[Verification Gate\]/g) || []).length
      if (hits > 0) {
        sess.gateSeqAt[pid] = seq
        sess.gateCountAt[pid] = (sess.gateCountAt[pid] || 0) + hits
      } else if (cumulative && text.length < prevLen) {
        delete sess.gateSeqAt[pid]
        sess.gateCountAt[pid] = 0
      }
      sess.gateTextLenAt[pid] = text.length
    }
    sess.partSeqPruneAt = (sess.partSeqPruneAt || 0) + 1
    if (sess.partSeqPruneAt >= 64) {
      sess.partSeqPruneAt = 0
      const ids = Object.keys(sess.partSeqAt)
      if (ids.length > 400) {
        const drop = ids.slice(0, ids.length - 400)
        for (const k of drop) {
          delete sess.partSeqAt[k]
          delete sess.gateSeqAt[k]
          delete sess.gateCountAt[k]
          delete sess.gateTextLenAt[k]
        }
      }
    }
  }
  const noteMsg = (sess, messageID) => {
    if (typeof messageID !== "string" || !messageID) return
    if (sess.lastMsgID !== messageID) {
      const now = Date.now()
      if (!Array.isArray(sess.msgChurnAt)) sess.msgChurnAt = []
      sess.msgChurnAt.push(now)
      while (sess.msgChurnAt.length && now - sess.msgChurnAt[0] > 5000) sess.msgChurnAt.shift()
      if (sess.msgChurnAt.length > 8) sess.msgChurnAt = sess.msgChurnAt.slice(-8)
      const churn = sess.msgChurnAt.length >= 4
      if (!churn) {
        sess.turnChars = 0
        sess.turnCeilingAt = 0
        sess.reasoningChars = 0
        sess.reasoningCeilingAt = 0
      }
    }
    sess.lastMsgID = messageID
  }
  const noteTurnMsg = (sess, messageID) => {
    if (typeof messageID !== "string" || !messageID) return
    if (!Array.isArray(sess.turnMsgIDs)) sess.turnMsgIDs = []
    if (!sess.turnMsgIDs.includes(messageID)) sess.turnMsgIDs.push(messageID)
    if (sess.turnMsgIDs.length > 100) sess.turnMsgIDs = sess.turnMsgIDs.slice(-100)
  }

  const markTurnWrite = (sess, filePath, unknown) => {
    const fp = typeof filePath === "string" ? filePath.replace(/\\/g, "/") : ""
    // Sticky boolean survives the bounded path-list eviction (a DOC claim must
    // not be washable by 50 later prose writes).
    if (!unknown && isCodeWritePath(fp)) sess.turnCodeWrite = true
    if (!Array.isArray(sess.turnWritePaths)) sess.turnWritePaths = []
    sess.turnWritePaths.push({ path: fp, unknown: !!unknown, at: Date.now() })
    if (sess.turnWritePaths.length > 50) sess.turnWritePaths = sess.turnWritePaths.slice(-50)
  }
  // W11 P1-4: write evidence is recorded ONCE per call, and only for a
  // completed write. A missing filePath is unknown (not evidence) — the
  // positive path decides by class instead of silently losing the write.
  const recordWriteEvidence = (sess, filePath, messageID) => {
    const fp = typeof filePath === "string" ? filePath.replace(/\\/g, "/") : ""
    const unknown = !fp
    markTurnWrite(sess, fp, unknown)
    sess.lastWriteAt = Date.now()
    // Prose evidence (tests/*.md, docs/*.md, reports) is not a task write;
    // code under tests/ (e.g. a test harness) still is.
    if (!unknown && looksEvidencePath(fp) && PROSE_WRITE_RE.test(fp)) return
    sess.lastTaskWriteAt = Date.now()
    sess.lastTaskWritePath = fp
    sess.lastTaskWriteMsgID = messageID || null
    sess.lastTaskWriteUnknown = unknown
    sess.lastTaskWritePartSeq = nextPartSeq(sess)
  }
  // W11: v1 hosts may write files through bash (`cat > src/a.ts`). A silent
  // stop after only such a write must still be caught. Conservative parse:
  // only explicit redirects / tee / cp / mv targets; evidence paths are
  // filtered by recordWriteEvidence.
  const stripHeredocBodies = (command) => {
    if (typeof command !== "string" || !command.includes("<<")) return command
    let out = ""
    let i = 0
    let q = null
    while (i < command.length) {
      const ch = command[i]
      if (q) { out += ch; if (ch === q) q = null; i++; continue }
      if (ch === "'" || ch === '"') { q = ch; out += ch; i++; continue }
      if (ch === "#" && (i === 0 || /[\s;&|]/.test(command[i - 1]))) {
        const nl = command.indexOf("\n", i)
        if (nl < 0) break
        out += "\n"
        i = nl + 1
        continue
      }
      if (ch === "<" && command[i + 1] === "<") {
        let j = i + 2
        let dash = false
        if (command[j] === "-") { dash = true; j++ }
        while (j < command.length && /\s/.test(command[j])) j++
        const dq = command[j] === "'" || command[j] === '"' ? command[j] : ""
        let delim = ""
        if (dq) {
          j++
          const start = j
          while (j < command.length && command[j] !== dq) j++
          delim = command.slice(start, j); j++
        } else {
          const start = j
          while (j < command.length && !/[\s;&|]/.test(command[j])) j++
          delim = command.slice(start, j)
        }
        if (!delim) { out += command.slice(i, j); i = j; continue }
        const nl = command.indexOf("\n", j)
        if (nl < 0) { out += command.slice(i); break }
        out += command.slice(i, nl + 1)
        let end = -1
        if (dash) {
          const esc = delim.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
          const re = new RegExp("\\n[\\t ]*" + esc + "(?=\\n|$)", "g")
          re.lastIndex = nl
          const m = re.exec(command)
          if (m) end = m.index
        } else {
          end = command.indexOf("\n" + delim, nl)
        }
        if (end < 0) { out += command.slice(i); break }
        const endLine = command.indexOf("\n", end + 1)
        i = endLine < 0 ? command.length : endLine + 1
        continue
      }
      out += ch; i++
    }
    return out
  }
  const bashWriteTargets = (command) => {
    if (typeof command !== "string" || !command) return []
    // Quote-aware heredoc removal: a quoted `<<` in an echo is not a heredoc,
    // and a redirect after the delimiter is still visible on the header line.
    const first = stripHeredocBodies(command)
    const out = []
    let q = null
    let esc = false
    for (let i = 0; i < first.length; i++) {
      const ch = first[i]
      if (esc) { esc = false; continue }
      if (ch === "\\") { esc = true; continue }
      if (q) { if (ch === q) q = null; continue }
      if (ch === "'" || ch === '"') { q = ch; continue }
      if (ch !== ">") continue
      if (first[i + 1] === "&") { i++; continue } // >&1
      // fd redirect only when the digit run is a standalone token (2>), not
      // part of a filename (foo2>).
      let d = i - 1
      while (d >= 0 && /\d/.test(first[d])) d--
      if (d < i - 1 && (d < 0 || /[\s;&|()]/.test(first[d]))) continue
      let j = i + 1
      if (first[j] === ">") j++
      while (j < first.length && /\s/.test(first[j])) j++
      const start = j
      while (j < first.length && !/[\s;&|()<>]/.test(first[j])) j++
      const target = first.slice(start, j).replace(/^['"]+|['"]+$/g, "")
      if (target) out.push(target)
      i = j - 1
    }
    const tokens = (s) => s.match(/(?:[^\s'"]+|"[^"]*"|'[^']*')+/g) || []
    for (const m of first.matchAll(/\b(tee|cp|mv)\b([^;&|()\n]*)/g)) {
      const raw = tokens(m[2])
      if (m[1] !== "tee") {
        const ti = raw.indexOf("-t")
        if (ti >= 0 && raw[ti + 1]) { out.push(raw[ti + 1]); continue }
        const tds = raw.indexOf("--target-directory")
        if (tds >= 0 && raw[tds + 1]) { out.push(raw[tds + 1]); continue }
        const td = raw.find((t) => t.startsWith("--target-directory="))
        if (td) { out.push(td.slice(td.indexOf("=") + 1)); continue }
        const combined = raw.find((t) => /^-[A-Za-z]*t[A-Za-z]*$/.test(t))
        const attachedT = raw.find((t) => /^-[A-Za-z]*t\S+/.test(t))
        if (attachedT) {
          const val = attachedT.slice(attachedT.indexOf("t") + 1)
          if (val) { out.push(val); continue }
        }
        if (combined) {
          const idx = raw.indexOf(combined)
          if (raw[idx + 1]) { out.push(raw[idx + 1]); continue }
        }
      }
      const args = raw.map((t) => t.replace(/^['"]+|['"]+$/g, "")).filter((t) => t && !t.startsWith("-"))
      if (m[1] === "tee") out.push(...args)
      else if (args.length >= 2) out.push(args[args.length - 1]) // destination
    }
    return out
      .map((p) => p.replace(/^['"]+|['"]+$/g, ""))
      .filter((p) => p && !p.startsWith("&") && !p.startsWith("-"))
  }
  const recordBashWrites = (sess, command, messageID, holder) => {
    if (!holder || holder.writeRecorded) return
    const root = findProjectRoot([directory])
    const targets = bashWriteTargets(command).filter((p) => {
      if (p.startsWith("/dev/")) return false
      if (!root) return true
      const abs = path.resolve(root, p)
      return abs === root || abs.startsWith(root + path.sep)
    })
    if (!targets.length) return
    for (const target of targets) recordWriteEvidence(sess, target, messageID)
    holder.writeRecorded = true
  }

  const observePart = (sessionID, part) => {
    if (!part || typeof part !== "object") return
    const sess = touchSession(sessionID)
    const ptext =
      typeof part.text === "string" && part.text ? part.text : part.type === "reasoning" && typeof part.content === "string" ? part.content : ""
    if ((part.type === "text" || part.type === "reasoning") && ptext) {
      // Robust against three streaming shapes: cumulative full-text updates,
      // delta chunks, and duplicate re-emissions. Inclusion heuristics:
      //   newText inside buffer  -> duplicate, skip
      //   buffer inside newText  -> cumulative update, replace
      //   neither                -> delta chunk, append
      // reasoning parts ride the same machinery in their own buffer/channel
      // (hermes #97630: a wall living only in reasoning_content is invisible
      // to any content-only guard).
      const reasoning = part.type === "reasoning"
      const store = reasoning ? sess.reasoningParts || (sess.reasoningParts = {}) : sess.textParts
      const pid = part.id || (reasoning ? "reasoning" : "text")
      const buf = store[pid] || ""
      // Three-shape robustness (cumulative / delta / duplicate re-emission)
      // with BOUNDED per-event work (SIGTRAP hardening round 2, 2026-10-17):
      // `buf + ptext` materializes the FULL cumulative text every event
      // (quadratic over a streaming turn — the 57GB malloc storm), and the
      // `includes` pair is O(n·m) on big strings. Exact-duplicate and a
      // bounded superset probe cover the real streaming shapes.
      //
      // Duplicate = WHOLE-BUFFER re-emission (`ptext === buf`) of a REAL part
      // state (≥ the detector's minimum period) — the old arbitrary-substring
      // `includes` ate ordinary delta chunks that merely occurred inside the
      // buffer (common words), silently truncating the observed stream AND
      // starving turnChars: the runaway ceiling stayed dark in production
      // while long runaway turns kept streaming (2026-10-17 crashes). Small
      // buffers always append: an identical-chunk spam ("!"×N delivered as
      // 1-char deltas) must keep accumulating or the wall detectors go blind
      // to it (T42); the cost of a double-appended tiny re-emission is a few
      // chars of turnChars, nothing the ≥3-copy bars can see.
      if (ptext === buf && buf.length >= LOOP_CHAR_MIN_PERIOD) {
        // duplicate re-emission — state unchanged: skip the
        // re-check AND the episode-clock advance (re-checking unchanged
        // text can re-fire on a stale tail; advancing lastMsgID on a
        // re-associated id fakes a new turn — review C2/N3)
        return
      }
      if (typeof part.messageID === "string" && part.messageID) {
        sess.partMsg[pid] = part.messageID
        noteMsg(sess, part.messageID)
        noteTurnMsg(sess, part.messageID)
        const pids = Object.keys(sess.partMsg)
        if (pids.length > 400) delete sess.partMsg[pids[0]]
      }
      // superset (cumulative update): exact `startsWith` for grown buffers,
      // `includes` only for small ones; a capped buffer carries the truncation
      // marker so a later cumulative update falls to the bounded merge below
      // (its head/tail land exactly where capText(buf + ptext) would keep them).
      const cumulative = ptext.length > buf.length && buf.length > 0 && (buf.length <= 1024 ? ptext.includes(buf) : ptext.startsWith(buf.slice(0, 64)))
      const added = cumulative ? Math.max(0, ptext.length - buf.length) : ptext.length
      if (cumulative) {
        store[pid] = capPart(ptext)
        if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
        else sess.turnChars = (sess.turnChars || 0) + added
      } else if (buf.length + ptext.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL) {
        // byte-equivalent of capText(buf + ptext) WITHOUT materializing it:
        // head(buf) + marker + tail(ptext) — the detectors read the tail and
        // the audit reads head+tail, so nothing observable is lost.
        store[pid] = buf.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + ptext.slice(-TEXT_CAP_TAIL)
        if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
        else sess.turnChars = (sess.turnChars || 0) + added
      } else {
        store[pid] = capPart(buf + ptext)
        if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
        else sess.turnChars = (sess.turnChars || 0) + added
      }
      pruneParts(store)
      stampPart(sess, pid, store[pid], ptext, cumulative)
      // D1-④: genuine user input (human user-role text, never a plugin
      // corrective prompt) decays the loop-guard budget and re-arms episodes.
      if (!reasoning) {
        const midForPid = sess.partMsg[pid]
        const roleForPid = midForPid && sess.roles ? sess.roles[midForPid] : null
        if (roleForPid === "user" && !isPluginInjected(ptext)) decayLoopBudget(sess)
      }
      maybeTextScan(sessionID, sess, reasoning ? "reasoning" : "text", added)
    } else if (part.type === "tool" && part.tool) {
      const st = part.state || {}
      const t = { tool: part.tool, t: Date.now() }
      noteMsg(sess, part.messageID)
      if (typeof part.id === "string" && part.id) t.pid = part.id
      // Re-observation of a call we already recorded (v1 re-emits the part on
      // every state change): only fill a missing result — never re-process
      // the input (SIGTRAP round 3: each re-emission used to deep-copy and
      // stringify the FULL tool arguments).
      if (t.pid) {
        for (let i = sess.tools.length - 1; i >= 0 && i >= sess.tools.length - 40; i--) {
          const prev = sess.tools[i]
          if (prev && prev.pid === t.pid) {
            if (typeof st.output === "string" && st.output && !prev.output) prev.output = st.output.slice(0, OUT_CAP)
            // v1 emits running → completed for the SAME part id; the early
            // return used to skip the completion timestamp and kill the
            // positive stop-guard on real hosts. Record the write ONCE.
            if (st.status === "completed" && (part.tool === "write" || part.tool === "edit") && !prev.writeRecorded) {
              const fp = (st.input && typeof st.input.filePath === "string" ? st.input.filePath : prev.filePath) || ""
              recordWriteEvidence(sess, fp, part.messageID || null)
              prev.writeRecorded = true
            }
            if (st.status === "completed" && part.tool === "bash" && st.input && typeof st.input.command === "string") {
              recordBashWrites(sess, st.input.command, part.messageID || null, prev)
            }
            return
          }
        }
      }
      // Successful, first observation only: a v1 re-observation or a failed
      // write must not clear the abort fence / turn scope.
      if ((part.tool === "write" || part.tool === "edit") && st.status === "completed") {
        const fp = st.input && typeof st.input.filePath === "string" ? st.input.filePath : ""
        recordWriteEvidence(sess, fp, part.messageID || null)
        t.writeRecorded = true
      }
      if (part.tool === "bash" && st.status === "completed" && st.input && typeof st.input.command === "string") {
        recordBashWrites(sess, st.input.command, part.messageID || null, t)
      }
      const inp = st.input && typeof st.input === "object" ? st.input : null
      if (inp) {
        if (typeof inp.filePath === "string") t.filePath = inp.filePath
        if (typeof inp.command === "string") {
          t.command = inp.command.slice(0, IN_CAP)
          if (inp.command.length > IN_CAP) t.truncated = true // truncation can forge a literal (F10)
        }
        if (typeof inp.name === "string") t.name = inp.name
        // canonical args identity (identical-tool-run): status-only
        // re-observations carry NO input and must never fabricate one;
        // oversized inputs get a bounded sampled FINGERPRINT (F10 refinement:
        // what breaks a run is a truncated/forgeable identity — a
        // deterministic fingerprint keeps identity, so identical-tool-run
        // still sees big-args storms) instead of a deep copy.
        let canon = ""
        if (inputTooBig(inp)) {
          if (typeof core.bigFingerprint === "function") {
            try {
              canon = "big:" + core.bigFingerprint(inp)
            } catch {
              canon = ""
            }
          }
          if (!canon) t.truncated = true // no fingerprint available: F10 fallback
        } else {
          try {
            canon = typeof core.canonicalJson === "function" ? core.canonicalJson(inp) : JSON.stringify(inp)
          } catch {
            canon = "" // a throwing input must never break observation
          }
        }
        if (canon) {
          t.args = canon.length > IN_CAP ? canon.slice(0, IN_CAP) : canon
          if (canon.length > IN_CAP) t.truncated = true // truncation can forge identity (F10)
        }
      }
      // result summary (D1-③) for ANY tool — the identical-run detector
      // compares results, and only bash used to be captured
      if (typeof st.output === "string" && st.output) t.output = st.output.slice(0, OUT_CAP)
      sess.tools.push(t)
      if (sess.tools.length > TOOL_CAP) sess.tools = sess.tools.slice(-TOOL_CAP)
      if (part.tool === "skill" && inp && typeof inp.name === "string" && inp.name.startsWith("vibeweaver")) sess.skillLoaded = true
      maybeToolLoopCheck(sessionID)
    }
  }

  // ---- v2 observation: tool hooks + session.* events ----
  const observeToolStart = (sessionID, tool, input, messageID, callID) => {
    if (typeof sessionID !== "string" || !sessionID || typeof tool !== "string" || !tool) return
    const sess = touchSession(sessionID)
    noteMsg(sess, messageID)
    const t = { tool, t: Date.now() }
    if (typeof callID === "string" && callID) t.pid = callID
    if (typeof messageID === "string" && messageID) t.mid = messageID
    // args identity only when input was ACTUALLY observed — a call observed
    // without input must never fabricate the `{}` identity (acceptance #4)
    const inp = input && typeof input === "object" ? input : null
    if (inp) {
      if (typeof inp.filePath === "string") t.filePath = inp.filePath
      if (typeof inp.command === "string") {
        t.command = inp.command.slice(0, IN_CAP)
        if (inp.command.length > IN_CAP) t.truncated = true // truncation can forge a literal (F10)
      }
      if (typeof inp.name === "string") t.name = inp.name
      // oversized inputs get a bounded sampled fingerprint (F10 refinement,
      // same as the v1 branch) instead of being deep-copied by canonicalJson
      let canon = ""
      if (inputTooBig(inp)) {
        if (typeof core.bigFingerprint === "function") {
          try {
            canon = "big:" + core.bigFingerprint(inp)
          } catch {
            canon = ""
          }
        }
        if (!canon) t.truncated = true // no fingerprint available: F10 fallback
      } else {
        try {
          canon = typeof core.canonicalJson === "function" ? core.canonicalJson(inp) : JSON.stringify(inp)
        } catch {
          canon = "" // a throwing input must never fail the tool hook
        }
      }
      if (canon) {
        t.args = canon.length > IN_CAP ? canon.slice(0, IN_CAP) : canon
        if (canon.length > IN_CAP) t.truncated = true // truncation can forge identity (F10)
      }
    }
    sess.tools.push(t)
    if (sess.tools.length > TOOL_CAP) sess.tools = sess.tools.slice(-TOOL_CAP)
    if (tool === "skill" && inp && typeof inp.name === "string" && inp.name.startsWith("vibeweaver")) sess.skillLoaded = true
    maybeToolLoopCheck(sessionID)
  }

  const observeToolEnd = (sessionID, tool, result, callID) => {
    if (typeof sessionID !== "string" || !sessionID || typeof tool !== "string" || !tool) return
    const sess = touchSession(sessionID)
    // W11 P1-4: v2 write evidence is recorded only after a successful
    // execute.after. A blocked/failed write never produces this event (the
    // hook filters status !== "completed"), so it cannot pollute the debt.
    if (tool === "write" || tool === "edit") {
      let idx = -1
      if (typeof callID === "string" && callID) {
        for (let i = sess.tools.length - 1; i >= 0; i--) {
          if (sess.tools[i] && sess.tools[i].pid === callID) { idx = i; break }
        }
      }
      if (idx < 0) {
        for (let i = sess.tools.length - 1; i >= 0; i--) {
          if (sess.tools[i] && sess.tools[i].tool === tool && !sess.tools[i].writeRecorded) { idx = i; break }
        }
      }
      if (idx >= 0 && !sess.tools[idx].writeRecorded) {
        const entry = sess.tools[idx]
        recordWriteEvidence(sess, entry.filePath || "", entry.mid || null)
        entry.writeRecorded = true
      }
    }
    // W11 re-review: v2 bash redirects are writes too. Match the completed
    // call by id (or the latest unrecorded bash observation).
    if (tool === "bash") {
      let idx = -1
      if (typeof callID === "string" && callID) {
        for (let i = sess.tools.length - 1; i >= 0; i--) {
          if (sess.tools[i] && sess.tools[i].pid === callID) { idx = i; break }
        }
      }
      if (idx < 0) {
        for (let i = sess.tools.length - 1; i >= 0; i--) {
          if (sess.tools[i] && sess.tools[i].tool === "bash" && !sess.tools[i].writeRecorded) { idx = i; break }
        }
      }
      if (idx >= 0 && sess.tools[idx].command) {
        recordBashWrites(sess, sess.tools[idx].command, sess.tools[idx].mid || null, sess.tools[idx])
      }
    }
    // Tool.Result = { output?, content?: string | Content[], metadata? } —
    // content is the model-visible channel; output is the structured value.
    const content = result && typeof result === "object" ? result.content : result
    let text = ""
    if (typeof content === "string") text = content
    else if (Array.isArray(content)) {
      // bounded gather: only enough blocks to fill the OUT_CAP summary —
      // joining an unbounded block array materializes the whole result
      const parts = []
      let got = 0
      for (const c of content) {
        if (!c || c.type !== "text" || typeof c.text !== "string" || !c.text) continue
        parts.push(c.text)
        got += c.text.length
        if (got >= OUT_CAP * 2) break
      }
      text = parts.join("\n")
    }
    if (!text && result && typeof result === "object" && typeof result.output === "string") text = result.output
    if (!text) return
    for (let i = sess.tools.length - 1; i >= 0; i--) {
      if (sess.tools[i].tool === tool && !sess.tools[i].output) {
        sess.tools[i].output = text.slice(0, OUT_CAP)
        break
      }
    }
  }

  const observeTextDelta = (sessionID, messageID, delta, channel) => {
    if (typeof sessionID !== "string" || !sessionID || typeof delta !== "string" || !delta) return
    const sess = touchSession(sessionID)
    const reasoning = channel === "reasoning"
    const pid = typeof messageID === "string" && messageID ? messageID : reasoning ? "reasoning" : "text"
    // session.text.delta events are pure increments in emission order.
    // W10: hidden reasoning is not visible-output runaway — only text counts
    // toward the ceiling (the reasoning channel still has shape detectors).
    noteMsg(sess, messageID)
    noteTurnMsg(sess, messageID)
    if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + delta.length
    else sess.turnChars = (sess.turnChars || 0) + delta.length
    const store = reasoning ? sess.reasoningParts || (sess.reasoningParts = {}) : sess.textParts
    // rope-append O(1); flatten+cap only on overshoot (per-token capPart
    // re-flattened the whole buffer every delta — SIGTRAP round 2)
    const next = (store[pid] || "") + delta
    store[pid] = next.length > (TEXT_CAP_HEAD + TEXT_CAP_TAIL) * 2 ? capPart(next) : next
    pruneParts(store)
    stampPart(sess, pid, store[pid], delta, false)
    maybeTextScan(sessionID, sess, reasoning ? "reasoning" : "text", delta.length)
  }

  const ingestFull = (sess, sessionID, messageID, items, reasoning) => {
    const joined = items
      .filter((c) => c && (typeof c.text === "string" || typeof c.content === "string"))
      .map((c) => (typeof c.text === "string" && c.text ? c.text : c.content))
      .join("\n")
    if (!joined) return
    noteMsg(sess, messageID)
    noteTurnMsg(sess, messageID)
    // bare messageID as key (NEVER a per-channel suffix — the same content
    // arriving via deltas AND content-updates must reconcile into ONE buffer
    // entry and count ONCE; the "#r" suffix double-counted turnChars and
    // duplicated the scan buffer — review C1)
    const pid = typeof messageID === "string" && messageID ? messageID : reasoning ? "reasoning" : "text"
    const store = reasoning ? sess.reasoningParts || (sess.reasoningParts = {}) : sess.textParts
    const buf = store[pid] || ""
    // same three-shape robustness as the v1 cumulative-update branch, same
    // bounded rules (SIGTRAP round 2 — never materialize buf+joined); the
    // duplicate shape is whole-buffer re-emission of a real part state only
    // (substring/tail matches must never eat real content — 2026-10-17)
    if (joined === buf && buf.length >= LOOP_CHAR_MIN_PERIOD) return
    const cumulative = joined.length > buf.length && buf.length > 0 && (buf.length <= 1024 ? joined.includes(buf) : joined.startsWith(buf.slice(0, 64)))
    const added = cumulative ? Math.max(0, joined.length - buf.length) : joined.length
    if (cumulative) {
      store[pid] = capPart(joined)
      if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
      else sess.turnChars = (sess.turnChars || 0) + added
    } else if (buf.length + joined.length > TEXT_CAP_HEAD + TEXT_CAP_TAIL) {
      store[pid] = buf.slice(0, TEXT_CAP_HEAD) + "\n…[truncated]…\n" + joined.slice(-TEXT_CAP_TAIL)
      if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
      else sess.turnChars = (sess.turnChars || 0) + added
    } else {
      store[pid] = capPart(buf + joined)
      if (reasoning) sess.reasoningChars = (sess.reasoningChars || 0) + added
      else sess.turnChars = (sess.turnChars || 0) + added
    }
    pruneParts(store)
    stampPart(sess, pid, store[pid], joined, cumulative)
    maybeTextScan(sessionID, sess, reasoning ? "reasoning" : "text", added)
  }

  const observeFullContent = (sessionID, messageID, content) => {
    if (typeof sessionID !== "string" || !sessionID || !Array.isArray(content)) return
    const sess = touchSession(sessionID)
    ingestFull(sess, sessionID, messageID, content.filter((c) => c && c.type === "text"), false)
    ingestFull(sess, sessionID, messageID, content.filter((c) => c && c.type === "reasoning"), true)
  }

  const observeSkill = (sessionID, name) => {
    if (typeof sessionID !== "string" || !sessionID) return
    const sess = touchSession(sessionID)
    if (typeof name === "string" && name.startsWith("vibeweaver")) sess.skillLoaded = true
  }

  // Host error/abort: never auto-resume a turn the user just cancelled.
  // A later successful write clears the error fence.
  const observeError = (sessionID) => {
    if (typeof sessionID !== "string" || !sessionID) return
    touchSession(sessionID).lastErrorAt = Date.now()
  }

  // RED-latch write gate (shared by both execute.before adapters).
  // Returns the block message to throw, or null.
  const beforeWrite = ({ tool, sessionID, filePath }) => {
    if (tool !== "write" && tool !== "edit") return null
    if (process.env.VIBEWEAVER_AUDIT === "off") return null
    const cur = typeof sessionID === "string" && sessionID ? sessionID : null
    const root = findProjectRoot([directory, filePath ? path.dirname(filePath) : null])
    if (!root || !state.roots[root]) return null
    releaseStale(root, cur, "write")
    const latch = readLatch(state.roots[root])
    if (!latch) return null
    if (filePath && isTestDirPath(root, filePath)) return null
    const selfLatched = cur === latch.sessionID
    return selfLatched
      ? "GATE-BLOCKED (vibeweaver-audit): YOUR session's mechanical audit is RED — read tests/gate_audit.md. To unblock: fix each [BAD] item (any test directory — tests/, dev/tests/, … — stays writable: repair the missing evidence and append `- audit-fix: …` entries to tests/verification_log.md), then re-emit a corrected [Verification Gate] line in your reply. The audit re-runs at every session idle and re-checks on every write. Starting a NEW task in this session? Per protocol write tests/acceptance.md first (Step 1 — tests/ is writable right now): a post-latch acceptance rewrite auto-releases the latch on your next gated write (journaled as new-task) — no other session, no TTL wait, no VIBEWEAVER_AUDIT=off needed; the old wave's debt stays in tests/gate_audit.md and your new wave's own final audit re-checks everything. Escalate via VIBEWEAVER_AUDIT=off only with user consent."
      : "GATE-BLOCKED (vibeweaver-audit): a mechanical RED latch for this project is still pending — read tests/gate_audit.md. The latch belongs to the session that earned it and does NOT release on other sessions' writes (D3: subagent/task-tool writes count as foreign). It releases only on that session's own new task (tests/acceptance.md rewritten after the latch) or after the red TTL (default 24h). Any test directory (tests/, dev/tests/, …) stays writable so evidence can be repaired. Escalate via VIBEWEAVER_AUDIT=off only with user consent."
  }

  // Session-idle driver (v1 "session.idle"; v2 "session.status" idle).
  const handleIdle = async (sessionID) => {
    if (typeof sessionID !== "string" || !sessionID) return
    if (process.env.VIBEWEAVER_AUDIT === "off") return
    // A stale latch (legacy / TTL) must not survive forever — the release
    // pass runs BEFORE the audit. D3: foreign sessions no longer release
    // anything; a fresh latch of THIS session survives (releaseStale refuses
    // it) and its own final audit decides.
    const idleRoot = findProjectRoot([directory])
    if (idleRoot) releaseStale(idleRoot, sessionID, "idle")
    flush()
    const sess = state.sessions[sessionID]
    // mid-task idle (no completion marker yet) -> warn-only audit, no red.
    // Skill-absent sessions have no gate line by definition: their final
    // audit is always meaningful (C17 skill-absent detection).
    const phase = sess && (completionHeuristic(sess) || !skillLoaded(sess)) ? "final" : "mid"
    const result = await runAudit(sessionID, phase)
    if (result && result.audit) {
      await log({
        service: "vibeweaver-audit",
        level: result.audit.red ? "warn" : result.audit.escalate ? "info" : "debug",
        message: `Audit ${result.audit.red ? "RED" : result.audit.escalate ? "ESCALATE" : "GREEN"} (BAD=${result.audit.bad} UNCERTAIN=${result.audit.uncertain})`,
        extra: { escalateReasons: result.audit.escalateReasons },
      })
    }
    maybeStopGuard(sessionID)
    // W11: v2 has no user-role boundary; clear the turn write evidence and
    // re-anchor the log at idle so a later task cannot inherit an earlier
    // CODE write or a completed old block. Role-less v1 hosts keep their
    // session-start snapshot (their writes stay attributable).
    const s2 = state.sessions[sessionID]
    const hasUserRole = !!(s2 && s2.roles && Object.values(s2.roles).includes("user"))
    const roleLess = !hasUserRole
    if (s2 && (!hasTelemetry || roleLess)) {
      s2.turnWritePaths = []
      s2.turnMsgIDs = []
      s2.turnCodeWrite = false
      s2.lastTaskWriteAt = 0
      s2.lastTaskWritePath = ""
      s2.lastTaskWriteUnknown = false
      s2.lastTaskWritePartSeq = NaN
      // A host with no user-role boundary has no other way to scope a turn;
      // clear the gate bookkeeping so an old gate cannot whitelist the next
      // one. Keep textParts/partMsg so the normal audit can still see the
      // completion text (T22 latch self-clear depends on it).
      s2.gateSeqAt = {}
      s2.gateCountAt = {}
      s2.gateTextLenAt = {}
      s2.partSeqAt = {}
      s2.turnChars = 0
      s2.turnCeilingAt = 0
      s2.reasoningChars = 0
      s2.reasoningCeilingAt = 0
      try {
        const txt = idleRoot ? safeRead(path.join(idleRoot, "tests", "verification_log.md")) : ""
        s2.userLogLen = txt.length
        s2.userLogHash = hashText(txt)
      } catch {
        /* keep the previous anchor */
      }
    }
  }

  return {
    observePart,
    observeMessage,
    observeToolStart,
    observeToolEnd,
    observeTextDelta,
    observeFullContent,
    observeSkill,
    observeError,
    beforeWrite,
    handleIdle,
  }
}

// ---------- opencode v1 adapter ----------

async function server({ client, directory }) {
  const core = await loadCore()
  if (!core) {
    // fail-safe: never crash opencode; the audit just stays silent
    console.error("[vibeweaver-audit] core module not found — audit disabled (set VIBEWEAVER_AUDIT_CORE)")
    return {}
  }
  const m = createAuditMachine({
    directory,
    core,
    log: (entry) => logToHost(client && client.app, entry),
    // loop-guard intervention (v1): stop the runaway generation, then resume
    // with a corrective user message. Provided only when the session APIs
    // exist — otherwise the guard stays fully inactive (no phantom budget).
    // API failures are swallowed — the loop-guard is best-effort and must
    // never break the hook.
    onDegenerate:
      client && client.session && typeof client.session.abort === "function" && typeof client.session.prompt === "function"
        ? async (sessionID, finding) => {
            try {
              await client.session.abort({ path: { id: sessionID } })
            } catch {
              /* best-effort */
            }
            try {
              await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: loopRecoveryText(finding) }] } })
            } catch {
              /* best-effort */
            }
          }
        : undefined,
    // stop-guard intervention (v1): idle-time corrective prompt — NO abort
    // (the turn already ended; aborting an idle session is meaningless).
    onStopPrompt:
      client && client.session && typeof client.session.prompt === "function"
        ? async (sessionID, text) => {
            try {
              await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text }] } })
              return true
            } catch {
              return false
            }
          }
        : undefined,
    capabilities: { telemetry: true }, // v1 message.updated carries role/tokens/finish (spike W0)
  })
  return {
    // Block BEFORE the write lands. The RED latch is scoped to the session
    // that earned it: a different session (or TTL/legacy staleness) releases
    // it right here, so a truncated or dead session can never hold the next
    // task hostage. Any test/tests directory stays writable so evidence
    // fixes never deadlock.
    "tool.execute.before": async (input, output) => {
      if (!input || (input.tool !== "write" && input.tool !== "edit")) return
      const args = (input && input.args) || (output && output.args) || {}
      const msg = m.beforeWrite({
        tool: input.tool,
        sessionID: input.sessionID,
        filePath: writePathFromArgs(args),
      })
      if (msg) throw new Error(msg)
    },
    event: async ({ event }) => {
      if (!event || !event.type || !event.properties) return
      const props = event.properties
      const sessionID = props.sessionID
      if (event.type === "message.part.updated" && sessionID) {
        m.observePart(sessionID, props.part)
      } else if (event.type === "message.updated" && sessionID) {
        m.observeMessage(sessionID, props.info)
      } else if (event.type === "session.error" && sessionID) {
        m.observeError(sessionID)
      } else if (event.type === "session.idle" && sessionID) {
        await m.handleIdle(sessionID)
      }
    },
  }
}

// ---------- opencode v2 adapter ----------

async function setup(ctx) {
  const core = await loadCore()
  if (!core) {
    console.error("[vibeweaver-audit] core module not found — audit disabled (set VIBEWEAVER_AUDIT_CORE)")
    return
  }
  const directory = ctx && ctx.location && typeof ctx.location.directory === "string" ? ctx.location.directory : null
  const hasV2Apis = !!(ctx && ctx.tool && typeof ctx.tool.hook === "function" && ctx.event && typeof ctx.event.subscribe === "function")
  if (!directory || !hasV2Apis) {
    // opencode v1's hybrid bridge calls setup() with a partial context (no
    // location/tool/event domains) — that is EXPECTED there and the v1 server
    // adapter provides the audit, so stay silent. Warn only when a location
    // IS present (a genuine v2 host missing hook/event APIs).
    if (directory && !hasV2Apis) {
      console.warn("[vibeweaver-audit] v2 setup: ctx.tool.hook/ctx.event.subscribe unavailable in this host — v2 adapter inactive for this instance")
    }
    return
  }
  const m = createAuditMachine({
    directory,
    core,
    log: (entry) => logToHost(null, entry),
    // loop-guard intervention (v2): interrupt (no auto-continue), then resume
    // with a corrective prompt. Absent session APIs degrade to observation-only.
    onDegenerate:
      ctx.session && typeof ctx.session.interrupt === "function" && typeof ctx.session.prompt === "function"
        ? async (sessionID, finding) => {
            try {
              await ctx.session.interrupt({ sessionID, continue: false })
            } catch {
              /* best-effort */
            }
            try {
              await ctx.session.prompt({ sessionID, text: loopRecoveryText(finding) })
            } catch {
              /* best-effort */
            }
          }
        : undefined,
    // stop-guard (v2): explicit euphemism/truncation triggers may post a
    // corrective prompt when the host exposes session.prompt; the positive
    // silent-stop leg stays debt-only because v2 has no user-role whitelist.
    onStopPrompt:
      ctx.session && typeof ctx.session.prompt === "function"
        ? async (sessionID, text) => {
            try {
              await ctx.session.prompt({ sessionID, text })
              return true
            } catch {
              return false
            }
          }
        : undefined,
    capabilities: { telemetry: false, promptable: !!(ctx.session && typeof ctx.session.prompt === "function") },
  })
  const registrations = []

  // Tool observation + RED-latch write gate via the execute.before hook
  // (fires for every tool; the gate only acts on write/edit).
  registrations.push(
    await ctx.tool.hook("execute.before", async (event) => {
      if (!event) return
      // pass input through AS-IS: observeToolStart treats a missing input as
      // unknown args (never fabricate the `{}` identity — acceptance #4)
      const rawInput = event.input && typeof event.input === "object" ? event.input : null
      if (event.tool === "write" || event.tool === "edit") {
        const args = rawInput || {}
        const msg = m.beforeWrite({
          tool: event.tool,
          sessionID: event.sessionID,
          filePath: writePathFromArgs(args),
        })
        if (msg) throw new Error(msg)
      }
      m.observeToolStart(event.sessionID, event.tool, rawInput, typeof event.messageID === "string" ? event.messageID : "", typeof event.id === "string" ? event.id : undefined)
    })
  )
  // Bash output capture (v1 got it from tool-part state.output).
  registrations.push(
    await ctx.tool.hook("execute.after", async (event) => {
      if (!event || event.status !== "completed") return
      m.observeToolEnd(event.sessionID, event.tool, event.result, typeof event.id === "string" ? event.id : undefined)
    })
  )

  const controller = new AbortController()
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        try {
          if (!event || typeof event.type !== "string") continue
          const data = event.data && typeof event.data === "object" ? event.data : {}
          const sessionID = typeof data.sessionID === "string" ? data.sessionID : null
          if (event.type === "session.text.delta" && sessionID) {
            m.observeTextDelta(sessionID, data.assistantMessageID, data.delta)
          } else if (event.type === "session.reasoning.delta" && sessionID) {
            // defensive: hosts that stream reasoning deltas (content stays
            // empty in the #97630 shape) route through the reasoning channel
            m.observeTextDelta(sessionID, data.assistantMessageID, data.delta, "reasoning")
          } else if (event.type === "session.message.content.updated" && sessionID) {
            m.observeFullContent(sessionID, data.messageID, data.content)
          } else if (event.type === "session.skill.activated" && sessionID) {
            m.observeSkill(sessionID, data.name)
          } else if (event.type === "session.error" && sessionID) {
            m.observeError(sessionID)
          } else if (event.type === "session.status" && sessionID && data.status && data.status.type === "idle") {
            await m.handleIdle(sessionID)
          }
        } catch {
          /* one bad event must not kill observation — fail-safe is the audit's whole point */
        }
      }
    } catch {
      /* stream closed/aborted — observation is advisory, never crash */
    }
  })()
  return () => {
    controller.abort()
    for (const r of registrations) {
      try {
        if (r && typeof r.dispose === "function") void r.dispose()
      } catch {
        /* disposal best-effort; the v2 host also scopes registrations to the plugin */
      }
    }
  }
}

export default {
  id: "vibeweaver-audit",
  server,
  setup,
}
