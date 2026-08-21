#!/usr/bin/env bash
# install.sh — Install vibeweaver skill into OpenCode (Linux/macOS)

set -euo pipefail

SKILL_NAME="vibeweaver"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Determine OpenCode skills directory
if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
    SKILLS_DIR="${XDG_CONFIG_HOME}/opencode/skills/${SKILL_NAME}"
else
    SKILLS_DIR="${HOME}/.config/opencode/skills/${SKILL_NAME}"
fi

# Files to install
FILES=(
    "SKILL.md"
    "COMPLETION_GATE.md"
    "CODING_PRINCIPLES.md"
    "ENGINEERING_STD.md"
    "REFERENCE.md"
    "APPENDIX.md"
    "MEMORY_TEMPLATES.md"
    "MEMORY_RULES.md"
    "TESTING_PROTOCOLS.md"
)

if [[ ! -f "${SCRIPT_DIR}/scripts/assert_artifacts.py" ]]; then
    echo "[ERROR] scripts/assert_artifacts.py not found at: ${SCRIPT_DIR}/scripts/"
    exit 1
fi

# Check source files exist
for file in "${FILES[@]}"; do
    if [[ ! -f "${SCRIPT_DIR}/${file}" ]]; then
        echo "[ERROR] ${file} not found at: ${SCRIPT_DIR}/${file}"
        exit 1
    fi
done

# Create target directory
mkdir -p "${SKILLS_DIR}"

# Copy all skill files
for file in "${FILES[@]}"; do
    cp "${SCRIPT_DIR}/${file}" "${SKILLS_DIR}/${file}"
    echo "[OK] Installed: ${file}"
done

# Copy skill scripts (canonical assert script + audit core module)
mkdir -p "${SKILLS_DIR}/scripts"
cp "${SCRIPT_DIR}/scripts/assert_artifacts.py" "${SKILLS_DIR}/scripts/assert_artifacts.py"
echo "[OK] Installed: scripts/assert_artifacts.py"
cp "${SCRIPT_DIR}/scripts/vibeweaver-audit-core.js" "${SKILLS_DIR}/scripts/vibeweaver-audit-core.js"
echo "[OK] Installed: scripts/vibeweaver-audit-core.js"

# Install the plugin pair (physical gate + Tier-0/1/2 auditor) into opencode's plugin dir
PLUGINS_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/opencode/plugins"
mkdir -p "${PLUGINS_DIR}"
for plugin in "vibeweaver-gate.js" "vibeweaver-audit.js"; do
    if [[ -f "${SCRIPT_DIR}/${plugin}" ]]; then
        cp "${SCRIPT_DIR}/${plugin}" "${PLUGINS_DIR}/${plugin}"
        echo "[OK] Installed plugin: ${plugin}"
    fi
done

echo ""
echo "[OK] vibeweaver skill installed to: ${SKILLS_DIR}/"
echo "     Files installed: $(( ${#FILES[@]} + 2 ))"
echo "     Plugins installed to: ${PLUGINS_DIR}/"
echo "     Restart OpenCode to activate."
