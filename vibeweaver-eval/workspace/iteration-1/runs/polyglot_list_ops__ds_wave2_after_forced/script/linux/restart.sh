#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "[RESTART] list_ops is library-only; restart = stop + fresh start smoke."
"$SCRIPT_DIR/stop.sh"
"$SCRIPT_DIR/start.sh"
echo "[RESTART] Done."
