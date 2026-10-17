"""G-DED artifact assertions — byte-level check of verification claims.
Canonical copy: vibeweaver skill `scripts/assert_artifacts.py`.
Mirrors COMPLETION_GATE.md §A4.4.1 minimum-check table (groups 1-21).
Group 12 enforces the A4.1 diagnosis clause; group 13 is a
claim-without-scope lint (approach modeled on J-Space Cognition Suite's
`ship` check at idea level; implementation here is original —
see repo README → Attribution). Groups 14-16 are change-wave content
gates: 14 secret scan (`vw-approved` marker ⇄ `- secret-approved:` log
pairing), 15 test-change guard, 16 risk-tier review. Project profiles
(tests/project_profile.json or --profile) declaratively skip groups that
are structurally N/A for the project kind (service/UI/new-project) —
a profile never weakens an applicable group. `--class DOC|CONFIG|CODE`
(COV-13 / §V11, or the log's `- class:` basis line) N/A's the memory (4)
and service-lifecycle (5) groups for the classes whose path card has no
such risk."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, sys

# Deterministic output encoding (2026-10-17 windows/CI): the locale encoding
# is cp1252/ascii on non-UTF-8 systems while every evidence string here is
# UTF-8 — `print` raised UnicodeEncodeError mid-run (the A4 "assert failed"
# class), and child-output decoding raised UnicodeDecodeError in reader
# threads. Consumers (gate/audit plugin, node harness) decode our stdout as
# UTF-8. errors="replace": the checker must never die on odd bytes.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

FAILS = []   # [{"code","severity","detail"}] — machine-readable per D4 (--json)
WARN_LINES = []
CUR_GROUP = "misc"
UNTRACKED_LIMIT = 2000      # path-count ceiling: the incident's 45k pnpm files
UNTRACKED_TOTAL = 0
WAVE_TOO_LARGE = ""         # non-empty = refuse to materialize the wave diff
WAVE_CACHE = {}
GIT_SIZE_WARN_KIB = 200 * 1024
GIT_SIZE_FAIL_KIB = 1024 * 1024
BLOB_WARN = 10 * 1024 * 1024
BLOB_FAIL = 40 * 1024 * 1024
VENDOR_RE = re.compile(
    r"(^|/)(?:node_modules|\.pnpm-store|\.venv|venv|site-packages|"
    r"__pycache__|\.next|\.nuxt|coverage|ms-playwright|playwright-report|"
    r"test-results)(?:/|$)")
BUILD_RE = re.compile(r"(^|/)(?:dist|build|target|\.yarn/cache)(?:/|$)")
SECRET_NAME_RE = re.compile(r"(^\.env($|\.)|\.(pem|key|crt)$|^config\.local\.)")
NODE_MANIFESTS = ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml",
                  "yarn.lock", "package-lock.json")
PY_MANIFESTS = ("requirements.txt", "pyproject.toml", "Pipfile",
                "poetry.lock", "setup.py")


def group(code: str):
    global CUR_GROUP
    CUR_GROUP = code


def warn(msg: str, code: str = ""):
    WARN_LINES.append({"code": code or CUR_GROUP, "detail": msg})
PASSES = 0
GIT_TIMEOUT = False
UNTRACKED_ERROR = 0

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
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),                  # Google API key
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
               r"xox[baprs]-[A-Za-z0-9-]{16,}|"
               # C3c rule-table parity with scripts/scan_secrets.py: the
               # lookbehind keeps `disk-usage-…`/`task-…` from matching
               # `sk-usage-…`; hyphenated key segments stay covered.
               r"(?<![A-Za-z0-9])sk-(?:proj-|svcacct-|admin-|ant-api\d{2}-|ant-admin\d{2}-|ant-oat\d{2}-|ant-)?[A-Za-z0-9_\-]{16,}"),
]
# generic k = v: quoted literal values are candidates; UNQUOTED values
# containing `.`/`(`/`)` are references or calls (os.environ.get(…),
# process.env.X, config.password, self.x) — the SAFE handling pattern,
# never flagged. Values outside the base charset (spaces, !#%…) may
# escape — documented tradeoff, biased against false-blocking.
GENERIC_KV = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:[A-Za-z0-9]{1,32}[_-]){0,4}"
    r"(?:api[_-]?key|apikey|secret|password|passwd|pwd|token|"
    r"private[_-]?key|access[_-]?key)(?:[_-][A-Za-z0-9]{1,32}){0,4}"
    r"[\"']?\s*[:=]\s*(?P<q>[\"']?)(?P<v>[A-Za-z0-9_/+.\-]{12,})")
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
                           capture_output=True, encoding="utf-8", errors="replace", timeout=20)
        return r.returncode, r.stdout
    except FileNotFoundError:
        return -1, ""
    except subprocess.TimeoutExpired:
        GIT_TIMEOUT = True
        return -2, ""


def _unquote_git(p: str) -> str:
    """Decode git's C-quoted path ("a\\tb" / octal UTF-8 escapes) to the
    real filename (dsh 2026-09-30 review; mainline merge 2026-10-15b)."""
    if len(p) < 2 or p[0] != '"' or p[-1] != '"':
        return p
    body = p[1:-1]
    simple = {"t": 9, "n": 10, "a": 7, "b": 8, "f": 12, "v": 11, "\\": 0x5C, '"': 0x22}
    out = bytearray()
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n:
            nxt = body[i + 1]
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if nxt in "01234567" and i + 3 < n and all(c in "01234567" for c in body[i + 2:i + 4]):
                out.append(int(body[i + 1:i + 4], 8))
                i += 4
                continue
            out.append(ord(nxt))
            i += 2
            continue
        out.extend(ch.encode("utf-8"))
        i += 1
    return out.decode("utf-8", "replace")


def _wave_paths(root, base):
    """Path list for the change wave — cheap preflight before `git log -p`."""
    paths = set()
    if base:
        rc, out = _git(root, "log", "--name-only", "--format=", f"{base}..HEAD")
    else:
        rc, out = _git(root, "show", "--name-only", "--format=", "HEAD")
    if rc == 0:
        paths.update(l for l in out.splitlines() if l.strip())
    for args in (["diff", "--name-only", "HEAD"],
                 ["diff", "--cached", "--name-only"]):
        rc, out = _git(root, *args)
        if rc == 0:
            paths.update(l for l in out.splitlines() if l.strip())
    return paths


def wave_diff_text(root):
    """Change-wave diff: PER-COMMIT patches of newest `backup: before changes`
    commit..HEAD (a net range diff would hide intra-wave add-then-remove),
    else `git show HEAD`; plus uncommitted `git diff HEAD`. "" = no git repo.

    Bounded by PATH COUNT before materializing patches (2026-10-18 incident:
    45k pnpm paths / 1.3GB wave -> OOM). A too-large wave is a hard failure,
    not a silently empty diff."""
    global WAVE_TOO_LARGE
    key = str(root)
    if key in WAVE_CACHE:
        return WAVE_CACHE[key]
    rc, _ = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        WAVE_CACHE[key] = ""
        return ""
    rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
                   "--grep=backup: before changes")
    base = sha.strip() if rc == 0 and sha.strip() else ""
    paths = _wave_paths(root, base)
    if len(paths) > UNTRACKED_LIMIT:
        WAVE_TOO_LARGE = f"{len(paths)} paths > {UNTRACKED_LIMIT}"
        WAVE_CACHE[key] = ""
        return ""
    parts = []
    if base:
        _, d = _git(root, "log", "-p", "--format=", f"{base}..HEAD")
        parts.append(d)
    else:
        _, d = _git(root, "show", "--format=", "HEAD")
        parts.append(d)
    _, d = _git(root, "diff", "HEAD")
    parts.append(d)
    text = "\n".join(parts)
    if len(text.encode("utf-8", "replace")) > 16 * 1024 * 1024:
        WAVE_TOO_LARGE = f"diff {len(text)} bytes > 16 MiB"
        text = ""
    WAVE_CACHE[key] = text
    return text


def untracked_files(root):
    """Untracked, non-gitignored files (never visible in git diff).

    Returns at most UNTRACKED_LIMIT paths; UNTRACKED_TOTAL preserves the real
    count so group 21 can fail fast instead of walking a 45k-file tree."""
    global UNTRACKED_TOTAL, UNTRACKED_ERROR
    rc, out = _git(root, "ls-files", "--others", "--exclude-standard")
    if rc != 0:
        UNTRACKED_ERROR = rc
        return []
    UNTRACKED_ERROR = 0
    lines = [_unquote_git(l) for l in out.splitlines() if l.strip()]
    # Keep the MAX observed count: a later transient failure/empty result must
    # not erase an earlier flood observation.
    UNTRACKED_TOTAL = max(UNTRACKED_TOTAL, len(lines))
    return lines[:UNTRACKED_LIMIT]


def non_git_text_files(root, limit=2000):
    """Bounded source/config walk for non-git projects (group 14 fallback)."""
    out = []
    skip = {".git", ".vibeweaver", "node_modules", ".pnpm-store", ".venv",
            "venv", "site-packages", "__pycache__", "dist", "build", "target",
            "coverage", ".next", ".nuxt", ".cache", "Library",
            "ms-playwright", "playwright-report", "test-results"}
    exts = CODE_EXT | {".env", ".pem", ".key", ".crt", ".json", ".toml",
                       ".yaml", ".yml", ".ini", ".cfg", ".txt"}
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for name in filenames:
                p = pathlib.Path(dirpath) / name
                if p.suffix in exts or SECRET_NAME_RE.search(name):
                    out.append(str(p.relative_to(root)))
                    if len(out) >= limit:
                        return out
    except OSError:
        pass
    return out


def ignored_secret_files(root):
    """Ignored files whose NAME is a secret carrier (`.env*`, keys, certs).
    `.gitignore` is prevention, not a blindfold — group 14 must still scan
    these, while dependency/build caches stay excluded."""
    out = []
    skip = {".git", ".vibeweaver", "node_modules", ".pnpm-store", ".venv",
            "venv", "site-packages", "__pycache__", "dist", "build", "target",
            "coverage", ".next", ".nuxt", ".cache", "Library",
            "ms-playwright", "playwright-report", "test-results"}
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for name in filenames:
                if SECRET_NAME_RE.search(name):
                    p = pathlib.Path(dirpath) / name
                    try:
                        if p.is_file() and p.stat().st_size <= 1_000_000:
                            out.append(str(p.relative_to(root)))
                    except OSError:
                        pass
    except OSError:
        pass
    return out


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
            # review R-I2: git C-quotes odd names ("tests/caf\303\251.py")
            # and pads space-names with a trailing tab — normalize both
            cur = _unquote_git(line[6:].rstrip("\t"))
            files.setdefault(cur, [[], []])
        elif line.startswith("+++ b/"):
            cur = _unquote_git(line[6:].rstrip("\t"))
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


def secret_scan(root, vl=""):  # vl = CURRENT task block (approval scoping)
    """Group 14 — secret scan. Returns (fails, warns). Only ADDED diff lines
    and untracked files; placeholder-marked lines exempt; .md warn-only;
    any assert_artifacts.py never scanned. A `vw-approved` inline marker
    exempts a credential line ONLY when verification_log.md carries the
    path-scoped pairing `- secret-approved: <path> — <reason>` (marker count
    per path must be ≤ approvals for that path — same binding shape as group
    15's `- test-change: <path>`). A bare mention of the marker on a line
    that matches no credential pattern is a no-op (prose mentions never
    trip the gate). Pairing failures FAIL regardless of file type (the
    .md warn-only rule applies only to plain unmarked secrets)."""
    fails, warns, marker_paths = [], [], {}

    def hit(path, lineno, text):
        if "assert_artifacts.py" in path or PLACEHOLDER.search(text):
            return
        found = any(rx.search(text) for rx in SECRET_RES)
        if not found:
            m = GENERIC_KV.search(text)
            found = bool(m) and (bool(m.group("q")) or
                                 bool(not any(c in m.group("v") for c in ".()")))
        if not found:
            return
        if re.search(r"vw-approved", text, re.I):
            marker_paths[path] = marker_paths.get(path, 0) + 1
            return
        (warns if path.endswith(".md") else fails).append(
            f"secret scan: {path}:{lineno}: credential-looking string "
            # review A4/re-review R3: NEVER echo any matched content (this
            # detail is routed into gate block messages / session logs) —
            # cite shape only (length), zero secret material
            f"on an added line — {len(text.strip())} chars matched (redacted) (A4.4 content gate)")

    for path, (added, _r) in parse_diff(wave_diff_text(root)).items():
        for lineno, l in added:
            hit(path, lineno, l)
    approved_files = set(re.findall(r"^- secret-approved:\s*(\S+)\s+—", vl, re.M))
    ignored = [p for p in ignored_secret_files(root) if p not in approved_files]
    rc_git, _ = _git(root, "rev-parse", "--git-dir")
    fallback = non_git_text_files(root) if rc_git != 0 else []
    scan_paths = list(dict.fromkeys(untracked_files(root) + ignored + fallback))
    for rel in scan_paths:
        p = root / rel
        try:
            if not p.is_file() or p.stat().st_size > 1_000_000:
                continue
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, l in enumerate(t.splitlines(), 1):
            hit(rel, i, l)
    for mpath, cnt in sorted(marker_paths.items()):
        approvals = len(re.findall(
            r"^- secret-approved:\s*" + re.escape(mpath) + r"(?![\w.\-])", vl, re.M))
        if approvals < cnt:
            fails.append(
                f"secret scan: {mpath}: {cnt} `vw-approved` marker line(s) but "
                f"{approvals} matching `- secret-approved: {mpath}` line(s) in "
                f"verification_log.md — every approved secret needs its own "
                f"path-scoped approval (A4.4 content gate)")
    return fails, warns


SKIP_MARKER = re.compile(r"@pytest\.mark\.(?:skip|xfail)|@unittest\.skip|\b(?:it|test|describe|this)\.skip|\bxfail\s*\(|\bxtest\b|\bskipTest\s*\(")
TEST_BASENAMES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg",
                  "jest.config.js", "jest.config.ts", "vitest.config.ts",
                  "vitest.config.js"}


def test_change_guard(root, vl):  # vl = CURRENT task block (license scoping, review R-I2)
    """Group 15 — test-change guard: REMOVED assertion lines in test code
    files require a `- test-change: <path> — <reason>` log line."""
    fails = []
    _diff = parse_diff(wave_diff_text(root))
    _added_by = {p: a for p, (a, _r) in _diff.items()}
    for path, (_a, removed) in _diff.items():
        if not _is_test_code(path) and os.path.basename(path) not in TEST_BASENAMES:
            continue
        n = sum(1 for l in removed if ASSERT_LINE.match(l))
        if n and not re.search(r"^- test-change:.*" + re.escape(path), vl, re.M):
            fails.append(
                f"test-change guard: {path}: {n} assertion line(s) removed "
                f"without a `- test-change:` justification in "
                f"verification_log.md (A4.8 test integrity)")
    # C3b (P1, BL-13): skip/xfail markers and test-runner config changes are
    # test weakenings too — each needs its `- test-change:` reason.
    for path, added in _added_by.items():
        if not _is_test_code(path) and os.path.basename(path) not in TEST_BASENAMES:
            continue
        if os.path.basename(path) in TEST_BASENAMES and not re.search(
                r"^- test-change:.*" + re.escape(path), vl, re.M):
            fails.append(f"{path}: test-runner config (conftest/pytest.ini/tox.ini/…) changed "
                         f"with no `- test-change: {path} — <reason>` line (C3b)")
            continue
        if any(SKIP_MARKER.search(l) for _n, l in added) and not re.search(
                r"^- test-change:.*" + re.escape(path), vl, re.M):
            fails.append(f"{path}: adds skip/xfail-style markers with no `- test-change: {path} — <reason>` "
                         f"line (C3b — a skipped test is a weakened test)")
    # C3b hash baseline: a test file that differs from the SEALED baseline
    # (tests/test_baseline.json, written only by scripts/evidence_seal.py)
    # needs a reason — this also catches weakenings committed BEFORE the wave
    # anchor (invisible to the diff window). Missing baseline + test-code
    # files in the wave: treated as a test change (BL-13 — no silent rebuild).
    try:
        _bl = json.loads(read(root / "tests" / "test_baseline.json") or "{}")
    except Exception:
        _bl = {}
    _bl_exists = (root / "tests" / "test_baseline.json").exists()
    _touched = {p for p in list(_diff.keys()) + untracked_files(root)
                if _is_test_code(p) or os.path.basename(p) in TEST_BASENAMES}
    if _bl_exists:
        for path in sorted(_touched):
            cur = hashlib.sha256((root / path).read_bytes()).hexdigest() if (root / path).is_file() else None
            if cur != _bl.get(path) and not re.search(r"^- test-change:.*" + re.escape(path), vl, re.M):
                fails.append(f"{path}: differs from the sealed test baseline and no `- test-change: {path} — <reason>` "
                             f"line licenses it (C3b hash baseline)")

    return fails



def code_fingerprint(root):
    """digest of wave code content — SHARED CONTRACT with
    scripts/evidence_seal.py: identical ext set AND identical file-set
    derivation (backup..HEAD + uncommitted + untracked; review R-I2)."""
    rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
                   "--grep=backup: before changes")
    paths = set()
    if rc == 0 and sha.strip():
        _, out = _git(root, "diff", "--name-only", f"{sha.strip()}..HEAD")
        paths.update(l.strip() for l in out.splitlines() if l.strip())
    _, out = _git(root, "diff", "--name-only", "HEAD")
    paths.update(l.strip() for l in out.splitlines() if l.strip())
    paths.update(untracked_files(root))
    parts = []
    for rel in sorted(_unquote_git(r) for r in paths):
        ext = os.path.splitext(rel)[1].lower()
        if ext not in FINGERPRINT_EXT or rel.startswith("tests/") or "assert_artifacts.py" in rel or "evidence_seal.py" in rel:
            continue
        fp = root / rel
        parts.append(f"{rel}:{hashlib.sha256(fp.read_bytes()).hexdigest() if fp.is_file() else 'gone'}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


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



# --- C1/C2 (P1, 2026-10-15): derived task class + evidence media validation
# fingerprint inputs — SHARED CONTRACT with evidence_seal.py (38 kinds)
FINGERPRINT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs",
                   ".java", ".sql", ".c", ".cc", ".cpp", ".h", ".hpp", ".kt",
                   ".swift", ".php", ".rb", ".cs", ".sh", ".bash", ".bat",
                   ".ps1", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg",
                   ".conf", ".tf", ".tfvars", ".xml", ".css", ".scss", ".sass",
                   ".less"}
CODE_KIND_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs",
                 ".java", ".sql", ".c", ".cc", ".cpp", ".h", ".hpp", ".kt",
                 ".swift", ".php", ".rb", ".cs"}
CONFIG_KIND_EXT = {".sh", ".bash", ".bat", ".ps1", ".toml", ".yaml", ".yml",
                   ".json", ".ini", ".cfg", ".conf", ".tf", ".tfvars", ".xml",
                   ".css", ".scss", ".sass", ".less"}
DOC_KIND_EXT = {".md", ".txt", ".rst", ".adoc", ".tex", ".docx", ".doc",
                ".xlsx", ".xls", ".pptx", ".ppt", ".pdf", ".odt", ".ods",
                ".odp", ".rtf", ".epub"}


def derive_class(paths):
    """C1 (§V11.2 ladder, first match by FILE KIND — never self-recollection):
    CODE (logic-bearing source, incl. behavior tests) > CONFIG (config/scripts/
    markup/CI) > DOC (prose · docs/ · memory/ · office assets). Returns
    (class, summary) or ("", "") when the wave names no classifiable file.
    Markup lives under CONFIG only when it is NOT under docs/ (design-doc
    HTML is a DOC asset — §V11.9)."""
    buckets = {"CODE": [], "CONFIG": [], "DOC": []}
    for pth in paths:
        p = pth.replace("\\", "/")
        ext = os.path.splitext(p)[1].lower()
        base = os.path.basename(p).lower()
        if p in ("tests/assert_artifacts.py", "tests/evidence_seal.py"):
            continue  # tooling copies (fixtures ship them) — not task code
        if ext in CODE_KIND_EXT:
            buckets["CODE"].append(pth)
        elif ext in DOC_KIND_EXT or "/docs/" in "/" + p or p.startswith("docs/") or "/memory/" in "/" + p or p.startswith("memory/"):
            buckets["DOC"].append(pth)
        elif ext in CONFIG_KIND_EXT or base in ("dockerfile", "makefile", "jenkinsfile") or p.startswith(".github/"):
            buckets["CONFIG"].append(pth)
    for kind in ("CODE", "CONFIG", "DOC"):
        if buckets[kind]:
            # counts + kinds only — never file names (S11b: downstream
            # negative checks scan the output; names also leak paths)
            exts = sorted({os.path.splitext(x)[1].lower() or os.path.basename(x).lower() for x in buckets[kind]})
            return kind, f"{len(buckets[kind])} file(s) kinds {'/'.join(exts[:5])}"
    return "", ""


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def media_probe(path: pathlib.Path):
    """C2 (2026-10-15): (ok, detail) — magic-bytes per media kind. A 1-byte
    'screenshot' named *.png is not evidence (the old st_size>0 check let it
    through). PNG additionally reports IHDR dimensions."""
    try:
        with path.open("rb") as fh:
            head = fh.read(4096)
    except OSError as exc:
        return False, f"unreadable ({exc})"
    ext = path.suffix.lower()
    if ext == ".png":
        if not head.startswith(PNG_MAGIC):
            return False, "not a PNG (bad magic bytes)"
        if len(head) < 24 or head[12:16] != b"IHDR":
            return False, "PNG without IHDR chunk"
        w, h = __import__("struct").unpack(">II", head[16:24])
        return True, f"PNG {w}x{h}"
    if ext == ".webm":
        ok = head.startswith(b"\x1a\x45\xdf\xa3")
        return ok, "WebM/EBML" if ok else "not WebM (bad magic bytes)"
    if ext == ".wav":
        ok = len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
        return ok, "WAV/RIFF" if ok else "not WAV (bad magic bytes)"
    if ext in (".mp4", ".m4v", ".mov"):
        ok = len(head) >= 12 and head[4:8] == b"ftyp"
        return ok, "MP4/ftyp" if ok else "not MP4 (bad ftyp)"
    if ext == ".mp3":
        ok = head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
        return ok, "MP3" if ok else "not MP3 (bad magic)"
    return True, "untyped evidence (existence only)"


def png_dims(path: pathlib.Path):
    try:
        with path.open("rb") as fh:
            head = fh.read(24)
        if not head.startswith(PNG_MAGIC) or len(head) < 24 or head[12:16] != b"IHDR":
            return None
        return __import__("struct").unpack(">II", head[16:24])
    except OSError:
        return None


_BASH_EXE = None
_BASH_PROBED = False


def _bash_exe():
    """Resolve a WORKING bash, once per process (2026-10-17, windows CI):
    `subprocess.run(["bash"], ...)` resolves `bash` to the System32 WSL stub
    before Git Bash — the stub exits non-zero with EMPTY stderr when no WSL
    distro is registered, which looked like "bash -n failed" on every .sh.
    Probe candidates with `bash -c 'exit 0'` and fall back to the standard
    Git for Windows paths; VIBEWEAVER_BASH overrides. None = no parser
    (fail-closed at the call site)."""
    global _BASH_EXE, _BASH_PROBED
    if _BASH_PROBED:
        return _BASH_EXE
    _BASH_PROBED = True
    cands = []
    if os.environ.get("VIBEWEAVER_BASH"):
        cands.append(os.environ["VIBEWEAVER_BASH"])
    w = shutil.which("bash")
    if w:
        cands.append(w)
    if os.name == "nt":
        cands += [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
    for c in cands:
        if not c or not os.path.isfile(c):
            continue
        try:
            if subprocess.run([c, "-c", "exit 0"], capture_output=True, timeout=10).returncode == 0:
                _BASH_EXE = c
                return c
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def script_syntax_check(path: pathlib.Path):
    """C2: a delivered script must be runnable syntax — non-empty, shebang for
    shell, then the parser: `bash -n` (.sh), `node --check` (.js/.mjs),
    py_compile (.py). Returns (ok, detail).
    Portability (2026-10-17): the shell parser reads the content from STDIN
    with BOM/CRLF normalized — the verdict is about the script's SYNTAX, not
    git's checkout line-ending policy, and a Windows `bash` opening a
    backslash path is not portable across runners (windows-latest failed
    every .sh with an empty-stderr `bash -n` while the same bytes parsed
    clean elsewhere)."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return False, f"unreadable ({exc})"
    if not raw:
        return False, "empty script (0 bytes)"
    text = raw.decode("utf-8", errors="replace").lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    first = text.splitlines()[0] if text else ""
    ext = path.suffix.lower()
    if ext in (".sh", ".bash") and not first.startswith("#!"):
        return False, "missing shebang"
    try:
        if ext in (".sh", ".bash"):
            # CRLF is its own verdict (ShellCheck SC1017 = error): a CRLF
            # script is not runnable at the execution host — the parser below
            # sees normalized text so "syntax" and "line endings" stay
            # independent judgments. Raw bytes carry the truth (text is
            # normalized below's parser input).
            if b"\r" in raw:
                return False, ("CRLF/CR line endings (SC1017) — run `tr -d '\\r' <in >out` or dos2unix; "
                               "prevent with .gitattributes `*.sh text eol=lf`")
            exe = _bash_exe()
            if not exe:
                return False, "checker unavailable (no working bash on PATH)"
            r = subprocess.run([exe, "-n"], input=text, capture_output=True, encoding="utf-8", errors="replace", timeout=10)
            detail = r.stderr.strip() or f"bash -n failed (rc={r.returncode} via {os.path.basename(str(exe))})"
            return r.returncode == 0, ("syntax ok" if r.returncode == 0 else detail[:120])
        if ext in (".js", ".mjs"):
            r = subprocess.run(["node", "--check", str(path)], capture_output=True, encoding="utf-8", errors="replace", timeout=10)
            return r.returncode == 0, ("syntax ok" if r.returncode == 0 else (r.stderr.strip() or "node --check failed")[:120])
        if ext == ".py":
            r = subprocess.run([sys.executable, "-m", "py_compile", str(path)], capture_output=True, encoding="utf-8", errors="replace", timeout=10)
            return r.returncode == 0, ("syntax ok" if r.returncode == 0 else (r.stderr.strip() or "py_compile failed")[:120])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"checker unavailable ({exc})"
    return True, "no parser for ext (existence only)"

def check(ok: bool, msg: str, code: str = "", severity: str = "block"):
    """D4 structured result: every failure carries code/severity/detail so the
    gate keys on exit code + severity (never prose keywords)."""
    global PASSES
    PASSES += 1
    if not ok:
        FAILS.append({"code": code or CUR_GROUP, "severity": severity, "detail": msg})


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


def _manifest_dirs(root: pathlib.Path, names):
    """Manifest directories up to depth 3 — monorepo `services/api/` too."""
    dirs = []
    skip = {".git", ".venv", "venv", "node_modules", ".pnpm-store", "dist",
            "build", "target", "coverage", ".next", ".nuxt", "site-packages",
            "__pycache__", "ms-playwright", "playwright-report", "test-results",
            "tests", "fixtures", "examples", "vendor"}
    try:
        for dirpath, dirnames, _filenames in os.walk(root):
            rel = pathlib.Path(dirpath).relative_to(root)
            if len(rel.parts) > 3:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if d not in skip and not d.startswith(".")]
            if any((pathlib.Path(dirpath) / n).exists() for n in names):
                dirs.append(pathlib.Path(dirpath))
    except OSError:
        pass
    return dirs


