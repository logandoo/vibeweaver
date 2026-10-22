#!/usr/bin/env bash
# self_check.sh — clean-clone bootstrap gate (PLAN W0 Task 3).
# Structural checks only: no current task block, baseline, or working note.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0

echo "[1/4] assert_artifacts.py --self-check"
python3 tests/assert_artifacts.py --self-check || fail=1

echo "[2/4] doc claims parity"
if [[ -f check_doc_counts.py ]]; then
    python3 check_doc_counts.py || fail=1
else
    echo "skip: check_doc_counts.py is repo-root tooling (dev tree)"
fi

echo "[3/4] payload coherence"
if [[ -f verify_skill.py ]]; then
    python3 verify_skill.py || fail=1
else
    echo "skip: verify_skill.py is repo-root tooling (dev tree)"
fi

echo "[4/4] contract lint"
if [[ -f scripts/contract_lint.py ]]; then
    python3 scripts/contract_lint.py || fail=1
elif [[ -f vibeweaver/scripts/contract_lint.py ]]; then
    python3 vibeweaver/scripts/contract_lint.py --root . || fail=1
else
    echo "skip: scripts/contract_lint.py not installed"
fi

if [[ "$fail" -ne 0 ]]; then
    echo "SELF-CHECK FAILED"
    exit 1
fi
echo "SELF-CHECK OK"
