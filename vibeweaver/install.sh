#!/usr/bin/env bash
# install.sh — thin wrapper around scripts/install.py (single implementation).
set -euo pipefail
exec python3 "$(dirname "$0")/scripts/install.py" "$@"
