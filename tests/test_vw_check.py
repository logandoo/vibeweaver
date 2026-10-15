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


def run(cwd, *extra):
    return subprocess.run([sys.executable, str(CHECKER), *extra], cwd=cwd,
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

    def test_no_bypass_hint_requires_reason(self):
        """W5-F: the 'delete the hash file' bypass recipe is gone from the
        model-visible output — a test change demands a `- test-change:` reason."""
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            f = d / "test_api.py"
            f.write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            f.write_text("def test_ok():\n    assert 2 == 2\n")
            r = run(td)
            self.assertEqual(r.returncode, 1)
            self.assertIn("TEST SET CHANGED", r.stdout)
            self.assertIn("test-change:", r.stdout)
            self.assertNotIn("delete .vw_test_hashes", r.stdout)
            self.assertNotIn("delete the hash", r.stdout.lower())

    def test_test_change_flag_rebaselines(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            f = d / "test_api.py"
            f.write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            f.write_text("def test_ok():\n    assert 1 == 1  # reviewed\n")
            r = run(td, "--test-change", "spelling-only edit reviewed by A4.9")
            self.assertEqual(r.returncode, 0, r.stdout[-300:])
            self.assertIn("re-baselined under justification", r.stdout)

    def test_stall_and_cap_declarations(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            (d / "test_api.py").write_text("def test_ok():\n    assert 1 == 2\n")
            outs = []
            for _ in range(5):
                outs.append(run(td).stdout)
            self.assertIn("- stall:", outs[2])   # 3rd identical failure
            self.assertIn("- cap-hit:", outs[4])  # 5th run
            self.assertIn("cap=5", outs[4])

    def test_hash_record_deletion_is_not_a_rebaseline(self):
        """Review R-C2: deleting .vw_test_hashes.json must not silently
        re-baseline a weakened suite (the bypass recipe stays dead)."""
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            f = d / "test_api.py"
            f.write_text("def test_ok():\n    assert 1 == 1\n")
            self.assertEqual(run(td).returncode, 0)
            f.write_text("def test_ok():\n    assert 1 == 1  # weakened\n")
            (d / ".vw_test_hashes.json").unlink()
            r = run(td)
            self.assertEqual(r.returncode, 1, r.stdout[-300:])
            self.assertIn("HASH RECORD MISSING", r.stdout)
            r2 = run(td, "--test-change", "reviewed spelling-only edit")
            self.assertEqual(r2.returncode, 0, r2.stdout[-300:])

    def test_check_sh_prints_completion_flag(self):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            (d / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
            # installed COV-2 layout: script/check.sh + scripts/vw_check.py
            (d / "script").mkdir()
            (d / "scripts").mkdir()
            (d / "script" / "check.sh").write_text((CHECKER.parent / "check.sh").read_text())
            (d / "scripts" / "vw_check.py").write_text(CHECKER.read_text())
            r = subprocess.run(["sh", str(d / "script" / "check.sh")], cwd=td,
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stdout[-300:])
            self.assertIn("ALL CHECKS PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
