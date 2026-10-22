#!/usr/bin/env python3
"""W0 Task 1.5 — state redaction CLI (values never echoed)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = [sys.executable, str((ROOT / "scripts" / "state_sanitize.py") if (ROOT / "scripts" / "state_sanitize.py").is_file() else (ROOT / "vibeweaver" / "scripts" / "state_sanitize.py"))]


class StateSanitizeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-state-"))
        self.state = self.tmp / ".vibeweaver"
        self.state.mkdir()
        self.file = self.state / "audit-state.json"
        self.file.write_text(json.dumps({
            "sessions": {
                "s1": {
                    "tools": [{"command": "sshpass -p " + "hunter" + "2" + " ssh root@host"}],
                    "text": ("AKIA" + "ABCDEFGHIJKLMNOP") + " leaked",
                }
            }
        }), encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        return subprocess.run(CLI + list(args), capture_output=True, text=True, timeout=30)

    def test_check_fails_and_never_echoes_value(self):
        r = self.run_cli("--check", str(self.state))
        self.assertEqual(r.returncode, 1)
        out = r.stdout + r.stderr
        self.assertNotIn("hunter2", out)
        self.assertNotIn("AKIA" + "ABCDEFGHIJKLMNOP", out)
        self.assertIn("credential", out)

    def test_fix_redacts_and_check_passes(self):
        self.assertEqual(self.run_cli("--fix", str(self.state)).returncode, 0)
        text = self.file.read_text(encoding="utf-8")
        self.assertNotIn("hunter2", text)
        self.assertNotIn("AKIA" + "ABCDEFGHIJKLMNOP", text)
        self.assertIn("[REDACTED:", text)
        self.assertEqual(self.run_cli("--check", str(self.state)).returncode, 0)

    def test_backup_fixture_is_scanned(self):
        bak = self.state / "audit-state.json.bak"
        bak.write_text(json.dumps({"cmd": "export API_KEY=" + "Zx9Qw8Er7Ty6Ui5"}), encoding="utf-8")
        r = self.run_cli("--check", str(self.state))
        self.assertEqual(r.returncode, 1)
        self.assertIn(".bak", r.stderr)

    def test_gitignore_contains_state_dir(self):
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".vibeweaver/", gi)


if __name__ == "__main__":
    unittest.main()
