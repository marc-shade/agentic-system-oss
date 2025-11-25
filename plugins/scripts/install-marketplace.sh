#!/bin/bash
# Install AGI Marketplace for Claude Code
# Usage: ./install-marketplace.sh [target-directory]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AGI Marketplace Installer${NC}"
echo "=========================="

# Determine target directory
TARGET_DIR="${1:-$HOME/.claude/marketplaces/agentic-marketplace}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Source: $PLUGIN_ROOT"
echo "  Target: $TARGET_DIR"

# Create target directory
echo -e "\n${YELLOW}Creating target directory...${NC}"
mkdir -p "$TARGET_DIR"

# Copy marketplace
echo -e "${YELLOW}Copying marketplace files...${NC}"
cp -r "$PLUGIN_ROOT/marketplace/"* "$TARGET_DIR/"

# Copy plugins
echo -e "${YELLOW}Copying plugins...${NC}"
mkdir -p "$TARGET_DIR/../plugins"
cp -r "$PLUGIN_ROOT/plugins/"* "$TARGET_DIR/../plugins/"

# Update manifest paths to be relative
echo -e "${YELLOW}Updating manifest paths...${NC}"
# The manifest uses relative paths, so no changes needed

# Create settings entry
SETTINGS_FILE="$HOME/.claude/settings.json"
echo -e "\n${YELLOW}Updating Claude Code settings...${NC}"

if [ -f "$SETTINGS_FILE" ]; then
    # Check if marketplace already exists
    if grep -q "agentic-marketplace" "$SETTINGS_FILE"; then
        echo -e "${YELLOW}Marketplace already in settings, skipping...${NC}"
    else
        echo -e "${RED}Settings file exists but needs manual update.${NC}"
        echo "Add this to your $SETTINGS_FILE:"
        echo ""
        echo '  "plugins": {'
        echo '    "marketplaces": ['
        echo '      {'
        echo '        "name": "agentic-marketplace",'
        echo "        \"path\": \"$TARGET_DIR\""
        echo '      }'
        echo '    ]'
        echo '  }'
    fi
else
    # Create new settings file
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    cat > "$SETTINGS_FILE" << EOF
{
  "plugins": {
    "marketplaces": [
      {
        "name": "agentic-marketplace",
        "path": "$TARGET_DIR"
      }
    ]
  }
}
EOF
    echo -e "${GREEN}Created settings file with marketplace.${NC}"
fi

# Create config directory
echo -e "\n${YELLOW}Creating config directory...${NC}"
mkdir -p "$HOME/.claude/agi"

# Copy default config if not exists
if [ ! -f "$HOME/.claude/agi/config.yaml" ]; then
    cp "$TARGET_DIR/../plugins/agi-core/config/defaults.yaml" "$HOME/.claude/agi/config.yaml"
    echo -e "${GREEN}Created default config at ~/.claude/agi/config.yaml${NC}"
else
    echo -e "${YELLOW}Config already exists, skipping...${NC}"
fi

echo -e "\n${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code"
echo "  2. Run: /plugin install agi-core@agentic-marketplace"
echo "  3. Run: /agi-init to initialize AGI session"
echo ""
echo "For higher tiers:"
echo "  /plugin install agi-memory@agentic-marketplace   (+ SQLite persistence)"
echo "  /plugin install agi-extended@agentic-marketplace (+ Docker services)"
echo "  /plugin install agi-cluster@agentic-marketplace  (+ Multi-node)"
