#!/usr/bin/env python3
"""verify_skill.py — integrity check for the vibeweaver skill package.

Run from the repo root:  python3 verify_skill.py
Exit 0 = package coherent. Mirrors the discipline the skill imposes on
projects: the package is checked, not assumed.

Checks:
  1. every payload file present
  2. SKILL.md frontmatter (name/description, description length)
  3. SKILL.md entry budget (soft 1400 lines warn / hard 1600 lines fail)
  4. every relative markdown link in SKILL.md resolves (one level deep)
  5. companion files' relative links resolve
  6. scripts/assert_artifacts.py compiles + carries all 13 markers
  7. SKILL.md's own marker list matches the canonical script's 13
  8. install.sh / install.bat install the full file set
   9. payload JS syntax — both plugins + 3 helper scripts (node --check,
      when node is available)
"""
import pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
PAYLOAD = ROOT / "vibeweaver"

FAILS = []
WARNS = []
MARKERS = [
    "verification_log", "cap=5", "screenshot", "MEMORY.md", "start.sh",
    "git repo needs", "FLOW_DESIGN", "README", "Baseline verified GREEN",
    "workflow trace", "media evidence", "diagnosis:",
    "claim without stated coverage",
]
PAYLOAD_FILES = [
    "SKILL.md", "COMPLETION_GATE.md", "CODING_PRINCIPLES.md", "ENGINEERING_STD.md",
    "REFERENCE.md", "APPENDIX.md", "MEMORY_TEMPLATES.md", "MEMORY_RULES.md",
    "TESTING_PROTOCOLS.md",
    "scripts/assert_artifacts.py", "scripts/vibeweaver-audit-core.js",
    "scripts/audit_selftest.mjs", "scripts/mutation_sweep.mjs",
    "vibeweaver-gate.js", "vibeweaver-audit.js", "install.sh", "install.bat",
]
INSTALLED_DOCS = [
    "SKILL.md", "COMPLETION_GATE.md", "CODING_PRINCIPLES.md", "ENGINEERING_STD.md",
    "REFERENCE.md", "APPENDIX.md", "MEMORY_TEMPLATES.md", "MEMORY_RULES.md",
    "TESTING_PROTOCOLS.md",
]
JS_PAYLOAD = [
    "vibeweaver-gate.js", "vibeweaver-audit.js", "scripts/vibeweaver-audit-core.js",
    "scripts/audit_selftest.mjs", "scripts/mutation_sweep.mjs",
]
SOFT_BUDGET = 1400
HARD_BUDGET = 1600


def fail(msg):
    FAILS.append(msg)


def warn(msg):
    WARNS.append(msg)


