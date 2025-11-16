#!/bin/bash
# Agentic System - Node Initialization Script
# Run this on any node to set up cluster configuration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 Agentic Network Node Initialization${NC}"
echo "============================================================"

# 1. Detect Current Node
HOSTNAME=$(hostname)
echo -e "\n${BLUE}1. Detecting Current Node${NC}"
echo "   Hostname: $HOSTNAME"

# Map hostname to node configuration
case "$HOSTNAME" in
    "Marcs-Mac-Studio.local")
        NODE_ID="mac-studio"
        PERSONA="orchestrator"
        PRIORITY=1
        STORAGE_BASE="/mnt/agentic-system"
        ;;
    "Marcs-MacBook-Air.local")
        NODE_ID="macbook-air"
        PERSONA="researcher"
        PRIORITY=2
        STORAGE_BASE="/Volumes/FILES/agentic-system"
        ;;
    "completeu-server.local")
        NODE_ID="completeu-server"
        PERSONA="server"
        PRIORITY=3
        STORAGE_BASE="/Volumes/FILES/agentic-system"
        ;;
    "macmini.fios-router.home")
        NODE_ID="macmini"
        PERSONA="worker"
        PRIORITY=4
        STORAGE_BASE="/Users/marc/agentic-system"
        ;;
    *)
        echo -e "${RED}❌ Unknown hostname: $HOSTNAME${NC}"
        echo "   Please configure this node manually."
        exit 1
        ;;
esac

echo -e "   ${GREEN}✅ Identified as: $NODE_ID ($PERSONA)${NC}"
echo -e "   Priority: $PRIORITY"
echo -e "   Storage: $STORAGE_BASE"

# 2. Check if storage base exists
echo -e "\n${BLUE}2. Verifying Storage Path${NC}"
if [ ! -d "$STORAGE_BASE" ]; then
    echo -e "${RED}❌ Storage base does not exist: $STORAGE_BASE${NC}"
    echo "   Please ensure the volume is mounted."
    exit 1
fi
echo -e "   ${GREEN}✅ Storage path exists${NC}"

# 3. Create Directory Structure
echo -e "\n${BLUE}3. Creating Directory Structure${NC}"
mkdir -p "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID"
mkdir -p "$STORAGE_BASE/databases/cluster"
mkdir -p "$STORAGE_BASE/logs"
mkdir -p "$STORAGE_BASE/mcp-servers"
mkdir -p "$STORAGE_BASE/intelligent-agents"
mkdir -p "$STORAGE_BASE/cluster-deployment"
mkdir -p "$STORAGE_BASE/workflows"
mkdir -p "$STORAGE_BASE/scripts"
mkdir -p ~/.claude
echo -e "   ${GREEN}✅ Directories created${NC}"

# 4. Create Node Configuration
echo -e "\n${BLUE}4. Creating Node Configuration${NC}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
NODE_CONFIG="$HOME/.claude/node-config.json"

cat > "$NODE_CONFIG" << EOF
{
  "node_id": "$NODE_ID",
  "persona": "$PERSONA",
  "priority": $PRIORITY,
  "created_at": "$TIMESTAMP",
  "storage": {
    "base": "$STORAGE_BASE",
    "databases": "$STORAGE_BASE/databases",
    "logs": "$STORAGE_BASE/logs"
  },
  "memory": {
    "local_db": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/local_memory.db",
    "personal_db": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/personal_memories.db",
    "shared_db": "$STORAGE_BASE/databases/cluster/shared_memories.db",
    "node_registry": "$STORAGE_BASE/databases/cluster/node_registry.db"
  }
}
EOF

echo -e "   ${GREEN}✅ Configuration created: $NODE_CONFIG${NC}"

# 5. Check Python Dependencies
echo -e "\n${BLUE}5. Verifying Python Dependencies${NC}"
if [ -f "$STORAGE_BASE/intelligent-agents/requirements.txt" ]; then
    echo "   Installing dependencies..."
    pip3 install -r "$STORAGE_BASE/intelligent-agents/requirements.txt" --user --quiet
    echo -e "   ${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "   ${YELLOW}⚠️  requirements.txt not found${NC}"
    echo "   This node may need components deployed first."
fi

# 6. Test Cluster Memory
echo -e "\n${BLUE}6. Testing Cluster Memory${NC}"
if [ -f "$STORAGE_BASE/cluster-deployment/test_cluster_memory.py" ]; then
    cd "$STORAGE_BASE/cluster-deployment"
    echo "   Running cluster memory tests..."
    if python3 test_cluster_memory.py > /tmp/cluster_test_output.txt 2>&1; then
        echo -e "   ${GREEN}✅ All cluster memory tests passed${NC}"
        # Show summary
        grep "✅" /tmp/cluster_test_output.txt | head -5
    else
        echo -e "   ${RED}❌ Cluster memory tests failed${NC}"
        tail -20 /tmp/cluster_test_output.txt
    fi
else
    echo -e "   ${YELLOW}⚠️  Cluster memory tests not found${NC}"
    echo "   This node may need components deployed first."
fi

# 7. Check MCP Configuration
echo -e "\n${BLUE}7. Checking MCP Configuration${NC}"
MCP_CONFIG="$HOME/.claude.json"
if [ -f "$MCP_CONFIG" ]; then
    echo -e "   ${GREEN}✅ MCP config exists: $MCP_CONFIG${NC}"

    # Check for required servers
    REQUIRED_SERVERS=("enhanced-memory-mcp" "agent-runtime-mcp" "ember-mcp")
    for server in "${REQUIRED_SERVERS[@]}"; do
        if grep -q "\"$server\"" "$MCP_CONFIG"; then
            echo -e "   ${GREEN}✅ $server configured${NC}"
        else
            echo -e "   ${YELLOW}⚠️  $server not found${NC}"
        fi
    done
else
    echo -e "   ${YELLOW}⚠️  MCP config not found${NC}"
    echo "   You may need to create $MCP_CONFIG manually."
fi

# 8. Summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ Node Initialization Complete!${NC}"
echo -e "\n${BLUE}Node Information:${NC}"
echo "   Node ID: $NODE_ID"
echo "   Persona: $PERSONA"
echo "   Priority: $PRIORITY"
echo "   Storage: $STORAGE_BASE"
echo "   Config: $NODE_CONFIG"

echo -e "\n${BLUE}Next Steps:${NC}"
if [ ! -f "$MCP_CONFIG" ]; then
    echo "   1. Create MCP configuration at $MCP_CONFIG"
    echo "      Add enhanced-memory-mcp, agent-runtime-mcp, ember-mcp servers"
fi
echo "   2. Restart Claude Code to load MCP servers"
echo "   3. Test cluster connectivity with other nodes"
echo ""
