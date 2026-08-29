#!/usr/bin/env bash
# vibeweaver lifecycle: pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile transpose.py
python3 - <<'EOF'
from transpose import transpose
assert transpose("ABC\nDEF") == "AD\nBE\nCF", transpose("ABC\nDEF")
assert transpose("AB\nDEF") == "AD\nBE\n F"
print("smoke check OK: ABC\nDEF -> AD\nBE\nCF")
EOF
