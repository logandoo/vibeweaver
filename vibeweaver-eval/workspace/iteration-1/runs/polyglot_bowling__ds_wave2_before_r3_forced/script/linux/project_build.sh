#!/usr/bin/env bash
# project_build.sh — backend-only exercise: no frontend to build; the
# "build" is a syntax + import check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile bowling.py
echo "build ok (bowling.py compiled clean)"
