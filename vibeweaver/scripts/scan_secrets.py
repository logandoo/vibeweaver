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
import os
import re
import subprocess
import sys
import tempfile
import threading
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
        r"(?i)(?<![A-Za-z0-9])(?P<key>(?:[A-Za-z0-9]{1,32}[_-]){0,4}"
        r"(?:api[_-]?key|apikey|secret|password|passwd|pwd|token|credential|"
        r"private[_-]?key|access[_-]?key)"
        r"(?:[_-][A-Za-z0-9]{1,32}){0,4})"
        r"\s*[=:]\s*(?P<q>[\"']?)(?P<val>[A-Za-z0-9+/_.-]{12,})[\"']?")),
]

ALLOW = re.compile(r"(?i)(example|placeholder|dummy|sample|redacted|\*\*\*|<[a-z_]+>|your[_-]|xxxx|changeme|test[_-]?key|fake)")

# W9 P0-1: the generic rule's false-positive boundaries. These are DATA
# shapes, not credentials:
#   - `- secret-approved: <path> — <reason>` is approval metadata (the generic
#     rule skips it; named key-shape rules still scan the line);
#   - `*_ALPHABET` / `*_CHARSET` / `*_CHARACTERS` are character-set constants;
#     `*_LENGTH` / `*_LEN` / `*_DIGITS` are benign only for numeric values;
#   - `/…` values are environment paths only for path-typed keys
#     (`PWD=/var/…`, `*_PATH`, `*_FILE`) — `api_key = /x/y` is NOT exempt;
#     other path prefixes (`~`, `$`, drive letters) cannot reach the value
#     class (no `~ $ : \`);
#   - an UNQUOTED value is a reference expression only when it is a call/index
#     (`getenv(`, `environ[...]`) or a dotted chain of identifiers rooted at a
#     known receiver (`os.`, `process.`, `config.`, `self.`) — NOT any dotted
#     value, so a prefixed key like `SG.abcdef…` is still detected.
APPROVAL_METADATA = re.compile(r"-\s*secret-approved:")
BENIGN_KEY = re.compile(
    r"(?i)(?:^|[_-])(?P<kind>alphabet|charset|characters|digits|length|len)$")
PATH_KEY = re.compile(r"(?i)(?:^|[_-])(?:pwd|path|dir|home|cwd|root|file)$")
PATH_VALUE = re.compile(r"^/")
REFERENCE_VALUE = re.compile(
    r"^(?:os|process|config|self|settings|env|this|window|globalThis|sys|import)"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def _generic_is_benign(m, body: str = "") -> bool:
    """W9 P0-1: shared verdict for a generic-credential regex match."""
    key = m.group("key") or ""
    val = m.group("val") or ""
    benign_key = BENIGN_KEY.search(key)
    if benign_key:
        kind = benign_key.group("kind").lower()
        if kind not in ("digits", "length", "len") or val.isdigit():
            return True
    if PATH_KEY.search(key) and PATH_VALUE.match(val):
        return True
    if not m.group("q"):
        tail = body[m.end():m.end() + 1] if body else ""
        if tail in ("(", "["):
            return True
        if REFERENCE_VALUE.match(val):
            return True
    return False


def match_line(body: str):
    """Return [(rule, start, end)] for one line; one shared path for text,
    diff, and group-14 parity (W9)."""
    approval = bool(APPROVAL_METADATA.search(body))
    hits = []
    for name, rx in RULES:
        m = rx.search(body)
        if not m:
            continue
        if name == "generic-credential" and (approval or _generic_is_benign(m, body)):
            continue
        if ALLOW.search(body[max(0, m.start() - 30):m.end() + 30]):
            continue
        hits.append((name, m.start(), m.end()))
    return hits

TEXT_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".json", ".toml", ".yaml", ".yml",
                 ".sh", ".md", ".txt", ".cfg", ".ini", ".tf"}
# TruffleHog's ".env suffix trap": Path(".env").suffix == "" — a bare .env is
# matched by NAME (and .env.* variants), not by suffix.
ENV_NAME = re.compile(r"^\.env($|\.)")


