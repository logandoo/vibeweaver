"""G-DED artifact assertions — byte-level check of verification claims.
Canonical copy: vibeweaver skill `scripts/assert_artifacts.py`.
Mirrors COMPLETION_GATE.md §A4.4.1 minimum-check table (all 16 groups).
Group 12 enforces the A4.1 diagnosis clause; group 13 is a
claim-without-scope lint (approach modeled on J-Space Cognition Suite's
`ship` check at idea level; implementation here is original —
see repo README → Attribution). Groups 14-16 are change-wave content
gates: 14 secret scan, 15 test-change guard, 16 risk-tier review."""
import argparse, os, pathlib, re, subprocess, sys

FAILS = []
PASSES = 0
GIT_TIMEOUT = False

# Group 13 word sets, chosen for what vibeweaver logs actually overclaim with.
# CLAIM  — verbs that assert a verification result happened.
# COVER  — scope/evidence indicators: quantifiers, counts, artifact refs.
# A bare object name is not scope: "the endpoint is verified" names WHAT,
# not HOW MUCH was checked, so object nouns (endpoint/file/…) are excluded.
CLAIM = re.compile(
    r"\b(?:verified|confirmed|validated|proven|tested)\b|"
    r"\ball\s+(?:checks?|tests?)\s+pass(?:es|ed)?\b|\bchecks?\s+pass\b|"
    r"已验证|验证通过|已确认|确认无误|已测试|测试通过|已证明",
    re.I,
)
COVER = re.compile(
    r"\b(?:all|each|every|both)\b|"                     # quantifiers
    r"\b\d+\s*/\s*\d+\b|"                               # 3/3 fractions
    r"\bcriterion\s*#?\d+\b|\bcriteria\b|"              # criterion scope
    r"\bn\s*[<≤=]\s*\d+\b|"                             # bounded sweeps
    r"tests/[\w./-]+|\S+\.(?:png|mp4|webm|wav)\b|\S+\.trace\.log\b|"  # artifact refs
    r"\bcoverage\b|\bcovered\b|\bsweep\b|\bswept\b|"
    r"全部|所有|每个|每条|逐一|逐条|覆盖|边界|用例|场景|"
    r"包括|包含|至少|至多|最多|最少|随机",
    re.I,
)
STRUCT_LINE = re.compile(r"^(?:#{1,6}\s|>|\|{1,2}\s*-+|\s*$)")
EXEMPT_LINE = re.compile(r"(?:^- iter \d+ (?:PASS|FAIL):|^- Baseline verified GREEN|^- COV-\d+ skipped)")
FENCE = re.compile(r"^\s{0,3}(?:```|~~~)")

# --- groups 14-16: change-wave content gates (canonical spec:
# COMPLETION_GATE.md §A4.4.1 rows 14-16) -------------------------------
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs",
            ".java", ".sql", ".sh"}
SECRET_RES = [
    re.compile(r"AKIA[0-9A-Z]{16}"),                       # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|"
               r"xox[baprs]-[A-Za-z0-9-]{16,}|"
               r"sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{16,}"),  # GitHub/Slack/OpenAI/Anthropic tokens
]
# generic k = v: quoted literal values are candidates; UNQUOTED values
# containing `.`/`(`/`)` are references or calls (os.environ.get(…),
# process.env.X, config.password, self.x) — the SAFE handling pattern,
# never flagged. Values outside the base charset (spaces, !#%…) may
# escape — documented tradeoff, biased against false-blocking.
GENERIC_KV = re.compile(
    r"(?i)\b(?:api[_-]?key|apikey|secret|password|passwd|pwd|token|"
    r"private[_-]?key|access[_-]?key)\b[\"']?\s*[:=]\s*"
    r"(?P<q>[\"']?)(?P<v>[A-Za-z0-9_/+.\-]{12,})")
PLACEHOLDER = re.compile(r"(?i)example|sample|dummy|placeholder|changeme|"
                         r"redacted|fake|<[^>]+>")
ASSERT_LINE = re.compile(r"^\s*(?:assert\b|self\.assert|expect\s*\(|"
                         r"pytest\.raises|require\s*\(|def test_|it\s*\(|"
                         r"test\s*\(|func Test|@Test)")
