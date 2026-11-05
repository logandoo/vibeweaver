#!/usr/bin/env python3
"""evidence_seal.py — the ONLY writer of tests/evidence_manifest.json and
tests/test_baseline.json (BL-12/BL-13, PLAN C3/C3b, 2026-10-15).

The seal binds what the log CLAIMS as evidence to content hashes, and binds
the test suite to a hash baseline:
  tests/evidence_manifest.json — {files: {rel: {sha256,size}}, code_fingerprint}
  tests/test_baseline.json     — {rel: sha256} for every test-code file

Design rules (blind-spot dispositions):
  * The manifest is written HERE, never by hand — assert_artifacts group 15b
    fails on hash mismatch (tamper) and on a stale code_fingerprint (evidence
    generated BEFORE later code changes — the "先造证据后改代码" case).
  * The test baseline updates ONLY when the change is licensed by a
    `- test-change: <path> — <reason>` line in tests/verification_log.md.
    Deleting the baseline is NOT a silent rebuild path (BL-13): this script
    recreates it only through the same licensing.

Usage:
  python3 scripts/evidence_seal.py            # seal (run from the project root)
  python3 scripts/evidence_seal.py --check    # verify an existing seal (no write)
  python3 scripts/evidence_seal.py --run-context PATH [--sha-map PATH]
Exit 0 = sealed/verified. Exit 1 = refused (a test change lacks its reason).

W25 multi-agent (PLAN Task 6, §MA6): the manifest carries the Consistency
Hub Evidence Manifest field set (missing values default to null — old
manifests still verify/read cleanly). With `--run-context PATH` (RunContext
JSON, schema vibeweaver-run-context/1) the identity/SHA fields and verifier
versions are populated; `--sha-map PATH` ({queue_id, candidate_sha,
final_commit_sha, final_tree_sha}) adds the integration SHA mapping.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

MEDIA_RE = re.compile(r"tests/(\S+\.(?:png|webm|wav|mp4|mp3))")
TRACE_RE = re.compile(r"tests/(workflows/\S+?\.trace\.log)")
# G5 (W18): non-web evidence (CLI/library task logs, bench reports, captured
# JSON) is bound too — the seal's tamper promise must not be web-only. Cited
# `tests/**/*.log|json|md` join the manifest under the cli/library profile
# (SLSA/in-toto: a subject digest binds ANY artifact type).
EVIDENCE_RE = re.compile(r"tests/(\S+\.(?:log|json|md))")
TEST_CHANGE_RE = re.compile(r"(\S+\.(?:py|js|mjs|ts|tsx|jsx|go|rs))")
# W25 Consistency Hub — Evidence Manifest field names (character-for-character;
# missing values default to null; old manifests without them still verify)
HUB_MANIFEST_FIELDS = (
    "repo_id", "task_id", "run_id", "attempt_id", "wave_id",
    "integration_run_id", "spec_hash", "acceptance_hash", "base_sha",
    "original_head_sha", "resolved_head_sha", "candidate_sha",
    "final_commit_sha", "tree_sha", "final_tree_sha", "dep_lock_digest",
    "env_digest", "skill_digest", "plugin_digest", "checker_digest",
    "config_digest", "hook_digest", "test_commands", "results",
    "review_records", "artifact_hashes", "archive_locations", "outbox_status",
)
RUN_CONTEXT_SCHEMA = "vibeweaver-run-context/1"
# Hub id grammar (shared with run_control.py): a forged/garbage id is refused
RUN_ID_RE = re.compile(r"^run-[0-9a-f]{32}$")
ATTEMPT_ID_RE = re.compile(r"^attempt-[0-9a-f]{32}$")
WAVE_ID_RE = re.compile(r"^wave-[0-9a-f]{32}$")
# code fingerprint inputs — SHARED CONTRACT with scripts/assert_artifacts.py
# (identical ext set AND identical file-set derivation; review R-I2 found the
# divergence red-locked group 15b after a clean seal).
FINGERPRINT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".go", ".rs",
                 ".java", ".sql", ".c", ".cc", ".cpp", ".h", ".hpp", ".kt",
                 ".swift", ".php", ".rb", ".cs", ".sh", ".bash", ".bat",
                 ".ps1", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg",
                 ".conf", ".tf", ".tfvars", ".xml", ".css", ".scss", ".sass",
                 ".less"}
TEST_BASENAMES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg",
                  "jest.config.js", "jest.config.ts", "vitest.config.ts",
                  "vitest.config.js"}


def _unquote_git(p: str) -> str:
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
                out.append(simple[nxt]); i += 2; continue
            if nxt in "01234567" and i + 3 < n and all(c in "01234567" for c in body[i + 2:i + 4]):
                out.append(int(body[i + 1:i + 4], 8)); i += 4; continue
            out.append(ord(nxt)); i += 2; continue
        out.extend(ch.encode("utf-8"))
        i += 1
    return out.decode("utf-8", "replace")


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_test_code(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    base = os.path.basename(rel)
    if "assert_artifacts.py" in base:
        return False
    if base in TEST_BASENAMES:
        return True
    ext = os.path.splitext(base)[1].lower()
    if ext not in {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"}:
        return False
    segs = rel.split("/")
    return any(s.lower() in ("test", "tests", "__tests__", "spec") for s in segs[:-1]) or \
        base.startswith("test_") or base.endswith(("_test.py", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))


def _git(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20)
        return r.returncode, r.stdout
    except Exception:
        return -1, ""


def wave_code_files(root):
    """Wave-changed source files (backup anchor..HEAD + uncommitted +
    untracked) — the code whose later change invalidates sealed evidence.
    SHARED CONTRACT: identical derivation in scripts/assert_artifacts.py."""
    rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
                   "--grep=backup: before changes")
    paths = set()
    if rc == 0 and sha.strip():
        _, out = _git(root, "diff", "--name-only", f"{sha.strip()}..HEAD")
        paths.update(l.strip() for l in out.splitlines() if l.strip())
    _, out = _git(root, "diff", "--name-only", "HEAD")
    paths.update(l.strip() for l in out.splitlines() if l.strip())
    _, out = _git(root, "ls-files", "--others", "--exclude-standard")
    paths.update(_unquote_git(l.strip()) for l in out.splitlines() if l.strip())
    return sorted(
        p for r in paths for p in [_unquote_git(r)]
        if os.path.splitext(p)[1].lower() in FINGERPRINT_EXT
        and "assert_artifacts.py" not in p
        and "evidence_seal.py" not in p
        and not p.startswith("tests/")
    )


def code_fingerprint(root):
    """stable digest of wave code content — shared contract with
    assert_artifacts.py (keep the two spellings identical)."""
    parts = []
    for rel in wave_code_files(root):
        p = pathlib.Path(root) / rel
        parts.append(f"{rel}:{sha256_file(p) if p.is_file() else 'gone'}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_files(root):
    out = {}
    rc, listing = _git(root, "ls-files")
    candidates = [l.strip() for l in listing.splitlines() if l.strip()] if rc == 0 else []
    _, untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    candidates += [l.strip() for l in untracked.splitlines() if l.strip()]
    for rel in candidates:
        if is_test_code(rel) and (pathlib.Path(root) / rel).is_file():
            out[rel] = sha256_file(pathlib.Path(root) / rel)
    return out


def _load_run_context(path):
    """RunContext JSON (schema vibeweaver-run-context/1) -> identity dict.
    Raises ValueError on a missing/unparseable/forged context (fail-closed:
    a manifest must never record identity the context cannot prove)."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"run context {path} missing/unparseable ({e})")
    if not isinstance(data, dict) or data.get("schema") != RUN_CONTEXT_SCHEMA:
        raise ValueError(f"run context {path}: schema must be {RUN_CONTEXT_SCHEMA!r} "
                         f"(forged/legacy context rejected, §MA1)")
    for key in ("repo_id", "task_id", "run_id", "attempt_id", "wave_id",
                "base_sha", "spec_hash", "skill_version", "checker_digest"):
        if not str(data.get(key, "")):
            raise ValueError(f"run context {path}: field `{key}` missing")
    # Fail closed on garbage identity: the Hub id grammar and lease_epoch >= 1
    # must hold before any identity lands in a manifest.
    for key, rx in (("run_id", RUN_ID_RE), ("attempt_id", ATTEMPT_ID_RE),
                    ("wave_id", WAVE_ID_RE)):
        if rx.match(str(data.get(key, ""))) is None:
            raise ValueError(f"run context {path}: field `{key}` has bad id "
                             f"format: {data.get(key)!r}")
    epoch = data.get("lease_epoch")
    if type(epoch) is not int or epoch < 1:
        raise ValueError(f"run context {path}: field `lease_epoch` must be an "
                         f"int >= 1 (got {epoch!r})")
    return data


