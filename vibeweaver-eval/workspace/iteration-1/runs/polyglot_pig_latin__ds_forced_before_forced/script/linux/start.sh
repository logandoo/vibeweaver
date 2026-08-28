#!/bin/sh
# pig_latin.py is a pure library module (no server to run).
# start.sh verifies the module is importable and runs a smoke check.
set -eu
cd "$(dirname "$0")/../.."
python3 -m py_compile pig_latin.py
python3 -c "import pig_latin; assert pig_latin.translate('hello') == 'ellohay', pig_latin.translate('hello')"
echo "start.sh: pig_latin.py smoke check PASSED"