TEST_DIR = re.compile(r"(^|/)(?:tests?|__tests__|spec)/")
RISK_PATH = re.compile(r"(?i)(^|/)(?:auth|security|payments?|billing|crypto|"
                       r"migrations?|permissions?|acl)(?:/|\.|_|$)")


def _git(root, *args):
    global GIT_TIMEOUT
    try:
        r = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True, timeout=20)
        return r.returncode, r.stdout
    except FileNotFoundError:
        return -1, ""
    except subprocess.TimeoutExpired:
        GIT_TIMEOUT = True
        return -2, ""


def wave_diff_text(root):
    """Change-wave diff: PER-COMMIT patches of newest `backup: before changes`
    commit..HEAD (a net range diff would hide intra-wave add-then-remove),
    else `git show HEAD`; plus uncommitted `git diff HEAD`. "" = no git repo."""
    rc, _ = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        return ""
    rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
                   "--grep=backup: before changes")
    parts = []
    if rc == 0 and sha.strip():
        _, d = _git(root, "log", "-p", "--format=", f"{sha.strip()}..HEAD")
        parts.append(d)
    else:
        _, d = _git(root, "show", "--format=", "HEAD")
        parts.append(d)
    _, d = _git(root, "diff", "HEAD")
    parts.append(d)
    return "\n".join(parts)


def untracked_files(root):
    """Untracked, non-gitignored files (never visible in git diff)."""
    rc, out = _git(root, "ls-files", "--others", "--exclude-standard")
    return [l for l in out.splitlines() if l.strip()] if rc == 0 else []


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_diff(text):
    """{path: [added, removed]} — added = [(new-file lineno, text)] via @@
    hunks; removed = [text]. Deleted files keep their `--- a/` path so
    removed lines and the path are retained (whole-file deletion must NOT
    fail-open the guards)."""
    files, cur, nline = {}, None, 0
    for line in text.splitlines():
        h = HUNK.match(line)
        if h:
            nline = int(h.group(1))
        elif line.startswith("--- a/"):
            cur = line[6:]
            files.setdefault(cur, [[], []])
        elif line.startswith("+++ b/"):
            cur = line[6:]
            files.setdefault(cur, [[], []])
        elif line.startswith("--- /dev/null"):
            cur = None
        elif line.startswith("+++ /dev/null"):
            pass                                # deleted file: keep a/ path
        elif cur and line.startswith("+"):
            files[cur][0].append((nline, line[1:]))
            nline += 1
        elif cur and line.startswith("-"):
            files[cur][1].append(line[1:])
        elif line.startswith(" "):
            nline += 1
    return files


def _is_test_code(path):
    p = pathlib.PurePosixPath(path)
    if p.suffix not in CODE_EXT or "assert_artifacts.py" in path:
        return False
    if TEST_DIR.search(path):
        return True
    n = p.name
    return (n.startswith("test_") or "_test." in n
            or ".test." in n or ".spec." in n)


def secret_scan(root):
    """Group 14 — secret scan. Returns (fails, warns). Only ADDED diff lines
    and untracked files; placeholder-marked lines exempt; .md warn-only;
    any assert_artifacts.py never scanned."""
    fails, warns = [], []

    def hit(path, lineno, text):
        if "assert_artifacts.py" in path or PLACEHOLDER.search(text):
            return
        found = any(rx.search(text) for rx in SECRET_RES)
        if not found:
            m = GENERIC_KV.search(text)
            found = bool(m) and (bool(m.group("q")) or
                                 not any(c in m.group("v") for c in ".()"))
        if found:
            (warns if path.endswith(".md") else fails).append(
                f"secret scan: {path}:{lineno}: credential-looking string "
                f"on an added line — {text.strip()[:50]!r} (A4.4 content gate)")

    for path, (added, _r) in parse_diff(wave_diff_text(root)).items():
        for lineno, l in added:
            hit(path, lineno, l)
    for rel in untracked_files(root):
        p = root / rel
        try:
            if not p.is_file() or p.stat().st_size > 1_000_000:
                continue
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, l in enumerate(t.splitlines(), 1):
            hit(rel, i, l)
    return fails, warns


