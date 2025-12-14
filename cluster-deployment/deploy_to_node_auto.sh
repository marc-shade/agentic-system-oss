#!/bin/bash
# Deploy autonomous agent to any node (auto-detect storage)


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

if [ -z "$1" ]; then
    echo "Usage: $0 <node-ip>"
    exit 1
fi

NODE_IP="$1"

echo "Deploying to $NODE_IP..."

# Detect remote storage base
echo "  Detecting storage base..."
if ssh "$NODE_IP" "test -d /Volumes/SSDRAID0/agentic-system" 2>/dev/null; then
    REMOTE_STORAGE="$STORAGE_BASE"
    echo "  Found: $REMOTE_STORAGE"
elif ssh "$NODE_IP" "test -d /Users/marc/agentic-system" 2>/dev/null; then
    REMOTE_STORAGE="/Users/marc/agentic-system"
    echo "  Found: $REMOTE_STORAGE"
elif ssh "$NODE_IP" "test -d /mnt/agentic-system" 2>/dev/null; then
    REMOTE_STORAGE="$STORAGE_BASE"
    echo "  Found: $REMOTE_STORAGE"
else
    echo "  ❌ Error: Could not find agentic-system on $NODE_IP"
    exit 1
fi

# Create directory if needed
echo "  Ensuring cluster-deployment directory exists..."
ssh "$NODE_IP" "mkdir -p $REMOTE_STORAGE/cluster-deployment"

# Copy agent files
echo "  Copying files..."
scp autonomous_node_agent.py \
    agent_chat_cli.py \
    node_chat_client.py \
    start_autonomous_agent_macos.sh \
    stop_autonomous_agent_macos.sh \
    "$NODE_IP:$REMOTE_STORAGE/cluster-deployment/"

# Make scripts executable
echo "  Making scripts executable..."
ssh "$NODE_IP" "chmod +x $REMOTE_STORAGE/cluster-deployment/start_autonomous_agent_macos.sh \
                                $REMOTE_STORAGE/cluster-deployment/stop_autonomous_agent_macos.sh \
                                $REMOTE_STORAGE/cluster-deployment/autonomous_node_agent.py \
                                $REMOTE_STORAGE/cluster-deployment/agent_chat_cli.py"

# Start agent
echo "  Starting agent..."
ssh "$NODE_IP" "export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY' && \
                cd $REMOTE_STORAGE/cluster-deployment && \
                ./start_autonomous_agent_macos.sh"

echo "✅ Deployment complete for $NODE_IP"
