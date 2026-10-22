#!/usr/bin/env python3
"""W1 Task 11 — claims registry fixtures."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = [sys.executable, str(ROOT / "scripts" / "check_claims.py")]


class ClaimsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-claims-"))
        (self.tmp / "release").mkdir()
        (self.tmp / "README.md").write_text("# x\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self):
        return subprocess.run(CLI + ["--root", str(self.tmp)], capture_output=True, text=True)

    def test_unbound_count_fails(self):
        (self.tmp / "README.md").write_text("score 70/71\n", encoding="utf-8")
        (self.tmp / "release" / "claims.json").write_text(json.dumps({"claims": []}), encoding="utf-8")
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("70/71", r.stdout)

    def test_effect_without_power_fields_fails(self):
        (self.tmp / "README.md").write_text("improved +251%\n", encoding="utf-8")
        (self.tmp / "release" / "claims.json").write_text(json.dumps({"claims": [
            {"id": "C1", "token": "+251%", "claim": "x", "n": None, "seeds": None, "ci": None}
        ]}), encoding="utf-8")
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing n/seeds/ci", r.stdout)

    def test_bound_claim_passes(self):
        (self.tmp / "README.md").write_text("improved +251%\n", encoding="utf-8")
        (self.tmp / "release" / "claims.json").write_text(json.dumps({"claims": [
            {"id": "C1", "token": "+251%", "claim": "x", "n": 16, "seeds": 1, "ci": "directional"}
        ]}), encoding="utf-8")
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 unbound", r.stdout)


if __name__ == "__main__":
    unittest.main()
