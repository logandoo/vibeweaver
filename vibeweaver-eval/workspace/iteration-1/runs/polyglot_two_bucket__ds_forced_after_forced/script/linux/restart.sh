#!/usr/bin/env bash
# vibeweaver lifecycle: pure Python library — restart = re-run start smoke check.
set -euo pipefail
cd "$(dirname "$0")/../.."
bash script/linux/start.sh
