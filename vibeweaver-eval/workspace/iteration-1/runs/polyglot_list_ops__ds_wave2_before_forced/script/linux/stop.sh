#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIDFILE="$PROJECT_DIR/.pid"

if [ ! -f "$PIDFILE" ]; then
    echo "[STOP] No .pid file found — nothing to stop (library-only project)."
    exit 0
fi

PID="$(cat "$PIDFILE")"
echo "[STOP] Terminating session PID $PID (targeted kill, never pattern-kill)."
kill "$PID" 2>/dev/null || true
rm -f "$PIDFILE"
echo "[STOP] Done."
