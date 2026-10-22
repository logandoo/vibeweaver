#!/usr/bin/env python3
"""Mutation sweep for verify_release.py (W1 Task 20). Each mutant must be killed."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts" / "verify_release.py"
MUTANTS = [
    ('if rel in declared:', 'if False:'),
    ('if got_size != size:', 'if False:'),
    ('if got_digest != digest:', 'if False:'),
    ('errors.append("extra file not in manifest: %s" % rel)', 'pass'),
    ('errors.append("missing file: %s" % rel)', 'pass'),
    ('if expected_tag is not None and manifest.get("tag") != expected_tag:', 'if False:'),
    ('if manifest.get("schema_version") != SCHEMA_VERSION:', 'if False:'),
    ('if not _safe_rel(rel):', 'if False:'),
    ('if not isinstance(digest, str) or not SHA256_RE.match(digest):', 'if False:'),
    ('if not isinstance(size, int) or isinstance(size, bool) or size < 0:', 'if False:'),
]


def main():
    original = TARGET.read_text(encoding="utf-8")
    killed = 0
    try:
        for old, new in MUTANTS:
            if old not in original:
                print("MISSED pattern: " + old)
                continue
            TARGET.write_text(original.replace(old, new, 1), encoding="utf-8")
            r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_release_manifest", "-q"],
                               cwd=ROOT, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                killed += 1
            else:
                print("SURVIVED: " + old)
    finally:
        TARGET.write_text(original, encoding="utf-8")
    score = killed / len(MUTANTS)
    print(f"MUTATION-SWEEP {killed}/{len(MUTANTS)} killed score={score:.0%}")
    return 0 if score >= 0.9 else 1


if __name__ == "__main__":
    sys.exit(main())
