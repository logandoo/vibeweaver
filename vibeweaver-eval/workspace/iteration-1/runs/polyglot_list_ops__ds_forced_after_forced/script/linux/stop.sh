#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# HOST-SAFETY: kill ONLY the PID recorded in .pid by start.sh — never a
# pattern-kill (pkill -f) which would hit unrelated services on shared hosts.
if [ -f "$PROJECT_DIR/.pid" ]; then
    PID=$(cat "$PROJECT_DIR/.pid")
    echo "[STOP] Stopping session (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    rm "$PROJECT_DIR/.pid"
    echo "[STOP] Stopped."
else
    echo "[STOP] No PID file found."
fi
