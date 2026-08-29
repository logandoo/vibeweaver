#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile robot_name.py
python3 -c "import robot_name; import re; r = robot_name.Robot(); assert re.match(r'^[A-Z]{2}[0-9]{3}$', r.name), r.name; old = r.name; r.reset(); assert r.name != old and re.match(r'^[A-Z]{2}[0-9]{3}$', r.name), r.name; print('smoke check OK:', r.name)"
