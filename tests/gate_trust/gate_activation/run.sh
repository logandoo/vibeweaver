#!/usr/bin/env bash
# W1 Task 6 — activation, profile/class preconditions, gate_result, DOC guard.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DRIVE="$ROOT/tests/gate_trust/drive_gate.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-act-XXXXXX")"
trap 'rm -rf "$T"' EXIT

H="$T/home"; mkdir -p "$H/scripts"
cat > "$H/scripts/assert_artifacts.py" <<'PY'
#!/usr/bin/env python3
import sys
if "--existing" in sys.argv and "--backend-only" not in sys.argv:
    print("assert_artifacts.py: all 1 checks pass")
    sys.exit(0)
print("FAIL: needs --existing")
sys.exit(1)
PY
DIG="$(python3 - <<'PY' "$H/scripts/assert_artifacts.py"
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
printf '%s  assert_artifacts.py\n' "$DIG" > "$H/scripts/assert_artifacts.sha256"

mkproj() {
  local p="$1" cls="$2" profile="$3"
  mkdir -p "$p/tests" "$p/src"
  printf '> cap=5  stall=3×\n1. fixture\n' > "$p/tests/acceptance.md"
  {
    printf '## Task: fixture\n- class: %s\n' "$cls"
    [ -n "$profile" ] && printf -- '- profile: %s\n' "$profile"
    printf -- '- Baseline verified GREEN\n- iter 1 PASS: criterion #1 (evidence: tests/x.log)\n'
  } > "$p/tests/verification_log.md"
  cp "$H/scripts/assert_artifacts.py" "$p/tests/assert_artifacts.py"
  printf 'x=1\n' > "$p/src/app.py"
}
fail=0
check() { local label="$1" expect="$2" out="$3"; if [[ "$out" == $expect ]]; then echo "PASS  $label"; else echo "FAIL  $label: $out"; fail=1; fi; }

# 1) lenient flag skipped without - profile -> block
P="$T/noprofile"; mkproj "$P" CODE ""
OUT="$(VIBEWEAVER_HOME="$H" node "$DRIVE" "$P" "$P/src/app.py")"
check "no-profile: lenient flag is not used" 'BLOCK:*' "$OUT"

# 2) with - profile -> --existing pass, gate_result records flags
P="$T/profile"; mkproj "$P" CODE full
OUT="$(VIBEWEAVER_HOME="$H" node "$DRIVE" "$P" "$P/src/app.py")"
check "profile-present: modify-existing passes" 'CLEAN' "$OUT"
if grep -q '"flags":"--existing"' "$P/tests/gate_result.json"; then echo "PASS  gate_result records --existing"; else echo "FAIL  gate_result missing"; fail=1; fi

# 3) DOC claim + code write -> block
P="$T/doc"; mkproj "$P" DOC full
OUT="$(VIBEWEAVER_HOME="$H" node "$DRIVE" "$P" "$P/src/app.py")"
check "DOC misreport + code write blocks" 'BLOCK:*' "$OUT"

# 4) marker without log -> GATE-INACTIVE note, not a block
P="$T/inactive"; mkdir -p "$P/.vibeweaver" "$P/src"
printf '{"project":"fixture"}\n' > "$P/.vibeweaver/project.json"
printf 'x=1\n' > "$P/src/app.py"
OUT="$(VW_DRIVE_JSON=1 VIBEWEAVER_HOME="$H" node "$DRIVE" "$P" "$P/src/app.py")"
if [[ "$OUT" == *GATE-INACTIVE* ]]; then echo "PASS  marker without log -> GATE-INACTIVE"; else echo "FAIL  GATE-INACTIVE: $OUT"; fail=1; fi

if [[ "$fail" -ne 0 ]]; then echo "GATE-ACTIVATION FAIL"; exit 1; fi
echo "GATE-ACTIVATION OK 5/5"
