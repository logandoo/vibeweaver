#!/usr/bin/env python3
"""run_oracle.py — machine-written oracle record (SKILL.md "Trusted oracle").

Only project/external tests certify a change (tier-1 oracle). The
`- iter N PASS` line in tests/verification_log.md is agent-written; this
script runs the project's own test command and writes what actually
happened to tests/oracle_run.json:

    {"schema": 1, "cmd": ..., "exit_code": ..., "tree_sha": ...,
     "test_file_hashes": {...}, "ts": "<UTC ISO>", "duration_s": ...}

assert_artifacts.py --final reads the record (group 1b) and WARNs — never
fails — when it is missing, stale (tree_sha != current tree) or red
(exit_code != 0).

Runner discovery and test-file hashing are vendored from the mini kit's
vibeweaver-mini/scripts/vw_check.py (pytest · go test · cargo test ·
npm test); tests/test_run_oracle.py pins the two in parity.

tree_sha hashes the working tree through a TEMPORARY index and object dir
(GIT_INDEX_FILE / GIT_OBJECT_DIRECTORY, the real objects as alternates), so
the user's index and object store are never written. Process artifacts the
agent writes AFTER a test run (log, acceptance, record, gate state, evidence
media) are excluded — SHARED CONTRACT with assert_artifacts.oracle_tree_sha.
null when the directory is not inside a git work tree.

Usage:
  python3 scripts/run_oracle.py [--root DIR] [--cmd "<test command>"] [--timeout S]

Exit code mirrors the test command's exit code; 2 = no runner found.
Stdlib only.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

SCHEMA = 1
RECORD = os.path.join("tests", "oracle_run.json")
SKIP = ("node_modules", ".venv", "venv", ".git", "site-packages", "__pycache__")

# SHARED CONTRACT with assert_artifacts.py ORACLE_TREE_EXCLUDE — keep identical.
ORACLE_TREE_EXCLUDE = (
    ":(exclude).vibeweaver", ":(exclude)memory",
    ":(exclude)tests/oracle_run.json", ":(exclude)tests/gate_result.json",
    ":(exclude)tests/.evidence.lock", ":(exclude)tests/evidence_manifest.json",
    ":(exclude)tests/test_baseline.json", ":(exclude)tests/verification_log.md",
    ":(exclude)tests/acceptance.md", ":(exclude)tests/working_note.md",
    ":(exclude)tests/review_package.md",
    ":(exclude,glob)tests/*.log", ":(exclude,glob)tests/*.png",
    ":(exclude,glob)tests/*.webm", ":(exclude,glob)tests/*.wav",
    ":(exclude,glob)tests/*.mp4", ":(exclude,glob)tests/*.mp3",
    ":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/.pytest_cache/**",
)


# --- vendored from vibeweaver-mini/scripts/vw_check.py (keep in parity) ----
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
        rs = sorted(t for t in glob.glob("**/*.rs", recursive=True) if clean(t))
        return rs or ["Cargo.toml"], ["cargo", "test", "--quiet"]
    if os.path.exists("package.json"):
        try:
            pkg = json.load(open("package.json"))
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
        if "test" not in scripts:
            return [], []
        js_pats = (
            "**/*.test.js", "**/*.test.mjs", "**/*.test.cjs", "**/*.test.ts",
            "**/*.test.tsx", "**/*.test.jsx",
            "**/*.spec.js", "**/*.spec.mjs", "**/*.spec.cjs", "**/*.spec.ts",
            "**/*.spec.tsx", "**/*.spec.jsx",
            "**/test.js", "**/test.mjs", "**/test.cjs", "**/test.ts",
            "**/test.mts", "**/test.cts", "**/test.jsx", "**/test.tsx",
            "**/*_test.js", "**/*_test.mjs", "**/*_test.cjs", "**/*_test.ts",
            "**/*_test.mts", "**/*_test.cts", "**/*_test.jsx", "**/*_test.tsx",
            "**/*.test.mts", "**/*.test.cts", "**/*.spec.mts", "**/*.spec.cts",
            "test/**/*.js", "test/**/*.mjs", "test/**/*.cjs", "test/**/*.ts",
            "test/**/*.tsx", "test/**/*.jsx", "test/**/*.mts", "test/**/*.cts",
            "tests/**/*.js", "tests/**/*.mjs", "tests/**/*.cjs", "tests/**/*.ts",
            "tests/**/*.tsx", "tests/**/*.jsx", "tests/**/*.mts", "tests/**/*.cts",
            "__tests__/**/*.js", "__tests__/**/*.mjs", "__tests__/**/*.cjs",
            "__tests__/**/*.ts", "__tests__/**/*.tsx", "__tests__/**/*.jsx",
            "__tests__/**/*.mts", "__tests__/**/*.cts",
            "**/test-*.js", "**/test-*.mjs", "**/test-*.cjs", "**/test-*.ts",
            "**/test-*.mts", "**/test-*.cts",
            "**/*-test.js", "**/*-test.mjs", "**/*-test.cjs", "**/*-test.ts",
            "**/*-test.mts", "**/*-test.cts",
        )
        js = sorted(set(t for pat in js_pats
                        for t in glob.glob(pat, recursive=True) if clean(t)))
        return js or ["package.json"], ["npm", "test", "--silent"]
    return [], []


def norm_key(p):
    return str(p).replace(os.sep, "/").replace("\\", "/")


def test_config_files():
    """Files that can change which tests run without changing a test file."""
    out = set()
    for pat in ("**/conftest.py", "**/pytest.ini", "**/tox.ini", "**/setup.cfg"):
        out.update(t for t in glob.glob(pat, recursive=True) if clean(t))
    for p in glob.glob("**/pyproject.toml", recursive=True):
        if clean(p):
            try:
                if "pytest" in open(p, encoding="utf-8").read():
                    out.add(p)
            except OSError:
                pass
    if os.path.isfile("package.json") and clean("package.json"):
        try:
            pkg = json.load(open("package.json", encoding="utf-8"))
            scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
            if "test" in scripts:
                out.add("package.json")
        except Exception:
            pass
    for pat in ("**/jest.config.*", "**/vitest.config.*", "**/.mocharc.*",
                "**/karma.conf.*", "**/playwright.config.*"):
        out.update(t for t in glob.glob(pat, recursive=True) if clean(t))
    return sorted(out)
# --- end vendored ----------------------------------------------------------


def _git(root, *args, env=None):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=60, env=env)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""


def oracle_tree_sha(root):
    """git tree sha of the working tree under `root` (index-free), or None.

    SHARED CONTRACT with assert_artifacts.oracle_tree_sha — keep identical."""
    rc, inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if rc != 0 or inside != "true":
        return None
    _, prefix = _git(root, "rev-parse", "--show-prefix")
    rc, objects = _git(root, "rev-parse", "--git-path", "objects")
    if rc != 0 or not objects:
        return None
    objects = os.path.abspath(os.path.join(str(root), objects))
    with tempfile.TemporaryDirectory(prefix="vw-oracle-") as td:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(td, "index"),
                   GIT_OBJECT_DIRECTORY=os.path.join(td, "objects"),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=objects)
        os.mkdir(os.path.join(td, "objects"))
        rc, _ = _git(root, "add", "-A", "--", ".", *ORACLE_TREE_EXCLUDE, env=env)
        if rc != 0:
            return None
        args = ["write-tree"] + (["--prefix=" + prefix] if prefix else [])
        rc, tree = _git(root, *args, env=env)
        return tree if rc == 0 and tree else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="project directory (default: cwd)")
    ap.add_argument("--cmd", help="test command (shell string); overrides runner discovery")
    ap.add_argument("--timeout", type=float, default=900, help="seconds (default 900)")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    os.chdir(root)

    tests, runner = discover()
    if args.cmd:
        cmd, run_argv, shell = args.cmd, args.cmd, True
    elif runner:
        cmd, run_argv, shell = " ".join(shlex.quote(a) for a in runner), runner, False
    else:
        print("run_oracle: NO TEST RUNNER FOUND (pytest / go test / cargo test / npm test) "
              "— pass --cmd \"<test command>\"; no record written (exit 2)")
        return 2

    hashes = {norm_key(t): sha(t) for t in tests + test_config_files() if os.path.isfile(t)}
    tree = oracle_tree_sha(root)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.monotonic()
    try:
        r = subprocess.run(run_argv, shell=shell, env=env, timeout=args.timeout)
        code = r.returncode
    except subprocess.TimeoutExpired:
        print(f"run_oracle: TIMEOUT after {args.timeout:g}s — recorded as exit 124")
        code = 124
    except OSError as e:
        print(f"run_oracle: RUNNER UNAVAILABLE ({e}) — recorded as exit 127")
        code = 127
    record = {
        "schema": SCHEMA,
        "cmd": cmd,
        "exit_code": code,
        "tree_sha": tree,
        "test_file_hashes": hashes,
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(time.monotonic() - t0, 3),
    }
    os.makedirs("tests", exist_ok=True)
    tmp = RECORD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, RECORD)
    print(f"run_oracle: exit_code={code} tree_sha={tree} -> {norm_key(RECORD)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
