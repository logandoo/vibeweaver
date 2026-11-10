#!/usr/bin/env python3
"""verify_skill.py check 11 — the contract_lint size/token caps are wired in.

Copies the package (verify_skill.py + vibeweaver/ + vibeweaver-mini/) to a
temp dir, pushes the always-resident contract past its 90k-token cap, and
expects verify_skill.py to fail naming the budget.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent


class VerifySkillBudgetTest(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="vw-budget-"))
        shutil.copy(REPO / "verify_skill.py", self.d / "verify_skill.py")
        ignore = shutil.ignore_patterns("__pycache__")
        for sub in ("vibeweaver", "vibeweaver-mini"):
            shutil.copytree(REPO / sub, self.d / sub, ignore=ignore)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def verify(self):
        return subprocess.run([sys.executable, "verify_skill.py"], cwd=self.d,
                              capture_output=True, text=True, timeout=120)

    def test_current_tree_within_budget(self):
        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("full contract", r.stdout)

    def test_growth_past_full_cap_fails(self):
        # +~10k tokens across three companions: the always-resident total
        # crosses 90k (two files also cross their 45 KB cap — either way the
        # budget must fail; the assertion pins the 90k message).
        for name in ("REFERENCE.md", "APPENDIX.md", "TESTING_PROTOCOLS.md"):
            with open(self.d / "vibeweaver" / name, "a", encoding="utf-8") as f:
                f.write("\npadding " * 1500 + "\n")
        r = self.verify()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("size budget", r.stdout)
        self.assertIn("cap 90000", r.stdout)


if __name__ == "__main__":
    unittest.main()
