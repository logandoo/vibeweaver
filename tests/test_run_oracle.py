#!/usr/bin/env python3
"""Oracle record — scripts/run_oracle.py + assert_artifacts.py group 1b.

Spec: SKILL.md "Trusted oracle" (only project/external tests certify).
run_oracle.py runs the project's own tests and writes tests/oracle_run.json;
`assert_artifacts.py --final` WARNs — never fails — when the record is
missing, stale (tree_sha != current tree) or red (exit_code != 0).
Black-box: real git fixture projects, scripts run by subprocess.
"""
import ast
import importlib.util
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
PAY = REPO / "vibeweaver" / "scripts"
ORACLE = PAY / "run_oracle.py"
CANON = PAY / "assert_artifacts.py"
VW_CHECK = REPO / "vibeweaver-mini" / "scripts" / "vw_check.py"
HAS_GIT = shutil.which("git") is not None
HAS_PYTEST = importlib.util.find_spec("pytest") is not None
PY = subprocess.list2cmdline([sys.executable]) if os.name == "nt" else shlex.quote(sys.executable)
GREEN_CMD = PY + " -c pass"
RED_CMD = PY + ' -c "raise SystemExit(1)"'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)


def git_init(d):
    run(["git", "init", "-q"], d)
    run(["git", "config", "user.email", "fx@example.invalid"], d)
    run(["git", "config", "user.name", "fx"], d)


def oracle(d, *args):
    return run([sys.executable, str(ORACLE), "--root", str(d), *args], d)


def record(d):
    return json.loads((d / "tests" / "oracle_run.json").read_text(encoding="utf-8"))


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="vw-oracle-test-"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)


class VendoredParityTest(unittest.TestCase):
    """run_oracle vendors vw_check's discovery + hashing: pin the two."""

    def _defs(self, path):
        out = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.FunctionDef):
                if ast.get_docstring(node) is not None:
                    node.body = node.body[1:]
                out[node.name] = ast.dump(node)
        return out

    def test_vendored_functions_match_vw_check(self):
        mine, theirs = self._defs(ORACLE), self._defs(VW_CHECK)
        for fn in ("sha", "clean", "discover", "norm_key", "test_config_files"):
            self.assertEqual(mine[fn], theirs[fn], f"{fn} drifted from vw_check.py")

    def test_payload_and_dev_copies_identical(self):
        self.assertEqual((REPO / "scripts" / "run_oracle.py").read_bytes(), ORACLE.read_bytes())


@unittest.skipUnless(HAS_GIT, "git not available")
class TreeShaContractTest(_Tmp):
    """SHARED CONTRACT: run_oracle.oracle_tree_sha == assert_artifacts.oracle_tree_sha."""

    def test_identical_and_index_untouched(self):
        ro, aa = _load("vw_run_oracle", ORACLE), _load("vw_assert_oracle", CANON)
        git_init(self.d)
        (self.d / "app.py").write_text("x = 1\n")
        run(["git", "add", "app.py"], self.d)
        index = (self.d / ".git" / "index").read_bytes()
        objects = sorted(p.name for p in (self.d / ".git" / "objects").rglob("*"))
        (self.d / "new.py").write_text("y = 2\n")
        a, b = ro.oracle_tree_sha(self.d), aa.oracle_tree_sha(self.d)
        self.assertRegex(a or "", r"^[0-9a-f]{40,64}$")
        self.assertEqual(a, b)
        self.assertEqual((self.d / ".git" / "index").read_bytes(), index, "real index modified")
        self.assertEqual(sorted(p.name for p in (self.d / ".git" / "objects").rglob("*")), objects,
                         "real object store written")
        (self.d / "new.py").write_text("y = 3\n")
        self.assertNotEqual(ro.oracle_tree_sha(self.d), a, "content change must move the tree")
        (self.d / "tests").mkdir()
        (self.d / "tests" / "verification_log.md").write_text("- iter 1 PASS: x\n")
        (self.d / "tests" / "oracle_run.json").write_text("{}")
        self.assertEqual(ro.oracle_tree_sha(self.d), aa.oracle_tree_sha(self.d))

    def test_not_a_git_repo_is_null(self):
        ro, aa = _load("vw_run_oracle2", ORACLE), _load("vw_assert_oracle2", CANON)
        self.assertIsNone(ro.oracle_tree_sha(self.d))
        self.assertIsNone(aa.oracle_tree_sha(self.d))


