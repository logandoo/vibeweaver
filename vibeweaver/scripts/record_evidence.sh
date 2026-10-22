#!/usr/bin/env bash
# record_evidence.sh — the ONLY sanctioned writer of machine values into
# tests/verification_log.md (G5, W18): git HEAD, UTC time and file hashes are
# CAPTURED here and copied verbatim — hand-typed hex is the incident class
# (a 63-char sha reached the log and only an adversarial review caught it).
#
#   bash scripts/record_evidence.sh --note "what this evidence shows"
#   bash scripts/record_evidence.sh --note "…" --hash tests/w18/final-build.log
#
# Appends ONE `- record:` line per invocation. Never edit the line afterwards.
set -euo pipefail
# run from the PROJECT root (cwd is the project — like assert_artifacts.py
# run from a project copy); paths below are project-relative.
NOTE=""; HASHES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --note) NOTE="${2:-}"; shift 2 ;;
    --hash) HASHES="$HASHES ${2:-}"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$NOTE" ] || { echo "record_evidence.sh: --note is required" >&2; exit 2; }
# one line per invocation: newlines in --note could smuggle fake log entries
# (- iter N PASS / - test-change: / - secret-approved:) through the sanctioned
# machine-writer channel (review A).
NOTE=$(printf %s "$NOTE" | tr '\n\r' '  ')
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
HEAD_SHA=$(git rev-parse HEAD 2>/dev/null || echo "no-git")
LINE="- record: ${TS} | HEAD ${HEAD_SHA}"
for h in $HASHES; do
  [ -f "$h" ] || { echo "record_evidence.sh: no such file: $h" >&2; exit 2; }
  if command -v sha256sum >/dev/null 2>&1; then D=$(sha256sum "$h" | cut -d' ' -f1); else D=$(shasum -a 256 "$h" | cut -d' ' -f1); fi
  LINE="$LINE | $h sha256=$D"
done
LINE="$LINE | note: $NOTE"
mkdir -p tests
printf '%s\n' "$LINE" >> tests/verification_log.md
echo "recorded: $LINE"
