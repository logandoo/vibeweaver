#!/usr/bin/env bash
# vibeweaver lifecycle: no service to restart; re-run the smoke check.
set -euo pipefail
cd "$(dirname "$0")"
./start.sh
