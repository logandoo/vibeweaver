#!/usr/bin/env python3
"""repo_budget.py — live-tree total bytes + top-N blobs, shrink-only ceiling.

The cumulative "reachable blob bytes" metric grows on every new commit and is
therefore not a valid ratchet. This tool measures the live working tree
(tracked + untracked, non-ignored) and freezes its total at adoption; existing
history is covered by group 21's largest-blob and .git-size checks.

Exit codes: 0 pass/budget; 1 growth; 2 config/discovery/I-O.
"""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import sys

try:
    from git_trust import run_git as _trusted_git
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from git_trust import run_git as _trusted_git

BASELINE = "tests/repo_budget_baseline.json"
DEFAULT_SLACK = 10


class RepoBudgetError(Exception):
    pass


def _git(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise RepoBudgetError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def _git_bytes(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise RepoBudgetError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout, p.stderr

def _ceiling(total, slack):
    if total <= 0:
        return 0
    return int(math.ceil(total * (100 + slack) / 100.0))


def _repo_prefix(root):
    rc, out, _ = _git(root, "rev-parse", "--show-prefix")
    return out.strip() if rc == 0 else ""


def _repo_rel(root, rel):
    prefix = _repo_prefix(root)
    return (prefix + rel) if prefix else rel


def _tracked_clean(root, rel):
    path = Path(root) / rel
    if path.is_symlink():
        raise RepoBudgetError(f"{rel} must be a regular file, not a symlink")
    rc, _, _ = _git(root, "ls-files", "--error-unmatch", rel)
    if rc != 0:
        raise RepoBudgetError(f"{rel} is not tracked — commit the baseline before --final")
    rc, actual, _ = _git(root, "hash-object", "--path", _repo_rel(root, rel), "--", rel)
    rc2, head, _ = _git(root, "rev-parse", f"HEAD:{_repo_rel(root, rel)}")
    if rc != 0 or rc2 != 0:
        raise RepoBudgetError(f"{rel} is not readable/clean from HEAD — commit it before --final")
    if actual != head:
        raise RepoBudgetError(f"{rel} differs from HEAD (uncommitted or assume-unchanged); "
                              "commit it before --final")


def _first_baseline_commit(root):
    rc, out, _ = _git(root, "log", "--reverse", "--diff-filter=A", "--format=%H", "--", BASELINE)
    if rc != 0 or not out.strip():
        return None
    return out.splitlines()[0].strip()


def _same_commit(root, a, b):
    _, ra, _ = _git(root, "rev-parse", a)
    _, rb, _ = _git(root, "rev-parse", b)
    return ra == rb


def _base_baseline(root, ref):
    rc, raw, _ = _git(root, "show", f"{ref}:{_repo_rel(root, BASELINE)}")
    if rc != 0:
        raise RepoBudgetError(f"--base {ref!r} has no {BASELINE}; pin the ADOPTION commit")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise RepoBudgetError(f"--base {ref!r}: baseline is unparseable") from exc


def discover(root):
    root = Path(root)
    rc, out, err = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--")
    if rc != 0:
        raise RepoBudgetError("git discovery failed" + (f": {err.strip()}" if err else ""))
    files = []
    for raw in out.split("\0"):
        if not raw:
            continue
        rel = raw.replace(os.sep, "/")
        if rel == BASELINE:
            continue
        if rel.startswith(".vibeweaver/") or rel == "tests/gate_result.json":
            continue
        path = root / rel
        try:
            if not path.is_file() or path.is_symlink():
                continue
            size = path.stat().st_size
        except OSError as exc:
            raise RepoBudgetError(f"cannot stat {rel}: {exc}") from exc
        files.append({"path": rel, "bytes": size})
    files.sort(key=lambda x: (-x["bytes"], x["path"]))
    return files


def load_baseline(root, allow_missing=False):
    path = Path(root) / BASELINE
    if path.is_symlink():
        raise RepoBudgetError(f"{BASELINE} must be a regular file, not a symlink")
    try:
        if path.stat().st_size > 64 * 1024:
            raise RepoBudgetError(f"{BASELINE} exceeds 64 KiB; the baseline is not a data store")
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = None
    except (OSError, ValueError) as exc:
        raise RepoBudgetError(f"cannot read {BASELINE}: {exc}") from exc
    if data is None:
        if allow_missing:
            return None
        rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
        if rc == 0:
            raise RepoBudgetError(f"{BASELINE} is tracked in HEAD but missing on disk; restore it")
        return None
    if not isinstance(data, dict) or data.get("version") != 1 or "ceiling" not in data:
        raise RepoBudgetError(f"{BASELINE} has an unsupported schema")
    return data


def write_baseline(root, data):
    path = Path(root) / BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=1, sort_keys=True) + "\n")
    os.replace(str(tmp), str(path))


def snapshot(root):
    files = discover(root)
    return sum(x["bytes"] for x in files), files


def cmd_init(root, args):
    if (Path(root) / BASELINE).exists():
        raise RepoBudgetError(f"{BASELINE} already exists; use `tighten`")
    rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
    if rc == 0:
        raise RepoBudgetError(f"{BASELINE} is tracked in HEAD but missing on disk; restore it")
    rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
    if hist.strip():
        raise RepoBudgetError(f"{BASELINE} exists in repository history; re-init is not allowed")
    if not 0 <= int(args.slack) <= 25:
        raise RepoBudgetError("--slack must be between 0 and 25")
    total, files = snapshot(root)
    data = {
        "version": 1,
        "live_tree_bytes": total,
        "ceiling": _ceiling(total, args.slack),
        "slack": int(args.slack),
        "largest_blob": files[0]["bytes"] if files else 0,
        "top_n": files[:10],
        "recorded_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "reason": args.reason or "adoption: freeze live-tree total",
    }
    write_baseline(root, data)
    print(f"repo_budget: initialized {BASELINE} (live={total} ceiling={data['ceiling']})")
    return 0


