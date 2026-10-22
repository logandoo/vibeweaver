// drive_before.mjs — invoke the v1 gate pre-hook.
// usage: node drive_before.mjs <project> <tool> <json-args>
import { existsSync } from "node:fs"
import path from "node:path"
import { pathToFileURL } from "node:url"

const project = process.argv[2]
const tool = process.argv[3]
const args = JSON.parse(process.argv[4] || "{}")
const here = path.dirname(new URL(import.meta.url).pathname)
const root = path.resolve(here, "..", "..")
const gatePath = [path.join(root, "vibeweaver-gate.js"), path.join(root, "vibeweaver", "vibeweaver-gate.js")].find((p) => existsSync(p))
const mod = await import(pathToFileURL(gatePath).href)
const hooks = await mod.default.server({ client: { app: { log: async () => {} } }, directory: project })
try {
  await hooks["tool.execute.before"]({ tool, args, sessionID: "s-risk" }, { args })
  console.log("CLEAN")
} catch (e) {
  console.log("BLOCK:" + String((e && e.message) || e))
}
