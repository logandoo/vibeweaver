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

# Copy the canonical artifact-assertion script (copied into projects per SKILL.md A4.4.1)
mkdir -p "${SKILLS_DIR}/scripts"
cp "${SCRIPT_DIR}/scripts/assert_artifacts.py" "${SKILLS_DIR}/scripts/assert_artifacts.py"
echo "[OK] Installed: scripts/assert_artifacts.py"

echo ""
echo "[OK] vibeweaver skill installed to: ${SKILLS_DIR}/"
echo "     Files installed: $(( ${#FILES[@]} + 1 ))"
echo "     Restart OpenCode to activate."
