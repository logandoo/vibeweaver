#!/usr/bin/env bash
# install.sh — install vibeweaver-mini + its checker gate into OpenCode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="vibeweaver-mini"
SKILLS_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/opencode/skills/${SKILL_NAME}"
PLUGINS_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/opencode/plugins"

FILES=(
    "SKILL.md"
    "scripts/vw_check.py"
    "scripts/check.sh"
    "scripts/setup_project.sh"
)

for f in "${FILES[@]}" "vibeweaver-mini-gate.js"; do
    if [[ ! -f "${SCRIPT_DIR}/${f}" ]]; then
        echo "[ERROR] ${f} not found at: ${SCRIPT_DIR}/${f}"
        exit 1
    fi
done

mkdir -p "${SKILLS_DIR}/scripts" "${PLUGINS_DIR}"

for f in "${FILES[@]}"; do
    cp "${SCRIPT_DIR}/${f}" "${SKILLS_DIR}/${f}"
    echo "[OK] Installed: ${f}"
done
cp "${SCRIPT_DIR}/vibeweaver-mini-gate.js" "${PLUGINS_DIR}/vibeweaver-mini-gate.js"
echo "[OK] Installed plugin: vibeweaver-mini-gate.js"

echo ""
echo "[OK] vibeweaver-mini installed to: ${SKILLS_DIR}/"
echo "     Plugin installed to: ${PLUGINS_DIR}/"
echo "     In your project, run: bash ${SKILLS_DIR}/scripts/setup_project.sh"
echo "     Restart OpenCode to activate."
