#!/usr/bin/env bash
# anakot-setup — full setup from scratch
#
# 1. Clone latest Anakot Agent upstream
# 2. Run actual agent setup (deps, venv, entry points)
# 3. Apply rebrand (anakot → anakot) + custom patches
# 4. Build & install desktop app
# 5. Sanity check — verify everything works
#
# Usage:
#   bash anakot-setup.sh [target_dir]
#
# After completion:
#   anakot --version        → Anakot Agent vX.Y.Z
#   anakot --help           → full CLI menu
#   anakot-desktop          → desktop GUI with Anakot branding

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
# Scripts are bundled in the repo (scripts/rebrand/) — no external deps
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REBRAND_PY="${SCRIPT_DIR}/rebrand.py"
CUSTOM_PATCHES="${SCRIPT_DIR}/custom_patches.py"

# Target: where to clone Anakot + apply rebrand
# Default: sibling directory to the repo (so repo stays clean)
TARGET_DIR="${1:-${REPO_ROOT}/../anakot-agent-v1}"

# Remotes
ANAKOT_REPO="https://github.com/Chensihakniroth/anakot-agent-v1.git"
# Fork remote — override with ANAKOT_FORK_REMOTE env var
ANAKOT_REMOTE="${ANAKOT_FORK_REMOTE:-https://github.com/Chensihakniroth/anakot-agent-v1.git}"

# ── Colors & Formatting ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Output helpers ─────────────────────────────────────────────────────
info()  { echo -e "${CYAN}==>${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; }
step()  { echo -e "\n${BOLD}${CYAN}═══ $* ═══${NC}"; }
substep() { echo -e "\n${CYAN}── $* ──${NC}"; }

# ── Step counter ───────────────────────────────────────────────────────
TOTAL_STEPS=5
CURRENT_STEP=0

advance_step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "\n${DIM}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC}"
}

# ── Error handler ──────────────────────────────────────────────────────
cleanup_on_error() {
    echo ""
    err "Setup failed at step ${CURRENT_STEP}/${TOTAL_STEPS}"
    warn "Check the output above for details."
    warn "You can re-run this script to resume."
    exit 1
}
trap cleanup_on_error ERR

# ── Header ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║${NC}           ${BOLD}Anakot Agent — Full Setup${NC}                      ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}     Rebranded Anakot Agent with custom modifications       ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${DIM}Target:${NC}     ${TARGET_DIR}"
echo -e "  ${DIM}Upstream:${NC}   ${ANAKOT_REPO}"
echo -e "  ${DIM}Fork:${NC}       ${ANAKOT_REMOTE}"
echo ""

# ── Step 1: Clone latest Anakot Agent ──────────────────────────────────
step "Step 1: Clone latest Anakot Agent"
advance_step

CLONE_SKIPPED=false

if [ -d "${TARGET_DIR}/.git" ]; then
    warn "Target directory already exists: ${TARGET_DIR}"
    echo "  (1) Remove and reclone (clean slate)"
    echo "  (2) Skip clone — continue from existing (reuse partial install)"
    echo "  (3) Abort"
    read -p "Choose [1/2/3]: " -n 1 -r
    echo
    case "$REPLY" in
        1)
            rm -rf "${TARGET_DIR}"
            ;;
        2)
            CLONE_SKIPPED=true
            info "Skipping clone — continuing from existing install"
            ;;
        *)
            err "Aborted"
            exit 1
            ;;
    esac
fi

if [ "$CLONE_SKIPPED" = false ]; then
    info "Cloning from ${ANAKOT_REPO}..."

    # Clone with progress bar
    if command -v pv >/dev/null 2>&1; then
        git clone --depth 1 --progress "${ANAKOT_REPO}" "${TARGET_DIR}" 2>&1 | \
            pv -l -t -e -r -b -N "Cloning" >/dev/null
    else
        git clone --depth 1 --progress "${ANAKOT_REPO}" "${TARGET_DIR}" 2>&1 | \
            while IFS= read -r line; do
                printf "\r\033[K  %s" "${line}"
            done
        echo
    fi

    if [ ! -d "${TARGET_DIR}/.git" ]; then
        err "Clone failed — no .git directory found"
        exit 1
    fi
    ok "Clone complete"

    # Set up remotes
    git remote rename origin upstream 2>/dev/null || true
    git remote add origin "${ANAKOT_REMOTE}" 2>/dev/null || true
    ok "Remotes configured: upstream=Anakot, origin=fork"
