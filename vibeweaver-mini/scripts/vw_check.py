#!/usr/bin/env python3
"""Deterministic completion checker — run me until I print ALL CHECKS PASS.

Fails closed: an unreadable hash record or a changed test set refuses to run.
Requires pytest. Fix the CODE, never the tests.
"""
import glob, hashlib, json, os, re, subprocess, sys

HASH_FILE = ".vw_test_hashes.json"

def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

SKIP = ("node_modules", ".venv", "venv", ".git", "site-packages")
tests = sorted(set(t for pat in ("**/*_test.py", "**/test_*.py")
                   for t in glob.glob(pat, recursive=True)
                   if os.path.isfile(t)
                   and not any(part in SKIP for part in t.replace("\\", "/").split("/"))))
if not tests:
    print("NO TESTS FOUND.")
    print("NEXT ACTION: write spec_test.py from the spec's own examples, then re-run.")
    print("NOTE: a suite you wrote yourself is weak evidence — say so in your report.")
    sys.exit(1)

hashes = {t: sha(t) for t in tests}
if os.path.exists(HASH_FILE):
    try:
        old = json.load(open(HASH_FILE))
        if not isinstance(old, dict):
            raise ValueError("bad record")
    except Exception:
        print("HASH RECORD UNREADABLE — refusing to run (fail-closed).")
        print("NEXT ACTION: if the tests are unchanged, delete .vw_test_hashes.json to re-baseline.")
        sys.exit(1)
    changed = sorted((set(old) ^ set(hashes)) | {t for t in old if t in hashes and hashes[t] != old[t]})
    if changed:
        print("TEST SET CHANGED since first run — refusing to run: " + ", ".join(changed))
        print("NEXT ACTION: restore the tests and fix the CODE; if the change is")
        print("intentional, record it and delete .vw_test_hashes.json to re-baseline.")
        sys.exit(1)
else:
    json.dump(hashes, open(HASH_FILE, "w"), indent=1)

try:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests],
                       capture_output=True, text=True, timeout=900)
except subprocess.TimeoutExpired:
    print("TIMEOUT — the test suite hung. Fix the hang, then re-run.")
    sys.exit(1)
out = (r.stdout + r.stderr).strip()
print(out[-2500:])
if r.returncode == 0:
    print("\nALL CHECKS PASS")
    sys.exit(0)
failing = re.findall(r"^(FAILED\s+\S+)", out, re.M)
if failing:
    print("\nFAILING TESTS:")
    for f in failing[:8]:
        print("  " + f)
m = re.search(r"E\s+(?:AssertionError|assert):\s*(.+)", out)
if m:
    print("\nFIRST FAILURE (observed != expected):\n  " + m.group(1).strip()[:300])
print("\nNOT DONE.")
print("NEXT ACTION: make the observed value equal the expected value for the first")
print("failing test, then run `python3 vw_check.py` again.")
sys.exit(1)
