#!/usr/bin/env bash
# vibeweaver lifecycle: pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile bowling.py
python3 - <<'EOF'
from bowling import BowlingGame
g = BowlingGame()
for p in [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]:
    g.roll(p)
assert g.score() == 300, g.score()
print("smoke check OK: perfect game =", g.score())
EOF
