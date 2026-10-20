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
    if ! grep -q "ALL CHECKS PASS" "$ROOT/vw_check.py" || ! grep -q "vw_test_hashes" "$ROOT/vw_check.py"; then
        echo "[ERROR] existing vw_check.py is not the mini checker; refusing to trust it." >&2
        echo "        Move it aside, then re-run this script." >&2
        exit 1
    fi
    echo "[OK] kept existing vw_check.py"
else
    cp "$HERE/vw_check.py" "$ROOT/vw_check.py"
    echo "[OK] copied vw_check.py"
fi

mkdir -p "$ROOT/script"
if [ -f "$ROOT/script/check.sh" ]; then
    if ! grep -q "vw_check" "$ROOT/script/check.sh" || ! grep -q "ALL CHECKS PASS" "$ROOT/script/check.sh"; then
        echo "[ERROR] existing script/check.sh is not the mini wrapper; refusing to trust it." >&2
        echo "        Move it aside, then re-run this script." >&2
        exit 1
    fi
    echo "[OK] kept existing script/check.sh"
else
    cp "$HERE/check.sh" "$ROOT/script/check.sh"
    echo "[OK] copied script/check.sh"
fi
chmod +x "$ROOT/script/check.sh"

echo "[OK] mini project ready: $ROOT"
echo "     Run: bash script/check.sh (or python3 vw_check.py) until ALL CHECKS PASS"
