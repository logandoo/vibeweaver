#!/usr/bin/env python3
"""source_ratchet.py — shrink-only source budgets with rare, budget-level grants.

This is a companion to source_budget.py (measurement/report only). It consumes
the same policy and discovery, then enforces:

  * new files: hard_lines ceiling;
  * existing over-hard files: frozen at adoption, may shrink, never grow;
  * source/tests group totals: ceilings that only shrink, plus active grants;
  * grants: append-only, human-only, expiring; never a per-file waiver.

Exit codes: 0 pass/budget; 1 ratchet violation; 2 config/discovery/I-O.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import subprocess
import sys

import source_budget as sb

try:
    from git_trust import run_git as _trusted_git
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from git_trust import run_git as _trusted_git

BASELINE = "tests/source_ratchet_baseline.json"
GRANTS = "tests/source_ratchet_grants.jsonl"
DEFAULT_SLACK = 5
GROUPS = ("source", "tests")
TEST_DIRS = ("tests/", "test/", "testing/", "__tests__/", "spec/")
TEST_NAME = re.compile(r"(^test_.*|.*_tests?\.[^.]+|.*\.(?:test|spec)\.[^.]+)$")


class RatchetError(Exception):
    pass


class RatchetRefusal(RatchetError):
    """A policy refusal (exit 1), distinct from an operational error (exit 2)."""


def _git(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise RatchetError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def _git_bytes(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise RatchetError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout, p.stderr

def _require_git(root):
    rc, out, err = _git(root, "rev-parse", "--is-inside-work-tree")
    if rc != 0 or out != "true":
        raise RatchetError("source ratchet requires a Git worktree" + (f" ({err})" if err else ""))


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_bytes_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _norm_sha(path):
    return _norm_bytes_sha(Path(path).read_bytes())


def _frozen_norm(root, path, meta):
    if meta.get("sha256_norm"):
        return meta["sha256_norm"]
    rc, raw, _ = _git_bytes(root, "show", f"HEAD:{_repo_rel(root, path)}")
    if rc == 0:
        return _norm_bytes_sha(raw)
    return meta.get("sha256")


def _repo_prefix(root):
    rc, out, _ = _git(root, "rev-parse", "--show-prefix")
    return out.strip() if rc == 0 else ""


def _repo_rel(root, rel):
    prefix = _repo_prefix(root)
    return (prefix + rel) if prefix else rel


def _tracked_clean(root, rel):
    path = Path(root) / rel
    if path.is_symlink():
        raise RatchetError(f"{rel} must be a regular file, not a symlink")
    rc, _, _ = _git(root, "ls-files", "--error-unmatch", rel)
    if rc != 0:
        raise RatchetError(f"{rel} is not tracked — commit the baseline/grants before --final")
    rc, actual, _ = _git(root, "hash-object", "--path", _repo_rel(root, rel), "--", rel)
    rc2, head, _ = _git(root, "rev-parse", f"HEAD:{_repo_rel(root, rel)}")
    if rc != 0 or rc2 != 0:
        raise RatchetError(f"{rel} is not readable/clean from HEAD — commit it before --final")
    if actual != head:
        raise RatchetError(f"{rel} differs from HEAD (uncommitted or assume-unchanged); commit it before --final")


def _first_baseline_commit(root):
    rc, out, _ = _git(root, "log", "--reverse", "--diff-filter=A", "--format=%H", "--", BASELINE)
    if rc != 0 or not out.strip():
        return None
    return out.splitlines()[0].strip()


def is_test_path(rel):
    if any(rel.startswith(d) for d in TEST_DIRS):
        return True
    return bool(TEST_NAME.match(posixpath.basename(rel)))


def group_of(rel):
    return "tests" if is_test_path(rel) else "source"


def _ceiling(total, slack, hard=0):
    if total <= 0:
        # An empty group gets one hard-cap of headroom so adoption does not
        # start at a zero ceiling; once the group has files, only slack applies.
        return max(0, int(hard))
    return int(math.ceil(total * (100 + slack) / 100.0))


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise RatchetError(f"cannot read {path}: {exc}") from exc


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=1, sort_keys=True) + "\n")
    os.replace(str(tmp), str(path))


def load_baseline(root, allow_missing=False):
    path = Path(root) / BASELINE
    if path.is_symlink():
        raise RatchetError(f"{BASELINE} must be a regular file, not a symlink")
    data = _load_json(path)
    if data is None:
        if allow_missing:
            return None
        rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
        if rc == 0:
            raise RatchetError(
                f"{BASELINE} is tracked in HEAD but missing on disk — restore it; "
                "delete-and-re-record would launder frozen debt")
        return None
    if not isinstance(data, dict) or data.get("version") != 1:
        raise RatchetError(f"{BASELINE} has an unsupported schema")
    for key in ("policy", "groups", "files"):
        if not isinstance(data.get(key), dict):
            raise RatchetError(f"{BASELINE} missing/unparseable `{key}`")
    for g in GROUPS:
        if not isinstance(data["groups"].get(g), dict) or "ceiling" not in data["groups"][g]:
            raise RatchetError(f"{BASELINE} group `{g}` has no ceiling")
    for path, meta in data["files"].items():
        if (not isinstance(meta, dict) or not isinstance(meta.get("lines"), int)
                or not isinstance(meta.get("raw_bytes"), int)
                or not isinstance(meta.get("sha256"), str) or not meta.get("sha256")):
            raise RatchetError(f"{BASELINE} file `{path}` has incomplete freeze metadata")
    return data


def load_grants(root, allow_missing=True):
    path = Path(root) / GRANTS
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RatchetError(f"cannot read {GRANTS}: {exc}") from exc
    grants = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError as exc:
            raise RatchetError(f"{GRANTS}:{i}: invalid JSON") from exc
        if not isinstance(item, dict) or item.get("group") not in GROUPS:
            raise RatchetError(f"{GRANTS}:{i}: invalid group")
        if not isinstance(item.get("lines"), int) or item["lines"] <= 0:
            raise RatchetError(f"{GRANTS}:{i}: lines must be a positive integer")
        if not item.get("by") or not item.get("reason"):
            raise RatchetError(f"{GRANTS}:{i}: by/reason required")
        grants.append(item)
    return grants


def active_grants(grants, today=None):
    today = today or datetime.date.today()
    out = []
    for g in grants:
        expires = g.get("expires")
        if expires:
            try:
                if datetime.date.fromisoformat(str(expires)) < today:
                    continue
            except ValueError:
                raise RatchetError(f"grant has invalid expires date: {expires!r}")
        out.append(g)
    return out


def grants_by_group(grants):
    totals = {g: 0 for g in GROUPS}
    for item in grants:
        totals[item["group"]] += int(item["lines"])
    return totals


def evaluate(root, config=None):
    policy = sb.load_policy(Path(root), config)
    report = sb.evaluate(Path(root), policy, final=True)
    return policy, report


def group_totals(report):
    totals = {g: 0 for g in GROUPS}
    for item in report.get("files", []):
        totals[group_of(item["path"])] += int(item["physical_lines"])
    return totals


def file_set(report):
    return {item["path"]: item for item in report.get("files", [])}


def _base_file(root, ref, rel):
    rc, out, err = _git(root, "show", f"{ref}:{_repo_rel(root, rel)}")
    if rc != 0:
        return None
    return out


def cmd_init(root, args):
    _require_git(root)
    target = Path(root) / BASELINE
    if target.exists():
        raise RatchetError(f"{BASELINE} already exists; use `tighten` (never re-baseline)")
    rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
    if rc == 0:
        raise RatchetError(
            f"{BASELINE} is tracked in HEAD but missing on disk — restore it; "
            "delete-and-re-record would launder frozen debt")
    rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
    if hist.strip():
        raise RatchetError(f"{BASELINE} exists in repository history; re-init/delete is not allowed")
    _policy, report = evaluate(root, args.config)
    hard = int(_policy["hard_lines"])
    slack = int(args.slack)
    if not 0 <= slack <= 25:
        raise RatchetError("--slack must be between 0 and 25")
    totals = group_totals(report)
    files = {}
    for path, item in file_set(report).items():
        if int(item["physical_lines"]) > hard:
            files[path] = {
                "lines": int(item["physical_lines"]),
                "sha256": _sha_file(Path(root) / path),
                "sha256_norm": _norm_sha(Path(root) / path),
                "raw_bytes": int(item["raw_bytes"]),
            }
    baseline = {
        "version": 1,
        "policy": {"warn_lines": int(_policy["warn_lines"]), "hard_lines": hard, "slack": slack},
        "groups": {g: {"ceiling": _ceiling(totals[g], slack, hard)} for g in GROUPS},
        "files": files,
        "recorded_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "reason": args.reason or "adoption: freeze existing over-hard files",
    }
    _write_json(target, baseline)
    print(f"source_ratchet: initialized {BASELINE} "
          f"(source={totals['source']} tests={totals['tests']} frozen={len(files)})")
    return 0


def _current(root, config):
    _policy, report = evaluate(root, config)
    return report, group_totals(report), file_set(report)


def _effective_ceilings(baseline, grants):
    add = grants_by_group(active_grants(grants))
    return {g: int(baseline["groups"][g]["ceiling"]) + add[g] for g in GROUPS}


def _violations(root, baseline, report, totals, files, grants, hard):
    eff = _effective_ceilings(baseline, grants)
    out = []
    for g in GROUPS:
        if totals[g] > eff[g]:
            out.append(f"{g} group ceiling exceeded: {totals[g]} > {eff[g]} lines")
    for path, item in files.items():
        cur = int(item["physical_lines"])
        frozen = baseline["files"].get(path)
        if frozen is not None:
            limit = int(frozen["lines"])
            if cur > limit:
                out.append(f"{path} is frozen at {limit} lines (now {cur}); "
                           "frozen files may shrink, never grow")
        elif cur > hard:
            out.append(f"{path} is a new file over the hard cap: {cur} > {hard} lines")
    for path in baseline["files"]:
        if path not in files:
            out.append(f"{path} is frozen but missing from the current source scan; "
                       "use `rekey` for a pure rename or `prune` for a deletion")
    return out


def cmd_budget(root, args):
    baseline = load_baseline(root, allow_missing=True)
    _policy, report = evaluate(root, args.config)
    totals = group_totals(report)
    files = file_set(report)
    hard = int(_policy["hard_lines"])
    data = {"schema": "source-ratchet/1", "result": "NO_BASELINE" if baseline is None else "PASS",
            "policy": _policy, "groups": {}, "near_cap": []}
    if baseline is not None:
        grants = load_grants(root)
        eff = _effective_ceilings(baseline, grants)
        for g in GROUPS:
            data["groups"][g] = {
                "current": totals[g],
                "base_ceiling": int(baseline["groups"][g]["ceiling"]),
                "grant": eff[g] - int(baseline["groups"][g]["ceiling"]),
                "ceiling": eff[g],
                "headroom": eff[g] - totals[g],
            }
        for path, item in files.items():
            cur = int(item["physical_lines"])
            frozen = baseline["files"].get(path)
            limit = int(frozen["lines"]) if frozen is not None else hard
            if cur >= max(1, int(limit * 0.8)):
                data["near_cap"].append({"path": path, "lines": cur, "limit": limit})
        data["near_cap"].sort(key=lambda x: (-x["lines"], x["path"]))
    if args.format == "json":
        print(json.dumps(data, indent=1, sort_keys=True))
    else:
        print(f"SOURCE-RATCHET result={data['result']} "
              f"source={totals['source']} tests={totals['tests']} hard={hard}")
        for g in GROUPS:
            if g in data["groups"]:
                x = data["groups"][g]
                print(f"{g}: {x['current']}/{x['ceiling']} (headroom {x['headroom']}, grant {x['grant']})")
        for item in data["near_cap"][:20]:
            print(f"NEAR-CAP {item['path']} {item['lines']}/{item['limit']}")
    return 0


def _base_baseline(root, ref):
    raw = _base_file(root, ref, BASELINE)
    if raw is None:
        raise RatchetError(f"--base {ref!r} has no {BASELINE}; pin the ADOPTION commit")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise RatchetError(f"--base {ref!r}: baseline is unparseable") from exc


def _base_grants(root, ref):
    raw = _base_file(root, ref, GRANTS)
    out = []
    if raw:
        for line in raw.splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise RatchetError(f"--base {ref!r}: grants are unparseable") from exc
    return out


def _base_file_violations(root, base, files, base_ref):
    out = []
    base_files = base.get("files", {}) if isinstance(base.get("files"), dict) else {}
    missing = {}
    for path, meta in base_files.items():
        cur = files.get(path)
        if cur is not None:
            if int(cur.get("lines", 0)) > int(meta.get("lines", 0)):
                out.append(f"{path} grew past its base frozen limit "
                           f"({meta.get('lines')} -> {cur.get('lines')})")
        else:
            rc, raw, _ = _git_bytes(root, "show", f"{base_ref}:{_repo_rel(root, path)}")
            base_norm = _norm_bytes_sha(raw) if rc == 0 else (meta.get("sha256_norm") or meta.get("sha256"))
            missing[path] = (base_norm, int(meta.get("lines", 0)))
    used = set()
    for path, item in files.items():
        if path in base_files:
            continue
        try:
            raw = (Path(root) / path).read_bytes()
        except OSError as exc:
            raise RatchetError(f"cannot read {path}: {exc}") from exc
        actual_sha = _norm_sha(Path(root) / path)
        actual_lines = sb.measure(raw)["physical_lines"]
        match = next((p for p, (sha, lines) in missing.items()
                      if sha == actual_sha and lines == actual_lines and p not in used), None)
        if match is None:
            out.append(f"{path} is a new frozen entry whose actual content does not "
                       "match a missing base frozen file; only a one-to-one rekey is allowed")
        else:
            used.add(match)
    return out


def _same_commit(root, a, b):
    _, ra, _ = _git(root, "rev-parse", a)
    _, rb, _ = _git(root, "rev-parse", b)
    return ra == rb


def cmd_check(root, args):
    baseline = load_baseline(root, allow_missing=True)
    if baseline is None:
        rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
        if hist.strip():
            print("source_ratchet: baseline was adopted then deleted; restore it from history "
                  "(delete-and-re-record is not a ratchet path)")
            return 2
        if args.final and not args.adopt_optional:
            print("source_ratchet: no baseline — run `init` before completion (fail-closed)")
            return 2
        print("source_ratchet: WARN no baseline — project has not adopted the ratchet")
        return 0
    rc, shallow, _ = _git(root, "rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() not in ("true", "false"):
        raise RatchetError("cannot verify repository depth (shallow probe failed); fail-closed")
    if shallow.strip() == "true":
        raise RatchetError("source ratchet needs full history (shallow clone); run `git fetch --unshallow`")
    if args.final:
        _tracked_clean(root, BASELINE)
        if (Path(root) / GRANTS).exists():
            _tracked_clean(root, GRANTS)
    _policy, report = evaluate(root, args.config)
    if report.get("result") == "ERROR" or report.get("errors"):
        raise RatchetError("source measurement failed: "
                           + "; ".join(report.get("errors", [])[:3]))
    binaries = report.get("excluded", {}).get("binary", [])
    if binaries:
        raise RatchetError("binary source file(s) cannot be measured safely: "
                           + ", ".join(binaries[:5]))
    totals = group_totals(report)
    files = file_set(report)
    hard = int(baseline["policy"].get("hard_lines", _policy["hard_lines"]))
    grants = load_grants(root)
    violations = _violations(root, baseline, report, totals, files, grants, hard)

    adoption = _first_baseline_commit(root)
    base_ref = args.base or adoption
    if args.base:
        if adoption is None:
            raise RatchetError("--base is set but the baseline has no adoption commit")
        if not _same_commit(root, args.base, adoption):
            raise RatchetError("--base must be the first commit that adds the baseline "
                               "(the adoption commit), not a later ancestor")
        if _same_commit(root, args.base, "HEAD"):
            raise RatchetError("--base must be a strict ancestor, not HEAD")
    if base_ref and not _same_commit(root, base_ref, "HEAD"):
        rc, _, _ = _git(root, "merge-base", "--is-ancestor", base_ref, "HEAD")
        if rc != 0:
            raise RatchetError(f"--base {base_ref!r} is not an ancestor of HEAD")
        base = _base_baseline(root, base_ref)
        base_grants = _base_grants(root, base_ref)
        if grants[:len(base_grants)] != base_grants:
            violations.append("grants log is not append-only since --base "
                              "(removed/rewritten lines are not a grant)")
        base_policy = base.get("policy", {}) if isinstance(base.get("policy"), dict) else {}
        if int(baseline["policy"].get("hard_lines", 0)) > int(base_policy.get("hard_lines", 0)):
            violations.append("policy.hard_lines was raised above --base; the hard cap is not editable")
        if int(baseline["policy"].get("slack", 0)) > int(base_policy.get("slack", 0)):
            violations.append("policy.slack was raised above --base; adoption slack is not editable")
        for g in GROUPS:
            old = int(base.get("groups", {}).get(g, {}).get("ceiling", 0))
            new = int(baseline["groups"][g]["ceiling"])
            if new > old:
                violations.append(f"{g} base ceiling was raised ({old} -> {new}); "
                                  "base edits are always rejected (grants are additive, not a baseline edit)")
        violations.extend(_base_file_violations(root, base, baseline["files"], base_ref))

    if args.format == "json":
        payload = {"schema": "source-ratchet/1",
                   "result": "FAIL" if violations else "PASS",
                   "policy": _policy, "groups": {}, "violations": violations,
                   "grants": grants}
        eff = _effective_ceilings(baseline, grants)
        for g in GROUPS:
            payload["groups"][g] = {"current": totals[g], "ceiling": eff[g],
                                    "headroom": eff[g] - totals[g]}
        text = json.dumps(payload, indent=1, sort_keys=True)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
    else:
        print(f"SOURCE-RATCHET result={'FAIL' if violations else 'PASS'} "
              f"source={totals['source']} tests={totals['tests']}")
        for v in violations:
            print("  - " + v)
        if violations:
            print("  fix: shrink, split by responsibility seam, rekey/prune a frozen path, "
                  "or ask a human for a budget-level grant (never edit the baseline)")
    return 1 if violations else 0


def cmd_tighten(root, args):
    _require_git(root)
    baseline = load_baseline(root)
    if baseline is None:
        raise RatchetError(f"no {BASELINE}; run `init` first")
    _policy, report = evaluate(root, args.config)
    totals = group_totals(report)
    files = file_set(report)
    slack = int(baseline["policy"].get("slack", DEFAULT_SLACK))
    hard = int(baseline["policy"].get("hard_lines", _policy["hard_lines"]))
    for g in GROUPS:
        proposed = _ceiling(totals[g], slack, hard)
        baseline["groups"][g]["ceiling"] = min(int(baseline["groups"][g]["ceiling"]), proposed)
    for path in list(baseline["files"]):
        if path not in files:
            # Preserve a missing frozen key: a rename is handled by `rekey`, a real
            # deletion by `prune`; silently dropping it is the scope-escape path.
            continue
        cur = int(files[path]["physical_lines"])
        if cur <= int(baseline["files"][path]["lines"]):
            baseline["files"][path]["lines"] = cur
            baseline["files"][path]["sha256"] = _sha_file(Path(root) / path)
            baseline["files"][path]["raw_bytes"] = int(files[path]["raw_bytes"])
    _write_json(Path(root) / BASELINE, baseline)
    print(f"source_ratchet: tightened {BASELINE} (source={totals['source']} tests={totals['tests']})")
    return 0


def cmd_grant(root, args):
    baseline = load_baseline(root)
    if baseline is None:
        raise RatchetError(f"no {BASELINE}; run `init` first")
    if args.lines <= 0:
        raise RatchetError("--lines must be positive")
    if not args.reason.strip() or not args.by.strip():
        raise RatchetError("grant requires --reason and --by (human-only)")
    grants = load_grants(root)
    before = int(baseline["groups"][args.group]["ceiling"]) + grants_by_group(active_grants(grants))[args.group]
    after = before + int(args.lines)
    if args.expires:
        try:
            datetime.date.fromisoformat(args.expires)
        except ValueError as exc:
            raise RatchetError("--expires must be YYYY-MM-DD") from exc
    item = {"ts": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "group": args.group, "lines": int(args.lines),
            "reason": args.reason.strip(), "by": args.by.strip(),
            "before": before, "after": after}
    if args.expires:
        item["expires"] = args.expires
    path = Path(root) / GRANTS
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(item, sort_keys=True) + "\n")
    print(f"source_ratchet: granted +{args.lines} {args.group} lines "
          f"(human-only; expires {args.expires or 'never'})")
    return 0


def cmd_rekey(root, args):
    baseline = load_baseline(root)
    if baseline is None:
        raise RatchetError(f"no {BASELINE}; run `init` first")
    old = Path(root) / args.old
    new = Path(root) / args.new
    frozen = baseline["files"].get(args.old)
    if frozen is None:
        raise RatchetError(f"{args.old} is not a frozen file")
    if not old.exists() and new.is_file():
        expected = _frozen_norm(root, args.old, frozen)
        actual = _norm_sha(new)
        if actual != expected:
            raise RatchetRefusal("rekey target content differs from the frozen file")
        baseline["files"][args.new] = dict(frozen)
        del baseline["files"][args.old]
        _write_json(Path(root) / BASELINE, baseline)
        print(f"source_ratchet: rekeyed {args.old} -> {args.new}")
        return 0
    if old.exists():
        raise RatchetRefusal("rekey refuses a copy; the old path still exists")
    raise RatchetError("rekey target is missing")


SKIP_SCAN_DIRS = {".git", ".vibeweaver", "dist", "build", "target", "coverage", "__pycache__"}


def _content_elsewhere(root, old, size, sha):
    root = Path(root)
    visited = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        real = os.path.realpath(dirpath)
        if real in visited:
            dirnames[:] = []
            continue
        visited.add(real)
        dirnames[:] = [d for d in dirnames if d not in SKIP_SCAN_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if rel == old:
                continue
            try:
                if path.is_symlink():
                    path = path.resolve()
                    if not path.is_file():
                        continue
                if size is not None and path.stat().st_size != int(size):
                    continue
                if _norm_sha(path) == sha:
                    return rel
            except OSError:
                continue
    return None


def cmd_prune(root, args):
    baseline = load_baseline(root)
    if baseline is None:
        raise RatchetError(f"no {BASELINE}; run `init` first")
    if args.path not in baseline["files"]:
        raise RatchetError(f"{args.path} is not a frozen file")
    if (Path(root) / args.path).exists():
        raise RatchetRefusal("prune refuses a path that still exists; use `rekey` for a rename")
    meta = baseline["files"][args.path]
    size = meta["raw_bytes"]
    sha = _frozen_norm(root, args.path, meta)
    other = _content_elsewhere(root, args.path, size, sha)
    if other is not None:
        raise RatchetRefusal(f"{args.path} content still exists at {other}; "
                             "use rekey or remove the moved copy")
    del baseline["files"][args.path]
    _write_json(Path(root) / BASELINE, baseline)
    print(f"source_ratchet: pruned deleted frozen path {args.path}")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--config", default=None, help="source_budget TOML path")
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

    p = sub.add_parser("grant")
    p.add_argument("--group", choices=GROUPS, required=True)
    p.add_argument("--lines", type=int, required=True)
    p.add_argument("--reason", default="")
    p.add_argument("--by", default="")
    p.add_argument("--expires", default="")
    p.set_defaults(func=cmd_grant)

    p = sub.add_parser("rekey")
    p.add_argument("--from", dest="old", required=True)
    p.add_argument("--to", dest="new", required=True)
    p.set_defaults(func=cmd_rekey)

    p = sub.add_parser("prune")
    p.add_argument("--path", required=True)
    p.set_defaults(func=cmd_prune)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"source_ratchet: ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        return args.func(root, args)
    except RatchetRefusal as exc:
        print(f"source_ratchet: REFUSED: {exc}", file=sys.stderr)
        return 1
    except (RatchetError, sb.BudgetError, OSError, ValueError) as exc:
        print(f"source_ratchet: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
