// W24 — structured working-note / compaction state tests.
// Usage: node tests/context_state_test.mjs
import { execFileSync } from "node:child_process"
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"
import { pathToFileURL } from "node:url"

const TMP = path.join(os.tmpdir(), "vw-context-state-w24")
const HOME = path.join(TMP, "home")
rmSync(TMP, { recursive: true, force: true })
mkdirSync(HOME, { recursive: true })
process.env.VIBEWEAVER_HOME = HOME
const gateFile = [
  path.resolve(import.meta.dirname, "..", "vibeweaver-gate.js"),
  path.resolve(import.meta.dirname, "..", "vibeweaver", "vibeweaver-gate.js"),
].find((p) => existsSync(p))
const gate = (await import(pathToFileURL(gateFile))).default
let count = 0
let failures = 0
const rec = (name, ok, detail = "") => {
  count++
  if (!ok) failures++
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

function project(name) {
  const root = path.join(TMP, name)
  mkdirSync(path.join(root, "tests"), { recursive: true })
  mkdirSync(path.join(root, "src"), { recursive: true })
  writeFileSync(path.join(root, "tests", "acceptance.md"), "> cap=5  stall=3×\n1. state retention\n")
  writeFileSync(path.join(root, "tests", "verification_log.md"), "## Task: state\n- iter 1 PASS: baseline (evidence: fixture, 1/1)\n")
  return root
}
const hooksFor = (root) => gate.server({ client: { app: { log: async () => {} } }, directory: root })
const compact = async (hooks, sid) => {
  const out = { context: [] }
  await hooks["experimental.session.compacting"]({ sessionID: sid }, out)
  return out.context.join("\n")
}
const bytes = (s) => Buffer.byteLength(s, "utf8")

const stateBlock = (state) => "```vibeweaver-state\n" + JSON.stringify(state) + "\n```\n"

// S1 — structured oversize note keeps priority fields, not narrative.
{
  const state = {
    version: 1, task: "structured task", updated: "iter 2", current_criterion: "#2",
    next_action: "NEXT-STRUCTURED: implement renderer",
    assumption: "structured state is enough", falsifier: "next action disappears",
    confirmed: ["C-1", "C-2"], open: ["O-1", "O-2"], excluded: ["E-1"],
    key_files: ["vibeweaver-gate.js:1600"], blocked: [],
  }
  const root = project("structured")
  const body = "NARRATIVE ".repeat(1000)
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state) + body)
  const bundle = await compact(await hooksFor(root), "s-structured")
  rec("S1a structured note next_action retained", bundle.includes("NEXT-STRUCTURED: implement renderer"), bundle.slice(0, 120))
  rec("S1b structured note criterion retained", bundle.includes("criterion: #2"), bundle.slice(0, 120))
  rec("S1c structured arrays retained", bundle.includes("O-1") && bundle.includes("C-1") && bundle.includes("E-1"), bundle.slice(0, 160))
  rec("S1d structured delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S1e — oversize structured arrays are trimmed, never at the expense of
// next_action/criterion, and the omission is explicit.
{
  const state = {
    version: 1, task: "oversize arrays", current_criterion: "#2-priority",
    next_action: "OVERSIZE-NEXT-ACTION: keep me",
    confirmed: Array.from({ length: 40 }, (_, i) => `CONF-${i + 1}: ` + "c".repeat(180)),
    open: Array.from({ length: 40 }, (_, i) => `OPEN-${i + 1}: ` + "o".repeat(180)),
    excluded: Array.from({ length: 40 }, (_, i) => `EXCL-${i + 1}: ` + "e".repeat(180)),
    key_files: Array.from({ length: 20 }, (_, i) => `src/f${i}.js:1 — key`),
    blocked: [],
  }
  const root = project("oversize-arrays")
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state))
  const bundle = await compact(await hooksFor(root), "s-oversize-arrays")
  rec("S1e next_action survives oversize arrays", bundle.includes("OVERSIZE-NEXT-ACTION: keep me") && bundle.includes("criterion: #2-priority"), bundle.slice(0, 140))
  rec("S1f oversize arrays trim with an omission marker", /more open|more confirmed|more excluded|more key_files/.test(bundle), bundle.slice(-120))
  rec("S1g oversize array delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S2 — malformed structured block falls back but keeps explicit next action.
{
  const root = project("malformed")
  writeFileSync(path.join(root, "tests", "working_note.md"),
    "```vibeweaver-state\n{not valid json}\n```\n" + "A".repeat(5000) + "\n## Next action\nMALFORMED-NEXT-ACTION\n")
  const bundle = await compact(await hooksFor(root), "s-malformed")
  rec("S2a malformed schema warning is visible", bundle.includes("WORKING-STATE SCHEMA WARNING"), bundle.slice(0, 100))
  rec("S2b malformed note keeps explicit next action", bundle.includes("MALFORMED-NEXT-ACTION"), bundle.slice(-120))
  rec("S2c malformed delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S2d — a schema block missing required fields gets the same warning/fallback,
// not silent acceptance or a dropped note.
{
  const root = project("missing-required")
  writeFileSync(path.join(root, "tests", "working_note.md"),
    "```vibeweaver-state\n" + JSON.stringify({ version: 1, task: "only task" }) + "\n```\n" + "C".repeat(4500) + "\n## Next action\nMISSING-REQUIRED-FALLBACK\n")
  const bundle = await compact(await hooksFor(root), "s-missing-required")
  rec("S2d missing next_action warns and falls back", bundle.includes("WORKING-STATE SCHEMA WARNING") && bundle.includes("MISSING-REQUIRED-FALLBACK"), bundle.slice(0, 120))
  rec("S2e missing-required delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S2f — an unknown schema version is not silently interpreted as v1.
{
  const root = project("unknown-version")
  writeFileSync(path.join(root, "tests", "working_note.md"),
    "```vibeweaver-state\n" + JSON.stringify({ version: 2, task: "future", next_action: "FUTURE-FORMAT" }) + "\n```\n## Next action\nV2-FALLBACK-NEXT\n")
  const bundle = await compact(await hooksFor(root), "s-unknown-version")
  rec("S2f unknown version warns and falls back", bundle.includes("WORKING-STATE SCHEMA WARNING") && bundle.includes("V2-FALLBACK-NEXT") && !bundle.includes("task: future"), bundle.slice(0, 140))
}

// S3 — freeform 50-line note keeps tail next action.
{
  const root = project("freeform")
  const lines = Array.from({ length: 49 }, (_, i) => `LONG-${i + 1}: ` + "x".repeat(100))
  lines.push("## Next action", "FREEFORM-TAIL-NEXT-ACTION")
  writeFileSync(path.join(root, "tests", "working_note.md"), lines.join("\n"))
  const bundle = await compact(await hooksFor(root), "s-freeform")
  rec("S3a freeform long note keeps tail next action", bundle.includes("FREEFORM-TAIL-NEXT-ACTION"), bundle.slice(-150))
  rec("S3b freeform delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S4 — snapshot stores enough raw note and renders structured state after deletion.
{
  const root = project("snapshot")
  const state = {
    version: 1, task: "snapshot task", current_criterion: "#4",
    next_action: "SNAPSHOT-NEXT: continue after deletion",
    confirmed: ["SNAP-C"], open: ["SNAP-O"], excluded: [], key_files: [], blocked: [],
  }
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state) + "B".repeat(12000))
  const hooks = await hooksFor(root)
  await compact(hooks, "s-snapshot")
  rmSync(path.join(root, "tests", "working_note.md"), { force: true })
  const bundle = await compact(hooks, "s-snapshot")
  rec("S4a snapshot renders structured next action", bundle.includes("SNAPSHOT-NEXT: continue after deletion"), bundle.slice(0, 150))
  rec("S4b snapshot includes criterion/open state", bundle.includes("criterion: #4") && bundle.includes("SNAP-O"), bundle.slice(0, 180))
  rec("S4c snapshot delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S4d — a >4KB freeform note proves the snapshot keeps the raw tail beyond the
// delivery budget: after deleting the source, the tail next action survives.
{
  const root = project("snapshot-long")
  const lines = Array.from({ length: 20 }, (_, i) => `SNAP-LONG-${i + 1}: ` + "s".repeat(900))
  lines.push("## Next action", "SNAPSHOT-LONG-TAIL-NEXT")
  writeFileSync(path.join(root, "tests", "working_note.md"), lines.join("\n"))
  const hooks = await hooksFor(root)
  await compact(hooks, "s-snapshot-long")
  const snap = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "memory-snapshot.json"), "utf8"))
  rec("S4d snapshot stores >4096B raw note", Buffer.byteLength(snap.text, "utf8") > 4096, `${Buffer.byteLength(snap.text, "utf8")}B`)
  rmSync(path.join(root, "tests", "working_note.md"), { force: true })
  const bundle = await compact(hooks, "s-snapshot-long")
  rec("S4e deleted-source snapshot keeps tail next action", bundle.includes("SNAPSHOT-LONG-TAIL-NEXT"), bundle.slice(-150))
  rec("S4f long snapshot delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S5 — debt brief cannot crowd out next action, and is bounded.
{
  const root = project("debt")
  const state = { version: 1, task: "debt task", next_action: "DEBT-NEXT-ACTION", confirmed: [], open: [], excluded: [], key_files: [], blocked: [] }
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state))
  writeFileSync(path.join(root, "tests", "gate_result.json"), JSON.stringify({
    completion: Array.from({ length: 10 }, (_, i) => "debt-" + (i + 1)), blocking: [],
  }))
  const bundle = await compact(await hooksFor(root), "s-debt")
  rec("S5a debt next action survives debt brief", bundle.includes("DEBT-NEXT-ACTION"), bundle.slice(0, 150))
  rec("S5b debt brief is bounded to first 3 + count", bundle.includes("debt-1") && bundle.includes("debt-3") && !bundle.includes("debt-10") && bundle.includes("+7"), bundle.slice(-180))
  rec("S5c combined delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S5d — the motivating >4KB freeform note + realistic long debt: next_action
// must survive the end-clipping that debt budget introduces.
{
  const root = project("freeform-debt")
  const lines = Array.from({ length: 49 }, (_, i) => `DEBT-LONG-${i + 1}: ` + "d".repeat(100))
  lines.push("## Next action", "DEBT-CROSS-NEXT-ACTION")
  writeFileSync(path.join(root, "tests", "working_note.md"), lines.join("\n"))
  writeFileSync(path.join(root, "tests", "gate_result.json"), JSON.stringify({
    completion: Array.from({ length: 10 }, (_, i) => `completion-${i + 1}: ` + "c".repeat(140)), blocking: [],
  }))
  const bundle = await compact(await hooksFor(root), "s-freeform-debt")
  rec("S5d long freeform + long debt keeps next action", bundle.includes("DEBT-CROSS-NEXT-ACTION"), bundle.slice(-150))
  rec("S5e long debt keeps omission count", bundle.includes("+7"), bundle.slice(-180))
  rec("S5f freeform+debt delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
  rec("S5f2 long debt keeps the resume rule", bundle.includes("Resume rule: after compaction"), bundle.slice(-140))
}

// S5g — multi-line Next action sections and duplicate sections: the LAST
// non-empty section wins and its full body is retained.
{
  const root = project("multiline-action")
  const note = "## Next action\nSTALE-ACTION\n\n" + "M".repeat(4400) +
    "\n## Next action\nSTEP-ONE: run gate\nSTEP-TWO: DETAIL-LINE-1\nSTEP-THREE: DETAIL-LINE-2\n" + "T".repeat(300)
  writeFileSync(path.join(root, "tests", "working_note.md"), note)
  const bundle = await compact(await hooksFor(root), "s-multiline-action")
  rec("S5g latest multi-line next action wins", bundle.includes("STEP-ONE: run gate") && bundle.includes("DETAIL-LINE-1") && bundle.includes("DETAIL-LINE-2"), bundle.slice(0, 160))
  rec("S5h multi-line action delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S5i — 10 short open items must not be silently sliced at 8.
{
  const state = {
    version: 1, task: "ten open items", next_action: "TEN-OPEN-NEXT",
    open: Array.from({ length: 10 }, (_, i) => "SHORT-OPEN-" + (i + 1)),
    confirmed: [], excluded: [], key_files: [], blocked: [],
  }
  const root = project("ten-open")
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state))
  const bundle = await compact(await hooksFor(root), "s-ten-open")
  rec("S5i all 10 short open items rendered", bundle.includes("SHORT-OPEN-10") && !bundle.includes("more open"), bundle.slice(0, 200))
}

// S5j — 40-item arrays keep marker counts that match the ORIGINAL total.
{
  const state = {
    version: 1, task: "array counts", next_action: "ARRAY-COUNT-NEXT",
    open: Array.from({ length: 40 }, (_, i) => `O-${i + 1}: ` + "o".repeat(160)),
    confirmed: Array.from({ length: 40 }, (_, i) => `C-${i + 1}: ` + "c".repeat(160)),
    excluded: Array.from({ length: 40 }, (_, i) => `E-${i + 1}: ` + "e".repeat(160)),
    key_files: Array.from({ length: 40 }, (_, i) => `K-${i + 1}: src/file.js — why`),
    blocked: [],
  }
  const root = project("array-counts")
  writeFileSync(path.join(root, "tests", "working_note.md"), stateBlock(state))
  const bundle = await compact(await hooksFor(root), "s-array-counts")
  const countCheck = (label, prefix) => {
    const marker = bundle.match(new RegExp(`\\+(\\d+) more ${label}`))
    const shown = (bundle.match(new RegExp(`^- ${prefix}`, "gm")) || []).length
    return !!marker && shown + Number(marker[1]) === 40
  }
  rec("S5j open/confirmed/excluded/key_files markers count the original totals", countCheck("open", "O-") && countCheck("confirmed", "C-") && countCheck("excluded", "E-") && countCheck("key_files", "K-"), bundle.slice(-260))
  rec("S5k array-count delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S5l — optional array type errors and non-numeric versions fall back with a
// warning instead of being silently coerced.
{
  const root = project("type-error")
  writeFileSync(path.join(root, "tests", "working_note.md"),
    "```vibeweaver-state\n" + JSON.stringify({ version: 1, task: "type", next_action: "TYPE-NEXT", confirmed: "not-an-array" }) + "\n```\n## Next action\nTYPE-FALLBACK-NEXT\n")
  const bundle = await compact(await hooksFor(root), "s-type-error")
  rec("S5l optional array type error warns and falls back", bundle.includes("WORKING-STATE SCHEMA WARNING") && bundle.includes("TYPE-FALLBACK-NEXT"), bundle.slice(0, 140))
}

// S5l2 — a non-string array element is a schema type error, not silent loss.
{
  const root = project("element-type-error")
  writeFileSync(path.join(root, "tests", "working_note.md"),
    "```vibeweaver-state\n" + JSON.stringify({ version: 1, task: "element", next_action: "ELEMENT-NEXT", open: ["O1", 5] }) + "\n```\n## Next action\nELEMENT-FALLBACK-NEXT\n")
  const bundle = await compact(await hooksFor(root), "s-element-type-error")
  rec("S5l2 non-string array element warns and falls back", bundle.includes("WORKING-STATE SCHEMA WARNING") && bundle.includes("ELEMENT-FALLBACK-NEXT"), bundle.slice(0, 140))
}

// S5n — a common action phrase also present in the head must not suppress the
// actual `## Next action` section (the old substring-probe bug).
{
  const root = project("repeat-action")
  const note = "# WN\n## Hypothesis ledger\nconfirmed: Run tests before editing\n" +
    "H".repeat(4300) + "\n## Next action\nRun tests\n"
  writeFileSync(path.join(root, "tests", "working_note.md"), note)
  const bundle = await compact(await hooksFor(root), "s-repeat-action")
  rec("S5n repeated action phrase still yields the action heading", bundle.includes("## Next action\nRun tests"), bundle.slice(0, 160))
  rec("S5n2 repeated-action delivery <=4096B", bytes(bundle) <= 4096, `${bytes(bundle)}B`)
}

// S5o — content after the current action section is still useful tail state.
{
  const root = project("tail-after-action")
  const note = "H".repeat(3800) + "\n## Next action\nACTION-TOKEN\n## Open\nTAIL-IMPORTANT\n"
  writeFileSync(path.join(root, "tests", "working_note.md"), note)
  const bundle = await compact(await hooksFor(root), "s-tail-after-action")
  rec("S5o content after the action section survives", bundle.includes("ACTION-TOKEN") && bundle.includes("TAIL-IMPORTANT"), bundle.slice(-160))
}

// S5p — earlier superseded action sections are removed, not shown as stale.
{
  const root = project("stale-action")
  const note = "## Next action\nSTALE-ACTION\n" + "H".repeat(4400) + "\n## Next action\nREAL-ACTION\n"
  writeFileSync(path.join(root, "tests", "working_note.md"), note)
  const bundle = await compact(await hooksFor(root), "s-stale-action")
  rec("S5p stale action section is removed", bundle.includes("REAL-ACTION") && !bundle.includes("STALE-ACTION"), bundle.slice(0, 140))
}

// S5m — an existing empty note resets state; it must not revive the old
// snapshot when the file is later deleted.
{
  const root = project("empty-reset")
  writeFileSync(path.join(root, "tests", "working_note.md"), "# WN\nEMPTY-RESET-OLD-TOKEN\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-empty-reset")
  writeFileSync(path.join(root, "tests", "working_note.md"), "   \n")
  const emptied = await compact(hooks, "s-empty-reset")
  rmSync(path.join(root, "tests", "working_note.md"), { force: true })
  const deleted = await compact(hooks, "s-empty-reset")
  rec("S5m empty note does not resurrect stale snapshot", !emptied.includes("EMPTY-RESET-OLD-TOKEN") && !deleted.includes("EMPTY-RESET-OLD-TOKEN") && deleted.includes("COMPACT-RESUME"), deleted.slice(0, 120))
  rec("S5m2 empty-note message distinguishes an existing empty file", emptied.includes("exists but is empty"), emptied.slice(0, 120))
}

// S5s — a read failure (EISDIR) must not delete a valid snapshot; delivery
// falls back to the preserved snapshot and says the source is unreadable.
{
  const root = project("read-error-snapshot")
  writeFileSync(path.join(root, "tests", "working_note.md"), "# WN\nREAD-ERROR-TOKEN\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-read-error")
  const notePath = path.join(root, "tests", "working_note.md")
  rmSync(notePath, { force: true })
  mkdirSync(notePath)
  const failedRead = await compact(hooks, "s-read-error")
  rmSync(notePath, { recursive: true, force: true })
  const recovered = await compact(hooks, "s-read-error")
  rec("S5s read failure falls back to the preserved snapshot", failedRead.includes("READ-ERROR-TOKEN") && failedRead.includes("unreadable") && recovered.includes("READ-ERROR-TOKEN"), failedRead.slice(0, 140))
}

// S5t — an oversize-but-readable note must refresh the snapshot (not resurrect
// an older task state) and be flagged as truncated.
{
  const root = project("oversize-refresh")
  const notePath = path.join(root, "tests", "working_note.md")
  writeFileSync(notePath, "# OLD\nOVERSIZE-OLD-TOKEN\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-oversize-refresh")
  writeFileSync(notePath, "OVERSIZE-NEW-TOKEN\n" + "x".repeat(1.1 * 1024 * 1024))
  await compact(hooks, "s-oversize-refresh")
  rmSync(notePath, { force: true })
  const afterDelete = await compact(hooks, "s-oversize-refresh")
  rec("S5t oversize note refreshes snapshot instead of resurrecting old state", afterDelete.includes("OVERSIZE-NEW-TOKEN") && !afterDelete.includes("OVERSIZE-OLD-TOKEN"), afterDelete.slice(0, 160))
}

// S5t2 — a freeform action at the tail of a >1MB note survives both live
// delivery and the head+tail snapshot.
{
  const root = project("oversize-tail")
  const notePath = path.join(root, "tests", "working_note.md")
  writeFileSync(notePath, "x".repeat(1.1 * 1024 * 1024) + "\n## Next action\nOVERSIZE-TAIL-ACTION\n")
  const hooks = await hooksFor(root)
  const live = await compact(hooks, "s-oversize-tail")
  rmSync(notePath, { force: true })
  const afterDelete = await compact(hooks, "s-oversize-tail")
  rec("S5t2 oversize tail action survives live delivery and snapshot", live.includes("OVERSIZE-TAIL-ACTION") && afterDelete.includes("OVERSIZE-TAIL-ACTION"), afterDelete.slice(0, 180))
}

// S5u — symlinked notes are not task state: external content is never
// snapshotted/delivered, and a symlink-to-empty does not delete a valid snapshot.
{
  const root = project("symlink-note")
  const outside = path.join(TMP, "outside-secret.txt")
  writeFileSync(outside, "EXTERNAL-SECRET-TOKEN\n")
  writeFileSync(path.join(root, "tests", "working_note.md"), "# WN\nSYMLINK-OLD-TOKEN\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-symlink-note")
  const notePath = path.join(root, "tests", "working_note.md")
  rmSync(notePath, { force: true })
  symlinkSync(outside, notePath)
  const linked = await compact(hooks, "s-symlink-note")
  const snap = path.join(root, ".vibeweaver", "memory-snapshot.json")
  const snapText = existsSync(snap) ? readFileSync(snap, "utf8") : ""
  rec("S5u symlink note is not snapshotted or delivered", !linked.includes("EXTERNAL-SECRET-TOKEN") && !snapText.includes("EXTERNAL-SECRET-TOKEN") && linked.includes("SYMLINK-OLD-TOKEN"), linked.slice(0, 160))
  rmSync(notePath, { force: true })
  writeFileSync(path.join(TMP, "empty-note-target.md"), "")
  symlinkSync(path.join(TMP, "empty-note-target.md"), notePath)
  const symlinkEmpty = await compact(hooks, "s-symlink-note")
  rec("S5u2 symlink-to-empty does not delete the snapshot", symlinkEmpty.includes("SYMLINK-OLD-TOKEN"), symlinkEmpty.slice(0, 140))
}

// S5v — EACCES (non-root) is treated like any other unreadable source,
// including a zero-byte file whose mode denies the open.
if (typeof process.getuid === "function" && process.getuid() !== 0) {
  const root = project("eacces-note")
  const notePath = path.join(root, "tests", "working_note.md")
  writeFileSync(notePath, "# WN\nEACCES-TOKEN\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-eacces")
  chmodSync(notePath, 0o000)
  const failed = await compact(hooks, "s-eacces")
  chmodSync(notePath, 0o644)
  const recovered = await compact(hooks, "s-eacces")
  rec("S5v EACCES falls back to the preserved snapshot", failed.includes("EACCES-TOKEN") && failed.includes("unreadable") && recovered.includes("EACCES-TOKEN"), failed.slice(0, 140))
  writeFileSync(notePath, "")
  chmodSync(notePath, 0o000)
  const zeroFailed = await compact(hooks, "s-eacces")
  chmodSync(notePath, 0o644)
  writeFileSync(notePath, "# WN\nEACCES-TOKEN\n")
  rec("S5v2 zero-byte EACCES still falls back (not empty reset)", zeroFailed.includes("EACCES-TOKEN") && zeroFailed.includes("unreadable"), zeroFailed.slice(0, 140))
}

// S5w — `.vibeweaver` symlinked outside the project must not write or read
// snapshot state; injected external state is never delivered as authoritative.
{
  const root = project("state-symlink")
  const notePath = path.join(root, "tests", "working_note.md")
  writeFileSync(notePath, "# WN\nSTATE-SYMLINK-TOKEN\n")
  const outside = path.join(TMP, "outside-state")
  rmSync(outside, { recursive: true, force: true })
  mkdirSync(outside, { recursive: true })
  rmSync(path.join(root, ".vibeweaver"), { recursive: true, force: true })
  symlinkSync(outside, path.join(root, ".vibeweaver"))
  const hooks = await hooksFor(root)
  await compact(hooks, "s-state-symlink")
  const wroteOutside = existsSync(path.join(outside, "memory-snapshot.json"))
  if (!wroteOutside) {
    writeFileSync(path.join(outside, "memory-snapshot.json"), JSON.stringify({ rel: "tests/working_note.md", text: "INJECTED-EXTERNAL-STATE", t: Date.now() }))
  }
  rmSync(notePath, { force: true })
  const deleted = await compact(hooks, "s-state-symlink")
  rec("S5w state-directory symlink is neither written nor read", !wroteOutside && !deleted.includes("INJECTED-EXTERNAL-STATE"), deleted.slice(0, 160))
}

// S6 — legacy snapshot without taskKey remains rejected (W23 compatibility).
{
  const root = project("legacy")
  writeFileSync(path.join(root, "tests", "working_note.md"), "## Next action\nLEGACY-SNAPSHOT-NEXT\n")
  const hooks = await hooksFor(root)
  await compact(hooks, "s-legacy")
  const p = path.join(root, ".vibeweaver", "memory-snapshot.json")
  const d = JSON.parse(readFileSync(p, "utf8"))
  delete d.taskKey
  writeFileSync(p, JSON.stringify(d))
  rmSync(path.join(root, "tests", "working_note.md"), { force: true })
  const bundle = await compact(hooks, "s-legacy")
  rec("S6a legacy no-taskKey snapshot rejected", !bundle.includes("LEGACY-SNAPSHOT-NEXT") && bundle.includes("COMPACT-RESUME"), bundle.slice(0, 120))
}

console.log(`\n=== W24 CONTEXT STATE: ${count - failures}/${count} passed, ${failures} failed ===`)
process.exit(failures ? 1 : 0)
