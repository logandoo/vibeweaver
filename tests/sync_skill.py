#!/usr/bin/env python3
"""sync_skill.py — fail-closed consistency check for vibeweaver shared scripts.

The dev tree is the source of truth. This checker compares every published
copy + the eval task pins (W9 P0-3):

  assert_artifacts.py:
    scripts/assert_artifacts.py (canonical)
    tests/assert_artifacts.py (project copy)
    <installed>/scripts/assert_artifacts.py
    <eval>/configs/fn_latest/opencode/skills/vibeweaver/scripts/assert_artifacts.py
    <eval>/suite/tasks/compliance_{pricing_tier,refund_flow,password_reset}/canonical/assert_artifacts.py
    each task.json > compliance.canonical_assert_sha

  scan_secrets.py:
    scripts/scan_secrets.py (canonical)
    <installed>/scripts/scan_secrets.py
    <eval>/configs/fn_latest/opencode/skills/vibeweaver/scripts/scan_secrets.py

Usage:
  python3 tests/sync_skill.py                 # verify (exit 1 on any drift)
  python3 tests/sync_skill.py --fix           # copy canonical bytes + repin
  python3 tests/sync_skill.py --allow-missing-eval
  python3 tests/sync_skill.py --allow-missing-installed

Exit 0 = every copy and pin agrees. Exit 1 = drift/missing copy/pin.
This script is dev-only; it is not part of the skill payload.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parent.parent
INSTALLED = Path(os.environ.get(
    "VIBEWEAVER_INSTALLED_SKILL",
    Path.home() / ".config" / "opencode" / "skills" / "vibeweaver"))
EVAL = Path(os.environ.get("VIBEWEAVER_EVAL_DIR", DEV.parent / "vibeweaver-eval"))
REPO = Path(os.environ.get("VIBEWEAVER_REPO_DIR", DEV.parent / "vibeweaver-repo"))
TASKS = ("compliance_pricing_tier", "compliance_refund_flow", "compliance_password_reset")
# W18 release-hygiene fix (2026-10-22, audit F4/F5): evidence dirs that MUST
# travel with a release — the published repo tree carries byte-identical copies.
EVIDENCE_DIRS = ("w18", "w18sync")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def eval_assert_copies(eval_dir: Path):
    return [
        ("eval snapshot", eval_dir / "configs" / "fn_latest" / "opencode" / "skills"
         / "vibeweaver" / "scripts" / "assert_artifacts.py"),
        *[(f"task {t}", eval_dir / "suite" / "tasks" / t / "canonical" / "assert_artifacts.py")
          for t in TASKS],
    ]


def eval_scan_copies(eval_dir: Path):
    return [
        ("eval snapshot", eval_dir / "configs" / "fn_latest" / "opencode" / "skills"
         / "vibeweaver" / "scripts" / "scan_secrets.py"),
    ]


def copy_plan(dev: Path, installed: Path, eval_dir: Path, repo: Path = None):
    """[(label, canonical, [copies])] — every copy a published duplicate.

    `repo=None` means "no repo target" (library callers/tests assemble their
    own target set); main() always passes the real REPO tree."""
    plan = [
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
    # W18 fix: the compat harness ships next to the payload in the repo
    # tree — a stale copy there re-opens quarantined failures (audit F1/F3).
    # The sync tooling ships too so the repo tree can reproduce the checks its
    # changelog cites (review I3 — claims never outlive their reproducer).
    if repo is not None:
        plan.append(("plugin_compat_test.mjs", dev / "tests" / "plugin_compat_test.mjs", [
            ("repo", repo / "tests" / "plugin_compat_test.mjs"),
        ]))
        plan.append(("sync_skill.py", dev / "tests" / "sync_skill.py", [
            ("repo", repo / "tests" / "sync_skill.py"),
        ]))
        plan.append(("test_sync_skill.py", dev / "tests" / "test_sync_skill.py", [
            ("repo", repo / "tests" / "test_sync_skill.py"),
        ]))
        # W0 Task 2/2.5/4: these ship with the payload and are covered by the
        # release manifest; a stale repo copy re-opens the three-line checker
        # hole or leaves bootstrap/evidence-lock out of the install.
        for rel in ("assert_artifacts.sha256", "evidence_lock.py", "repair_checker.sh", "state_sanitize.py"):
            plan.append((rel, dev / "scripts" / rel, [
                ("installed", installed / "scripts" / rel),
                ("repo", repo / "vibeweaver" / "scripts" / rel),
            ]))
        plan.append(("bootstrap.md", dev / "bootstrap.md", [
            ("installed", installed / "bootstrap.md"),
            ("repo", repo / "vibeweaver" / "bootstrap.md"),
        ]))
        plan.append(("contract_lint.py", dev / "scripts" / "contract_lint.py", [
            ("repo", repo / "vibeweaver" / "scripts" / "contract_lint.py"),
        ]))
    return plan


def evidence_parity(dev: Path, repo: Path):
    """File-set + hash parity for EVIDENCE_DIRS (dev/tests/<d> ↔ repo/tests/<d>).

    Evidence that exists only in the dev tree is exactly the audit's F4 gap:
    claims published without their anchor. Extra/missing/drifted files all fail
    closed; --fix restores the set (copies + deletes strays)."""
    errors, lines = [], []
    for d in EVIDENCE_DIRS:
        dev_dir, repo_dir = dev / "tests" / d, repo / "tests" / d
        if not dev_dir.is_dir():
            lines.append(f"SKIP evidence {d} (no dev source): {dev_dir}")
            continue
        dev_files = {p.relative_to(dev_dir).as_posix(): sha256(p)
                     for p in sorted(dev_dir.rglob("*")) if p.is_file()}
        repo_files = ({p.relative_to(repo_dir).as_posix(): sha256(p)
                       for p in sorted(repo_dir.rglob("*")) if p.is_file()}
                      if repo_dir.is_dir() else {})
        before = len(errors)
        for rel, want in dev_files.items():
            if rel not in repo_files:
                errors.append(f"evidence {d}: repo copy missing: {rel}")
            elif repo_files[rel] != want:
                errors.append(f"evidence {d}: DRIFT — {rel} expected {want[:12]} "
                              f"got {repo_files[rel][:12]}")
        for rel in sorted(set(repo_files) - set(dev_files)):
            errors.append(f"evidence {d}: extra file in repo copy: {rel}")
        if len(errors) == before:
            lines.append(f"OK   evidence {d:8s} {len(dev_files)} file(s) match")
    return errors, lines


def check(dev: Path = DEV, installed: Path = INSTALLED, eval_dir: Path = EVAL,
          allow_missing_eval: bool = False,
          allow_missing_installed: bool = False,
          repo: Path = None,
          allow_missing_repo: bool = False):
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
    if repo is not None and not repo.is_dir():
        if allow_missing_repo:
            missing_ok.append(f"repo tree absent (allowed): {repo}")
        else:
            errors.append(f"repo tree missing: {repo} (pass --allow-missing-repo "
                          f"only for a dev-only checkout)")

    for name, canonical, copies in copy_plan(dev, installed, eval_dir, repo):
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
                if label == "repo" and allow_missing_repo:
                    missing_ok.append(f"{label} absent (allowed): {path}")
                    continue
                errors.append(f"{name}: {label} missing: {path}")
                continue
            got = sha256(path)
            if got != want:
                errors.append(f"{name}: {label} DRIFT — expected {want[:12]} got {got[:12]} ({path})")
            else:
                lines.append(f"OK   {label:18s} {got[:12]}")

    if repo is not None and repo.is_dir():
        ev_errors, ev_lines = evidence_parity(dev, repo)
        errors.extend(ev_errors)
        lines.extend(ev_lines)

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
                payload = json.loads(task_json.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"task {t}: task.json unreadable ({exc})")
                continue
            pin = (payload.get("compliance") or {}).get("canonical_assert_sha")
            if not isinstance(pin, str) or not SHA_RE.match(pin):
                errors.append(f"task {t}: compliance.canonical_assert_sha missing or malformed")
            elif pin != want:
                errors.append(f"task {t}: canonical_assert_sha DRIFT — pin {pin[:12]} "
                              f"!= file {want[:12]}")
            else:
                lines.append(f"OK   pin {t:26s} {pin[:12]}")

    for line in missing_ok:
        lines.append(f"SKIP {line}")
    return errors, lines


def _is_eval_copy(label: str) -> bool:
    return label == "eval snapshot" or label.startswith("task ")


def _tree_ready(root: Path, *markers: str) -> bool:
    """A tree is 'present' only when its expected sentinel paths exist — an
    empty/bogus sibling directory must not receive scattered skill copies."""
    return root.is_dir() and all((root / m).exists() for m in markers)


def apply_fix(dev: Path = DEV, installed: Path = INSTALLED, eval_dir: Path = EVAL,
              allow_missing_eval: bool = False,
              allow_missing_installed: bool = False,
              repo: Path = None,
              allow_missing_repo: bool = False):
    """Copy canonical bytes to every READY copy tree and repin task.json.

    A target tree that is absent or lacks its sentinel is skipped, never
    invented (avoids scattering skill copies into a bogus sibling path).
    Returns (fixed, skipped).
    """
    fixed, skipped = [], []
    eval_ready = _tree_ready(eval_dir, "suite", "configs")
    installed_ready = _tree_ready(installed, "scripts")
    repo_ready = repo is not None and _tree_ready(repo, "vibeweaver", "tests")
    for name, canonical, copies in copy_plan(dev, installed, eval_dir, repo):
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
            if label == "repo" and not repo_ready:
                skipped.append(f"{label} — repo tree absent/incomplete ({repo})")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            same = path.is_file() and sha256(path) == want
            if not same:
                shutil.copyfile(canonical, path)
                fixed.append(f"{name}: {label} <- {canonical}")
    if repo_ready:
        for d in EVIDENCE_DIRS:
            dev_dir, repo_dir = dev / "tests" / d, repo / "tests" / d
            if not dev_dir.is_dir():
                continue
            dev_files = {p.relative_to(dev_dir).as_posix(): p
                         for p in sorted(dev_dir.rglob("*")) if p.is_file()}
            repo_files = ({p.relative_to(repo_dir).as_posix(): p
                           for p in sorted(repo_dir.rglob("*")) if p.is_file()}
                          if repo_dir.is_dir() else {})
            for rel, src in dev_files.items():
                dst = repo_dir / rel
                if rel not in repo_files or sha256(src) != sha256(dst):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    fixed.append(f"evidence {d}: {rel} <- {src}")
            for rel in sorted(set(repo_files) - set(dev_files)):
                repo_files[rel].unlink()
                fixed.append(f"evidence {d}: removed stray {rel}")
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
            if n != 1:
                raise SystemExit(f"sync_skill.py: cannot update exactly one pin in {task_json}")
            if new != text:
                task_json.write_text(new)
                fixed.append(f"pin {t} <- {want[:12]}")
    return fixed, skipped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="copy canonical bytes + repin")
    ap.add_argument("--allow-missing-eval", action="store_true")
    ap.add_argument("--allow-missing-installed", action="store_true")
    ap.add_argument("--allow-missing-repo", action="store_true")
    args = ap.parse_args(argv)
    if args.fix:
        fixed, skipped = apply_fix(allow_missing_eval=args.allow_missing_eval,
                                   allow_missing_installed=args.allow_missing_installed,
                                   repo=REPO, allow_missing_repo=args.allow_missing_repo)
        for line in fixed:
            print(f"FIX  {line}")
        for line in skipped:
            print(f"SKIP {line}")
    errors, lines = check(allow_missing_eval=args.allow_missing_eval,
                          allow_missing_installed=args.allow_missing_installed,
                          repo=REPO, allow_missing_repo=args.allow_missing_repo)
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


if __name__ == "__main__":
    sys.exit(main())
