#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile pig_latin.py
python3 -c "import pig_latin; assert pig_latin.translate('pig') == 'igpay'; assert pig_latin.translate('quick fast run') == 'ickquay astfay unray'; assert pig_latin.translate('rhythm') == 'ythmrhay'; print('smoke check OK')"
