#!/bin/bash
# Deploy autonomous agent to a single macOS node


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
REMOTE_STORAGE="$STORAGE_BASE"

echo "Deploying to $NODE_IP..."

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

# Start agent (requires ANTHROPIC_API_KEY to be set on remote)
echo "  Starting agent..."
ssh "$NODE_IP" "export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY' && \
                cd $REMOTE_STORAGE/cluster-deployment && \
                ./start_autonomous_agent_macos.sh"

echo "✅ Deployment complete for $NODE_IP"
