#!/usr/bin/env python3
"""artifact_budget.py — caps for generated evidence, with automatic indexing.

Groups (defaults):
  review      tests/review_package*.md       512 KiB/file, 1 MiB total
  logs        tests/**/*.log                 5 MiB/file,  50 MiB total
  trajectory  tests/eval/**/trajectory.json  2 MiB/file, 100 MiB total
  media       tests/**/*.{png,webm,wav,mp4,mp3} 5 MiB/file, 50 MiB total

Existing over-cap artifacts are frozen at adoption; they may shrink, never
grow. New artifacts must fit the caps. A review package over the cap is
replaced by a small index plus an external (ignored) archive; no human
approval is involved.

Exit codes: 0 pass/budget; 1 cap violation; 2 config/discovery/I-O.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import posixpath
import subprocess
import sys

try:
    from git_trust import run_git as _trusted_git
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from git_trust import run_git as _trusted_git

BASELINE = "tests/artifact_baseline.json"
MIGRATIONS = "tests/artifact_migrations.jsonl"
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".webm", ".wav", ".mp4", ".mov", ".m4v", ".mp3"}
GROUPS = {
    "review": {"per_file": 512 * 1024, "total": 1024 * 1024},
    "logs": {"per_file": 5 * 1024 * 1024, "total": 50 * 1024 * 1024},
    "trajectory": {"per_file": 2 * 1024 * 1024, "total": 100 * 1024 * 1024},
    "media": {"per_file": 5 * 1024 * 1024, "total": 50 * 1024 * 1024},
}


class ArtifactError(Exception):
    pass


class ArtifactRefusal(ArtifactError):
    """A policy refusal (exit 1), distinct from an operational error (exit 2)."""


def _git(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise ArtifactError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def _git_bytes(root, *args):
    try:
        p = _trusted_git(root, *args, timeout=30, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise ArtifactError(f"git {' '.join(args)} failed: {exc}") from exc
    return p.returncode, p.stdout, p.stderr

def _sha(path):
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
        raise ArtifactError(f"{rel} must be a regular file, not a symlink")
    rc, _, _ = _git(root, "ls-files", "--error-unmatch", rel)
    if rc != 0:
        raise ArtifactError(f"{rel} is not tracked — commit the baseline before --final")
    rc, actual, _ = _git(root, "hash-object", "--path", _repo_rel(root, rel), "--", rel)
    rc2, head, _ = _git(root, "rev-parse", f"HEAD:{_repo_rel(root, rel)}")
    if rc != 0 or rc2 != 0:
        raise ArtifactError(f"{rel} is not readable/clean from HEAD — commit it before --final")
    if actual != head:
        raise ArtifactError(f"{rel} differs from HEAD (uncommitted or assume-unchanged); "
                            "commit it before --final")


def _same_commit(root, a, b):
    _, ra, _ = _git(root, "rev-parse", a)
    _, rb, _ = _git(root, "rev-parse", b)
    return ra == rb


def _first_baseline_commit(root):
    rc, out, _ = _git(root, "log", "--reverse", "--diff-filter=A", "--format=%H", "--", BASELINE)
    if rc != 0 or not out.strip():
        return None
    return out.splitlines()[0].strip()


def _base_baseline(root, ref):
    rc, raw, _ = _git(root, "show", f"{ref}:{_repo_rel(root, BASELINE)}")
    if rc != 0:
        raise ArtifactError(f"--base {ref!r} has no {BASELINE}; pin the ADOPTION commit")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ArtifactError(f"--base {ref!r}: baseline is unparseable") from exc


def _load_migrations(root, allow_missing=True):
    path = Path(root) / MIGRATIONS
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ArtifactError(f"cannot read {MIGRATIONS}: {exc}") from exc
    out = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError as exc:
            raise ArtifactError(f"{MIGRATIONS}:{i}: invalid JSON") from exc
        if not isinstance(item, dict) or item.get("group") not in GROUPS:
            raise ArtifactError(f"{MIGRATIONS}:{i}: invalid group")
        if not item.get("by") or not item.get("reason"):
            raise ArtifactError(f"{MIGRATIONS}:{i}: by/reason required")
        for key in ("before_ceiling", "after_ceiling"):
            if not isinstance(item.get(key), int):
                raise ArtifactError(f"{MIGRATIONS}:{i}: {key} must be an integer")
        if not isinstance(item.get("added_frozen"), list):
            raise ArtifactError(f"{MIGRATIONS}:{i}: added_frozen must be a list")
        out.append(item)
    return out


def _base_migrations(root, ref):
    rc, raw, _ = _git(root, "show", f"{ref}:{_repo_rel(root, MIGRATIONS)}")
    out = []
    if raw:
        for line in raw.splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as exc:
                    raise ArtifactError(f"--base {ref!r}: migrations are unparseable") from exc
    return out


def _migration_covers(base, current, group, ceiling, before, path=None):
    for item in current[len(base):]:
        if item.get("group") != group:
            continue
        if int(item.get("before_ceiling", -1)) != int(before):
            continue
        if int(item.get("after_ceiling", 0)) < ceiling:
            continue
        if path is None or path in item.get("added_frozen", []):
            return True
    return False


def classify(rel, aliases=False):
    base = posixpath.basename(rel).lower()
    low = rel.lower()
    if low.startswith("tests/") and base.endswith(".md") and (
            base.startswith("review_package") or (aliases and "review" in base)):
        return "review"
    if low.startswith("tests/") and base.endswith(".log"):
        return "logs"
    if low.startswith("tests/eval/") and base == "trajectory.json":
        return "trajectory"
    if low.startswith("tests/") and posixpath.splitext(base)[1] in MEDIA_EXTS:
        return "media"
    return None


def unclassified_review(root, aliases=False):
    if aliases:
        return []
    root = Path(root)
    rc, out, _ = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    found = []
    if rc == 0:
        for raw in out.split("\0"):
            if not raw:
                continue
            rel = raw.replace(os.sep, "/")
            base = posixpath.basename(rel).lower()
            if (rel.startswith("tests/") and base.endswith(".md")
                    and "review" in base and classify(rel, aliases=True) is not None
                    and classify(rel) is None):
                try:
                    found.append({"path": rel, "bytes": (root / rel).stat().st_size})
                except OSError:
                    continue
    return sorted(found, key=lambda x: x["path"])


def discover(root, aliases=False):
    root = Path(root)
    rc, out, err = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--")
    if rc != 0:
        raise ArtifactError("git discovery failed" + (f": {err}" if err else ""))
    files = []
    seen = set()
    for raw in out.split("\0"):
        if not raw:
            continue
        rel = raw.replace(os.sep, "/")
        if rel in seen:
            continue
        seen.add(rel)
        group = classify(rel, aliases=aliases)
        if group is None:
            continue
        path = root / rel
        try:
            if not path.is_file() or path.is_symlink():
                continue
            size = path.stat().st_size
        except OSError as exc:
            raise ArtifactError(f"cannot stat {rel}: {exc}") from exc
        files.append({"path": rel, "group": group, "bytes": size})
    files.sort(key=lambda x: x["path"])
    return files


def _load_baseline(root, allow_missing=False):
    path = Path(root) / BASELINE
    if path.is_symlink():
        raise ArtifactError(f"{BASELINE} must be a regular file, not a symlink")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = None
    except (OSError, ValueError) as exc:
        raise ArtifactError(f"cannot read {BASELINE}: {exc}") from exc
    if data is None:
        if allow_missing:
            return None
        rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
        if rc == 0:
            raise ArtifactError(
                f"{BASELINE} is tracked in HEAD but missing on disk — restore it; "
                "delete-and-re-record would launder frozen artifacts")
        return None
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ArtifactError(f"{BASELINE} has an unsupported schema")
    for g in GROUPS:
        entry = data.get("groups", {}).get(g)
        if not isinstance(entry, dict) or "ceiling" not in entry:
            raise ArtifactError(f"{BASELINE} group `{g}` has no ceiling")
    if not isinstance(data.get("files"), dict):
        raise ArtifactError(f"{BASELINE} missing `files`")
    for path, meta in data["files"].items():
        if (not isinstance(meta, dict) or not isinstance(meta.get("bytes"), int)
                or not isinstance(meta.get("sha256"), str) or not meta.get("sha256")):
            raise ArtifactError(f"{BASELINE} file `{path}` has incomplete freeze metadata")
    return data


def _write_baseline(root, data):
    path = Path(root) / BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=1, sort_keys=True) + "\n")
    os.replace(str(tmp), str(path))


def totals(files):
    out = {g: 0 for g in GROUPS}
    for item in files:
        out[item["group"]] += int(item["bytes"])
    return out


def symlink_artifacts(root):
    rc, out, _ = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    found = []
    if rc == 0:
        for raw in out.split("\0"):
            if not raw:
                continue
            rel = raw.replace(os.sep, "/")
            if classify(rel, aliases=True) and (Path(root) / rel).is_symlink():
                found.append(rel)
    return sorted(set(found))


def cmd_init(root, args):
    if (Path(root) / BASELINE).exists():
        raise ArtifactError(f"{BASELINE} already exists; use `tighten`")
    rc, _, _ = _git(root, "cat-file", "-e", "HEAD:" + _repo_rel(root, BASELINE))
    if rc == 0:
        raise ArtifactError(f"{BASELINE} is tracked in HEAD but missing on disk; restore it")
    rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
    if hist.strip():
        raise ArtifactError(f"{BASELINE} exists in repository history; re-init is not allowed")
    files = discover(root)
    current = totals(files)
    frozen = {}
    for item in files:
        cap = GROUPS[item["group"]]["per_file"]
        if item["bytes"] > cap:
            frozen[item["path"]] = {
                "bytes": item["bytes"],
                "sha256": _sha(Path(root) / item["path"]),
                "sha256_norm": _norm_sha(Path(root) / item["path"]),
            }
    groups = {}
    for g, cfg in GROUPS.items():
        # Adoption headroom: if legacy already exceeds the total cap, allow one
        # new artifact of up to the per-file cap before the group is full.
        # `tighten` drops this extra headroom once the legacy shrinks.
        headroom = cfg["per_file"] if current[g] > cfg["total"] else 0
        groups[g] = {
            "per_file": cfg["per_file"],
            "total": cfg["total"],
            "ceiling": max(current[g], cfg["total"]) + headroom,
        }
    data = {
        "version": 1,
        "groups": groups,
        "files": frozen,
        "recorded_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "reason": args.reason or "adoption: freeze existing over-cap artifacts",
        "classifier": "review_package_v1",
    }
    _write_baseline(root, data)
    print(f"artifact_budget: initialized {BASELINE} "
          f"(files={len(files)} frozen={len(frozen)})")
    return 0


def cmd_budget(root, args):
    baseline = _load_baseline(root, allow_missing=True)
    aliases = bool(baseline and baseline.get("classifier") == "review_aliases_v1")
    files = discover(root, aliases=aliases)
    current = totals(files)
    data = {"schema": "artifact-budget/1",
            "result": "NO_BASELINE" if baseline is None else "PASS",
            "groups": {}, "near_cap": [], "unclassified_review": unclassified_review(root, aliases)}
    if baseline is not None:
        for g, cfg in GROUPS.items():
            ceiling = int(baseline["groups"][g]["ceiling"])
            data["groups"][g] = {"current": current[g], "ceiling": ceiling,
                                 "headroom": ceiling - current[g]}
        for item in files:
            limit = GROUPS[item["group"]]["per_file"]
            frozen = baseline["files"].get(item["path"])
            if frozen is not None:
                limit = int(frozen["bytes"])
            if item["bytes"] >= int(limit * 0.8):
                data["near_cap"].append({"path": item["path"], "bytes": item["bytes"], "limit": limit})
        data["near_cap"].sort(key=lambda x: (-x["bytes"], x["path"]))
    if args.format == "json":
        print(json.dumps(data, indent=1, sort_keys=True))
    else:
        print(f"ARTIFACT-BUDGET result={data['result']} files={len(files)}")
        for g in GROUPS:
            if g in data["groups"]:
                x = data["groups"][g]
                print(f"{g}: {x['current']}/{x['ceiling']} (headroom {x['headroom']})")
        for item in data["near_cap"][:20]:
            print(f"NEAR-CAP {item['path']} {item['bytes']}/{item['limit']}")
        for item in data["unclassified_review"]:
            print(f"WARN unclassified review-like artifact {item['path']} "
                  f"({item['bytes']} bytes); migrate the classifier in a human-authorized baseline update")
    return 0


def _violations(baseline, files, current):
    out = []
    for g, cfg in GROUPS.items():
        ceiling = int(baseline["groups"][g]["ceiling"])
        if current[g] > ceiling:
            out.append(f"{g} group ceiling exceeded: {current[g]} > {ceiling} bytes")
    for item in files:
        frozen = baseline["files"].get(item["path"])
        if frozen is not None:
            limit = int(frozen["bytes"])
            if item["bytes"] > limit:
                out.append(f"{item['path']} is frozen at {limit} bytes (now {item['bytes']}); "
                           "frozen artifacts may shrink, never grow")
        elif item["bytes"] > GROUPS[item["group"]]["per_file"]:
            out.append(f"{item['path']} is over the {item['group']} per-file cap: "
                       f"{item['bytes']} > {GROUPS[item['group']]['per_file']} bytes")
    current_paths = {item["path"] for item in files}
    for path in baseline["files"]:
        if path not in current_paths:
            out.append(f"{path} is a frozen artifact missing from the current scan; "
                       "move it back into scope or run `prune` after a real deletion")
    return out


def cmd_check(root, args):
    baseline = _load_baseline(root, allow_missing=True)
    if baseline is None:
        rc, hist, _ = _git(root, "log", "--all", "--format=%H", "--", BASELINE)
        if hist.strip():
            print("artifact_budget: baseline was adopted then deleted; restore it from history")
            return 2
        if args.final and not args.adopt_optional:
            print("artifact_budget: no baseline — run `init` before completion (fail-closed)")
            return 2
        print("artifact_budget: WARN no baseline — project has not adopted the artifact budget")
        return 0
    rc, shallow, _ = _git(root, "rev-parse", "--is-shallow-repository")
    if rc != 0 or shallow.strip() not in ("true", "false"):
        raise ArtifactError("cannot verify repository depth (shallow probe failed); fail-closed")
    if shallow.strip() == "true":
        raise ArtifactError("artifact budget needs full history (shallow clone); run `git fetch --unshallow`")
    if args.final:
        _tracked_clean(root, BASELINE)
        if (Path(root) / MIGRATIONS).exists():
            _tracked_clean(root, MIGRATIONS)
    aliases = baseline.get("classifier") == "review_aliases_v1"
    files = discover(root, aliases=aliases)
    current = totals(files)
    violations = _violations(baseline, files, current)
    for rel in symlink_artifacts(root):
        violations.append(f"{rel} is a symlink artifact; the cap cannot measure it (fail-closed)")
    adoption = _first_baseline_commit(root)
    base_ref = args.base or adoption
    if args.base:
        if adoption is None:
            raise ArtifactError("--base is set but the baseline has no adoption commit")
        if not _same_commit(root, args.base, adoption):
            raise ArtifactError("--base must be the first commit that adds the baseline "
                                "(the adoption commit), not a later ancestor")
        if _same_commit(root, args.base, "HEAD"):
            raise ArtifactError("--base must be a strict ancestor, not HEAD")
    if base_ref and not _same_commit(root, base_ref, "HEAD"):
        rc, _, _ = _git(root, "merge-base", "--is-ancestor", base_ref, "HEAD")
        if rc != 0:
            raise ArtifactError(f"--base {base_ref!r} is not an ancestor of HEAD")
        base = _base_baseline(root, base_ref)
        migrations = _load_migrations(root)
        base_migrations = _base_migrations(root, base_ref)
        if migrations[:len(base_migrations)] != base_migrations:
            violations.append("migration log is not append-only since --base")
        for g in GROUPS:
            old = int(base.get("groups", {}).get(g, {}).get("ceiling", 0))
            new = int(baseline["groups"][g]["ceiling"])
            if new > old and not _migration_covers(base_migrations, migrations, g, new, old):
                violations.append(f"{g} base ceiling was raised ({old} -> {new}) without a matching migration")
            for key in ("per_file", "total"):
                old_k = int(base.get("groups", {}).get(g, {}).get(key, 0))
                new_k = int(baseline["groups"][g].get(key, 0))
                if new_k > old_k:
                    violations.append(f"{g}.{key} was raised above --base")
        base_files = base.get("files", {}) if isinstance(base.get("files"), dict) else {}
        for path, meta in baseline["files"].items():
            prior = base_files.get(path)
            if prior is None:
                if not any(path in m.get("added_frozen", []) for m in migrations[len(base_migrations):]):
                    violations.append(f"{path} is a new frozen entry; no migration since --base adds it")
            elif int(meta.get("bytes", 0)) > int(prior.get("bytes", 0)):
                violations.append(f"{path} grew past its base frozen size "
                                  f"({prior.get('bytes')} -> {meta.get('bytes')})")
    unclassified = unclassified_review(root, aliases)
    if args.format == "json":
        payload = {"schema": "artifact-budget/1",
                   "result": "FAIL" if violations else "PASS",
                   "unclassified_review": unclassified,
                   "groups": {g: {"current": current[g],
                                  "ceiling": int(baseline["groups"][g]["ceiling"])}
                              for g in GROUPS},
                   "violations": violations}
        text = json.dumps(payload, indent=1, sort_keys=True)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
    else:
        print(f"ARTIFACT-BUDGET result={'FAIL' if violations else 'PASS'}")
        for v in violations:
            print("  - " + v)
        if violations:
            print("  fix: shrink, archive, or regenerate a smaller artifact; "
                  "review packages over cap become index + external archive")
        for item in unclassified:
            print(f"WARN unclassified review-like artifact {item['path']} "
                  f"({item['bytes']} bytes); migrate the classifier in a human-authorized baseline update")
    return 1 if violations else 0


def cmd_tighten(root, args):
    baseline = _load_baseline(root)
    if baseline is None:
        raise ArtifactError(f"no {BASELINE}; run `init` first")
    files = discover(root, aliases=baseline.get("classifier") == "review_aliases_v1")
    current = totals(files)
    for g, cfg in GROUPS.items():
        proposed = max(current[g], cfg["total"])
        baseline["groups"][g]["ceiling"] = min(int(baseline["groups"][g]["ceiling"]), proposed)
    for path in list(baseline["files"]):
        item = next((f for f in files if f["path"] == path), None)
        if item is None:
            # Preserve the freeze; a real deletion uses `prune`, a move must stay
            # visible in the artifact groups.
            continue
        if item["bytes"] <= GROUPS[item["group"]]["per_file"]:
            # No longer over the applicable cap: drop the grandfather key.
            del baseline["files"][path]
            continue
        if item["bytes"] <= int(baseline["files"][path]["bytes"]):
            baseline["files"][path]["bytes"] = item["bytes"]
            baseline["files"][path]["sha256"] = _sha(Path(root) / path)
    _write_baseline(root, baseline)
    print(f"artifact_budget: tightened {BASELINE} (files={len(files)})")
    return 0


def _summary(text, marker="## git diff -U10"):
    if marker in text:
        return text.split(marker, 1)[0].rstrip() + "\n"
    return "\n".join(text.splitlines()[:200]).rstrip() + "\n"


def cmd_review_index(root, args):
    source = Path(args.input)
    if not source.is_file():
        raise ArtifactError(f"review package input not found: {source}")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    archive_dir = Path(args.archive_dir)
    if not archive_dir.is_absolute():
        archive_dir = Path(root) / archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / (digest + ".md")
    archive.write_bytes(raw)
    try:
        display = str(archive.relative_to(Path(root)))
    except ValueError:
        display = str(archive)
    text = raw.decode("utf-8", "replace")
    summary = _summary(text)
    header = (
        "# Review package index\n\n"
        f"- full_package: {display}\n"
        f"- size: {len(raw)} bytes\n"
        f"- sha256: {digest}\n"
        "- note: the full diff is archived outside the committed tree; "
        "this index is the committed evidence anchor.\n\n"
    )
    limit = max(256, int(args.max_bytes))
    room = max(64, limit - len(header.encode("utf-8")) - 32)
    body = summary.encode("utf-8")[:room].decode("utf-8", "ignore")
    index = Path(args.index)
    if not index.is_absolute():
        index = Path(root) / index
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(header + body + "\n", encoding="utf-8")
    if index.stat().st_size > limit:
        index.write_text(header, encoding="utf-8")
    print(f"artifact_budget: review package indexed: {index} "
          f"({index.stat().st_size} bytes; full {len(raw)} bytes sha256={digest[:12]}...)")
    return 0


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
    baseline = _load_baseline(root)
    if baseline is None:
        raise ArtifactError(f"no {BASELINE}; run `init` first")
    if args.path not in baseline["files"]:
        raise ArtifactError(f"{args.path} is not a frozen artifact")
    if (Path(root) / args.path).exists():
        raise ArtifactRefusal("prune refuses a path that still exists")
    meta = baseline["files"][args.path]
    size = int(meta["bytes"])
    sha = _frozen_norm(root, args.path, meta)
    other = _content_elsewhere(root, args.path, size, sha)
    if other is not None:
        raise ArtifactRefusal(f"{args.path} content still exists at {other}; "
                              "move it back or remove the moved copy")
    del baseline["files"][args.path]
    _write_baseline(root, baseline)
    print(f"artifact_budget: pruned deleted frozen artifact {args.path}")
    return 0


def cmd_reclassify(root, args):
    baseline = _load_baseline(root)
    if baseline is None:
        raise ArtifactError(f"no {BASELINE}; run `init` first")
    if not args.by.strip() or not args.reason.strip():
        raise ArtifactError("reclassify requires --by and --reason (human-authorized baseline migration)")
    files = discover(root, aliases=True)
    current = totals(files)
    cfg = GROUPS["review"]
    added = []
    for item in files:
        if item["group"] != "review":
            continue
        frozen = baseline["files"].get(item["path"])
        if item["bytes"] > cfg["per_file"]:
            baseline["files"][item["path"]] = {
                "bytes": item["bytes"],
                "sha256": _sha(Path(root) / item["path"]),
                "sha256_norm": _norm_sha(Path(root) / item["path"]),
            }
            if frozen is None:
                added.append(item["path"])
        elif frozen is not None:
            del baseline["files"][item["path"]]
    old_ceiling = int(baseline["groups"]["review"]["ceiling"])
    new_ceiling = max(current["review"], cfg["total"]) + cfg["per_file"]
    if new_ceiling < old_ceiling:
        new_ceiling = old_ceiling
    baseline["groups"]["review"]["ceiling"] = new_ceiling
    baseline["classifier"] = "review_aliases_v1"
    record = {
        "ts": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "by": args.by.strip(),
        "reason": args.reason.strip(),
        "group": "review",
        "classifier": "review_aliases_v1",
        "before_ceiling": old_ceiling,
        "after_ceiling": new_ceiling,
        "after_total": current["review"],
        "added_frozen": sorted(added),
    }
    path = Path(root) / MIGRATIONS
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    _write_baseline(root, baseline)
    print(f"artifact_budget: reclassified review aliases "
          f"(review ceiling {old_ceiling} -> {new_ceiling}, frozen added {len(added)})")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="project root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
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

    p = sub.add_parser("review-index")
    p.add_argument("--input", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--archive-dir", required=True)
    p.add_argument("--max-bytes", type=int, default=512 * 1024)
    p.set_defaults(func=cmd_review_index)

    p = sub.add_parser("prune")
    p.add_argument("--path", required=True)
    p.set_defaults(func=cmd_prune)

    p = sub.add_parser("reclassify")
    p.add_argument("--by", default="")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_reclassify)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"artifact_budget: ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        return args.func(root, args)
    except ArtifactRefusal as exc:
        print(f"artifact_budget: REFUSED: {exc}", file=sys.stderr)
        return 1
    except (ArtifactError, OSError, ValueError) as exc:
        print(f"artifact_budget: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
