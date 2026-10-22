# Review package — W18 release-hygiene fix (2026-10-22)

Scope: F1-F7 + root cause (audit docs/AUDIT_20261022_w18_release_claims.md §Remediation 1-4). Acceptance: dev tree tests/acceptance.md #14-18.
Two trees: DEV = /Users/logan/Documents/DEV/SKILLS/vibeweaver (base d92beee) · REPO = /Users/logan/Documents/DEV/SKILLS/vibeweaver-repo (base d81a7051).

## DEV commits + stat
4d9c6f0 test(w18-fix): harness dual-layout payload resolution (payloadFile) + wave evidence logs
1736ff7 feat(w18-fix): sync_skill controlled list — repo target + evidence-dir parity + --allow-missing-repo
 tests/fix_w18_dev_suite.log  |   6 +++
 tests/fix_w18_repo_suite.log |  12 +++++
 tests/fix_w18_sync_green.log |  17 +++++++
 tests/fix_w18_sync_real.log  |  18 ++++++++
 tests/fix_w18_sync_red.log   |  16 +++++++
 tests/plugin_compat_test.mjs |  16 +++++--
 tests/sync_skill.py          | 107 +++++++++++++++++++++++++++++++++++++++----
 tests/test_sync_skill.py     |  65 ++++++++++++++++++++++++++
 tests/verification_log.md    |  16 +++++++
 tests/working_note.md        |  17 +++++++
 10 files changed, 277 insertions(+), 13 deletions(-)

## REPO commits + stat
134e13c fix(w18): release hygiene — synced harness, no CI quarantine, README counts bound to runs, W18 evidence in-tree, tag w18
 .github/workflows/verify.yml           |   7 +-
 CHANGELOG.md                           |   8 +
 CHANGELOG_zh.md                        |   8 +
 README.md                              |   2 +-
 README_zh.md                           |   2 +-
 check_doc_counts.py                    | 195 ++++++++
 tests/VERIFICATION_LOG_w18_archived.md |  83 ++++
 tests/cdc_green.log                    |  11 +
 tests/cdc_realtree_post.log            |   5 +
 tests/cdc_realtree_pre.log             |   7 +
 tests/cdc_red.log                      |   7 +
 tests/plugin_compat_test.mjs           | 240 +++++++++-
 tests/test_check_doc_counts.py         | 127 +++++
 tests/w18/baseline-build.log           | 744 +++++++++++++++++++++++++++++
 tests/w18/final-assert.log             |   3 +
 tests/w18/final-assert2.log            |   3 +
 tests/w18/final-fresh-build.log        | 814 ++++++++++++++++++++++++++++++++
 tests/w18/final-scan-secrets.log       |   1 +
 tests/w18/iter1-assert-groups.log      |  54 +++
 tests/w18/iter1-build.log              | 751 +++++++++++++++++++++++++++++
 tests/w18/iter1-compat.log             |  92 ++++
 tests/w18/iter3-build.log              | 614 ++++++++++++++++++++++++
 tests/w18/iter4-build.log              | 812 ++++++++++++++++++++++++++++++++
 tests/w18/iter5-assert-groups.log      |  56 +++
 tests/w18/iter5-build.log              | 812 ++++++++++++++++++++++++++++++++
 tests/w18/iter6-assert-groups.log      |  58 +++
 tests/w18/iter6-build.log              | 814 ++++++++++++++++++++++++++++++++
 tests/w18/r1-runbook-drill.log         |  35 ++
 tests/w18/red-revert-assert-r2.log     |   5 +
 tests/w18/red-revert-assert.log        |   3 +
 tests/w18sync/baseline-build.log       | 814 ++++++++++++++++++++++++++++++++
 tests/w18sync/final-scan.log           |   1 +
 tests/w18sync/iter1-build.log          | 831 ++++++++++++++++++++++++++++++++
 tests/w18sync/iter2-build.log          | 832 ++++++++++++++++++++++++++++++++
 tests/w18sync/iter3-build.log          | 617 ++++++++++++++++++++++++
 tests/w18sync/iter4-build.log          | 832 ++++++++++++++++++++++++++++++++
 tests/w18sync/r3-baseline.log          | 832 ++++++++++++++++++++++++++++++++
 tests/w18sync/r3-final.log             | 836 +++++++++++++++++++++++++++++++++
 tests/w18sync/r3-iter1.log             | 617 ++++++++++++++++++++++++
 tests/w18sync/r3-iter2.log             | 617 ++++++++++++++++++++++++
 tests/w18sync/r3-iter3.log             | 834 ++++++++++++++++++++++++++++++++
 tests/w18sync/r3-iter4.log             | 617 ++++++++++++++++++++++++
 42 files changed, 14643 insertions(+), 10 deletions(-)

## DEV diff -U10
diff --git a/tests/plugin_compat_test.mjs b/tests/plugin_compat_test.mjs
index 5fd5dcd..d11263f 100644
--- a/tests/plugin_compat_test.mjs
+++ b/tests/plugin_compat_test.mjs
@@ -998,20 +998,28 @@ const BLOCK = "function foo() {\n  return computeValue(x)\n}\n"
   await h8["experimental.session.compacting"]({ sessionID: "s1" }, out8b)
   rec(
     "D8-gate-v1: delivery survives source deletion via harness snapshot",
     out8b.context.length === 1 && out8b.context[0].includes("ZULU-9") && out8b.context[0].includes("harness snapshot"),
     out8b.context[0] ? out8b.context[0].slice(0, 80) : "none"
   )
 }
 
 // ---------- W18 batch1: G1 three-state seal + G2 write-path shape ----------
 const REPO_ROOT = path.resolve(import.meta.dirname, "..")
+// Dual-layout payload resolution (W18 release-hygiene fix, 2026-10-22): the
+// dev tree keeps the payload at the root, the published repo tree nests it
+// under vibeweaver/ — same fallback contract as the plugin loaders.
+const payloadFile = (rel) => {
+  const local = path.join(REPO_ROOT, rel)
+  return existsSync(local) ? local : path.join(REPO_ROOT, "vibeweaver", rel)
+}
+const payloadScript = (name) => payloadFile(path.join("scripts", name))
 
 // A project scaffold whose assert_artifacts.py run is GREEN and which has NO
 // evidence seal (tests/evidence_manifest.json / tests/test_baseline.json) —
 // the W12 "first write of a wave" state. Self-checked below (fixture-drift
 // guard: a scaffold that stopped passing must fail loudly, not silently).
 function assertGreenProject(name) {
   const root = path.join(TMP, name)
   rmrf(root)
   for (const d of ["tests", "memory", "script/linux"]) mkdirSync(path.join(root, d), { recursive: true })
   writeFileSync(path.join(root, ".gitignore"), ".DS_Store\n__pycache__/\n.venv/\nnode_modules/\n.pnpm-store/\n.env\n")
@@ -1020,21 +1028,21 @@ function assertGreenProject(name) {
     path.join(root, "tests", "verification_log.md"),
     "## Task: fixture | 2026-10-21\n- Baseline verified GREEN\n- iter 1 PASS: all criteria (evidence: scaffold, 1/1)\n- working-note: created → distilled → deleted\n"
   )
   writeFileSync(path.join(root, "memory", "MEMORY.md"), "# Project Memory Index\n- [T](topic.md)\n")
   writeFileSync(path.join(root, "memory", "topic.md"), "# t\n")
   for (const s of ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]) {
     const p = path.join(root, "script", "linux", s)
     writeFileSync(p, "#!/bin/sh\nexit 0\n")
     chmodSync(p, 0o755)
   }
