#!/usr/bin/env python3
"""Dual verdicts in the lab harness (EVAL_G3_PILOT_REPORT "测量发现" recommendation).

The harness used to skip the hidden test whenever the agent exited non-zero,
conflating process failure with behavioural failure, and a timeout discarded
the agent's whole event stream (transcript, tokens, gate events). These tests
pin the new behaviour:

  * `verdict` keeps its old semantics (no past number moves);
  * `behavioral_verdict` = what the hidden test says about the delivered
    worktree, also when the agent exited non-zero or timed out;
  * `process_verdict` = ok / agent_failed / timed_out / setup_failure;
  * a timed-out run keeps its partial stdout.

Run: python3 -m unittest tests.test_eval_run_grading
"""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import eval_run  # noqa: E402


def fake_agent(exit_code, write_artifact=True, timed_out=False, stdout="partial"):
    def _run(name, work, home, model, agent_kind):
        if write_artifact:
            (work / "hello.txt").write_text("hello\n", encoding="utf-8")
        a = {"exit": exit_code, "stdout": stdout, "stderr": "", "cmd": "fake",
             "seconds": 1.0}
        if timed_out:
            a["timed_out"] = True
        return a
    return _run


class TestDualVerdicts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self.tmp.name) / "run"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, agent_fn):
        # no isolation noise: the fake agent only writes inside its worktree
        with mock.patch.object(eval_run, "run_agent", agent_fn):
            eval_run.main(["--scenario", "smoke", "--agent", "mock",
                           "--out", str(self.out)])
        return json.loads((self.out / "verdict.json").read_text(encoding="utf-8"))

    def test_exit_zero_correct_artifact(self):
        v = self.run_main(fake_agent(0))
        self.assertEqual(v["verdict"], "pass")
        self.assertEqual(v["behavioral_verdict"], "pass")
        self.assertEqual(v["process_verdict"], "ok")

    def test_nonzero_exit_still_graded(self):
        v = self.run_main(fake_agent(1))
        self.assertEqual(v["verdict"], "fail")            # legacy semantics kept
        self.assertEqual(v["behavioral_verdict"], "pass")  # work was delivered
        self.assertEqual(v["process_verdict"], "agent_failed")
        self.assertIsNotNone(v["hidden_test"]["exit"])

    def test_nonzero_exit_without_artifact(self):
        v = self.run_main(fake_agent(1, write_artifact=False))
        self.assertEqual(v["verdict"], "fail")
        self.assertEqual(v["behavioral_verdict"], "fail")

    def test_timeout_graded_and_transcript_kept(self):
        v = self.run_main(fake_agent(-1, timed_out=True, stdout="partial-stream"))
        self.assertEqual(v["verdict"], "indeterminate")   # legacy semantics kept
        self.assertEqual(v["behavioral_verdict"], "pass")
        self.assertEqual(v["process_verdict"], "timed_out")
        traj = json.loads((self.out / "trajectory.json").read_text(encoding="utf-8"))
        self.assertEqual(traj["agent"]["stdout"], "partial-stream")

    def test_setup_failure_not_graded(self):
        def crashed(name, work, home, model, agent_kind):
            raise RuntimeError("could not start")
        v = self.run_main(crashed)
        self.assertEqual(v["verdict"], "indeterminate")
        self.assertEqual(v["behavioral_verdict"], "indeterminate")
        self.assertEqual(v["process_verdict"], "setup_failure")


class TestTimeoutKeepsOutput(unittest.TestCase):
    def test_process_group_timeout_carries_partial_output(self):
        cmd = [sys.executable, "-c",
               "import sys,time; print('early-line'); sys.stdout.flush(); time.sleep(30)"]
        with self.assertRaises(eval_run.ProcessGroupTimeout) as cm:
            eval_run.run_process_group(cmd, cwd=None, env=None, timeout=1)
        self.assertIn("early-line", cm.exception.stdout)

    def test_run_agent_returns_partial_stream_on_timeout(self):
        err = eval_run.ProcessGroupTimeout("killed")
        err.stdout, err.stderr = '{"type":"step_finish"}\n', "e"
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(eval_run, "run_process_group", side_effect=err), \
                mock.patch.object(eval_run, "build_env", return_value={}):
            eval_run.args = mock.Mock(arm="bare")
            a = eval_run.run_agent("smoke", pathlib.Path(d), pathlib.Path(d),
                                   "m", "opencode")
        self.assertEqual(a["exit"], -1)
        self.assertTrue(a["timed_out"])
        self.assertIn("step_finish", a["stdout"])


if __name__ == "__main__":
    unittest.main()
