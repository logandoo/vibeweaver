// state_bounds_test.mjs — PLAN W0 Task 1.5 acceptance #18.
// Redaction before write, bounded state under a 20k-event stream, retention.
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

process.env.VIBEWEAVER_MAX_STATE_BYTES = "120000"
process.env.VIBEWEAVER_RETENTION_DAYS = "14"
const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..")
const auditPath = [path.join(repoRoot, "vibeweaver-audit.js"), path.join(repoRoot, "vibeweaver", "vibeweaver-audit.js")].find((p) => existsSync(p))
const audit = (await import(pathToFileURL(auditPath).href)).default

function mkproj(label) {
  const root = mkdtempSync(path.join(os.tmpdir(), "vw-state-" + label + "-"))
  mkdirSync(path.join(root, "tests"), { recursive: true })
  writeFileSync(path.join(root, "tests", "verification_log.md"), "## fixture\n- class: CODE\n")
  return root
}
function load(root) {
  return audit.server({ client: { app: { log: async () => {} } }, directory: root })
}
const results = []
function rec(name, ok, detail = "") {
  results.push(ok)
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}
const skillPart = (sid) => ({
  type: "tool", tool: "skill", callID: "skill-1", messageID: "m0",
  state: { status: "completed", input: { name: "vibeweaver" }, output: "loaded" },
})

// 1) redaction + 20k bounded stream
{
  const root = mkproj("stream")
  const hooks = await load(root)
  const s = path.join(root, ".vibeweaver", "audit-state.json")
  await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "s1", part: skillPart("s1") } } })
  await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "s1", part: { type: "reasoning", id: "r1", messageID: "m1", text: `sshpass -p ${"hunter" + "2"} AKIA${"ABCDEFGHIJKLMNOP"}` } } } })
  const N = Number(process.env.VW_STATE_EVENTS || 20000)
  for (let i = 0; i < N; i++) {
    const part = {
      type: "tool", tool: "bash", callID: "c" + i, messageID: "m1",
      state: {
        status: "completed",
        input: { command: `sshpass -p ${"hunter" + "2"} echo ${i} ${"AKIA" + "ABCDEFGHIJKLMNOP"}` },
        output: "ok " + "x".repeat(200),
      },
    }
    await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "s1", part } } })
  }
  await hooks.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
  const raw = existsSync(s) ? readFileSync(s, "utf8") : ""
  const size = existsSync(s) ? statSync(s).size : 0
  rec("20k-event state stays under the 120 KB cap", size > 0 && size <= 120000, `size=${size}`)
  rec("state file contains no plaintext credential", !raw.includes("hunter2") && !raw.includes("AKIA" + "ABCDEFGHIJKLMNOP"), `len=${raw.length}`)
  rec("state preserves the command shape with redaction markers", raw.includes("[REDACTED:sshpass:") && raw.includes("[REDACTED:aws-access-key-id:"), "")
  rmSync(root, { recursive: true, force: true })
}

// 2) retention drops sessions older than the window
{
  const root = mkproj("retention")
  mkdirSync(path.join(root, ".vibeweaver"), { recursive: true })
  const old = { sessions: { old: { text: "stale", textParts: {}, tools: [], skillLoaded: false, updatedAt: 1 } }, roots: {} }
  writeFileSync(path.join(root, ".vibeweaver", "audit-state.json"), JSON.stringify(old))
  const hooks = await load(root)
  await hooks.event({ event: { type: "message.part.updated", properties: { sessionID: "new", part: skillPart("new") } } })
  await hooks.event({ event: { type: "session.idle", properties: { sessionID: "new" } } })
  const st = JSON.parse(readFileSync(path.join(root, ".vibeweaver", "audit-state.json"), "utf8"))
  rec("retention drops stale sessions", !st.sessions.old && !!st.sessions.new, Object.keys(st.sessions).join(","))
  rmSync(root, { recursive: true, force: true })
}

const fails = results.filter((ok) => !ok).length
console.log(`\nSTATE-BOUNDS ${results.length - fails}/${results.length} passed`)
process.exit(fails ? 1 : 0)
