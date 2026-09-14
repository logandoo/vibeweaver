#!/usr/bin/env python3
"""Deterministic completion checker — run me until I print ALL CHECKS PASS.

Runs every *_test.py in the working directory with pytest, refuses to run if
test files were modified after the first run, and prints a precise next action.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

HASH_FILE = ".vw_test_hashes.json"


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


tests = sorted(set(
    t for pattern in ("*_test.py", "test_*.py", "**/*_test.py")
    for t in glob.glob(pattern, recursive=True)
    if os.path.isfile(t)
))

if not tests:
    print("NO TESTS FOUND.")
    print("NEXT ACTION: read the spec and write spec_test.py with one test per")
    print("required behavior (use the spec's own examples as expected values),")
    print("then run me again: python3 vw_check.py")
    sys.exit(1)

hashes = {t: sha(t) for t in tests}
if os.path.exists(HASH_FILE):
    try:
        old = json.load(open(HASH_FILE))
    except Exception:
        old = {}
    changed = [t for t in old if t not in hashes or hashes[t] != old[t]]
    if changed:
        print("TEST FILES MODIFIED — refusing to run: " + ", ".join(changed))
        print("NEXT ACTION: restore the test file(s) exactly; fix the CODE, not the tests.")
        sys.exit(1)
else:
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=1)

r = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests],
                   capture_output=True, text=True)
out = (r.stdout + r.stderr).strip()
print(out[-2500:])
if r.returncode == 0:
    print("\nALL CHECKS PASS")
    sys.exit(0)

# Structured repair packet (VeriHarness: location + observed + expected beats
# raw diagnostics; alternatives are what the repair loop acts on).
import re
failing = re.findall(r"^(FAILED\s+\S+)", out, re.M)
if failing:
    print("\nFAILING TESTS:")
    for f in failing[:8]:
        print("  " + f)
m = re.search(r"E\s+(?:AssertionError|assert):\s*(.+)", out)
if m:
    line = m.group(1).strip()
    print("\nFIRST FAILURE (observed != expected):")
    print("  " + line[:300])
print("\nNOT DONE.")
print("NEXT ACTION: change the CODE so the observed value equals the expected")
print("value for the first failing test above, then run `python3 vw_check.py` again.")
sys.exit(1)
