#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile two_bucket.py
python3 - <<'PY'
import two_bucket
assert two_bucket.measure(3, 5, 1, "one") == (4, "one", 5)
assert two_bucket.measure(2, 3, 3, "one") == (2, "two", 2)
try:
    two_bucket.measure(6, 15, 5, "one")
    raise SystemExit("expected ValueError for impossible goal")
except ValueError:
    pass
print("smoke check OK")
PY