fi

cd "${TARGET_DIR}"

# ── Step 2: Run actual agent setup ─────────────────────────────────────
step "Step 2: Run actual agent setup"
advance_step

# 2a. Install Python dependencies
substep "Installing Python dependencies"
info "Running uv sync..."
uv sync 2>&1 | while IFS= read -r line; do printf "\r\033[K  %s" "${line}"; done
echo
ok "Python dependencies installed"

# 2b. Install dev dependencies
substep "Installing dev dependencies"
info "Running uv sync --extra dev..."
uv sync --extra dev 2>&1 | while IFS= read -r line; do printf "\r\033[K  %s" "${line}"; done
echo
ok "Dev dependencies installed"

# 2c. Build TUI
substep "Building TUI"
cd ui-tui
info "Installing npm dependencies..."
npm install 2>&1 | tail -3
info "Building..."
npm run build 2>&1 | while IFS= read -r line; do printf "\r\033[K  Building TUI: %s" "${line}"; done
echo
cd ..
ok "TUI built"

# 2d. Build desktop app
substep "Building desktop app"
cd apps/desktop
info "Installing npm dependencies..."
npm install 2>&1 | tail -5
info "Building..."
npm run build 2>&1 | while IFS= read -r line; do printf "\r\033[K  Building desktop: %s" "${line}"; done
echo
cd ../..
ok "Desktop app built"

# 2e. Link global CLI binaries
substep "Linking global CLI binaries"
ln -sf "${TARGET_DIR}/.venv/bin/anakot" "${HOME}/.local/bin/anakot"
ln -sf "${TARGET_DIR}/.venv/bin/anakot-agent" "${HOME}/.local/bin/anakot-agent"
ln -sf "${TARGET_DIR}/.venv/bin/anakot-acp" "${HOME}/.local/bin/anakot-acp"
ok "Global binaries linked"

# 2f. Set up desktop symlink
substep "Setting up desktop symlink"
mkdir -p "${HOME}/.anakot"
ln -sfn "${TARGET_DIR}" "${HOME}/.anakot/anakot-agent"
touch "${TARGET_DIR}/.anakot-bootstrap-complete"
ok "Desktop symlink created"

# ── Step 3: Apply rebrand + custom patches ────────────────────────────
step "Step 3: Apply rebrand + custom patches"
advance_step

# 3a. Apply rebrand
substep "Applying rebrand (anakot → anakot)"
if [ ! -f "${REBRAND_PY}" ]; then
    err "Rebrand script not found at ${REBRAND_PY}"
    exit 1
fi
info "Running rebrand.py..."
python3 "${REBRAND_PY}" "${TARGET_DIR}" 2>&1 | while IFS= read -r line; do printf "\r\033[K  %s" "${line}"; done
echo
ok "Rebrand applied"

# 3b. Apply custom patches
substep "Applying custom patches"
if [ -f "${CUSTOM_PATCHES}" ]; then
    info "Running custom_patches.py..."
    python3 "${CUSTOM_PATCHES}" "${TARGET_DIR}" 2>&1 | while IFS= read -r line; do printf "\r\033[K  %s" "${line}"; done
    echo
    ok "Custom patches applied"
else
    warn "Custom patches script not found — skipping"
fi

# 3c. Re-sync dependencies
substep "Re-syncing dependencies"
info "Regenerating anakot* binaries..."
uv sync 2>&1 | while IFS= read -r line; do printf "\r\033[K  %s" "${line}"; done
echo
ok "Dependencies re-synced"

# 3d. Relink binaries
substep "Relinking global binaries"
ln -sf "${TARGET_DIR}/.venv/bin/anakot" "${HOME}/.local/bin/anakot"
ln -sf "${TARGET_DIR}/.venv/bin/anakot-agent" "${HOME}/.local/bin/anakot-agent"
ln -sf "${TARGET_DIR}/.venv/bin/anakot-acp" "${HOME}/.local/bin/anakot-acp"
ok "Global binaries relinked"

