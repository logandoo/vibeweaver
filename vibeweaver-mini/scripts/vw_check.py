#!/usr/bin/env python3
"""Deterministic completion checker — run me until I print ALL CHECKS PASS.

Fails closed: an unreadable hash record or a changed test set refuses to run.
Auto-detects the runner: pytest (test_*.py / *_test.py) · go test (*_test.go) ·
cargo test (Cargo.toml) · npm test (package.json with a test script).
Fix the CODE, never the tests.

Loop bounds (aligned with the main skill): cap=5 runs, stall=3x same first
failure — the run counter lives in .vw_loop_state.json and the declarations
print for the model to honor.

Test changes need JUSTIFICATION, not a bypass: when the test set changed, log
`- test-change: <path> — <reason>` in the task log and re-run with
`--test-change "<reason>"` (the hash record only re-baselines through that
flag — it is machine-maintained).

Run via `script/check.sh` (COV-2 path): the completion flag is THIS checker's
exit 0, and check.sh prints the ALL CHECKS PASS line itself.
"""
import glob, hashlib, json, os, re, subprocess, sys

HASH_FILE = ".vw_test_hashes.json"
STATE_FILE = ".vw_loop_state.json"
CAP = 5
STALL = 3
SKIP = ("node_modules", ".venv", "venv", ".git", "site-packages", "__pycache__")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def clean(t):
    return os.path.isfile(t) and not any(part in SKIP for part in t.replace("\\", "/").split("/"))


def discover():
    """(test files, runner argv) — multi-runner auto-detect (W5-F)."""
    py = sorted(set(t for pat in ("**/*_test.py", "**/test_*.py")
                    for t in glob.glob(pat, recursive=True) if clean(t)))
    if py:
        return py, [sys.executable, "-m", "pytest", "-q", *py]
    go = sorted(set(t for pat in ("**/*_test.go",) for t in glob.glob(pat, recursive=True) if clean(t)))
    if go:
        return go, ["go", "test", "./..."]
    if os.path.exists("Cargo.toml"):
        # cargo runs inline #[cfg(test)] units too — a Rust project is never
        # "NO TESTS" just because tests/ is empty (review R-I2)
        rs = sorted(t for t in glob.glob("**/*.rs", recursive=True) if clean(t))
        return rs or ["Cargo.toml"], ["cargo", "test", "--quiet"]
    if os.path.exists("package.json"):
        try:
            pkg = json.load(open("package.json"))
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
        if "test" not in scripts:
            # a package.json without a test script is NOT an npm-test project
            return [], []
        js = sorted(set(t for pat in ("**/*.test.js", "**/*.test.ts", "**/*.spec.js", "**/*.spec.ts")
                        for t in glob.glob(pat, recursive=True) if clean(t)))
        return js or ["package.json"], ["npm", "test", "--silent"]
    return [], []


def bump_state(passed, first_fail):
    """cap=5 / stall=3x loop bookkeeping (the declarations ride stdout)."""
    try:
        st = json.load(open(STATE_FILE))
        if not isinstance(st, dict):
            raise ValueError
    except Exception:
        st = {"runs": 0, "same_fail": 0, "sig": ""}
    notes = []
    if passed:
        st = {"runs": 0, "same_fail": 0, "sig": ""}
    else:
        st["runs"] = int(st.get("runs", 0)) + 1
        sig = (first_fail or "")[:200]
        if sig and sig == st.get("sig"):
            st["same_fail"] = int(st.get("same_fail", 0)) + 1
        else:
            st["same_fail"] = 1 if sig else int(st.get("same_fail", 0))
        st["sig"] = sig
        if st["same_fail"] >= STALL:
            notes.append(f"- stall: the same first failure {STALL}x in a row — declare the stall "
                         f"in the log and change direction (cap={CAP}  stall={STALL}x); do not retry it")
        if st["runs"] >= CAP:
            notes.append(f"- cap-hit: {CAP} checker runs without ALL CHECKS PASS — stop this "
                         f"direction and re-plan/escalate (cap={CAP}  stall={STALL}x)")
    json.dump(st, open(STATE_FILE, "w"), indent=1)
    return notes