-  writeFileSync(path.join(root, "tests", "assert_artifacts.py"), readFileSync(path.join(REPO_ROOT, "scripts", "assert_artifacts.py"), "utf8"))
+  writeFileSync(path.join(root, "tests", "assert_artifacts.py"), readFileSync(payloadScript("assert_artifacts.py"), "utf8"))
   execFileSync("git", ["init", "-q"], { cwd: root })
   execFileSync("git", ["config", "user.email", "compat@test"], { cwd: root })
   execFileSync("git", ["config", "user.name", "compat"], { cwd: root })
   execFileSync("git", ["add", "-A"], { cwd: root })
   execFileSync("git", ["commit", "-qm", "baseline"], { cwd: root })
   execFileSync("git", ["commit", "-qm", "backup: before changes", "--allow-empty"], { cwd: root })
   return root
 }
 
 function runAssertJson(root) {
@@ -1110,52 +1118,52 @@ function runAssertJson(root) {
   }
   const noSealNote = /evidence seal: none yet/.test(out)
   const assertDetail = j && !j.ok ? JSON.stringify(j.fails).slice(0, 160) : ""
   rec("D10-gate-v1: no-seal root → `evidence seal: none yet` surfaced, NOT GATE-BLOCKED", !!(j && j.ok) && !blocked && noSealNote, blocked ? "BLOCKED: " + out.slice(0, 90) : `assert.ok=${!!(j && j.ok)} note=${noSealNote}${assertDetail ? " fails=" + assertDetail : ""}`)
 }
 
 {
   // G1 three-state (gate side): seal exists + wave code changed after the
   // seal → the stale state BLOCKS and the message keeps its STALE wording.
   const root = assertGreenProject("gate-stale-v1")
-  execFileSync("python3", [path.join(REPO_ROOT, "scripts", "evidence_seal.py")], { cwd: root, encoding: "utf8" })
+  execFileSync("python3", [payloadScript("evidence_seal.py")], { cwd: root, encoding: "utf8" })
   mkdirSync(path.join(root, "src"), { recursive: true })
   writeFileSync(path.join(root, "src", "late.js"), "export const x = 1\n")
   const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
   let blocked = null
   try {
     await loaded.hooks[0]["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "st1", args: { path: path.join(root, "src", "a.js") } }, { output: "ok" })
   } catch (e) {
     blocked = e
   }
   rec("D10b-gate-v1: seal present + code changed after seal → GATE-BLOCKED with STALE", !!blocked && /STALE/.test(String((blocked && blocked.message) || "")), blocked ? "blocked (STALE)" : "UNEXPECTEDLY clean")
 }
 
 {
   // G2 doc↔impl consistency: the trust-model sentence and the implementation
   // must agree — either both exempt tests/ writes or neither does (no gray
   // zone; the W12 drift was exactly this gray zone).
   const gateSrc = readFileSync(GATE_MODULE, "utf8")
   const auditSrc = readFileSync(AUDIT_MODULE, "utf8")
-  const cgSrc = readFileSync(path.join(REPO_ROOT, "COMPLETION_GATE.md"), "utf8")
+  const cgSrc = readFileSync(payloadFile("COMPLETION_GATE.md"), "utf8")
   const docSaysNeverGated = /tests\/`? writes are never gated/.test(cgSrc)
   const implExemptsTests = /isEvidencePath/.test(gateSrc) && /seg === "tests"/.test(gateSrc)
   const auditExemptsTests = /writePathFromArgs/.test(auditSrc) && /isTestDirPath/.test(auditSrc)
   rec("D11-gate-v1: doc↔impl agree that tests/ writes are never gated (gate + audit plugins)", docSaysNeverGated && implExemptsTests && auditExemptsTests, `doc=${docSaysNeverGated} gate=${implExemptsTests} audit=${auditExemptsTests}`)
 }
 
 {
   // G1 three-state (gate side): bootstrap window — a stale seal BEFORE any
   // green `- iter N PASS` in the task block is advisory (note), not a block.
   const root = assertGreenProject("gate-stale-bootstrap-v1")
   writeFileSync(path.join(root, "tests", "verification_log.md"), "## Task: w18-bootstrap\n- Baseline verified GREEN\n- iter 1 FAIL: criterion #1 | diagnosis: the validator ran before state hydration | changed: app/a.py\n- working-note: created (fixture)\n")
-  execFileSync("python3", [path.join(REPO_ROOT, "scripts", "evidence_seal.py")], { cwd: root, encoding: "utf8" })
+  execFileSync("python3", [payloadScript("evidence_seal.py")], { cwd: root, encoding: "utf8" })
   mkdirSync(path.join(root, "src"), { recursive: true })
   writeFileSync(path.join(root, "src", "late.js"), "export const x = 1\n")
   const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
   let blocked = null
   let out = ""
   try {
     const o = { output: "ok" }
     await loaded.hooks[0]["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "sb1", args: { path: path.join(root, "src", "a.js") } }, o)
     out = String(o.output)
   } catch (e) {
diff --git a/tests/sync_skill.py b/tests/sync_skill.py
index ab4b730..5c6812d 100644
--- a/tests/sync_skill.py
+++ b/tests/sync_skill.py
@@ -33,21 +33,25 @@ import os
 import re
 import shutil
 import sys
 from pathlib import Path
 
 DEV = Path(__file__).resolve().parent.parent
 INSTALLED = Path(os.environ.get(
     "VIBEWEAVER_INSTALLED_SKILL",
     Path.home() / ".config" / "opencode" / "skills" / "vibeweaver"))
 EVAL = Path(os.environ.get("VIBEWEAVER_EVAL_DIR", DEV.parent / "vibeweaver-eval"))
+REPO = Path(os.environ.get("VIBEWEAVER_REPO_DIR", DEV.parent / "vibeweaver-repo"))
 TASKS = ("compliance_pricing_tier", "compliance_refund_flow", "compliance_password_reset")
+# W18 release-hygiene fix (2026-10-22, audit F4/F5): evidence dirs that MUST
+# travel with a release — the published repo tree carries byte-identical copies.
+EVIDENCE_DIRS = ("w18", "w18sync")
 SHA_RE = re.compile(r"^[0-9a-f]{64}$")
 
 
 def sha256(path: Path) -> str:
     h = hashlib.sha256()
     with path.open("rb") as f:
         for chunk in iter(lambda: f.read(1 << 20), b""):
             h.update(chunk)
     return h.hexdigest()
 
@@ -61,76 +65,133 @@ def eval_assert_copies(eval_dir: Path):
     ]
 
 
 def eval_scan_copies(eval_dir: Path):
     return [
         ("eval snapshot", eval_dir / "configs" / "fn_latest" / "opencode" / "skills"
          / "vibeweaver" / "scripts" / "scan_secrets.py"),
     ]
 
 
-def copy_plan(dev: Path, installed: Path, eval_dir: Path):
-    """[(label, canonical, [copies])] — every copy a published duplicate."""
-    return [
+def copy_plan(dev: Path, installed: Path, eval_dir: Path, repo: Path = None):
+    """[(label, canonical, [copies])] — every copy a published duplicate.
+
+    `repo=None` means "no repo target" (library callers/tests assemble their
+    own target set); main() always passes the real REPO tree."""
+    plan = [
         ("assert_artifacts.py", dev / "scripts" / "assert_artifacts.py", [
             ("project copy", dev / "tests" / "assert_artifacts.py"),
             ("installed", installed / "scripts" / "assert_artifacts.py"),
             *eval_assert_copies(eval_dir),
         ]),
         ("scan_secrets.py", dev / "scripts" / "scan_secrets.py", [
             ("installed", installed / "scripts" / "scan_secrets.py"),
             *eval_scan_copies(eval_dir),
         ]),
     ]
+    # W18 fix: the compat harness ships next to the payload in the repo
+    # tree — a stale copy there re-opens quarantined failures (audit F1/F3).
+    if repo is not None:
+        plan.append(("plugin_compat_test.mjs", dev / "tests" / "plugin_compat_test.mjs", [
+            ("repo", repo / "tests" / "plugin_compat_test.mjs"),
+        ]))
+    return plan
+
+
+def evidence_parity(dev: Path, repo: Path):
+    """File-set + hash parity for EVIDENCE_DIRS (dev/tests/<d> ↔ repo/tests/<d>).
+
+    Evidence that exists only in the dev tree is exactly the audit's F4 gap:
+    claims published without their anchor. Extra/missing/drifted files all fail
+    closed; --fix restores the set (copies + deletes strays)."""
+    errors, lines = [], []
+    for d in EVIDENCE_DIRS:
+        dev_dir, repo_dir = dev / "tests" / d, repo / "tests" / d
+        if not dev_dir.is_dir():
+            lines.append(f"SKIP evidence {d} (no dev source): {dev_dir}")
+            continue
+        dev_files = {p.relative_to(dev_dir).as_posix(): sha256(p)
+                     for p in sorted(dev_dir.rglob("*")) if p.is_file()}
+        repo_files = ({p.relative_to(repo_dir).as_posix(): sha256(p)
+                       for p in sorted(repo_dir.rglob("*")) if p.is_file()}
+                      if repo_dir.is_dir() else {})
+        before = len(errors)
+        for rel, want in dev_files.items():
+            if rel not in repo_files:
+                errors.append(f"evidence {d}: repo copy missing: {rel}")
+            elif repo_files[rel] != want:
+                errors.append(f"evidence {d}: DRIFT — {rel} expected {want[:12]} "
+                              f"got {repo_files[rel][:12]}")
+        for rel in sorted(set(repo_files) - set(dev_files)):
+            errors.append(f"evidence {d}: extra file in repo copy: {rel}")
+        if len(errors) == before:
+            lines.append(f"OK   evidence {d:8s} {len(dev_files)} file(s) match")
+    return errors, lines
 
 
 def check(dev: Path = DEV, installed: Path = INSTALLED, eval_dir: Path = EVAL,
           allow_missing_eval: bool = False,
-          allow_missing_installed: bool = False):
+          allow_missing_installed: bool = False,
+          repo: Path = None,
+          allow_missing_repo: bool = False):
     """Return (errors, lines). Empty errors == every copy and pin agrees."""
     errors, lines = [], []
     missing_ok = []
     if not eval_dir.is_dir():
         if allow_missing_eval:
             missing_ok.append(f"eval tree absent (allowed): {eval_dir}")
         else:
             errors.append(f"eval tree missing: {eval_dir} (pass --allow-missing-eval "
                           f"only for a dev-only checkout)")
     if not installed.is_dir():
         if allow_missing_installed:
             missing_ok.append(f"installed skill absent (allowed): {installed}")
         else:
             errors.append(f"installed skill missing: {installed} (pass "
                           f"--allow-missing-installed only when it is not installed)")
+    if repo is not None and not repo.is_dir():
+        if allow_missing_repo:
+            missing_ok.append(f"repo tree absent (allowed): {repo}")
+        else:
+            errors.append(f"repo tree missing: {repo} (pass --allow-missing-repo "
+                          f"only for a dev-only checkout)")
 
-    for name, canonical, copies in copy_plan(dev, installed, eval_dir):
+    for name, canonical, copies in copy_plan(dev, installed, eval_dir, repo):
         if not canonical.is_file():
             errors.append(f"canonical missing: {canonical}")
             continue
         want = sha256(canonical)
         lines.append(f"OK   canonical {name} {want[:12]}")
         for label, path in copies:
             if not path.is_file():
                 if _is_eval_copy(label) and allow_missing_eval:
                     missing_ok.append(f"{label} absent (allowed): {path}")
                     continue
                 if label == "installed" and allow_missing_installed:
                     missing_ok.append(f"{label} absent (allowed): {path}")
                     continue
+                if label == "repo" and allow_missing_repo:
+                    missing_ok.append(f"{label} absent (allowed): {path}")
+                    continue
                 errors.append(f"{name}: {label} missing: {path}")
                 continue
             got = sha256(path)
             if got != want:
                 errors.append(f"{name}: {label} DRIFT — expected {want[:12]} got {got[:12]} ({path})")
             else:
                 lines.append(f"OK   {label:18s} {got[:12]}")
 
+    if repo is not None and repo.is_dir():
+        ev_errors, ev_lines = evidence_parity(dev, repo)
+        errors.extend(ev_errors)
+        lines.extend(ev_lines)
+
     # Eval task pins must match the task-local canonical bytes.
     if eval_dir.is_dir():
         for t in TASKS:
             canonical = eval_dir / "suite" / "tasks" / t / "canonical" / "assert_artifacts.py"
             task_json = eval_dir / "suite" / "tasks" / t / "task.json"
             if not canonical.is_file() or not task_json.is_file():
                 errors.append(f"task {t}: canonical file or task.json missing")
                 continue
             want = sha256(canonical)
             try:
@@ -157,46 +218,71 @@ def _is_eval_copy(label: str) -> bool:
 
 
 def _tree_ready(root: Path, *markers: str) -> bool:
     """A tree is 'present' only when its expected sentinel paths exist — an
     empty/bogus sibling directory must not receive scattered skill copies."""
     return root.is_dir() and all((root / m).exists() for m in markers)
 
 
 def apply_fix(dev: Path = DEV, installed: Path = INSTALLED, eval_dir: Path = EVAL,
               allow_missing_eval: bool = False,
-              allow_missing_installed: bool = False):
+              allow_missing_installed: bool = False,
+              repo: Path = None,
+              allow_missing_repo: bool = False):
     """Copy canonical bytes to every READY copy tree and repin task.json.
 
     A target tree that is absent or lacks its sentinel is skipped, never
     invented (avoids scattering skill copies into a bogus sibling path).
     Returns (fixed, skipped).
     """
     fixed, skipped = [], []
     eval_ready = _tree_ready(eval_dir, "suite", "configs")
     installed_ready = _tree_ready(installed, "scripts")
-    for name, canonical, copies in copy_plan(dev, installed, eval_dir):
+    repo_ready = repo is not None and _tree_ready(repo, "vibeweaver", "tests")
+    for name, canonical, copies in copy_plan(dev, installed, eval_dir, repo):
         if not canonical.is_file():
             continue
         want = sha256(canonical)
         for label, path in copies:
             if _is_eval_copy(label) and not eval_ready:
                 skipped.append(f"{label} — eval tree absent/incomplete ({eval_dir})")
                 continue
             if label == "installed" and not installed_ready:
                 skipped.append(f"{label} — installed skill absent/incomplete ({installed})")
                 continue
+            if label == "repo" and not repo_ready:
+                skipped.append(f"{label} — repo tree absent/incomplete ({repo})")
+                continue
             path.parent.mkdir(parents=True, exist_ok=True)
             same = path.is_file() and sha256(path) == want
             if not same:
                 shutil.copyfile(canonical, path)
                 fixed.append(f"{name}: {label} <- {canonical}")
+    if repo_ready:
+        for d in EVIDENCE_DIRS:
+            dev_dir, repo_dir = dev / "tests" / d, repo / "tests" / d
+            if not dev_dir.is_dir():
+                continue
+            dev_files = {p.relative_to(dev_dir).as_posix(): p
+                         for p in sorted(dev_dir.rglob("*")) if p.is_file()}
+            repo_files = ({p.relative_to(repo_dir).as_posix(): p
+                           for p in sorted(repo_dir.rglob("*")) if p.is_file()}
+                          if repo_dir.is_dir() else {})
+            for rel, src in dev_files.items():
+                dst = repo_dir / rel
+                if rel not in repo_files or sha256(src) != sha256(dst):
+                    dst.parent.mkdir(parents=True, exist_ok=True)
+                    shutil.copyfile(src, dst)
+                    fixed.append(f"evidence {d}: {rel} <- {src}")
+            for rel in sorted(set(repo_files) - set(dev_files)):
+                repo_files[rel].unlink()
+                fixed.append(f"evidence {d}: removed stray {rel}")
     if eval_ready:
         for t in TASKS:
             canonical = eval_dir / "suite" / "tasks" / t / "canonical" / "assert_artifacts.py"
             task_json = eval_dir / "suite" / "tasks" / t / "task.json"
             if not canonical.is_file() or not task_json.is_file():
                 continue
             want = sha256(canonical)
             text = task_json.read_text()
             new, n = re.subn(r'("canonical_assert_sha"\s*:\s*")[0-9a-f]{64}(")',
                              lambda m: m.group(1) + want + m.group(2), text)
@@ -206,30 +292,33 @@ def apply_fix(dev: Path = DEV, installed: Path = INSTALLED, eval_dir: Path = EVA
                 task_json.write_text(new)
                 fixed.append(f"pin {t} <- {want[:12]}")
     return fixed, skipped
 
 
 def main(argv=None):
     ap = argparse.ArgumentParser()
     ap.add_argument("--fix", action="store_true", help="copy canonical bytes + repin")
     ap.add_argument("--allow-missing-eval", action="store_true")
     ap.add_argument("--allow-missing-installed", action="store_true")
+    ap.add_argument("--allow-missing-repo", action="store_true")
     args = ap.parse_args(argv)
     if args.fix:
         fixed, skipped = apply_fix(allow_missing_eval=args.allow_missing_eval,
-                                   allow_missing_installed=args.allow_missing_installed)
+                                   allow_missing_installed=args.allow_missing_installed,
+                                   repo=REPO, allow_missing_repo=args.allow_missing_repo)
         for line in fixed:
             print(f"FIX  {line}")
         for line in skipped:
             print(f"SKIP {line}")
     errors, lines = check(allow_missing_eval=args.allow_missing_eval,
-                          allow_missing_installed=args.allow_missing_installed)
+                          allow_missing_installed=args.allow_missing_installed,
+                          repo=REPO, allow_missing_repo=args.allow_missing_repo)
     for line in lines:
         print(line)
     for line in errors:
         print(f"FAIL {line}", file=sys.stderr)
     if errors:
         print(f"sync_skill.py: {len(errors)} drift/missing item(s) — FAIL (exit 1)",
               file=sys.stderr)
         return 1
     print("sync_skill.py: clean — every copy and pin agrees (exit 0)")
     return 0
diff --git a/tests/test_sync_skill.py b/tests/test_sync_skill.py
index cf9b4e3..2f1e243 100644
--- a/tests/test_sync_skill.py
+++ b/tests/test_sync_skill.py
@@ -50,20 +50,41 @@ def build(root):
         target.write_bytes((dev / "scripts" / "scan_secrets.py").read_bytes())
     for task in sync_skill.TASKS:
         canonical = evald / "suite" / "tasks" / task / "canonical" / "assert_artifacts.py"
         canonical.parent.mkdir(parents=True)
         canonical.write_bytes((dev / "scripts" / "assert_artifacts.py").read_bytes())
         (canonical.parent.parent / "task.json").write_text(json.dumps(
             {"compliance": {"canonical_assert_sha": sha(canonical)}}, indent=2) + "\n")
     return dev, installed, evald
 
 
+def build_full(root):
+    """Miniature tree that also carries a repo copy + W18 evidence dirs."""
+    dev, installed, evald = build(root / "repo-wave")
+    (dev / "tests" / "plugin_compat_test.mjs").write_text("harness-v1\n")
+    for d in sync_skill.EVIDENCE_DIRS:
+        (dev / "tests" / d).mkdir(parents=True, exist_ok=True)
+        (dev / "tests" / d / f"{d}-a.log").write_text(f"{d} evidence A\n")
+        (dev / "tests" / d / f"{d}-b.log").write_text(f"{d} evidence B\n")
+    repo = dev.parent / "repo"
+    (repo / "vibeweaver").mkdir(parents=True)
+    (repo / "tests").mkdir(parents=True)
+    (repo / "vibeweaver" / "SKILL.md").write_text("payload sentinel\n")
+    (repo / "tests" / "plugin_compat_test.mjs").write_bytes(
+        (dev / "tests" / "plugin_compat_test.mjs").read_bytes())
+    for d in sync_skill.EVIDENCE_DIRS:
+        (repo / "tests" / d).mkdir(parents=True, exist_ok=True)
+        for f in (dev / "tests" / d).iterdir():
+            (repo / "tests" / d / f.name).write_bytes(f.read_bytes())
+    return dev, installed, evald, repo
+
+
 def main():
     root = pathlib.Path(tempfile.mkdtemp(prefix="vwsync-"))
     dev, installed, evald = build(root)
 
     errors, _ = sync_skill.check(dev, installed, evald)
     rec("SS1 clean miniature tree → no drift", not errors, "; ".join(errors)[:140])
 
     snap = (evald / "configs" / "fn_latest" / "opencode" / "skills"
             / "vibeweaver" / "scripts" / "assert_artifacts.py")
     snap.write_text("tampered\n")
@@ -104,20 +125,64 @@ def main():
     # configs/ or suite/ subtree is invented inside it.
     empty_eval = root / "eval-empty"
     empty_eval.mkdir()
     fixed, skipped = sync_skill.apply_fix(dev, installed, empty_eval,
                                           allow_missing_eval=True)
     rec("SS8 --fix does not populate an incomplete eval tree",
         not (empty_eval / "configs").exists() and not (empty_eval / "suite").exists()
         and any("incomplete" in s for s in skipped),
         f"configs={(empty_eval / 'configs').exists()} skipped={len(skipped)}")
 
+    # SS9-SS13 (W18 release-hygiene fix, 2026-10-22): the repo tree joined the
+    # controlled list — plugin_compat harness byte parity + evidence-dir parity.
+    dev2, installed2, evald2, repo2 = build_full(root)
+
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS9 clean tree incl. repo harness + evidence → no drift", not errors,
+        "; ".join(errors)[:140])
+
+    (repo2 / "tests" / "plugin_compat_test.mjs").write_text("stale harness\n")
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS10 stale repo harness → fail closed",
+        any("plugin_compat_test.mjs" in e and "DRIFT" in e for e in errors),
+        "; ".join(errors)[:160])
+
+    sync_skill.apply_fix(dev2, installed2, evald2, repo=repo2)
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS11 --fix restores the repo harness", not errors, "; ".join(errors)[:140])
+
+    (repo2 / "tests" / "w18" / "w18-a.log").unlink()
+    (repo2 / "tests" / "w18" / "w18-extra.log").write_text("stray\n")
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS12 evidence set mismatch (missing + extra) → fail closed",
+        any("missing" in e for e in errors) and any("extra" in e for e in errors),
+        "; ".join(errors)[:160])
+
+    sync_skill.apply_fix(dev2, installed2, evald2, repo=repo2)
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS13 --fix restores the evidence set", not errors, "; ".join(errors)[:140])
+
+    missing_repo = root / "repo-absent"
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=missing_repo,
+                                 allow_missing_repo=True)
+    fixed, skipped = sync_skill.apply_fix(dev2, installed2, evald2, repo=missing_repo,
+                                          allow_missing_repo=True)
+    rec("SS14 --allow-missing-repo skips, never invents the repo tree",
+        not errors and not missing_repo.exists()
+        and any("repo tree" in s for s in skipped),
+        f"errors={len(errors)} exists={missing_repo.exists()} skipped={len(skipped)}")
+
+    (repo2 / "tests" / "w18sync" / "w18sync-b.log").write_text("tampered\n")
+    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
+    rec("SS15 tampered evidence file → fail closed",
+        any("w18sync" in e and "DRIFT" in e for e in errors), "; ".join(errors)[:160])
+
     fails = [n for n, ok, _ in RESULTS if not ok]
     print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
           (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
     return 1 if fails else 0
 
 
 def test_sync_skill_vectors():
     """pytest entry point (the file is also a direct-run harness)."""
     assert main() == 0
 

## REPO diff -U10 (code/config)
diff --git a/.github/workflows/verify.yml b/.github/workflows/verify.yml
index 2515413..84008f0 100644
--- a/.github/workflows/verify.yml
+++ b/.github/workflows/verify.yml
@@ -35,26 +35,29 @@ jobs:
       - name: Setup Node
         uses: actions/setup-node@v5
         with:
           node-version: "20"
 
       - name: Audit selftest + mutation sweep (node, required)
         run: |
           node vibeweaver/scripts/audit_selftest.mjs
           node vibeweaver/scripts/mutation_sweep.mjs
 
-      - name: Plugin compat harness (node, known E3/G9 allowed)
-        run: node tests/plugin_compat_test.mjs --allow-known
+      - name: Plugin compat harness (node, no quarantine)
+        run: node tests/plugin_compat_test.mjs
 
       - name: Mini checker gate harness
         run: node tests/mini_gate_test.mjs
 
+      - name: Doc claims parity (README counts vs harness runs)
+        run: python3 check_doc_counts.py
+
       - name: Mini installers (Windows)
         if: runner.os == 'Windows'
         shell: cmd
         run: |
           call vibeweaver-mini\install.bat
           if errorlevel 1 exit /b 1
           mkdir "%TEMP%\vw-mini-proj"
           call vibeweaver-mini\scripts\setup_project.bat "%TEMP%\vw-mini-proj"
           if not exist "%TEMP%\vw-mini-proj\vw_check.py" exit /b 1
           if not exist "%TEMP%\vw-mini-proj\script\check.sh" exit /b 1
diff --git a/check_doc_counts.py b/check_doc_counts.py
new file mode 100644
index 0000000..21be4d9
--- /dev/null
+++ b/check_doc_counts.py
@@ -0,0 +1,195 @@
+#!/usr/bin/env python3
+"""check_doc_counts.py — bind README test-count claims to a real run.
+
+W18 audit (2026-10-22) found the published README/CHANGELOG stating counts no
+in-tree run could reproduce ("plugin compat 82/82" over a tree that ran 70/71 —
+audit findings F1/F6). Numbers in prose drift; runs do not. This checker makes
+the docs' claims executable:
+
+  1. run each suite and parse its SUMMARY count(s)
+  2. extract every count claim the READMEs state ON THE LINE THAT NAMES THE
+     SUITE'S COMMAND (a claim is bound to the command that reproduces it;
+     historical prose counts — wave notes, benchmark tables — are not claims)
+  3. fail on any mismatch, on a red suite (failures must be 0 for claims to
+     bind), on a suite the docs never quantify, and on any leftover CI
+     quarantine flag (`--allow-known`: the W18 audit's F2 — a green CI over a
+     live failure)
+
+Usage:
+  python3 check_doc_counts.py            # run suites + check README claims
+  python3 check_doc_counts.py --skip-run # doc shapes only (no suite execution)
+
+Exit 0 = every stated count equals what this tree prints. Stdlib only.
+"""
+import re
+import subprocess
+import sys
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parent
+
+# claim = the regex that captures the claim ON an anchor line;
+# run   = the SUMMARY regex of an executed suite (group 1..n).
+SUITES = {
+    "selftest": {
+        "cmd": ["node", "vibeweaver/scripts/audit_selftest.mjs"],
+        "anchor": "audit_selftest",
+        "claim": re.compile(r"(\d+)\s*(?:项\s*)?fixture\s*(?:checks|检查)"),
+        "run": re.compile(r"fixture checks: (\d+), failures: (\d+)"),
+    },
+    "mutation": {
+        "cmd": ["node", "vibeweaver/scripts/mutation_sweep.mjs"],
+        "anchor": "mutation_sweep",
+        "claim": re.compile(r"(\d+)\s*(?:项\s*)?(?:mutations?|变异)"),
+        "run": re.compile(r"MUTATION SWEEP: (\d+) passed, (\d+) failed"),
+    },
+    "compat": {
+        "cmd": ["node", "tests/plugin_compat_test.mjs"],
+        "anchor": "plugin_compat",
+        "claim": re.compile(r"(?<![\w.])(\d+)\s*/\s*(\d+)"),
+        "run": re.compile(r"COMPAT HARNESS: (\d+)/(\d+) passed, (\d+) failed"),
+    },
+    "mini": {
+        "cmd": ["node", "tests/mini_gate_test.mjs"],
+        "anchor": "mini_gate",
+        "claim": re.compile(r"(?<![\w.])(\d+)\s*/\s*(\d+)"),
+        "run": re.compile(r"RESULT: (\d+)/(\d+) passed, (\d+) failed"),
+    },
+}
+
+QUARANTINE = re.compile(r"allow[-_]?known|allowKnown|E3/G9 allowed")
+QUARANTINE_FILES = (".github/workflows/verify.yml", "tests/plugin_compat_test.mjs")
+DOCS = ("README.md", "README_zh.md")
+
+
+def _to_value(key, groups):
+    """Claim/run groups → the canonical value for a suite."""
+    if key in ("selftest", "mutation"):
+        return int(groups[0])
+    return (int(groups[0]), int(groups[1]))
+
+
+def fmt(value):
+    return f"{value[0]}/{value[1]}" if isinstance(value, tuple) else str(value)
+
+
+def extract_claims(text):
+    """{suite: [claimed values]} — only lines that name the suite's command.
+
+    Prose that merely mentions a number (wave notes, benchmark tables) never
+    names the command and is therefore never a claim."""
+    claims = {}
+    for line in text.splitlines():
+        for key, spec in SUITES.items():
+            if spec["anchor"] not in line:
+                continue
+            for m in spec["claim"].finditer(line):
+                value = _to_value(key, m.groups())
+                seen = claims.setdefault(key, [])
+                if value not in seen:  # distinct claims only — same value twice
+                    seen.append(value)  # (command line + files row) is one claim
+    return claims
+
+
+def parse_run(key, text):
+    """Suite SUMMARY output → canonical value, None when unparseable."""
+    m = SUITES[key]["run"].search(text)
+    if not m:
+        return None
+    if key in ("selftest", "mutation"):
+        return (int(m.group(1)), int(m.group(2)))
+    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
+
+
+def compare_counts(runs, claims):
+    """Every stated claim must equal the run; a red run binds nothing."""
+    errors = []
+    for key in SUITES:
+        run = runs.get(key)
+        if run is None:
+            errors.append(f"{key}: run output unparseable — cannot bind claims")
+            continue
+        failed = run[-1]
+        if failed:
+            errors.append(f"{key}: suite red ({failed} failed) — claims cannot bind a red run")
+            continue
+        runval = _to_value(key, run)
+        got = claims.get(key)
+        if not got:
+            errors.append(f"{key}: no count claim found in the docs "
+                          f"(state {fmt(runval)} next to the command)")
+            continue
+        for claim in got:
+            if claim != runval:
+                errors.append(f"{key}: claim {fmt(claim)} != run {fmt(runval)}")
+    return errors
+
+
+def scan_quarantine_text(text):
+    """True when a quarantine escape hatch is present (CI/harness files).
+
+    Full-line comments are not code: a historical note that documents the
+    quarantine's REMOVAL (tests/plugin_compat_test.mjs W18 D-W18-2 comment)
+    must not trip the ban — an in-effect handler or a CI flag always sits on
+    an executable line."""
+    for line in text.splitlines():
+        stripped = line.strip()
+        if stripped.startswith("//") or stripped.startswith("#"):
+            continue
+        if QUARANTINE.search(line):
+            return True
+    return False
+
+
+def scan_quarantine(root=ROOT):
+    errors = []
+    for rel in QUARANTINE_FILES:
+        path = root / rel
+        if path.is_file() and scan_quarantine_text(path.read_text(errors="replace")):
+            errors.append(f"{rel}: quarantine flag present — CI must run without --allow-known")
+    return errors
+
+
+def run_suite(key):
+    spec = SUITES[key]
+    try:
+        proc = subprocess.run(spec["cmd"], cwd=str(ROOT), text=True,
+                              capture_output=True, timeout=900)
+    except (OSError, subprocess.TimeoutExpired) as exc:
+        return None, f"{key}: run failed to execute ({exc})"
+    return parse_run(key, proc.stdout + proc.stderr), None
+
+
+def main(argv=None):
+    argv = argv if argv is not None else sys.argv[1:]
+    skip_run = "--skip-run" in argv
+    errors, runs = [], {}
+    for key in SUITES:
+        if skip_run:
+            continue
+        value, err = run_suite(key)
+        runs[key] = value
+        if err:
+            errors.append(err)
+    for rel in DOCS:
+        path = ROOT / rel
+        if not path.is_file():
+            errors.append(f"{rel}: missing — the counts live here")
+            continue
+        claims = extract_claims(path.read_text(errors="replace"))
+        errors.extend(f"{rel}: {e}" for e in compare_counts(runs, claims))
+    errors.extend(scan_quarantine(ROOT))
+    for key in SUITES:
+        print(f"{'SKIP' if skip_run else 'RUN '} {key:9s} "
+              f"{fmt(_to_value(key, runs[key])) if runs.get(key) else '(not run)'}")
+    for err in errors:
+        print(f"FAIL {err}")
+    if errors:
+        print(f"check_doc_counts.py: {len(errors)} claim mismatch(es) — FAIL (exit 1)")
+        return 1
+    print("check_doc_counts.py: every stated count equals this tree's runs (exit 0)")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tests/plugin_compat_test.mjs b/tests/plugin_compat_test.mjs
index 3f07f20..d11263f 100644
--- a/tests/plugin_compat_test.mjs
+++ b/tests/plugin_compat_test.mjs
@@ -8,21 +8,21 @@
 //     ("tool.execute.before"/"tool.execute.after"/"event").
 //   - v2.0.16 semantics: PluginModule schema (default export must be
 //     {id, setup} or {id, effect}; excess keys tolerated), then setup(ctx)
 //     with a fake Promise-plugin context (tool.hook / event.subscribe /
 //     location / app / options), hook invocation with v2 event shapes.
 //
 // Usage: node tests/plugin_compat_test.mjs
 // Exit 0 only when every check passes.
 
 import { execFileSync } from "node:child_process"
-import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
+import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
 import os from "node:os"
 import { pathToFileURL } from "node:url"
 import path from "node:path"
 
 const GATE_MODULE = (() => {
   const local = path.resolve(import.meta.dirname, "..", "vibeweaver-gate.js")
   const nested = path.resolve(import.meta.dirname, "..", "vibeweaver", "vibeweaver-gate.js")
   return existsSync(local) ? local : nested
 })()
 const AUDIT_MODULE = (() => {
@@ -591,21 +591,38 @@ async function newAuditV1(root) {
   rec("E2-audit-v1: test-dir write stays writable under RED latch", !blockedTest, blockedTest ? "blocked" : "clean")
 
   const root2 = auditLatchedProject("audit-red-v1b", "s-other")
   const auditHooksV1b = await newAuditV1(root2)
   let blockedOther = null
   try {
     await auditHooksV1b["tool.execute.before"]({ tool: "write", sessionID: "s-new", callID: "c3" }, { args: { filePath: path.join(root2, "src", "a.js") } })
   } catch (e) {
     blockedOther = e
   }
-  rec("E3-audit-v1: stale (other-session) latch auto-releases on write", !blockedOther, blockedOther ? "blocked" : "clean")
+  // W18 D-W18-2 re-spec — spec-test-conflict flag (VERIFICATION_UPGRADES §V2
+  // rule 2/3, ADR D-W18-3): this case asserted the PRE-D3 behavior ("a
+  // foreign session's write auto-releases the stale latch"). D3 (2026-10-15
+  // adversarial-review PoC: one subagent/task-tool write bypassed the whole
+  // gate) and ADR D-p0-1 deliberately REMOVED that release path; the spec
+  // (releaseStale's rule list + the foreign-block message) is the source of
+  // truth for code behavior, so the assertion is TIGHTENED to it: a foreign
+  // write releases nothing and is itself blocked. Reverting the assertion to
+  // the old expectation would re-open the documented bypass.
+  rec("E3-audit-v1: D3 — a foreign write releases nothing and is blocked (subagent bypass closed)", !!blockedOther && /still pending/.test(String(blockedOther && blockedOther.message)), blockedOther ? "blocked (D3)" : "UNEXPECTEDLY clean — foreign write released the latch")
+  let latchAfter = null
+  try {
+    const st3 = JSON.parse(readFileSync(path.join(root2, ".vibeweaver", "audit-state.json"), "utf8"))
+    latchAfter = (st3.roots && st3.roots[root2] && st3.roots[root2].red) || null
+  } catch {
+    latchAfter = null
+  }
+  rec("E3b-audit-v1: the latch survives the foreign write (no release recorded)", !!latchAfter && latchAfter.sessionID === "s-other", latchAfter ? `latched=${latchAfter.sessionID}` : "latch gone")
 }
 
 if (auditV2def) {
   const root = auditLatchedProject("audit-red-v2", "s-red")
   const { ctx, toolHooks, bus } = makeV2Ctx(root)
   const cleanup = await auditV2def.value.setup(ctx)
   rec("F0-audit-v2: setup(ctx) registers execute.before hook + cleanup", toolHooks.before.length === 1 && typeof cleanup === "function", `before=${toolHooks.before.length} cleanup=${typeof cleanup}`)
 
   let blocked = null
   try {
@@ -979,15 +996,226 @@ const BLOCK = "function foo() {\n  return computeValue(x)\n}\n"
   rmSync(path.join(root8, "tests", "working_note.md"), { force: true })
   const out8b = { context: [] }
   await h8["experimental.session.compacting"]({ sessionID: "s1" }, out8b)
   rec(
     "D8-gate-v1: delivery survives source deletion via harness snapshot",
     out8b.context.length === 1 && out8b.context[0].includes("ZULU-9") && out8b.context[0].includes("harness snapshot"),
     out8b.context[0] ? out8b.context[0].slice(0, 80) : "none"
   )
 }
 
+// ---------- W18 batch1: G1 three-state seal + G2 write-path shape ----------
+const REPO_ROOT = path.resolve(import.meta.dirname, "..")
+// Dual-layout payload resolution (W18 release-hygiene fix, 2026-10-22): the
+// dev tree keeps the payload at the root, the published repo tree nests it
+// under vibeweaver/ — same fallback contract as the plugin loaders.
+const payloadFile = (rel) => {
+  const local = path.join(REPO_ROOT, rel)
+  return existsSync(local) ? local : path.join(REPO_ROOT, "vibeweaver", rel)
+}
+const payloadScript = (name) => payloadFile(path.join("scripts", name))
+
+// A project scaffold whose assert_artifacts.py run is GREEN and which has NO
+// evidence seal (tests/evidence_manifest.json / tests/test_baseline.json) —
+// the W12 "first write of a wave" state. Self-checked below (fixture-drift
+// guard: a scaffold that stopped passing must fail loudly, not silently).
+function assertGreenProject(name) {
+  const root = path.join(TMP, name)
+  rmrf(root)
+  for (const d of ["tests", "memory", "script/linux"]) mkdirSync(path.join(root, d), { recursive: true })
+  writeFileSync(path.join(root, ".gitignore"), ".DS_Store\n__pycache__/\n.venv/\nnode_modules/\n.pnpm-store/\n.env\n")
+  writeFileSync(path.join(root, "tests", "acceptance.md"), "> cap=5  stall=3×\n\n# Acceptance\n1. ok\n")
+  writeFileSync(
+    path.join(root, "tests", "verification_log.md"),
+    "## Task: fixture | 2026-10-21\n- Baseline verified GREEN\n- iter 1 PASS: all criteria (evidence: scaffold, 1/1)\n- working-note: created → distilled → deleted\n"
+  )
+  writeFileSync(path.join(root, "memory", "MEMORY.md"), "# Project Memory Index\n- [T](topic.md)\n")
+  writeFileSync(path.join(root, "memory", "topic.md"), "# t\n")
+  for (const s of ["start.sh", "stop.sh", "restart.sh", "project_build.sh"]) {
+    const p = path.join(root, "script", "linux", s)
+    writeFileSync(p, "#!/bin/sh\nexit 0\n")
+    chmodSync(p, 0o755)
+  }
+  writeFileSync(path.join(root, "tests", "assert_artifacts.py"), readFileSync(payloadScript("assert_artifacts.py"), "utf8"))
+  execFileSync("git", ["init", "-q"], { cwd: root })
+  execFileSync("git", ["config", "user.email", "compat@test"], { cwd: root })
+  execFileSync("git", ["config", "user.name", "compat"], { cwd: root })
+  execFileSync("git", ["add", "-A"], { cwd: root })
+  execFileSync("git", ["commit", "-qm", "baseline"], { cwd: root })
+  execFileSync("git", ["commit", "-qm", "backup: before changes", "--allow-empty"], { cwd: root })
+  return root
+}
+
+function runAssertJson(root) {
+  const out = execFileSync("python3", ["tests/assert_artifacts.py", "--existing", "--json"], { cwd: root, encoding: "utf8" })
+  return JSON.parse(out.slice(out.indexOf("{")))
+}
+
+{
+  // G2 — the REAL host write/edit tools carry the target as `args.path`
+  // (opencode write {path, content} / edit {path, oldString, newString}); the
+  // gate read only `args.filePath`, so its tests/-evidence exemption
+  // (COMPLETION_GATE §A4.4.2 "tests/ writes are never gated") never engaged
+  // and every evidence write was GATE-BLOCKED (W12: 30+ false blocks; W18
+  // reproduced live on this repo's first write of the wave). Args-shape parity.
+  const root = redProject("gate-argspath-red")
+  const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
+  const h = loaded.hooks[0]
+  let blockedTests = null
+  try {
+    await h["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "ap1", args: { path: path.join(root, "tests", "acceptance.md"), content: "x" } }, { output: "ok" })
+  } catch (e) {
+    blockedTests = e
+  }
+  rec("D9-gate-v1: host args.path shape — tests/ write is never gated", !blockedTests, blockedTests ? "BLOCKED (args.path unseen)" : "clean")
+  let blockedSrc = null
+  try {
+    await h["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "ap2", args: { path: path.join(root, "src", "x.js"), content: "x" } }, { output: "ok" })
+  } catch (e) {
+    blockedSrc = e
+  }
+  rec("D9b-gate-v1: host args.path shape — src write on a RED project still BLOCKS", !!blockedSrc && /GATE-BLOCKED/.test(String((blockedSrc && blockedSrc.message) || "")), blockedSrc ? "blocked" : "UNEXPECTEDLY clean")
+  if (gateV2def) {
+    const root2 = redProject("gate-argspath-red-v2")
+    const { ctx, toolHooks } = makeV2Ctx(root2)
+    await gateV2def.value.setup(ctx)
+    let b1 = null
+    try {
+      await toolHooks.after[0]({ tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "ap3", input: { path: path.join(root2, "tests", "verification_log.md"), content: "x" }, status: "completed", result: { content: "ok" } })
+    } catch (e) {
+      b1 = e
+    }
+    let b2 = null
+    try {
+      await toolHooks.after[0]({ tool: "write", sessionID: "s1", agent: "a", messageID: "m1", id: "ap4", input: { path: path.join(root2, "src", "y.js"), content: "x" }, status: "completed", result: { content: "ok" } })
+    } catch (e) {
+      b2 = e
+    }
+    rec("D9c-gate-v2: host args.path shape — tests/ writable, src still BLOCKS", !b1 && !!b2, `tests=${b1 ? "blocked" : "clean"} src=${b2 ? "blocked" : "clean"}`)
+  }
+}
+
+{
+  // G1 three-state (gate side): NO seal at all is a bootstrap state — the
+  // gate surfaces `evidence seal: none yet` as a non-blocking note and does
+  // NOT GATE-BLOCKED (missing != violation; OWASP first-run-baseline).
+  const root = assertGreenProject("gate-noseal-v1")
+  let j = null
+  try {
+    j = runAssertJson(root)
+  } catch (e) {
+    j = { ok: false, fails: [{ detail: "assert run crashed: " + String(e).slice(0, 160) }] }
+  }
+  const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
+  let blocked = null
+  let out = ""
+  try {
+    const o = { output: "ok" }
+    await loaded.hooks[0]["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "ns1", args: { path: path.join(root, "src", "a.js") } }, o)
+    out = String(o.output)
+  } catch (e) {
+    blocked = e
+    out = String((e && e.message) || "")
+  }
+  const noSealNote = /evidence seal: none yet/.test(out)
+  const assertDetail = j && !j.ok ? JSON.stringify(j.fails).slice(0, 160) : ""
+  rec("D10-gate-v1: no-seal root → `evidence seal: none yet` surfaced, NOT GATE-BLOCKED", !!(j && j.ok) && !blocked && noSealNote, blocked ? "BLOCKED: " + out.slice(0, 90) : `assert.ok=${!!(j && j.ok)} note=${noSealNote}${assertDetail ? " fails=" + assertDetail : ""}`)
+}
+
+{
+  // G1 three-state (gate side): seal exists + wave code changed after the
+  // seal → the stale state BLOCKS and the message keeps its STALE wording.
+  const root = assertGreenProject("gate-stale-v1")
+  execFileSync("python3", [payloadScript("evidence_seal.py")], { cwd: root, encoding: "utf8" })
+  mkdirSync(path.join(root, "src"), { recursive: true })
+  writeFileSync(path.join(root, "src", "late.js"), "export const x = 1\n")
+  const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
+  let blocked = null
+  try {
+    await loaded.hooks[0]["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "st1", args: { path: path.join(root, "src", "a.js") } }, { output: "ok" })
+  } catch (e) {
+    blocked = e
+  }
+  rec("D10b-gate-v1: seal present + code changed after seal → GATE-BLOCKED with STALE", !!blocked && /STALE/.test(String((blocked && blocked.message) || "")), blocked ? "blocked (STALE)" : "UNEXPECTEDLY clean")
+}
+
+{
+  // G2 doc↔impl consistency: the trust-model sentence and the implementation
+  // must agree — either both exempt tests/ writes or neither does (no gray
+  // zone; the W12 drift was exactly this gray zone).
+  const gateSrc = readFileSync(GATE_MODULE, "utf8")
+  const auditSrc = readFileSync(AUDIT_MODULE, "utf8")
+  const cgSrc = readFileSync(payloadFile("COMPLETION_GATE.md"), "utf8")
+  const docSaysNeverGated = /tests\/`? writes are never gated/.test(cgSrc)
+  const implExemptsTests = /isEvidencePath/.test(gateSrc) && /seg === "tests"/.test(gateSrc)
+  const auditExemptsTests = /writePathFromArgs/.test(auditSrc) && /isTestDirPath/.test(auditSrc)
+  rec("D11-gate-v1: doc↔impl agree that tests/ writes are never gated (gate + audit plugins)", docSaysNeverGated && implExemptsTests && auditExemptsTests, `doc=${docSaysNeverGated} gate=${implExemptsTests} audit=${auditExemptsTests}`)
+}
+
+{
+  // G1 three-state (gate side): bootstrap window — a stale seal BEFORE any
+  // green `- iter N PASS` in the task block is advisory (note), not a block.
+  const root = assertGreenProject("gate-stale-bootstrap-v1")
+  writeFileSync(path.join(root, "tests", "verification_log.md"), "## Task: w18-bootstrap\n- Baseline verified GREEN\n- iter 1 FAIL: criterion #1 | diagnosis: the validator ran before state hydration | changed: app/a.py\n- working-note: created (fixture)\n")
+  execFileSync("python3", [payloadScript("evidence_seal.py")], { cwd: root, encoding: "utf8" })
+  mkdirSync(path.join(root, "src"), { recursive: true })
+  writeFileSync(path.join(root, "src", "late.js"), "export const x = 1\n")
+  const loaded = await loadAsV1(gateMod, { client: { app: { log: async () => {} } }, directory: root }, "vibeweaver-gate")
+  let blocked = null
+  let out = ""
+  try {
+    const o = { output: "ok" }
+    await loaded.hooks[0]["tool.execute.after"]({ tool: "write", sessionID: "s1", callID: "sb1", args: { path: path.join(root, "src", "a.js") } }, o)
+    out = String(o.output)
+  } catch (e) {
+    blocked = e
+    out = String((e && e.message) || "")
+  }
+  rec("D10c-gate-v1: bootstrap window (stale seal, no green PASS) → advisory STALE note, NOT GATE-BLOCKED", !blocked && /STALE/.test(out) && /advisory/.test(out), blocked ? "BLOCKED: " + out.slice(0, 90) : out.slice(0, 90))
+}
+
+{
+  // G2 parity — the SECOND write-gating plugin (review A Critical #2): the
+  // audit plugin's RED-latch evidence-fix exemption must also honor the real
+  // host arg shape, or a latched session cannot write tests/acceptance.md
+  // despite the block message promising exactly that.
+  const root = auditLatchedProject("audit-argspath", "s-red")
+  const hooks = await newAuditV1(root)
+  let blockedTests = null
+  try {
+    await hooks["tool.execute.before"]({ tool: "write", sessionID: "s-red", callID: "at1" }, { args: { path: path.join(root, "tests", "acceptance.md"), content: "x" } })
+  } catch (e) {
+    blockedTests = e
+  }
+  rec("D12-audit-v1: host args.path shape — tests/ write stays writable under the RED latch", !blockedTests, blockedTests ? "BLOCKED (args.path unseen)" : "clean")
+  let blockedSrc = null
+  try {
+    await hooks["tool.execute.before"]({ tool: "write", sessionID: "s-red", callID: "at2" }, { args: { path: path.join(root, "src", "x.js"), content: "x" } })
+  } catch (e) {
+    blockedSrc = e
+  }
+  rec("D12b-audit-v1: host args.path shape — the latching session's src write still BLOCKS", !!blockedSrc && /GATE-BLOCKED \(vibeweaver-audit\)/.test(String((blockedSrc && blockedSrc.message) || "")), blockedSrc ? "blocked" : "UNEXPECTEDLY clean")
+  if (auditV2def) {
+    const root2 = auditLatchedProject("audit-argspath-v2", "s-red")
+    const { ctx, toolHooks } = makeV2Ctx(root2)
+    await auditV2def.value.setup(ctx)
+    let b1 = null
+    try {
+      await toolHooks.before[0]({ tool: "write", sessionID: "s-red", agent: "a", messageID: "m1", id: "at3", input: { path: path.join(root2, "tests", "verification_log.md"), content: "x" } })
+    } catch (e) {
+      b1 = e
+    }
+    let b2 = null
+    try {
+      await toolHooks.before[0]({ tool: "write", sessionID: "s-red", agent: "a", messageID: "m1", id: "at4", input: { path: path.join(root2, "src", "y.js"), content: "x" } })
+    } catch (e) {
+      b2 = e
+    }
+    rec("D12c-audit-v2: args.path shape — tests/ writable, src still BLOCKS", !b1 && !!b2, `tests=${b1 ? "blocked" : "clean"} src=${b2 ? "blocked" : "clean"}`)
+  }
+}
+
 console.log(`\n=== COMPAT HARNESS: ${count - failures}/${count} passed, ${failures} failed ===`)
-const allowKnown = process.argv.includes("--allow-known")
-const known = ["E3-audit-v1:", "G9-loopguard-v1:"]
-const onlyKnown = failedNames.every((n) => known.some((k) => n.startsWith(k)))
-process.exit(failures ? (allowKnown && onlyKnown ? 0 : 1) : 0)
\ No newline at end of file
+// W18 D-W18-2: the known-failure quarantine (--allow-known / E3/G9) is
+// REMOVED — both regressions are fixed in this wave, and a permanently
+// quarantined failure is exactly the blind spot the quarantine created.
+process.exit(failures ? 1 : 0)
\ No newline at end of file
diff --git a/tests/test_check_doc_counts.py b/tests/test_check_doc_counts.py
new file mode 100644
index 0000000..62c773e
--- /dev/null
+++ b/tests/test_check_doc_counts.py
@@ -0,0 +1,127 @@
+#!/usr/bin/env python3
+"""Checks for check_doc_counts.py (W18 release-hygiene fix, 2026-10-22).
+
+The W18 audit found README/CHANGELOG counts that no in-tree run could
+reproduce (F1/F6). These checks prove the binder (a) reads both languages'
+claim shapes, (b) ignores historical prose counts, (c) FAILS on a mismatch
+(the falsifiable anchor: 70/71 vs 82/82), and (d) bans the CI quarantine flag.
+"""
+import importlib.util
+import pathlib
+import re
+
+ROOT = pathlib.Path(__file__).resolve().parent.parent
+spec = importlib.util.spec_from_file_location(
+    "check_doc_counts", ROOT / "check_doc_counts.py")
+cdc = importlib.util.module_from_spec(spec)
+spec.loader.exec_module(cdc)
+
+RESULTS = []
+
+
+def rec(name, ok, detail=""):
+    RESULTS.append((name, ok, detail))
+    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
+
+
+EN = """\
+node vibeweaver/scripts/audit_selftest.mjs  # 571 fixture checks (T6 skips)
+node vibeweaver/scripts/mutation_sweep.mjs  # 44 mutations, each must be caught
+node tests/plugin_compat_test.mjs           # 82/82 dual loader compat
+node tests/mini_gate_test.mjs               # 62/62 mini checker gate: idle + installers
+| `scripts/audit_selftest.mjs` / `scripts/mutation_sweep.mjs` | 571 fixture checks / 44 mutation checks |
+"""
+
+ZH = """\
+node vibeweaver/scripts/audit_selftest.mjs  # 571 项 fixture 检查（无校准数据时 T6 SKIP）
+node vibeweaver/scripts/mutation_sweep.mjs  # 44 项变异，每项都必须被抓到
+node tests/plugin_compat_test.mjs           # 82/82 双 loader 兼容
+node tests/mini_gate_test.mjs               # 62/62 mini checker gate：v1/v2 write
+| `scripts/audit_selftest.mjs` / `mutation_sweep.mjs` | 571 项 fixture 检查 / 44 项变异检查 |
+"""
+
+HISTORY = """\
+- **第十三波：按比例验证。** 证据是 166 条 fixture 断言、41 项变异、两轮对抗评审。
+qwen3.6 上 mini 赢；44% 抬到 81%。
+"""
+
+SELFTEST_RUN = "=== SUMMARY ===\nfixture checks: 571, failures: 0, skipped: 1\n"
+MUTATION_RUN = "=== MUTATION SWEEP: 44 passed, 0 failed ===\n"
+COMPAT_RUN = "=== COMPAT HARNESS: 82/82 passed, 0 failed ===\n"
+MINI_RUN = "RESULT: 62/62 passed, 0 failed\n"
+
+
+def main():
+    en = cdc.extract_claims(EN)
+    rec("CDC1 EN claim shapes extracted",
+        en.get("selftest") == [571] and en.get("mutation") == [44]
+        and en.get("compat") == [(82, 82)] and en.get("mini") == [(62, 62)],
+        str(en))
+
+    zh = cdc.extract_claims(ZH)
+    rec("CDC2 ZH claim shapes extracted (same values)",
+        zh == en, str(zh))
+
+    hist = cdc.extract_claims(HISTORY)
+    rec("CDC3 historical prose counts are not claims (no command anchor)",
+        not hist, str(hist))
+
+    runs = {
+        "selftest": cdc.parse_run("selftest", SELFTEST_RUN),
+        "mutation": cdc.parse_run("mutation", MUTATION_RUN),
+        "compat": cdc.parse_run("compat", COMPAT_RUN),
+        "mini": cdc.parse_run("mini", MINI_RUN),
+    }
+    rec("CDC4 run parsers read SUMMARY lines",
+        runs["selftest"] == (571, 0) and runs["mutation"] == (44, 0)
+        and runs["compat"] == (82, 82, 0) and runs["mini"] == (62, 62, 0),
+        str(runs))
+
+    rec("CDC5 matching claims pass silently", cdc.compare_counts(runs, en) == [],
+        str(cdc.compare_counts(runs, en)))
+
+    stale = dict(en)
+    stale["compat"] = [(70, 71)]
+    errs = cdc.compare_counts(runs, stale)
+    rec("CDC6 mismatched claim FAILS (falsifiable anchor: 70/71 vs 82/82)",
+        any("compat" in e and "70/71" in e for e in errs), str(errs)[:160])
+
+    missing = {"selftest": [571], "mutation": [44], "compat": [(82, 82)]}
+    errs = cdc.compare_counts(runs, missing)
+    rec("CDC7 suite with no claim is a named error", any("mini" in e for e in errs),
+        str(errs)[:160])
+
+    red = dict(en)
+    red["compat"] = [(82, 82, 1)]
+    runs_red = dict(runs)
+    runs_red["compat"] = (82, 82, 1)
+    errs = cdc.compare_counts(runs_red, red)
+    rec("CDC8 a red suite cannot bind claims (failures must be 0)",
+        any("red" in e or "failed" in e for e in errs), str(errs)[:160])
+
+    rec("CDC9 quarantine ban flags --allow-known in CI/harness",
+        cdc.scan_quarantine_text("run: node tests/plugin_compat_test.mjs --allow-known\n")
+        and not cdc.scan_quarantine_text("run: node tests/plugin_compat_test.mjs\n"),
+        "")
+
+    rec("CDC10 historical comment documenting removal is not quarantine",
+        not cdc.scan_quarantine_text(
+            "// W18 D-W18-2: the known-failure quarantine (--allow-known / E3/G9) is\n"
+            "// REMOVED\n")
+        and cdc.scan_quarantine_text(
+            "const allowKnown = process.argv.includes(\"--allow-known\")\n"),
+        "")
+
+    fails = [n for n, ok, _ in RESULTS if not ok]
+    print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
+          (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
+    return 1 if fails else 0
+
+
+def test_check_doc_counts_vectors():
+    assert main() == 0
+
+
+if __name__ == "__main__":
+    import sys
+    sys.exit(main())

## REPO diff -U10 (docs)
diff --git a/CHANGELOG.md b/CHANGELOG.md
index a89f76d..a00eb4c 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,14 +1,22 @@
 # Changelog
 
 Waves of design history, newest first. Entries are moved verbatim from the README; the current state of the project is described in [README.md](README.md).
 
+## 2026-10-22: Release hygiene — claims bound to runs, evidence travels with the release
+
+**The gap.** An external audit of the published tree (2026-10-22, `docs/AUDIT_20261022_w18_release_claims.md` in the dev tree) found the W18 changelog claiming `plugin compat 82/82 (E3/G9 fixed — quarantine removed)` while the tree it was published in ran a pre-W18 71-case harness whose E3 assertion encoded the CLOSED subagent bypass as its expectation ("a foreign write auto-releases the latch") — `node tests/plugin_compat_test.mjs` gave 70/71, CI laundered the live failure through `--allow-known`, README said a third thing (70/71, E3 known), and the W18 evidence logs lived only in the dev tree.
+
+**The mechanism.** The compat harness (82 cases, E3 re-anchored to the D3 spec + E3b latch-survival) is synchronized into this tree — `tests/sync_skill.py` now byte-pins it and the `tests/w18`/`tests/w18sync` evidence dirs, so a stale copy or evidence stranded in the dev tree fails closed. CI runs without any quarantine flag, and a new `check_doc_counts.py` step binds every README count to a real suite run (a red run binds nothing; a mismatched claim fails CI). The W18 evidence and its archived verification log are committed here with the claims they support, and releases carry tags from `w18` on.
+
+**Verification.** plugin compat 82/82 on THIS tree, exit 0, no quarantine code path · audit_selftest 571/0 (1 skipped) · mutation_sweep 44/0 · mini gate 62/62 · unittest 56 OK · verify_skill 10 OK · `check_doc_counts.py` 10/10 vectors + real-tree binding green · `tests/test_sync_skill.py` 15/15 (SS9-SS15 pin stale-harness and evidence drift, missing/extra/DRIFT all fail-closed) · dual adversarial fresh-context review.
+
 ## 2026-10-21: W18 residual closures — the ratchet spans history, acks bind to claims
 
 **The gap.** Two sharp edges survived the batch-2/3 review: a hand-RAISED debt baseline could be COMMITTED and then passed (the check only compared against HEAD, and a 50-revision churn window could evict the low anchor), and a `- claim-ack:` line ref could drift onto a different claim and silently license it.
 
 **The mechanism.** The debt ratchet's min now spans the baseline path's committed revisions (newest 50 + the first-ever adoption anchor) — raises in the worktree OR in history fail, and churn commits launder nothing. Claim acks now carry the quoted claim (`- claim-ack: line N "<quoted claim>" — <reason>`); the quote binds the suppression to the claim's content, and drifted/fenced/misquoted acks suppress nothing and are flagged `stale claim-ack`.
 
 **Verification.** assert group fixtures 75/75 (S67 raise+commit · S69 quote-mismatch retarget · S70 55-commit churn window all pin the closures) · audit_selftest 571/0 · mutation_sweep 44/0 · plugin compat 82/82 · `--existing --final` 29/29 · scoped adversarial review (R1b/R2 closed) · four copies + eval pins repinned.
 
 ## 2026-10-21: W18 batch 2/3 — debt ratchet, claim-lint discipline, validated wave anchors, output-order unification
 
diff --git a/CHANGELOG_zh.md b/CHANGELOG_zh.md
index fa79ef6..46c9c7c 100644
--- a/CHANGELOG_zh.md
+++ b/CHANGELOG_zh.md
@@ -1,14 +1,22 @@
 # 变更记录
 
 设计演变史，新的在前。条目从 README 原样迁移；项目当前状态见 [README_zh.md](README_zh.md)。
 
+## 2026-10-22：发布卫生 — 宣称绑定实跑，证据随发布同行
+
+**缺口。** 2026-10-22 对发布树的外部审计（dev 树 `docs/AUDIT_20261022_w18_release_claims.md`）发现：W18 变更记录宣称 `plugin compat 82/82（E3/G9 已修 — 豁免已删）`，而它所发布的那棵树跑的是 W18 之前的 71 例旧 harness——其 E3 断言把**已封堵**的 subagent 旁路当期望值（「外会话写自动放闩」），实跑 70/71，CI 用 `--allow-known` 把活失败洗绿，README 又是第三种口径（70/71，E3 已知），W18 证据日志只留在 dev 树。
+
+**机制。** 兼容 harness（82 例，E3 按 D3 规格重定 + E3b 存活断言）同步进本树——`tests/sync_skill.py` 现在字节钉住它与 `tests/w18`、`tests/w18sync` 证据目录，副本过期或证据滞留 dev 树一律 fail-closed。CI 不再有任何豁免开关，并新增 `check_doc_counts.py` 步骤把 README 的每个计数绑定到真实套件实跑（红跑不绑定；宣称不符即 CI 失败）。W18 证据与其验证日志归档随宣称同提交入库，发布从 `w18` 起带 tag。
+
+**验证。** 本树 plugin compat 82/82、exit 0、无豁免代码路径 · audit_selftest 571/0（1 skip）· mutation_sweep 44/0 · mini gate 62/62 · unittest 56 OK · verify_skill 10 OK · `check_doc_counts.py` 10/10 向量 + 真实树绑定绿 · `tests/test_sync_skill.py` 15/15（SS9-SS15 钉住 harness 过期与证据漂移，missing/extra/DRIFT 全 fail-closed）· 双对抗全新上下文复审。
+
 ## 2026-10-21：W18 残余销项 — 棘轮跨历史、ack 绑定声明
 
 **缺口。** 批 2/3 复审后仍余两处：提交级抬高债基线后可通过（只对 HEAD 比较，且 50 修订 churn 窗口可驱逐低锚）；`- claim-ack:` 行号漂移后会静默改挂到别的声明行。
 
 **机制。** 债棘轮的 min 改为横跨该路径的全部提交修订（最新 50 + 首次采纳锚）——工作树或历史中的抬高一律 FAIL，churn 提交洗不掉。claim-ack 强制携带引文（`- claim-ack: line N "<quoted claim>" — <reason>`）绑定声明内容，漂移/fence/引文不符的 ack 一律不抑制并标 `stale claim-ack`。
 
 **验证。** assert 组 75/75（S67 提交级抬高 · S69 引文改挂 · S70 55 次 churn 窗口三用例钉住）· audit_selftest 571/0 · sweep 44/0 · compat 82/82 · `--existing --final` 29/29 · scoped 对抗复审（R1b/R2 闭合）· 四副本 + eval pins 重钉。
 
 ## 2026-10-21：W18 第 2/3 批 — 债棘轮、claim-lint 纪律、锚点校验、输出顺序唯一化
 
diff --git a/README.md b/README.md
index 81bd940..0948a24 100644
--- a/README.md
+++ b/README.md
@@ -851,21 +851,21 @@ welcome.
 | `scripts/audit_selftest.mjs` / `scripts/mutation_sweep.mjs` | 571 fixture checks (T24 loop-guard, T25 task-class, T26 final-run, T27 stop-guard, T29–T33 latch-release, T34–T35 tool-storm, T36–T39 self-lock/lock-escape/scope/source-hygiene suites) / 44 mutation checks, including the latch-release regressions                                                      |
 | `install.sh` / `install.bat`                                | Installers (skill files + both plugins)                                                                                                                                        |
 
 ## Testing
 
 ```bash
 python3 verify_skill.py                     # package integrity: payload, links, markers, syntax
 python3 -m unittest discover -s tests -v    # skill self-tests + checker regression tests
 node vibeweaver/scripts/audit_selftest.mjs  # 571 fixture checks (T6 skips without calibration data)
 node vibeweaver/scripts/mutation_sweep.mjs  # 44 mutations, each must be caught
-node tests/plugin_compat_test.mjs           # 70/71 dual loader compat (E3 known)
+node tests/plugin_compat_test.mjs           # 82/82 dual loader compat (no quarantine)
 node tests/mini_gate_test.mjs               # 62/62 mini checker gate: v1/v2 write + idle + installers
 ```
 
 CI runs the Python checks and the node harnesses on Ubuntu / macOS / Windows
 (`.github/workflows/verify.yml`).
 
 ## Contributing
 
 Issues and PRs are welcome, especially ports to other agents (Claude Code, Codex,
 …). If you adapt the skill to another agent, open an issue and link it so it can be
diff --git a/README_zh.md b/README_zh.md
index d888283..b77cc74 100644
--- a/README_zh.md
+++ b/README_zh.md
@@ -357,21 +357,21 @@ vibeweaver 与技术栈无关，从不假设语言、框架或数据库：
 
 ## 测试
 
 本仓库用 skill 要求别人项目的方式检查自己：
 
 ```bash
 python3 verify_skill.py                     # 包完整性：payload、链接、标记、语法
 python3 -m unittest discover -s tests -v    # 技能自测 + checker 回归测试
 node vibeweaver/scripts/audit_selftest.mjs  # 571 项 fixture 检查（无校准数据时 T6 SKIP）
 node vibeweaver/scripts/mutation_sweep.mjs  # 44 项变异，每项都必须被抓到
-node tests/plugin_compat_test.mjs           # 70/71 双 loader 兼容（E3 已知）
+node tests/plugin_compat_test.mjs           # 82/82 双 loader 兼容（无豁免）
 node tests/mini_gate_test.mjs               # 62/62 mini checker gate：v1/v2 write + idle + 安装器
 ```
 
 CI 在 Ubuntu / macOS / Windows 上跑这些（`.github/workflows/verify.yml`）。
 
 ## 贡献
 
 欢迎 issue 和 PR，尤其是移植到其他 agent（Claude Code、Codex 等）。适配后开个 issue 附链接，会列进本 README。
 
 工作流图是生成的，不是手画的：改 `docs/assets/*.mmd`，再用 `mmdc -i <名字>.mmd -o <名字>.svg -b white` 重新渲染，两个文件一起提交。