def test_change_guard(root, vl):
    """Group 15 — test-change guard: REMOVED assertion lines in test code
    files require a `- test-change: <path> — <reason>` log line."""
    fails = []
    for path, (_a, removed) in parse_diff(wave_diff_text(root)).items():
        if not _is_test_code(path):
            continue
        n = sum(1 for l in removed if ASSERT_LINE.match(l))
        if n and not re.search(r"^- test-change:.*" + re.escape(path), vl, re.M):
            fails.append(
                f"test-change guard: {path}: {n} assertion line(s) removed "
                f"without a `- test-change:` justification in "
                f"verification_log.md (A4.8 test integrity)")
    return fails


def risk_tier(root):
    """Group 16 — risk-tier: diffs/untracked files touching risk-tier code
    paths require tests/review_package.md on disk."""
    paths = set(parse_diff(wave_diff_text(root))) | set(untracked_files(root))
    hits = sorted(p for p in paths
                  if pathlib.PurePosixPath(p).suffix in CODE_EXT
                  and RISK_PATH.search(p))
    rp = root / "tests" / "review_package.md"
    if hits and not (rp.exists() and rp.stat().st_size > 0):
        return [f"risk-tier: change-wave touches risk-tier path(s) "
                f"({', '.join(hits[:5])}) but tests/review_package.md "
                f"missing/empty — A4.9 review non-skippable (A4.9)"]
    return []


def check(ok: bool, msg: str):
    global PASSES
    PASSES += 1
    if not ok:
        FAILS.append(msg)


