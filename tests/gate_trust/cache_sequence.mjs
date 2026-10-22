// cache_sequence.mjs — one process, one gate instance: exercises the result
// cache across writes the way a live host does.
// usage: node cache_sequence.mjs <project> <VIBEWEAVER_HOME>
import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs"
import { createHash } from "node:crypto"
import path from "node:path"
import { pathToFileURL } from "node:url"

const project = process.argv[2]
const home = process.argv[3]
if (!project || !home) {
  console.error("usage: node cache_sequence.mjs <project> <home>")
  process.exit(2)
}
process.env.VIBEWEAVER_HOME = home
const here = path.dirname(new URL(import.meta.url).pathname)
const repoRoot = path.resolve(here, "..", "..")
const gatePath = [path.join(repoRoot, "vibeweaver-gate.js"), path.join(repoRoot, "vibeweaver", "vibeweaver-gate.js")].find((p) => existsSync(p))
const mod = await import(pathToFileURL(gatePath).href)
const hooks = await mod.default.server({
  client: { app: { log: async () => {} } },
  directory: project,
})
const target = path.join(project, "src", "app.js")

async function call(final) {
  if (final) process.env.VIBEWEAVER_GATE_FINAL = "1"
  else delete process.env.VIBEWEAVER_GATE_FINAL
  try {
    await hooks["tool.execute.after"]({ tool: "write", args: { path: target }, sessionID: "s-cache" }, { output: "" })
    return "CLEAN"
  } catch (e) {
    return "BLOCK:" + String((e && e.message) || e)
  }
}
function runs() {
  try {
    return readFileSync(path.join(project, "checker_runs.log"), "utf8").trim().split("\n").filter(Boolean).length
  } catch {
    return 0
  }
}

const a = await call(false)
const b = await call(false)
console.log(`STEP1 ${a} ${b} ${runs()}`)

const c = await call(true)
console.log(`STEP2 ${c} ${runs()}`)

appendFileSync(path.join(project, "tests", "verification_log.md"), "- evidence: changed\n")
const d = await call(false)
console.log(`STEP3 ${d} ${runs()}`)

const canonical = path.join(home, "scripts", "assert_artifacts.py")
appendFileSync(canonical, "\n# checker updated\n")
const digest = createHash("sha256").update(readFileSync(canonical)).digest("hex")
writeFileSync(path.join(home, "scripts", "assert_artifacts.sha256"), `${digest}  assert_artifacts.py\n`)
const e = await call(false)
console.log(`STEP4 ${e}`)
