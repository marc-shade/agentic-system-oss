#!/bin/bash
# Agentic System - Multi-Node Deployment Script
# Deploys latest MCP servers, agents, and systems to remote nodes

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

NODE_HOST="${1:-}"
NODE_NAME="${2:-}"

if [ -z "$NODE_HOST" ] || [ -z "$NODE_NAME" ]; then
    echo "Usage: $0 <node-host> <node-name>"
    echo "Example: $0 Marcs-MacBook-Air.local macbook-air"
    exit 1
fi

echo "🚀 Deploying to $NODE_NAME ($NODE_HOST)..."

# Define source and target paths
SOURCE_BASE="$STORAGE_BASE"
TARGET_BASE="$STORAGE_BASE"

# Create remote directory structure
echo "📁 Creating directory structure on $NODE_NAME..."
ssh marc@$NODE_HOST "mkdir -p $TARGET_BASE/{mcp-servers,intelligent-agents,databases,scripts,logs,config}"

# 1. Deploy MCP Servers
echo "📦 Deploying MCP servers..."
rsync -avz --delete \
  "$SOURCE_BASE/mcp-servers/enhanced-memory-mcp/" \
  "marc@$NODE_HOST:$TARGET_BASE/mcp-servers/enhanced-memory-mcp/"

rsync -avz --delete \
  "$SOURCE_BASE/mcp-servers/agent-runtime-mcp/" \
  "marc@$NODE_HOST:$TARGET_BASE/mcp-servers/agent-runtime-mcp/"

rsync -avz --delete \
  "$SOURCE_BASE/mcp-servers/ember-mcp/" \
  "marc@$NODE_HOST:$TARGET_BASE/mcp-servers/ember-mcp/"

# 2. Deploy Intelligent Agents
echo "🤖 Deploying intelligent agents framework..."
rsync -avz --delete \
  "$SOURCE_BASE/intelligent-agents/" \
  "marc@$NODE_HOST:$TARGET_BASE/intelligent-agents/"

# 3. Deploy Cluster Memory System
echo "💾 Deploying cluster memory system..."
rsync -avz \
  "$SOURCE_BASE/cluster-deployment/" \
  "marc@$NODE_HOST:$TARGET_BASE/cluster-deployment/"

# 4. Deploy Self-Healing System
echo "🛡️  Deploying self-healing and optimization systems..."
rsync -avz --delete \
  "$SOURCE_BASE/intelligent-self-healing/" \
  "marc@$NODE_HOST:$TARGET_BASE/intelligent-self-healing/"

rsync -avz --delete \
  "$SOURCE_BASE/workflows/" \
  "marc@$NODE_HOST:$TARGET_BASE/workflows/"

# 5. Deploy Scripts
echo "📜 Deploying utility scripts..."
rsync -avz \
  "$SOURCE_BASE/scripts/" \
  "marc@$NODE_HOST:$TARGET_BASE/scripts/"

# 6. Deploy CLAUDE.md
echo "📄 Deploying CLAUDE.md..."
rsync -avz \
  "$SOURCE_BASE/CLAUDE.md" \
  "marc@$NODE_HOST:$TARGET_BASE/"

# 7. Create node configuration
echo "⚙️  Creating node configuration..."
ssh marc@$NODE_HOST "cat > ~/.claude/node-config.json" << EOF
{
  "node_id": "$NODE_NAME",
  "persona": "$([ "$NODE_NAME" = "macbook-air" ] && echo "researcher" || echo "developer")",
  "priority": 2,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "storage": {
    "base": "$TARGET_BASE",
    "databases": "$TARGET_BASE/databases",
    "logs": "$TARGET_BASE/logs"
  }
}
EOF

# 8. Install Python dependencies on remote node
echo "🐍 Installing Python dependencies..."
ssh marc@$NODE_HOST "cd $TARGET_BASE/intelligent-agents && pip3 install -r requirements.txt --user 2>&1 | tail -5"

# 9. Run cluster deployment
echo "🌐 Running cluster deployment on $NODE_NAME..."
ssh marc@$NODE_HOST "cd $TARGET_BASE/cluster-deployment && ./deploy-to-node.sh"

# 10. Create symbolic link for easy access
echo "🔗 Creating symbolic links..."
ssh marc@$NODE_HOST "ln -sf $TARGET_BASE ~/agentic-system 2>/dev/null || true"

echo "✅ Deployment to $NODE_NAME complete!"
echo ""
echo "Next steps on $NODE_NAME:"
echo "  1. Restart Claude Code to load new MCP servers"
echo "  2. Verify cluster memory: python3 $TARGET_BASE/cluster-deployment/test_cluster_memory.py"
echo "  3. Check system status: cat ~/.claude/node-config.json"
