#!/usr/bin/env python3
"""Executable acceptance for scripts/artifact_budget.py + review-package cap."""
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
SCRIPT = PAYLOAD / "scripts" / "artifact_budget.py"
BASELINE = "tests/artifact_baseline.json"


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


class ArtifactFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "Fixture")
        put(self.repo, ".gitignore", ".vibeweaver/\n")
        commit(self.repo, [".gitignore"], "initial")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.repo), *args],
            capture_output=True, text=True,
        )

    def init(self, *args):
        result = self.cli("init", *args)
        if result.returncode == 0 and (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        return result

    def check(self, *args):
        if (self.repo / BASELINE).exists():
            commit(self.repo, [BASELINE], "baseline")
        migrations = self.repo / "tests" / "artifact_migrations.jsonl"
        if migrations.exists():
            commit(self.repo, ["tests/artifact_migrations.jsonl"], "migrations")
        return self.cli("check", "--final", *args)

    def baseline(self):
        return json.loads((self.repo / BASELINE).read_text(encoding="utf-8"))

    def test_init_freezes_existing_over_cap_review_package(self):
        put(self.repo, "tests/review_package.md", "x" * (600 * 1024))
        self.assertEqual(0, self.init().returncode)
        self.assertEqual(600 * 1024, self.baseline()["files"]["tests/review_package.md"]["bytes"])
        self.assertEqual(0, self.check().returncode)

    def test_existing_review_package_growth_fails_and_shrink_passes(self):
        put(self.repo, "tests/review_package.md", "x" * (600 * 1024))
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/review_package.md", "x" * (650 * 1024))
        grown = self.check()
        self.assertEqual(1, grown.returncode)
        self.assertIn("frozen", (grown.stdout + grown.stderr).lower())
        put(self.repo, "tests/review_package.md", "x" * (400 * 1024))
        self.assertEqual(0, self.check().returncode)

    def test_new_over_cap_review_package_fails(self):
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/review_package.md", "x" * (512 * 1024 + 1))
        over = self.check()
        self.assertEqual(1, over.returncode)
        self.assertIn("cap", (over.stdout + over.stderr).lower())

    def test_logs_trajectory_and_media_groups(self):
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/big.log", "x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(1, self.check().returncode)
        put(self.repo, "tests/big.log", "x")
        self.assertEqual(0, self.check().returncode)
        put(self.repo, "tests/eval/run/trajectory.json", "x" * (2 * 1024 * 1024 + 1))
        self.assertEqual(1, self.check().returncode)
        put(self.repo, "tests/eval/run/trajectory.json", "x")
        self.assertEqual(0, self.check().returncode)
        put(self.repo, "tests/shot.png", "x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(1, self.check().returncode)

    def test_group_total_ceiling(self):
        self.assertEqual(0, self.init().returncode)
        # review total cap is 1 MiB; two 512 KiB files fit, a third exceeds.
        put(self.repo, "tests/review_package_a.md", "x" * (512 * 1024))
        put(self.repo, "tests/review_package_b.md", "x" * (512 * 1024))
        self.assertEqual(0, self.check().returncode)
        put(self.repo, "tests/review_package_c.md", "x" * (512 * 1024))
        self.assertEqual(1, self.check().returncode)

    def test_tighten_lowers_legacy_ceiling_but_not_below_configured_cap(self):
        put(self.repo, "tests/review_package.md", "x" * (2 * 1024 * 1024))
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/review_package.md", "x" * 100)
        self.assertEqual(0, self.cli("tighten").returncode)
        self.assertEqual(1024 * 1024, self.baseline()["groups"]["review"]["ceiling"])
        self.assertNotIn("tests/review_package.md", self.baseline()["files"])

    def test_review_index_archives_full_package_and_stays_small(self):
        big = self.repo / "full.md"
        body = "# Review Package\n\n## git diff --stat\n\n a.py | 1000 ++\n\n## git diff -U10\n" + ("x" * 500000)
        big.write_text(body, encoding="utf-8")
        index = self.repo / "tests" / "review_package.md"
        archive = self.repo / ".vibeweaver" / "artifacts" / "review"
        result = self.cli("review-index", "--input", str(big), "--index", str(index),
                          "--archive-dir", str(archive), "--max-bytes", "4000")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(index.is_file())
        self.assertLess(index.stat().st_size, 4000)
        archived = list(archive.iterdir())
        self.assertEqual(1, len(archived))
        self.assertIn("sha256", index.read_text(encoding="utf-8").lower())

    def test_base_rejects_ceiling_and_new_frozen_entry(self):
        self.assertEqual(0, self.init().returncode)
        base = git(self.repo, "rev-parse", "HEAD")
        data = self.baseline()
        data["groups"]["review"]["ceiling"] += 10 * 1024 * 1024
        data["files"]["tests/review_package.md"] = {"bytes": 100, "sha256": "x"}
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.check("--base", base)
        self.assertEqual(1, result.returncode)
        out = (result.stdout + result.stderr).lower()
        self.assertIn("raised", out)
        self.assertIn("new frozen", out)

    def test_missing_frozen_artifact_fails_and_prune_refuses_move(self):
        put(self.repo, "tests/review_package.md", "x" * (600 * 1024))
        self.assertEqual(0, self.init().returncode)
        commit(self.repo, ["tests/review_package.md"], "review")
        (self.repo / "tests" / "w10").mkdir()
        git(self.repo, "mv", "tests/review_package.md", "tests/w10/review_fix_package.md")
        self.assertEqual(1, self.check().returncode)
        moved = self.cli("prune", "--path", "tests/review_package.md")
        self.assertEqual(1, moved.returncode)
        self.assertIn("still exists", (moved.stdout + moved.stderr).lower())
        git(self.repo, "rm", "-q", "tests/w10/review_fix_package.md")
        git(self.repo, "commit", "-q", "-m", "remove moved review")
        self.assertEqual(0, self.cli("prune", "--path", "tests/review_package.md").returncode)
        self.assertNotIn("tests/review_package.md", self.baseline()["files"])

    @unittest.skipIf(os.name == "nt", "POSIX symlink fixture")
    def test_symlink_review_package_fails(self):
        self.assertEqual(0, self.init().returncode)
        outside = Path(self.tmp.name) / "outside_review.md"
        outside.write_text("x" * (600 * 1024), encoding="utf-8")
        target = self.repo / "tests" / "review_package.md"
        target.parent.mkdir(exist_ok=True)
        os.symlink(outside, target)
        result = self.check()
        self.assertEqual(1, result.returncode)
        self.assertIn("symlink", (result.stdout + result.stderr).lower())

    def test_prune_refuses_untracked_copy(self):
        put(self.repo, "tests/review_package.md", "x" * (600 * 1024))
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/w10/review_fix_package.md", "x" * (600 * 1024))
        (self.repo / "tests" / "review_package.md").unlink()
        result = self.cli("prune", "--path", "tests/review_package.md")
        self.assertEqual(1, result.returncode)
        self.assertIn("still exists", (result.stdout + result.stderr).lower())

    def test_reclassify_migrates_legacy_review_aliases(self):
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/review_fix_package.md", "x" * (600 * 1024))
        result = self.cli("reclassify", "--by", "human", "--reason", "N7 migration")
        self.assertEqual(0, result.returncode, result.stderr)
        data = self.baseline()
        self.assertEqual("review_aliases_v1", data["classifier"])
        self.assertIn("tests/review_fix_package.md", data["files"])
        self.assertTrue((self.repo / "tests" / "artifact_migrations.jsonl").is_file())
        self.assertEqual(0, self.check().returncode)

    def test_unclassified_review_is_reported_but_not_capped(self):
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/review_fix_package.md", "x" * 100)
        report = self.cli("budget", "--format", "json")
        self.assertEqual(0, report.returncode, report.stderr)
        data = json.loads(report.stdout)
        self.assertEqual(["tests/review_fix_package.md"],
                         [x["path"] for x in data["unclassified_review"]])
        self.assertEqual(0, self.check().returncode)

    def test_prune_ignores_machine_archive_copy(self):
        put(self.repo, "tests/review_package.md", "x" * (600 * 1024))
        self.assertEqual(0, self.init().returncode)
        archive = self.repo / ".vibeweaver" / "artifacts" / "review"
        archive.mkdir(parents=True)
        shutil.copy(self.repo / "tests" / "review_package.md", archive / "copy.md")
        (self.repo / "tests" / "review_package.md").unlink()
        result = self.cli("prune", "--path", "tests/review_package.md")
        self.assertEqual(0, result.returncode)

    def test_assume_unchanged_baseline_is_rejected(self):
        self.assertEqual(0, self.init().returncode)
        git(self.repo, "update-index", "--assume-unchanged", BASELINE)
        data = self.baseline()
        data["groups"]["review"]["ceiling"] = 10 ** 12
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.cli("check", "--final")
        self.assertEqual(2, result.returncode)
        out = (result.stdout + result.stderr).lower()
        self.assertTrue("assume-unchanged" in out or "differs from head" in out)

    def test_auto_base_rejects_committed_ceiling_raise(self):
        self.assertEqual(0, self.init().returncode)
        data = self.baseline()
        data["groups"]["review"]["ceiling"] = 10 ** 12
        (self.repo / BASELINE).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(1, result.returncode)
        self.assertIn("raised", (result.stdout + result.stderr).lower())

    def test_final_requires_tracked_baseline(self):
        self.assertEqual(0, self.init().returncode)
        (self.repo / BASELINE).unlink()
        (self.repo / BASELINE).write_text(json.dumps({
            "version": 1,
            "groups": {g: {"per_file": 1, "total": 1, "ceiling": 1000000} for g in
                       ("review", "logs", "trajectory", "media")},
            "files": {},
        }), encoding="utf-8")
        result = self.cli("check", "--final")
        self.assertEqual(2, result.returncode)
        self.assertIn("before --final", (result.stdout + result.stderr).lower())

    def test_uppercase_log_and_gif_are_capped(self):
        self.assertEqual(0, self.init().returncode)
        put(self.repo, "tests/BIG.LOG", "x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(1, self.check().returncode)
        put(self.repo, "tests/BIG.LOG", "x")
        put(self.repo, "tests/shot.GIF", "x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(1, self.check().returncode)

    def test_adopt_optional_final_without_baseline_passes(self):
        early = self.cli("check", "--final", "--adopt-optional")
        self.assertEqual(0, early.returncode, early.stderr)
        self.assertIn("not adopted", (early.stdout + early.stderr).lower())
        self.assertEqual(2, self.cli("check", "--final").returncode)

    def test_no_baseline_nonfinal_warns_final_fails_closed(self):
        put(self.repo, "tests/review_package.md", "x")
        early = self.cli("check")
        self.assertEqual(0, early.returncode, early.stderr)
        self.assertIn("no baseline", (early.stdout + early.stderr).lower())
        self.assertEqual(2, self.check().returncode)

    def test_make_review_package_caps_and_indexes_large_diff(self):
        base = git(self.repo, "rev-parse", "HEAD")
        put(self.repo, "big.txt", "line\n" * 2000)
        commit(self.repo, ["big.txt"], "big change")
        head = git(self.repo, "rev-parse", "HEAD")
        scripts = self.repo / "scripts"
        scripts.mkdir()
        shutil.copy(PAYLOAD / "scripts" / "artifact_budget.py", scripts / "artifact_budget.py")
        shutil.copy(PAYLOAD / "scripts" / "git_trust.py", scripts / "git_trust.py")
        shutil.copy(PAYLOAD / "scripts" / "make_review_package.sh", scripts / "make_review_package.sh")
        result = subprocess.run(
            ["bash", str(scripts / "make_review_package.sh"), base, head,
             "tests/review_package.md", "--max-bytes", "2000"],
            cwd=self.repo, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        index = (self.repo / "tests" / "review_package.md").read_text(encoding="utf-8")
        self.assertIn("Review package index", index)
        self.assertIn("sha256", index.lower())
        archives = list((self.repo / ".vibeweaver" / "artifacts" / "review").iterdir())
        self.assertEqual(1, len(archives))


if __name__ == "__main__":
    unittest.main()
