#!/usr/bin/env bash
set -euo pipefail

echo "[RESTART] Restarting (library-only project)..."
bash "$(dirname "$0")/stop.sh"
bash "$(dirname "$0")/start.sh"
echo "[RESTART] Done."
