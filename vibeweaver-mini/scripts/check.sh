#!/bin/sh
# COV-2 lifecycle path for mini tasks: completion flag = checker exit 0, and
# THIS script prints the ALL CHECKS PASS line (the flag the agent reports).
# Usage: bash script/check.sh [--test-change "<reason>"]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
CHECKER=""
for c in "$HERE/vw_check.py" "scripts/vw_check.py" "vw_check.py"; do
  if [ -f "$c" ]; then CHECKER="$c"; break; fi
done
if [ -z "$CHECKER" ]; then
  echo "vw_check.py not found next to check.sh or under scripts/" >&2
  exit 1
fi
PY="${VIBEWEAVER_MINI_PYTHON:-python3}"
if "$PY" "$CHECKER" "$@"; then
  echo "ALL CHECKS PASS"
  exit 0
fi
exit 1