# 3e. Rebuild desktop
substep "Rebuilding desktop after rebrand"
cd apps/desktop
info "Building..."
npm run build 2>&1 | while IFS= read -r line; do printf "\r\033[K  Building desktop: %s" "${line}"; done
echo
cd "${TARGET_DIR}"
ok "Desktop rebuilt with Anakot branding"

# 3f. Install desktop system-wide
substep "Installing desktop system-wide"
if command -v pacman >/dev/null 2>&1; then
    APPIMAGE=$(find "${TARGET_DIR}/apps/desktop/release/" -name "*.AppImage" -type f 2>/dev/null | head -1)
    if [ -n "${APPIMAGE}" ]; then
        info "Installing AppImage desktop (Arch)..."
        sudo mkdir -p /opt/anakot-desktop
        EXTRACT_DIR="${HOME}/.anakot/tmp-extract"
        rm -rf "${EXTRACT_DIR}"
        mkdir -p "${EXTRACT_DIR}"
        cp "${APPIMAGE}" "${EXTRACT_DIR}/"
        chmod +x "${EXTRACT_DIR}/$(basename "${APPIMAGE}")"
        (cd "${EXTRACT_DIR}" && ./$(basename "${APPIMAGE}") --appimage-extract >/dev/null 2>&1)
        if [ -d "${EXTRACT_DIR}/squashfs-root" ]; then
            sudo rm -rf /opt/anakot-desktop/squashfs-root
            sudo mv "${EXTRACT_DIR}/squashfs-root" /opt/anakot-desktop/
            sudo chown -R "$(id -u):$(id -g)" /opt/anakot-desktop/squashfs-root
        fi
        rm -rf "${EXTRACT_DIR}"
        sudo tee /usr/share/applications/anakot-desktop.desktop > /dev/null << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Anakot
GenericName=AI Agent
Comment=The self-improving AI agent that grows with you
Exec=/opt/anakot-desktop/squashfs-root/AppRun
Icon=anakot-desktop
Terminal=false
Categories=Development;
MimeType=x-scheme-handler/anakot;
Keywords=ai;agent;assistant;anakot;nous;
StartupNotify=true
StartupWMClass=Anakot
EOF
        sudo ln -sf /opt/anakot-desktop/squashfs-root/AppRun /usr/local/bin/anakot-desktop

        # Install Anakot icon system-wide — prefer the current fork's Anakot logo,
        # fall back to the AppImage's bundled icon.
        CURRENT_FORK_ICON="${TARGET_DIR}/apps/desktop/public/apple-touch-icon.png"
        APPIMAGE_ICONS="/opt/anakot-desktop/squashfs-root/usr/share/icons/hicolor"
        ICON_INSTALLED=false

        for size in 256x256 512x512 1024x1024; do
            dst="/usr/share/icons/hicolor/${size}/apps/anakot-desktop.png"
            # Prefer current fork's Anakot logo (the girl with "N" badge)
            if [ -f "${CURRENT_FORK_ICON}" ]; then
                sudo mkdir -p "/usr/share/icons/hicolor/${size}/apps/"
                sudo cp "${CURRENT_FORK_ICON}" "${dst}"
                ICON_INSTALLED=true
            # Fallback: use AppImage's bundled icon
            elif [ -f "${APPIMAGE_ICONS}/${size}/apps/Anakot.png" ]; then
                sudo mkdir -p "/usr/share/icons/hicolor/${size}/apps/"
                sudo cp "${APPIMAGE_ICONS}/${size}/apps/Anakot.png" "${dst}"
                ICON_INSTALLED=true
            fi
        done

        if [ "${ICON_INSTALLED}" = true ]; then
            sudo gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
            ok "Desktop icon installed"
        else
            warn "Desktop icon: no source icons found"
        fi

        ok "Desktop installed (extracted AppImage)"
    else
        warn "No AppImage found — build it: cd apps/desktop && npm run dist:linux"
    fi
