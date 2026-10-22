// drive_gate.mjs — invoke the v1 gate hook against a temp project.
// usage: node drive_gate.mjs <project> <target>   (env: VIBEWEAVER_HOME)
import { existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const project = process.argv[2]
const target = process.argv[3]
if (!project || !target) {
  console.error("usage: node drive_gate.mjs <project> <target>")
  process.exit(2)
}
const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")
const candidates = [
  process.env.VIBEWEAVER_GATE_MODULE,
  path.join(repoRoot, "vibeweaver-gate.js"),
  path.join(repoRoot, "vibeweaver", "vibeweaver-gate.js"),
].filter(Boolean)
const gatePath = candidates.find((p) => existsSync(p))
if (!gatePath) {
  console.error("gate module not found (dev or repo layout)")
  process.exit(2)
}
const mod = await import(pathToFileURL(gatePath).href)
const gate = mod.default
const hooks = await gate.server({
  client: { app: { log: async () => {} } },
  directory: project,
})
let verdict = "CLEAN"
let notes = []
try {
  const out = { output: "" }
  const r = await hooks["tool.execute.after"](
    { tool: "write", args: { path: target }, sessionID: "s-gate-trust" },
    out,
  )
  if (r && r.notes) notes = r.notes
  if (out.output) notes.push(out.output)
} catch (e) {
  verdict = "BLOCK:" + String((e && e.message) || e)
}
if (process.env.VW_DRIVE_JSON === "1") {
  console.log(JSON.stringify({ verdict, notes }))
} else {
  console.log(verdict)
}
