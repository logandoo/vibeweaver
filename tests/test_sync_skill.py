#!/usr/bin/env python3
"""TP/FP checks for tests/sync_skill.py (W9 P0-3).

Builds a miniature dev/installed/eval tree, proves a clean verdict, then
tampers one copy and one task pin and proves both fail closed. `--fix`
restores the tree and the verdict.
"""
import hashlib
import importlib.util
import json
import pathlib
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SYNC = REPO / "tests" / "sync_skill.py"
spec = importlib.util.spec_from_file_location("sync_skill", SYNC)
sync_skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_skill)

RESULTS = []


def rec(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root):
    dev = root / "dev"
    installed = root / "installed"
    evald = root / "eval"
    (dev / "scripts").mkdir(parents=True)
    (dev / "tests").mkdir(parents=True)
    (installed / "scripts").mkdir(parents=True)
    snap = evald / "configs" / "fn_latest" / "opencode" / "skills" / "vibeweaver" / "scripts"
    snap.mkdir(parents=True)
    (dev / "scripts" / "assert_artifacts.py").write_text("canon-assert\n", encoding="utf-8")
    (dev / "scripts" / "scan_secrets.py").write_text("canon-scan\n", encoding="utf-8")
    # W0 Task 2/2.5/4 controlled files (pin + lock + repair + bootstrap)
    for name in ("assert_artifacts.sha256", "evidence_lock.py", "repair_checker.sh", "state_sanitize.py", "contract_lint.py"):
        (dev / "scripts" / name).write_text("canon-%s\n" % name, encoding="utf-8")
        (installed / "scripts" / name).write_bytes((dev / "scripts" / name).read_bytes())
    (dev / "bootstrap.md").write_text("# bootstrap\n", encoding="utf-8")
    (installed / "bootstrap.md").write_bytes((dev / "bootstrap.md").read_bytes())
    for target in [
        dev / "tests" / "assert_artifacts.py",
        installed / "scripts" / "assert_artifacts.py",
        snap / "assert_artifacts.py",
    ]:
        target.write_bytes((dev / "scripts" / "assert_artifacts.py").read_bytes())
    for target in [installed / "scripts" / "scan_secrets.py", snap / "scan_secrets.py"]:
        target.write_bytes((dev / "scripts" / "scan_secrets.py").read_bytes())
    for task in sync_skill.TASKS:
        canonical = evald / "suite" / "tasks" / task / "canonical" / "assert_artifacts.py"
        canonical.parent.mkdir(parents=True)
        canonical.write_bytes((dev / "scripts" / "assert_artifacts.py").read_bytes())
        (canonical.parent.parent / "task.json").write_text(json.dumps(
            {"compliance": {"canonical_assert_sha": sha(canonical)}}, indent=2) + "\n",
            encoding="utf-8")
    return dev, installed, evald


