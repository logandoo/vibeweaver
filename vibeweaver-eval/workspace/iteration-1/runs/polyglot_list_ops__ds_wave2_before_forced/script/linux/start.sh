#!/usr/bin/env bash
set -euo pipefail

echo "[START] list_ops is a library-only project (no server lifecycle)."
echo "[START] Running import smoke check..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

python3 -c "import list_ops; assert list_ops.length([1, 2, 3]) == 3; print('[START] list_ops import + smoke OK')"

# Record session PID using the §A6 pidfile pattern so stop.sh always has a
# targeted PID to kill (never a pattern-kill).
echo $$ > "$PROJECT_DIR/.pid"
echo "[START] Session PID recorded: $(cat "$PROJECT_DIR/.pid")"
