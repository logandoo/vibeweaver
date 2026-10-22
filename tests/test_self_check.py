#!/usr/bin/env python3
"""W0 Task 3 — clean-clone structural self-check (no task block required)."""
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vw_assert_mod", (ROOT / "scripts" / "assert_artifacts.py") if (ROOT / "scripts" / "assert_artifacts.py").is_file() else (ROOT / "vibeweaver" / "scripts" / "assert_artifacts.py"))
assert_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assert_mod)


def build_tree(tmp):
    pay = tmp / "vibeweaver"
    (pay / "scripts").mkdir(parents=True)
    for name in assert_mod.PAYLOAD_MD:
        body = "# %s\n\n[ref](REFERENCE.md)\n" % name if name != "REFERENCE.md" else "# REFERENCE\n"
        (pay / name).write_text(body, encoding="utf-8")
    for rel in assert_mod.PAYLOAD_REQUIRED:
        p = pay / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture\n", encoding="utf-8")
    (tmp / "tests").mkdir()
    (tmp / "tests" / "assert_artifacts.py").write_bytes((pay / "scripts" / "assert_artifacts.py").read_bytes())
    for rel in ("tests/gate_trust/run.sh", "tests/gate_trust/cache_invalidation.sh",
                "tests/gate_trust/evidence_integrity/run.sh"):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/sh\n", encoding="utf-8")
    return pay


class SelfCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-selfcheck-"))
        self.pay = build_tree(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_tree_passes_without_task_block(self):
        self.assertEqual(assert_mod.self_check_files(self.tmp), [])

    def test_missing_payload_fails(self):
        (self.pay / "VERIFICATION_UPGRADES.md").unlink()
        errs = assert_mod.self_check_files(self.tmp)
        self.assertTrue(any("VERIFICATION_UPGRADES.md" in e for e in errs), errs)

    def test_broken_link_fails(self):
        (self.pay / "CODING_PRINCIPLES.md").write_text("[dead](NO_SUCH.md)\n", encoding="utf-8")
        errs = assert_mod.self_check_files(self.tmp)
        self.assertTrue(any("broken link" in e and "NO_SUCH.md" in e for e in errs), errs)

    def test_manifest_mismatch_fails(self):
        (self.tmp / "release").mkdir()
        manifest = {"schema_version": 1, "tag": "t", "commit": "c",
                    "files": [{"path": "vibeweaver/SKILL.md", "sha256": "0" * 64, "bytes": 1}]}
        (self.tmp / "release" / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        errs = assert_mod.self_check_files(self.tmp)
        self.assertTrue(any("manifest sha256 mismatch" in e for e in errs), errs)

    def test_canonical_copy_mismatch_fails(self):
        (self.tmp / "tests" / "assert_artifacts.py").write_text("stub\n", encoding="utf-8")
        errs = assert_mod.self_check_files(self.tmp)
        self.assertTrue(any("byte-identical" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
