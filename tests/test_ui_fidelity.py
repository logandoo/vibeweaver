"""Unit tests for vibeweaver/scripts/ui_fidelity.py (design-copy fidelity, §A4.1.2)."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "vibeweaver" / "scripts" / "ui_fidelity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ui_fidelity_under_test", SCRIPT)
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


class Diff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.mod = load_module()
        self.w, self.h = 30, 10
        base = bytearray()
        for _ in range(self.w * self.h):
            base += bytes((180, 180, 180, 255))
        self.base = bytes(base)
        cand = bytearray(base)
        for y in range(2, 5):        # 4x3 black block at x=3,y=2
            for x in range(3, 7):
                o = (y * self.w + x) * 4
                cand[o:o + 4] = bytes((0, 0, 0, 255))
        self.ref_png = self.dir / "ref.png"
        self.cand_png = self.dir / "cand.png"
        self.mod.write_png(str(self.ref_png), self.w, self.h, self.base)
        self.mod.write_png(str(self.cand_png), self.w, self.h, bytes(cand))

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_passes(self):
        r = run("diff", str(self.ref_png), str(self.ref_png),
                "--out", str(self.dir), "--name", "same")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_block_change_fails_with_cluster(self):
        r = run("diff", str(self.ref_png), str(self.cand_png),
                "--out", str(self.dir), "--name", "blk",
                "--max-diff-percent", "0.1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        report = json.loads((self.dir / "ui-diff-blk.json").read_text())
        self.assertEqual(report["diff_pixels"], 12)
        self.assertEqual(len(report["clusters"]), 1)
        c = report["clusters"][0]
        self.assertEqual((c["x"], c["y"], c["w"], c["h"]), (3, 2, 4, 3))
        self.assertTrue((self.dir / "ui-diff-blk.png").exists())

    def test_size_mismatch_refused(self):
        small = self.dir / "small.png"
        self.mod.write_png(str(small), self.w, 5, self.base[: self.w * 5 * 4])
        r = run("diff", str(self.ref_png), str(small),
                "--out", str(self.dir), "--name", "dim")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_allow_dim_mismatch_still_fails_but_reports(self):
        small = self.dir / "small.png"
        self.mod.write_png(str(small), self.w, 5, self.base[: self.w * 5 * 4])
        r = run("diff", str(self.ref_png), str(small),
                "--out", str(self.dir), "--name", "dim2", "--allow-dim-mismatch")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        report = json.loads((self.dir / "ui-diff-dim2.json").read_text())
        self.assertTrue(report["dimensions"]["mismatch"])
        self.assertEqual(report["diff_pixels"], 0)   # crop rows are identical


class Boxes(unittest.TestCase):
    def test_flags_pass_and_overlap_rules(self):
        mod = load_module()
        ref = [{"name": "a", "x": 0, "y": 0, "w": 10, "h": 10},
               {"name": "b", "x": 12, "y": 0, "w": 10, "h": 10}]
        cand = [{"name": "a", "x": 3, "y": 0, "w": 10, "h": 10,
                 "occluded_by": [".x"]},
                {"name": "b", "x": 12, "y": 0, "w": 10, "h": 10}]
        rep = mod.boxes_report(ref, cand, 2)
        st = {e["name"]: e["status"] for e in rep["elements"]}
        self.assertEqual(st["a"], "moved+occluded")
        self.assertFalse(rep["pass"])
        self.assertTrue(mod.boxes_report(ref, ref, 2)["pass"])

        # sibling intersection flagged; parent/child containment is not
        sib = [{"name": "x", "x": 0, "y": 0, "w": 10, "h": 10},
               {"name": "y", "x": 5, "y": 5, "w": 10, "h": 10}]
        rep2 = mod.boxes_report(sib, sib, 2)
        self.assertEqual(len(rep2["overlaps"]), 1)
        nested = [{"name": "x", "x": 0, "y": 0, "w": 10, "h": 10},
                  {"name": "z", "x": 2, "y": 2, "w": 3, "h": 3}]
        rep3 = mod.boxes_report(nested, nested, 2)
        self.assertEqual(len(rep3["overlaps"]), 0)
        self.assertTrue(rep3["pass"])


FIX = ROOT / "tests" / "fixtures" / "uif_fidelity"


class DifferentialVsUpstream(unittest.TestCase):
    """Pinned against pixelmatch@5.3.0 (node + pngjs) run on the identical
    fixture PNGs — exercises the anti-aliasing path and the chromatic (i/q)
    channels with real numbers, so a broken AA/i/q implementation cannot
    pass the suite. Pinned 2026-10-14: aa=(0,84), chroma=(144,0), mixed=(12,84)."""

    def _diff(self, ref, cand):
        mod = load_module()
        w1, h1, img1 = mod.read_png(str(FIX / ref))
        w2, h2, img2 = mod.read_png(str(FIX / cand))
        self.assertEqual((w1, h1), (w2, h2))
        d, _out, aa, _pts = mod.diff_images(img1, img2, w1, h1,
                                            threshold=0.1, include_aa=False,
                                            draw=False)
        return d, aa

    def test_aa_pair_matches_upstream(self):
        self.assertEqual(self._diff("aa_ref.png", "aa_cand.png"), (0, 84))

    def test_chroma_pair_matches_upstream(self):
        self.assertEqual(self._diff("chroma_ref.png", "chroma_cand.png"), (144, 0))

    def test_mixed_pair_matches_upstream(self):
        self.assertEqual(self._diff("mixed_ref.png", "mixed_cand.png"), (12, 84))


class ExitCodes(unittest.TestCase):
    def test_missing_file_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            r = run("diff", "/nonexistent/ref.png", "/nonexistent/cand.png",
                    "--out", td)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_bad_threshold_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            mod = load_module()
            p = pathlib.Path(td) / "x.png"
            mod.write_png(str(p), 4, 4, bytes((9, 9, 9, 255)) * 16)
            r = run("diff", str(p), str(p), "--out", td, "--threshold", "1.5")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_malformed_boxes_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            bad = pathlib.Path(td) / "bad.json"
            bad.write_text('[{"x": 0}]', encoding="utf-8")
            good = pathlib.Path(td) / "good.json"
            good.write_text("[]", encoding="utf-8")
            r = run("boxes", str(bad), str(good), "--out", td)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


class RefBoxes(unittest.TestCase):
    def _write_two_rect_image(self, mod, td):
        w, h = 64, 40
        img = bytearray()
        for y in range(h):
            for x in range(w):
                c = (240, 240, 240)
                if 8 <= x < 28 and 6 <= y < 18:
                    c = (200, 60, 60)
                if 40 <= x < 56 and 20 <= y < 30:
                    c = (60, 60, 200)
                img += bytes(c) + b"\xff"
        p = pathlib.Path(td) / "ref.png"
        mod.write_png(str(p), w, h, bytes(img))
        return p

    def test_cli_extracts_regions_with_preview(self):
        with tempfile.TemporaryDirectory() as td:
            mod = load_module()
            p = self._write_two_rect_image(mod, td)
            r = run("refboxes", str(p), "--out", td, "--name", "t")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            regions = json.loads(
                (pathlib.Path(td) / "ui-refboxes-t.json").read_text())
            self.assertEqual([(x["x"], x["y"], x["w"], x["h"]) for x in regions],
                             [(8, 6, 20, 12), (40, 20, 16, 10)])
            self.assertTrue((pathlib.Path(td) / "ui-refboxes-t.png").exists())

    def test_bad_bg_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            mod = load_module()
            p = self._write_two_rect_image(mod, td)
            r = run("refboxes", str(p), "--out", td, "--bg", "zz")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
