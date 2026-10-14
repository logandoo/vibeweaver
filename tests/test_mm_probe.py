"""Unit tests for vibeweaver/scripts/mm_probe.py (incl. the comparative sub-probe)."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "vibeweaver" / "scripts" / "mm_probe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mm_probe_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


class Selftest(unittest.TestCase):
    def test_selftest_passes(self):
        r = run("--selftest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("selftest PASS", r.stdout)


class ComparativeProbe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.mod = load_module()

    def tearDown(self):
        self.tmp.cleanup()

    def _solution(self):
        gt = json.loads((self.dir / "probe_compare.expected").read_text())
        solved = [(v, s) for v in self.mod.COMPARE_VARIANTS
                  for s in self.mod.COMPARE_SHAPES
                  if self.mod._compare_verify(gt, v, s)]
        self.assertEqual(len(solved), 1, solved)
        return solved[0], gt

    def test_generate_then_unique_solution_without_plaintext(self):
        path = self.mod.generate_compare(str(self.dir))
        self.assertTrue(pathlib.Path(path).exists())
        _solved, gt = self._solution()
        self.assertEqual(set(gt.keys()),
                         {"v", "salt", "variant_hash", "shape_hash"})
        # no exact JSON value equals a variant/shape name (substring checks
        # would flake on hex hashes — "added" is a valid hex substring)
        for name in self.mod.COMPARE_VARIANTS + self.mod.COMPARE_SHAPES:
            self.assertNotIn(name, gt.values())

    def test_check_exit_codes(self):
        self.mod.generate_compare(str(self.dir))
        solved, _gt = self._solution()
        r = run("--compare-check", solved[0], solved[1], "--dir", str(self.dir))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        other_shape = next(s for s in self.mod.COMPARE_SHAPES
                           if s != solved[1])
        r = run("--compare-check", solved[0], other_shape, "--dir", str(self.dir))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)   # shape field
        other_variant = next(v for v in self.mod.COMPARE_VARIANTS
                             if v != solved[0])
        r = run("--compare-check", other_variant, solved[1], "--dir", str(self.dir))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)   # variant field
        r = run("--compare-check", "frobnicate", "circle", "--dir", str(self.dir))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_corrupt_expected_exits_2(self):
        self.mod.generate_compare(str(self.dir))
        (self.dir / "probe_compare.expected").write_text("{not json")
        r = run("--compare-check", "moved", "circle", "--dir", str(self.dir))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_flag_combo_rejected(self):
        r = run("--selftest", "--compare-generate")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_scene_semantics_per_variant(self):
        """Render-vs-claim: sampled pixels must match the declared change and
        every diff pixel must lie inside the declared change rects."""
        for variant in self.mod.COMPARE_VARIANTS:
            scene_a, scene_b, meta, info = self.mod._compare_scenes(
                variant=variant, rng=__import__("random").Random(7))
            for sx, sy, expected in info["samples"]:
                self.assertEqual(scene_b[sy][sx], expected,
                                 (variant, sx, sy))
            for yy in range(len(scene_a)):
                for xx in range(len(scene_a[0])):
                    if scene_a[yy][xx] != scene_b[yy][xx]:
                        self.assertTrue(
                            any(rx <= xx < rx + rw and ry <= yy < ry + rh
                                for rx, ry, rw, rh in info["changed"]),
                            (variant, xx, yy))

    def test_all_variants_render_with_visible_diff(self):
        for variant in self.mod.COMPARE_VARIANTS:
            png, meta = self.mod.render_compare(variant=variant)
            self.assertTrue(png.startswith(b"\x89PNG"), variant)
            self.assertEqual(meta["variant"], variant)
            self.assertGreaterEqual(meta["diff_pixels"], 80, variant)


if __name__ == "__main__":
    unittest.main()
