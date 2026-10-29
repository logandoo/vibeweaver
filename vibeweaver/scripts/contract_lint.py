#!/usr/bin/env python3
"""contract_lint.py — one-command contradiction / placeholder / size lint.

PLAN W0 Task 3 + Task 8 (minimum): the contract must be internally consistent
before a release. Checks:
  * COV-0 exists exactly once; COV numbering is 0..13 with no hole/duplicate
  * the legacy line-176 contradiction ("final answer" + "only tests/") is gone
  * precedence is explicit: COV-0 > line-176 pointer > COV-9
  * banned placeholders outside quotes/code fences
  * size caps: SKILL < 49 KB; companions <= 45 KB; bootstrap <= 2 KB
  * profiles/core presence is a warning until Task 9 lands
"""
import argparse
import json
import pathlib
import re
import sys

COV_RE = re.compile(r"^`COV-(\d+)\.", re.M)
COMPANIONS = (
    "COMPLETION_GATE.md", "AUDIT_PLUGIN.md", "CODING_PRINCIPLES.md", "ENGINEERING_STD.md",
    "REFERENCE.md", "APPENDIX.md", "MEMORY_TEMPLATES.md", "MEMORY_RULES.md",
    "TESTING_PROTOCOLS.md", "WORKFLOWS_EXTENDED.md", "VERIFICATION_UPGRADES.md",
)
BANNED = (
    "TBD", "handle edge cases", "similar to Task N", "appropriate validation",
)
SKIP_HINTS = ("placeholder", "no placeholders", "banned", "plan failure",
              "placeholders —", "placeholder scan", "never write",
              "each is a plan", "without actual test code")


def payload_root(root):
    if (root / "vibeweaver" / "SKILL.md").is_file():
        return root / "vibeweaver"
    return root


def _live_text(text):
    """Strip fenced/inline code and quoted spans: examples are not rules."""
    text = re.sub(r"```[\s\S]*?(?:```|$)", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r'"[^"\n]*"', "", text)
    text = re.sub(r"“[^”\n]*”", "", text)
    return text


def lint(root):
    root = pathlib.Path(root)
    pay = payload_root(root)
    errors = []
    warnings = []
    skill = pay / "SKILL.md"
    if not skill.is_file():
        return ["SKILL.md missing under %s" % pay], warnings
    text = skill.read_text(encoding="utf-8", errors="replace")

    cov0 = len(re.findall(r"^`COV-0\.", text, re.M))
    if cov0 != 1:
        errors.append("COV-0 must exist exactly once (found %d)" % cov0)
    nums = sorted(int(m) for m in COV_RE.findall(text))
    expected = list(range(0, 14))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        errors.append("COV numbering mismatch: missing=%s duplicate=%s" % (missing, dupes))
    if "Precedence: COV-0" not in text:
        errors.append("COV-0 precedence line missing (COV-0 > line-176 pointer > COV-9)")

    for i, line in enumerate(text.splitlines(), 1):
        if "final answer" in line and "only tests/" in line:
            errors.append("SKILL.md:%d still contains the legacy final-answer/only-tests contradiction" % i)

    for md in [skill] + [pay / c for c in COMPANIONS if (pay / c).is_file()]:
        body = md.read_text(encoding="utf-8", errors="replace")
        live = _live_text(body)
        for term in BANNED:
            recent = []
            for ln, line in enumerate(live.splitlines(), 1):
                ctx = " ".join(recent[-2:] + [line]).lower()
                if term.lower() in line.lower() and not any(h in ctx for h in SKIP_HINTS):
                    errors.append("%s:%d banned placeholder %r" % (md.name, ln, term))
                recent.append(line)

    size = skill.stat().st_size
    if size >= 49000:
        errors.append("SKILL.md is %d bytes (must be < 49000)" % size)
    for c in COMPANIONS:
        p = pay / c
        if p.is_file() and p.stat().st_size > 45000:
            errors.append("%s is %d bytes (companion cap 45000)" % (c, p.stat().st_size))
    boot = pay / "bootstrap.md"
    if boot.exists() and boot.stat().st_size > 2048:
        errors.append("bootstrap.md is %d bytes (cap 2048)" % boot.stat().st_size)

    core = (root / "profiles" / "core" / "SKILL.md") if (root / "profiles" / "core" / "SKILL.md").is_file() else (pay / "profiles" / "core" / "SKILL.md")
    if not core.is_file():
        errors.append("profiles/core/SKILL.md missing (Task 9)")
    elif len(core.read_text(encoding="utf-8", errors="replace")) // 4 > 4000:
        errors.append("profiles/core/SKILL.md exceeds 4k tokens")
    mini = (root / "vibeweaver-mini" / "SKILL.md") if (root / "vibeweaver-mini" / "SKILL.md").is_file() else (pay / "vibeweaver-mini" / "SKILL.md")
    if mini.is_file() and len(mini.read_text(encoding="utf-8", errors="replace")) // 4 > 2000:
        errors.append("vibeweaver-mini/SKILL.md exceeds 2k tokens")
    full_tokens = sum(len((pay / f).read_text(encoding="utf-8", errors="replace")) for f in ("SKILL.md",) + COMPANIONS if (pay / f).is_file()) // 4
    if full_tokens > 90000:
        errors.append("full contract is %d tokens (cap 90000)" % full_tokens)
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    errors, warnings = lint(pathlib.Path(args.root).resolve())
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    else:
        for w in warnings:
            print("WARN  " + w)
        for e in errors:
            print("CONFLICT  " + e)
        print("0 conflicts" if not errors else "%d conflicts" % len(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
