#!/bin/bash
# Deploy Autonomous Chat Daemon to Linux Node
# Usage: ./deploy_chat_daemon_linux.sh [node_hostname]

set -e

# Configuration

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

NODE_HOST="${1:-192.168.1.183}"  # macpro51 IP address
REMOTE_USER="marc"
REMOTE_BASE="$STORAGE_BASE"
LOCAL_BASE="$STORAGE_BASE"

echo "📦 Deploying Autonomous Chat Daemon to $NODE_HOST"
echo "================================================"

# 1. Check if node is reachable
echo ""
echo "1. Checking node connectivity..."
if ! ping -c 1 "$NODE_HOST" &> /dev/null; then
    echo "❌ Cannot reach $NODE_HOST"
    exit 1
fi
echo "✓ Node is reachable"

# 2. Ensure remote directories exist
echo ""
echo "2. Creating remote directories..."
ssh "${REMOTE_USER}@${NODE_HOST}" "mkdir -p ${REMOTE_BASE}/cluster-deployment ${REMOTE_BASE}/logs"
echo "✓ Directories created"

# 3. Copy Python files
echo ""
echo "3. Copying Python modules..."
scp "${LOCAL_BASE}/cluster-deployment/node_self_catalog.py" \
    "${REMOTE_USER}@${NODE_HOST}:${REMOTE_BASE}/cluster-deployment/"
scp "${LOCAL_BASE}/cluster-deployment/multi_turn_chat.py" \
    "${REMOTE_USER}@${NODE_HOST}:${REMOTE_BASE}/cluster-deployment/"
scp "${LOCAL_BASE}/cluster-deployment/autonomous_chat_daemon.py" \
    "${REMOTE_USER}@${NODE_HOST}:${REMOTE_BASE}/cluster-deployment/"
echo "✓ Python files copied"

# 4. Copy startup scripts
echo ""
echo "4. Copying startup scripts..."
scp "${LOCAL_BASE}/cluster-deployment/start_autonomous_chat_daemon.sh" \
    "${REMOTE_USER}@${NODE_HOST}:${REMOTE_BASE}/cluster-deployment/"
scp "${LOCAL_BASE}/cluster-deployment/stop_autonomous_chat_daemon.sh" \
    "${REMOTE_USER}@${NODE_HOST}:${REMOTE_BASE}/cluster-deployment/"
ssh "${REMOTE_USER}@${NODE_HOST}" "chmod +x ${REMOTE_BASE}/cluster-deployment/start_autonomous_chat_daemon.sh ${REMOTE_BASE}/cluster-deployment/stop_autonomous_chat_daemon.sh"
echo "✓ Scripts copied and made executable"

# 5. Install systemd service
echo ""
echo "5. Installing systemd service..."
scp "${LOCAL_BASE}/cluster-deployment/autonomous-chat-daemon.service" \
    "${REMOTE_USER}@${NODE_HOST}:/tmp/"
ssh "${REMOTE_USER}@${NODE_HOST}" "
    mkdir -p ~/.config/systemd/user
    mv /tmp/autonomous-chat-daemon.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable autonomous-chat-daemon.service
"
echo "✓ Service installed and enabled"

# 6. Test daemon can start
echo ""
echo "6. Testing daemon startup..."
ssh "${REMOTE_USER}@${NODE_HOST}" "
    cd ${REMOTE_BASE}/cluster-deployment
    python3 -c 'import node_self_catalog; import multi_turn_chat; import autonomous_chat_daemon; print(\"✓ All imports successful\")'
"

# 7. Start the service
echo ""
echo "7. Starting autonomous chat daemon..."
ssh "${REMOTE_USER}@${NODE_HOST}" "
    systemctl --user start autonomous-chat-daemon.service
    sleep 2
    systemctl --user status autonomous-chat-daemon.service --no-pager
"

echo ""
echo "================================================"
echo "✅ Deployment complete!"
echo ""
echo "Service status:"
echo "  systemctl --user status autonomous-chat-daemon.service"
echo ""
echo "View logs:"
echo "  tail -f ${REMOTE_BASE}/logs/autonomous-chat-daemon.log"
echo "  journalctl --user -u autonomous-chat-daemon.service -f"
echo ""
echo "Control service:"
echo "  systemctl --user stop autonomous-chat-daemon.service"
echo "  systemctl --user restart autonomous-chat-daemon.service"
