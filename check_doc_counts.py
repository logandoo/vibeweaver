#!/usr/bin/env python3
"""check_doc_counts.py — bind README test-count claims to a real run.

W18 audit (2026-10-22) found the published README/CHANGELOG stating counts no
in-tree run could reproduce ("plugin compat 82/82" over a tree that ran 70/71 —
audit findings F1/F6). Numbers in prose drift; runs do not. This checker makes
the docs' claims executable:

  1. run each suite and parse its SUMMARY count(s)
  2. extract every count claim the READMEs state ON THE LINE THAT NAMES THE
     SUITE'S COMMAND (a claim is bound to the command that reproduces it;
     historical prose counts — wave notes, benchmark tables — are not claims)
  3. fail on any mismatch, on a red suite (failures must be 0 for claims to
     bind), on a suite the docs never quantify, and on any leftover CI
     quarantine flag (`--allow-known`: the W18 audit's F2 — a green CI over a
     live failure)

Usage:
  python3 check_doc_counts.py            # run suites + check README claims
  python3 check_doc_counts.py --skip-run # doc shapes only (no suite execution)

Exit 0 = every stated count equals what this tree prints. Stdlib only.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# claim = the regex that captures the claim ON an anchor line;
# run   = the SUMMARY regex of an executed suite (group 1..n).
SUITES = {
    "selftest": {
        "cmd": ["node", "vibeweaver/scripts/audit_selftest.mjs"],
        "anchor": "audit_selftest",
        "claim": re.compile(r"(\d+)\s*(?:项\s*)?fixture\s*(?:checks|检查)"),
        "run": re.compile(r"fixture checks: (\d+), failures: (\d+)"),
    },
    "mutation": {
        "cmd": ["node", "vibeweaver/scripts/mutation_sweep.mjs"],
        "anchor": "mutation_sweep",
        "claim": re.compile(r"(\d+)\s*(?:项\s*)?(?:mutations?|变异)"),
        "run": re.compile(r"MUTATION SWEEP: (\d+) passed, (\d+) failed"),
    },
    "compat": {
        "cmd": ["node", "tests/plugin_compat_test.mjs"],
        "anchor": "plugin_compat",
        "claim": re.compile(r"(?<![\w.])(\d+)\s*/\s*(\d+)"),
        "run": re.compile(r"COMPAT HARNESS: (\d+)/(\d+) passed, (\d+) failed"),
    },
    "mini": {
        "cmd": ["node", "tests/mini_gate_test.mjs"],
        "anchor": "mini_gate",
        "claim": re.compile(r"(?<![\w.])(\d+)\s*/\s*(\d+)"),
        "run": re.compile(r"RESULT: (\d+)/(\d+) passed, (\d+) failed"),
    },
}

QUARANTINE = re.compile(r"allow[-_]?known|allowKnown|E3/G9 allowed")
QUARANTINE_FILES = (".github/workflows/verify.yml", "tests/plugin_compat_test.mjs")
DOCS = ("README.md", "README_zh.md")


def _to_value(key, groups):
    """Claim/run groups → the canonical value for a suite."""
    if key in ("selftest", "mutation"):
        return int(groups[0])
    return (int(groups[0]), int(groups[1]))


def fmt(value):
    return f"{value[0]}/{value[1]}" if isinstance(value, tuple) else str(value)


def extract_claims(text):
    """{suite: [claimed values]} — only lines that name the suite's command.

    Prose that merely mentions a number (wave notes, benchmark tables) never
    names the command and is therefore never a claim."""
    claims = {}
    for line in text.splitlines():
        for key, spec in SUITES.items():
            if spec["anchor"] not in line:
                continue
            for m in spec["claim"].finditer(line):
                value = _to_value(key, m.groups())
                seen = claims.setdefault(key, [])
                if value not in seen:  # distinct claims only — same value twice
                    seen.append(value)  # (command line + files row) is one claim
    return claims


def parse_run(key, text):
    """Suite SUMMARY output → canonical value, None when unparseable."""
    m = SUITES[key]["run"].search(text)
    if not m:
        return None
    if key in ("selftest", "mutation"):
        return (int(m.group(1)), int(m.group(2)))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def compare_counts(runs, claims):
    """Every stated claim must equal the run; a red run binds nothing."""
    errors = []
    for key in SUITES:
        run = runs.get(key)
        if run is None:
            errors.append(f"{key}: run output unparseable — cannot bind claims")
            continue
        failed = run[-1]
        if failed:
            errors.append(f"{key}: suite red ({failed} failed) — claims cannot bind a red run")
            continue
        runval = _to_value(key, run)
        got = claims.get(key)
        if not got:
            errors.append(f"{key}: no count claim found in the docs "
                          f"(state {fmt(runval)} next to the command)")
            continue
        for claim in got:
            if claim != runval:
                errors.append(f"{key}: claim {fmt(claim)} != run {fmt(runval)}")
    return errors


def scan_quarantine_text(text):
    """True when a quarantine escape hatch is present (CI/harness files).

    Full-line comments are not code: a historical note that documents the
    quarantine's REMOVAL (tests/plugin_compat_test.mjs W18 D-W18-2 comment)
    must not trip the ban — an in-effect handler or a CI flag always sits on
    an executable line."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        if QUARANTINE.search(line):
            return True
    return False


def scan_quarantine(root=ROOT):
    errors = []
    for rel in QUARANTINE_FILES:
        path = root / rel
        if path.is_file() and scan_quarantine_text(path.read_text(errors="replace")):
            errors.append(f"{rel}: quarantine flag present — CI must run without --allow-known")
    return errors


def run_suite(key):
    spec = SUITES[key]
    try:
        proc = subprocess.run(spec["cmd"], cwd=str(ROOT), text=True,
                              capture_output=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{key}: run failed to execute ({exc})"
    return parse_run(key, proc.stdout + proc.stderr), None


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    skip_run = "--skip-run" in argv
    errors, runs = [], {}
    for key in SUITES:
        if skip_run:
            continue
        value, err = run_suite(key)
        runs[key] = value
        if err:
            errors.append(err)
    for rel in DOCS:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"{rel}: missing — the counts live here")
            continue
        claims = extract_claims(path.read_text(errors="replace"))
        errors.extend(f"{rel}: {e}" for e in compare_counts(runs, claims))
    errors.extend(scan_quarantine(ROOT))
    for key in SUITES:
        print(f"{'SKIP' if skip_run else 'RUN '} {key:9s} "
              f"{fmt(_to_value(key, runs[key])) if runs.get(key) else '(not run)'}")
    for err in errors:
        print(f"FAIL {err}")
    if errors:
        print(f"check_doc_counts.py: {len(errors)} claim mismatch(es) — FAIL (exit 1)")
        return 1
    print("check_doc_counts.py: every stated count equals this tree's runs (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
