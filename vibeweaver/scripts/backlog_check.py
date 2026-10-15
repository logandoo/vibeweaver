#!/usr/bin/env python3
"""backlog_check.py — C8 outer-loop ledger gate.

Two checks over tests/backlog.json (the machine-checkable stop condition):
  1. schema: valid JSON, top-level userStories list, each item carrying
     id / title / priority / passes (acceptanceCriteria + dependsOn optional).
  2. evidence binding: every item with passes:true must be named by at
     least one line in tests/verification_log.md or tests/progress.txt —
     a pass flag without an executed-test record is COV-1 fraud at the
     backlog level (a flip without evidence is the outer-loop failure mode).

Usage: python3 backlog_check.py [project-root]   (default: cwd)
Exit 0 = clean (or no backlog.json — the check is inert outside C8).
Exit 1 = violations, named on stdout.
"""
import json
import pathlib
import re
import sys

REQUIRED = ("id", "title", "priority", "passes")


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    backlog = root / "tests" / "backlog.json"
    if not backlog.is_file():
        print("backlog_check.py: no tests/backlog.json — inert (exit 0)")
        return 0

    fails = []
    try:
        data = json.loads(backlog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL tests/backlog.json: not valid JSON — {e}")
        return 1

    if not isinstance(data, dict):
        print("FAIL tests/backlog.json: top-level value must be an object with `userStories`")
        return 1

    items = data.get("userStories")
    if not isinstance(items, list):
        print("FAIL tests/backlog.json: top-level `userStories` list missing")
        return 1

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            fails.append(f"userStories[{i}]: not an object")
            continue
        for key in REQUIRED:
            if key not in item:
                fails.append(f"userStories[{i}] ({item.get('id', '?')}): missing required key `{key}`")
        if "passes" in item and not isinstance(item["passes"], bool):
            fails.append(f"userStories[{i}] ({item.get('id', '?')}): `passes` must be a boolean")

    passed_ids = [str(it.get("id")) for it in items if isinstance(it, dict) and it.get("passes") is True and it.get("id")]
    if passed_ids:
        evidence = ""
        for name in ("verification_log.md", "progress.txt"):
            p = root / "tests" / name
            if p.is_file():
                evidence += p.read_text(encoding="utf-8", errors="replace") + "\n"
        # C3e (P1, 2026-10-15): a mere ID mention is NOT evidence — the
        # line must carry EXECUTION proof: a command marker AND its exit 0
        # ("- TODO: US-3 not started" must never mark US-3 done).
        exec_ok = re.compile(r"(?:exit(?:\s*code)?|rc)\s*[:=]?\s*0\b|(?:→|->)\s*0\b", re.I)
        cmd_mark = re.compile(r"(?:\$\s|command\s*[:=]|cmd\s*[:=]|\bran\b|\bexecuted\b|\brun\b)", re.I)
        for pid in passed_ids:
            hit = False
            for line in evidence.splitlines():
                if not re.search(rf"^\s*-.*\b{re.escape(pid)}\b", line, re.M):
                    continue
                if exec_ok.search(line) and cmd_mark.search(line):
                    hit = True
                    break
            if not hit:
                fails.append(
                    f"{pid}: passes:true but no line in tests/verification_log.md or "
                    f"tests/progress.txt carries EXECUTION evidence for it (a command "
                    f"marker AND its exit 0) — a mention or TODO is not a test run "
                    f"(C3e / COV-1)")

    if fails:
        print(f"backlog_check.py: {len(fails)} violation(s):")
        for f in fails:
            print("  FAIL " + f)
        return 1
    done = sum(1 for it in items if isinstance(it, dict) and it.get("passes") is True)
    print(f"backlog_check.py: clean — {done}/{len(items)} items passing, all evidence-bound (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
