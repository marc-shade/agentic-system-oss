#!/bin/bash
# Master Installer - Install All Agentic System Components
# This script can be run by Claude Code to install everything automatically

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Agentic System - Master Installer"
echo "====================================="
echo ""

# Get installation profile from argument or interactive prompt
PROFILE="${1:-}"

if [ -z "$PROFILE" ]; then
    echo "Select installation profile:"
    echo "  1) minimal    - Development/testing (Claude Code + Python + Git only)"
    echo "  2) standard   - Production node (all AI platforms + core infrastructure)"
    echo "  3) full       - Complete system (everything including monitoring)"
    echo "  4) custom     - Choose individual components"
    echo ""
    read -p "Enter choice (1-4): " CHOICE

    case "$CHOICE" in
        1) PROFILE="minimal" ;;
        2) PROFILE="standard" ;;
        3) PROFILE="full" ;;
        4) PROFILE="custom" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

echo ""
echo "Installation Profile: $PROFILE"
echo ""

# Make all install scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Installation tracking
INSTALL_RESULTS=()

# Helper function to run installer
run_installer() {
    local name="$1"
    local script="$2"
    local optional="${3:-false}"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Installing: $name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ -f "$SCRIPT_DIR/$script" ]; then
        if bash "$SCRIPT_DIR/$script"; then
            INSTALL_RESULTS+=("✓ $name")
            echo -e "${GREEN}✓ $name installation complete${NC}"
        else
            if [ "$optional" = "true" ]; then
                INSTALL_RESULTS+=("⚠ $name (optional - failed)")
                echo -e "${YELLOW}⚠ $name installation failed (optional - continuing)${NC}"
            else
                INSTALL_RESULTS+=("✗ $name (FAILED)")
                echo -e "${RED}✗ $name installation failed${NC}"
                return 1
            fi
        fi
    else
        echo -e "${RED}✗ Installer script not found: $script${NC}"
        return 1
    fi
}

# === Prerequisites Check ===
echo -e "${BLUE}Checking Prerequisites...${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Please install Python 3.10+ first:"
    echo "  macOS: brew install python@3.11"
    echo "  Linux: apt install python3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git not found${NC}"
    echo "Please install Git first"
    exit 1
fi
echo -e "${GREEN}✓ Git $(git --version | awk '{print $3}')${NC}"

# Check Node.js (required for Gemini CLI)
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠ Node.js not found (required for Gemini CLI)${NC}"
    echo "Install from: https://nodejs.org/"
else
    echo -e "${GREEN}✓ Node.js $(node --version)${NC}"
fi

echo ""

# === Component Installation Based on Profile ===

case "$PROFILE" in
    minimal)
        echo "Minimal installation - skipping additional components"
        echo "You have:"
        echo "  - Claude Code (already installed)"
        echo "  - Python ${PYTHON_VERSION}"
        echo "  - Git"
        ;;

    standard)
        echo "Standard installation - AI platforms + core infrastructure"
        echo ""

        # AI Platforms
        run_installer "Ollama" "install-ollama.sh"
        # Note: OpenAI Codex and Gemini CLI require manual auth, skip in automated install

        # Core Infrastructure
        run_installer "Qdrant" "install-qdrant.sh"
        run_installer "Temporal" "install-temporal.sh"
        run_installer "AutoKitteh" "install-autokitteh.sh"
        ;;

    full)
        echo "Full installation - everything including monitoring"
        echo ""

        # AI Platforms
        run_installer "Ollama" "install-ollama.sh"

        # Core Infrastructure
        run_installer "Qdrant" "install-qdrant.sh"
        run_installer "Temporal" "install-temporal.sh"
        run_installer "AutoKitteh" "install-autokitteh.sh"

        # Monitoring Stack (optional)
        run_installer "Monitoring Stack" "install-monitoring.sh" "true"
        ;;

    custom)
        echo "Custom installation - choose components"
        echo ""

        read -p "Install Ollama? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_installer "Ollama" "install-ollama.sh"
        fi

        read -p "Install Qdrant? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_installer "Qdrant" "install-qdrant.sh"
        fi

        read -p "Install Temporal? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_installer "Temporal" "install-temporal.sh"
        fi

        read -p "Install AutoKitteh? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_installer "AutoKitteh" "install-autokitteh.sh"
        fi

        read -p "Install Monitoring Stack? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_installer "Monitoring Stack" "install-monitoring.sh" "true"
        fi
        ;;
esac

# === Installation Summary ===
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Installation Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ${#INSTALL_RESULTS[@]} -gt 0 ]; then
    echo "Results:"
    for result in "${INSTALL_RESULTS[@]}"; do
        echo "  $result"
    done
else
    echo "No new components installed (minimal profile or all already present)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Install Python dependencies:"
echo "   pip3 install -r requirements.txt"
echo ""
echo "2. Set up authentication:"
echo "   ./bootstrap.sh"
echo ""
echo "3. Configure MCP servers:"
echo "   ./configure-all-mcps.sh"
echo ""
echo "4. Start cluster daemon:"
echo "   cd cluster-deployment && ./start_daemon.sh"
echo ""
echo "5. Verify installation:"
echo "   ./verify-onboarding.sh"
echo ""
echo "See SYSTEM_REQUIREMENTS.md for detailed information."
echo ""
