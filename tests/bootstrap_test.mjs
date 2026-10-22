// bootstrap_test.mjs — PLAN W0 Task 4.
// v1: inject once at session start; re-inject after compaction; skip children;
//     never stack on an already-forced full contract.
// v2: session context hook injects once. no-hook: bootstrap.md fallback exists.
import { existsSync } from "node:fs"
import os from "node:os"
import path from "node:path"

import { existsSync as exists } from "node:fs"
import { fileURLToPath, pathToFileURL } from "node:url"
const HERE = new URL("..", import.meta.url).pathname
const HOME = exists(new URL("../vibeweaver/SKILL.md", import.meta.url).pathname)
  ? new URL("../vibeweaver", import.meta.url).pathname
  : HERE
process.env.VIBEWEAVER_HOME = HOME
const GATE_PATH = exists(new URL("../vibeweaver-gate.js", import.meta.url).pathname)
  ? new URL("../vibeweaver-gate.js", import.meta.url).pathname
  : new URL("../vibeweaver/vibeweaver-gate.js", import.meta.url).pathname
const gate = (await import(pathToFileURL(GATE_PATH).href)).default
const boot = (arr) => (arr || []).filter((s) => String(s).includes("using-vibeweaver (bootstrap v")).length
const results = []
function rec(name, ok, detail = "") {
  results.push([name, ok])
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

const hooks = await gate.server({
  client: { app: { log: async () => {} } },
  directory: os.tmpdir(),
})
const sys = hooks["experimental.chat.system.transform"]

{
  const out = { system: ["base"] }
  await sys({ sessionID: "boot-s1" }, out)
  const first = boot(out.system)
  await sys({ sessionID: "boot-s1" }, out)
  const second = boot(out.system)
  const text = out.system.find((s) => String(s).includes("using-vibeweaver (bootstrap v")) || ""
  rec("v1 session start injects exactly once", first === 1 && second === 1, `first=${first} second=${second}`)
  rec("bootstrap payload is the 1-2 KB pointer", String(text).length > 200 && String(text).length < 4096 && String(text).includes("tests/"), `len=${String(text).length}`)
}

{
  await hooks.event({ event: { type: "session.compacted", properties: { sessionID: "boot-s1" } } })
  const out = { system: ["base"] }
  await sys({ sessionID: "boot-s1" }, out)
  rec("v1 compaction re-injects the pointer", boot(out.system) === 1, `n=${boot(out.system)}`)
}

{
  const out = { system: ["base"] }
  await sys({ sessionID: "boot-child", parentID: "boot-s1" }, out)
  rec("v1 subagent session gets no bootstrap", boot(out.system) === 0, `n=${boot(out.system)}`)
}

{
  const out = { system: ["## §1 OPERATING COVENANT — full contract already loaded"] }
  await sys({ sessionID: "boot-full" }, out)
  rec("v1 full contract already injected -> no double stack", boot(out.system) === 0, `n=${boot(out.system)}`)
}

{
  let contextHook = null
  const cleanup = await gate.setup({
    location: { directory: os.tmpdir() },
    tool: { hook: async () => ({ dispose() {} }) },
    event: { subscribe: async function* () {} },
    session: { hook: async (name, cb) => { if (name === "context") contextHook = cb; return { dispose() {} } } },
  })
  const out = { system: ["base"] }
  await contextHook({ sessionID: "boot-v2" }, out)
  await contextHook({ sessionID: "boot-v2" }, out)
  rec("v2 session context hook injects once", boot(out.system) === 1, `n=${boot(out.system)}`)
  if (typeof cleanup === "function") cleanup()
}

{
  const r = await gate.setup({ location: { directory: os.tmpdir() } })
  const file = path.join(HOME, "bootstrap.md")
  rec("no-hook fallback: setup is inert and bootstrap.md exists", r === undefined && existsSync(file), `setup=${typeof r} file=${existsSync(file)}`)
}

const fails = results.filter(([, ok]) => !ok).length
console.log(`\nBOOTSTRAP ${results.length - fails}/${results.length} passed`)
process.exit(fails ? 1 : 0)