elif command -v dpkg >/dev/null 2>&1; then
    DEB_FILE=$(find "${TARGET_DIR}/apps/desktop/release/" -name "*.deb" -type f 2>/dev/null | head -1)
    if [ -n "${DEB_FILE}" ]; then
        sudo dpkg -i "${DEB_FILE}" 2>&1 || warn "dpkg install failed — try: sudo apt-get install -f"
        ok "Desktop .deb installed"
    else
        warn "No .deb file found — build it: cd apps/desktop && npm run dist:linux"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows — build NSIS installer and run it silently
    info "Building Windows NSIS installer..."
    cd apps/desktop
    npm run build 2>&1 | tail -5
    npm run dist:win:nsis 2>&1 | tail -10
    cd "${TARGET_DIR}"

    # Find the NSIS installer
    NSIS_INSTALLER=$(find "${TARGET_DIR}/apps/desktop/release/" -name "Anakot-*-win-*.exe" -type f 2>/dev/null | head -1)
    if [ -n "${NSIS_INSTALLER}" ]; then
        info "Running NSIS installer silently..."
        # NSIS silent install: /S flag, install to default location
        "${NSIS_INSTALLER}" //S 2>&1 || warn "NSIS installer exited with code $?"

        # Add install directory to PATH (user-level)
        INSTALL_DIR="${LOCALAPPDATA:-${HOME}/AppData/Local}/Programs/Anakot"
        if [ -d "${INSTALL_DIR}" ]; then
            # Add to user PATH via registry (PowerShell)
            powershell.exe -Command "
                \$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
                if (\$currentPath -notlike '*${INSTALL_DIR}*') {
                    [Environment]::SetEnvironmentVariable('Path', \"\$currentPath;${INSTALL_DIR}\", 'User')
                    Write-Host 'Added ${INSTALL_DIR} to user PATH'
                }
            " 2>&1 || warn "Could not update PATH — add ${INSTALL_DIR} manually"

            # Create Start Menu shortcut (NSIS does this, but ensure it exists)
            START_MENU_DIR="${APPDATA:-${HOME}/AppData/Roaming/Microsoft/Windows/Start Menu/Programs}/Anakot"
            mkdir -p "${START_MENU_DIR}"
            if [ -f "${INSTALL_DIR}/Anakot.exe" ]; then
                # Create a shortcut using PowerShell
                powershell.exe -Command "
                    \$WshShell = New-Object -ComObject WScript.Shell
                    \$Shortcut = \$WshShell.CreateShortcut('${START_MENU_DIR}/Anakot.lnk')
                    \$Shortcut.TargetPath = '${INSTALL_DIR}/Anakot.exe'
                    \$Shortcut.WorkingDirectory = '${INSTALL_DIR}'
                    \$Shortcut.Save()
                    Write-Host 'Start Menu shortcut created'
                " 2>&1 || warn "Could not create Start Menu shortcut"
            fi

            # Register anakot:// URL scheme via registry
            powershell.exe -Command "
                \$regPath = 'HKCU:\\Software\\Classes\\anakot'
                if (-not (Test-Path \$regPath)) {
                    New-Item -Path \$regPath -Force | Out-Null
                    Set-ItemProperty -Path \$regPath -Name '(Default)' -Value 'URL:Anakot Protocol'
                    Set-ItemProperty -Path \$regPath -Name 'URL Protocol' -Value ''
                    New-Item -Path \"\$regPath\\shell\\open\\command\" -Force | Out-Null
                    Set-ItemProperty -Path \"\$regPath\\shell\\open\\command\" -Name '(Default)' -Value '\"${INSTALL_DIR}\\Anakot.exe\" \"%1\"'
                    Write-Host 'Registered anakot:// URL scheme'
                }
            " 2>&1 || warn "Could not register URL scheme"

            ok "Desktop installed (Windows NSIS)"
        else
            warn "NSIS installer not found — run it manually from apps/desktop/release/"
        fi
    else
        warn "No Windows installer found — build it: cd apps/desktop && npm run dist:win:nsis"
    fi
else
    warn "No supported platform detected"
    warn "Build manually: cd apps/desktop && npm run dist:linux (or dist:win:nsis for Windows)"
fi

# ── Step 4: Sanity check ───────────────────────────────────────────────
step "Step 4: Sanity check"
advance_step

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        ok "${desc}"
        PASS=$((PASS + 1))
    else
        err "${desc}"
        FAIL=$((FAIL + 1))
    fi
}

