#!/usr/bin/env bash
set -euo pipefail

echo "[START] transpose is a library-only project (no server lifecycle)."
echo "[START] Running import smoke check..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

python3 -c "from transpose import transpose; assert transpose('ABC\n123') == 'A1\nB2\nC3'; assert transpose('ABC\nDE') == 'AD\nBE\nC'; assert transpose('AB\nDEF') == 'AD\nBE\n F'; print('[START] transpose import + smoke OK')"

# Record session PID using the §A6 pidfile pattern so stop.sh always has a
# targeted PID to kill (never a pattern-kill).
echo $$ > "$PROJECT_DIR/.pid"
echo "[START] Session PID recorded: $(cat "$PROJECT_DIR/.pid")"
