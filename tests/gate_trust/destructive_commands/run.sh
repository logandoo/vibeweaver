#!/usr/bin/env bash
# W1 Task 7.5 — destructive command guard (10 fixtures).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DRIVE="$ROOT/tests/gate_trust/drive_before.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-destr-XXXXXX")"; trap 'rm -rf "$T"' EXIT
P="$T/proj"; mkdir -p "$P/tests" "$P/src"
printf '> cap=5  stall=3×\n1. x\n' > "$P/tests/acceptance.md"
printf '## T\n- class: CODE\n- profile: full\n- iter 1 PASS: x\n' > "$P/tests/verification_log.md"
printf '' > "$P/tests/decisions.md"
fail=0
expect() { local l="$1" e="$2" c="$3"; local o; o="$(node "$DRIVE" "$P" bash "{\"command\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$c")}")"; if [[ "$o" == $e ]]; then echo "PASS  $l"; else echo "FAIL  $l: $o"; fail=1; fi; }

expect "git add -A blocks" 'BLOCK:*' 'git add -A'
expect "git add -u passes" 'CLEAN' 'git add -u'
expect "git reset --hard blocks" 'BLOCK:*' 'git reset --hard'
expect "git clean -fdx blocks" 'BLOCK:*' 'git clean -fdx'
expect "git checkout -- . blocks" 'BLOCK:*' 'git checkout -- .'
expect "rm -rf src blocks" 'BLOCK:*' 'rm -rf src'
expect "rm -rf node_modules passes" 'CLEAN' 'rm -rf node_modules'
expect "rm -rf .venv dist build passes" 'CLEAN' 'rm -rf .venv dist build'
expect "rm -rf \$TMPDIR/foo passes" 'CLEAN' 'rm -rf $TMPDIR/foo'
expect "truncate blocks" 'BLOCK:*' 'truncate -s 0 app.log'
printf -- '- destructive-approved: git add -A — fixture approval\n' > "$P/tests/decisions.md"
expect "ADR allows git add -A" 'CLEAN' 'git add -A'
if [[ "$fail" -ne 0 ]]; then echo "DESTRUCTIVE FAIL"; exit 1; fi
echo "DESTRUCTIVE OK 11/11"
