#!/bin/bash
# Deploy Node Chat System to All Cluster Nodes
#
# This script deploys the real-time node chat system to all nodes in the cluster.
# Run from any node - it will detect platform and deploy appropriately.

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

echo "======================================================================"
echo "  Node Chat System Deployment"
echo "======================================================================"
echo

# Detect storage base
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    STORAGE_BASE="$STORAGE_BASE"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    STORAGE_BASE="$STORAGE_BASE"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "Storage base: $STORAGE_BASE"
echo

# Load cluster nodes
CLUSTER_CONFIG="$STORAGE_BASE/cluster-deployment/cluster-nodes.json"
if [[ ! -f "$CLUSTER_CONFIG" ]]; then
    echo "❌ Cluster configuration not found: $CLUSTER_CONFIG"
    exit 1
fi

# Get list of nodes
NODES=$(python3 -c "import json; config=json.load(open('$CLUSTER_CONFIG')); print(' '.join(config['nodes'].keys()))")

echo "Cluster nodes: $NODES"
echo

for NODE in $NODES; do
    echo "----------------------------------------------------------------------"
    echo "  Deploying to: $NODE"
    echo "----------------------------------------------------------------------"

    # Get node configuration
    NODE_IP=$(python3 -c "import json; config=json.load(open('$CLUSTER_CONFIG')); print(config['nodes']['$NODE']['ip'])")
    NODE_OS=$(python3 -c "import json; config=json.load(open('$CLUSTER_CONFIG')); print(config['nodes']['$NODE']['os'])")
    NODE_STORAGE=$(python3 -c "import json; config=json.load(open('$CLUSTER_CONFIG')); print(config['nodes']['$NODE']['storage_base'])")

    echo "  IP: $NODE_IP"
    echo "  OS: $NODE_OS"
    echo "  Storage: $NODE_STORAGE"
    echo

    # Copy files
    echo "  📦 Copying node chat files..."
    scp -q \
        "$STORAGE_BASE/cluster-deployment/node_chat_daemon.py" \
        "$STORAGE_BASE/cluster-deployment/node_chat_client.py" \
        "$STORAGE_BASE/cluster-deployment/node_persona.py" \
        "$NODE_IP:$NODE_STORAGE/cluster-deployment/"

    # Copy MCP server
    echo "  📦 Copying MCP server..."
    ssh "$NODE_IP" "mkdir -p $NODE_STORAGE/mcp-servers/node-chat-mcp"
    scp -q \
        "$STORAGE_BASE/mcp-servers/node-chat-mcp/server.py" \
        "$NODE_IP:$NODE_STORAGE/mcp-servers/node-chat-mcp/"

    # Make scripts executable
    echo "  🔧 Setting permissions..."
    ssh "$NODE_IP" "chmod +x $NODE_STORAGE/cluster-deployment/node_chat_*.py $NODE_STORAGE/cluster-deployment/node_persona.py"

    # Create inbox directory
    echo "  📂 Creating inbox directory..."
    ssh "$NODE_IP" "mkdir -p $NODE_STORAGE/cluster-inbox && chmod 750 $NODE_STORAGE/cluster-inbox"

    # Install Python dependencies
    echo "  📚 Installing Python dependencies..."
    ssh "$NODE_IP" "pip3 install --user psutil requests flask >/dev/null 2>&1"

    # Platform-specific service installation
    if [[ "$NODE_OS" == "linux" ]]; then
        echo "  🚀 Installing systemd service..."
        scp -q "$STORAGE_BASE/services/node-chat-daemon.service" "$NODE_IP:/tmp/"
        ssh "$NODE_IP" "mkdir -p ~/.config/systemd/user && \
                        mv /tmp/node-chat-daemon.service ~/.config/systemd/user/ && \
                        systemctl --user daemon-reload && \
                        systemctl --user enable node-chat-daemon.service && \
                        systemctl --user restart node-chat-daemon.service"

        # Check service status
        if ssh "$NODE_IP" "systemctl --user is-active node-chat-daemon.service" | grep -q "active"; then
            echo "  ✅ Daemon started successfully"
        else
            echo "  ⚠️  Daemon may not be running - check logs"
        fi
    else
        echo "  🚀 Starting daemon (macOS)..."
        ssh "$NODE_IP" "pkill -f node_chat_daemon.py || true"
        ssh "$NODE_IP" "nohup python3 $NODE_STORAGE/cluster-deployment/node_chat_daemon.py > $NODE_STORAGE/logs/node-chat-daemon.log 2>&1 &"
        sleep 2

        # Check if running
        if ssh "$NODE_IP" "pgrep -f node_chat_daemon.py" >/dev/null; then
            echo "  ✅ Daemon started successfully"
        else
            echo "  ⚠️  Daemon may not be running - check logs"
        fi
    fi

    # Add MCP server to ~/.claude.json
    echo "  ⚙️  Configuring MCP server..."
    ssh "$NODE_IP" "python3 - <<'PYEOF'
import json
from pathlib import Path

config_path = Path.home() / '.claude.json'
with open(config_path) as f:
    config = json.load(f)

# Add or update node-chat MCP server
config.setdefault('mcpServers', {})
config['mcpServers']['node-chat'] = {
    'command': 'python3',
    'args': ['$NODE_STORAGE/mcp-servers/node-chat-mcp/server.py'],
    'env': {},
    'disabled': False
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('✓ MCP server configured')
PYEOF
"

    echo "  ✅ Deployment complete for $NODE"
    echo
done

echo "======================================================================"
echo "  ✅ Node Chat System Deployed to All Nodes"
echo "======================================================================"
echo
echo "Next steps:"
echo "  1. Restart Claude Code on each node to load the MCP server"
echo "  2. Use the following MCP tools to chat between nodes:"
echo "     - send_message_to_node()"
echo "     - get_conversation_history()"
echo "     - get_my_awareness()"
echo "     - get_cluster_awareness()"
echo "     - check_for_new_messages()"
echo "     - broadcast_to_cluster()"
echo
echo "Chat daemon status:"
for NODE in $NODES; do
    NODE_IP=$(python3 -c "import json; config=json.load(open('$CLUSTER_CONFIG')); print(config['nodes']['$NODE']['ip'])")
    if curl -s -m 2 "http://$NODE_IP:5200/api/chat/status" >/dev/null 2>&1; then
        echo "  ✅ $NODE - daemon running"
    else
        echo "  ⚠️  $NODE - daemon not responding"
    fi
done
echo
