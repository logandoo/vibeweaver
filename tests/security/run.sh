#!/usr/bin/env bash
# W1 Task 20 — eight security fixtures (reuse executable seams).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }
run() { local label="$1"; shift; "$@" >/tmp/vw-sec.log 2>&1; ok $? "$label"; }

run "fake-checker pin" bash "$ROOT/tests/gate_trust/run.sh"
run "symlink+traversal (plugin compat)" node "$ROOT/tests/plugin_compat_test.mjs"
run "secret state redaction" python3 -m unittest tests.test_state_sanitize
run "manifest mismatch" python3 -m unittest tests.test_release_manifest
run "destructive command guard" bash "$ROOT/tests/gate_trust/destructive_commands/run.sh"
run "risk-path guard" bash "$ROOT/tests/gate_trust/risk_paths/run.sh"
python3 "$ROOT/tests/security/mutation_sweep.py" >/tmp/vw-sec.log 2>&1; ok $? "checker mutation sweep"
if grep -q "COV-11" "$ROOT/docs/TRUST_MODEL.md" && grep -qi "prompt injection" "$ROOT/docs/TRUST_MODEL.md"; then echo "PASS  prompt-injection policy"; else echo "FAIL  prompt-injection policy"; fail=1; fi
if [ "$fail" -ne 0 ]; then echo "SECURITY FAIL"; exit 1; fi
echo "SECURITY OK 8/8"
