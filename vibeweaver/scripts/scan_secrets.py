#!/usr/bin/env python3
"""scan_secrets.py — best-effort secret scan over a git diff or file list.

Usage:
  python3 scripts/scan_secrets.py                 # scan `git diff HEAD` added lines (wave diff)
  python3 scripts/scan_secrets.py --diff BASE..HEAD
  python3 scripts/scan_secrets.py --files path1 path2 ...
  python3 scripts/scan_secrets.py --all PATH      # scan every text file under PATH (working tree)

W3 (2026-10-15): the completion checklist runs BOTH named checks — the diff
scan (what this wave added) and `--all .` (what older waves swept in). A clean
diff proves nothing about pre-committed keys.
Exit 0 = clean. Exit 1 = findings (each printed as `FINDING <path>:<line>: <rule>`).
Best-effort only — a clean run is NOT proof that no secret exists (asymmetry
rule: establish absence with a named check, and this is one named check).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# C3c (2026-10-15): rule table aligned with gitleaks (72977e4/ddcc753) —
# modern OpenAI/Anthropic key shapes carry hyphenated segments the old
# `sk-(?:ant-)?[A-Za-z0-9]{20,}` missed (sk-ant-api03-/sk-proj-). The
# lookbehind keeps `disk-usage-...` from matching `sk-usage-...`.
RULES = [
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai-anthropic-key", re.compile(
        r"(?<![A-Za-z0-9])sk-(?:proj-|svcacct-|admin-|ant-api\d{2}-|ant-admin\d{2}-|ant-oat\d{2}-|ant-)[A-Za-z0-9_\-]{16,}"
        r"|(?<![A-Za-z0-9])sk-[A-Za-z0-9]{20,}"
        r"|sk-[A-Za-z0-9_\-]{16,}T3BlbkFJ")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("generic-credential", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|passwd|token|credential)\b\s*[=:]\s*[\"']?[A-Za-z0-9+/_-]{12,}[\"']?")),
]

ALLOW = re.compile(r"(?i)(example|placeholder|dummy|sample|redacted|\*\*\*|<[a-z_]+>|your[_-]|xxxx|changeme|test[_-]?key|fake)")

TEXT_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".json", ".toml", ".yaml", ".yml",
                 ".sh", ".md", ".txt", ".cfg", ".ini", ".tf"}
# TruffleHog's ".env suffix trap": Path(".env").suffix == "" — a bare .env is
# matched by NAME (and .env.* variants), not by suffix.
ENV_NAME = re.compile(r"^\.env($|\.)")


SKIP_DIRS = {".git", ".vibeweaver", "node_modules", ".venv", "venv", "__pycache__"}


def is_scannable(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return False  # harness state / deps: .vibeweaver is a TRANSCRIPT store —
        # scanning echoes of inputs is a category error (it re-flags every
        # test literal the session ever saw)
    return p.is_file() and (p.suffix in TEXT_SUFFIXES or bool(ENV_NAME.match(p.name)) or p.suffix == ".env")


def scan_text(path: str, text: str, added_only: bool = False, prefix_len: int = 0):
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        body = line[prefix_len:] if prefix_len and line[:1] in "+-" else line
        if added_only and not line.startswith("+"):
            continue
        for name, rx in RULES:
            m = rx.search(body)
            if m and not ALLOW.search(body[max(0, m.start() - 30):m.end() + 30]):
                findings.append((path, i, name))
    return findings


def scan_diff(range_spec: str):
    try:
        out = subprocess.run(["git", "diff", "-U0", range_spec], capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"git diff failed: {e}", file=sys.stderr)
        return []
    findings = []
    path = "(diff)"
    for line in out.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for name, rx in RULES:
                m = rx.search(line[1:])
                if m and not ALLOW.search(line[max(0, m.start() - 30):m.end() + 30]):
                    findings.append((path, 0, name))
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", default="", help="git diff range, e.g. main..HEAD or BASE..HEAD")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--all", default="", help="scan all text files under PATH")
    args = ap.parse_args()

    findings = []
    if args.diff or (not args.files and not args.all):
        rng = args.diff or "HEAD"
        findings += scan_diff(rng if args.diff else "HEAD")
    for f in args.files:
        p = Path(f)
        if p.is_file():
            findings += scan_text(str(p), p.read_text(errors="replace"))
    if args.all:
        for p in Path(args.all).rglob("*"):
            if is_scannable(p):
                findings += scan_text(str(p), p.read_text(errors="replace"))

    if findings:
        for path, line, name in findings:
            loc = f"{path}:{line}" if line else path
            print(f"FINDING {loc}: {name}")
        print(f"scan_secrets.py: {len(findings)} finding(s) — do NOT commit; rotate if real (exit 1)")
        return 1
    print("scan_secrets.py: clean (named check: aws/github/slack/ai-keys/pem/jwt/generic-credential)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
