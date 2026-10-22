#!/usr/bin/env python3
"""Release manifest contract (PLAN W0 Task 1).

Pure-function tests over a temporary bundle tree:
  make_manifest(root, tag, commit) -> dict
  verify_manifest(root, manifest) -> list[str]

Failure classes pinned here: missing file, extra file, hash mismatch,
bytes mismatch, duplicate path, bad schema, malformed digest.
"""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "scripts") if (ROOT / "scripts" / "make_release_manifest.py").is_file() else (ROOT / "vibeweaver" / "scripts")))

from make_release_manifest import make_manifest, payload_files  # noqa: E402
from verify_release import verify_manifest  # noqa: E402


class ReleaseManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-manifest-"))
        self.root = self.tmp / "bundle"
        payload = self.root / "vibeweaver"
        (payload / "scripts").mkdir(parents=True)
        (payload / "vibeweaver-mini").mkdir(parents=True)
        (payload / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        (payload / "REFERENCE.md").write_text("# ref\n", encoding="utf-8")
        (payload / "vibeweaver-gate.js").write_text("export default {}\n", encoding="utf-8")
        (payload / "install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (payload / "scripts" / "assert_artifacts.py").write_text("print(1)\n", encoding="utf-8")
        (payload / "vibeweaver-mini" / "SKILL.md").write_text("mini\n", encoding="utf-8")
        # excluded trees must never enter the manifest
        (payload / "tests").mkdir()
        (payload / "tests" / "acceptance.md").write_text("evidence\n", encoding="utf-8")
        (payload / "memory").mkdir()
        (payload / "memory" / "MEMORY.md").write_text("memory\n", encoding="utf-8")
        (payload / "scripts" / "__pycache__").mkdir()
        (payload / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
        self.manifest = make_manifest(self.root, "w18.2", "deadbeef")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_manifest_shape_and_deterministic_order(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["tag"], "w18.2")
        self.assertEqual(self.manifest["commit"], "deadbeef")
        paths = [f["path"] for f in self.manifest["files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertIn("vibeweaver/SKILL.md", paths)
        self.assertIn("vibeweaver/scripts/assert_artifacts.py", paths)
        self.assertNotIn("vibeweaver/tests/acceptance.md", paths)
        self.assertNotIn("vibeweaver/memory/MEMORY.md", paths)
        self.assertFalse(any("__pycache__" in p for p in paths))

    def test_clean_tree_verifies(self):
        self.assertEqual(verify_manifest(self.root, self.manifest), [])

    def test_missing_file_fails(self):
        (self.root / "vibeweaver" / "REFERENCE.md").unlink()
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("missing" in e and "REFERENCE.md" in e for e in errors), errors)

    def test_extra_file_fails(self):
        (self.root / "vibeweaver" / "scripts" / "SNEAK.py").write_text("extra\n", encoding="utf-8")
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("extra" in e and "SNEAK.py" in e for e in errors), errors)

    def test_hash_mismatch_fails(self):
        p = self.root / "vibeweaver" / "SKILL.md"
        p.write_text("# skilL\n", encoding="utf-8")  # same byte count, different digest
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("sha256" in e and "SKILL.md" in e for e in errors), errors)

    def test_bytes_mismatch_fails(self):
        entry = next(f for f in self.manifest["files"] if f["path"] == "vibeweaver/REFERENCE.md")
        entry["bytes"] = entry["bytes"] + 1
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("bytes" in e and "REFERENCE.md" in e for e in errors), errors)

    def test_duplicate_path_fails(self):
        self.manifest["files"].append(dict(self.manifest["files"][0]))
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("duplicate" in e for e in errors), errors)

    def test_bad_schema_fails(self):
        bad = dict(self.manifest)
        bad["schema_version"] = 999
        errors = verify_manifest(self.root, bad)
        self.assertTrue(any("schema_version" in e for e in errors), errors)

    def test_malformed_digest_fails(self):
        self.manifest["files"][0]["sha256"] = "not-a-digest"
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("sha256" in e for e in errors), errors)

    def test_path_traversal_rejected(self):
        self.manifest["files"].append({"path": "../escape.txt", "sha256": "0" * 64, "bytes": 1})
        errors = verify_manifest(self.root, self.manifest)
        self.assertTrue(any("unsafe path" in e for e in errors), errors)

    def test_payload_files_dev_layout(self):
        # Dev tree has the payload at the root (no vibeweaver/ nesting).
        dev = self.tmp / "dev"
        dev.mkdir()
        (dev / "SKILL.md").write_text("# dev\n", encoding="utf-8")
        (dev / "scripts").mkdir()
        (dev / "scripts" / "assert_artifacts.py").write_text("print(2)\n", encoding="utf-8")
        rels = payload_files(dev)
        self.assertIn("SKILL.md", rels)
        self.assertIn("scripts/assert_artifacts.py", rels)


if __name__ == "__main__":
    unittest.main()