def main():
    # 1) payload files
    for rel in PAYLOAD_FILES:
        p = PAYLOAD / rel
        if not p.is_file():
            fail("missing payload file: %s" % rel)
    if FAILS:
        return 1

    skill = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
    lines = skill.splitlines()

    # 2) frontmatter
    if not skill.startswith("---\n"):
        fail("SKILL.md does not start with YAML frontmatter")
        return 1
    m = re.match(r"^---\n(.*?)\n---\n", skill, re.S)
    if not m:
        fail("SKILL.md frontmatter is not closed")
        return 1
    fm = m.group(1)
    if not re.search(r"^name:\s*vibeweaver\s*$", fm, re.M):
        fail("SKILL.md frontmatter name must be 'vibeweaver'")
    dm = re.search(r"^description:\s*\|?\s*$", fm, re.M)
    if not dm:
        fail("SKILL.md frontmatter missing description")
    else:
        desc_block = "\n".join(l for l in fm[dm.end():].splitlines() if l.startswith("  "))
        if len(desc_block.strip()) > 1024:
            warn("SKILL.md description is %d chars (> 1024; Anthropic-hosted skills cap there — opencode accepts it)" % len(desc_block.strip()))

    # 3) entry budget
    if len(lines) > HARD_BUDGET:
        fail("SKILL.md entry budget exceeded: %d lines > %d (hard) — split into companions" % (len(lines), HARD_BUDGET))
    elif len(lines) > SOFT_BUDGET:
        warn("SKILL.md is %d lines (> soft budget %d) — prefer companion files for new detail" % (len(lines), SOFT_BUDGET))

    # 4)+5) relative markdown links resolve, directly from SKILL.md and each
    #       companion; and every companion is linked directly from SKILL.md
    #       (one level deep — no nested chains for the agent to walk)
    link_re = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    fence_re = re.compile(r"^\s{0,3}(?:```|~~~)")

    def live_lines(md):
        """Strip fenced code blocks — links inside examples are not links."""
        out = []
        in_fence = False
        for ln in md.read_text(encoding="utf-8").splitlines():
            if fence_re.match(ln):
                in_fence = not in_fence
                continue
            if not in_fence:
                out.append(ln)
        return "\n".join(out)

    md_files = [PAYLOAD / "SKILL.md"] + \
               [n for n in sorted(PAYLOAD.glob("*.md")) if n.name != "SKILL.md"]
    for md in md_files:
        for text, url in link_re.findall(live_lines(md)):
            if re.match(r"^[a-z]+: ?", url) or url.startswith("#") or url.startswith("<"):
                continue  # external or in-file anchor
            t = url.split("#", 1)[0].strip()
            if not t:
                continue
            if not (md.parent / t).exists():
                fail("%s links to missing file: %s" % (md.name, url))
    skill_linked = {url.split("#", 1)[0].strip() for text, url in link_re.findall(live_lines(PAYLOAD / "SKILL.md"))}
    for n in PAYLOAD.glob("*.md"):
        if n.name != "SKILL.md" and n.name not in skill_linked:
            fail("SKILL.md does not link its companion %s (one-level-deep rule)" % n.name)

    # 6) canonical assertion script
    script_p = PAYLOAD / "scripts" / "assert_artifacts.py"
    script = script_p.read_text(encoding="utf-8")
    try:
        subprocess.run([sys.executable, "-m", "py_compile", str(script_p)],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        fail("scripts/assert_artifacts.py does not compile")
    for mk in MARKERS:
        if mk not in script:
            fail("canonical assert script missing marker: %r" % mk)

    # 7) SKILL.md's marker list matches the script's
    sk_m = [mk for mk in MARKERS if mk in skill]
    if len(sk_m) != len(MARKERS):
        missing = [mk for mk in MARKERS if mk not in skill]
        fail("SKILL.md no longer lists all 13 markers (missing: %s)" % ", ".join(missing))

    # 8) installers carry the full set
    sh = (PAYLOAD / "install.sh").read_text(encoding="utf-8")
    for doc in INSTALLED_DOCS:
        if '"%s"' % doc not in sh:
            fail("install.sh does not install %s" % doc)
    if "scripts/assert_artifacts.py" not in sh:
        fail("install.sh does not install scripts/assert_artifacts.py")
    bat = (PAYLOAD / "install.bat").read_text(encoding="utf-8")
    for doc in INSTALLED_DOCS:
        if doc not in bat:
            fail("install.bat does not install %s" % doc)
    if "scripts\\assert_artifacts.py" not in bat:
        fail("install.bat does not install scripts\\assert_artifacts.py")

    # 9) plugin + helper script syntax (best effort — node optional locally, present in CI)
    node = shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory() as td:
            for i, rel in enumerate(JS_PAYLOAD):
                src = PAYLOAD / rel
                suffix = ".mjs" if rel.endswith(".mjs") else ".js"
                tmp = pathlib.Path(td) / (("payload_%d" % i) + suffix)
                tmp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                r = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True)
                if r.returncode != 0:
                    fail("payload syntax check failed for %s:\n" % rel + (r.stderr or r.stdout)[:400])
    else:
        warn("node not found — payload syntax check skipped (CI covers it)")

    if WARNS:
        for w in WARNS:
            print("[verify_skill] WARN: " + w)
    if FAILS:
        for f in FAILS:
            print("[verify_skill] FAIL: " + f)
        print("verify_skill.py: %d failure(s)" % len(FAILS))
        return 1
    print("verify_skill.py: package coherent (%d lines in SKILL.md, %d checks OK)" % (len(lines), 9))
    return 0


if __name__ == "__main__":
    sys.exit(main())
