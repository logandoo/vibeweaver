#!/bin/sh
# setup_project.sh — put the mini checker where the gate can find it.
# Usage: sh setup_project.sh [project-root]   (default: current directory)

set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:-$PWD}"

if [ ! -d "$ROOT" ]; then
    echo "not a directory: $ROOT" >&2
    exit 1
fi

if [ -f "$ROOT/vw_check.py" ]; then
    echo "[OK] kept existing vw_check.py"
else
    cp "$HERE/vw_check.py" "$ROOT/vw_check.py"
    echo "[OK] copied vw_check.py"
fi

mkdir -p "$ROOT/script"
if [ -f "$ROOT/script/check.sh" ]; then
    echo "[OK] kept existing script/check.sh"
else
    cp "$HERE/check.sh" "$ROOT/script/check.sh"
    echo "[OK] copied script/check.sh"
fi
chmod +x "$ROOT/script/check.sh"

echo "[OK] mini project ready: $ROOT"
echo "     Run: bash script/check.sh (or python3 vw_check.py) until ALL CHECKS PASS"
