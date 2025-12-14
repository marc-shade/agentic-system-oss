#!/bin/bash
# Setup script for agi-cluster plugin
# Configures cluster communication and verifies node connectivity

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}AGI-Cluster Plugin Setup${NC}"
echo "========================="

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$HOME/.claude/agi"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Plugin: $PLUGIN_DIR"
echo "  Config: $CONFIG_DIR"

# Create config directory
mkdir -p "$CONFIG_DIR"

# Copy cluster configuration if not exists
if [ ! -f "$CONFIG_DIR/cluster-topology.yaml" ]; then
    cp "$PLUGIN_DIR/config/cluster-topology.yaml" "$CONFIG_DIR/"
    echo -e "${GREEN}Created cluster-topology.yaml${NC}"
else
    echo -e "${YELLOW}cluster-topology.yaml exists, skipping${NC}"
fi

if [ ! -f "$CONFIG_DIR/node-profiles.yaml" ]; then
    cp "$PLUGIN_DIR/config/node-profiles.yaml" "$CONFIG_DIR/"
    echo -e "${GREEN}Created node-profiles.yaml${NC}"
else
    echo -e "${YELLOW}node-profiles.yaml exists, skipping${NC}"
fi

# Detect this node
THIS_NODE=$(hostname -s 2>/dev/null || hostname)
echo -e "\n${YELLOW}This node: $THIS_NODE${NC}"

# Test SSH connectivity to other nodes
echo -e "\n${YELLOW}Testing SSH connectivity...${NC}"

NODES=("mac-studio.local" "macpro51.local" "macbook-air-m3.local")

for node in "${NODES[@]}"; do
    # Skip self
    if [[ "$node" == *"$THIS_NODE"* ]]; then
        echo -e "  ${GREEN}$node: SELF${NC}"
        continue
    fi

    # Test SSH
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "marc@$node" "echo OK" 2>/dev/null; then
        echo -e "  ${GREEN}$node: OK${NC}"
    else
        echo -e "  ${YELLOW}$node: UNREACHABLE (may need SSH key setup)${NC}"
    fi
done

# Create shared inbox directory
INBOX_DIR="/mnt/agentic-system/cluster-inbox"
if [ -d "/mnt/agentic-system" ]; then
    mkdir -p "$INBOX_DIR"
    chmod 777 "$INBOX_DIR" 2>/dev/null || true
    echo -e "\n${GREEN}Created cluster inbox: $INBOX_DIR${NC}"
fi

# Install claude-flow if not present
echo -e "\n${YELLOW}Checking claude-flow...${NC}"
if command -v npx &> /dev/null; then
    if npx claude-flow --version &> /dev/null; then
        echo -e "${GREEN}claude-flow: OK${NC}"
    else
        echo -e "${YELLOW}Installing claude-flow...${NC}"
        npm install -g claude-flow 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}npm not found - claude-flow unavailable${NC}"
fi

# Verify MCP servers
echo -e "\n${YELLOW}Verifying MCP servers...${NC}"

for server in node-chat cluster-execution; do
    if [ -f "$PLUGIN_DIR/mcp/$server/server.py" ] || [ -L "$PLUGIN_DIR/mcp/$server" ]; then
        echo -e "  ${GREEN}$server: OK${NC}"
    else
        echo -e "  ${RED}$server: MISSING${NC}"
    fi
done

if [ -d "$PLUGIN_DIR/mcp/claude-flow" ] || [ -L "$PLUGIN_DIR/mcp/claude-flow" ]; then
    echo -e "  ${GREEN}claude-flow: OK${NC}"
else
    echo -e "  ${YELLOW}claude-flow: Using global installation${NC}"
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo ""
echo "Cluster configuration:"
echo "  Topology: $CONFIG_DIR/cluster-topology.yaml"
echo "  Profiles: $CONFIG_DIR/node-profiles.yaml"
echo ""
echo "Next steps:"
echo "  1. Edit cluster-topology.yaml to match your nodes"
echo "  2. Setup SSH keys: ssh-copy-id marc@<node>"
echo "  3. Restart Claude Code to load MCP servers"
echo "  4. Run /cluster-status to verify connectivity"
