#!/bin/bash
# Setup script for agi-memory plugin
# Creates databases and initializes MCP servers

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}AGI-Memory Plugin Setup${NC}"
echo "========================"

# Get plugin directory
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="$HOME/.claude/agi/databases"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Plugin: $PLUGIN_DIR"
echo "  Databases: $DB_DIR"

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python 3.10+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}Python $PYTHON_VERSION OK${NC}"

# Create database directory
echo -e "\n${YELLOW}Creating database directory...${NC}"
mkdir -p "$DB_DIR"

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
pip3 install --quiet mcp sqlite3 aiosqlite 2>/dev/null || true

# Check Node.js for Ember
echo -e "\n${YELLOW}Checking Node.js for Ember...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Node.js $NODE_VERSION OK${NC}"

    # Install Ember dependencies
    if [ -d "$PLUGIN_DIR/mcp/ember" ]; then
        echo -e "${YELLOW}Installing Ember dependencies...${NC}"
        cd "$PLUGIN_DIR/mcp/ember"
        npm install --quiet 2>/dev/null || true
        cd - > /dev/null
    fi
else
    echo -e "${YELLOW}Node.js not found - Ember MCP will be unavailable${NC}"
fi

# Initialize databases
echo -e "\n${YELLOW}Initializing databases...${NC}"
python3 "$PLUGIN_DIR/scripts/init-databases.py" --db-dir "$DB_DIR"

# Verify MCP servers
echo -e "\n${YELLOW}Verifying MCP servers...${NC}"

# Check agent-runtime
if [ -f "$PLUGIN_DIR/mcp/agent-runtime/server.py" ]; then
    echo -e "${GREEN}  agent-runtime: OK${NC}"
else
    echo -e "${RED}  agent-runtime: MISSING${NC}"
fi

# Check agi
if [ -f "$PLUGIN_DIR/mcp/agi/server.py" ]; then
    echo -e "${GREEN}  agi: OK${NC}"
else
    echo -e "${RED}  agi: MISSING${NC}"
fi

# Check ember
if [ -f "$PLUGIN_DIR/mcp/ember/dist/index.js" ]; then
    echo -e "${GREEN}  ember: OK${NC}"
else
    echo -e "${YELLOW}  ember: Not built (run 'npm run build' in mcp/ember)${NC}"
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo ""
echo "MCP servers configured in plugin's .mcp.json"
echo "Databases initialized at: $DB_DIR"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code to load MCP servers"
echo "  2. Run /agi-goals to manage goals"
echo "  3. Run /agi-consolidate to process learnings"
