// vibeweaver-audit core — pure, headless-testable triage logic.
// Imported by vibeweaver-audit.js (plugin) and scripts/audit_selftest.mjs.
// Deliberately NOT a plugin module and NOT installed into the plugins dir:
// opencode's legacy plugin loader iterates EVERY export and throws
// "Plugin export is not a function" on non-factory exports — so the core
// must live outside the scanned directory.

import { execFileSync } from "node:child_process"
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs"
import path from "node:path"
import crypto from "node:crypto"

export const DEFAULTS = {
  samplingRate: 10,
  escOnUncertain: true,
  escOnHighRisk: true,
  maxPacket: 800,
  forbiddenRaw: [
    /(^|[;&|]\s*)npm run (build|dev|start|preview)\b/,
    /(^|[;&|]\s*)vite\b/,
    /(^|[;&|]\s*)npm start\b/,
    /(^|[;&|]\s*)uvicorn\b/,
    /\bpkill -f\b/,
  ],
}

// ---------------- helpers (never throw) ----------------

function sizeOf(p) {
  try {
    return statSync(p).size
  } catch {
    return 0
  }
}

function mtimeOf(p) {
  try {
    return statSync(p).mtimeMs
  } catch {
    return null
  }
}

function safeRead(p) {
  try {
    return statSync(p).size > 0 ? readFileSync(p, "utf8") : ""
  } catch {
    return ""
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

function walkDir(root, rel, pred) {
  const out = []
  let names = []
  try {
    names = readdirSync(path.join(root, rel))
  } catch {
    return out
  }
  for (const f of names) {
    const p = path.join(root, rel, f)
    if (sizeOf(p) > 0 && pred(f)) out.push(path.join(rel, f))
  }
  return out
}

// A file counts as "code" for ordering checks when it is not evidence/docs
// (tests/, memory/, .vibeweaver/, *.md/*.html/*.txt/*.log/*.json) — commits or
// writes that only document/record a verification run are legitimate and must
// NOT trip the fresh-run / ordering checks.
const BENIGN_RE = /(^|[\/])(tests|memory|\.vibeweaver)([\/]|$)|\.(md|html|txt|log|json|png|webm|wav|mp4|mp3|pyc|docx|doc|xlsx|xls|pptx|ppt|pdf|odt|ods|odp|rtf|odg|epub|mht|docm|xlsm|pptm)$/i

function isCodeFile(p) {
  if (typeof p !== "string") return false
  return !BENIGN_RE.test(p)
}

function gitCodeChangedAfter(root, sinceMs) {
  try {
    // Parse per-commit timestamps: a file counts as "changed after the run"
    // only when its commit time is STRICTLY after the log write. Commits in
    // the same second as the log write (e.g. the baseline commit) are not
    // violations even though --since includes them.
    const out = execFileSync("git", ["log", "--since=" + Math.floor(sinceMs / 1000), "--format=COMMIT %ct", "--name-only", "HEAD"], {
      cwd: root,
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "pipe", "pipe"],
    })
    let curTime = null
    const late = []
    for (const raw of out.split("\n")) {
      const line = raw.trim()
      const m = line.match(/^COMMIT (\d+)$/)
      if (m) {
        curTime = parseInt(m[1], 10) * 1000
        continue
      }
      if (line && curTime !== null && curTime > sinceMs && isCodeFile(line)) late.push(line)
    }
    return { changed: late.length > 0, files: late }
  } catch {
    return null
  }
}

const FLAG_COMBOS = [[], ["--existing"], ["--backend-only"], ["--existing", "--backend-only"]]

function runAssert(root) {
  const attempts = []
  for (const flags of FLAG_COMBOS) {
    try {
      const out = execFileSync("python3", [path.join(root, "tests", "assert_artifacts.py"), ...flags], {
        cwd: root,
        encoding: "utf8",
        timeout: 15000,
        stdio: ["ignore", "pipe", "pipe"],
      })
      return { ok: true, flags, output: out.trim() }
    } catch (err) {
      attempts.push({ flags: flags.join(" ") || "(none)", output: `${err.stdout || ""}${err.stderr || ""}`.trim().slice(0, 300) })
    }
  }
  return { ok: false, attempts }
}

export function isForbiddenCommand(cmd, forbiddenRaw = DEFAULTS.forbiddenRaw) {
  if (typeof cmd !== "string") return false
  return forbiddenRaw.some((re) => re.test(cmd))
}

// Stable short hash for a raw command string — used by C8 dedup so the same
// forbidden command is flagged only ONCE per project root (a latch must be
// self-clearable; re-flagging immutable history on every audit would pin the
// session forever). sha1 slice: collision risk negligible at the 100-entry cap.
export function hashCommand(cmd) {
  return crypto.createHash("sha1").update(cmd).digest("hex").slice(0, 12)
}

export function hashSession(sessionID, salt) {
  const h = crypto.createHash("sha256").update(`${salt}::${sessionID}`).digest()
  return h.readUInt32BE(0) % 100
}

// ---------------- loop-guard no-op bash detection ----------------
// Intent-narration loop (2026-09-28 incident): the model announces a tool
// call ("use Read now", "final", "grading") and then emits bare `echo` bash
// calls INSTEAD of the tool call. Every echo exits 0 and the strings vary,
// so byte-repeat and failure detectors stay silent — the loop lives in the
// TOOL channel, not the text stream. Contract: >= NOOP_RUN_MIN trailing
// no-op bash calls (literal echo/printf/true/: with no side effects, one
// distinct call each) -> { kind: "noop-bash", pattern }. Detection is
// content-level (no-op vs real), never byte-level, so varied narration
// strings cannot evade it. Conservative by construction: anything with a
// metacharacter, expansion, escape, or a second command is "real" and
// resets the run — a missed no-op is acceptable, a false positive is not.
const NOOP_RUN_MIN = 4

// Shell tokens that give a command side effects or structure. Newlines are
// command separators (chaining) and are rejected wholesale before tokenize.
// `#` is NOT here: a comment at word boundary is handled in the tokenizer.
const BASH_META = /[;&|<>()$`{}[\]*?~!\n\r]/

// Split one bash command into literal words (quotes removed), or null if the
// command has any structure (metacharacter / expansion / unclosed quote).
// A null means "real command". Backslashes are literal output formatting
// (escape sequences in echo/printf args are stdout work, not side effects);
// `$`/backtick (expansion) stay forbidden even inside double quotes. A `#`
// at word boundary starts a comment (rest of line dropped, like the shell).
function tokenizeBashLiteral(cmd) {
  const tokens = []
  let i = 0
  let cur = ""
  let saw = false
  const push = () => {
    if (saw) {
      tokens.push(cur)
      cur = ""
      saw = false
    }
  }
  while (i < cmd.length) {
    const ch = cmd[i]
    if (ch === "\\" && i + 1 < cmd.length) {
      cur += cmd[i + 1]
      saw = true
      i += 2
      continue
    }
    if (ch === "'") {
      const j = cmd.indexOf("'", i + 1)
      if (j < 0) return null
      cur += cmd.slice(i + 1, j)
      saw = true
      i = j + 1
      continue
    }
    if (ch === '"') {
      const j = cmd.indexOf('"', i + 1)
      if (j < 0) return null
      const inner = cmd.slice(i + 1, j)
      if (/[`$]/.test(inner)) return null // expansion inside double quotes
      cur += inner
      saw = true
      i = j + 1
      continue
    }
    if (ch === "#" && !saw) break // comment at word boundary — drop the rest
    if (/\s/.test(ch)) {
      push()
      i++
      continue
    }
    if (BASH_META.test(ch)) return null
    cur += ch
    saw = true
    i++
  }
  push()
  return tokens
}

// True for a bash command that is a pure narration/no-op marker: bare
// `true`/`:`, or literal `echo`/`printf` (every argument a quoted string or
// plain word). Everything else is a real command. Conservative by
// construction: structural doubt resolves to "real" (a missed no-op is
// acceptable, a false positive is not).
export function isNoopBashCommand(cmd) {
  if (typeof cmd !== "string") return false
  let c = cmd.trim()
  if (!c) return false
  if (/[\r\n]/.test(c)) return false // newline-chained second command
  c = c.replace(/;\s*$/, "") // trailing lone `;` (`echo final;`) is not structure
  if (c === "true" || c === ":") return true
  const tokens = tokenizeBashLiteral(c)
  if (!tokens || !tokens.length) return false
  const head = tokens[0].split("/").pop() // /bin/echo == echo
  return head === "echo" || head === "printf"
}

// Trailing run of distinct no-op bash calls in a tool-observation list
// (`[{tool, command, pid?, truncated?}]`). Streaming re-observations of the
// SAME tool part (same pid) count once — host state transitions must not
// inflate the run. Entries with an UNKNOWN command (status-only
// re-observation, missing input) are skipped without consuming the pid, so
// they can never mask the real observation of the same call. A truncated
// recorded command breaks the run (truncation can forge a literal).
// Returns { kind: "noop-bash", pattern } | null.
export function noopBashFinding(tools, minRun = NOOP_RUN_MIN) {
  if (!Array.isArray(tools) || tools.length < 1) return null
  const seenPid = new Set()
  let run = 0
  let sample = ""
  for (let i = tools.length - 1; i >= 0; i--) {
    const t = tools[i]
    if (!t || typeof t !== "object") break
    if (t.pid != null && seenPid.has(t.pid)) continue // duplicate observation of one call
    if (t.tool !== "bash") break
    const cmd = typeof t.command === "string" ? t.command : ""
    if (!cmd.trim()) continue // unknown command (status-only re-obs) — skip
    if (t.pid != null) seenPid.add(t.pid)
    if (t.truncated || !isNoopBashCommand(cmd)) break
    run++
    if (!sample) sample = cmd.trim().slice(0, 40)
    if (run >= minRun) return { kind: "noop-bash", pattern: `${run} consecutive no-op bash calls (e.g. ${sample})` }
  }
  return null
}

// ---------------- triage core ----------------

function check(checks, id, name, v, evidence) {
  checks.push({ id, name, verdict: v, evidence })
}

function highRisk(tools) {
  const files = new Set()
  let designDocs = false
  for (const t of tools) {
    if ((t.tool === "write" || t.tool === "edit") && t.filePath) {
      files.add(t.filePath)
      if (/(FLOW_DESIGN|PAGE_DESIGN|DATABASE_DESIGN|BACKEND_DESIGN)\.html$/i.test(t.filePath)) designDocs = true
    }
  }
  return files.size >= 3 || designDocs
}

export function auditProject(opts) {
  const {
    root,
    sessionID = "unknown",
    sessionText = "",
    tools = [],
    skillLoaded = false,
    phase = "final", // "mid" (warn-only subset) | "final" (full triage)
    config = {},
    priorFlagged = [], // C8 dedup: hashCommand()s already flagged for this root
  } = opts

  if (!skillLoaded) {
    // C17: the skill was NOT loaded, but code was written into a
    // vibeweaver-active project. Could be a legitimate user override or a
    // protocol bypass — mechanically unresolvable, so UNCERTAIN + escalate
    // (never blocks; the fresh-brain reviewer adjudicates).
    const wroteCode = tools.some((t) => (t.tool === "write" || t.tool === "edit") && isCodeFile(t.filePath))
    if (phase === "final" && wroteCode) {
      return {
        checks: [{
          id: "C17",
          name: "vibeweaver-active project modified without loading the skill",
          verdict: "UNCERTAIN",
          evidence: "code written but no `skill` tool call with a vibeweaver* name observed — user override or protocol bypass; reviewer adjudicates",
        }],
        bad: 0,
        uncertain: 1,
        escalate: true,
        escalateReasons: ["SKILL-ABSENT"],
        red: false,
        skipped: false,
        gateLine: null,
      }
    }
    return { checks: [], bad: 0, uncertain: 0, escalate: false, escalateReasons: [], red: false, skipped: true, gateLine: null }
  }

  const cfg = { ...DEFAULTS, ...config }
  const checks = []
  const escalateReasons = new Set()
  const testsDir = path.join(root, "tests")
  const log = safeRead(path.join(testsDir, "verification_log.md"))
  const acc = safeRead(path.join(testsDir, "acceptance.md"))
  const text = sessionText || ""
  const iterCount = (log.match(/^- iter \d+ (PASS|FAIL):/gm) || []).length

  // Group A — on-disk artifacts (both phases)
  if (iterCount >= 1) check(checks, "A1", "verification_log has ≥1 iter entry", "OK", `${iterCount} entries`)
  else if (sizeOf(path.join(testsDir, "verification_log.md")) > 0)
    check(checks, "A1", "verification_log has ≥1 iter entry", "BAD", "file exists but 0 `- iter N PASS|FAIL:` lines")
  else check(checks, "A1", "verification_log has ≥1 iter entry", "BAD", "file missing/empty")

  if (/^>\s*cap=5\s+stall=3/m.test(acc)) check(checks, "A2", "acceptance.md first line `> cap=5  stall=3×`", "OK", "matches")
  else if (sizeOf(path.join(testsDir, "acceptance.md")) > 0)
    check(checks, "A2", "acceptance.md first line `> cap=5  stall=3×`", "BAD", "file exists, first line does not match")
  else check(checks, "A2", "acceptance.md first line `> cap=5  stall=3×`", "BAD", "file missing")

  const cited = []
  for (const m of (log + "\n" + acc).matchAll(/tests\/(\S+\.(?:png|webm|wav|mp4|mp3))/g)) cited.push(m[1])
  const missing = cited.filter((f) => sizeOf(path.join(testsDir, f)) <= 0)
  if (!missing.length) check(checks, "A3", "cited media/screenshots exist and >0 bytes", "OK", `${cited.length} cited`)
  else check(checks, "A3", "cited media/screenshots exist and >0 bytes", "BAD", `missing/empty: ${missing.join(", ")}`)

  // Group C8 — script-only lifecycle (both phases; the only live check).
  // Dedup by command hash: a forbidden command flags only the FIRST time it
  // is seen for this root. The latch is thereby self-clearable — re-auditing
  // immutable history cannot pin a session forever, while every NEW distinct
  // forbidden command still flags (and is persisted by the caller).
  const hasScripts = existsSync(path.join(root, "script"))
  const rawCmds = tools.filter((t) => t.tool === "bash").map((t) => t.command || "")
  const forbidden = rawCmds.filter((c) => isForbiddenCommand(c, cfg.forbiddenRaw))
  const priorSet = new Set(priorFlagged)
  const freshForbidden = forbidden.filter((c) => !priorSet.has(hashCommand(c)))
  if (freshForbidden.length > 0)
    check(checks, "C8", "script-only lifecycle ↔ bash commands", "BAD", `forbidden raw commands: ${freshForbidden.map((c) => c.slice(0, 80)).join(" | ")}`)
  else if (forbidden.length > 0)
    check(checks, "C8", "script-only lifecycle ↔ bash commands", "OK", `${forbidden.length} forbidden raw command(s) already flagged and recorded — not re-flagged`)
  else check(checks, "C8", "script-only lifecycle ↔ bash commands", "OK", hasScripts ? "no forbidden raw command observed" : "no script/ dir — raw commands legitimate")
  const newlyFlagged = [...new Set(freshForbidden.map(hashCommand))]

  if (phase === "mid") {
    const bad = checks.filter((c) => c.verdict === "BAD").length
    return { checks, bad, uncertain: 0, escalate: bad > 0, escalateReasons: bad ? ["BAD"] : [], red: bad > 0, skipped: false, gateLine: null, newlyFlagged }
  }

  // Group B — narration markers in final text
  // COV-13 task class: STRUCTURAL, read from the gate line's own `|`-separated
  // field only. The value must be exactly DOC/CONFIG/CODE and the NEXT field
  // must not be another class name (that shape is the unfilled template
  // `Class: DOC|CONFIG|CODE`, which splits across fields). Prose mentions
  // inside other fields (`Loop executed: no (Class: DOC — …)`) never license.
  const gateMatch = text.match(/\[Verification Gate\][^\n]*/)
  const gateLine = gateMatch ? gateMatch[0].trim() : ""
  const gateFields = gateLine.split("|").map((s) => s.trim())
  const clsIdx = gateFields.findIndex((s) => /^Class:/i.test(s))
  let classField = ""
  if (clsIdx >= 0) {
    const fm = gateFields[clsIdx].match(/^Class:[ \t]*(DOC|CONFIG|CODE)$/i)
    const nxt = (gateFields[clsIdx + 1] || "").trim()
    if (fm && !/^(CONFIG|CODE|DOC)$/i.test(nxt)) classField = fm[1].toUpperCase()
  }
  const liteClass = classField === "DOC" || classField === "CONFIG"
  // Class basis line: scoped to the CURRENT (last `##`) task block — an older
  // block's `- class:` is history and must not license the current task.
  const logBlocks = log.split(/^(?=## )/m)
  const curLogBlock = logBlocks.length ? logBlocks[logBlocks.length - 1] : log
  const logClassM = [...curLogBlock.matchAll(/^-[ \t]*class:[ \t]*(DOC|CONFIG|CODE)[ \t]*[—-][ \t]*(\S[^\n]*)/gim)]
  const logClass = logClassM.length ? logClassM[logClassM.length - 1][1].toUpperCase() : ""
  const SKIP_REASONS = /documentation-only|doc-only|config-only|no runtime|no build|no UI|no service|na reason|no lesson|nothing persistable|informational only|纯文档|纯配置/i
  // A reason must be STATED on a real line — checklist echoes (`- [ ] …`) and
  // table rows (`| … |`) are template text, never a claim's own reason.
  const reasonLineStated = (log + "\n" + text).split("\n").some((l) => {
    const s = l.trim()
    if (!s || s.startsWith("- [") || s.startsWith("|")) return false
    return SKIP_REASONS.test(s)
  })
  const m = (re) => re.test(text)
  if (m(/\[Verification Gate\]/)) check(checks, "B1", "`[Verification Gate]` line present", "OK", "found")
  else check(checks, "B1", "`[Verification Gate]` line present", "BAD", "missing from assistant text")
  if (m(/HARD-GATE-1:\s*NO-TEST-NO-DONE/)) check(checks, "B2", "`HARD-GATE-1: NO-TEST-NO-DONE` present", "OK", "found")
  else check(checks, "B2", "`HARD-GATE-1: NO-TEST-NO-DONE` present", "BAD", "missing")
  if (m(/HARD-GATE-2:\s*SCRIPT-ONLY/)) check(checks, "B3", "`HARD-GATE-2: SCRIPT-ONLY` present", "OK", "found")
  else check(checks, "B3", "`HARD-GATE-2: SCRIPT-ONLY` present", "BAD", "missing")
  if (m(/\[Covenant Recall\]/)) check(checks, "B4", "`[Covenant Recall]` line present", "OK", "found")
  else check(checks, "B4", "`[Covenant Recall]` line present", "BAD", "missing")
  if (m(/\[Memory Gate\]/)) check(checks, "B5", "`[Memory Gate]` line present", "OK", "found")
  else check(checks, "B5", "`[Memory Gate]` line present", "BAD", "missing")
  if (m(/\[Convergence\]/)) check(checks, "B6", "`[Convergence]` line present", "OK", "found")
  else check(checks, "B6", "`[Convergence]` line present", "BAD", "missing")
  const liteHdr = /^\s*\|\s*#\s*\|\s*Problem\s*\|\s*What Changed & Evidence\s*\|\s*$/im
  if (liteClass) {
    // lite table licensed by the class; the full 8-column table is legitimate
    // over-delivery for a DOC/CONFIG task and stays accepted.
    if (liteHdr.test(text) || m(/\| # \| Problem \| Research Sources/)) check(checks, "B7", "completion table (lite licensed)", "OK", `Class: ${classField}`)
    else check(checks, "B7", "completion table (lite licensed)", "BAD", `neither the §V11.6 lite header nor the 8-column header found (Class: ${classField})`)
  } else if (m(/\| # \| Problem \| Research Sources/)) check(checks, "B7", "8-column completion table header", "OK", "found")
  else if (liteHdr.test(text)) check(checks, "B7", "8-column completion table header", "BAD", "lite table used without a filled `Class: DOC|CONFIG` field (§V11.6)")
  else check(checks, "B7", "8-column completion table header", "BAD", "missing from assistant text")
  if (m(/assert_artifacts\.py:\s*pass=\d+\/fail=0/)) check(checks, "B8", "`assert_artifacts.py: pass=N/fail=0` field", "OK", "found")
  else check(checks, "B8", "`assert_artifacts.py: pass=N/fail=0` field", "BAD", "missing")
  if (m(/covenant_recall:\s*pass/)) check(checks, "B9", "`covenant_recall: pass` field", "OK", "found")
  else check(checks, "B9", "`covenant_recall: pass` field", "BAD", "missing")
  if (m(/memory_gate:\s*pass/)) check(checks, "B10", "`memory_gate: pass` field", "OK", "found")
  else if (m(/memory_gate:\s*na/) && (liteClass || reasonLineStated)) check(checks, "B10", "`memory_gate` field", "OK", liteClass ? `na (Class: ${classField})` : "na (stated reason line)")
  else check(checks, "B10", "`memory_gate: pass` field", "BAD", "missing (na is licensed only by Class: DOC/CONFIG or a stated reason line — a checklist echo is not a reason)")
  if (classField && logClass && classField !== logClass) check(checks, "B11", "`Class` field", "BAD", `class mismatch: gate line ${classField} vs log ${logClass} — one class per task (COV-13)`)
  else if (classField) check(checks, "B11", "`Class: DOC|CONFIG|CODE` field", "OK", classField)
  else check(checks, "B11", "`Class: DOC|CONFIG|CODE` field", "BAD", "missing or template left unfilled (COV-13)")

  // Group C — claim ↔ artifact cross-checks (triage)
  // gateLine extracted above (Group B) — shared with the Class field.
  const field = (re) => {
    const mm = gateLine.match(re)
    return mm ? mm[1] : null
  }

  const loop = field(/Loop executed:\s*(yes|no|N\/A)/i)
  const itersClaimed = field(/Iterations:\s*(\d+)/i)
  const e2e = field(/E2E depth:\s*(real-HTTP|workflow-trace|service-direct|unit-only)/i)
  const tdd = field(/TDD RED evidence:\s*(yes|no|N\/A)/i)
  const fresh = field(/Fresh-run on final tree:\s*(yes|no|N\/A)/i)
  const review = field(/Code review:\s*(\S+)/i)
  const hard1 = field(/HARD-GATE-1:\s*NO-TEST-NO-DONE=(\w+)/i)
  const hard2 = field(/HARD-GATE-2:\s*SCRIPT-ONLY=(\w+)/i)

  if (loop === "yes" && iterCount >= 1) check(checks, "C1", "`Loop executed: yes` ↔ iter entries", "OK", `${iterCount} entries`)
  else if (loop === "yes") check(checks, "C1", "`Loop executed: yes` ↔ iter entries", "BAD", `claimed yes but log has ${iterCount} entries`)
  else if (loop === "no" || loop === "N/A") check(checks, "C1", "`Loop executed: yes` ↔ iter entries", "OK", `claimed ${loop}`)
  else check(checks, "C1", "`Loop executed: yes` ↔ iter entries", "UNCERTAIN", "claim absent")

  if (itersClaimed === null) check(checks, "C2", "`Iterations: N` ↔ log line count", "UNCERTAIN", "claim absent")
  else if (parseInt(itersClaimed, 10) <= iterCount) check(checks, "C2", "`Iterations: N` ↔ log line count", "OK", `claimed ${itersClaimed}, log has ${iterCount}`)
  else check(checks, "C2", "`Iterations: N` ↔ log line count", "BAD", `claimed ${itersClaimed} but log has ${iterCount}`)

  const mediaM = gateLine.match(/Media graded externally:\s*(\d+)\/(\d+)/i)
  if (mediaM) {
    const graded = parseInt(mediaM[2], 10) || 0
    const mediaFiles = walkDir(testsDir, "", (f) => /\.(png|webm|wav|mp4|mp3)$/.test(f)).length
    if (graded === 0) check(checks, "C3", "`Media graded externally: N` ↔ media files", "OK", "claimed 0")
    else if (mediaFiles >= graded) check(checks, "C3", "`Media graded externally: N` ↔ media files", "OK", `${mediaFiles} media files on disk >= ${graded}`)
    else check(checks, "C3", "`Media graded externally: N` ↔ media files", "BAD", `claimed ${graded} graded but only ${mediaFiles} media files on disk`)
  } else check(checks, "C3", "`Media graded externally: N` ↔ media files", "UNCERTAIN", "claim absent")

  const traces = walkDir(testsDir, "workflows", (f) => f.endsWith(".trace.log"))
  if (e2e === "real-HTTP" || e2e === "workflow-trace") {
    if (traces.length > 0) check(checks, "C4", "`E2E depth` ↔ workflow traces", "OK", `${traces.length} trace.log on disk`)
    else check(checks, "C4", "`E2E depth` ↔ workflow traces", "BAD", `claimed ${e2e} but no tests/workflows/*.trace.log`)
  } else if (e2e) check(checks, "C4", "`E2E depth` ↔ workflow traces", "OK", `claimed ${e2e}, no trace required`)
  else check(checks, "C4", "`E2E depth` ↔ workflow traces", "UNCERTAIN", "claim absent")

  if (tdd === "yes" && /- iter \d+ FAIL:/.test(log)) check(checks, "C5", "`TDD RED evidence: yes` ↔ FAIL line", "OK", "FAIL line found")
  else if (tdd === "yes") check(checks, "C5", "`TDD RED evidence: yes` ↔ FAIL line", "BAD", "claimed yes but no `- iter N FAIL:` line")
  else if (tdd === "no" || tdd === "N/A") check(checks, "C5", "`TDD RED evidence: yes` ↔ FAIL line", "OK", `claimed ${tdd}`)
  else check(checks, "C5", "`TDD RED evidence: yes` ↔ FAIL line", "UNCERTAIN", "claim absent")

  if (fresh === "yes") {
    const logMtime = mtimeOf(path.join(testsDir, "verification_log.md"))
    const codeAfter = logMtime !== null ? gitCodeChangedAfter(root, logMtime) : null
    if (logMtime === null) check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "UNCERTAIN", "log missing")
    else if (codeAfter === null) check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "UNCERTAIN", "git unavailable")
    else if (!codeAfter.changed) check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "OK", "no code file changed after last log write")
    else check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "BAD", `code changed after last verification_log write: ${codeAfter.files.slice(0, 3).join(", ")}`)
  } else if (fresh === "no" || fresh === "N/A") check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "OK", `claimed ${fresh}`)
  else check(checks, "C6", "`Fresh-run: yes` ↔ no commit after last test run", "UNCERTAIN", "claim absent")

  if (review === "N/A") {
    if (/A4\.9 not triggered/i.test(text)) check(checks, "C7", "`Code review: N/A` ↔ backing reason", "OK", "`A4.9 not triggered` found")
    else check(checks, "C7", "`Code review: N/A` ↔ backing reason", "BAD", "N/A claimed without `A4.9 not triggered` reason")
  } else if (review) {
    if (tools.some((t) => t.tool === "task")) check(checks, "C7", "`Code review` ↔ reviewer dispatch", "OK", "`task` tool call observed")
    else check(checks, "C7", "`Code review` ↔ reviewer dispatch", "UNCERTAIN", `${review} claimed but no task dispatch in tool log`)
  } else check(checks, "C7", "`Code review` ↔ reviewer dispatch", "UNCERTAIN", "claim absent")

  const readFiles = tools.filter((t) => t.tool === "read").map((t) => t.filePath || "")
  // basename match — works regardless of where the skill is installed
  const r1 = readFiles.some((p) => /[\\/]TESTING_PROTOCOLS\.md$/i.test(p))
  const r1b = readFiles.some((p) => /[\\/]COMPLETION_GATE\.md$/i.test(p))
  const rRef = readFiles.some((p) => /[\\/]REFERENCE\.md$/i.test(p))
  check(checks, "C9", "R1 read (TESTING_PROTOCOLS.md)", r1 ? "OK" : "UNCERTAIN", r1 ? "read observed" : "no read of TESTING_PROTOCOLS.md in tool log")
  check(checks, "C10", "R1b read (COMPLETION_GATE.md)", r1b ? "OK" : "UNCERTAIN", r1b ? "read observed" : "no read of COMPLETION_GATE.md in tool log")
  check(checks, "C11", "R2-R5 read (REFERENCE.md)", rRef ? "OK" : "UNCERTAIN", rRef ? "read observed" : "no read observed (branch may not need it)")

  if (loop === "yes") {
    if (/Verifier:\s*mm-sensor|Verifier:\s*model-native|Verifier:\s*direct read/.test(text)) check(checks, "C12", "verifier announced (COV-5)", "OK", "announcement found")
    else check(checks, "C12", "verifier announced (COV-5)", "BAD", "loop executed but no verifier announcement")
  } else check(checks, "C12", "verifier announced (COV-5)", "UNCERTAIN", "loop claim absent")

  // COV-9: state-skip is a Class DOC license. CONFIG runs the baseline
  // (§V11.3) — its skip must name a mid-task escalation, not "documentation-only".
  const baselineLine = /- Baseline verified GREEN/.test(log)
  const escalationSkip = /COV-9 skipped[^\n]*escalat/i.test(log)
  const docSkip = /COV-9 skipped/.test(log) && (classField === "DOC" || classField === "")
  const baseline = baselineLine || escalationSkip || docSkip
  const didWrite = tools.some((t) => t.tool === "write" || t.tool === "edit")
  if (baseline) check(checks, "C13", "COV-9 baseline recorded in log", "OK", "baseline line found")
  else if (didWrite) check(checks, "C13", "COV-9 baseline recorded in log", "BAD", "files edited but no baseline/skip line in log")
  else check(checks, "C13", "COV-9 baseline recorded in log", "UNCERTAIN", "no writes observed")

  // ordering: a code write AFTER the last log write means the log may be stale
  const codeWrites = tools
    .filter((t) => (t.tool === "write" || t.tool === "edit") && isCodeFile(t.filePath) && typeof t.t === "number")
    .map((t) => t.t)
  const lastCodeWrite = codeWrites.length ? Math.max(...codeWrites) : null
  const logMtimeMs = mtimeOf(path.join(testsDir, "verification_log.md"))
  if (lastCodeWrite === null) {
    // Class DOC writes prose only — "no code writes" is definitional, not a gap.
    if (classField === "DOC") check(checks, "C16", "code write precedes last log write", "OK", "Class DOC — no code writes expected")
    else check(checks, "C16", "code write precedes last log write", "UNCERTAIN", "no timestamped code writes in tool log")
  } else if (logMtimeMs !== null && lastCodeWrite <= logMtimeMs + 1_000) check(checks, "C16", "code write precedes last log write", "OK", "last code write before log")
  else if (logMtimeMs !== null) check(checks, "C16", "code write precedes last log write", "BAD", `code written ${Math.round((lastCodeWrite - logMtimeMs) / 1000)}s after last log write`)
  else check(checks, "C16", "code write precedes last log write", "UNCERTAIN", "log missing")

  // COV-13 misreport guard: the class licenses the lite path only for its own
  // file kinds. Prose = docs/evidence artifacts only; any other write under a
  // DOC claim (including tests/** code files, .json/.sh, untimed writes) or a
  // logic-source write under a CONFIG claim = the class was wrong → escalate UP.
  const PROSE_NAME_RE = /(^|[\/])(LICENSE|COPYING|README|CHANGELOG|AUTHORS|NOTICE|CONTRIBUTORS)(\.[A-Za-z0-9]+)?$/
  const PROSE_EXT_RE = /\.(md|txt|rst|png|webm|wav|mp4|mp3|log)$/i
  const MEMDOC_DIR_RE = /(^|[\/])(memory|docs)([\/]|$)/i
  const LOGIC_SRC_RE = /\.(py|js|ts|tsx|jsx|go|rs|java|c|cc|cpp|h|hpp|rb|php|cs|kt|swift|m|scala|pl|lua|r|jl)$/i
  const DOC_TOOLING_RE = /(^|[\/\\])tests[\/\\]assert_artifacts\.py$/i
  // §V11.9 DOC-asset render gate: FILE-KIND triggered (every class — a mixed
  // CODE wave shipping a docx owes the same render as a DOC wave; assets are
  // never a class misreport, their gate IS the render). Evidence is bound to
  // THIS task block + this answer, per asset, and to files that EXIST on disk
  // — probe_vision.* is COV-5 tooling output, never a document page.
  const ASSET_RE = /\.(docx|doc|xlsx|xls|pptx|ppt|pdf|odt|ods|odp|rtf|odg|epub|mht|docm|xlsm|pptm)$/i
  const isProsePath = (p) => PROSE_NAME_RE.test(p) || PROSE_EXT_RE.test(p)
    || (MEMDOC_DIR_RE.test(p) && !LOGIC_SRC_RE.test(p) && !ASSET_RE.test(p))
  const evidText = curLogBlock + "\n" + text // current task block + this answer only
  const isProbeArtifact = (f) => /^probe_vision\./i.test(f.split(/[\/\\]/).pop() || "")
  const mediaOnDisk = (line) => [...line.matchAll(/\btests\/(\S+\.(?:png|webm))\b/g)]
    .map((mm) => mm[1]).filter((f) => !isProbeArtifact(f))
    .some((f) => sizeOf(path.join(testsDir, f)) > 0)
  const TOOLCHAIN_RE = /soffice|libreoffice|pymupdf|pdftoppm|poppler|imagemagick/i
  const naLineOk = (line) => /N\/A/i.test(line) && TOOLCHAIN_RE.test(line) && !/<[^>]*>/.test(line)
  const renderLines = evidText.split("\n").filter((l) => /^[\s>*+—–-]*\s*render:/i.test(l) && !/^\s*>/.test(l))
  const classWrites = tools.filter((t) => (t.tool === "write" || t.tool === "edit") && typeof t.filePath === "string")
  // Wave state: the canonical office pipeline (python-docx .save / soffice /
  // pandoc via bash) never appears as a write-tool row — read the disk.
  const waveFiles = (() => {
    try {
      // Whole change wave, not just the working tree: assets COMMITTED mid-wave
      // are still deliveries. --name-status (binary-safe); D = not a delivery.
      const collect = (args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8", timeout: 8000, stdio: ["ignore", "pipe", "pipe"] })
        .split("\n").map((s) => s.trim()).filter(Boolean)
        .filter((l) => !l.startsWith("D"))
        .map((l) => l.split("\t").pop())
      let base = ""
      try {
        base = execFileSync("git", ["-C", root, "log", "--format=%H", "-1", "--fixed-strings", "--grep=backup: before changes"], { encoding: "utf8", timeout: 8000, stdio: ["ignore", "pipe", "pipe"] }).trim()
      } catch { base = "" }
      // No `backup:` marker → the wave is the working tree only (pre-wave
      // history must never count as deliveries).
      return [...new Set([
        ...(base ? collect(["log", "--name-status", "--format=", `${base}..HEAD`]) : []),
        ...collect(["diff", "--name-status", "HEAD"]),
        ...collect(["diff", "--cached", "--name-status"]),
        ...collect(["ls-files", "--others", "--exclude-standard"]),
      ])]
    } catch { return [] }
  })()
  const assetSet = [...new Set([
    ...classWrites.map((t) => t.filePath).filter((p) => ASSET_RE.test(p)),
    ...waveFiles.filter((p) => ASSET_RE.test(p)),
  ])]
  const assetNameMatch = (p, line) => {
    const base = (p.split(/[\/\\]/).pop() || "").toLowerCase()
    const stem = base.replace(/\.[^.]+$/, "")
    return line.toLowerCase().includes(base) || (stem.length >= 4 && line.toLowerCase().includes(stem))
  }
  const uncoveredAssets = assetSet.filter((p) => !renderLines.some((l) => assetNameMatch(p, l) && (mediaOnDisk(l) || naLineOk(l))))
  const misreportPath = (p) => !isProsePath(p) && !DOC_TOOLING_RE.test(p) && !ASSET_RE.test(p)
  const docMis = classField === "DOC" && (
    classWrites.some((t) => misreportPath(t.filePath)) || waveFiles.some(misreportPath))
  const cfgMis = classField === "CONFIG" && (
    classWrites.some((t) => LOGIC_SRC_RE.test(t.filePath)) || waveFiles.some((p) => LOGIC_SRC_RE.test(p)))
  if (docMis || cfgMis) {
    const badPath = (classWrites.map((t) => t.filePath).find((p) => (docMis ? misreportPath(p) : LOGIC_SRC_RE.test(p)))
      || waveFiles.find((p) => (docMis ? misreportPath(p) : LOGIC_SRC_RE.test(p))) || "(path)")
    check(checks, "C18", `Class ${classField} matches the change set`, "BAD",
          `delivered ${badPath} under a \`Class: ${classField}\` claim — misreported class (COV-13: escalate, never de-escalate)`)
  } else if (uncoveredAssets.length > 0) {
    check(checks, "C18", "DOC-asset render gate (file-kind)", "BAD",
          `delivered ${uncoveredAssets[0]} without bound render evidence — NO RENDER, NO DONE (§V11.9; add \`render: <asset> — <existing page images>\` or \`render: <asset> — N/A (<missing tool>)\` to this task's log/answer)`)
  } else if (classField === "DOC" || classField === "CONFIG" || assetSet.length > 0) {
    check(checks, "C18", `Class ${classField || "—"} matches the change set`, "OK",
          assetSet.length > 0
            ? "change set within the class's file kinds + per-asset render evidence bound (§V11.9)"
            : "change set within the class's file kinds")
  }

  // na 豁免不是免检：state-skip 只对纯配置/纯文档合法，且必须明说。
  // 机器只查"有没有说"——"说得对不对"交给 Tier-2 审查。理由必须是真行
  // （reasonLineStated，Group B）——清单回声不构成理由。许可证按字段区分：
  // HARD-GATE-1=na 仅 Class DOC（CONFIG 跑 smoke，应 =pass）或陈述理由；
  // HARD-GATE-2=na 对 DOC/CONFIG（无服务生命周期）或陈述理由。
  const na1Ok = (v) => v === "pass" || (v === "na" && (classField === "DOC" || reasonLineStated))
  const na2Ok = (v) => v === "pass" || (v === "na" && (liteClass || reasonLineStated))
  const na1Unc = (v) => v === "na" && !(classField === "DOC" || reasonLineStated)
  const na2Unc = (v) => v === "na" && !(liteClass || reasonLineStated)
  if (na1Ok(hard1)) check(checks, "C14", "`HARD-GATE-1` value", "OK", hard1)
  else if (na1Unc(hard1)) check(checks, "C14", "`HARD-GATE-1` value", "UNCERTAIN", "na without a stated reason line (documentation-only/config-only/no lesson/...)")
  else check(checks, "C14", "`HARD-GATE-1` value", hard1 ? "BAD" : "UNCERTAIN", hard1 || "claim absent")
  if (na2Ok(hard2)) check(checks, "C15", "`HARD-GATE-2` value", "OK", hard2)
  else if (na2Unc(hard2)) check(checks, "C15", "`HARD-GATE-2` value", "UNCERTAIN", "na without a stated reason line (documentation-only/config-only/no lesson/...)")
  else check(checks, "C15", "`HARD-GATE-2` value", hard2 ? "BAD" : "UNCERTAIN", hard2 || "claim absent")

  const assertsPath = path.join(testsDir, "assert_artifacts.py")
  const assertRun = existsSync(assertsPath) ? runAssert(root) : null
  if (assertRun && assertRun.ok) check(checks, "A4", "assert_artifacts.py exit 0", "OK", `exit 0 (${assertRun.flags.join(" ")})`)
  else if (assertRun) check(checks, "A4", "assert_artifacts.py exit 0", "BAD", `failed all flag combos: ${assertRun.attempts.map((a) => a.output.slice(0, 120)).join(" || ")}`)
  else check(checks, "A4", "assert_artifacts.py exit 0", "UNCERTAIN", "tests/assert_artifacts.py missing — inline floor applies")

  // Tier-2 escalation triggers
  const bad = checks.filter((c) => c.verdict === "BAD").length
  const uncertain = checks.filter((c) => c.verdict === "UNCERTAIN").length
  if (bad > 0) escalateReasons.add("BAD")
  if (uncertain > 0 && cfg.escOnUncertain) escalateReasons.add("UNCERTAIN")
  if (cfg.escOnHighRisk && highRisk(tools)) escalateReasons.add("HIGH-RISK")
  if (hashSession(sessionID, root) < cfg.samplingRate) escalateReasons.add("SAMPLING")

  return {
    checks,
    bad,
    uncertain,
    escalate: escalateReasons.size > 0,
    escalateReasons: [...escalateReasons],
    red: bad > 0,
    skipped: false,
    gateLine,
    newlyFlagged,
  }
}

// ---------------- report ----------------

export function buildReport(audit, sessionID, packets = [], footerLines = []) {
  const lines = [
    `# Gate Audit — ${sessionID} | ${new Date().toISOString()}`,
    `AUDIT: BAD=${audit.bad} UNCERTAIN=${audit.uncertain} escalate=${audit.escalate}${audit.escalateReasons.length ? ` reasons=[${audit.escalateReasons.join(",")}]` : ""}${audit.red ? " BLOCKING=yes" : ""}`,
    "",
  ]
  if (audit.skipped) {
    lines.push("Session did not load the vibeweaver skill — not audited.")
    return lines.join("\n") + "\n"
  }
  for (const c of audit.checks) lines.push(`- [${c.verdict}] ${c.id} ${c.name} — ${c.evidence}`)
  if (packets.length) {
    lines.push("", "## Tier-2 review packets (fresh-brain reviewer inputs)", "")
    for (const p of packets) lines.push(`<packet id="${p.id}">`, p.body, "</packet>", "")
  }
  if (footerLines.length) {
    lines.push("", "## Stale RED releases (auto-cleared latches — audit trail, never delete)", "")
    for (const l of footerLines) lines.push(l)
  }
  return lines.join("\n") + "\n"
}