def _ignored(root: pathlib.Path, rel: str) -> bool:
    """True only when a COMMITTED .gitignore supplies the match.

    `check-ignore -q` alone would accept a global excludes file or
    `.git/info/exclude`, leaving collaborators/CI unprotected."""
    rc, out = _git(root, "check-ignore", "-v", "--no-index", rel)
    if rc != 0:
        return False
    src = out.split(":", 1)[0].strip()
    if not src.endswith(".gitignore") or src.startswith("/") or "/.git/" in src:
        return False
    # The matching .gitignore must be COMMITTED (HEAD), so the protection
    # travels with the repo; a staged-only, nested-untracked, or global
    # excludes file named `.gitignore` does not count.
    rc2, _ = _git(root, "cat-file", "-e", f"HEAD:{src}")
    if rc2 != 0:
        return False
    # The matching PATTERN must be committed too: an uncommitted `.gitignore`
    # edit is local-only protection (the incident can recur on a fresh clone).
    rc3, _ = _git(root, "diff", "--quiet", "HEAD", "--", src)
    return rc3 == 0


def repo_hygiene_check(root: pathlib.Path, existing: bool, final: bool):
    """Group 21 — repository hygiene / VCS budget (COV-9 preflight, A10.1).

    The incident class: one `git add -A` committed a pnpm store + browser
    cache + SQL dumps (~1.3GB); a later `git rm --cached` did not shrink the
    history. This gate fails BEFORE that state becomes the baseline."""
    rc, _ = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        if rc in (-2, -3):
            check(False, "repo-hygiene: git call timed out/overflowed — cannot verify the repository (fail-closed; re-run)")
        elif (root / ".git").exists():
            check(False, "repo-hygiene: git command failed inside an existing .git — cannot verify (fail-closed)")
        elif existing:
            check(True, "repo-hygiene: na (no git repo)")
        else:
            check(False, "new-project git repo missing — run `git init` first (C1 step 1)")
        return

    check((root / ".gitignore").is_file(),
          "repo-hygiene: .gitignore missing — write it BEFORE installing dependencies (A10.1/APPENDIX §A12)")
    rc, _ = _git(root, "cat-file", "-e", "HEAD:.gitignore")
    check(rc == 0,
          "repo-hygiene: .gitignore is not committed in HEAD — commit it so collaborators/CI get the protection")

    node_dirs = _manifest_dirs(root, NODE_MANIFESTS)
    pnpm_dirs = _manifest_dirs(root, ("pnpm-lock.yaml", "pnpm-workspace.yaml"))
    py_dirs = _manifest_dirs(root, PY_MANIFESTS)
    if node_dirs:
        missing = []
        for d in node_dirs:
            rel = (d / "node_modules/probe").relative_to(root).as_posix()
            if not _ignored(root, rel):
                missing.append(rel)
        check(not missing,
              "repo-hygiene: .gitignore does not cover node_modules/ at: "
              + ", ".join(missing[:3]) + (" …" if len(missing) > 3 else "")
              + " — `git add -A` would sweep dependencies into history")
    if pnpm_dirs:
        missing = []
        for d in pnpm_dirs:
            rel = (d / ".pnpm-store/probe").relative_to(root).as_posix()
            if not _ignored(root, rel) and not _ignored(root, ".pnpm-store/probe"):
                missing.append(rel)
        check(not missing,
              "repo-hygiene: .gitignore does not cover .pnpm-store/ at: "
              + ", ".join(missing[:3]) + (" …" if len(missing) > 3 else "")
              + " — the 886MB incident path")
    if py_dirs:
        missing = []
        for d in py_dirs:
            rel_venv = (d / ".venv/probe").relative_to(root).as_posix()
            rel_venv2 = (d / "venv/probe").relative_to(root).as_posix()
            if not (_ignored(root, rel_venv) or _ignored(root, rel_venv2)):
                missing.append(rel_venv)
        check(not missing,
              "repo-hygiene: .gitignore does not cover .venv/ or venv/ at: "
              + ", ".join(missing[:3]) + (" …" if len(missing) > 3 else "")
              + " — Python deps are not source")

    rc, out = _git(root, "ls-files")
    if rc != 0:
        check(False, "repo-hygiene: git ls-files failed — cannot verify tracked paths (fail-closed)")
        tracked = []
    else:
        tracked = [l for l in out.splitlines() if l.strip()]
    bad = [p for p in tracked if VENDOR_RE.search(p)]
    check(not bad,
          "repo-hygiene: tracked vendor/cache path(s): " + ", ".join(bad[:3])
          + (" …" if len(bad) > 3 else "")
          + " — `git rm -r --cached` them, then commit .gitignore (index-only cleanup does NOT shrink .git)")
    built = [p for p in tracked if BUILD_RE.search(p)]
    if built:
        warn("repo-hygiene: tracked build output(s): " + ", ".join(built[:3])
             + (" …" if len(built) > 3 else "") + " — verify these are not generated (A10.1)", "21")

    check(UNTRACKED_ERROR == 0,
          "repo-hygiene: git ls-files --others failed — cannot verify the untracked count (fail-closed)")
    if UNTRACKED_TOTAL > 500:
        warn(f"repo-hygiene: {UNTRACKED_TOTAL} untracked non-ignored files (> 500) — likely a missing ignore rule", "21")
    check(UNTRACKED_TOTAL <= UNTRACKED_LIMIT,
          f"repo-hygiene: {UNTRACKED_TOTAL} untracked non-ignored files > {UNTRACKED_LIMIT} — fix .gitignore or split the wave; refusing to scan the tree")

    rc, out = _git(root, "count-objects", "-v")
    size_kib = 0
    if rc != 0:
        check(False, "repo-hygiene: git count-objects failed — cannot verify .git size (fail-closed)")
    else:
        for line in out.splitlines():
            m = re.match(r"^(?:size|size-pack):\s*(\d+)", line)
            if m:
                size_kib += int(m.group(1))
    check(size_kib <= GIT_SIZE_FAIL_KIB,
          f"repo-hygiene: .git is {size_kib / 1024:.0f} MiB > 1 GiB — history is contaminated; run the A10.1 filter-repo runbook (Class-E, backup first)")
    if size_kib > GIT_SIZE_WARN_KIB:
        warn(f"repo-hygiene: .git is {size_kib / 1024:.0f} MiB (> 200 MiB) — schedule the A10.1 history audit", "21")

    if final:
        rc, out = _git(root, "rev-list", "--objects", "--all")
        reachable = set()
        if rc == 0:
            reachable = {line.split(" ", 1)[0] for line in out.splitlines() if line.strip()}
        rc2, out2 = _git(root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                         "--batch-all-objects")
        max_blob = 0
        if rc != 0 or rc2 != 0:
            check(False, "repo-hygiene: git rev-list/cat-file failed — cannot verify the largest reachable blob (fail-closed)")
        else:
            for line in out2.splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[1] == "blob" and parts[0] in reachable:
                    try:
                        max_blob = max(max_blob, int(parts[2]))
                    except ValueError:
                        pass
        check(max_blob <= BLOB_FAIL,
              f"repo-hygiene: largest blob {max_blob / 1024 / 1024:.1f} MiB > 40 MiB — move it to LFS/releases and rewrite history (A10.1)")
        if max_blob > BLOB_WARN:
            warn(f"repo-hygiene: largest blob {max_blob / 1024 / 1024:.1f} MiB (> 10 MiB) — audit before the next wave", "21")

    check(not GIT_TIMEOUT,
          "repo-hygiene: a git call timed out — cannot fully verify the repository (fail-closed; re-run)")
    if WAVE_TOO_LARGE:
        check(False, f"repo-hygiene: change wave too large ({WAVE_TOO_LARGE}) — split the wave before verification")


