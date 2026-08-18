"""Self-test suite for the vibeweaver skill package.

Validates the canonical assertion script against fixture projects
(pass + mutation-based failures), the stall observer in the plugin
(via node, when available), and the package integrity checker itself.
Standard library only; node is optional (plugin test skips without it).
"""
import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "vibeweaver"
CANONICAL = PAYLOAD / "scripts" / "assert_artifacts.py"
FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "pass_project"
PY = sys.executable

MARKERS = [
    "verification_log", "cap=5", "screenshot", "MEMORY.md", "start.sh",
    "git repo needs", "FLOW_DESIGN", "README", "Baseline verified GREEN",
    "workflow trace", "media evidence", "diagnosis:",
    "claim without stated coverage",
]


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)


class TestCanonicalScript(unittest.TestCase):
    def test_compiles(self):
        py_compile.compile(str(CANONICAL), doraise=True)

    def test_carries_all_13_markers(self):
        text = CANONICAL.read_text(encoding="utf-8")
        missing = [m for m in MARKERS if m not in text]
        self.assertEqual(missing, [], "canonical script missing markers: %s" % missing)


class TestAssertOnProject(unittest.TestCase):
    """Stage the fixture into a temp dir, install the canonical script, mutate."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vibeweaver-fixture-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(str(FIXTURE), str(self.tmp), dirs_exist_ok=True)
        shutil.copy(str(CANONICAL), str(self.tmp / "tests" / "assert_artifacts.py"))
        if os.name != "nt":
            for s in (self.tmp / "script" / "linux").glob("*.sh"):
                s.chmod(0o755)

    def assert_it(self, *flags):
        return run([PY, str(self.tmp / "tests" / "assert_artifacts.py"), *flags], cwd=str(self.tmp))

    def test_modify_existing_passes(self):
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("checks pass", r.stdout)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_new_project_passes(self):
        build = self.tmp / "script" / "linux" / "project_build.sh"
        build.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        if os.name != "nt":
            build.chmod(0o755)
        run(["git", "-C", str(self.tmp), "init", "-q"])
        run(["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"])
        run(["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "one"])
        run(["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "two", "--allow-empty"])
        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html",
                    "PAGE_DESIGN.html", "README.md", "requirements.txt"]:
            (self.tmp / doc).write_text("x\n", encoding="utf-8")
        r = self.assert_it()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_diagnosis_fails(self):
        log = self.tmp / "tests" / "verification_log.md"
        text = log.read_text(encoding="utf-8")
        text = text.replace(
            "| diagnosis: auth-service TTL 300s mismatches gateway 3600s |",
            "|")
        log.write_text(text, encoding="utf-8")
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("diagnosis:", r.stdout)

    def test_claim_without_coverage_fails(self):
        log = self.tmp / "tests" / "verification_log.md"
        log.write_text(log.read_text(encoding="utf-8") +
                       "\n- the endpoint is verified to work now\n", encoding="utf-8")
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("claim without stated coverage", r.stdout)

    def test_claim_inside_fence_ignored(self):
        # the fixture's fenced RED block contains "verified" and must not fire
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("claim without stated coverage", r.stdout)

    def test_cited_png_missing_fails(self):
        (self.tmp / "tests" / "shot.png").unlink()
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("screenshot claimed but missing/empty", r.stdout)

    def test_cited_workflow_trace_missing_fails(self):
        (self.tmp / "tests" / "workflows" / "flow.trace.log").unlink()
        r = self.assert_it("--existing", "--backend-only")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("workflow trace claimed but missing/empty", r.stdout)


DRIVER = """
import { VibeweaverGate } from "./gate.mjs"
import path from "node:path"
const dir = process.argv[2]
const hooks = await VibeweaverGate({ client: { app: { log: async () => {} } }, directory: dir })
const after = hooks["tool.execute.after"]
for (let i = 1; i <= 3; i++) {
  const out = { output: "base" }
  let err = ""
  try {
    await after({ tool: "edit", args: { filePath: path.join(dir, "src", "app.py") } }, out)
  } catch (e) { err = String((e && e.message) || e) }
  const text = (out.output || "") + (err ? "\\nTHROW " + err : "")
  console.log("R" + i + " STALL=" + (text.includes("STALL observed") ? "Y" : "N") + " THROW=" + (err ? "Y" : "N"))
}
"""


class TestGatePlugin(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_stall_observer_fires_on_third_same_file_edit(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="vibeweaver-gate-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "tests").mkdir()
        (tmp / "tests" / "verification_log.md").write_text(
            "## Task: x | 2026-08-19\n"
            "- iter 1 FAIL: criterion #1 (y) | diagnosis: z | changed: src/app.py\n",
            encoding="utf-8")
        (tmp / "tests" / "acceptance.md").write_text(
            "> cap=5  stall=3×\n\n1. x works\n", encoding="utf-8")
        shutil.copy(str(PAYLOAD / "vibeweaver-gate.js"), str(tmp / "gate.mjs"))
        (tmp / "driver.mjs").write_text(DRIVER, encoding="utf-8")
        r = run(["node", str(tmp / "driver.mjs"), str(tmp)], cwd=str(tmp))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = [l for l in r.stdout.splitlines() if l.startswith("R")]
        self.assertEqual(len(lines), 3, r.stdout)
        self.assertIn("STALL=N", lines[0])
        self.assertIn("STALL=N", lines[1])
        self.assertIn("STALL=Y", lines[2])
        state = tmp / ".vibeweaver" / "state.json"
        self.assertTrue(state.is_file(), "stall observer must persist .vibeweaver/state.json")
        import json
        ops = json.loads(state.read_text(encoding="utf-8"))["ops"]
        self.assertEqual(len(ops), 3)
        self.assertTrue(all(o["p"] == 0 for o in ops))


class TestPackageCoherence(unittest.TestCase):
    def test_verify_skill_exits_zero(self):
        r = run([PY, str(ROOT / "verify_skill.py")], cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
