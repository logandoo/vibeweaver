#!/usr/bin/env bash
# W1 Task 7 — risk-path pre-write gate.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DRIVE="$ROOT/tests/gate_trust/drive_before.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-risk-XXXXXX")"; trap 'rm -rf "$T"' EXIT
P="$T/proj"; mkdir -p "$P/tests" "$P/src/auth"
printf '> cap=5  stall=3×\n1. x\n' > "$P/tests/acceptance.md"
printf '## T\n- class: CODE\n- profile: full\n- iter 1 PASS: x\n' > "$P/tests/verification_log.md"
printf '' > "$P/tests/decisions.md"
fail=0
check() { local l="$1" e="$2" o="$3"; if [[ "$o" == $e ]]; then echo "PASS  $l"; else echo "FAIL  $l: $o"; fail=1; fi; }

check "risk path without ADR blocks" 'BLOCK:*' "$(node "$DRIVE" "$P" write "{\"path\":\"$P/src/auth/login.py\"}")"
printf -- '- risk-approved: src/auth/login.py — user-approved fixture\n' > "$P/tests/decisions.md"
check "risk path with ADR passes" 'CLEAN' "$(node "$DRIVE" "$P" write "{\"path\":\"$P/src/auth/login.py\"}")"
check "ordinary path passes" 'CLEAN' "$(node "$DRIVE" "$P" write "{\"path\":\"$P/src/app.py\"}")"
printf '' > "$P/tests/decisions.md"
check "risk deletion without ADR blocks" 'BLOCK:*' "$(node "$DRIVE" "$P" bash '{"command":"rm -rf src/auth"}')"
printf -- '- risk-approved: src/auth — user-approved fixture\n' > "$P/tests/decisions.md"
check "risk deletion with ADR passes" 'CLEAN' "$(node "$DRIVE" "$P" bash '{"command":"rm -rf src/auth"}')"
if [[ "$fail" -ne 0 ]]; then echo "RISK-PATHS FAIL"; exit 1; fi
echo "RISK-PATHS OK 5/5"
