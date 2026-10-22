#!/usr/bin/env bash
# Checker pin fixtures (PLAN W0 Task 2).
#   fake-checker: BLOCKED · canonical: PASS · tampered: BLOCKED
# Exit 0 only when every verdict matches.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DRIVE="$ROOT/tests/gate_trust/drive_gate.mjs"
CANON="$ROOT/vibeweaver/scripts/assert_artifacts.py"
[[ -f "$CANON" ]] || CANON="$ROOT/scripts/assert_artifacts.py"
HOME_DIR="$(dirname "$(dirname "$CANON")")"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-gate-trust-XXXXXX")"
trap 'rm -rf "$T"' EXIT

mkproj() {
  local p="$1"
  mkdir -p "$p/tests" "$p/src"
  printf '> cap=5  stall=3x\n1. fixture\n' > "$p/tests/acceptance.md"
  printf '## fixture\n- class: CODE - basis: fixture\n- Baseline verified GREEN - fixture\n' > "$p/tests/verification_log.md"
  printf 'const x = 1\n' > "$p/src/app.js"
}

fake_checker() {
  cat > "$1" <<'PY'
#!/usr/bin/env python3
print("assert_artifacts.py: all 3 checks pass")
PY
}

fail=0
check() {
  local label="$1" expect="$2" out="$3"
  case "$expect" in
    blocked)
      if [[ "$out" == BLOCK:* && "$out" == *checker* ]]; then echo "PASS  $label: BLOCKED"; else echo "FAIL  $label: $out"; fail=1; fi ;;
    not-checker)
      if [[ "$out" == BLOCK:* && "$out" == *checker* ]]; then echo "FAIL  $label: checker block unexpected: $out"; fail=1; else echo "PASS  $label: PASS (no checker block)"; fi ;;
    clean)
      if [[ "$out" == CLEAN ]]; then echo "PASS  $label: CLEAN"; else echo "FAIL  $label: $out"; fail=1; fi ;;
  esac
}

# 1) fake 3-line checker -> pin mismatch -> BLOCKED
P="$T/fake"; mkproj "$P"; fake_checker "$P/tests/assert_artifacts.py"
OUT="$(VIBEWEAVER_HOME="$HOME_DIR" node "$DRIVE" "$P" "$P/src/app.js")"
check "fake-checker" blocked "$OUT"

# 2) canonical checker copy -> digest matches -> no checker block
P="$T/canonical"; mkproj "$P"; cp "$CANON" "$P/tests/assert_artifacts.py"
OUT="$(VIBEWEAVER_HOME="$HOME_DIR" node "$DRIVE" "$P" "$P/src/app.js")"
check "canonical" not-checker "$OUT"

# 3) one-byte tamper -> BLOCKED
P="$T/tampered"; mkproj "$P"; cp "$CANON" "$P/tests/assert_artifacts.py"
printf '\n# tamper\n' >> "$P/tests/assert_artifacts.py"
OUT="$(VIBEWEAVER_HOME="$HOME_DIR" node "$DRIVE" "$P" "$P/src/app.js")"
check "tampered" blocked "$OUT"

# 4) protected checker path is not an evidence exemption
P="$T/protected"; mkproj "$P"; fake_checker "$P/tests/assert_artifacts.py"
OUT="$(VIBEWEAVER_HOME="$HOME_DIR" node "$DRIVE" "$P" "$P/tests/assert_artifacts.py")"
check "protected-checker-write" blocked "$OUT"

# 5) ordinary evidence write stays exempt
OUT="$(VIBEWEAVER_HOME="$HOME_DIR" node "$DRIVE" "$P" "$P/tests/verification_log.md")"
check "evidence-write" clean "$OUT"

if [[ "$fail" -ne 0 ]]; then echo "CHECKER-PIN FAIL"; exit 1; fi
echo "CHECKER-PIN OK 5/5"
