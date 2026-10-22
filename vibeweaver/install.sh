#!/usr/bin/env bash
# install.sh — thin wrapper around scripts/install.py (single implementation).
set -euo pipefail
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
exec "$PY" "$(dirname "$0")/scripts/install.py" "$@"