def _load_sha_map(path):
    """integration SHA map ({queue_id, candidate_sha, final_commit_sha,
    final_tree_sha} — integrate.py record_sha_map shape)."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"sha map {path} missing/unparseable ({e})")
    if not isinstance(data, dict):
        raise ValueError(f"sha map {path}: must be a JSON object")
    for key in ("queue_id", "candidate_sha", "final_commit_sha", "final_tree_sha"):
        if not isinstance(data.get(key), str) or not data.get(key):
            raise ValueError(f"sha map {path}: field `{key}` missing")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the existing seal without writing")
    ap.add_argument("--run-context", default="",
                    help="W25: RunContext JSON (schema vibeweaver-run-context/1) — "
                         "populate the manifest identity/SHA + verifier-version fields")
    ap.add_argument("--sha-map", default="",
                    help="W25: integration SHA map JSON {queue_id, candidate_sha, "
                         "final_commit_sha, final_tree_sha} (integrate.py record_sha_map)")
    args = ap.parse_args()
    root = pathlib.Path(".").resolve()
    run = None
    sha_map = None
    try:
        if args.run_context:
            run = _load_run_context(args.run_context)
        if args.sha_map:
            sha_map = _load_sha_map(args.sha_map)
        if sha_map and run is None:
            raise ValueError("--sha-map requires --run-context (the SHA map is "
                             "bound to a run's identity, §MA6)")
    except ValueError as e:
        print(f"evidence_seal.py: REFUSED — {e}")
        return 1
    tests = root / "tests"
    log = (tests / "verification_log.md").read_text(errors="replace") if (tests / "verification_log.md").exists() else ""
    acc = (tests / "acceptance.md").read_text(errors="replace") if (tests / "acceptance.md").exists() else ""

    # regex groups capture the path AFTER `tests/` — keys are always
    # repo-relative `tests/...` (assert group 15b resolves them from root)
    _prof = {}
    _pf = tests / "project_profile.json"
    if _pf.exists():
        try:
            _prof = json.loads(_pf.read_text(errors="replace")) or {}
        except Exception:
            _prof = {}
    _prof_name = str(_prof.get("profile") or _prof.get("kind") or "")
    cited = sorted(set("tests/" + r for r in MEDIA_RE.findall(log + "\n" + acc)) |
                   set("tests/" + r for r in TRACE_RE.findall(log + "\n" + acc)))
    if _prof_name in ("cli", "library"):
        cited = sorted(set(cited) |
                       set("tests/" + r for r in EVIDENCE_RE.findall(log + "\n" + acc)))
    # self-referential subjects are NEVER bound (review A): the log/acceptance
    # and the seal's own files are mutated BY the workflow (the mandated
    # post-assert log append, the new-task acceptance rewrite, re-sealing) —
    # binding them creates a tamper trap that can never converge.
    SELF_REFS = {"tests/verification_log.md", "tests/acceptance.md",
                 "tests/evidence_manifest.json", "tests/test_baseline.json",
                 "tests/debt_baseline.json", "tests/working_note.md"}
    cited = [c for c in cited if c not in SELF_REFS]
    files = {}
    for rel in cited:
        p = root / rel
        if p.is_file() and p.stat().st_size > 0:
            files[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size}

    manifest = {"version": 1, "files": files, "code_fingerprint": code_fingerprint(root)}
    # W25 Hub Evidence Manifest: every field present, missing values default
    # to null (old manifests without them still verify — --check below only
    # compares files/code_fingerprint). `skill_version` is ADDITIVE: the
    # 28-field Hub list keeps its names.
    for _f in HUB_MANIFEST_FIELDS:
        manifest[_f] = None
    manifest["skill_version"] = None
    if run:
        manifest["repo_id"] = run.get("repo_id")
        manifest["task_id"] = run.get("task_id")
        manifest["run_id"] = run.get("run_id")
        manifest["attempt_id"] = run.get("attempt_id")
        manifest["wave_id"] = run.get("wave_id")
        manifest["spec_hash"] = run.get("spec_hash")
        manifest["base_sha"] = run.get("base_sha")
        # verifier versions pinned at evidence time (§MA6 immutability):
        # skill_digest is a REAL digest of the version string ('sha256:'
        # prefix), and the raw value lives in the additive `skill_version`
        # field — it never silently carries the raw string.
        manifest["skill_version"] = run.get("skill_version")
        manifest["skill_digest"] = "sha256:" + hashlib.sha256(
            str(run.get("skill_version")).encode("utf-8")).hexdigest()
        manifest["checker_digest"] = run.get("checker_digest")
        manifest["archive_locations"] = [str(run.get("artifact_root") or ""),
                                         str(run.get("state_root") or "")]
    if sha_map:
        manifest["integration_run_id"] = sha_map.get("queue_id")
        manifest["candidate_sha"] = sha_map.get("candidate_sha")
        manifest["final_commit_sha"] = sha_map.get("final_commit_sha")
        manifest["final_tree_sha"] = sha_map.get("final_tree_sha")
    baseline_new = test_files(root)
    baseline_p = tests / "test_baseline.json"
    baseline_old = {}
    if baseline_p.exists():
        try:
            baseline_old = json.loads(baseline_p.read_text())
        except Exception:
            baseline_old = {}

    # license scoping (review R-I2 pair): only the CURRENT task block's
    # `- test-change:` lines license — an old block's reason must not cover a
    # later wave's test change.
    cur_block = re.split(r"(?m)^(?=## )", log)[-1] if log else ""
    # every path token in a `- test-change:` line is licensed (one line may
    # name several files); lines are anchored so stray mentions don't license
    reasons = set()
    for _l in cur_block.splitlines():
        if _l.lstrip().startswith("- test-change:"):
            reasons.update(m.group(1) for m in TEST_CHANGE_RE.finditer(_l))
    problems = []
    for rel, digest in sorted(baseline_new.items()):
        old = baseline_old.get(rel)
        if old is not None and old != digest and rel not in reasons:
            problems.append(f"test file {rel} changed since the sealed baseline and no `- test-change: {rel} — <reason>` line licenses it")
    for rel in sorted(set(baseline_old) - set(baseline_new)):
        if rel not in reasons:
            problems.append(f"test file {rel} was REMOVED since the sealed baseline and no `- test-change: {rel} — <reason>` line licenses it")
    if baseline_old == {} and baseline_new and not args.check:
        # BL-13 (review R-C1): deleting the baseline is NOT a re-baseline
        # path. Creating it for test files that are IN THE WAVE (changed or
        # untracked) needs their `- test-change:` reasons — the same license a
        # baseline UPDATE needs. A truly fresh suite (no test-code in the
        # wave) seals freely.
        wave_touch = set()
        rc, sha = _git(root, "log", "--format=%H", "-1", "--fixed-strings",
                       "--grep=backup: before changes")
        if rc == 0 and sha.strip():
            _, out = _git(root, "diff", "--name-only", f"{sha.strip()}..HEAD")
            wave_touch.update(l.strip() for l in out.splitlines() if l.strip())
        _, out = _git(root, "diff", "--name-only", "HEAD")
        wave_touch.update(l.strip() for l in out.splitlines() if l.strip())
        _, out = _git(root, "ls-files", "--others", "--exclude-standard")
        wave_touch.update(l.strip() for l in out.splitlines() if l.strip())
        for rel in sorted(baseline_new):
            if rel in wave_touch and rel not in reasons:
                problems.append(
                    f"test file {rel} is NEW/changed in the wave with no `- test-change: {rel} — <reason>` "
                    f"line — creating a baseline around an unlicensed test change is a silent rebuild (C3b/BL-13)")

    if problems:
        print("evidence_seal.py: REFUSED — test changes need their reasons (C3b/BL-13):")
        for pr in problems:
            print("  - " + pr)
        return 1

    if args.check:
        man_p = tests / "evidence_manifest.json"
        if not man_p.exists():
            print("evidence_seal.py: no manifest to check")
            return 1
        try:
            man = json.loads(man_p.read_text())
        except Exception:
            print("evidence_seal.py: manifest unreadable")
            return 1
        ok = man.get("code_fingerprint") == manifest["code_fingerprint"] and man.get("files") == files
        print("evidence_seal.py: " + ("seal VERIFIED" if ok else "seal STALE or TAMPERED — re-run tests + re-seal"))
        return 0 if ok else 1

    tmp_m = str(tests / "evidence_manifest.json") + ".tmp"
    with open(tmp_m, "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    os.replace(tmp_m, tests / "evidence_manifest.json")
    tmp_b = str(baseline_p) + ".tmp"
    with open(tmp_b, "w") as fh:
        json.dump(baseline_new, fh, indent=1, sort_keys=True)
    os.replace(tmp_b, baseline_p)
    print(f"evidence_seal.py: sealed {len(files)} evidence file(s), "
          f"test baseline {len(baseline_new)} file(s), code fingerprint recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
