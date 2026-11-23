#!/usr/bin/env bash
# make_review_package.sh — assemble ONE self-contained file for an A4.9
# reviewer (T1, W18): log slice + stat + -U10 diff for a commit range.
# Reviewers get a FILE, never a raw diff dump to reconstruct (漏字段 was the
# manual-assembly incident class).
#
#   bash scripts/make_review_package.sh <BASE> <HEAD> [outfile] [--max-bytes N]
#
# If the package exceeds --max-bytes (default 512 KiB), the committed outfile
# becomes a small index; the full package is archived under
# .vibeweaver/artifacts/review/ with its sha256. No human approval is needed.
set -euo pipefail

MAX_BYTES=524288
POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --max-bytes)
      [ "$#" -ge 2 ] || { echo "make_review_package.sh: --max-bytes needs a value" >&2; exit 2; }
      MAX_BYTES="$2"; shift 2 ;;
    --max-bytes=*)
      MAX_BYTES="${1#*=}"; shift ;;
    -h|--help)
      echo "usage: make_review_package.sh <BASE> <HEAD> [outfile] [--max-bytes N]" >&2
      exit 0 ;;
    *)
      POSITIONAL+=("$1"); shift ;;
  esac
done
case "$MAX_BYTES" in
  ''|*[!0-9]*) echo "make_review_package.sh: --max-bytes must be a positive integer" >&2; exit 2 ;;
esac
[ "$MAX_BYTES" -gt 0 ] || { echo "make_review_package.sh: --max-bytes must be positive" >&2; exit 2; }
if [ "$MAX_BYTES" -gt 524288 ]; then
  echo "make_review_package.sh: --max-bytes capped at 524288 (artifact per-file cap)" >&2
  MAX_BYTES=524288
fi

BASE="${POSITIONAL[0]:?usage: make_review_package.sh <BASE> <HEAD> [outfile]}"
HEAD_SHA="${POSITIONAL[1]:?usage: make_review_package.sh <BASE> <HEAD> [outfile]}"
OUT="${POSITIONAL[2]:-tests/review_package.md}"
cd "$(dirname "$0")/.."
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "${TMPDIR:-/tmp}/review_package.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
{
  echo "# Review Package — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "Range: ${BASE}..${HEAD_SHA}"
  echo
  echo "## Task context"
  echo "- acceptance: tests/acceptance.md (criteria the change must satisfy)"
  echo "- iteration log: tests/verification_log.md (claims under review)"
  echo
  echo "## git log --oneline (the range's commits)"
  git log --oneline "${BASE}..${HEAD_SHA}"
  echo
  echo "## git diff --stat"
  git diff --stat "${BASE}..${HEAD_SHA}"
  echo
  echo "## git diff -U10"
  git diff -U10 "${BASE}..${HEAD_SHA}"
  echo
  echo "## Uncommitted / untracked (if any)"
  git status --porcelain || true
} > "$TMP"
SIZE="$(wc -c < "$TMP" | tr -d ' ')"
if [ "$SIZE" -le "$MAX_BYTES" ]; then
  mv "$TMP" "$OUT"
  echo "review package written: $OUT ($(wc -l < "$OUT") lines, $SIZE bytes)"
else
  python3 scripts/artifact_budget.py --root . review-index \
    --input "$TMP" --index "$OUT" \
    --archive-dir .vibeweaver/artifacts/review --max-bytes "$MAX_BYTES"
  echo "review package indexed: $OUT (full $SIZE bytes archived under .vibeweaver/artifacts/review)"
fi
