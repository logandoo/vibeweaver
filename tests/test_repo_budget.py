#!/usr/bin/env python3
"""Executable acceptance for scripts/repo_budget.py (live-tree total)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "vibeweaver"
SCRIPT = PAYLOAD / "scripts" / "repo_budget.py"
BASELINE = "tests/repo_budget_baseline.json"


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def put(repo, rel, data):
    path = Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def commit(repo, paths, message="fixture"):
    git(repo, "add", "--", *paths)
    result = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message],
                            capture_output=True, text=True)
    text = result.stdout + result.stderr
    if (result.returncode and "nothing to commit" not in text
            and "nothing added to commit" not in text
            and "no changes added to commit" not in text):
        raise AssertionError(f"git commit failed: {text}")


class RepoBudgetFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "Fixture")
        put(self.repo, ".gitignore", "ignored.bin\n")
        put(self.repo, "small.py", "x\n")
        git(self.repo, "add", "--", ".gitignore", "small.py")
        git(self.repo, "commit", "-q", "-m", "initial")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.repo), *args],
            capture_output=True, text=True,
        )

    def baseline(self):
        return json.loads((self.repo / BASELINE).read_text(encoding="utf-8"))

    def init(self, *args):
        result = self.cli("init", *args)
        if result.returncode == 0 and (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        return result

    def check(self, *args):
        if (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        return self.cli("check", "--final", *args)

    def test_init_and_check_pass(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.assertIn("live_tree_bytes", self.baseline())
        self.assertEqual(0, self.check().returncode)

    def test_live_tree_growth_fails_and_removal_passes(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        put(self.repo, "big.bin", b"x" * 4096)
        grown = self.check()
        self.assertEqual(1, grown.returncode)
        self.assertIn("ceiling", (grown.stdout + grown.stderr).lower())
        (self.repo / "big.bin").unlink()
        self.assertEqual(0, self.check().returncode)

    def test_ignored_file_does_not_count(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        put(self.repo, "ignored.bin", b"x" * 100000)
        self.assertEqual(0, self.check().returncode)

    def test_tighten_lowers_and_locks_gain(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        put(self.repo, "big.bin", b"x" * 4096)
        self.assertEqual(1, self.check().returncode)
        (self.repo / "big.bin").unlink()
        self.assertEqual(0, self.cli("tighten").returncode)
        before = self.baseline()["ceiling"]
        put(self.repo, "one.bin", b"x")
        self.assertEqual(1, self.check().returncode)
        (self.repo / "one.bin").unlink()
        self.assertEqual(before, self.baseline()["ceiling"])

    def test_no_baseline_nonfinal_warns_final_fails_closed(self):
        early = self.cli("check")
        self.assertEqual(0, early.returncode, early.stderr)
        self.assertIn("no baseline", (early.stdout + early.stderr).lower())
        self.assertEqual(2, self.cli("check", "--final").returncode)

    def test_base_rejects_ceiling_raise(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        data = self.baseline()
        data["ceiling"] = 10 ** 12
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.check("--base", base)
        self.assertEqual(1, result.returncode)
        self.assertIn("raised", (result.stdout + result.stderr).lower())

    def test_baseline_padding_is_rejected(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        data = self.baseline()
        data["reason"] = "x" * (70 * 1024)
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(2, result.returncode)
        self.assertIn("64 kib", (result.stdout + result.stderr).lower())

    def test_machine_state_is_excluded(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        put(self.repo, ".vibeweaver/state.json", b"x" * (1024 * 1024))
        put(self.repo, "tests/gate_result.json", b"x" * (1024 * 1024))
        self.assertEqual(0, self.check().returncode)

    def test_final_requires_tracked_baseline(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        (self.repo / BASELINE).unlink()
        (self.repo / BASELINE).write_text(json.dumps({"version": 1, "ceiling": 10 ** 12,
                                                       "live_tree_bytes": 0, "slack": 0,
                                                       "largest_blob": 0, "top_n": []}),
                                           encoding="utf-8")
        result = self.cli("check", "--final")
        self.assertEqual(2, result.returncode)
        self.assertIn("before --final", (result.stdout + result.stderr).lower())

    def test_adopt_optional_final_without_baseline_passes(self):
        early = self.cli("check", "--final", "--adopt-optional")
        self.assertEqual(0, early.returncode, early.stderr)
        self.assertIn("not adopted", (early.stdout + early.stderr).lower())
        self.assertEqual(2, self.cli("check", "--final").returncode)

    def test_assume_unchanged_baseline_is_rejected(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        git(self.repo, "update-index", "--assume-unchanged", BASELINE)
        data = self.baseline()
        data["ceiling"] = 10 ** 12
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.cli("check", "--final")
        self.assertEqual(2, result.returncode)
        out = (result.stdout + result.stderr).lower()
        self.assertTrue("assume-unchanged" in out or "differs from head" in out)

    def test_auto_base_rejects_committed_ceiling_raise(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        data = self.baseline()
        data["ceiling"] = 10 ** 12
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(1, result.returncode)
        self.assertIn("raised", (result.stdout + result.stderr).lower())

    def test_shallow_clone_fails_closed(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        clone = Path(self.tmp.name) / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        self.repo.as_uri(), str(clone)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(clone),
                                 "check", "--final", "--adopt-optional"],
                                capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertIn("full history", (result.stdout + result.stderr).lower())

    def test_budget_json_has_headroom_and_top_n(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        result = self.cli("budget", "--format", "json")
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("headroom", data)
        self.assertTrue(data["top_n"])


if __name__ == "__main__":
    unittest.main()
