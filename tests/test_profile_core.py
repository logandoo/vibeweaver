#!/usr/bin/env python3
"""W1 Task 9 — core profile content + install budget."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAY = ROOT / "vibeweaver" if (ROOT / "vibeweaver" / "SKILL.md").is_file() else ROOT
CORE = PAY / "profiles" / "core" / "SKILL.md"


class CoreProfileTest(unittest.TestCase):
    def test_core_exists_and_fits_budget(self):
        self.assertTrue(CORE.is_file())
        text = CORE.read_text(encoding="utf-8")
        self.assertLessEqual(len(text) // 4, 4000)
        for n in range(0, 14):
            self.assertIn("COV-%d" % n, text)

    def test_token_budget_check_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "token_budget.py"),
                            "--root", str(ROOT), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("TOKEN-BUDGET OK", r.stdout)

    def test_install_core_profile(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-core-"))
        home = tmp / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
        r = subprocess.run(["bash", str(PAY / "install.sh"), "--profile", "core"],
                           capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        skill = home / ".config" / "opencode" / "skills" / "vibeweaver"
        installed = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(installed) // 4, 4000)
        manifest = json.loads((skill / ".installed.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["profile"], "core")
        r = subprocess.run([sys.executable, str(PAY / "scripts" / "install.py"), "--check"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("profile=core", r.stdout)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
