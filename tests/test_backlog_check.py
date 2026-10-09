"""Unit tests for vibeweaver/scripts/backlog_check.py (C8 outer-loop ledger gate)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "vibeweaver" / "scripts" / "backlog_check.py"


def run(root):
    return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)


class BacklogCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        (self.root / rel).write_text(text, encoding="utf-8")

    def test_inert_without_backlog(self):
        r = run(self.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("inert", r.stdout)

    def test_invalid_json_fails(self):
        self.write("tests/backlog.json", "{not json")
        r = run(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not valid JSON", r.stdout)

    def test_missing_userStories_fails(self):
        self.write("tests/backlog.json", json.dumps({"nope": []}))
        r = run(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("userStories", r.stdout)

    def test_missing_required_key_fails(self):
        self.write("tests/backlog.json", json.dumps({"userStories": [{"id": "US-1", "passes": False}]}))
        r = run(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("title", r.stdout)

    def test_passes_non_boolean_fails(self):
        self.write(
            "tests/backlog.json",
            json.dumps({"userStories": [{"id": "US-1", "title": "t", "priority": 1, "passes": "yes"}]}),
        )
        r = run(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("boolean", r.stdout)

    def test_pass_true_without_evidence_fails(self):
        self.write(
            "tests/backlog.json",
            json.dumps({"userStories": [{"id": "US-1", "title": "t", "priority": 1, "passes": True}]}),
        )
        self.write("tests/verification_log.md", "## Task\n- iter 1 PASS: something else\n")
        r = run(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("US-1", r.stdout)
        self.assertIn("COV-1", r.stdout)

    def test_pass_true_with_evidence_passes(self):
        self.write(
            "tests/backlog.json",
            json.dumps({"userStories": [{"id": "US-1", "title": "t", "priority": 1, "passes": True}]}),
        )
        self.write("tests/progress.txt", "- US-1 done, tests green\n")
        r = run(self.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("clean", r.stdout)

    def test_pass_false_needs_no_evidence(self):
        self.write(
            "tests/backlog.json",
            json.dumps({"userStories": [{"id": "US-9", "title": "t", "priority": 2, "passes": False}]}),
        )
        r = run(self.root)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
