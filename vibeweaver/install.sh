#!/usr/bin/env bash
# install.sh — thin wrapper around scripts/install.py (single implementation).
set -euo pipefail
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*) PY=python ;;
    *) if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi ;;
esac
command -v "$PY" >/dev/null 2>&1 || PY=python
exec "$PY" "$(dirname "$0")/scripts/install.py" "$@"
