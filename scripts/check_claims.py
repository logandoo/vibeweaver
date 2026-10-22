#!/usr/bin/env python3
"""check_claims.py — every README/current-CHANGELOG count/effect claim is bound.

W1 Task 11. A claim is bound when `release/claims.json` has an entry whose
`token` matches the literal; effect claims (`%`, `+`) additionally require
`n`, `seeds`, and `ci` — otherwise the claim is `directional` at best and must
not be published as a verified effect.
"""
import argparse
import json
import pathlib
import re
import sys

TOKEN_RE = re.compile(r"\b\d+/\d+\b|\+?\d+(?:\.\d+)?%")
FENCE_RE = re.compile(r"^```")


def payload_root(root):
    return root / "vibeweaver" if (root / "vibeweaver" / "SKILL.md").is_file() else root


def live_text(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    out, fence = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line.strip()):
            fence = not fence
            continue
        if not fence:
            out.append(line)
    return "\n".join(out)


def current_changelog(path):
    """Newest entry = the FIRST `## ` block after the preamble (reverse-chronological)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"(?m)^(?=## )", text)
    for part in parts[1:]:
        if part.strip():
            return part
    return parts[-1] if parts else ""


def tokens_of(text):
    return sorted(set(TOKEN_RE.findall(text)))


def check(root):
    root = pathlib.Path(root)
    reg = root / "release" / "claims.json"
    if not reg.is_file():
        return ["release/claims.json missing"]
    data = json.loads(reg.read_text(encoding="utf-8"))
    claims = {c.get("token"): c for c in data.get("claims", []) if c.get("token")}
    errors = []
    for name in ("README.md", "README_zh.md"):
        p = root / name
        if p.is_file():
            for tok in tokens_of(live_text(p)):
                if tok not in claims:
                    errors.append(f"{name}: unbound claim {tok}")
    for name in ("CHANGELOG.md", "CHANGELOG_zh.md"):
        p = root / name
        if p.is_file():
            for tok in tokens_of(current_changelog(p)):
                if tok not in claims:
                    errors.append(f"{name} (current entry): unbound claim {tok}")
    for tok, c in claims.items():
        effect = ("%" in tok) or tok.startswith("+")
        if effect:
            if c.get("n") in (None, "") or c.get("seeds") in (None, "") or not c.get("ci"):
                errors.append(f"effect claim {tok} ({c.get('id')}): missing n/seeds/ci")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    errors = check(pathlib.Path(args.root).resolve())
    if args.json:
        print(json.dumps({"ok": not errors, "unbound": errors}, indent=2))
    else:
        for e in errors:
            print("UNBOUND  " + e)
        print("0 unbound" if not errors else f"{len(errors)} unbound")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