SKIP_DIRS = {
    ".git", ".vibeweaver", "node_modules", ".pnpm-store", ".venv", "venv",
    "__pycache__", "site-packages", "dist", "build", "target", "coverage",
    ".next", ".nuxt", ".cache", ".yarn", ".parcel-cache", "Library",
    "ms-playwright", "playwright-report", "test-results",
}
MAX_FILES = 20000
MAX_BYTES = 256 * 1024 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_DIFF_BYTES = 16 * 1024 * 1024
# Ignored files still deserve a secret scan when their NAME is a secret
# carrier (`.env`, keys, certs). Ignored dependency/build trees do not.
SECRET_NAME_RE = re.compile(r"(^\.env($|\.)|\.(pem|key|crt)$|^config\.local\.)")


def is_scannable(p: Path, *, ignore_skip_dirs: bool = False) -> bool:
    if not ignore_skip_dirs and any(part in SKIP_DIRS for part in p.parts):
        return False  # harness state / deps: .vibeweaver is a TRANSCRIPT store —
        # scanning echoes of inputs is a category error (it re-flags every
        # test literal the session ever saw)
    return p.is_file() and (p.suffix in TEXT_SUFFIXES
                            or bool(ENV_NAME.match(p.name))
                            or p.suffix in {".env", ".pem", ".key", ".crt"})


def scan_text(path: str, text: str, added_only: bool = False, prefix_len: int = 0):
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        body = line[prefix_len:] if prefix_len and line[:1] in "+-" else line
        if added_only and not line.startswith("+"):
            continue
        for name, _start, _end in match_line(body):
            findings.append((path, i, name))
    return findings


def _git_diff_bounded(range_spec: str):
    """Stream `git diff` with a hard byte cap (never materialize a 1.3GB
    incident diff first). Stderr goes to a temp file (a full pipe deadlocks);
    a watchdog kills a hung git at 60s. Returns (rc, bytes, stderr)."""
    err = tempfile.TemporaryFile()
    try:
        p = subprocess.Popen(["git", "diff", "-U0", range_spec],
                             stdout=subprocess.PIPE, stderr=err)
    except Exception as e:  # noqa: BLE001
        err.close()
        return 127, b"", str(e).encode()
    timer = threading.Timer(60, p.kill)
    timer.start()
    chunks = []
    total = 0
    try:
        while True:
            chunk = p.stdout.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DIFF_BYTES:
                p.kill()
                p.wait()
                return 2, b"", f"diff exceeds {MAX_DIFF_BYTES // (1024 * 1024)} MiB".encode()
            chunks.append(chunk)
        rc = p.wait()
    finally:
        timer.cancel()
    try:
        err.seek(0)
        errdata = err.read()
    finally:
        err.close()
    return rc, b"".join(chunks), errdata


def scan_diff(range_spec: str):
    rc, raw, err = _git_diff_bounded(range_spec)
    if rc != 0:
        print(f"scan_secrets.py: git diff failed (rc={rc}): "
              f"{err.decode('utf-8', 'replace').strip()[:200]} (exit 1)", file=sys.stderr)
        return None
    findings = []
    path = "(diff)"
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for name, _start, _end in match_line(line[1:]):
                findings.append((path, 0, name))
    return findings


def _git_paths(root: Path, args):
    """NUL-delimited git path list; None = not a git repo / git unavailable."""
    try:
        r = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    return [p.decode("utf-8", "replace") for p in r.stdout.split(b"\0") if p]