check "anakot --version" ./anakot --version

VERSION_OUTPUT=$(./anakot --version 2>&1 || true)
if echo "${VERSION_OUTPUT}" | grep -q "Anakot Agent"; then
    ok "Version shows 'Anakot Agent'"
    PASS=$((PASS + 1))
else
    err "Version does not show 'Anakot Agent'"
    FAIL=$((FAIL + 1))
fi

check "anakot_constants imports" python3 -c "import anakot_constants"
check "anakot_logging imports" python3 -c "import anakot_logging"
check "anakot_state imports" python3 -c "import anakot_state"

ANAKOT_CLI_REFS=$(grep -rl "from anakot_cli\|import anakot_cli" --include="*.py" . 2>/dev/null | grep -v __pycache__ | grep -v rebrand | grep -v update_cmd_git | grep -v banner.py | wc -l || true)
if [ "${ANAKOT_CLI_REFS}" -eq 0 ]; then
    ok "No anakot_cli imports in code"
    PASS=$((PASS + 1))
else
    err "Found ${ANAKOT_CLI_REFS} files with anakot_cli imports"
    FAIL=$((FAIL + 1))
fi

check "Desktop logo present" test -f apps/desktop/public/anakot-logo.png
check "Desktop font present" test -f apps/desktop/public/staravenue.ttf

SYNTAX_ERRORS=$(python3 -c "
import ast, os
errors = []
for dirpath, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.git','node_modules','__pycache__','.venv','venv','dist','build'}]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(dirpath, f)
            try:
                with open(path) as fh:
                    ast.parse(fh.read())
            except SyntaxError:
                errors.append(path)
print(len(errors))
" 2>/dev/null)
if [ "${SYNTAX_ERRORS}" -eq 0 ]; then
    ok "No Python syntax errors"
    PASS=$((PASS + 1))
else
    err "Found ${SYNTAX_ERRORS} Python syntax errors"
    FAIL=$((FAIL + 1))
fi

ORIGIN_URL=$(git remote get-url origin 2>/dev/null || true)
if echo "${ORIGIN_URL}" | grep -q "anakot-agent"; then
    ok "Git origin points to anakot fork"
    PASS=$((PASS + 1))
else
    err "Git origin does not point to fork: ${ORIGIN_URL}"
    FAIL=$((FAIL + 1))
fi

# ── Summary ────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  Anakot Agent Setup Complete${NC}"
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${DIM}Target:${NC}     ${TARGET_DIR}"
echo -e "  ${DIM}Real Anakot:${NC} ${HOME}/.anakot/anakot-agent/ (untouched)"
echo -e "  ${DIM}Anakot:${NC}      ${TARGET_DIR} (rebranded)"
echo ""
echo -e "  ${GREEN}Checks passed: ${PASS}${NC}"
if [ "${FAIL}" -gt 0 ]; then
    echo -e "  ${RED}Checks failed: ${FAIL}${NC}"
    echo ""
    warn "Some checks failed. Review the output above."
    exit 1
fi
echo ""
echo -e "  ${GREEN}All checks passed!${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    anakot --version          → verify version"
echo -e "    anakot --help             → see all commands"
echo -e "    anakot-desktop            → launch desktop GUI"
echo ""
echo -e "  ${BOLD}To update from upstream:${NC}"
echo -e "    cd ${TARGET_DIR}"
echo -e "    git fetch upstream main"
echo -e "    git merge upstream/main"
echo -e "    python3 ${REBRAND_PY} ${TARGET_DIR}"
echo -e "    python3 ${CUSTOM_PATCHES} ${TARGET_DIR}"
echo -e "    git add -A && git commit -m 'sync: upstream + rebrand + custom'"
echo -e "    git push origin main"
echo -e "    uv sync"
echo ""
