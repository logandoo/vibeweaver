#!/usr/bin/env python3
"""verify_release.py — verify a release bundle against release/MANIFEST.json.

Consumer command (from the release bundle root):

    python3 scripts/verify_release.py
    # MANIFEST OK N/N

Failure is closed: missing file, extra file, byte-count drift, digest drift,
duplicate/unsafe paths, or a bad schema exits 1 and names the path. A tag /
commit mismatch is also an error when the caller supplies an expected value.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

from make_release_manifest import SCHEMA_VERSION, payload_files

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_rel(p):
    if not isinstance(p, str) or not p:
        return False
    if "\\" in p or p.startswith("/") or p.startswith("../") or "/../" in p:
        return False
    if p in (".", ".."):
        return False
    return True


def verify_manifest(root, manifest, expected_tag=None, expected_commit=None):
    """Return a list of human-readable errors. Empty list == verified."""
    root = pathlib.Path(root)
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version is %r, expected %r" % (manifest.get("schema_version"), SCHEMA_VERSION))
    if expected_tag is not None and manifest.get("tag") != expected_tag:
        errors.append("tag is %r, expected %r" % (manifest.get("tag"), expected_tag))
    if expected_commit is not None and manifest.get("commit") != expected_commit:
        errors.append("commit is %r, expected %r" % (manifest.get("commit"), expected_commit))

    files = manifest.get("files")
    if not isinstance(files, list):
        return errors + ["files is not a list"]

    declared = {}
    for i, entry in enumerate(files):
        if not isinstance(entry, dict):
            errors.append("files[%d] is not an object" % i)
            continue
        rel = entry.get("path")
        if not _safe_rel(rel):
            errors.append("unsafe path: %r" % (rel,))
            continue
        if rel in declared:
            errors.append("duplicate path: %s" % rel)
            continue
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.match(digest):
            errors.append("bad sha256 for %s: %r" % (rel, digest))
            continue
        size = entry.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append("bad bytes for %s: %r" % (rel, size))
            continue
        declared[rel] = (digest, size)

    actual = set(payload_files(root))
    for rel in sorted(actual - set(declared)):
        errors.append("extra file not in manifest: %s" % rel)
    for rel in sorted(set(declared) - actual):
        errors.append("missing file: %s" % rel)

    for rel in sorted(set(declared) & actual):
        digest, size = declared[rel]
        p = root / rel
        try:
            got_size = p.stat().st_size
        except OSError as e:
            errors.append("missing file: %s (%s)" % (rel, e))
            continue
        if got_size != size:
            errors.append("bytes mismatch for %s: manifest=%d actual=%d" % (rel, size, got_size))
            continue
        got_digest = _sha256(p)
        if got_digest != digest:
            errors.append("sha256 mismatch for %s: manifest=%s actual=%s" % (rel, digest, got_digest))
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify a release bundle against its manifest")
    ap.add_argument("--root", default=".", help="bundle root (holds vibeweaver/ and release/)")
    ap.add_argument("--manifest", default="", help="manifest path (default: <root>/release/MANIFEST.json)")
    ap.add_argument("--tag", default="", help="expected tag (optional)")
    ap.add_argument("--commit", default="", help="expected commit (optional)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    mp = pathlib.Path(args.manifest) if args.manifest else root / "release" / "MANIFEST.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("MANIFEST FAILED: %s not found" % mp, file=sys.stderr)
        return 1
    except (OSError, ValueError) as e:
        print("MANIFEST FAILED: cannot read %s: %s" % (mp, e), file=sys.stderr)
        return 1

    errors = verify_manifest(
        root, manifest,
        expected_tag=args.tag or None,
        expected_commit=args.commit or None,
    )
    total = len(manifest.get("files", [])) if isinstance(manifest, dict) else 0
    if args.json:
        print(json.dumps({"ok": not errors, "total": total, "errors": errors}, indent=2))
    elif errors:
        print("MANIFEST FAILED: %d error(s) against %s" % (len(errors), mp), file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
    else:
        print("MANIFEST OK %d/%d" % (total, total))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