def build_full(root):
    """Miniature tree that also carries a repo copy + W18 evidence dirs."""
    dev, installed, evald = build(root / "repo-wave")
    (dev / "tests" / "plugin_compat_test.mjs").write_text("harness-v1\n", encoding="utf-8")
    (dev / "tests" / "sync_skill.py").write_text("sync-tool-v1\n", encoding="utf-8")
    (dev / "tests" / "test_sync_skill.py").write_text("sync-test-v1\n", encoding="utf-8")
    for d in sync_skill.EVIDENCE_DIRS:
        (dev / "tests" / d).mkdir(parents=True, exist_ok=True)
        (dev / "tests" / d / f"{d}-a.log").write_text(f"{d} evidence A\n", encoding="utf-8")
        (dev / "tests" / d / f"{d}-b.log").write_text(f"{d} evidence B\n", encoding="utf-8")
    repo = dev.parent / "repo"
    (repo / "vibeweaver").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "vibeweaver" / "SKILL.md").write_text("payload sentinel\n", encoding="utf-8")
    (repo / "vibeweaver" / "scripts").mkdir(parents=True)
    for name in ("assert_artifacts.sha256", "evidence_lock.py", "repair_checker.sh", "state_sanitize.py", "contract_lint.py"):
        (repo / "vibeweaver" / "scripts" / name).write_bytes((dev / "scripts" / name).read_bytes())
    (repo / "vibeweaver" / "bootstrap.md").write_bytes((dev / "bootstrap.md").read_bytes())
    for name in ("plugin_compat_test.mjs", "sync_skill.py", "test_sync_skill.py"):
        (repo / "tests" / name).write_bytes((dev / "tests" / name).read_bytes())
    for d in sync_skill.EVIDENCE_DIRS:
        (repo / "tests" / d).mkdir(parents=True, exist_ok=True)
        for f in (dev / "tests" / d).iterdir():
            (repo / "tests" / d / f.name).write_bytes(f.read_bytes())
    return dev, installed, evald, repo


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix="vwsync-"))
    dev, installed, evald = build(root)

    errors, _ = sync_skill.check(dev, installed, evald)
    rec("SS1 clean miniature tree -> no drift", not errors, "; ".join(errors)[:140])

    snap = (evald / "configs" / "fn_latest" / "opencode" / "skills"
            / "vibeweaver" / "scripts" / "assert_artifacts.py")
    snap.write_text("tampered\n", encoding="utf-8")
    errors, _ = sync_skill.check(dev, installed, evald)
    rec("SS2 tampered eval snapshot -> fail closed",
        any("DRIFT" in e and "eval snapshot" in e for e in errors), "; ".join(errors)[:160])

    sync_skill.apply_fix(dev, installed, evald)
    errors, _ = sync_skill.check(dev, installed, evald)
    rec("SS3 --fix restores the snapshot", not errors, "; ".join(errors)[:140])

    task_json = evald / "suite" / "tasks" / sync_skill.TASKS[0] / "task.json"
    payload = json.loads(task_json.read_text())
    payload["compliance"]["canonical_assert_sha"] = "0" * 64
    task_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    errors, _ = sync_skill.check(dev, installed, evald)
    rec("SS4 stale canonical_assert_sha -> fail closed",
        any("canonical_assert_sha DRIFT" in e for e in errors), "; ".join(errors)[:160])

    sync_skill.apply_fix(dev, installed, evald)
    errors, _ = sync_skill.check(dev, installed, evald)
    rec("SS5 --fix repins task.json", not errors, "; ".join(errors)[:140])

    # SS6 — an absent eval tree is never invented by --fix (reviewer 2 #1).
    missing_eval = root / "eval-absent"
    fixed, skipped = sync_skill.apply_fix(dev, installed, missing_eval,
                                          allow_missing_eval=True)
    rec("SS6 --fix does not invent an absent eval tree",
        not missing_eval.exists() and any("eval tree absent" in s for s in skipped),
        f"exists={missing_eval.exists()} skipped={len(skipped)}")

    # SS7 — --allow-missing-eval covers the task canonicals too (reviewer 2 #2).
    errors, _ = sync_skill.check(dev, installed, missing_eval, allow_missing_eval=True)
    rec("SS7 --allow-missing-eval covers task canonicals", not errors,
        "; ".join(errors)[:140])

    # SS8 — an existing-but-incomplete eval tree is not treated as ready: no
    # configs/ or suite/ subtree is invented inside it.
    empty_eval = root / "eval-empty"
    empty_eval.mkdir()
    fixed, skipped = sync_skill.apply_fix(dev, installed, empty_eval,
                                          allow_missing_eval=True)
    rec("SS8 --fix does not populate an incomplete eval tree",
        not (empty_eval / "configs").exists() and not (empty_eval / "suite").exists()
        and any("incomplete" in s for s in skipped),
        f"configs={(empty_eval / 'configs').exists()} skipped={len(skipped)}")

    # SS9-SS13 (W18 release-hygiene fix, 2026-10-22): the repo tree joined the
    # controlled list — plugin_compat harness byte parity + evidence-dir parity.
    dev2, installed2, evald2, repo2 = build_full(root)

    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS9 clean tree incl. repo harness + evidence -> no drift", not errors,
        "; ".join(errors)[:140])

    (repo2 / "tests" / "plugin_compat_test.mjs").write_text("stale harness\n", encoding="utf-8")
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS10 stale repo harness -> fail closed",
        any("plugin_compat_test.mjs" in e and "DRIFT" in e for e in errors),
        "; ".join(errors)[:160])

    sync_skill.apply_fix(dev2, installed2, evald2, repo=repo2)
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS11 --fix restores the repo harness", not errors, "; ".join(errors)[:140])

    (repo2 / "tests" / "w18" / "w18-a.log").unlink()
    (repo2 / "tests" / "w18" / "w18-extra.log").write_text("stray\n", encoding="utf-8")
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS12 evidence set mismatch (missing + extra) -> fail closed",
        any("missing" in e for e in errors) and any("extra" in e for e in errors),
        "; ".join(errors)[:160])

    sync_skill.apply_fix(dev2, installed2, evald2, repo=repo2)
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS13 --fix restores the evidence set", not errors, "; ".join(errors)[:140])

    missing_repo = root / "repo-absent"
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=missing_repo,
                                 allow_missing_repo=True)
    fixed, skipped = sync_skill.apply_fix(dev2, installed2, evald2, repo=missing_repo,
                                          allow_missing_repo=True)
    rec("SS14 --allow-missing-repo skips, never invents the repo tree",
        not errors and not missing_repo.exists()
        and any("repo tree" in s for s in skipped),
        f"errors={len(errors)} exists={missing_repo.exists()} skipped={len(skipped)}")

    (repo2 / "tests" / "w18sync" / "w18sync-b.log").write_text("tampered\n", encoding="utf-8")
    errors, _ = sync_skill.check(dev2, installed2, evald2, repo=repo2)
    rec("SS15 tampered evidence file -> fail closed",
        any("w18sync" in e and "DRIFT" in e for e in errors), "; ".join(errors)[:160])

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
          (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
    return 1 if fails else 0


def test_sync_skill_vectors():
    """pytest entry point (the file is also a direct-run harness)."""
    assert main() == 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
