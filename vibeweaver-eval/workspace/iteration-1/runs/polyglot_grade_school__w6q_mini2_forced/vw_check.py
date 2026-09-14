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
print("\nNOT DONE.")
print("NEXT ACTION: fix the first failing assertion above (the right side is the")
print("expected value), then run `python3 vw_check.py` again.")
sys.exit(1)
