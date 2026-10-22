#!/usr/bin/env python3
"""state_sanitize.py — find/redact credentials in runtime state (PLAN W0 Task 1.5).

The audit plugin records bash command text in `.vibeweaver/audit-state.json`.
A real host once accumulated ~70 passwords and a 7.4 MB state file; that is
the incident this tool exists for.

  python3 scripts/state_sanitize.py --check .vibeweaver/
  python3 scripts/state_sanitize.py --fix   .vibeweaver/

Check exits 1 when a credential-looking value is present. It NEVER prints the
value: only the file, JSON path and rule name. Fix replaces the value with
`[REDACTED:<kind>:<len>]` while preserving the command shape for diagnosis.

Credential rotation is still required after a leak: .gitignore prevents future
commits, it does not clean history.
"""
import argparse
import json
import pathlib
import re
import sys

# Reuse the canonical rule table (single source of truth with the secret scan).
HERE = pathlib.Path(__file__).resolve().parent
for _cand in (HERE, HERE.parent / "vibeweaver" / "scripts", HERE.parent.parent / "vibeweaver" / "scripts"):
    if (_cand / "scan_secrets.py").is_file() and str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))
from scan_secrets import RULES, ALLOW, _generic_is_benign

SSHPASS_RE = re.compile(r"(sshpass\s+-p\s+)(\S+)")
BEARER_RE = re.compile(r"(?i)(authorization:\s*bearer\s+)(\S{12,})")


def _redact_match(name, m):
    if name == "generic-credential":
        if not m.group("val"):
            return m.group(0)
        val = m.group("val")
        s, e = m.span("val")
        base = m.group(0)
        return base[: s - m.start()] + "[REDACTED:%s:%d]" % (name, len(val)) + base[e - m.start():]
    val = m.group(0)
    return "[REDACTED:%s:%d]" % (name, len(val))


def redact_text(text):
    if not isinstance(text, str) or not text:
        return text
    out = text
    for name, rx in RULES:
        def repl(m, _name=name):
            if _name == "generic-credential":
                if _generic_is_benign(m, out):
                    return m.group(0)
            if ALLOW.search(out[max(0, m.start() - 30):m.end() + 30]):
                return m.group(0)
            return _redact_match(_name, m)
        out = rx.sub(repl, out)
    out = SSHPASS_RE.sub(
        lambda m: m.group(0) if m.group(2).startswith("[REDACTED:")
        else m.group(1) + "[REDACTED:sshpass:%d]" % len(m.group(2)), out)
    out = BEARER_RE.sub(
        lambda m: m.group(0) if m.group(2).startswith("[REDACTED:")
        else m.group(1) + "[REDACTED:bearer:%d]" % len(m.group(2)), out)
    return out


def walk(value, path=""):
    """Yield (json-path, string) for every string leaf."""
    if isinstance(value, str):
        yield path or "$", value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, "%s.%s" % (path, k) if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, "%s[%d]" % (path, i))


def scrub_obj(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: scrub_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_obj(v) for v in value]
    return value


def scan_file(p):
    """Return [(json-path, kind)] without exposing values."""
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        # not JSON: scan line by line (backup/crash dumps)
        hits = []
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if redact_text(line) != line:
                    hits.append(("line %d" % i, "credential"))
        except OSError:
            pass
        return hits
    hits = []
    for jp, s in walk(data):
        if redact_text(s) != s:
            # name the rule without printing the value
            kind = "credential"
            for name, rx in RULES:
                m = rx.search(s)
                if m:
                    kind = name
                    break
            hits.append((jp, kind))
    return hits


def files_under(paths):
    out = []
    for raw in paths:
        p = pathlib.Path(raw)
        if p.is_dir():
            out.extend(sorted(x for x in p.rglob("*") if x.is_file()))
        elif p.is_file():
            out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--fix", action="store_true")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    files = files_under(args.paths or ["."])
    findings = []
    for p in files:
        for jp, kind in scan_file(p):
            findings.append({"file": str(p), "path": jp, "kind": kind})
    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings}, indent=2))
    elif findings:
        print("STATE-SANITIZE: %d credential finding(s)" % len(findings), file=sys.stderr)
        for f in findings:
            print("  - %s [%s] %s" % (f["file"], f["kind"], f["path"]), file=sys.stderr)
        print("  (values redacted from this report)", file=sys.stderr)

    if not args.check:
        fixed = 0
        for p in files:
            try:
                raw = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not raw:
                continue
            try:
                data = json.loads(raw)
                new = json.dumps(scrub_obj(data), separators=(",", ":"), ensure_ascii=False)
            except ValueError:
                new = redact_text(raw)
            if new != raw:
                tmp = p.with_suffix(p.suffix + ".tmp")
                tmp.write_text(new, encoding="utf-8")
                tmp.replace(p)
                fixed += 1
        if not args.json:
            print("STATE-SANITIZE: fixed %d file(s)" % fixed)
        return 0

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
