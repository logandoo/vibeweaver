#!/usr/bin/env python3
"""Executable acceptance for scripts/source_ratchet.py (stdlib only)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "vibeweaver"
SCRIPT = PAYLOAD / "scripts" / "source_ratchet.py"
BASELINE = "tests/source_ratchet_baseline.json"
GRANTS = "tests/source_ratchet_grants.jsonl"


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def put(repo, rel, data):
    path = Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
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


class RatchetFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "Fixture")
        put(self.repo, ".gitignore", ".vibeweaver/\n")
        put(self.repo, "config.toml",
            '[source_budget]\nmode="shadow"\nwarn_lines=3\nhard_lines=5\n')
        commit(self.repo, [".gitignore", "config.toml"], "initial")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.repo), *args],
            capture_output=True, text=True, env=env,
        )

    def init(self, *args):
        result = self.cli("init", *args)
        if result.returncode == 0 and (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        return result

    def check(self, *args):
        if (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        if (self.repo / GRANTS).exists():
            commit(self.repo, [GRANTS], "grants")
        return self.cli("check", "--final", *args)

    def budget(self, *args):
        return self.cli("budget", *args)

    def lines(self, rel, count):
        put(self.repo, rel, "x\n" * count)

    def baseline(self):
        return json.loads((self.repo / BASELINE).read_text(encoding="utf-8"))

    def write_baseline(self, data):
        put(self.repo, BASELINE, json.dumps(data, indent=1, sort_keys=True) + "\n")

    def test_init_freezes_existing_over_hard_file_and_check_passes(self):
        self.lines("big.py", 6)
        result = self.init("--slack", "0")
        self.assertEqual(0, result.returncode, result.stderr)
        data = self.baseline()
        self.assertEqual(6, data["files"]["big.py"]["lines"])
        self.assertEqual(0, self.check().returncode)

    def test_existing_over_hard_file_growth_fails_and_shrink_passes(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("big.py", 7)
        grown = self.check()
        self.assertEqual(1, grown.returncode)
        self.assertIn("frozen", (grown.stdout + grown.stderr).lower())
        self.lines("big.py", 4)
        self.assertEqual(0, self.check().returncode)

    def test_new_file_over_hard_fails_under_hard_passes(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("new.py", 6)
        over = self.check()
        self.assertEqual(1, over.returncode)
        self.assertIn("hard", (over.stdout + over.stderr).lower())
        self.lines("new.py", 5)
        self.assertEqual(0, self.check().returncode)

    def test_group_ceiling_and_budget_headroom(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("b.py", 4)
        over = self.check()
        self.assertEqual(1, over.returncode)
        self.assertIn("group", (over.stdout + over.stderr).lower())
        report = self.budget("--format", "json")
        self.assertEqual(0, report.returncode, report.stderr)
        data = json.loads(report.stdout)
        self.assertIn("source", data["groups"])
        self.assertLess(data["groups"]["source"]["headroom"], 0)

    def test_tighten_only_lowers_and_locks_the_gain(self):
        self.lines("big.py", 8)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("big.py", 5)
        self.assertEqual(0, self.cli("tighten").returncode)
        self.assertEqual(5, self.baseline()["files"]["big.py"]["lines"])
        self.lines("big.py", 8)
        self.assertEqual(1, self.check().returncode)

    def test_init_refuses_overwrite_and_delete_re_record(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.assertEqual(2, self.init("--slack", "0").returncode)
        commit(self.repo, [BASELINE, "big.py"], "adopt")
        (self.repo / BASELINE).unlink()
        self.assertEqual(2, self.init("--slack", "0").returncode)

    def test_grant_is_append_only_and_effective(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("b.py", 4)
        self.assertEqual(1, self.check().returncode)
        grant = self.cli("grant", "--group", "source", "--lines", "10",
                         "--reason", "fixture feature", "--by", "human")
        self.assertEqual(0, grant.returncode, grant.stderr)
        self.assertIn("fixture feature", (self.repo / GRANTS).read_text(encoding="utf-8"))
        self.assertEqual(0, self.check().returncode)

    def test_expired_grant_is_ignored(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("b.py", 4)
        grant = self.cli("grant", "--group", "source", "--lines", "10",
                         "--reason", "expired fixture", "--by", "human",
                         "--expires", "2000-01-01")
        self.assertEqual(0, grant.returncode, grant.stderr)
        self.assertEqual(1, self.check().returncode)

    def test_group_classification_tests_vs_source(self):
        self.lines("src/app.py", 4)
        self.lines("tests/test_app.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        data = self.baseline()
        self.assertEqual(4, data["groups"]["source"]["ceiling"])
        self.assertEqual(4, data["groups"]["tests"]["ceiling"])

    def test_base_rejects_hand_raised_ceiling(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        data = self.baseline()
        data["groups"]["source"]["ceiling"] += 100
        self.write_baseline(data)
        raised = self.check("--base", base)
        self.assertEqual(1, raised.returncode)
        self.assertIn("grant", (raised.stdout + raised.stderr).lower())

    def test_base_accepts_appended_grant_and_rejects_later_ancestor_base(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        grant = self.cli("grant", "--group", "source", "--lines", "10",
                         "--reason", "standing budget", "--by", "human")
        self.assertEqual(0, grant.returncode, grant.stderr)
        self.assertEqual(0, self.check("--base", base).returncode)
        commit(self.repo, [GRANTS], "grant")
        later = git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(2, self.check("--base", later).returncode)

    def test_rekey_allows_pure_rename_but_refuses_copy(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        commit(self.repo, [BASELINE, "big.py"], "baseline")
        git(self.repo, "mv", "big.py", "renamed.py")
        moved = self.cli("rekey", "--from", "big.py", "--to", "renamed.py")
        self.assertEqual(0, moved.returncode, moved.stderr)
        self.assertIn("renamed.py", self.baseline()["files"])
        self.assertNotIn("big.py", self.baseline()["files"])
        put(self.repo, "copy.py", "x\n" * 6)
        copy = self.cli("rekey", "--from", "renamed.py", "--to", "copy.py")
        self.assertEqual(1, copy.returncode, copy.stderr)

    def test_assume_unchanged_baseline_is_rejected(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        git(self.repo, "update-index", "--assume-unchanged", BASELINE)
        data = self.baseline()
        data["policy"]["hard_lines"] = 5000
        data["groups"]["source"]["ceiling"] = 1000000
        self.write_baseline(data)
        self.lines("huge.py", 4000)
        result = self.cli("check", "--final")
        self.assertEqual(2, result.returncode)
        out = (result.stdout + result.stderr).lower()
        self.assertTrue("assume-unchanged" in out or "differs from head" in out)

    def test_base_rejects_spoofed_rekey_sha(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        commit(self.repo, ["big.py"], "big")
        old = self.baseline()["files"]["big.py"]
        self.lines("new.py", 20)
        git(self.repo, "rm", "-q", "big.py")
        git(self.repo, "commit", "-q", "-m", "delete big")
        data = self.baseline()
        del data["files"]["big.py"]
        data["files"]["new.py"] = {"lines": 20, "sha256": old["sha256"],
                                   "raw_bytes": old.get("raw_bytes", 12)}
        self.write_baseline(data)
        result = self.check("--base", base)
        self.assertEqual(1, result.returncode)
        self.assertIn("actual content", (result.stdout + result.stderr).lower())

    def test_final_requires_tracked_baseline(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        (self.repo / BASELINE).unlink()
        self.write_baseline({
            "version": 1,
            "policy": {"warn_lines": 3, "hard_lines": 5, "slack": 0},
            "groups": {"source": {"ceiling": 1000}, "tests": {"ceiling": 1000}},
            "files": {},
        })
        raw = self.cli("check", "--final")
        self.assertEqual(2, raw.returncode)
        self.assertIn("before --final", (raw.stdout + raw.stderr).lower())

    def test_binary_source_fails_closed(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        put(self.repo, "binary.py", b"x\x00y" * 100)
        result = self.check()
        self.assertEqual(2, result.returncode)
        self.assertIn("binary", (result.stdout + result.stderr).lower())

    def test_base_rejects_policy_and_frozen_limit_raise(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        data = self.baseline()
        data["files"]["big.py"]["lines"] = 20
        self.write_baseline(data)
        result = self.check("--base", base)
        self.assertEqual(1, result.returncode)
        self.assertIn("frozen", (result.stdout + result.stderr).lower())

    def test_base_head_is_rejected(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        result = self.check("--base", "HEAD")
        self.assertEqual(2, result.returncode)
        self.assertIn("strict ancestor", (result.stdout + result.stderr).lower())

    def test_committed_delete_reinit_is_refused(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        git(self.repo, "rm", BASELINE)
        git(self.repo, "commit", "-q", "-m", "delete baseline")
        self.assertEqual(2, self.init("--slack", "0").returncode)

    def test_frozen_file_leaving_scope_fails(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        commit(self.repo, ["big.py"], "big")
        (self.repo / "vendor").mkdir()
        git(self.repo, "mv", "big.py", "vendor/big.py")
        result = self.check()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing", (result.stdout + result.stderr).lower())

    def test_prune_refuses_content_moved_to_excluded_dir(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        commit(self.repo, ["big.py"], "big")
        (self.repo / "vendor").mkdir()
        git(self.repo, "mv", "big.py", "vendor/big.py")
        result = self.cli("prune", "--path", "big.py")
        self.assertEqual(1, result.returncode)
        self.assertIn("still exists", (result.stdout + result.stderr).lower())
        self.assertIn("big.py", self.baseline()["files"])

    def test_prune_refuses_untracked_copy_in_vendor(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        (self.repo / "vendor").mkdir()
        shutil.copy(self.repo / "big.py", self.repo / "vendor" / "big.py")
        (self.repo / "big.py").unlink()
        result = self.cli("prune", "--path", "big.py")
        self.assertEqual(1, result.returncode)
        self.assertIn("still exists", (result.stdout + result.stderr).lower())

    def test_rekey_accepts_crlf_variant(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        commit(self.repo, ["big.py"], "big")
        git(self.repo, "mv", "big.py", "renamed.py")
        (self.repo / "renamed.py").write_bytes(b"x\r\n" * 6)
        result = self.cli("rekey", "--from", "big.py", "--to", "renamed.py")
        self.assertEqual(0, result.returncode, result.stderr)

    def test_prune_refuses_copy_in_venv(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        (self.repo / ".venv").mkdir()
        shutil.copy(self.repo / "big.py", self.repo / ".venv" / "big.py")
        (self.repo / "big.py").unlink()
        result = self.cli("prune", "--path", "big.py")
        self.assertEqual(1, result.returncode)
        self.assertIn("still exists", (result.stdout + result.stderr).lower())

    def test_shallow_clone_fails_closed(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        commit(self.repo, ["big.py"], "big")
        clone = Path(self.tmp.name) / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        self.repo.as_uri(), str(clone)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(clone),
                                 "check", "--final", "--adopt-optional"],
                                capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertIn("full history", (result.stdout + result.stderr).lower())

    def test_prune_deleted_frozen_path(self):
        self.lines("big.py", 6)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        (self.repo / "big.py").unlink()
        self.assertEqual(0, self.cli("prune", "--path", "big.py").returncode)
        self.assertNotIn("big.py", self.baseline()["files"])

    def test_grant_tighten_does_not_zero_the_base(self):
        self.lines("a.py", 4)
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.lines("b.py", 4)
        self.assertEqual(1, self.check().returncode)
        grant = self.cli("grant", "--group", "source", "--lines", "10",
                         "--reason", "temporary", "--by", "human")
        self.assertEqual(0, grant.returncode, grant.stderr)
        self.assertEqual(0, self.cli("tighten").returncode)
        self.assertGreaterEqual(int(self.baseline()["groups"]["source"]["ceiling"]), 0)
        self.assertGreater(int(self.baseline()["groups"]["source"]["ceiling"]), 0)

    def test_subdirectory_history_check_uses_cwd_relative_path(self):
        sub = self.repo / "project"
        put(sub, ".gitignore", ".vibeweaver/\n")
        put(sub, "config.toml", '[source_budget]\nmode="shadow"\nwarn_lines=3\nhard_lines=5\n')
        put(sub, "big.py", "x\n" * 6)
        commit(self.repo, ["project/.gitignore", "project/config.toml", "project/big.py"], "project")
        def run(*args):
            return subprocess.run([sys.executable, str(SCRIPT), "--root", str(sub), *args],
                                  capture_output=True, text=True)
        r = run("init", "--slack", "0")
        self.assertEqual(0, r.returncode, r.stderr)
        commit(self.repo, ["project/tests/source_ratchet_baseline.json"], "sub baseline")
        git(self.repo, "rm", "-q", "project/tests/source_ratchet_baseline.json")
        git(self.repo, "commit", "-q", "-m", "delete sub baseline")
        self.assertEqual(2, run("init", "--slack", "0").returncode)
        self.assertEqual(2, run("check", "--final", "--adopt-optional").returncode)

    def test_no_baseline_nonfinal_warns_final_fails_closed(self):
        self.lines("a.py", 4)
        early = self.cli("check")
        self.assertEqual(0, early.returncode, early.stderr)
        self.assertIn("no baseline", (early.stdout + early.stderr).lower())
        self.assertEqual(2, self.check().returncode)

    def test_grant_requires_human_metadata(self):
        self.assertEqual(0, self.init("--slack", "0").returncode)
        self.assertEqual(2, self.cli("grant", "--group", "source", "--lines", "1").returncode)
        self.assertEqual(2, self.cli("grant", "--group", "source", "--lines", "1",
                                     "--reason", "x").returncode)


if __name__ == "__main__":
    unittest.main()
