#!/usr/bin/env python3
"""make_release_manifest.py — deterministic release manifest (PLAN W0 Task 1).

The manifest is the consumer-verifiable integrity root for a release bundle:

    release/MANIFEST.json
    {
      "schema_version": 1,
      "tag": "w18.2",
      "commit": "<40-hex>",
      "files": [{"path": "vibeweaver/SKILL.md", "sha256": "...", "bytes": 48970}, ...]
    }

Paths are POSIX-relative to the bundle root (the directory that holds
`vibeweaver/` and `release/`). The dev tree (payload at its root) is also
supported so the same functions can be exercised before a release.
"""
import argparse
import hashlib
import json
import pathlib
import sys

SCHEMA_VERSION = 1

# Files that are delivered to a consumer. Keep this list explicit: a manifest
# that silently grows to include tests/memory is both a leak and a moving
# verification target.
TOP_LEVEL_FILES = {
    "SKILL.md",
    "COMPLETION_GATE.md",
    "CODING_PRINCIPLES.md",
    "ENGINEERING_STD.md",
    "REFERENCE.md",
    "APPENDIX.md",
    "MEMORY_TEMPLATES.md",
    "MEMORY_RULES.md",
    "TESTING_PROTOCOLS.md",
    "WORKFLOWS_EXTENDED.md",
    "VERIFICATION_UPGRADES.md",
    "install.sh",
    "install.bat",
    "vibeweaver-gate.js",
    "vibeweaver-audit.js",
}
SCRIPT_SUFFIXES = {".py", ".js", ".mjs", ".sh", ".bat"}
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
    "memory",
    "tests",
    "release",
    "dist",
    "build",
}
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}


def _payload_prefix(root):
    """"vibeweaver/" in the release repo layout, "" in the dev tree."""
    nested = root / "vibeweaver" / "SKILL.md"
    if nested.is_file():
        return "vibeweaver/"
    return ""


def _included(rel, prefix):
    """Return True when a POSIX-relative payload path belongs in the manifest."""
    if not rel:
        return False
    parts = rel.split("/")
    if any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return False
    name = parts[-1]
    if name in EXCLUDED_NAMES or name.startswith("."):
        return False
    if pathlib.PurePosixPath(rel).suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if prefix:
        if not rel.startswith(prefix):
            return False
        inner = rel[len(prefix):]
        if not inner or "/" in inner.split("/")[0] and not inner.startswith("vibeweaver-mini/"):
            # only direct payload files, scripts/, and the sibling mini tree
            pass
        if inner.startswith("vibeweaver-mini/"):
            return True
        if "/" not in inner:
            return inner in TOP_LEVEL_FILES
        if inner.startswith("scripts/"):
            return pathlib.PurePosixPath(inner).suffix.lower() in SCRIPT_SUFFIXES
        return False
    # dev layout: payload files live at the root
    if "/" not in rel:
        return rel in TOP_LEVEL_FILES
    if rel.startswith("scripts/"):
        return pathlib.PurePosixPath(rel).suffix.lower() in SCRIPT_SUFFIXES
    if rel.startswith("vibeweaver-mini/"):
        return True
    return False


def payload_files(root):
    """Sorted POSIX-relative files covered by the release manifest."""
    root = pathlib.Path(root)
    prefix = _payload_prefix(root)
    out = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if _included(rel, prefix):
            out.append(rel)
    return sorted(set(out))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_manifest(root, tag, commit):
    """Build the manifest dict. Pure over the tree; no clock, no host data."""
    root = pathlib.Path(root)
    files = []
    for rel in payload_files(root):
        p = root / rel
        files.append({"path": rel, "sha256": _sha256(p), "bytes": p.stat().st_size})
    return {
        "schema_version": SCHEMA_VERSION,
        "tag": str(tag),
        "commit": str(commit),
        "files": files,
    }


def _default_commit(root):
    """Best-effort HEAD lookup; an explicit --commit always wins."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate release/MANIFEST.json")
    ap.add_argument("--root", default=".", help="bundle root (holds vibeweaver/ or the dev payload)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--commit", default="", help="commit SHA (default: git HEAD)")
    ap.add_argument("--out", default="", help="output path (default: <root>/release/MANIFEST.json)")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    commit = args.commit or _default_commit(root)
    manifest = make_manifest(root, args.tag, commit)
    if not manifest["files"]:
        print("MANIFEST FAILED: no payload files found under %s" % root, file=sys.stderr)
        return 1
    out = pathlib.Path(args.out) if args.out else root / "release" / "MANIFEST.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    sha_line = "%s  %s\n" % (digest, out.name)
    (out.parent / "MANIFEST.sha256").write_text(sha_line, encoding="utf-8")
    print("MANIFEST WROTE %d files -> %s (sha256=%s)" % (len(manifest["files"]), out, digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