def main():
    global PASSES
    ap = argparse.ArgumentParser()
    ap.add_argument("--existing", action="store_true", help="Modify-Existing task: skip new-project §A5 design-doc + git checks")
    ap.add_argument("--backend-only", action="store_true", help="no UI: skip PAGE_DESIGN.html and project_build.sh checks")
    ap.add_argument("--profile", default="", help="project profile: service|backend-api|web-static|cli|library — skips structurally-N/A groups (overrides tests/project_profile.json)")
    ap.add_argument("--class", dest="task_class", default="", choices=["DOC", "CONFIG", "CODE"],
                    help="COV-13 task class (§V11): DOC N/A's memory + service-lifecycle groups; CONFIG N/A's memory when the log carries `- memory: na (<why>)`. Default: auto-detect from the `- class: <X> — <basis>` first entry of the task block in tests/verification_log.md")
    ap.add_argument("--final", action="store_true",
                    help="completion-time run (A4.4.1): additionally enforces group 19 — tests/working_note.md must be distilled+deleted (§A7.15). Mid-task / physical-gate runs omit this flag.")
    ap.add_argument("--json", action="store_true",
                    help="D4 machine-readable result: print ONLY {ok, passes, fails:[{code,severity,detail}]} on stdout (diagnostics on stderr)")
    args = ap.parse_args()

    def info(msg=""):
        # --json keeps stdout PURE JSON; diagnostics move to stderr
        print(msg, file=sys.stderr if args.json else sys.stdout)

    root = pathlib.Path(__file__).resolve().parent.parent

    # --- project profile: declarative N/A for groups that are structurally
    # impossible for this project kind (a library has no service to start).
    # A profile SKIPS a group only; it never weakens an applicable group.
    # Explicit keys in tests/project_profile.json override the preset.
    prof_name = args.profile
    prof_cfg = {}
    pf = root / "tests" / "project_profile.json"
    if pf.exists():
        try:
            loaded = json.loads(pf.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prof_cfg = loaded
                if not prof_name:
                    prof_name = str(prof_cfg.get("profile", "") or "")
            else:
                check(False, "tests/project_profile.json must contain a JSON "
                             "object with a 'profile' key (A4.4.1 profile)")
        except (OSError, ValueError) as e:
            check(False, f"tests/project_profile.json unparseable ({e}) — "
                         f"profile overrides ignored (A4.4.1 profile)")
    KNOWN_PROFILES = ("service", "backend-api", "web-static", "cli", "library")
    if prof_name and prof_name not in KNOWN_PROFILES:
        info(f"profile: {prof_name} — WARN unknown profile name, preset "
              f"skips not applied; only explicit keys below take effect")
    for k in ("no_service", "no_ui", "no_new_project"):
        if k in prof_cfg and not isinstance(prof_cfg[k], bool):
            check(False, f"tests/project_profile.json: '{k}' must be boolean, "
                         f"got {type(prof_cfg[k]).__name__} — override ignored "
                         f"(A4.4.1 profile)")
            prof_cfg[k] = None
    no_service = prof_cfg.get("no_service")
    no_ui = prof_cfg.get("no_ui")
    no_new_project = prof_cfg.get("no_new_project")
    if prof_name == "cli" or prof_name == "library" or prof_name == "web-static":
        no_service = True if no_service is None else no_service
    if prof_name in ("backend-api", "cli", "library"):
        no_ui = True if no_ui is None else no_ui
    if prof_name == "backend-api":
        no_service = False if no_service is None else no_service
    backend_only = args.backend_only or bool(no_ui)
    existing = args.existing or bool(no_new_project)
    skips = []
    if no_service:
        skips.append("service lifecycle N/A (group 5 skipped)")
    if backend_only and not args.backend_only:
        skips.append("UI N/A")
    if existing and not args.existing:
        skips.append("new-project gates N/A")
    if prof_name or skips or any(prof_cfg.get(k) is not None
                                 for k in ("no_service", "no_ui", "no_new_project")):
        info("profile: " + (prof_name or "custom")
              + (" — " + "; ".join(skips) if skips else " — full gates"))

    tests = root / "tests"
    vl = read(tests / "verification_log.md")
    acc = read(tests / "acceptance.md")

    # --- COV-13 task class (VERIFICATION_UPGRADES §V11): which groups are
    # structurally N/A for this change wave. --class wins; otherwise the
    # `- class: <X> — <basis>` first entry of the CURRENT task block in the log.
    # A class never weakens an applicable group — it only N/A's groups whose
    # risk is not in the class's path card.
    cls = (args.task_class or "").upper()
    cls_basis = "--class flag"
    # Multi-block logs: the CURRENT task is the LAST `## ` block — an older
    # block's `- class:` / `- memory: na` is history and licenses nothing here.
    # A trailing non-task `## ` heading must not truncate the current task
    # (review R-I4) — the task block is the last ITER-BEARING block, same
    # selection group 20 uses.
    def _last_iter_block(block_text: str) -> str:
        _live = []
        _fence = False
        for _l in block_text.splitlines():
            if FENCE.match(_l):
                _fence = not _fence
                continue
            if not _fence:
                _live.append(_l)
        _cur = ""
        for _b in re.split(r"(?m)^(?=## )", "\n".join(_live)):
            if (re.search(r"(?m)^## Task\b", _b)
                    or re.search(r"(?m)^- iter \d+ (?:PASS|FAIL)\b", _b)):
                _cur = _b
        return _cur or re.split(r"(?m)^(?=## )", block_text)[-1]

    cur_block = _last_iter_block(vl) if vl else ""

    # Fence/quote-aware line filter (dsh 2026-09-30): fenced examples and
    # blockquoted echoes never license anything (class · render · exec rows).
    def _live_lines(block: str):
        in_fence = False
        out = []
        for _l in block.splitlines():
            if FENCE.match(_l):
                in_fence = not in_fence
                continue
            if in_fence or _l.lstrip().startswith(">"):
                continue
            out.append(_l)
        return out

    # Widened class-line grammar (dsh 2026-09-30): indent · list bullets ·
    # spaced colon · all three dash variants · optional basis — an author must
    # not hide the FIRST declaration behind a later flush-left line.
    _class_re = re.compile(
        r"^\s*(?:[-*]|\d+[.)])?\s*class\s*:\s*(DOC|CONFIG|CODE)\b\s*(?:[—–-]\s*(.+))?$", re.I)
    m_all = []
    for _l in _live_lines(cur_block):
        _m = _class_re.match(_l)
        if _m:
            m_all.append((_m.group(1).upper(), (_m.group(2) or "").strip()))
    _classes = [m[0] for m in m_all]
    if m_all:
        # One class per task (§V11.7): FIRST entry is the basis line; a later
        # DIFFERENT `- class:` is a contradiction/append attempt — escalate by
        # EDITING the line, never appending (§V11.4#3 只升不降).
        _dups = [c for c in _classes[1:] if c != _classes[0]]
        if _dups:
            group("18")
            check(False, f"tests/verification_log.md: class contradiction/append — "
                         f"`- class: {_classes[0]}` then `- class: {_dups[-1]}` in one task block "
                         f"(one class per task §V11.7; 升类=改写该行非追加，只升不降 §V11.4#3)")
    if not cls and m_all:
        cls = _classes[0]
        cls_basis = "log: - class: " + m_all[0][0] + (" — " + m_all[0][1][:60] if m_all[0][1] else "")
    if cls and m_all and args.task_class:
        # flag-vs-log cross-check: a contradicting --class must not silently
        # disable the class's own gates (§V11.7 one class per task).
        group("18")
        if m_all[0][0] != cls:
            check(False, f"--class {cls} contradicts the log's `- class: {m_all[0][0]}` "
                         f"in the current task block — one class per task (§V11.7)")
    # 18b) C1 (P1, BL-15): class DERIVES from the wave diff's file kinds
    # (§V11.2 ladder). The log/flag class is a CLAIM cross-checked against the
    # derivation — SWE-bench-Pro-style: never trust the agent's self-report.
    # Hard whenever the wave names classifiable files (a silent misreport must
    # not dodge the class's own gates). Zero-declared: derivation fills in.
    _c1_paths = sorted(set(parse_diff(wave_diff_text(root)).keys()) | set(untracked_files(root)))
    _derived, _dsum = derive_class(_c1_paths)
    _rank = {"DOC": 1, "CONFIG": 2, "CODE": 3}
    if _derived:
        if not cls:
            cls = _derived
            cls_basis = "derived from wave diff: " + _dsum
        elif _rank.get(cls, 0) < _rank.get(_derived, 0):
            # FAIL only the LENIENT direction (a code wave claiming DOC dodges
            # the class's gates); an over-strict declaration merely runs more
            # gates and is never a misreport in the harmful direction.
            group("18")
            check(False, f"task class mismatch (C1): the wave diff's file kinds derive {_derived} "
                         f"({_dsum}) but this task claims the MORE LENIENT `class: {cls}` "
                         f"({cls_basis}) — restate `- class:` honestly or move the offending "
                         f"files out of the wave")
    class_skip_memory = (cls == "DOC" and not re.search(
        r"^- iter \d+ FAIL|^- stall:|cap-hit", cur_block, re.M)) or (
        cls == "CONFIG" and bool(re.search(r"^-[ \t]*memory:[ \t]*na[ \t]*\(", cur_block, re.M | re.I)))
    class_skip_service = cls == "DOC"
    # §V11.9 DOC-asset render + exec gates — FILE-KIND triggered (every class:
    # a mixed CODE wave shipping a docx owes the same render). Assets come from
    # git --name-status + untracked (binary-safe; deletions are not deliveries).
    _asset_re = re.compile(r"\.(docx|doc|xlsx|xls|pptx|ppt|pdf|odt|ods|odp|rtf|odg|epub|mht|docm|xlsm|pptm)$", re.I)
    # Whole change wave, not just the working tree: assets COMMITTED mid-wave are
    # still deliveries (newest `backup: before changes`..HEAD + uncommitted +
    # untracked). --name-status is binary-safe; D = not a delivery.
    _paths = set()
    _rcb, _base = _git(root, "log", "--format=%H", "-1", "--fixed-strings", "--grep=backup: before changes")
    # No `backup:` marker → the wave is the working tree only (pre-wave history
    # must never count as deliveries).
    _ranges = (["log", "--name-status", "--format=", f"{_base.strip()}..HEAD"] if _rcb == 0 and _base.strip()
               else ["diff", "--name-status", "HEAD"])
    for _args in (_ranges, ["diff", "--name-status", "HEAD"], ["diff", "--cached", "--name-status"],
                  ["ls-files", "--others", "--exclude-standard"]):
        _rc, _out = _git(root, *_args)
        for _line in _out.splitlines():
            if not _line.strip():
                continue
            if "\t" in _line:
                # name-status row: the STATUS column carries deletions — only
                # THERE does `D` mean "not a delivery" (dsh 2026-09-30 C-fix:
                # a bare path starting with `D` is a delivery). Rename/copy
                # rows (`R100\told\tnew`) deliver the LAST field.
                _status, _, _rest = _line.partition("\t")
                if _status.strip().startswith("D"):
                    continue
                if _rest:
                    _paths.add(_unquote_git(_rest.split("\t")[-1]))
            else:
                # `git ls-files --others` prints bare single-column paths — a
                # tab-less line IS the path, not a malformed name-status row.
                _paths.add(_unquote_git(_line))
    _wave_assets = sorted(p for p in _paths if _asset_re.search(p))
    _render_lines = [l for l in _live_lines(cur_block) if re.match(r"^\s*(?:[-*]\s+)?render\s*:", l, re.I)]
    _toolchain_re = re.compile(r"soffice|libreoffice|pymupdf|pdftoppm|poppler|imagemagick", re.I)

    def _line_ok(_l):
        # dsh §V11.9 binding: EVERY cited image must exist non-empty under
        # tests/ (no path escapes — one real png cannot launder a fabricated
        # co-citation); N/A only for rows citing NO images. Mainline C2/BL-14
        # on top: real media magic + IHDR >= 320x200 for render PNGs.
        _pngs = []
        for f in re.findall(r"tests/([\w./-]*[\w-]+\.(?:png|webm))", _l, re.I):
            if os.path.basename(f).lower().startswith("probe_vision."):
                continue
            _norm = os.path.normpath(f)
            if _norm.startswith("..") or os.path.isabs(_norm):
                return False
            _pngs.append(_norm)
        if not _pngs:
            return bool(re.search(r"N/A", _l, re.I)) and bool(_toolchain_re.search(_l)) and "<" not in _l
        for _f in _pngs:
            _p = tests / _f
            if not (_p.exists() and _p.stat().st_size > 0):
                return False
            _ok_m, _det = media_probe(_p)
            if not _ok_m:
                return False
            if _p.suffix.lower() == ".png":
                _d = png_dims(_p)
                if not _d or _d[0] < 320 or _d[1] < 200:
                    return False
        return True

    _split_re = re.compile(r"\s+[—–-]\s+")

    def _declared_of(_l):
        _m = re.match(r"^\s*(?:[-*]\s+)?(?:render|exec-check)\s*:\s*", _l, re.I)
        if not _m:
            return None
        _rest = _l[_m.end():]
        return _split_re.split(_rest, maxsplit=1)[0].strip().strip('`"\'') or None

    def _named(_p, _l):
        # dsh §V11.9 per-asset binding: the row must DECLARE this asset — the
        # token before the first spaced dash separator, normpath-compared.
        _d = _declared_of(_l)
        if not _d:
            return False
        _p_norm = os.path.normpath(_p.replace("\\", "/")).replace("\\", "/")
        _d_norm = os.path.normpath(_d.replace("\\", "/")).replace("\\", "/")
        if _p_norm == _d_norm:
            return True
        if "/" in _d_norm:
            return False
        if os.path.basename(_p_norm).lower() != _d_norm.lower():
            return False
        _same = [a for a in _wave_assets
                 if os.path.basename(a.replace("\\", "/")).lower() == _d_norm.lower()]
        return len(_same) <= 1

    _uncovered = [p for p in _wave_assets
                  if not any(_named(p, l) and _line_ok(l) for l in _render_lines)]
    # 17a) §V11.9 DOC-asset render gate (NO RENDER, NO DONE)
    group("17a")
    if _uncovered:
        check(False, f"§V11.9 DOC-asset render gate: {_uncovered[0]} delivered without bound render "
                     "evidence — add `render: <asset> — <existing page images>` or "
                     "`render: <asset> — N/A (soffice missing)` (name the CONCRETE missing tool — "
                     "soffice|libreoffice|pymupdf|pdftoppm|poppler|imagemagick — never a placeholder) "
                     "to the log (NO RENDER, NO DONE)")
    # 17b) §V11.9 exec-check: delivered office assets need the named
    group("17b")
    # executable-behavior check recorded (vbaProject/PDF JS/macro sheet).
    _exec_lines = [l for l in _live_lines(cur_block) if re.match(r"^\s*(?:[-*]\s+)?exec-check\s*:", l, re.I)]

    def _exec_ok(_l):
        # verdict is the token AFTER the separator — "unclean"/"not clean"
        # never certifies (substring 'clean' launders it otherwise).
        _parts = _split_re.split(_l, maxsplit=1)
        if len(_parts) < 2:
            return False
        _verdict = _parts[1].strip().lower()
        return bool(re.match(r"clean\b", _verdict) or re.match(r"escalat", _verdict))

    _exec_uncovered = [p for p in _wave_assets
                       if not any(_named(p, l) and _exec_ok(l) for l in _exec_lines)]
    if _exec_uncovered:
        check(False, f"§V11.9 exec-check: {_exec_uncovered[0]} delivered without a recorded "
                     "executable-behavior check — add `exec-check: <asset> — clean` or "
                     "`exec-check: <asset> — escalated → Class CODE` (vbaProject.bin / PDF JS / macro sheet)")
    if cls:
        info(f"class: {cls} — {cls_basis}"
              + ("; group 4 N/A (no lesson / docs-only wave)" if class_skip_memory else "")
              + ("; group 5 N/A (no service lifecycle in a DOC wave)" if class_skip_service else ""))

    # 1) verification_log — exists, has >=1 standard iteration entry (COV-1)
    group("1")
    check(vl and len(vl.strip()) > 0, "tests/verification_log.md missing or empty (COV-1)")
    check(bool(re.search(r"^- iter \d+ (PASS|FAIL)\b", vl, re.M)),
          "verification_log.md has no `- iter N PASS/FAIL:` entries (A4.1 Step 4)")

    # 2) acceptance.md — exists, first line cap/stall stop-condition (COV-7)
    group("2")
    check(bool(re.search(r"^>\s*cap=5\s+stall=3", acc, re.M)),
          "tests/acceptance.md missing first line `> cap=5  stall=3×` (COV-7)")

    # 3) screenshots cited in the log files must exist >0 bytes (A4.4)
    #    C2 (P1): + magic bytes — a 1-byte file named *.png is not evidence
    group("3")
    for png in re.findall(r"tests/(\S+\.png)", vl + "\n" + acc, re.I):
        p = tests / png
        if not (p.exists() and p.stat().st_size > 0):
            check(False, f"screenshot claimed but missing/empty: tests/{png} (A4.4)")
            continue
        ok_media, detail = media_probe(p)
        check(ok_media, f"screenshot tests/{png} is not a real PNG: {detail} (C2 media magic)")

    # 4) memory — MEMORY.md + >=1 topic file + index pointers (A7.9/A7.10)
    group("4")
    #    Class DOC / lesson-less CONFIG: N/A (§V11.3 lesson-triggered) —
    #    printed above as `class: … group 4 N/A` gate evidence.
    if not class_skip_memory:
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

    # 4b) trigger literal-prefix lint (§A7.16) — a trigger glob whose literal
    group("4b")
    #     leading path no longer exists in the repo is a SILENT non-delivery
    #     (same failure class as a stale reference, A7.6 rule 8). Globs
    #     starting with `**` carry no literal prefix and are exempt. Runs
    #     independent of group 4's class skip: a stale trigger is dishonest
    #     evidence in every class.
    def _triggers_of(fm):
        out = []
        lines = fm.split("\n")
        for i, ln in enumerate(lines):
            m = re.match(r"^triggers:\s*(.*)$", ln)
            if not m:
                continue
            rest = m.group(1).strip()
            if rest.startswith("["):
                inner = re.sub(r"^\[|\]\s*$", "", rest)
                out.extend(v.strip().strip("'\"") for v in inner.split(",") if v.strip())
            elif not rest:
                for ln2 in lines[i + 1:]:
                    li = re.match(r"^\s*-\s+[\"']?([^\"']+?)[\"']?\s*(?:#.*)?$", ln2)
                    if not li:
                        break
                    out.append(li.group(1))
            else:
                out.append(re.sub(r"[\"']", "", re.sub(r"\s+#.*$", "", rest)).strip())
            break
        return out

    mem_dir = root / "memory"
    if mem_dir.is_dir():
        for topic in sorted(mem_dir.glob("*.md")):
            if topic.name == "MEMORY.md":
                continue
            text = read(topic).replace("\r\n", "\n").lstrip("﻿")
            fm = re.match(r"^---\n([\s\S]*?)\n---", text)
            if not fm:
                continue
            for glob_pat in _triggers_of(fm.group(1)):
                if glob_pat.startswith("**"):
                    continue
                prefix = re.split(r"[*?]", glob_pat, 1)[0].rstrip("/")
                if prefix and not (root / prefix).exists():
                    check(False,
                          f"memory/{topic.name}: trigger {glob_pat!r} — literal prefix {prefix!r} no longer exists in the repo (stale trigger = silent non-delivery, §A7.16)")

    # 5) scripts — start/stop/restart (+ project_build unless no-UI) (A2/COV-2)
    group("5")
    #    exec-bit is only meaningful on POSIX; on Windows .sh files ride along
    #    and only their existence is enforceable.
    #    Profiles (cli/library/web-static) skip this group — structurally N/A
    #    (a library has no service lifecycle; skipping is declarative, and the
    #    skip line above names it in the output for the completion gate).
    #    Class DOC: N/A — a prose change wave carries no service lifecycle.
    if not no_service and not class_skip_service:
        posix = os.name != "nt"
        for s in ["start.sh", "stop.sh", "restart.sh"]:
            sp = root / "script" / "linux" / s
            if not sp.exists():
                check(False, f"script/linux/{s} missing or not executable (A2/COV-2)")
                continue
            is_exec = bool(sp.stat().st_mode & 0o111) if posix else True
            check(is_exec,
                  f"script/linux/{s} missing or not executable (A2/COV-2)")
        if not backend_only:
            bp = root / "script" / "linux" / "project_build.sh"
            check(bp.exists(), "script/linux/project_build.sh missing (A2; use --backend-only if no UI)")
    # 5b) C2 (P1): delivered scripts must be runnable syntax — non-empty,
    #     shebang on shell, parser-clean (bash -n / node --check / py_compile).
    group("5b")
    if not no_service and not class_skip_service:
        seen_scripts = set()
        for sdir in (root / "script",):
            if not sdir.exists():
                continue
            for sp in sorted(sdir.rglob("*"))[:80]:
                if not sp.is_file() or sp.suffix.lower() not in (".sh", ".bash", ".bat", ".js", ".mjs", ".py"):
                    continue
                if "assert_artifacts.py" in sp.name:
                    continue
                seen_scripts.add(sp)
        for sp in sorted(seen_scripts):
            ok_syn, syn_detail = script_syntax_check(sp)
            check(ok_syn, f"{sp.relative_to(root)} fails script syntax check: {syn_detail} (C2)")

    # 6) git — new projects: repo exists with >=2 commits (C1 step 1/15, A9)
    group("6")
    if not existing:
        try:
            r = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=20)
            rc, out = r.returncode, r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            rc, out = -1, ""
        n_commits = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
        check(rc == 0 and n_commits >= 2,
              f"new-project git repo needs >=2 commits (init + final); found {n_commits} (C1 step 1/15)")

    # 7) §A5 design docs — new projects (skipped with --existing) (A5 / C1 step 2)
    group("7")
    if not existing:
        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html"]:
            check((root / doc).exists(), f"new-project design doc missing: {doc} (A5 / C1 step 2)")
        if not backend_only:
            check((root / "PAGE_DESIGN.html").exists(),
                  "new-project design doc missing: PAGE_DESIGN.html (A5; use --backend-only if no UI)")

    # 8) README + requirements — new projects (skipped with --existing) (C1 step 15)
    group("8")
    if not existing:
        check(any((root / n).exists() for n in ["README.md", "README.html"]),
              "new-project README.md/README.html missing (C1 step 15)")
        check(any((root / n).exists() for n in ["requirements.txt", "package.json"]),
              "new-project requirements.txt/package.json missing (C1 step 15)")

    # 9) COV-9 — Modify-Existing tasks: baseline verdict recorded on disk (COV-9)
    group("9")
    #    State-skip is a Class DOC license; CONFIG/CODE run the baseline (§V11.3) —
    #    their skip must name a mid-task escalation, never "documentation-only".
    if existing:
        # Review B5: scoped to the CURRENT task block — one historical green
        # baseline must never license every later change-wave ("EVERY
        # change-wave gets its own three lines", COV-9).
        baseline_line = bool(re.search(r"Baseline verified GREEN", cur_block, re.M))
        # Review B6: the THIRD COV-9 literal (pre-existing failures) now has a
        # machine-recognized form — "Baseline has N pre-existing failures" plus
        # a named disposition (awaiting decision / quarantined / escalation / ADR).
        red_baseline = bool(re.search(r"Baseline has \d+ pre-existing failures", cur_block, re.M)) and bool(
            re.search(r"awaiting decision|quarantin|escalat|ADR", cur_block, re.I))
        escalation_skip = bool(re.search(r"COV-9 skipped[^\n]*escalat", cur_block, re.M | re.I))
        # Review B5: the DOC state-skip is licensed only by an EXPLICIT
        # `- class: DOC` — an unlabeled task block is not a DOC task.
        doc_skip = bool(re.search(r"COV-9 skipped", cur_block, re.M)) and cls == "DOC"
        check(baseline_line or red_baseline or escalation_skip or doc_skip,
              "current task block missing the COV-9 baseline verdict (per change-wave): "
              "`- Baseline verified GREEN`, or `- Baseline has N pre-existing failures` with a "
              "named disposition, or `- COV-9 skipped —` (Class DOC only) / an escalation (§V11.3)")

    # 10) A4.7b — workflow traces cited in the log must exist >0 bytes (A4.7b)
    group("10")
    for wf in re.findall(r"tests/workflows/(\S+?\.trace\.log)", vl):
        p = tests / "workflows" / wf
        check(p.exists() and p.stat().st_size > 0,
              f"workflow trace claimed but missing/empty: tests/workflows/{wf} (A4.7b)")

    # 11) A4.1 — video/audio evidence cited in the log must exist >0 bytes (A4.1 Step 2/3)
    #     C2 (P1): + magic bytes per kind (webm/wav/mp4/mp3)
    group("11")
    for m in re.findall(r"tests/(\S+\.(?:webm|wav|mp4|mp3))", vl, re.I):
        p = tests / m
        if not (p.exists() and p.stat().st_size > 0):
            check(False, f"media evidence claimed but missing/empty: tests/{m} (A4.1)")
            continue
        ok_media, detail = media_probe(p)
        check(ok_media, f"media evidence tests/{m} has wrong format: {detail} (C2 media magic)")

    # 12) FAIL diagnosis clause — every failed iteration must carry its diagnosis
    group("12")
    #     (A4.1 Step 4 — a retry without its diagnosis is the same attempt again)
    for i, line in enumerate(vl.splitlines(), 1):
        if re.match(r"^- iter \d+ FAIL:", line.strip()):
            check("diagnosis:" in line,
                  f"verification_log.md line {i}: FAIL entry lacks `diagnosis:` clause (A4.1 Step 4)")

    # 12b) diagnosis substance (log-format lint) — the diagnosis must be one
    group("12b")
    #      falsifiable clause, not a placeholder token (§A4.1 Step 4). The
    #      capture runs to the `| changed:` field (not the first `|`) so a
    #      diagnosis mentioning alternation is not truncated into a false
    #      placeholder verdict.
    for i, line in enumerate(vl.splitlines(), 1):
        m = re.match(r"^- iter \d+ FAIL:.*?\bdiagnosis:\s*(.*?)\s*(?:\|\s*changed:|$)", line.strip())
        if m is not None:
            d = m.group(1).strip()
            if len(d) < 10 or re.fullmatch(r"(?i)[-?]*|none|n/?a|idk|unknown|tbd", d):
                check(False,
                      f"verification_log.md line {i}: FAIL diagnosis is a placeholder — one falsifiable clause required (A4.1 Step 4 log lint)")

    # 13) claim-without-coverage — a verification claim must state what it covered
    group("13")
    #     (A4.4 Gate Function — "verified" without a stated scope is not a result)
    for i, snippet in claim_without_coverage(vl):
        check(False,
              f"verification_log.md line {i}: claim without stated coverage — {snippet!r} (A4.4 claim rule)")

    # 14) secret scan — the change-wave diff / untracked files must not ADD
    group("14")
    #     credential-looking lines (.md warn-only; placeholder-marked exempt)
    s14_fails, s14_warns = secret_scan(root, cur_block)
    for w in s14_warns:
        warn(w, "14")
    for f in s14_fails:
        check(False, f)

    # 15) test-change guard — removed test assertions need a logged reason
    group("15")
    for f in test_change_guard(root, cur_block):
        check(False, f)

    # 15b) C3 (P1, BL-11/12): evidence manifest — tamper + freshness.
    #     The manifest is written ONLY by scripts/evidence_seal.py; a hash
    #     mismatch means the evidence changed after sealing, and a stale
    #     code_fingerprint means the evidence predates later code changes
    #     ("先造证据后改代码"). At completion (--final) cited media must be
    #     sealed at all (missing != success - Agent Evidence spec).
    group("15b")
    _man_p = tests / "evidence_manifest.json"
    if _man_p.exists():
        try:
            _man = json.loads(read(_man_p) or "{}")
        except Exception:
            _man = {}
        for _rel, _meta in sorted((_man.get("files") or {}).items()):
            _fp = root / _rel
            if not _fp.is_file():
                check(False, f"sealed evidence missing: {_rel} (evidence_manifest) - evidence deleted after seal (C3)")
                continue
            _cur = hashlib.sha256(_fp.read_bytes()).hexdigest()
            check(_cur == (_meta or {}).get("sha256"),
                  f"sealed evidence {_rel} hash mismatch (C3 tamper) - the file changed after "
                  f"scripts/evidence_seal.py sealed it; re-run the covering tests and re-seal")
        check(code_fingerprint(root) == _man.get("code_fingerprint"),
              "sealed evidence is STALE (C3 freshness) - wave code changed after evidence_seal.py "
              "ran; re-run the covering tests and re-seal (missing != success)")
    elif args.final:
        _cited_media = re.findall(r"tests/(\S+\.(?:png|webm|wav|mp4|mp3))", vl, re.I)
        if _cited_media:
            check(False, f"cited media evidence is not sealed (C3) - run `python3 scripts/evidence_seal.py` "
                         f"(writes tests/evidence_manifest.json; {len(set(_cited_media))} file(s) cited)")

    # 16) risk-tier — risk-tier code paths require the A4.9 review package
    group("16")
    for f in risk_tier(root):
        check(False, f)

    # 19) working-note lifecycle (--final only) — the task working memory is a
    group("19")
    #     scratch artifact: distilled into memory/ (A7.9) and deleted BEFORE
    #     the completion table; a leftover means an undistilled lesson or a
    #     zombie state file leaking into the next task (§A7.15)
    if args.final:
        check(not (tests / "working_note.md").exists(),
              "tests/working_note.md still present at completion — distill into memory/ (A7.9) and delete it first (§A7.15 working-note lifecycle)")

    # 20) working-note creation side (§A7.15) — group 19 checks the note is
    group("20")
    #     GONE at completion; this group checks it EXISTED during the work.
    #     Fence-aware (a quoted example launders nothing) and scoped to the
    #     LAST ITER-BEARING block — a trailing non-task `## ` heading must not
    #     truncate the current task into silence (fail-open guard).
    live = []
    in_fence = False
    for _l in vl.splitlines():
        if FENCE.match(_l):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        live.append(_l)
    blocks = re.split(r"(?m)^(?=## )", "\n".join(live))
    cur = ""
    for _b in blocks:
        if re.search(r"(?m)^- iter \d+ (?:PASS|FAIL)\b", _b):
            cur = _b
    if cur:
        iters = len(re.findall(r"(?m)^- iter \d+ (?:PASS|FAIL)\b", cur))
        has_fail = bool(re.search(r"(?m)^- iter \d+ FAIL\b", cur))
        if iters >= 2 or has_fail:
            check(bool(re.search(r"(?m)^- working-note:\s*\S", cur)),
                  "verification_log.md current task block: ≥2 iterations / a FAIL without "
                  "`- working-note:` lifecycle lines (created → updated → distilled → deleted) "
                  "or a stated `- working-note: na (<why>)` (§A7.15 creation side)")

    # 21) repository hygiene / VCS budget (COV-9 preflight, A10.1) — every
    #     class and every project kind; no profile can skip it.
    group("21")
    repo_hygiene_check(root, existing, args.final)

    if GIT_TIMEOUT:
        warn("groups 14-16/21: a git call timed out — content gates ran "
             "on partial data (fail-open); re-run to confirm", "git")

    all_fails = list(FAILS) + [{"code": w.get("code", CUR_GROUP), "severity": "warn", "detail": w.get("detail", str(w))} for w in WARN_LINES]
    if args.json:
        ok = not FAILS  # warns never flip ok (advisory by definition)
        print(json.dumps({"ok": ok, "passes": PASSES, "fails": all_fails}))
        sys.exit(0 if ok else 1)
    for w in WARN_LINES:
        print("WARN " + w.get("detail", str(w)))
    if FAILS:
        print("ASSERT FAILURES (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f["detail"])
        sys.exit(1)
    print(f"assert_artifacts.py: all {PASSES} checks pass (exit 0)")


if __name__ == "__main__":
    main()
