#!/usr/bin/env bash
# vibeweaver lifecycle: pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile phone_number.py
python3 -c "from phone_number import PhoneNumber; assert PhoneNumber('+1 (613)-995-0253').number == '6139950253'; assert PhoneNumber('12234567890').area_code == '223'; assert PhoneNumber('2234567890').pretty() == '(223)-456-7890'; print('smoke check OK')"
