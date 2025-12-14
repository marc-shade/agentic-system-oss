#!/bin/bash
# Deploy Convex Heartbeat to all cluster nodes
# Usage: ./deploy-to-nodes.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONVEX_URL="http://macpro51.local:3210"
CONVEX_ADMIN_KEY="convex-self-hosted|0151d95174e8f04d4cb67383c9b48ac2d91c0e31d5c23ba3cd5fceeb9370911f26bcfe5355"

echo "=== Convex Heartbeat Deployment ==="
echo ""

# Function to deploy to macOS node
deploy_macos() {
    local node_name=$1
    local node_id=$2
    local host=$3

    echo "Deploying to $node_name ($host)..."

    # Create remote directory
    ssh "$host" "mkdir -p /Volumes/SSDRAID0/agentic-system/services/convex-heartbeat"

    # Copy files
    scp "$SCRIPT_DIR/heartbeat_client.py" "$host:/Volumes/SSDRAID0/agentic-system/services/convex-heartbeat/"

    # Create customized plist
    local plist_content=$(cat "$SCRIPT_DIR/com.agentic.convex-heartbeat.plist" | sed "s/NODE_ID_PLACEHOLDER/$node_id/g")
    echo "$plist_content" | ssh "$host" "cat > ~/Library/LaunchAgents/com.agentic.convex-heartbeat.plist"

    # Load the service
    ssh "$host" "launchctl unload ~/Library/LaunchAgents/com.agentic.convex-heartbeat.plist 2>/dev/null || true"
    ssh "$host" "launchctl load ~/Library/LaunchAgents/com.agentic.convex-heartbeat.plist"

    echo "  ✓ $node_name deployed and started"
}

# Function to deploy locally (Linux/macpro51)
deploy_local_linux() {
    echo "Deploying to macpro51 (local)..."

    # Install systemd service
    mkdir -p ~/.config/systemd/user/
    cp "$SCRIPT_DIR/convex-heartbeat.service" ~/.config/systemd/user/

    # Reload and start
    systemctl --user daemon-reload
    systemctl --user enable convex-heartbeat.service
    systemctl --user restart convex-heartbeat.service

    echo "  ✓ macpro51 (builder) deployed and started"
}

# Deploy to each node
echo "1. Deploying to macpro51 (builder) - local"
deploy_local_linux

echo ""
echo "2. Deploying to mac-studio (orchestrator)"
deploy_macos "mac-studio" "orchestrator" "marc@mac-studio.local" || echo "  ⚠ mac-studio deployment failed (node may be offline)"

echo ""
echo "3. Deploying to macbook-air (researcher)"
deploy_macos "macbook-air" "researcher" "marc@macbook-air.local" || echo "  ⚠ macbook-air deployment failed (node may be offline)"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Check status:"
echo "  Local:       systemctl --user status convex-heartbeat"
echo "  mac-studio:  ssh marc@mac-studio.local 'launchctl list | grep convex'"
echo "  macbook-air: ssh marc@macbook-air.local 'launchctl list | grep convex'"
echo ""
echo "Monitor cluster:"
echo "  python3 $SCRIPT_DIR/heartbeat_client.py --subscribe"
echo ""
echo "Dashboard:"
echo "  http://macpro51.local:6791"