def iter_ignored_secrets(root: Path):
    """Ignored files whose NAME is a secret carrier (`.env*`, keys, certs).
    Git-aware enumeration intentionally omits ignored paths; this bounded walk
    restores the security net without re-entering dependency caches."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if SECRET_NAME_RE.search(name):
                p = Path(dirpath) / name
                if is_scannable(p, ignore_skip_dirs=True):
                    yield p


def iter_all(root: Path):
    """Git-aware enumeration: tracked + untracked non-ignored, plus ignored
    secret-bearing filenames. Never a raw filesystem walk over dependency
    caches. Non-git trees fall back to a pruned os.walk (fixture path)."""
    root = Path(root)
    if root.is_file():
        # An explicitly named file is always scanned, even under a directory
        # named build/dist/cache (ancestor names are not scope).
        if is_scannable(root, ignore_skip_dirs=True):
            yield root
        return
    tracked = _git_paths(root, ["ls-files", "-z"])
    untracked = _git_paths(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    if tracked is not None and untracked is not None:
        seen = set()
        for rel in tracked + untracked:
            p = root / rel
            # Git already decided scope. Do not let an ancestor directory
            # named `build/`/`dist/` suppress a tracked source file.
            if is_scannable(p, ignore_skip_dirs=True):
                seen.add(p.resolve())
                yield p
        for p in iter_ignored_secrets(root):
            if p.resolve() not in seen:
                seen.add(p.resolve())
                yield p
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            # os.walk already pruned SKIP_DIRS relative to the scan root;
            # an ancestor path component must not suppress the whole scan.
            if is_scannable(p, ignore_skip_dirs=True):
                yield p


def emit_findings(findings):
    for path, line, name in findings:
        loc = f"{path}:{line}" if line else path
        print(f"FINDING {loc}: {name}")
    if findings:
        print(f"scan_secrets.py: {len(findings)} finding(s) — do NOT commit; rotate if real (exit 1)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", default="", help="git diff range, e.g. main..HEAD or BASE..HEAD")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--all", default="", help="scan all text files under PATH")
    ap.add_argument("--approvals", default="tests/verification_log.md",
                    help="log carrying `- secret-approved: <path> — <reason>` lines")
    args = ap.parse_args()

    approved = set()
    apath = Path(args.approvals)
    if apath.is_file():
        try:
            approved = set(re.findall(
                r"^- secret-approved:\s*(\S+)\s+—", apath.read_text(errors="replace"), re.M))
        except OSError:
            approved = set()

    findings = []
    if args.diff or (not args.files and not args.all):
        rng = args.diff or "HEAD"
        diff_findings = scan_diff(rng if args.diff else "HEAD")
        if diff_findings is None:
            return 1
        findings += diff_findings
    for f in args.files:
        p = Path(f)
        if p.is_file():
            if p.stat().st_size > MAX_FILE_BYTES:
                print(f"scan_secrets.py: {p} exceeds {MAX_FILE_BYTES // (1024 * 1024)} MiB — "
                      f"not scanned (exit 1)", file=sys.stderr)
                return 1
            findings += scan_text(str(p), p.read_text(errors="replace"))
    if args.all:
        if not Path(args.all).exists():
            print(f"scan_secrets.py: --all path does not exist: {args.all} (exit 1)",
                  file=sys.stderr)
            return 1
        files = 0
        total = 0
        capped = []
        base = Path(args.all)
        for p in iter_all(base):
            try:
                rel = p.relative_to(base).as_posix()
            except ValueError:
                rel = p.name
            # Path approval is for ignored secret-CARRIER files (`.env*`,
            # keys/certs), never for an arbitrary tracked source file.
            if rel in approved and SECRET_NAME_RE.search(p.name):
                continue
            files += 1
            if files > MAX_FILES or total > MAX_BYTES:
                capped.append(f"scan budget at {files} files / {total // (1024 * 1024)} MiB")
                break
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    capped.append(f"{p} > {MAX_FILE_BYTES // (1024 * 1024)} MiB")
                    continue
                text = p.read_text(errors="replace")
            except OSError as e:
                capped.append(f"{p}: {e}")
                continue
            total += len(text.encode("utf-8", "replace"))
            findings += scan_text(str(p), text)
        if capped:
            emit_findings(findings)
            for line in capped[:5]:
                print(f"scan_secrets.py: not fully scanned — {line}", file=sys.stderr)
            print(f"scan_secrets.py: scan INCOMPLETE ({len(capped)} cap/skip event(s)) — "
                  f"cannot certify clean (exit 1)", file=sys.stderr)
            return 1

    if findings:
        emit_findings(findings)
        return 1
    print("scan_secrets.py: clean (named check: aws/github/slack/ai-keys/pem/jwt/generic-credential)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
