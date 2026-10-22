#!/usr/bin/env python3
"""W0 Task 3/8 — contract lint fixtures."""
import importlib.util
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vw_contract_lint", (ROOT / "scripts" / "contract_lint.py") if (ROOT / "scripts" / "contract_lint.py").is_file() else (ROOT / "vibeweaver" / "scripts" / "contract_lint.py"))
lint_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint_mod)


def build_tree(tmp):
    pay = tmp / "vibeweaver"
    pay.mkdir(parents=True)
    lines = ["`COV-0. Delivery contract` — artifacts on disk.",
             "Precedence: COV-0 > the artifacts pointer below > COV-9.", ""]
    for n in range(1, 14):
        lines.append("`COV-%d. Rule %d` — text." % (n, n))
    (pay / "SKILL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in lint_mod.COMPANIONS:
        (pay / name).write_text("# %s\n" % name, encoding="utf-8")
    (pay / "bootstrap.md").write_text("# bootstrap\n", encoding="utf-8")
    (tmp / "profiles" / "core").mkdir(parents=True)
    (tmp / "profiles" / "core" / "SKILL.md").write_text("# core\n`COV-0` .. `COV-13`\n", encoding="utf-8")
    return pay


class ContractLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-lint-"))
        self.pay = build_tree(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def errors(self):
        return lint_mod.lint(self.tmp)[0]

    def test_clean_contract(self):
        self.assertEqual(self.errors(), [])

    def test_duplicate_cov0_fails(self):
        p = self.pay / "SKILL.md"
        p.write_text(p.read_text(encoding="utf-8") + "`COV-0. duplicate` — x.\n", encoding="utf-8")
        self.assertTrue(any("COV-0" in e for e in self.errors()), self.errors())

    def test_missing_cov_fails(self):
        p = self.pay / "SKILL.md"
        p.write_text(p.read_text(encoding="utf-8").replace("`COV-7. Rule 7` — text.\n", ""), encoding="utf-8")
        self.assertTrue(any("COV numbering" in e for e in self.errors()), self.errors())

    def test_precedence_missing_fails(self):
        p = self.pay / "SKILL.md"
        p.write_text(p.read_text(encoding="utf-8").replace("Precedence: COV-0", "Precedence: none"), encoding="utf-8")
        self.assertTrue(any("precedence" in e.lower() for e in self.errors()), self.errors())

    def test_banned_placeholder_fails(self):
        (self.pay / "REFERENCE.md").write_text("We will TBD the endpoint.\n", encoding="utf-8")
        self.assertTrue(any("TBD" in e for e in self.errors()), self.errors())

    def test_legacy_contradiction_fails(self):
        p = self.pay / "SKILL.md"
        p.write_text(p.read_text(encoding="utf-8") + "artifacts on disk and in your final answer; only tests/ counts.\n", encoding="utf-8")
        self.assertTrue(any("legacy" in e for e in self.errors()), self.errors())

    def test_missing_core_profile_fails(self):
        (self.tmp / "profiles" / "core" / "SKILL.md").unlink()
        self.assertTrue(any("profiles/core" in e for e in self.errors()), self.errors())

    def test_skill_size_cap_fails(self):
        (self.pay / "SKILL.md").write_text("x" * 49000, encoding="utf-8")
        self.assertTrue(any("49000" in e for e in self.errors()), self.errors())


if __name__ == "__main__":
    unittest.main()
