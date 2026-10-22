#!/usr/bin/env bash
# Evidence integrity fixtures (PLAN W0 Task 2.5 / Acceptance #28).
#   1 acceptance changed        -> BLOCK
#   2 FAIL line deleted        -> BLOCK
#   3 profile changed          -> BLOCK
#   4 debt baseline changed    -> BLOCK
#   5 1-byte fake PNG          -> BLOCK
#   6 legacy log migration     -> PASS
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOCK="$ROOT/scripts/evidence_lock.py"
[[ -f "$LOCK" ]] || LOCK="$ROOT/vibeweaver/scripts/evidence_lock.py"
DRIVE="$ROOT/tests/gate_trust/drive_gate.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-evi-XXXXXX")"
trap 'rm -rf "$T"' EXIT

mkproj() {
  local p="$1"
  mkdir -p "$p/tests"
  printf '> cap=5  stall=3x\n\n## Task A\n1. criterion A\n' > "$p/tests/acceptance.md"
  printf '## Task A\n- class: CODE\n- Baseline verified GREEN\n- iter 1 PASS: criterion #1 (evidence: tests/x.log)\n' > "$p/tests/verification_log.md"
  printf '{"profile":"library"}\n' > "$p/tests/project_profile.json"
  printf '{"max_bytes":4096,"recorded":[]}\n' > "$p/tests/debt_baseline.json"
}
fail=0
expect() { local label="$1" rc="$2"; if [[ "$rc" -ne 0 ]]; then echo "PASS  $label: BLOCKED"; else echo "FAIL  $label: not blocked"; fail=1; fi; }
expect_ok() { local label="$1" rc="$2"; if [[ "$rc" -eq 0 ]]; then echo "PASS  $label: PASS"; else echo "FAIL  $label: rc=$rc"; fail=1; fi; }

# 1) acceptance changed after lock
P="$T/acc"; mkproj "$P"; python3 "$LOCK" --root "$P" --init >/dev/null
printf '2. criterion B (loosened)\n' >> "$P/tests/acceptance.md"
python3 "$LOCK" --root "$P" --check >/dev/null 2>&1; expect acceptance "$?"
OUT="$(VIBEWEAVER_HOME="$(dirname "$(dirname "$LOCK")")" node "$DRIVE" "$P" "$P/tests/acceptance.md" 2>&1 || true)"
if [[ "$OUT" == *"evidence lock"* || "$OUT" == *"acceptance section changed"* ]]; then echo "PASS  gate-protected-acceptance: BLOCKED"; else echo "FAIL  gate-protected-acceptance: $OUT"; fail=1; fi

# 2) FAIL line deleted after seal
P="$T/log"; mkproj "$P"
printf -- '- iter 2 FAIL: criterion #2 | diagnosis: fixture failure\n' >> "$P/tests/verification_log.md"
python3 "$LOCK" --root "$P" --init >/dev/null
python3 "$LOCK" --root "$P" --seal-log >/dev/null
python3 - "$P" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]) / "tests" / "verification_log.md"
lines = [l for l in p.read_text().splitlines() if "iter 2 FAIL" not in l]
p.write_text("\n".join(lines) + "\n")
PY
python3 "$LOCK" --root "$P" --check >/dev/null 2>&1; expect deleted-fail "$?"

# 3) profile changed
P="$T/prof"; mkproj "$P"; python3 "$LOCK" --root "$P" --init >/dev/null
printf '{"profile":"library","no_service":false}\n' > "$P/tests/project_profile.json"
python3 "$LOCK" --root "$P" --check >/dev/null 2>&1; expect profile "$?"

# 4) debt baseline changed
P="$T/debt"; mkproj "$P"; python3 "$LOCK" --root "$P" --init >/dev/null
printf '{"max_bytes":4096,"recorded":[{"path":"big.bin","bytes":999}]}\n' > "$P/tests/debt_baseline.json"
python3 "$LOCK" --root "$P" --check >/dev/null 2>&1; expect debt "$?"

# 5) 1-byte fake PNG cited as evidence
P="$T/png"; mkproj "$P"
printf 'x' > "$P/tests/shot.png"
printf -- '- evidence: tests/shot.png (terminal state)\n' >> "$P/tests/verification_log.md"
python3 "$LOCK" --root "$P" --init >/dev/null
python3 "$LOCK" --root "$P" --check >/dev/null 2>&1; expect fake-png "$?"

# 6) legacy log without a chain -> init + check passes
P="$T/legacy"; mkproj "$P"
python3 "$LOCK" --root "$P" --init >/dev/null
python3 "$LOCK" --root "$P" --check --final >/dev/null 2>&1; expect_ok legacy-migration "$?"

if [[ "$fail" -ne 0 ]]; then echo "EVIDENCE-INTEGRITY FAIL"; exit 1; fi
echo "EVIDENCE-INTEGRITY OK 6/6"
