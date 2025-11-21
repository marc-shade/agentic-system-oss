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
        NODE_TYPE="orchestrator"
        CAPABILITIES='["orchestration","heavy-processing","coordination","mlx-gpu"]'
        STORAGE_BASE="/Volumes/SSDRAID0/agentic-system"
        HARDWARE='{"model": "Mac Studio", "chip": "Apple M2 Max", "storage": "8TB RAID0"}'
        ;;
    "Marcs-MacBook-Air.local"|*"MacBook-Air"*)
        NODE_ID="macbook-air-m3"
        PERSONA="mobile-researcher"
        PRIORITY=4
        NODE_TYPE="distributed-worker"
        CAPABILITIES='["research","lightweight-processing","mobile-operations"]'
        STORAGE_BASE="$HOME/agentic-system"
        HARDWARE='{"model": "MacBook Air", "chip": "Apple M3", "storage": "500GB SSD"}'
        ;;
    "completeu-server"*|*"completeu"*)
        NODE_ID="completeu-server"
        PERSONA="inference-server"
        PRIORITY=2
        NODE_TYPE="distributed-worker"
        CAPABILITIES='["ollama-inference","model-serving","api-endpoints"]'
        STORAGE_BASE="$HOME/agentic-system"
        HARDWARE='{"model": "Mac Studio", "chip": "Apple M2 Ultra", "storage": "2TB SSD"}'
        ;;
    "macpro51"*|*"macpro"*)
        NODE_ID="macpro51"
        PERSONA="linux-worker"
        PRIORITY=3
        NODE_TYPE="distributed-worker"
        CAPABILITIES='["linux-operations","x86-tasks","containerization","ollama-inference"]'
        STORAGE_BASE="/mnt/agentic-system"
        HARDWARE='{"model": "Mac Pro 5,1", "chip": "Intel Xeon", "os": "Fedora 43", "storage": "4TB HDD"}'
        ;;
    "macmini.fios-router.home")
        NODE_ID="macmini"
        PERSONA="worker"
        PRIORITY=5
        NODE_TYPE="distributed-worker"
        CAPABILITIES='["background-tasks","monitoring"]'
        STORAGE_BASE="$HOME/agentic-system"
        HARDWARE='{"model": "Mac mini", "chip": "Apple M1", "storage": "256GB SSD"}'
        ;;
    *)
        echo -e "${RED}❌ Unknown hostname: $HOSTNAME${NC}"
        echo "   Please configure this node manually."
        exit 1
        ;;
esac

echo -e "   ${GREEN}✅ Identified as: $NODE_ID ($PERSONA)${NC}"
echo -e "   Type: $NODE_TYPE"
echo -e "   Priority: $PRIORITY"
echo -e "   Storage: $STORAGE_BASE"

# 2. Check if storage base exists
echo -e "\n${BLUE}2. Verifying Storage Path${NC}"
if [ ! -d "$STORAGE_BASE" ]; then
    echo -e "${YELLOW}⚠️  Storage base does not exist: $STORAGE_BASE${NC}"
    echo "   Creating storage base..."
    mkdir -p "$STORAGE_BASE"
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
  "node_type": "$NODE_TYPE",
  "persona": "$PERSONA",
  "priority": $PRIORITY,
  "capabilities": $CAPABILITIES,
  "hardware": $HARDWARE,
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

# 5. Initialize Node Registry Database
echo -e "\n${BLUE}5. Initializing Node Registry${NC}"
NODE_REGISTRY_DB="$STORAGE_BASE/databases/cluster/node_registry.db"

if [ ! -f "$NODE_REGISTRY_DB" ]; then
    echo "   Creating node registry database..."
    sqlite3 "$NODE_REGISTRY_DB" << EOSQL
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL UNIQUE,
    node_name TEXT NOT NULL,
    role TEXT NOT NULL,
    hardware TEXT,
    capabilities TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    metadata TEXT
);
EOSQL
fi

# Register this node
echo "   Registering node in registry..."
sqlite3 "$NODE_REGISTRY_DB" << EOSQL
INSERT OR REPLACE INTO nodes (node_id, node_name, role, hardware, capabilities, status, metadata)
VALUES (
    '$NODE_ID',
    '$PERSONA',
    '$NODE_TYPE',
    '$HARDWARE',
    '$CAPABILITIES',
    'active',
    '{"priority": $PRIORITY, "storage_base": "$STORAGE_BASE"}'
);
EOSQL

echo -e "   ${GREEN}✅ Node registered in cluster${NC}"

# 6. Summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ Node Initialization Complete!${NC}"
echo -e "\n${BLUE}Node Information:${NC}"
echo "   Node ID: $NODE_ID"
echo "   Type: $NODE_TYPE"
echo "   Persona: $PERSONA"
echo "   Priority: $PRIORITY"
echo "   Storage: $STORAGE_BASE"
echo "   Config: $NODE_CONFIG"
echo "   Registry: $NODE_REGISTRY_DB"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "   1. Cluster registry updated with this node"
echo "   2. Start cluster-node-api.py to enable cluster communication"
echo "   3. Test cluster connectivity with other nodes"
echo ""
