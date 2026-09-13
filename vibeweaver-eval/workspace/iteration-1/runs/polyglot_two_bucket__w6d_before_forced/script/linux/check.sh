#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
HARNESS="/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/opencode/two_bucket_checks.py"
mkdir -p tests
python3 "$HARNESS" canon | tee tests/green_evidence.log
python3 "$HARNESS" sweep | tee tests/differential_sweep.log
echo "check OK"
