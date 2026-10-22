#!/usr/bin/env bash
# make_review_package.sh — assemble ONE self-contained file for an A4.9
# reviewer (T1, W18): log slice + stat + -U10 diff for a commit range.
# Reviewers get a FILE, never a raw diff dump to reconstruct (漏字段 was the
# manual-assembly incident class).
#
#   bash scripts/make_review_package.sh <BASE> <HEAD> [outfile]
set -euo pipefail
BASE="${1:?usage: make_review_package.sh <BASE> <HEAD> [outfile]}"
HEAD_SHA="${2:?usage: make_review_package.sh <BASE> <HEAD> [outfile]}"
OUT="${3:-tests/review_package.md}"
cd "$(dirname "$0")/.."
mkdir -p "$(dirname "$OUT")"
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
} > "$OUT"
echo "review package written: $OUT ($(wc -l < "$OUT") lines)"
