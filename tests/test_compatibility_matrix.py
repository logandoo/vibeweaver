#!/usr/bin/env python3
"""W1 Task 21 — docs matrix must match the real CI legs."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAY = ROOT / "vibeweaver" if (ROOT / "vibeweaver" / "SKILL.md").is_file() else ROOT


def verify_yml():
    for p in (ROOT / ".github" / "workflows" / "verify.yml",
              ROOT.parent / "vibeweaver-repo" / ".github" / "workflows" / "verify.yml"):
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return ""


class CompatibilityMatrixTest(unittest.TestCase):
    def test_supported_rows_have_ci_legs(self):
        yml = verify_yml()
        self.assertTrue(yml, "verify.yml not found")
        oses = re.findall(r"^\s+os:\s*\[([^\]]+)\]", yml, re.M)
        pys = re.findall(r"^\s+python-version:\s*\[([^\]]+)\]", yml, re.M)
        legs = set()
        for o in oses:
            for oo in [x.strip().strip('"') for x in o.split(",")]:
                for p in pys:
                    for pp in [x.strip().strip('"') for x in p.split(",")]:
                        legs.add((oo.replace("-latest", ""), pp))
        self.assertIn(("ubuntu", "3.9"), legs)
        self.assertIn(("macos", "3.12"), legs)
        self.assertIn(("windows", "3.9"), legs)
        doc = (ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        for osname in ("Linux", "macOS", "Windows"):
            self.assertIn(osname, doc)
        self.assertIn("adapter", doc)
        self.assertNotIn("Node 20 / 22", doc)
        self.assertIn("unsupported", doc)

    def test_actions_are_pinned(self):
        yml = verify_yml()
        for line in yml.splitlines():
            if "uses:" in line and "actions/" in line:
                self.assertRegex(line, r"@[0-9a-f]{40}", line)

    def test_model_class_default_is_core(self):
        boot = (PAY / "bootstrap.md").read_text(encoding="utf-8")
        self.assertIn("VIBEWEAVER_MODEL_CLASS", boot)
        self.assertIn("unknown", boot.lower())
        gate = (PAY / "vibeweaver-gate.js").read_text(encoding="utf-8")
        self.assertIn("VIBEWEAVER_MODEL_CLASS", gate)


if __name__ == "__main__":
    unittest.main()
