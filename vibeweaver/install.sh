#!/usr/bin/env bash
# install.sh — Install vibeweaver skill into OpenCode (Linux/macOS)
#
# Release trust (PLAN W0 Task 1): before copying anything, verify the bundle
# against release/MANIFEST.json. A missing manifest is a hard error in the
# release layout (install.sh inside vibeweaver/); the dev tree (payload at the
# repository root) gets an explicit unverified warning. --no-verify is an
# explicit development escape hatch, never a silent fallback.

set -euo pipefail

SKILL_NAME="vibeweaver"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=0
VERIFY=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --no-verify) VERIFY=0 ;;
        -h|--help)
            echo "usage: install.sh [--dry-run] [--no-verify]"
            echo "  --dry-run    print the install plan + manifest digest, copy nothing"
            echo "  --no-verify  skip manifest verification (development only)"
            exit 0
            ;;
        *) echo "[ERROR] unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

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
    "WORKFLOWS_EXTENDED.md"
    "VERIFICATION_UPGRADES.md"
    "bootstrap.md"
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

# --- release verification (before any copy) ---------------------------------
MANIFEST=""
for candidate in "${SCRIPT_DIR}/../release/MANIFEST.json" "${SCRIPT_DIR}/release/MANIFEST.json"; do
    if [[ -f "${candidate}" ]]; then MANIFEST="$(cd "$(dirname "${candidate}")" && pwd)/MANIFEST.json"; break; fi
done

if [[ "${VERIFY}" -eq 1 ]]; then
    if [[ -z "${MANIFEST}" ]]; then
        # Release layout: install.sh sits inside <bundle>/vibeweaver/ and the
        # bundle root carries vibeweaver-mini/ (repo) or release/.
        if [[ -d "${SCRIPT_DIR}/../release" || -f "${SCRIPT_DIR}/../verify_skill.py" ]]; then
            echo "[ERROR] release manifest missing: expected $(cd "${SCRIPT_DIR}/.." && pwd)/release/MANIFEST.json" >&2
            echo "        refusing to install an unverifiable release bundle (use --no-verify only for development)" >&2
            exit 1
        fi
        echo "[WARN] release manifest not found — dev-tree install (unverified). Release bundles always carry release/MANIFEST.json." >&2
    else
        ROOT="$(cd "$(dirname "${MANIFEST}")/.." && pwd)"
        PY="$(command -v python3 || command -v python || true)"
        if [[ -z "${PY}" ]]; then
            echo "[ERROR] python3 is required to verify the release manifest" >&2
            exit 1
        fi
        VERIFIER="${SCRIPT_DIR}/scripts/verify_release.py"
        if [[ ! -f "${VERIFIER}" ]]; then
            VERIFIER="${SCRIPT_DIR}/../scripts/verify_release.py"
        fi
        if [[ ! -f "${VERIFIER}" ]]; then
            echo "[ERROR] verify_release.py not found — cannot verify the bundle" >&2
            exit 1
        fi
        if ! "${PY}" "${VERIFIER}" --root "${ROOT}" --manifest "${MANIFEST}"; then
            echo "[ERROR] manifest verification failed — refusing to install a partial/tampered bundle" >&2
            exit 1
        fi
        DIGEST="$("${PY}" - <<'PY' "${MANIFEST}"
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
        echo "[OK] bundle verified: manifest sha256=${DIGEST}"
    fi
else
    echo "[WARN] --no-verify: manifest verification skipped (development only)" >&2
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] target: ${SKILLS_DIR}/"
    for file in "${FILES[@]}"; do echo "[dry-run] would install: ${file}"; done
    echo "[dry-run] would install: scripts/assert_artifacts.py"
    echo "[dry-run] would install: scripts/assert_artifacts.sha256"
    echo "[dry-run] would install: scripts/repair_checker.sh"
    echo "[dry-run] would install: scripts/evidence_lock.py"
    echo "[dry-run] would install: scripts/state_sanitize.py"
    echo "[dry-run] would install: scripts/vibeweaver-audit-core.js"
    echo "[dry-run] would install: scripts/backlog_check.py"
    echo "[dry-run] would install: scripts/scan_secrets.py"
    echo "[dry-run] would install: scripts/ui_fidelity.py"
    echo "[dry-run] would install: scripts/mm_probe.py"
    echo "[dry-run] would install: scripts/evidence_seal.py"
    echo "[dry-run] would install plugins: vibeweaver-gate.js vibeweaver-audit.js"
    exit 0
fi

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
if [[ -f "${SCRIPT_DIR}/scripts/assert_artifacts.sha256" ]]; then
    cp "${SCRIPT_DIR}/scripts/assert_artifacts.sha256" "${SKILLS_DIR}/scripts/assert_artifacts.sha256"
    echo "[OK] Installed: scripts/assert_artifacts.sha256"
fi
for extra in repair_checker.sh evidence_lock.py state_sanitize.py; do
    if [[ -f "${SCRIPT_DIR}/scripts/${extra}" ]]; then
        cp "${SCRIPT_DIR}/scripts/${extra}" "${SKILLS_DIR}/scripts/${extra}"
        echo "[OK] Installed: scripts/${extra}"
    fi
done
cp "${SCRIPT_DIR}/scripts/vibeweaver-audit-core.js" "${SKILLS_DIR}/scripts/vibeweaver-audit-core.js"
cp "${SCRIPT_DIR}/scripts/backlog_check.py" "${SKILLS_DIR}/scripts/backlog_check.py"
echo "[OK] Installed: scripts/backlog_check.py"
cp "${SCRIPT_DIR}/scripts/scan_secrets.py" "${SKILLS_DIR}/scripts/scan_secrets.py"
echo "[OK] Installed: scripts/scan_secrets.py"
cp "${SCRIPT_DIR}/scripts/ui_fidelity.py" "${SKILLS_DIR}/scripts/ui_fidelity.py"
echo "[OK] Installed: scripts/ui_fidelity.py"
cp "${SCRIPT_DIR}/scripts/mm_probe.py" "${SKILLS_DIR}/scripts/mm_probe.py"
echo "[OK] Installed: scripts/mm_probe.py"
cp "${SCRIPT_DIR}/scripts/evidence_seal.py" "${SKILLS_DIR}/scripts/evidence_seal.py"
echo "[OK] Installed: scripts/evidence_seal.py"
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
echo "     Files installed: $(( ${#FILES[@]} + 7 ))"
echo "     Plugins installed to: ${PLUGINS_DIR}/"
echo "     Restart OpenCode to activate."
