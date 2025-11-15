#!/bin/bash
# Install AutoKitteh - Event-Driven Workflows

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📦 Installing AutoKitteh..."
echo "============================"
echo ""

# Check if already installed
if command -v ak &> /dev/null; then
    echo -e "${YELLOW}⚠ AutoKitteh already installed${NC}"
    ak version
    exit 0
fi

# Install via official script (works on macOS and Linux)
echo "Installing via official script..."
curl -fsSL https://get.autokitteh.com | sh

# Verify installation
if command -v ak &> /dev/null; then
    echo ""
    echo -e "${GREEN}✓ AutoKitteh installed successfully${NC}"
    ak version
    echo ""
    echo "Note: Use 'ak up' to start AutoKitteh server"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi
