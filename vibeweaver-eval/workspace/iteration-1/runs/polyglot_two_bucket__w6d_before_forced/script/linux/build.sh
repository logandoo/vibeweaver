#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile two_bucket.py
echo "build OK: two_bucket.py compiles"
