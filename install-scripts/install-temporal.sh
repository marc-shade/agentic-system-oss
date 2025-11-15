#!/bin/bash
# Install Temporal - Workflow Engine

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📦 Installing Temporal..."
echo "========================="
echo ""

# Check if already installed
if command -v temporal &> /dev/null; then
    echo -e "${YELLOW}⚠ Temporal already installed${NC}"
    temporal --version
    exit 0
fi

# Detect OS
OS=$(uname -s)

case "$OS" in
    Darwin)
        echo "Detected macOS"
        if command -v brew &> /dev/null; then
            echo "Installing via Homebrew..."
            brew install temporal
        else
            echo -e "${RED}✗ Homebrew required for macOS installation${NC}"
            echo "Install Homebrew: https://brew.sh"
            exit 1
        fi
        ;;
    Linux)
        echo "Detected Linux"
        echo "Installing via official script..."
        curl -sSf https://temporal.download/cli.sh | sh
        # Add to PATH
        export PATH="$HOME/.temporalio/bin:$PATH"
        echo 'export PATH="$HOME/.temporalio/bin:$PATH"' >> ~/.bashrc
        ;;
    *)
        echo -e "${RED}✗ Unsupported OS: $OS${NC}"
        exit 1
        ;;
esac

# Verify installation
if command -v temporal &> /dev/null; then
    echo ""
    echo -e "${GREEN}✓ Temporal installed successfully${NC}"
    temporal --version
    echo ""
    echo "Note: Use 'temporal server start-dev' to start Temporal server"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi
