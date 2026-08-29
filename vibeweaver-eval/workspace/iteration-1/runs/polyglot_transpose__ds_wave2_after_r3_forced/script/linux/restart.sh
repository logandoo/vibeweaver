#!/usr/bin/env bash
# vibeweaver lifecycle: pure Python library — stop (no-op) then start (compile + smoke).
set -euo pipefail
cd "$(dirname "$0")/.."
bash linux/stop.sh
bash linux/start.sh
