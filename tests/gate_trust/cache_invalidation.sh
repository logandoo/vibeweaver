#!/usr/bin/env bash
# Cache invalidation fixtures (PLAN W0 Task 2 step 6).
# 1) checker update invalidates a cached pass
# 2) mid-task pass is not reused for a --final run
# 3) evidence change invalidates a cached pass
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SEQ="$ROOT/tests/gate_trust/cache_sequence.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/vw-cache-XXXXXX")"
trap 'rm -rf "$T"' EXIT

HOME_DIR="$T/home"; P="$T/proj"
mkdir -p "$HOME_DIR/scripts" "$P/tests" "$P/src"
cat > "$HOME_DIR/scripts/assert_artifacts.py" <<'PY'
#!/usr/bin/env python3
import pathlib, sys
mode = "final" if "--final" in sys.argv else "mid"
with open(pathlib.Path.cwd() / "checker_runs.log", "a", encoding="utf-8") as f:
    f.write(mode + "\n")
print("assert_artifacts.py: all 3 checks pass")
PY
DIGEST="$(python3 - <<'PY' "$HOME_DIR/scripts/assert_artifacts.py"
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
printf '%s  assert_artifacts.py\n' "$DIGEST" > "$HOME_DIR/scripts/assert_artifacts.sha256"
cp "$HOME_DIR/scripts/assert_artifacts.py" "$P/tests/assert_artifacts.py"
printf '> cap=5  stall=3x\n1. fixture\n' > "$P/tests/acceptance.md"
printf '## fixture\n- class: CODE - basis: fixture\n- Baseline verified GREEN - fixture\n' > "$P/tests/verification_log.md"

OUT="$(node "$SEQ" "$P" "$HOME_DIR")"
echo "$OUT"
fail=0
line() { echo "$OUT" | grep -E "^$1 " || true; }

S1="$(line STEP1)"; S2="$(line STEP2)"; S3="$(line STEP3)"; S4="$(line STEP4)"
if [[ "$S1" == "STEP1 CLEAN CLEAN 1" ]]; then
  echo "PASS  cache-hit: second identical mid-task run reuses the clean verdict"
else echo "FAIL  cache-hit: $S1"; fail=1; fi

if [[ "$S2" == "STEP2 CLEAN 2" ]]; then
  echo "PASS  mid-task -> final re-runs"
else echo "FAIL  mid-task -> final: $S2"; fail=1; fi

if [[ "$S3" == "STEP3 CLEAN 3" ]]; then
  echo "PASS  evidence change re-runs"
else echo "FAIL  evidence change: $S3"; fail=1; fi

S4_HEAD="${S4#STEP4 }"; S4_HEAD="${S4_HEAD%%$'\n'*}"
if [[ "$S4_HEAD" == BLOCK:* ]] && echo "$OUT" | grep -q "checker was modified"; then
  echo "PASS  checker update invalidates the pin"
else echo "FAIL  checker update: $S4"; fail=1; fi

if [[ "$fail" -ne 0 ]]; then echo "CACHE-INVALIDATION FAIL"; exit 1; fi
echo "CACHE-INVALIDATION OK 4/4"
