#!/usr/bin/env python3
"""check_doc_counts.py — bind README/CHANGELOG test-count claims to a real run.

W18 audit (2026-10-22) found the published docs stating counts no in-tree run
could reproduce ("plugin compat 82/82" over a tree that ran 70/71 — audit
findings F1/F6). Numbers in prose drift; runs do not. This checker makes the
docs' claims executable:

  1. run each suite and parse its SUMMARY count(s) — a non-zero exit or a red
     run binds nothing
  2. extract count claims the READMEs state ON THE LINE THAT NAMES THE SUITE'S
     COMMAND, plus the name-anchored claims in the NEWEST changelog entry
     (the "plugin compat N/N" form the W18 claim actually used)
  3. fail on any mismatch, on a suite the docs never quantify, and on any
     leftover CI quarantine flag (`--allow-known`: audit F2 — green CI over a
     live failure)

Historical prose counts (wave notes, benchmark tables, older changelog
entries) are history, not claims — only command/name-anchored lines bind.

Usage:
  python3 check_doc_counts.py      # run suites + check doc claims

Exit 0 = every stated count equals what this tree prints. Stdlib only;
all file/process text is read as UTF-8 so the Windows matrix legs decode the
CJK/emoji suite output deterministically (review C1).
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# claim = regex capturing the claim on an anchored line;
# run   = SUMMARY regex of an executed suite.
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

# The newest changelog entry binds by NAME ("plugin compat 82/82" — the exact
# shape of the falsified W18 claim). Values are (a, b): selftest/mutation read
# as (total, failures), compat/mini as (passed, total).
CHANGELOG_CLAIM = {
    "selftest": re.compile(r"audit_selftest\s+(\d+)\s*/\s*(\d+)"),
    "mutation": re.compile(r"mutation[_ ]sweep\s+(\d+)\s*/\s*(\d+)"),
    "compat": re.compile(r"plugin compat\s+(\d+)\s*/\s*(\d+)"),
    "mini": re.compile(r"mini[ _]gate\s+(\d+)\s*/\s*(\d+)"),
}

QUARANTINE = re.compile(r"allow[-_]?known|allowKnown|E3/G9 allowed")
QUARANTINE_FILES = (".github/workflows/verify.yml", "tests/plugin_compat_test.mjs")
DOCS = ("README.md", "README_zh.md")
CHANGELOGS = ("CHANGELOG.md", "CHANGELOG_zh.md")

# 2026-10-22 CI incident: the mini gate's case count is platform dependent
# (62 macOS / 60 Linux / 55 Windows — POSIX-only blocks + installer cases in
# tests/mini_gate_test.mjs). Claims may carry a platform tag; the tag-less form
# is universal and must match every leg. Each CI matrix leg binds the claim
# for ITS platform; foreign platforms' claims defer to their own leg.
PLATFORM = {"darwin": "macOS", "linux": "Linux", "win32": "Windows"}.get(
    __import__("sys").platform, __import__("sys").platform)
TAGGED_PAIR = re.compile(
    r"(?<![\w.])(\d+)\s*/\s*(\d+)(?:\s*\((macOS|Linux|Windows)\))?")


def _read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def fmt(value):
    return f"{value[0]}/{value[1]}" if isinstance(value, tuple) else str(value)


def extract_claims(text):
    """{suite: [(value, tag)]} — only lines naming the suite's command. The
    tag is the platform qualifier ("62/62 (macOS)") or None (universal).
    Prose that merely mentions a number (wave notes, benchmark tables) never
    names the command and is therefore never a claim."""
    claims = {}
    for line in text.splitlines():
        for key, spec in SUITES.items():
            if spec["anchor"] not in line:
                continue
            found = []
            if key in ("compat", "mini"):
                pm = TAGGED_PAIR.search(line)
                if pm:
                    found.append(((int(pm.group(1)), int(pm.group(2))), pm.group(3)))
                    if pm.group(3):  # platform-list form: tagged follow-ons
                        for pm2 in TAGGED_PAIR.finditer(line[pm.end():]):
                            if pm2.group(3):
                                found.append(((int(pm2.group(1)), int(pm2.group(2))),
                                              pm2.group(3)))
            else:
                for m in spec["claim"].finditer(line):
                    found.append((int(m.group(1)), None))
            for item in found:
                seen = claims.setdefault(key, [])
                if item not in seen:
                    seen.append(item)
    return claims


def extract_changelog_claims(text):
    """{suite: [(value, tag)]} from the NEWEST changelog entry only.

    Older entries are dated history — their counts were true of their tree.
    The newest entry describes THIS tree and must reproduce here."""
    parts = re.split(r"(?m)^## ", text)
    section = parts[1] if len(parts) > 1 else ""
    claims = {}
    for key, pattern in CHANGELOG_CLAIM.items():
        seen = []
        for m in pattern.finditer(section):
            line_end = section.find("\n", m.start())
            rest = section[m.end():line_end]
            tagm = re.match(r"\s*\((macOS|Linux|Windows)\)", rest)
            item = ((int(m.group(1)), int(m.group(2))),
                    tagm.group(1) if tagm else None)
            if item not in seen:
                seen.append(item)
            if tagm:  # platform-list form: tagged follow-ons belong here
                for pm in TAGGED_PAIR.finditer(rest[tagm.end():]):
                    if pm.group(3):
                        it2 = ((int(pm.group(1)), int(pm.group(2))), pm.group(3))
                        if it2 not in seen:
                            seen.append(it2)
        if seen:
            claims[key] = seen
    return claims


def parse_run(key, text):
    """Suite SUMMARY output → canonical value, None when unparseable."""
    m = SUITES[key]["run"].search(text)
    if not m:
        return None
    if key in ("selftest", "mutation"):
        return (int(m.group(1)), int(m.group(2)))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _matches(key, claim, run):
    """README claims may state the total alone ("571 fixture checks") or
    total/failures ("571/0"); changelog claims state a/b per suite."""
    if key in ("selftest", "mutation"):
        if isinstance(claim, int):
            return claim == run[0]
        return claim == (run[0], run[1])
    return claim == (run[0], run[1])


def compare_counts(runs, claims, where="docs"):
    """Every applicable claim must equal the run; a red run binds nothing.

    Claim = (value, tag). tag None = universal (must match this run); tag
    == PLATFORM = must match this run; other tags defer to their own CI
    matrix leg (each leg binds its platform's number)."""
    errors = []
    for key in SUITES:
        run = runs.get(key)
        if run is None:
            errors.append(f"{key}: run output unparseable — cannot bind claims")
            continue
        if run[-1]:
            errors.append(f"{key}: suite red ({run[-1]} failed) — "
                          f"claims cannot bind a red run")
            continue
        got = claims.get(key)
        if not got:
            errors.append(f"{key}: no count claim found in {where} "
                          f"(state {fmt(_claim_repr(key, run))} next to the name)")
            continue
        applicable = [c for c in got if c[1] in (None, PLATFORM)]
        if not applicable:
            errors.append(f"{key}: no count claim for this platform ({PLATFORM}) "
                          f"in {where} — foreign-tag claims defer to their leg")
            continue
        for value, tag in applicable:
            if not _matches(key, value, run):
                suffix = f"/{tag}" if tag else ""
                errors.append(f"{key}: claim {fmt(value)}{suffix} != run "
                              f"{fmt(_claim_repr(key, run))}")
    return errors


def _claim_repr(key, run):
    return (run[0], run[1]) if key in ("selftest", "mutation") else (run[0], run[1])


def scan_quarantine_text(text):
    """True when a quarantine escape hatch is present (CI/harness files).

    Full-line comments are not code: a historical note documenting the
    quarantine's REMOVAL must not trip the ban — an in-effect handler or a CI
    flag always sits on an executable line. KNOWN BOUNDARY (review I3): this
    is a signature scan — a renamed flag in an unlisted file escapes it; the
    red-run binding is the second line of defense."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        if QUARANTINE.search(line):
            return True
    return False


def scan_quarantine(root=None):
    root = root or ROOT
    errors = []
    for rel in QUARANTINE_FILES:
        path = root / rel
        if path.is_file() and scan_quarantine_text(_read(path)):
            errors.append(f"{rel}: quarantine flag present — "
                          f"CI must run without --allow-known")
    return errors


def evaluate_proc(key, proc_text, returncode):
    """Test seam (review I2/M2): a suite binds only when it exited 0 AND its
    SUMMARY parsed — a red exit with a green-looking SUMMARY binds nothing."""
    if returncode != 0:
        return None, f"{key}: suite exited {returncode} — claims cannot bind a red run"
    value = parse_run(key, proc_text)
    if value is None:
        return None, f"{key}: run output unparseable — cannot bind claims"
    return value, None


def run_suite(key):
    spec = SUITES[key]
    try:
        proc = subprocess.run(spec["cmd"], cwd=str(ROOT), text=True,
                              encoding="utf-8", errors="replace",
                              capture_output=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{key}: run failed to execute ({exc})"
    return evaluate_proc(key, proc.stdout + proc.stderr, proc.returncode)


def main(argv=None, root=None, run=run_suite):
    argv = argv if argv is not None else sys.argv[1:]
    root = root or ROOT
    errors, runs = [], {}
    for key in SUITES:
        value, err = run(key)
        runs[key] = value
        if err:
            errors.append(err)
    for rel in DOCS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing — the counts live here")
            continue
        claims = extract_claims(_read(path))
        errors.extend(f"{rel}: {e}" for e in compare_counts(runs, claims, rel))
    for rel in CHANGELOGS:
        path = root / rel
        if not path.is_file():
            continue
        claims = extract_changelog_claims(_read(path))
        if claims:
            errors.extend(f"{rel} (newest entry): {e}"
                          for e in compare_counts(runs, claims, f"{rel} newest entry"))
    errors.extend(scan_quarantine(root))
    for key in SUITES:
        print(f"RUN  {key:9s} "
              f"{fmt(runs[key][:2]) if runs.get(key) else '(unbound)'}")
    for err in errors:
        print(f"FAIL {err}")
    if errors:
        print(f"check_doc_counts.py: {len(errors)} claim mismatch(es) — FAIL (exit 1)")
        return 1
    print("check_doc_counts.py: every stated count equals this tree's runs (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
