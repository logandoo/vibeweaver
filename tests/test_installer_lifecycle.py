#!/usr/bin/env python3
"""W1 Task 5.5 — installer lifecycle (install/check/upgrade/rollback/uninstall)."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build_source(tmp):
    src = tmp / "src"
    (src / "scripts").mkdir(parents=True)
    (src / "SKILL.md").write_text("# skill v1\n", encoding="utf-8")
    (src / "COMPLETION_GATE.md").write_text("# gate v1\n", encoding="utf-8")
    (src / "bootstrap.md").write_text("# bootstrap\n", encoding="utf-8")
    (src / "profiles" / "core").mkdir(parents=True)
    (src / "profiles" / "core" / "SKILL.md").write_text("# core\n", encoding="utf-8")
    (src / "scripts" / "assert_artifacts.py").write_text("print('v1')\n", encoding="utf-8")
    (src / "vibeweaver-gate.js").write_text("export default {}\n", encoding="utf-8")
    shutil.copy(ROOT / "scripts" / "install.py", src / "scripts" / "install.py")
    return src


class InstallerLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-inst-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.src = build_source(self.tmp)
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"))
        self.env.pop("VIBEWEAVER_HOME", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_installer(self, *args, src=None):
        return subprocess.run(
            [sys.executable, str((src or self.src) / "scripts" / "install.py"), *args],
            capture_output=True, text=True, timeout=60, env=self.env,
        )

    @property
    def skill(self):
        return self.home / ".config" / "opencode" / "skills" / "vibeweaver"

    def test_dry_run_writes_nothing(self):
        r = self.run_installer("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("dry-run", r.stdout)
        self.assertFalse(self.skill.exists())

    def test_install_writes_files_and_manifest(self):
        r = self.run_installer("--profile", "full")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.skill / "SKILL.md").is_file())
        self.assertTrue((self.skill / "scripts" / "assert_artifacts.py").is_file())
        manifest = json.loads((self.skill / ".installed.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["profile"], "full")
        self.assertTrue(any(f["path"] == "SKILL.md" for f in manifest["files"]))

    def test_check_green_then_detects_drift(self):
        self.assertEqual(self.run_installer("--profile", "full").returncode, 0)
        r = self.run_installer("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("profile=full", r.stdout)
        (self.skill / "SKILL.md").write_text("tampered\n", encoding="utf-8")
        self.assertEqual(self.run_installer("--check").returncode, 1)

    def test_upgrade_backs_up_and_updates(self):
        self.assertEqual(self.run_installer("--profile", "full").returncode, 0)
        (self.src / "SKILL.md").write_text("# skill v2\n", encoding="utf-8")
        r = self.run_installer("--profile", "full", "--backup")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.skill / "SKILL.md").read_text(encoding="utf-8"), "# skill v2\n")
        backups = list((self.home / ".config" / "opencode" / "skills").glob("vibeweaver.bak.*"))
        self.assertTrue(backups, "no backup directory created")

    def test_rollback_restores_previous_install(self):
        self.assertEqual(self.run_installer("--profile", "full", "--backup").returncode, 0)
        (self.src / "SKILL.md").write_text("# skill v2\n", encoding="utf-8")
        self.assertEqual(self.run_installer("--profile", "full", "--backup").returncode, 0)
        r = self.run_installer("--rollback")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v1", (self.skill / "SKILL.md").read_text(encoding="utf-8"))

    def test_uninstall_preserves_memory(self):
        self.assertEqual(self.run_installer("--profile", "full").returncode, 0)
        (self.skill / "memory").mkdir(exist_ok=True)
        (self.skill / "memory" / "MEMORY.md").write_text("keep me\n", encoding="utf-8")
        r = self.run_installer("--uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.skill / "SKILL.md").exists())
        self.assertTrue((self.skill / "memory" / "MEMORY.md").is_file())

    def test_force_required_for_unmanaged_file(self):
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("user file\n", encoding="utf-8")
        r = self.run_installer("--profile", "full")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--force", r.stderr)
        r = self.run_installer("--profile", "full", "--force")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.skill / "SKILL.md").read_text(encoding="utf-8"), "# skill v1\n")

    def test_from_migration_and_unknown_profile(self):
        self.assertEqual(self.run_installer("--profile", "full").returncode, 0)
        r = self.run_installer("--from", "w18.2.4")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("migration", r.stdout.lower())
        r = self.run_installer("--profile", "bogus")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
