#!/bin/bash
# Deploy Autonomous Node Agents to Cluster
#
# This script deploys the autonomous agent system to all nodes:
# 1. Copies agent code to each node
# 2. Creates systemd service files
# 3. Starts autonomous agents
# 4. Verifies agent-to-agent communication

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORAGE_BASE="$STORAGE_BASE"

echo "=================================================="
echo "Deploying Autonomous Node Agents to Cluster"
echo "=================================================="
echo ""

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo "   Please export ANTHROPIC_API_KEY before running deployment"
    exit 1
fi

echo "✅ API key found"
echo ""

# Nodes to deploy to
NODES=(
    "192.168.1.16:mac-studio"
    "192.168.1.76:macbook-air-m3"
)

# Deploy to local node (macpro51) first
echo "📦 Deploying to local node (macpro51)..."
echo ""

# Ensure logs directory exists
mkdir -p "$STORAGE_BASE/logs"

# Make agent executable
chmod +x "$SCRIPT_DIR/autonomous_node_agent.py"
chmod +x "$SCRIPT_DIR/agent_chat_cli.py"

# Install systemd service
echo "  Installing systemd service..."
SERVICE_FILE="$HOME/.config/systemd/user/autonomous-node-agent.service"

# Replace API key placeholder
sed "s|%ANTHROPIC_API_KEY%|$ANTHROPIC_API_KEY|g" "$SERVICE_FILE" > /tmp/autonomous-node-agent.service.tmp
mv /tmp/autonomous-node-agent.service.tmp "$SERVICE_FILE"

# Reload systemd
systemctl --user daemon-reload

# Enable and start service
systemctl --user enable autonomous-node-agent.service
systemctl --user restart autonomous-node-agent.service

# Check status
sleep 2
if systemctl --user is-active --quiet autonomous-node-agent.service; then
    echo "  ✅ Service started successfully"
else
    echo "  ❌ Service failed to start"
    systemctl --user status autonomous-node-agent.service
    exit 1
fi

echo ""

# Deploy to remote nodes
for NODE_INFO in "${NODES[@]}"; do
    IFS=':' read -r NODE_IP NODE_ID <<< "$NODE_INFO"

    echo "📦 Deploying to $NODE_ID ($NODE_IP)..."
    echo ""

    # Check connectivity
    if ! ssh "$NODE_IP" "echo '✓ Connected'" >/dev/null 2>&1; then
        echo "  ❌ Cannot connect to $NODE_IP - skipping"
        echo ""
        continue
    fi

    # Determine storage base on remote node
    if [[ "$NODE_ID" == mac-* ]]; then
        REMOTE_STORAGE="$STORAGE_BASE"
    else
        REMOTE_STORAGE="$STORAGE_BASE"
    fi

    # Copy agent files
    echo "  Copying agent files..."
    scp "$SCRIPT_DIR/autonomous_node_agent.py" \
        "$SCRIPT_DIR/agent_chat_cli.py" \
        "$SCRIPT_DIR/node_chat_client.py" \
        "$NODE_IP:$REMOTE_STORAGE/cluster-deployment/"

    # Create systemd service
    echo "  Creating systemd service..."
    ssh "$NODE_IP" "mkdir -p ~/.config/systemd/user"

    # Generate service file for remote node
    SERVICE_CONTENT="[Unit]
Description=Autonomous Node Agent - AI-to-AI communication and collaboration
Documentation=file://$REMOTE_STORAGE/cluster-deployment/autonomous_node_agent.py
After=network.target node-chat-daemon.service
Wants=node-chat-daemon.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $REMOTE_STORAGE/cluster-deployment/autonomous_node_agent.py
Restart=always
RestartSec=10
Environment=\"ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY\"
Environment=\"PYTHONPATH=$REMOTE_STORAGE/cluster-deployment\"
WorkingDirectory=$REMOTE_STORAGE/cluster-deployment

# Logging
StandardOutput=append:$REMOTE_STORAGE/logs/autonomous-agent.log
StandardError=append:$REMOTE_STORAGE/logs/autonomous-agent-error.log

# Resource limits
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=default.target"

    echo "$SERVICE_CONTENT" | ssh "$NODE_IP" "cat > ~/.config/systemd/user/autonomous-node-agent.service"

    # Enable and start service
    echo "  Starting service..."
    ssh "$NODE_IP" "systemctl --user daemon-reload && \
                   systemctl --user enable autonomous-node-agent.service && \
                   systemctl --user restart autonomous-node-agent.service"

    # Check status
    sleep 2
    if ssh "$NODE_IP" "systemctl --user is-active --quiet autonomous-node-agent.service"; then
        echo "  ✅ Service started on $NODE_ID"
    else
        echo "  ❌ Service failed to start on $NODE_ID"
    fi

    echo ""
done

echo "=================================================="
echo "✅ Deployment Complete"
echo "=================================================="
echo ""
echo "All autonomous agents are now running!"
echo ""
echo "Test agent-to-agent communication:"
echo "  python3 $SCRIPT_DIR/agent_chat_cli.py chat --node mac-studio"
echo "  python3 $SCRIPT_DIR/agent_chat_cli.py chat --node macbook-air-m3"
echo ""
echo "Watch cluster conversations:"
echo "  python3 $SCRIPT_DIR/agent_chat_cli.py watch"
echo ""
echo "Check cluster status:"
echo "  python3 $SCRIPT_DIR/agent_chat_cli.py status"
echo ""
