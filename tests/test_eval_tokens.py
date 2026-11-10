#!/usr/bin/env python3
"""Tests for scripts/eval_tokens.py and scripts/eval_token_report.py.

cost.json `tokens` was null in every lab run although each trajectory carries
opencode's `step_finish` events with per-step token counts. These tests pin the
parser (sum, unknown-vs-zero, junk tolerance), the family classifier, the
report aggregation and the idempotent backfill.

Run: python3 -m unittest tests.test_eval_tokens
"""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import eval_tokens  # noqa: E402
import eval_token_report  # noqa: E402


def step(inp, out, reasoning=0, cache_read=0, cache_write=0, cost=0):
    return json.dumps({
        "type": "step_finish", "timestamp": 1, "sessionID": "s",
        "part": {"type": "step-finish", "reason": "tool-calls", "cost": cost,
                 "tokens": {"input": inp, "output": out, "reasoning": reasoning,
                            "cache": {"read": cache_read, "write": cache_write}}}})


STDOUT = "\n".join([
    '{"type":"text","part":{"text":"hello"}}',
    step(100, 20, reasoning=5, cache_read=7, cache_write=3, cost=0.5),
    "not json at all",
    '{"type":"step_finish","part":{"tokens":"garbage"}}',
    step(50, 10, cost=0.25),
])


class TestSummarize(unittest.TestCase):
    def test_sums_step_finish_events(self):
        t = eval_tokens.summarize_tokens(STDOUT)
        self.assertEqual(t["steps"], 2)
        self.assertEqual(t["input"], 150)
        self.assertEqual(t["output"], 30)
        self.assertEqual(t["reasoning"], 5)
        self.assertEqual(t["cache_read"], 7)
        self.assertEqual(t["cache_write"], 3)
        self.assertEqual(t["total"], 150 + 30 + 5 + 7 + 3)
        self.assertAlmostEqual(t["cost"], 0.75)

    def test_no_events_is_unknown_not_zero(self):
        self.assertIsNone(eval_tokens.summarize_tokens(""))
        self.assertIsNone(eval_tokens.summarize_tokens(None))
        self.assertIsNone(eval_tokens.summarize_tokens('{"type":"text"}\nplain'))

    def test_prose_mention_is_not_an_event(self):
        # a model quoting the event name in text must not count
        self.assertIsNone(eval_tokens.summarize_tokens(
            '{"type":"text","part":{"text":"saw step_finish tokens input 5"}}'))


class TestFamily(unittest.TestCase):
    def test_family(self):
        self.assertEqual(eval_token_report.family("g3_comp_refund"), "compliance")
        self.assertEqual(eval_token_report.family("g3_teeth_redfirst_bill"), "teeth")
        self.assertEqual(eval_token_report.family("g3_csv_roundtrip"), "capability")


def make_run(root, name, arm, model, stdout, verdict, wall=10.0, tokens=None):
    d = root / "campaign" / name
    d.mkdir(parents=True)
    (d / "trajectory.json").write_text(json.dumps(
        {"scenario": name.split("__")[0], "agent": {"exit": 0, "stdout": stdout}}),
        encoding="utf-8")
    (d / "cost.json").write_text(json.dumps(
        {"wall_seconds": wall, "model": model, "arm": arm, "seed": 0,
         "tokens": tokens, "keep_me": [1, 2]}, indent=2), encoding="utf-8")
    (d / "verdict.json").write_text(json.dumps({"verdict": verdict}), encoding="utf-8")
    return d


class TestReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        make_run(self.root, "g3_csv__bare__s0", "bare", "m", step(10, 1), "pass")
        make_run(self.root, "g3_csv__bare__s1", "bare", "m", step(30, 3), "fail")
        make_run(self.root, "g3_csv__full_deployed__s0", "full_deployed", "m",
                 "\n".join([step(1000, 10), step(2000, 20)]), "pass", wall=99.0)
        make_run(self.root, "g3_csv__full_forced__s0", "full_forced", "m", "",
                 "indeterminate")  # timed out: no transcript

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_and_aggregate(self):
        rows = eval_token_report.collect(self.root)
        self.assertEqual(len(rows), 4)
        groups = eval_token_report.aggregate(rows)
        bare = groups[("m", "bare", "capability")]
        self.assertEqual(bare["n"], 2)
        self.assertEqual(bare["no_tokens"], 0)
        self.assertEqual(bare["median_total"], 22)   # median of 11 and 33
        self.assertEqual(bare["pass"], 1)
        self.assertEqual(bare["fail"], 1)
        full = groups[("m", "full_deployed", "capability")]
        self.assertEqual(full["median_total"], 3030)
        self.assertEqual(full["median_steps"], 2)
        forced = groups[("m", "full_forced", "capability")]
        self.assertEqual(forced["no_tokens"], 1)
        self.assertIsNone(forced["median_total"])
        self.assertEqual(forced["indeterminate"], 1)

    def test_markdown_renders_every_group(self):
        md = eval_token_report.render_markdown(
            eval_token_report.aggregate(eval_token_report.collect(self.root)))
        self.assertIn("full_deployed", md)
        self.assertIn("| m | bare | capability | 2 | 0 |", md)

    def test_backfill_is_idempotent_and_preserves_keys(self):
        n1 = eval_token_report.backfill(self.root)
        self.assertEqual(n1, 3)   # the timed-out run has no events: left null
        p = self.root / "campaign" / "g3_csv__bare__s0" / "cost.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(d["tokens"]["total"], 11)
        self.assertEqual(d["keep_me"], [1, 2])
        before = p.read_text(encoding="utf-8")
        n2 = eval_token_report.backfill(self.root)
        self.assertEqual(n2, 0)
        self.assertEqual(p.read_text(encoding="utf-8"), before)
        forced = json.loads((self.root / "campaign" / "g3_csv__full_forced__s0"
                             / "cost.json").read_text(encoding="utf-8"))
        self.assertIsNone(forced["tokens"])


if __name__ == "__main__":
    unittest.main()
