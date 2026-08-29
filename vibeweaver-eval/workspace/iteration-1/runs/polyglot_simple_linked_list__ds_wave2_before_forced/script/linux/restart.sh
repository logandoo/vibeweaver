#!/usr/bin/env bash
# vibeweaver lifecycle: restart = re-run the smoke check (pure library).
set -euo pipefail
cd "$(dirname "$0")/../.."
exec bash script/linux/start.sh
