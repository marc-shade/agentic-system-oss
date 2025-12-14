#!/bin/bash
#
# Cluster Memory Deployment Script
# Run this on each node to set up cluster memory integration
#

set -e


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

echo "🌐 Cluster Memory System Deployment"
echo "===================================="
echo ""

# Detect current node
if [[ $(hostname) == *"Mac-Studio"* ]]; then
    NODE_ID="mac-studio"
    PERSONA="Orchestrator"
elif [[ $(hostname) == *"MacBook-Air"* ]]; then
    NODE_ID="macbook-air"
    PERSONA="Researcher"
elif [[ $(hostname) == *"MacBook-Pro"* ]]; then
    NODE_ID="macbook-pro"
    PERSONA="Developer"
else
    echo "❌ Unknown node - cannot auto-detect configuration"
    exit 1
fi

echo "📍 Detected Node: $NODE_ID ($PERSONA)"
echo ""

# Check if deployment package exists
DEPLOY_DIR="$STORAGE_BASE/cluster-deployment"
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "❌ Deployment directory not found: $DEPLOY_DIR"
    exit 1
fi

# Check if MCP server directory exists
MCP_DIR="$HOME/Documents/Cline/MCP/enhanced-memory-mcp"
if [ ! -d "$MCP_DIR" ]; then
    echo "❌ MCP server directory not found: $MCP_DIR"
    echo "   Please ensure enhanced-memory-mcp is installed"
    exit 1
fi

echo "Step 1: Copying cluster_memory.py"
cp "$DEPLOY_DIR/cluster_memory.py" "$MCP_DIR/"
echo "✅ cluster_memory.py installed"
echo ""

echo "Step 2: Verifying node configuration"
NODE_CONFIG="$HOME/.claude/node-config.json"
if [ -f "$NODE_CONFIG" ]; then
    echo "✅ Node configuration found"
    echo "   Node ID: $(jq -r '.node_id' $NODE_CONFIG)"
else
    echo "⚠️  Node configuration not found at $NODE_CONFIG"
    echo "   Creating default configuration..."

    mkdir -p "$HOME/.claude"
    cat > "$NODE_CONFIG" <<EOF
{
  "node_id": "$NODE_ID",
  "persona_config": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/persona_state.json",
  "memory": {
    "local_db": "$HOME/Documents/Cline/MCP/enhanced-memory-mcp/memory.db",
    "personal_db": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/personal_memories.db",
    "shared_db": "$STORAGE_BASE/databases/cluster/shared_memories.db",
    "node_registry_db": "$STORAGE_BASE/databases/cluster/node_registry.db"
  },
  "cluster": {
    "enabled": true,
    "discovery": {
      "method": "bonjour",
      "broadcast_interval": 30,
      "service_name": "_agentic-cluster._tcp"
    }
  },
  "sync": {
    "enabled": true,
    "strategy": "eventual_consistency",
    "conflict_resolution": "last_write_wins_with_node_priority",
    "node_priority": {
      "mac-studio": 1,
      "macbook-air": 2,
      "macbook-pro": 2
    }
  }
}
EOF
    echo "✅ Created node configuration"
fi
echo ""

echo "Step 3: Ensuring cluster database directories exist"
CLUSTER_DB_DIR="$STORAGE_BASE/databases/cluster"
NODE_DB_DIR="$CLUSTER_DB_DIR/nodes/$NODE_ID"

mkdir -p "$NODE_DB_DIR"
echo "✅ Directories created"
echo ""

echo "Step 4: Running test"
cd "$MCP_DIR"
if python3 "$DEPLOY_DIR/test_cluster_memory.py"; then
    echo ""
    echo "✅ Cluster memory test passed!"
else
    echo ""
    echo "⚠️  Test failed - please check error messages above"
    echo "   Common issues:"
    echo "   - Empty database files (solution: delete and rerun)"
    echo "   - Permission issues on shared storage"
fi
echo ""

echo "Step 5: Integration status"
echo "ℹ️  To complete integration, server.py needs cluster memory handlers"
echo "   See INTEGRATION_CHANGES.md for details"
echo ""

echo "===================================="
echo "📊 Deployment Summary"
echo "===================================="
echo "Node ID: $NODE_ID"
echo "Persona: $PERSONA"
echo "Personal DB: $NODE_DB_DIR/personal_memories.db"
echo "Shared DB: $CLUSTER_DB_DIR/shared_memories.db"
echo ""
echo "Next steps:"
echo "1. Apply server.py integration (if not already done)"
echo "2. Restart Claude Code"
echo "3. Test cross-node memory sharing"
echo ""
echo "✅ Deployment complete on $NODE_ID!"
