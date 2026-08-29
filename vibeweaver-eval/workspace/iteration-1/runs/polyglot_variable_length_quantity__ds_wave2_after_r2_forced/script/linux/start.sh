#!/usr/bin/env bash
set -e
python3 -c "import variable_length_quantity as v; assert callable(v.encode) and callable(v.decode)" && echo "VLQ library import OK"
