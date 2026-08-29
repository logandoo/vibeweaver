# A4.9 Review Package — VLQ encode/decode

## Range: a056e23^..a056e23 (feat: implement VLQ encode/decode)

## git log --oneline
c0d8505 backup: before changes
a056e23 feat: implement VLQ encode/decode (32-bit restricted)
1645302 feat: implement pig-latin translate() (vowel/xr/yt, qu, y split-point rules)

## git diff --stat
 .../memory/MEMORY.md                               |   8 +
 .../memory/fix_variable_length_quantity.md         |  32 ++
 .../tests/assert_artifacts.py                      | 479 +++++++++++++++++++++
 .../tests/canonical_suite_run.log                  |   5 +
 .../tests/differential_sweep_run.log               |   1 +
 .../tests/project_profile.json                     |   5 +
 .../tests/verification_log.md                      |  10 +
 .../variable_length_quantity.py                    |  28 +-
 8 files changed, 566 insertions(+), 2 deletions(-)

## git diff -U10
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/MEMORY.md b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/MEMORY.md
new file mode 100644
index 0000000..399064c
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/MEMORY.md
@@ -0,0 +1,8 @@
+# Project Memory Index
+
+## Fix Tracking
+- ⏳ [Fix: VLQ encode/decode implementation](fix_variable_length_quantity.md) — Implemented canonical VLQ encoding/decoding with 32-bit restriction (2026-08-29)
+
+## Key Dependencies & Conventions
+- Pure-Python standard-library module `variable_length_quantity.py` exposing `encode(numbers)` and `decode(bytes_)` (Exercism-style exercise)
+- Exercise contract: inputs restricted to 32-bit unsigned integers (encode raises ValueError for out-of-range); decode raises ValueError("incomplete sequence") when the byte stream ends on a continuation byte
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/fix_variable_length_quantity.md b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/fix_variable_length_quantity.md
new file mode 100644
index 0000000..fae65c3
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/memory/fix_variable_length_quantity.md
@@ -0,0 +1,32 @@
+---
+name: Fix: VLQ encode/decode implementation
+description: Canonical variable-length-quantity encode/decode for a 32-bit-unsigned restricted exercise
+type: fix
+date: 2026-08-29
+status: ⏳
+commit: N/A
+file_refs:
+  - path: variable_length_quantity.py
+    range: "1-32"
+    sha_at_time: N/A
+last_validated: 2026-08-29
+---
+
+# Fix: VLQ encode/decode implementation
+
+**Problem:** Starter file provided `encode(numbers)` / `decode(bytes_)` stubs returning `None`; the exercise requires canonical VLQ encoding and decoding restricted to 32-bit unsigned integers.
+
+**Root Cause:** No implementation existed.
+
+**Correct Fix:** Implemented bit-grouping encode and streaming decode in `variable_length_quantity.py`:
+- `encode`: validates each number is in `[0, 0xFFFFFFFF]` (raises `ValueError("negative integer")` / `ValueError("integer too large")`), emits 7-bit groups least-significant-first collected into a list then reversed, with `0x80` continuation bit set on every byte except the last. Zero → `[0]`.
+- `decode`: streams bytes, accumulating `(value << 7) | (byte & 0x7F)`; each byte with bit 7 clear terminates a value; if the stream ends mid-sequence raises `ValueError("incomplete sequence")`.
+
+**Failed Approaches (DO NOT retry):**
+- None (single implementation wave, all 34 canonical tests + 8019-check differential sweep passed first try).
+
+**Rejected Alternatives:**
+- String/binary-based chunking (bin(n) → 7-bit groups) — rejected for the implementation as roundabout; used ONLY as the independent reference for differential testing.
+- Unrestricted VLQ (no 32-bit cap) — rejected; prompt explicitly restricts to 32-bit unsigned.
+
+**Verification:** 34/34 canonical-suite tests pass (tests/canonical_suite_run.log); independent string-based reference sweep 8019 checks / 0 failures (tests/differential_sweep_run.log), including round-trip, multi-value, random-byte-sequence, and error-message checks. Status ⏳ (verified by tests but not user-confirmed).
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/assert_artifacts.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/assert_artifacts.py
new file mode 100644
index 0000000..5c0a36b
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/assert_artifacts.py
@@ -0,0 +1,479 @@
+"""G-DED artifact assertions — byte-level check of verification claims.
+Canonical copy: vibeweaver skill `scripts/assert_artifacts.py`.
+Mirrors COMPLETION_GATE.md §A4.4.1 minimum-check table (all 16 groups).
+Group 12 enforces the A4.1 diagnosis clause; group 13 is a
+claim-without-scope lint (approach modeled on J-Space Cognition Suite's
+`ship` check at idea level; implementation here is original —
+see repo README → Attribution). Groups 14-16 are change-wave content
+gates: 14 secret scan (`vw-approved` marker ⇄ `- secret-approved:` log
+pairing), 15 test-change guard, 16 risk-tier review. Project profiles
+(tests/project_profile.json or --profile) declaratively skip groups that
+are structurally N/A for the project kind (service/UI/new-project) —
+a profile never weakens an applicable group."""
+import argparse, json, os, pathlib, re, subprocess, sys
+
+FAILS = []
+PASSES = 0
+GIT_TIMEOUT = False
+
+# Group 13 word sets, chosen for what vibeweaver logs actually overclaim with.
+# CLAIM  — verbs that assert a verification result happened.
+# COVER  — scope/evidence indicators: quantifiers, counts, artifact refs.
+# A bare object name is not scope: "the endpoint is verified" names WHAT,
+# not HOW MUCH was checked, so object nouns (endpoint/file/…) are excluded.
+CLAIM = re.compile(
+    r"\b(?:verified|confirmed|validated|proven|tested)\b|"
+    r"\ball\s+(?:checks?|tests?)\s+pass(?:es|ed)?\b|\bchecks?\s+pass\b|"
+    r"已验证|验证通过|已确认|确认无误|已测试|测试通过|已证明",
+    re.I,
+)
+COVER = re.compile(
+    r"\b(?:all|each|every|both)\b|"                     # quantifiers
+    r"\b\d+\s*/\s*\d+\b|"                               # 3/3 fractions
+    r"\bcriterion\s*#?\d+\b|\bcriteria\b|"              # criterion scope
+    r"\bn\s*[<≤=]\s*\d+\b|"                             # bounded sweeps
+    r"tests/[\w./-]+|\S+\.(?:png|mp4|webm|wav)\b|\S+\.trace\.log\b|"  # artifact refs
+    r"\bcoverage\b|\bcovered\b|\bsweep\b|\bswept\b|"
+    r"全部|所有|每个|每条|逐一|逐条|覆盖|边界|用例|场景|"
+    r"包括|包含|至少|至多|最多|最少|随机",
+    re.I,
+)
+STRUCT_LINE = re.compile(r"^(?:#{1,6}\s|>|\|{1,2}\s*-+|\s*$)")
+EXEMPT_LINE = re.compile(r"(?:^- iter \d+ (?:PASS|FAIL):|^- Baseline verified GREEN|^- COV-\d+ skipped)")
+FENCE = re.compile(r"^\s{0,3}(?:```|~~~)")
+
+# --- groups 14-16: change-wave content gates (canonical spec:
+# COMPLETION_GATE.md §A4.4.1 rows 14-16) -------------------------------
+CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs",
+            ".java", ".sql", ".sh"}
+SECRET_RES = [
+    re.compile(r"AKIA[0-9A-Z]{16}"),                       # AWS access key id
+    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
+    re.compile(r"ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|"
+               r"xox[baprs]-[A-Za-z0-9-]{16,}|"
+               r"sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{16,}"),  # GitHub/Slack/OpenAI/Anthropic tokens
+]
+# generic k = v: quoted literal values are candidates; UNQUOTED values
+# containing `.`/`(`/`)` are references or calls (os.environ.get(…),
+# process.env.X, config.password, self.x) — the SAFE handling pattern,
+# never flagged. Values outside the base charset (spaces, !#%…) may
+# escape — documented tradeoff, biased against false-blocking.
+GENERIC_KV = re.compile(
+    r"(?i)\b(?:api[_-]?key|apikey|secret|password|passwd|pwd|token|"
+    r"private[_-]?key|access[_-]?key)\b[\"']?\s*[:=]\s*"
+    r"(?P<q>[\"']?)(?P<v>[A-Za-z0-9_/+.\-]{12,})")
+PLACEHOLDER = re.compile(r"(?i)example|sample|dummy|placeholder|changeme|"
+                         r"redacted|fake|<[^>]+>")
+ASSERT_LINE = re.compile(r"^\s*(?:assert\b|self\.assert|expect\s*\(|"
+                         r"pytest\.raises|require\s*\(|def test_|it\s*\(|"
+                         r"test\s*\(|func Test|@Test)")
+TEST_DIR = re.compile(r"(^|/)(?:tests?|__tests__|spec)/")
+RISK_PATH = re.compile(r"(?i)(^|/)(?:auth|security|payments?|billing|crypto|"
+                       r"migrations?|permissions?|acl)(?:/|\.|_|$)")
+
+
+def _git(root, *args):
+    global GIT_TIMEOUT
+    try:
+        r = subprocess.run(["git", "-C", str(root), *args],
+                           capture_output=True, text=True, timeout=20)
+        return r.returncode, r.stdout
+    except FileNotFoundError:
+        return -1, ""
+    except subprocess.TimeoutExpired:
+        GIT_TIMEOUT = True
+        return -2, ""
+
+
+def wave_diff_text(root):
+    """Change-wave diff: PER-COMMIT patches of newest `backup: before changes`
+    commit..HEAD (a net range diff would hide intra-wave add-then-remove),
+    else `git show HEAD`; plus uncommitted `git diff HEAD`. "" = no git repo."""
+    rc, _ = _git(root, "rev-parse", "--git-dir")
+    if rc != 0:
+        return ""
+    rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
+                   "--grep=backup: before changes")
+    parts = []
+    if rc == 0 and sha.strip():
+        _, d = _git(root, "log", "-p", "--format=", f"{sha.strip()}..HEAD")
+        parts.append(d)
+    else:
+        _, d = _git(root, "show", "--format=", "HEAD")
+        parts.append(d)
+    _, d = _git(root, "diff", "HEAD")
+    parts.append(d)
+    return "\n".join(parts)
+
+
+def untracked_files(root):
+    """Untracked, non-gitignored files (never visible in git diff)."""
+    rc, out = _git(root, "ls-files", "--others", "--exclude-standard")
+    return [l for l in out.splitlines() if l.strip()] if rc == 0 else []
+
+
+HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
+
+
+def parse_diff(text):
+    """{path: [added, removed]} — added = [(new-file lineno, text)] via @@
+    hunks; removed = [text]. Deleted files keep their `--- a/` path so
+    removed lines and the path are retained (whole-file deletion must NOT
+    fail-open the guards)."""
+    files, cur, nline = {}, None, 0
+    for line in text.splitlines():
+        h = HUNK.match(line)
+        if h:
+            nline = int(h.group(1))
+        elif line.startswith("--- a/"):
+            cur = line[6:]
+            files.setdefault(cur, [[], []])
+        elif line.startswith("+++ b/"):
+            cur = line[6:]
+            files.setdefault(cur, [[], []])
+        elif line.startswith("--- /dev/null"):
+            cur = None
+        elif line.startswith("+++ /dev/null"):
+            pass                                # deleted file: keep a/ path
+        elif cur and line.startswith("+"):
+            files[cur][0].append((nline, line[1:]))
+            nline += 1
+        elif cur and line.startswith("-"):
+            files[cur][1].append(line[1:])
+        elif line.startswith(" "):
+            nline += 1
+    return files
+
+
+def _is_test_code(path):
+    p = pathlib.PurePosixPath(path)
+    if p.suffix not in CODE_EXT or "assert_artifacts.py" in path:
+        return False
+    if TEST_DIR.search(path):
+        return True
+    n = p.name
+    return (n.startswith("test_") or "_test." in n
+            or ".test." in n or ".spec." in n)
+
+
+def secret_scan(root, vl=""):
+    """Group 14 — secret scan. Returns (fails, warns). Only ADDED diff lines
+    and untracked files; placeholder-marked lines exempt; .md warn-only;
+    any assert_artifacts.py never scanned. A `vw-approved` inline marker
+    exempts a credential line ONLY when verification_log.md carries the
+    path-scoped pairing `- secret-approved: <path> — <reason>` (marker count
+    per path must be ≤ approvals for that path — same binding shape as group
+    15's `- test-change: <path>`). A bare mention of the marker on a line
+    that matches no credential pattern is a no-op (prose mentions never
+    trip the gate). Pairing failures FAIL regardless of file type (the
+    .md warn-only rule applies only to plain unmarked secrets)."""
+    fails, warns, marker_paths = [], [], {}
+
+    def hit(path, lineno, text):
+        if "assert_artifacts.py" in path or PLACEHOLDER.search(text):
+            return
+        found = any(rx.search(text) for rx in SECRET_RES)
+        if not found:
+            m = GENERIC_KV.search(text)
+            found = bool(m) and (bool(m.group("q")) or
+                                 bool(not any(c in m.group("v") for c in ".()")))
+        if not found:
+            return
+        if re.search(r"vw-approved", text, re.I):
+            marker_paths[path] = marker_paths.get(path, 0) + 1
+            return
+        (warns if path.endswith(".md") else fails).append(
+            f"secret scan: {path}:{lineno}: credential-looking string "
+            f"on an added line — {text.strip()[:50]!r} (A4.4 content gate)")
+
+    for path, (added, _r) in parse_diff(wave_diff_text(root)).items():
+        for lineno, l in added:
+            hit(path, lineno, l)
+    for rel in untracked_files(root):
+        p = root / rel
+        try:
+            if not p.is_file() or p.stat().st_size > 1_000_000:
+                continue
+            t = p.read_text(encoding="utf-8")
+        except (UnicodeDecodeError, OSError):
+            continue
+        for i, l in enumerate(t.splitlines(), 1):
+            hit(rel, i, l)
+    for mpath, cnt in sorted(marker_paths.items()):
+        approvals = len(re.findall(
+            r"^- secret-approved:\s*" + re.escape(mpath) + r"(?![\w.\-])", vl, re.M))
+        if approvals < cnt:
+            fails.append(
+                f"secret scan: {mpath}: {cnt} `vw-approved` marker line(s) but "
+                f"{approvals} matching `- secret-approved: {mpath}` line(s) in "
+                f"verification_log.md — every approved secret needs its own "
+                f"path-scoped approval (A4.4 content gate)")
+    return fails, warns
+
+
+def test_change_guard(root, vl):
+    """Group 15 — test-change guard: REMOVED assertion lines in test code
+    files require a `- test-change: <path> — <reason>` log line."""
+    fails = []
+    for path, (_a, removed) in parse_diff(wave_diff_text(root)).items():
+        if not _is_test_code(path):
+            continue
+        n = sum(1 for l in removed if ASSERT_LINE.match(l))
+        if n and not re.search(r"^- test-change:.*" + re.escape(path), vl, re.M):
+            fails.append(
+                f"test-change guard: {path}: {n} assertion line(s) removed "
+                f"without a `- test-change:` justification in "
+                f"verification_log.md (A4.8 test integrity)")
+    return fails
+
+
+def risk_tier(root):
+    """Group 16 — risk-tier: diffs/untracked files touching risk-tier code
+    paths require tests/review_package.md on disk."""
+    paths = set(parse_diff(wave_diff_text(root))) | set(untracked_files(root))
+    hits = sorted(p for p in paths
+                  if pathlib.PurePosixPath(p).suffix in CODE_EXT
+                  and RISK_PATH.search(p))
+    rp = root / "tests" / "review_package.md"
+    if hits and not (rp.exists() and rp.stat().st_size > 0):
+        return [f"risk-tier: change-wave touches risk-tier path(s) "
+                f"({', '.join(hits[:5])}) but tests/review_package.md "
+                f"missing/empty — A4.9 review non-skippable (A4.9)"]
+    return []
+
+
+def check(ok: bool, msg: str):
+    global PASSES
+    PASSES += 1
+    if not ok:
+        FAILS.append(msg)
+
+
+def read(p: pathlib.Path) -> str:
+    try:
+        return p.read_text(encoding="utf-8")
+    except (FileNotFoundError, UnicodeDecodeError):
+        return ""
+
+
+def claim_without_coverage(vl: str):
+    """Return violating (line_number, line) pairs: a claim verb on a prose line
+    whose own line states no coverage scope. Fenced blocks, headings, tables
+    and structured entries are exempt — see EXEMPT_LINE."""
+    hits = []
+    in_fence = False
+    for i, line in enumerate(vl.splitlines(), 1):
+        if FENCE.match(line):
+            in_fence = not in_fence
+            continue
+        if in_fence:
+            continue
+        stripped = line.strip()
+        if not stripped or STRUCT_LINE.match(stripped) or EXEMPT_LINE.match(stripped):
+            continue
+        if CLAIM.search(stripped) and not COVER.search(stripped):
+            hits.append((i, stripped[:80]))
+    return hits
+
+
+def main():
+    global PASSES
+    ap = argparse.ArgumentParser()
+    ap.add_argument("--existing", action="store_true", help="Modify-Existing task: skip new-project §A5 design-doc + git checks")
+    ap.add_argument("--backend-only", action="store_true", help="no UI: skip PAGE_DESIGN.html and project_build.sh checks")
+    ap.add_argument("--profile", default="", help="project profile: service|backend-api|web-static|cli|library — skips structurally-N/A groups (overrides tests/project_profile.json)")
+    args = ap.parse_args()
+
+    root = pathlib.Path(__file__).resolve().parent.parent
+
+    # --- project profile: declarative N/A for groups that are structurally
+    # impossible for this project kind (a library has no service to start).
+    # A profile SKIPS a group only; it never weakens an applicable group.
+    # Explicit keys in tests/project_profile.json override the preset.
+    prof_name = args.profile
+    prof_cfg = {}
+    pf = root / "tests" / "project_profile.json"
+    if pf.exists():
+        try:
+            loaded = json.loads(pf.read_text(encoding="utf-8"))
+            if isinstance(loaded, dict):
+                prof_cfg = loaded
+                if not prof_name:
+                    prof_name = str(prof_cfg.get("profile", "") or "")
+            else:
+                check(False, "tests/project_profile.json must contain a JSON "
+                             "object with a 'profile' key (A4.4.1 profile)")
+        except (OSError, ValueError) as e:
+            check(False, f"tests/project_profile.json unparseable ({e}) — "
+                         f"profile overrides ignored (A4.4.1 profile)")
+    KNOWN_PROFILES = ("service", "backend-api", "web-static", "cli", "library")
+    if prof_name and prof_name not in KNOWN_PROFILES:
+        print(f"profile: {prof_name} — WARN unknown profile name, preset "
+              f"skips not applied; only explicit keys below take effect")
+    for k in ("no_service", "no_ui", "no_new_project"):
+        if k in prof_cfg and not isinstance(prof_cfg[k], bool):
+            check(False, f"tests/project_profile.json: '{k}' must be boolean, "
+                         f"got {type(prof_cfg[k]).__name__} — override ignored "
+                         f"(A4.4.1 profile)")
+            prof_cfg[k] = None
+    no_service = prof_cfg.get("no_service")
+    no_ui = prof_cfg.get("no_ui")
+    no_new_project = prof_cfg.get("no_new_project")
+    if prof_name == "cli" or prof_name == "library" or prof_name == "web-static":
+        no_service = True if no_service is None else no_service
+    if prof_name in ("backend-api", "cli", "library"):
+        no_ui = True if no_ui is None else no_ui
+    if prof_name == "backend-api":
+        no_service = False if no_service is None else no_service
+    backend_only = args.backend_only or bool(no_ui)
+    existing = args.existing or bool(no_new_project)
+    skips = []
+    if no_service:
+        skips.append("service lifecycle N/A (group 5 skipped)")
+    if backend_only and not args.backend_only:
+        skips.append("UI N/A")
+    if existing and not args.existing:
+        skips.append("new-project gates N/A")
+    if prof_name or skips or any(prof_cfg.get(k) is not None
+                                 for k in ("no_service", "no_ui", "no_new_project")):
+        print("profile: " + (prof_name or "custom")
+              + (" — " + "; ".join(skips) if skips else " — full gates"))
+
+    tests = root / "tests"
+    vl = read(tests / "verification_log.md")
+    acc = read(tests / "acceptance.md")
+
+    # 1) verification_log — exists, has >=1 standard iteration entry (COV-1)
+    check(vl and len(vl.strip()) > 0, "tests/verification_log.md missing or empty (COV-1)")
+    check(bool(re.search(r"^- iter \d+ (PASS|FAIL):", vl, re.M)),
+          "verification_log.md has no `- iter N PASS/FAIL:` entries (A4.1 Step 4)")
+
+    # 2) acceptance.md — exists, first line cap/stall stop-condition (COV-7)
+    check(bool(re.search(r"^>\s*cap=5\s+stall=3", acc, re.M)),
+          "tests/acceptance.md missing first line `> cap=5  stall=3×` (COV-7)")
+
+    # 3) screenshots cited in the log files must exist >0 bytes (A4.4)
+    for png in re.findall(r"tests/(\S+\.png)", vl + "\n" + acc):
+        p = tests / png
+        check(p.exists() and p.stat().st_size > 0,
+              f"screenshot claimed but missing/empty: tests/{png} (A4.4)")
+
+    # 4) memory — MEMORY.md + >=1 topic file + index pointers (A7.9/A7.10)
+    mem = root / "memory"
+    idx_text = read(mem / "MEMORY.md")
+    check(bool(idx_text), "memory/MEMORY.md missing (A7.10)")
+    if idx_text:
+        topics = sorted(mem.glob("*.md"))
+        check(len(topics) >= 2, "memory/: MEMORY.md + >=1 topic file required (A7.9)")
+        check(bool(re.search(r"\]\([^)]+\.md\)", idx_text)),
+              "memory/MEMORY.md index has no topic-file pointers (A7.9)")
+        check(any(p.name != "MEMORY.md" for p in topics),
+              "memory/: at least one topic file besides MEMORY.md (A7.9)")
+
+    # 5) scripts — start/stop/restart (+ project_build unless no-UI) (A2/COV-2)
+    #    exec-bit is only meaningful on POSIX; on Windows .sh files ride along
+    #    and only their existence is enforceable.
+    #    Profiles (cli/library/web-static) skip this group — structurally N/A
+    #    (a library has no service lifecycle; skipping is declarative, and the
+    #    skip line above names it in the output for the completion gate).
+    if not no_service:
+        posix = os.name != "nt"
+        for s in ["start.sh", "stop.sh", "restart.sh"]:
+            sp = root / "script" / "linux" / s
+            if not sp.exists():
+                check(False, f"script/linux/{s} missing or not executable (A2/COV-2)")
+                continue
+            is_exec = bool(sp.stat().st_mode & 0o111) if posix else True
+            check(is_exec,
+                  f"script/linux/{s} missing or not executable (A2/COV-2)")
+        if not backend_only:
+            bp = root / "script" / "linux" / "project_build.sh"
+            check(bp.exists(), "script/linux/project_build.sh missing (A2; use --backend-only if no UI)")
+
+    # 6) git — new projects: repo exists with >=2 commits (C1 step 1/15, A9)
+    if not existing:
+        try:
+            r = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
+                               capture_output=True, text=True, timeout=20)
+            rc, out = r.returncode, r.stdout
+        except (FileNotFoundError, subprocess.TimeoutExpired):
+            rc, out = -1, ""
+        n_commits = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
+        check(rc == 0 and n_commits >= 2,
+              f"new-project git repo needs >=2 commits (init + final); found {n_commits} (C1 step 1/15)")
+
+    # 7) §A5 design docs — new projects (skipped with --existing) (A5 / C1 step 2)
+    if not existing:
+        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html"]:
+            check((root / doc).exists(), f"new-project design doc missing: {doc} (A5 / C1 step 2)")
+        if not backend_only:
+            check((root / "PAGE_DESIGN.html").exists(),
+                  "new-project design doc missing: PAGE_DESIGN.html (A5; use --backend-only if no UI)")
+
+    # 8) README + requirements — new projects (skipped with --existing) (C1 step 15)
+    if not existing:
+        check(any((root / n).exists() for n in ["README.md", "README.html"]),
+              "new-project README.md/README.html missing (C1 step 15)")
+        check(any((root / n).exists() for n in ["requirements.txt", "package.json"]),
+              "new-project requirements.txt/package.json missing (C1 step 15)")
+
+    # 9) COV-9 — Modify-Existing tasks: baseline verdict recorded on disk (COV-9)
+    if existing:
+        check(bool(re.search(r"Baseline verified GREEN|COV-9 skipped", vl, re.M)),
+              "tests/verification_log.md missing `- Baseline verified GREEN` or `- COV-9 skipped —` entry (COV-9)")
+
+    # 10) A4.7b — workflow traces cited in the log must exist >0 bytes (A4.7b)
+    for wf in re.findall(r"tests/workflows/(\S+?\.trace\.log)", vl):
+        p = tests / "workflows" / wf
+        check(p.exists() and p.stat().st_size > 0,
+              f"workflow trace claimed but missing/empty: tests/workflows/{wf} (A4.7b)")
+
+    # 11) A4.1 — video/audio evidence cited in the log must exist >0 bytes (A4.1 Step 2/3)
+    for m in re.findall(r"tests/(\S+\.(?:webm|wav|mp4|mp3))", vl):
+        p = tests / m
+        check(p.exists() and p.stat().st_size > 0,
+              f"media evidence claimed but missing/empty: tests/{m} (A4.1)")
+
+    # 12) FAIL diagnosis clause — every failed iteration must carry its diagnosis
+    #     (A4.1 Step 4 — a retry without its diagnosis is the same attempt again)
+    for i, line in enumerate(vl.splitlines(), 1):
+        if re.match(r"^- iter \d+ FAIL:", line.strip()):
+            check("diagnosis:" in line,
+                  f"verification_log.md line {i}: FAIL entry lacks `diagnosis:` clause (A4.1 Step 4)")
+
+    # 13) claim-without-coverage — a verification claim must state what it covered
+    #     (A4.4 Gate Function — "verified" without a stated scope is not a result)
+    for i, snippet in claim_without_coverage(vl):
+        check(False,
+              f"verification_log.md line {i}: claim without stated coverage — {snippet!r} (A4.4 claim rule)")
+
+    # 14) secret scan — the change-wave diff / untracked files must not ADD
+    #     credential-looking lines (.md warn-only; placeholder-marked exempt)
+    s14_fails, s14_warns = secret_scan(root, vl)
+    for w in s14_warns:
+        print("WARN " + w)
+    for f in s14_fails:
+        check(False, f)
+
+    # 15) test-change guard — removed test assertions need a logged reason
+    for f in test_change_guard(root, vl):
+        check(False, f)
+
+    # 16) risk-tier — risk-tier code paths require the A4.9 review package
+    for f in risk_tier(root):
+        check(False, f)
+
+    if GIT_TIMEOUT:
+        print("WARN groups 14-16: a git call timed out — content gates ran "
+              "on partial data (fail-open); re-run to confirm")
+
+    if FAILS:
+        print("ASSERT FAILURES (%d):" % len(FAILS))
+        for f in FAILS:
+            print("  - " + f)
+        sys.exit(1)
+    print(f"assert_artifacts.py: all {PASSES} checks pass (exit 0)")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/canonical_suite_run.log b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/canonical_suite_run.log
new file mode 100644
index 0000000..6b0e354
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/canonical_suite_run.log
@@ -0,0 +1,5 @@
+..................................
+----------------------------------------------------------------------
+Ran 34 tests in 0.000s
+
+OK
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/differential_sweep_run.log b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/differential_sweep_run.log
new file mode 100644
index 0000000..fe32881
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/differential_sweep_run.log
@@ -0,0 +1 @@
+SWEEP DONE: checks=8019 failures=0
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/project_profile.json b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/project_profile.json
new file mode 100644
index 0000000..b23a6c7
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/project_profile.json
@@ -0,0 +1,5 @@
+{
+  "profile": "library",
+  "no_service": true,
+  "no_ui": true
+}
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/verification_log.md b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/verification_log.md
new file mode 100644
index 0000000..b9315d1
--- /dev/null
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/tests/verification_log.md
@@ -0,0 +1,10 @@
+# Verification Log — Variable Length Quantity (encode/decode)
+
+> First line of tests/acceptance.md: `> cap=5  stall=3×` (user-owned stop condition)
+
+## Task: variable-length-quantity | 2026-08-29
+- probe: model-native FAIL (image read error: model has no image input; token score 0/6, color MISMATCH) → mm-sensor not in available_skills → Verifier: direct read (no multimodal model, no mm-sensor)
+- Baseline verified GREEN — baseline run: `python3 -c "import variable_length_quantity"` → "module imports OK"; encode/decode present as callables (stubs); no syntax/import errors on the untouched starter tree. Baseline commit: dc937309 (backup: before changes).
+- iter 1 FAIL: criteria #1-#23 (all) | diagnosis: stubs return None — no implementation exists yet (RED evidence, expected failure "None != [...]", 34 tests fail) | changed: tests/test_vlq.py (temp runner, outside workspace)
+- iter 2 PASS: criteria #1-#22 (canonical suite) — evidence: tests/canonical_suite_run.log "Ran 34 tests ... OK" (34/34: encode 21, decode 11, empty-lists 1, includes ValueError cases) | changed: variable_length_quantity.py
+- iter 3 PASS: criterion #23 (differential round-trip sweep) — evidence: tests/differential_sweep_run.log "SWEEP DONE: checks=8019 failures=0" (coverage: 5015 single values incl. 32-bit edges 0/0x7F/0x80/0xFFFFFFF/0xFFFFFFFF + 5000 random, 4 multi-value lists, 3000 random byte sequences, 4 error-path messages checked against an independent string-based reference encode_ref/decode_ref; non-canonical random sequences correctly re-encode to canonical minimal form, >32-bit decode outputs correctly rejected by encode) | changed: none (verification only)
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/variable_length_quantity.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/variable_length_quantity.py
index 41bdcdc..f870617 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/variable_length_quantity.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_before_r3_forced/variable_length_quantity.py
@@ -1,6 +1,30 @@
 def encode(numbers):
-    pass
+    output = []
+    for number in numbers:
+        if number < 0:
+            raise ValueError("negative integer")
+        if number > 0xFFFFFFFF:
+            raise ValueError("integer too large")
+        sequence = [number & 0x7F]
+        number >>= 7
+        while number:
+            sequence.append(0x80 | (number & 0x7F))
+            number >>= 7
+        output.extend(reversed(sequence))
+    return output
 
 
 def decode(bytes_):
-    pass
+    values = []
+    value = 0
+    count = 0
+    for byte in bytes_:
+        value = (value << 7) | (byte & 0x7F)
+        count += 1
+        if byte & 0x80 == 0:
+            values.append(value)
+            value = 0
+            count = 0
+    if count:
+        raise ValueError("incomplete sequence")
+    return values