def main():
    reason = None
    if "--test-change" in sys.argv:
        i = sys.argv.index("--test-change")
        if i + 1 >= len(sys.argv) or not sys.argv[i + 1].strip():
            print("USAGE: vw_check.py --test-change \"<why the test change is legitimate>\"")
            return 2
        reason = sys.argv[i + 1].strip()

    tests, runner = discover()
    if not tests:
        print("NO TESTS FOUND.")
        print("NEXT ACTION: write spec_test.py from the spec's own examples, then re-run.")
        print("NOTE: a suite you wrote yourself is weak evidence — say so in your report.")
        return 1

    hashes = {t: sha(t) for t in tests}
    if os.path.exists(HASH_FILE):
        try:
            old = json.load(open(HASH_FILE))
            if not isinstance(old, dict):
                raise ValueError("bad record")
        except Exception:
            print("HASH RECORD UNREADABLE — refusing to run (fail-closed).")
            print("The record is machine-maintained; report the corruption instead of rebuilding it.")
            return 1
        changed = sorted((set(old) ^ set(hashes)) | {t for t in old if t in hashes and hashes[t] != old[t]})
        if changed:
            if not reason:
                # W5-F: the bypass recipe used to live here ("delete the hash
                # file to re-baseline") — a weakened test set now demands a
                # `- test-change:` justification instead.
                print("TEST SET CHANGED since first run — refusing to run: " + ", ".join(changed))
                print("A test change needs its justification: log")
                print("  - test-change: <path> — <reason>")
                print("in tests/verification_log.md, then re-run with")
                print("  python3 vw_check.py --test-change \"<the same reason>\"")
                print("Never edit tests to pass — fix the CODE (or justify the test change).")
                return 1
            print(f"TEST SET CHANGED — re-baselined under justification: {reason}")
            for t in changed:
                print(f"  - test-change: {t} — {reason}")
            json.dump(hashes, open(HASH_FILE, "w"), indent=1)
    else:
        # Review R-C2 (BL-13): deleting the record must not silently
        # re-baseline a weakened suite. First-ever run (no loop state) seals
        # freely; a record vanishing AFTER the checker has run before demands
        # the same `--test-change` justification a change needs.
        if os.path.exists(STATE_FILE) and not reason:
            print("HASH RECORD MISSING but the checker has run before — refusing to run.")
            print("Deleting the record is not a re-baseline: log")
            print("  - test-change: <path> — <reason>")
            print("then re-run with --test-change \"<the same reason>\".")
            return 1
        if reason:
            print(f"HASH RECORD created under justification: {reason}")
        json.dump(hashes, open(HASH_FILE, "w"), indent=1)

    try:
        r = subprocess.run(runner, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        print("TIMEOUT — the test suite hung. Fix the hang, then re-run.")
        return 1
    except FileNotFoundError as e:
        print(f"RUNNER UNAVAILABLE ({runner[0]}): {e} — install it or adjust the suite.")
        return 1
    out = (r.stdout + r.stderr).strip()
    print(out[-2500:])
    if r.returncode == 5 or "Missing script" in out or "no tests ran" in out.lower():
        print("RUNNER MISCONFIGURED — the runner found no runnable tests (not a code failure).")
        print("Fix the suite/runner wiring first; do NOT treat this as a failing assertion.")
        return 1
    if r.returncode == 0:
        print("\nALL CHECKS PASS")
        bump_state(True, None)
        return 0
    failing = re.findall(r"^(FAILED\s+\S+|--- FAIL: \S+|not ok \d+ \S+|FAIL\s+\S+)", out, re.M)
    if failing:
        print("\nFAILING TESTS:")
        for f in failing[:8]:
            print("  " + f)
    # first-failure signature (stall detection): pytest `E ...` line, else the
    # first failing-test marker, else the output head — stable across runners
    m = re.search(r"^E\s+(?:AssertionError:|assert:)?\s*(.+)$", out, re.M)
    first = m.group(1).strip()[:300] if m else (failing[0][:300] if failing else out[:200])
    if first:
        print("\nFIRST FAILURE (observed != expected):\n  " + first)
    for note in bump_state(False, first):
        print(note)
    print("\nNOT DONE.")
    print("NEXT ACTION: make the observed value equal the expected value for the first")
    print("failing test, then run the checker again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
