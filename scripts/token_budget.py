#!/usr/bin/env python3
"""token_budget.py — profile size guard (W1 Task 9).

Estimates tokens as chars/4 (documented approximation) and enforces:
core <= 4k, full <= 90k, mini <= 2k. `--check` exits 1 when a cap is exceeded.
"""
import argparse
import pathlib
import sys

CAPS = {"core": 4000, "full": 90000, "mini": 2000}

PROFILES = {
    "core": ("profiles/core/SKILL.md",),
    "full": ("SKILL.md",) + tuple(
        n for n in ("COMPLETION_GATE.md", "CODING_PRINCIPLES.md", "ENGINEERING_STD.md",
                    "REFERENCE.md", "APPENDIX.md", "MEMORY_TEMPLATES.md",
                    "MEMORY_RULES.md", "TESTING_PROTOCOLS.md",
                    "WORKFLOWS_EXTENDED.md", "VERIFICATION_UPGRADES.md")),
    "mini": ("vibeweaver-mini/SKILL.md",),
}


def payload_root(root):
    if (root / "vibeweaver" / "SKILL.md").is_file():
        return root / "vibeweaver"
    return root


def measure(root):
    pay = payload_root(root)
    out = []
    for name, files in PROFILES.items():
        chars = 0
        found = True
        for rel in files:
            p = pay / rel
            if not p.is_file():
                # mini is a sibling tree in the repo, not inside the payload
                alt = root / rel
                if alt.is_file():
                    p = alt
                else:
                    found = False
                    continue
            chars += len(p.read_text(encoding="utf-8", errors="replace"))
        out.append((name, chars // 4, CAPS[name], found))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--require-mini", action="store_true")
    args = ap.parse_args(argv)
    rows = measure(pathlib.Path(args.root).resolve())
    bad = []
    for name, tokens, cap, found in rows:
        status = "OK" if found and tokens <= cap else ("MISSING" if not found else "OVER")
        print(f"{name:5s} tokens={tokens:6d} cap={cap:6d} {status}")
        if found and tokens > cap:
            bad.append(name)
        if not found and args.require_mini and name == "mini":
            bad.append("mini-missing")
    if args.check:
        print("TOKEN-BUDGET " + ("OK" if not bad else "FAIL: " + ", ".join(bad)))
        return 0 if not bad else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
