#!/usr/bin/env bash
# COV-2 lifecycle: library-only workspace (no persistent server).
# "start" = verify the module is importable and passes its smoke check.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile variable_length_quantity.py
python3 -c "from variable_length_quantity import encode, decode; assert encode([0]) == [0]; assert decode([0x81, 0x00]) == [128]; print('smoke OK')"
echo "start.sh: module import + smoke check passed"
