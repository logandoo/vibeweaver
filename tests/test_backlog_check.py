"""backlog_check.py tests (C3e / BL-19 — coverage restored 2026-10-15).

Spec: a `passes:true` backlog item needs EXECUTION evidence (a command
marker AND its exit 0) on a line naming the id — mentions/TODOs never count.
Run: python3 tests/test_backlog_check.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
CHECK = REPO / "scripts" / "backlog_check.py"
RESULTS = []


def rec(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def fixture(stories, log_lines):
    d = pathlib.Path(tempfile.mkdtemp(prefix="vwbacklog-"))
    (d / "tests").mkdir()
    (d / "tests" / "backlog.json").write_text(json.dumps({"userStories": stories}))
    (d / "tests" / "verification_log.md").write_text("## Task: t\n" + "\n".join(log_lines) + "\n")
    return d


def run(d):
    return subprocess.run([sys.executable, str(CHECK)], cwd=d, capture_output=True, text=True, timeout=30)


def main():
    ok_story = {"id": "US-1", "title": "t", "priority": "p", "passes": True}
    todo_story = {"id": "US-3", "title": "t", "priority": "p", "passes": True}
    todo_story2 = {"id": "US-4", "title": "t", "priority": "p", "passes": True}
    open_story = {"id": "US-9", "title": "t", "priority": "p", "passes": False}

    d = fixture([ok_story], ["- US-1: ran pytest tests/test_us1.py → exit 0 (1/1)"])
    r = run(d)
    rec("C3e execution-evidence line (command + exit 0) satisfies passes:true",
        r.returncode == 0, f"rc={r.returncode}")

    d = fixture([todo_story], ["- TODO: US-3 还没开始"])
    r = run(d)
    rec("C3e TODO/mention is NOT execution evidence -> FAIL",
        r.returncode == 1 and "US-3" in r.stdout and "EXECUTION evidence" in r.stdout,
        f"rc={r.returncode}")

    d = fixture([todo_story2], ["- US-4 passed all checks"])  # claim without command/exit
    r = run(d)
    rec("C3e claim-only line (no command/exit code) -> FAIL",
        r.returncode == 1 and "US-4" in r.stdout, f"rc={r.returncode}")

    d = fixture([open_story], ["- nothing done yet"])
    r = run(d)
    rec("C3e passes:false items need no evidence -> clean",
        r.returncode == 0, f"rc={r.returncode}")

    d = fixture([ok_story], ["- US-1: executed script/check.sh — exit code 0"])
    r = run(d)
    rec("C3e 'executed … exit code 0' phrasing also counts",
        r.returncode == 0, f"rc={r.returncode}")

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
          (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