def read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def claim_without_coverage(vl: str):
    """Return violating (line_number, line) pairs: a claim verb on a prose line
    whose own line states no coverage scope. Fenced blocks, headings, tables
    and structured entries are exempt — see EXEMPT_LINE."""
    hits = []
    in_fence = False
    for i, line in enumerate(vl.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped or STRUCT_LINE.match(stripped) or EXEMPT_LINE.match(stripped):
            continue
        if CLAIM.search(stripped) and not COVER.search(stripped):
            hits.append((i, stripped[:80]))
    return hits


def main():
    global PASSES
    ap = argparse.ArgumentParser()
    ap.add_argument("--existing", action="store_true", help="Modify-Existing task: skip new-project §A5 design-doc + git checks")
    ap.add_argument("--backend-only", action="store_true", help="no UI: skip PAGE_DESIGN.html and project_build.sh checks")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    tests = root / "tests"
    vl = read(tests / "verification_log.md")
    acc = read(tests / "acceptance.md")

    # 1) verification_log — exists, has >=1 standard iteration entry (COV-1)
    check(vl and len(vl.strip()) > 0, "tests/verification_log.md missing or empty (COV-1)")
    check(bool(re.search(r"^- iter \d+ (PASS|FAIL):", vl, re.M)),
          "verification_log.md has no `- iter N PASS/FAIL:` entries (A4.1 Step 4)")

    # 2) acceptance.md — exists, first line cap/stall stop-condition (COV-7)
    check(bool(re.search(r"^>\s*cap=5\s+stall=3", acc, re.M)),
          "tests/acceptance.md missing first line `> cap=5  stall=3×` (COV-7)")

    # 3) screenshots cited in the log files must exist >0 bytes (A4.4)
    for png in re.findall(r"tests/(\S+\.png)", vl + "\n" + acc):
        p = tests / png
        check(p.exists() and p.stat().st_size > 0,
              f"screenshot claimed but missing/empty: tests/{png} (A4.4)")

    # 4) memory — MEMORY.md + >=1 topic file + index pointers (A7.9/A7.10)
    mem = root / "memory"
    idx_text = read(mem / "MEMORY.md")
    check(bool(idx_text), "memory/MEMORY.md missing (A7.10)")
    if idx_text:
        topics = sorted(mem.glob("*.md"))
        check(len(topics) >= 2, "memory/: MEMORY.md + >=1 topic file required (A7.9)")
        check(bool(re.search(r"\]\([^)]+\.md\)", idx_text)),
              "memory/MEMORY.md index has no topic-file pointers (A7.9)")
        check(any(p.name != "MEMORY.md" for p in topics),
              "memory/: at least one topic file besides MEMORY.md (A7.9)")

    # 5) scripts — start/stop/restart (+ project_build unless --backend-only) (A2/COV-2)
    #    exec-bit is only meaningful on POSIX; on Windows .sh files ride along
    #    and only their existence is enforceable.
    posix = os.name != "nt"
    for s in ["start.sh", "stop.sh", "restart.sh"]:
        sp = root / "script" / "linux" / s
        is_exec = (sp.stat().st_mode & 0o111) if posix else True
        check(sp.exists() and is_exec,
              f"script/linux/{s} missing or not executable (A2/COV-2)")
    if not args.backend_only:
        bp = root / "script" / "linux" / "project_build.sh"
        check(bp.exists(), "script/linux/project_build.sh missing (A2; use --backend-only if no UI)")

    # 6) git — new projects: repo exists with >=2 commits (C1 step 1/15, A9)
    if not args.existing:
        try:
            r = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
                               capture_output=True, text=True, timeout=20)
            rc, out = r.returncode, r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            rc, out = -1, ""
        n_commits = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
        check(rc == 0 and n_commits >= 2,
              f"new-project git repo needs >=2 commits (init + final); found {n_commits} (C1 step 1/15)")

    # 7) §A5 design docs — new projects (skipped with --existing) (A5 / C1 step 2)
    if not args.existing:
        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html"]:
            check((root / doc).exists(), f"new-project design doc missing: {doc} (A5 / C1 step 2)")
        if not args.backend_only:
            check((root / "PAGE_DESIGN.html").exists(),
                  "new-project design doc missing: PAGE_DESIGN.html (A5; use --backend-only if no UI)")

    # 8) README + requirements — new projects (skipped with --existing) (C1 step 15)
    if not args.existing:
        check(any((root / n).exists() for n in ["README.md", "README.html"]),
              "new-project README.md/README.html missing (C1 step 15)")
        check(any((root / n).exists() for n in ["requirements.txt", "package.json"]),
              "new-project requirements.txt/package.json missing (C1 step 15)")

    # 9) COV-9 — Modify-Existing tasks: baseline verdict recorded on disk (COV-9)
    if args.existing:
        check(bool(re.search(r"Baseline verified GREEN|COV-9 skipped", vl, re.M)),
              "tests/verification_log.md missing `- Baseline verified GREEN` or `- COV-9 skipped —` entry (COV-9)")

    # 10) A4.7b — workflow traces cited in the log must exist >0 bytes (A4.7b)
    for wf in re.findall(r"tests/workflows/(\S+?\.trace\.log)", vl):
        p = tests / "workflows" / wf
        check(p.exists() and p.stat().st_size > 0,
              f"workflow trace claimed but missing/empty: tests/workflows/{wf} (A4.7b)")

    # 11) A4.1 — video/audio evidence cited in the log must exist >0 bytes (A4.1 Step 2/3)
    for m in re.findall(r"tests/(\S+\.(?:webm|wav|mp4|mp3))", vl):
        p = tests / m
        check(p.exists() and p.stat().st_size > 0,
              f"media evidence claimed but missing/empty: tests/{m} (A4.1)")

    # 12) FAIL diagnosis clause — every failed iteration must carry its diagnosis
    #     (A4.1 Step 4 — a retry without its diagnosis is the same attempt again)
    for i, line in enumerate(vl.splitlines(), 1):
        if re.match(r"^- iter \d+ FAIL:", line.strip()):
            check("diagnosis:" in line,
                  f"verification_log.md line {i}: FAIL entry lacks `diagnosis:` clause (A4.1 Step 4)")

    # 13) claim-without-coverage — a verification claim must state what it covered
    #     (A4.4 Gate Function — "verified" without a stated scope is not a result)
    for i, snippet in claim_without_coverage(vl):
        check(False,
              f"verification_log.md line {i}: claim without stated coverage — {snippet!r} (A4.4 claim rule)")

    # 14) secret scan — the change-wave diff / untracked files must not ADD
    #     credential-looking lines (.md warn-only; placeholder-marked exempt)
    s14_fails, s14_warns = secret_scan(root)
    for w in s14_warns:
        print("WARN " + w)
    for f in s14_fails:
        check(False, f)

    # 15) test-change guard — removed test assertions need a logged reason
    for f in test_change_guard(root, vl):
        check(False, f)

    # 16) risk-tier — risk-tier code paths require the A4.9 review package
    for f in risk_tier(root):
        check(False, f)

    if GIT_TIMEOUT:
        print("WARN groups 14-16: a git call timed out — content gates ran "
              "on partial data (fail-open); re-run to confirm")

    if FAILS:
        print("ASSERT FAILURES (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print(f"assert_artifacts.py: all {PASSES} checks pass (exit 0)")


if __name__ == "__main__":
    main()