def cmd_budget(root, args):
    baseline = load_baseline(root, allow_missing=True)
    total, files = snapshot(root)
    data = {"schema": "repo-budget/1",
            "result": "NO_BASELINE" if baseline is None else "PASS",
            "live_tree_bytes": total, "top_n": files[:10], "groups": {}}
    if baseline is not None:
        ceiling = int(baseline["ceiling"])
        data["ceiling"] = ceiling
        data["headroom"] = ceiling - total
        data["baseline_live_tree_bytes"] = int(baseline.get("live_tree_bytes", 0))
    if args.format == "json":
        print(json.dumps(data, indent=1, sort_keys=True))
    else:
        print(f"REPO-BUDGET result={data['result']} live={total} "
              f"ceiling={data.get('ceiling', 'n/a')} headroom={data.get('headroom', 'n/a')}")
        for item in data["top_n"][:10]:
            print(f"TOP {item['bytes']:>10} {item['path']}")
    return 0


def cmd_check(root, args):
    baseline = load_baseline(root, allow_missing=True)
    if baseline is None:
        rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
        if hist.strip():
            print("repo_budget: baseline was adopted then deleted; restore it from history")
            return 2
        if args.final and not args.adopt_optional:
            print("repo_budget: no baseline — run `init` before completion (fail-closed)")
            return 2
        print("repo_budget: WARN no baseline — project has not adopted the live-tree budget")
        return 0
    rc, shallow, _ = _git(root, "rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() not in ("true", "false"):
        raise RepoBudgetError("cannot verify repository depth (shallow probe failed); fail-closed")
    if shallow.strip() == "true":
        raise RepoBudgetError("repo budget needs full history (shallow clone); run `git fetch --unshallow`")
    if args.final:
        _tracked_clean(root, BASELINE)
    total, files = snapshot(root)
    ceiling = int(baseline["ceiling"])
    violations = []
    if total > ceiling:
        violations.append(f"live tree grew beyond its ceiling: {total} > {ceiling} bytes")
    adoption = _first_baseline_commit(root)
    base_ref = args.base or adoption
    if args.base:
        if adoption is None:
            raise RepoBudgetError("--base is set but the baseline has no adoption commit")
        if not _same_commit(root, args.base, adoption):
            raise RepoBudgetError("--base must be the first commit that adds the baseline "
                                  "(the adoption commit), not a later ancestor")
        if _same_commit(root, args.base, "HEAD"):
            raise RepoBudgetError("--base must be a strict ancestor, not HEAD")
    if base_ref and not _same_commit(root, base_ref, "HEAD"):
        rc, _, _ = _git(root, "merge-base", "--is-ancestor", base_ref, "HEAD")
        if rc != 0:
            raise RepoBudgetError(f"--base {base_ref!r} is not an ancestor of HEAD")
        base = _base_baseline(root, base_ref)
        if ceiling > int(base.get("ceiling", 0)):
            violations.append(f"repo ceiling was raised above --base "
                              f"({base.get('ceiling')} -> {ceiling})")
        if int(baseline.get("slack", 0)) > int(base.get("slack", 0)):
            violations.append("repo slack was raised above --base")
    if args.format == "json":
        payload = {"schema": "repo-budget/1", "result": "FAIL" if violations else "PASS",
                   "live_tree_bytes": total, "ceiling": ceiling,
                   "headroom": ceiling - total, "violations": violations,
                   "top_n": files[:10]}
        text = json.dumps(payload, indent=1, sort_keys=True)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
    else:
        print(f"REPO-BUDGET result={'FAIL' if violations else 'PASS'} "
              f"live={total} ceiling={ceiling}")
        for v in violations:
            print("  - " + v)
        if violations:
            print("  fix: archive generated binaries, move large assets to LFS/releases, "
                  "or shrink the live tree; no per-file human waiver")
    return 1 if violations else 0


def cmd_tighten(root, args):
    baseline = load_baseline(root)
    if baseline is None:
        raise RepoBudgetError(f"no {BASELINE}; run `init` first")
    total, files = snapshot(root)
    slack = int(baseline.get("slack", DEFAULT_SLACK))
    baseline["ceiling"] = min(int(baseline["ceiling"]), _ceiling(total, slack))
    baseline["live_tree_bytes"] = total
    baseline["largest_blob"] = files[0]["bytes"] if files else 0
    baseline["top_n"] = files[:10]
    write_baseline(root, baseline)
    print(f"repo_budget: tightened {BASELINE} (live={total} ceiling={baseline['ceiling']})")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--slack", type=int, default=DEFAULT_SLACK)
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("budget")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=cmd_budget)

    p = sub.add_parser("check")
    p.add_argument("--final", action="store_true")
    p.add_argument("--adopt-optional", action="store_true",
                   help="build-hook mode: no baseline in an unadopted project is a WARN")
    p.add_argument("--base", default="")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--output", default="")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("tighten")
    p.set_defaults(func=cmd_tighten)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"repo_budget: ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        return args.func(root, args)
    except (RepoBudgetError, OSError, ValueError) as exc:
        print(f"repo_budget: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
