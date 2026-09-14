"""Regression tests for the mini kit's deterministic checker.

Runs the checker shipped at vibeweaver-mini/scripts/vw_check.py against
throwaway fixtures. Skipped when pytest is unavailable (the checker runs it).
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

CHECKER = (pathlib.Path(__file__).resolve().parent.parent
           / "vibeweaver-mini" / "scripts" / "vw_check.py")


def run(cwd):
    return subprocess.run([sys.executable, str(CHECKER)], cwd=cwd,
                          capture_output=True, text=True)


@unittest.skipUnless(importlib.util.find_spec("pytest"), "pytest not installed")
class VwCheckTests(unittest.TestCase):
    def test_no_tests_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            r = run(td)
            self.assertEqual(r.returncode, 1)
            self.assertIn("NO TESTS FOUND", r.stdout)

    def test_nested_test_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "tests"
            d.mkdir()
            (d / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
            r = run(td)
            self.assertEqual(r.returncode, 0, r.stdout[-300:])
            self.assertIn("ALL CHECKS PASS", r.stdout)

    def test_modified_test_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "tests"
            d.mkdir()
            f = d / "test_api.py"
            f.write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            f.write_text("def test_ok():\n    assert 2 == 2\n")
            r = run(td)
            self.assertEqual(r.returncode, 1)
            self.assertIn("TEST SET CHANGED", r.stdout)

    def test_added_test_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "tests"
            d.mkdir()
            (d / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            (d / "test_new.py").write_text("def test_new():\n    assert 1 == 1\n")
            r = run(td)
            self.assertEqual(r.returncode, 1)
            self.assertIn("TEST SET CHANGED", r.stdout)

    def test_corrupt_hash_record_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "tests"
            d.mkdir()
            (d / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            (pathlib.Path(td) / ".vw_test_hashes.json").write_text("{bad json")
            r = run(td)
            self.assertEqual(r.returncode, 1)
            self.assertIn("UNREADABLE", r.stdout)


if __name__ == "__main__":
    unittest.main()
