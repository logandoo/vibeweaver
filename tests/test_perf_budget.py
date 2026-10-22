#!/usr/bin/env python3
"""W1 Task 9.5 — perf budget fixtures."""
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PerfBudgetTest(unittest.TestCase):
    def test_budget_constants(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import perf_budget
        self.assertLessEqual(perf_budget.BUDGETS["scan_45k"], 5.0)
        self.assertLessEqual(perf_budget.BUDGETS["assert"], 10.0)
        self.assertLessEqual(perf_budget.BUDGETS["install"], 6.0)

    def test_quick_check_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "perf_budget.py"),
                            "--check", "--quick"], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PERF PASS", r.stdout)
        self.assertTrue(list((ROOT / "tests" / "perf").glob("perf_*.log")))


if __name__ == "__main__":
    unittest.main()
