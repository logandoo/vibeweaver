"""Artifact assertion checker (substitute for the skill's canonical
scripts/assert_artifacts.py, which was NOT present in the installed skill
directory). Verifies the mandatory on-disk artifacts for this task.

This is a verification/evidence checker, not a test of list_ops.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

checks = []


def check(name, ok):
    checks.append((name, ok))


def read(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as fh:
        return fh.read()


acc = read("tests/acceptance.md")
check("acceptance.md exists", bool(acc.strip()))
check("acceptance.md first line == '> cap=5  stall=3×'", acc.splitlines()[0] == "> cap=5  stall=3\u00d7")

vlog = read("tests/verification_log.md")
check("verification_log.md has baseline entry", "Baseline verified GREEN" in vlog)
check("verification_log.md has iteration entry", "iter 1 PASS" in vlog)

transcript = read("tests/verification_transcript.log")
check("transcript shows ALL PASS", "RESULT: ALL PASS" in transcript)
check("transcript covers all 8 ops", all(op in transcript for op in
      ["append", "concat", "filter", "length", "map", "foldl", "foldr", "reverse"]))

check("decisions.md exists (AUTO)", os.path.isfile(os.path.join(ROOT, "tests/decisions.md")))
check("project_profile.json valid", bool(json.loads(read("tests/project_profile.json"))))

src = read("list_ops.py")
for fn in ["append", "concat", "filter", "length", "map", "foldl", "foldr", "reverse"]:
    check(f"list_ops.py defines {fn}()", f"def {fn}(" in src)

check("memory/MEMORY.md exists", os.path.isfile(os.path.join(ROOT, "memory/MEMORY.md")))
check("memory topic file exists", os.path.isfile(os.path.join(ROOT, "memory/list_ops.md")))

passed = sum(1 for _, ok in checks if ok)
failed = len(checks) - passed
for name, ok in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
print(f"\nassert_artifacts: pass={passed}/fail={failed}")
sys.exit(1 if failed else 0)