class RunOracleRecordTest(_Tmp):
    def test_cmd_override_green_and_red(self):
        git_init(self.d) if HAS_GIT else None
        r = oracle(self.d, "--cmd", GREEN_CMD)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = record(self.d)
        self.assertEqual(set(rec), {"schema", "cmd", "exit_code", "tree_sha",
                                    "test_file_hashes", "ts", "duration_s"})
        self.assertEqual((rec["schema"], rec["cmd"], rec["exit_code"]), (1, GREEN_CMD, 0))
        self.assertTrue(rec["ts"].endswith("+00:00"), rec["ts"])
        self.assertIsInstance(rec["duration_s"], float)
        if HAS_GIT:
            self.assertRegex(rec["tree_sha"], r"^[0-9a-f]{40,64}$")
        r = oracle(self.d, "--cmd", RED_CMD)
        self.assertEqual(r.returncode, 1, "exit code must mirror the test command")
        self.assertEqual(record(self.d)["exit_code"], 1)

    def test_not_git_records_null_tree(self):
        r = oracle(self.d, "--cmd", GREEN_CMD)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIsNone(record(self.d)["tree_sha"])

    def test_no_runner_exits_2_without_record(self):
        r = oracle(self.d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("NO TEST RUNNER FOUND", r.stdout)
        self.assertFalse((self.d / "tests" / "oracle_run.json").exists())

    @unittest.skipUnless(HAS_PYTEST, "pytest not importable by this interpreter")
    def test_pytest_discovery_passing_and_failing(self):
        if HAS_GIT:
            git_init(self.d)
        (self.d / "tests").mkdir()
        t = self.d / "tests" / "test_math.py"
        t.write_text("def test_add():\n    assert 1 + 1 == 2\n")
        r = oracle(self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = record(self.d)
        self.assertIn("pytest", rec["cmd"])
        self.assertEqual(rec["exit_code"], 0)
        self.assertIn("tests/test_math.py", rec["test_file_hashes"])
        t.write_text("def test_add():\n    assert 1 + 1 == 3\n")
        r = oracle(self.d)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(record(self.d)["exit_code"], 1)


@unittest.skipUnless(HAS_GIT, "git not available")
class FinalOracleWarnTest(_Tmp):
    """--final group 1b: WARN-only — exit code and PASSES never change."""

    def setUp(self):
        super().setUp()
        d = self.d
        (d / "memory").mkdir()
        (d / "memory" / "MEMORY.md").write_text("# Index\n- [T](topic.md)\n")
        (d / "memory" / "topic.md").write_text("# t\n")
        (d / "script" / "linux").mkdir(parents=True)
        for s in ("start.sh", "stop.sh", "restart.sh", "project_build.sh"):
            p = d / "script" / "linux" / s
            p.write_text("#!/bin/sh\nexit 0\n")
            p.chmod(0o755)
        (d / "tests").mkdir()
        (d / ".gitignore").write_text(".DS_Store\n__pycache__/\n*.pyc\n.venv/\nvenv/\n"
                                      "node_modules/\n.pnpm-store/\ndist/\nbuild/\n.env\n")
        shutil.copy(CANON, d / "tests" / "assert_artifacts.py")
        (d / "tests" / "acceptance.md").write_text("> cap=5  stall=3×\n1. ok\n")
        (d / "tests" / "verification_log.md").write_text(
            "# vl\n- iter 1 PASS: smoke (evidence: scaffold, all 1/1 checks)\n"
            "- Baseline verified GREEN\n")
        (d / "app.py").write_text("x = 1\n")
        git_init(d)
        run(["git", "add", "-A"], d)
        run(["git", "commit", "-qm", "initial"], d)
        run(["git", "commit", "-q", "--allow-empty", "-m", "backup: before changes"], d)

    def final(self, *extra):
        return run([sys.executable, "tests/assert_artifacts.py", "--existing", *extra], self.d)

    def oracle_warns(self, r):
        return [l for l in r.stdout.splitlines() if l.startswith("WARN oracle record:")]

    def green_base(self):
        """--final with a fresh green record: the reference shape (no 1b warn)."""
        self.assertEqual(oracle(self.d, "--cmd", GREEN_CMD).returncode, 0)
        base = self.final("--final")
        self.assertEqual(self.oracle_warns(base), [], base.stdout)
        if os.name != "nt":
            self.assertEqual(base.returncode, 0, base.stdout + base.stderr)
        return base

    def assert_unchanged(self, r, base):
        """WARN-only: exit code and the PASSES summary line never move."""
        self.assertEqual(r.returncode, base.returncode, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1], base.stdout.splitlines()[-1])

    def test_missing_warns_without_failing(self):
        self.assertEqual(self.oracle_warns(self.final()), [], "group 1b runs at --final only")
        base = self.green_base()
        (self.d / "tests" / "oracle_run.json").unlink()
        r = self.final("--final")
        self.assert_unchanged(r, base)
        w = self.oracle_warns(r)
        self.assertEqual(len(w), 1, r.stdout)
        self.assertIn("missing", w[0])
        j = json.loads(self.final("--final", "--json").stdout)
        self.assertEqual(j["ok"], base.returncode == 0)
        self.assertTrue(any(f["code"] == "1b" and f["severity"] == "warn" for f in j["fails"]), j)

    def test_fresh_green_is_silent_even_after_log_edit_and_commit(self):
        base = self.green_base()
        with open(self.d / "tests" / "verification_log.md", "a") as f:
            f.write("- oracle: project-tests (tests/oracle_run.json)\n")
        run(["git", "add", "-A"], self.d)
        run(["git", "commit", "-qm", "record"], self.d)
        r = self.final("--final")
        self.assert_unchanged(r, base)
        self.assertEqual(self.oracle_warns(r), [], r.stdout)

    def test_stale_warns_without_failing(self):
        base = self.green_base()
        (self.d / "app.py").write_text("x = 2\n")
        r = self.final("--final")
        self.assert_unchanged(r, base)
        w = self.oracle_warns(r)
        self.assertEqual(len(w), 1, r.stdout)
        self.assertIn("STALE", w[0])

    def test_red_warns_without_failing(self):
        base = self.green_base()
        self.assertEqual(oracle(self.d, "--cmd", RED_CMD).returncode, 1)
        r = self.final("--final")
        self.assert_unchanged(r, base)
        w = self.oracle_warns(r)
        self.assertEqual(len(w), 1, r.stdout)
        self.assertIn("RED", w[0])

    def test_unreadable_record_warns_without_failing(self):
        base = self.green_base()
        (self.d / "tests" / "oracle_run.json").write_text("{not json")
        r = self.final("--final")
        self.assert_unchanged(r, base)
        self.assertIn("unreadable", " ".join(self.oracle_warns(r)))


if __name__ == "__main__":
    unittest.main()
