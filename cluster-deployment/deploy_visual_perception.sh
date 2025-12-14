#!/bin/bash
#
# Deploy Cluster Visual Perception to All Nodes
# This script deploys the visual perception daemon to macOS and Linux nodes
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PERCEPTION_DIR="$SCRIPT_DIR/../intelligent-agents/perception"

# Node definitions
declare -A NODES=(
    ["mac-studio"]="Marcs-Mac-Studio.local"
    ["macbook-air"]="Marcs-MacBook-Air.local"
    ["completeu-server"]="completeu-server.local"
)

declare -A NODE_STORAGE=(
    ["mac-studio"]="$STORAGE_BASE"
    ["macbook-air"]="/Users/marc/agentic-system"
    ["completeu-server"]="$STORAGE_BASE"
)

SSH_USER="marc"
SSH_KEY="$HOME/.ssh/id_ed25519"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_node() {
    local node=$1
    local hostname=${NODES[$node]}

    if ping -c 1 -W 2 "$hostname" &>/dev/null; then
        echo "online"
    else
        echo "offline"
    fi
}

deploy_to_node() {
    local node=$1
    local hostname=${NODES[$node]}
    local storage=${NODE_STORAGE[$node]}

    log_info "Deploying to $node ($hostname)..."

    # Check if node is reachable
    if [[ $(check_node "$node") == "offline" ]]; then
        log_warn "$node is offline, skipping"
        return 1
    fi

    # Create directories on remote
    log_info "Creating directories on $node..."
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "
        mkdir -p $storage/intelligent-agents/perception
        mkdir -p $storage/databases/sensory/screenshots
        mkdir -p $storage/logs
        mkdir -p ~/Library/LaunchAgents 2>/dev/null || mkdir -p ~/.config/systemd/user
    "

    # Copy perception scripts
    log_info "Copying perception scripts to $node..."
    scp -i "$SSH_KEY" \
        "$PERCEPTION_DIR/cluster_visual_daemon.py" \
        "$PERCEPTION_DIR/visual_memory_bridge.py" \
        "$SSH_USER@$hostname:$storage/intelligent-agents/perception/"

    # Make executable
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "
        chmod +x $storage/intelligent-agents/perception/*.py
    "

    # Deploy service (detect platform)
    log_info "Deploying service to $node..."
    if ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "uname" | grep -q "Darwin"; then
        # macOS - use launchd
        deploy_launchd "$node" "$hostname" "$storage"
    else
        # Linux - use systemd
        deploy_systemd "$node" "$hostname" "$storage"
    fi

    log_info "✓ Deployed to $node"
}

deploy_launchd() {
    local node=$1
    local hostname=$2
    local storage=$3

    # Create launchd plist with SAFETY GUARDS
    # - KeepAlive with SuccessfulExit only (won't restart on crash loop)
    # - ProcessType Background (lower CPU priority)
    # - Nice value for reduced priority
    # - ThrottleInterval of 60 seconds (prevent rapid restarts)
    # - StartCalendarInterval for periodic checks instead of continuous
    local plist_content="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>Label</key>
    <string>com.agentic.cluster-visual-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$storage/intelligent-agents/perception/cluster_visual_daemon.py</string>
        <string>--interval</string>
        <string>30</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$storage</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>STORAGE_BASE</key>
        <string>$storage</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Background</string>
    <key>Nice</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>$storage/logs/cluster_visual_daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$storage/logs/cluster_visual_daemon.error.log</string>
    <key>ThrottleInterval</key>
    <integer>60</integer>
    <key>StartInterval</key>
    <integer>300</integer>
</dict>
</plist>"

    # Write plist to remote
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "cat > ~/Library/LaunchAgents/com.agentic.cluster-visual-daemon.plist" <<< "$plist_content"

    # Load the service
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "
        launchctl unload ~/Library/LaunchAgents/com.agentic.cluster-visual-daemon.plist 2>/dev/null || true
        launchctl load ~/Library/LaunchAgents/com.agentic.cluster-visual-daemon.plist
        echo 'launchd service loaded'
    "
}

deploy_systemd() {
    local node=$1
    local hostname=$2
    local storage=$3

    # Create systemd service
    local service_content="[Unit]
Description=Cluster Visual Daemon - AGI Environmental Awareness
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $storage/intelligent-agents/perception/cluster_visual_daemon.py --interval 10
WorkingDirectory=$storage
Environment=STORAGE_BASE=$storage
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target"

    # Write service to remote
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "cat > ~/.config/systemd/user/cluster-visual-daemon.service" <<< "$service_content"

    # Enable and start
    ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "
        systemctl --user daemon-reload
        systemctl --user enable cluster-visual-daemon.service
        systemctl --user start cluster-visual-daemon.service
        echo 'systemd service started'
    "
}

check_status() {
    log_info "Checking visual daemon status across cluster..."
    echo ""

    for node in "${!NODES[@]}"; do
        local hostname=${NODES[$node]}

        if [[ $(check_node "$node") == "offline" ]]; then
            echo -e "$node: ${RED}OFFLINE${NC}"
            continue
        fi

        # Check if service is running
        local status=$(ssh -i "$SSH_KEY" "$SSH_USER@$hostname" "
            if [[ -f ~/Library/LaunchAgents/com.agentic.cluster-visual-daemon.plist ]]; then
                launchctl list | grep cluster-visual-daemon && echo 'RUNNING' || echo 'STOPPED'
            elif [[ -f ~/.config/systemd/user/cluster-visual-daemon.service ]]; then
                systemctl --user is-active cluster-visual-daemon.service 2>/dev/null || echo 'STOPPED'
            else
                echo 'NOT INSTALLED'
            fi
        " 2>/dev/null || echo "ERROR")

        if [[ "$status" == *"RUNNING"* ]] || [[ "$status" == "active" ]]; then
            echo -e "$node ($hostname): ${GREEN}RUNNING${NC}"
        elif [[ "$status" == *"STOPPED"* ]] || [[ "$status" == "inactive" ]]; then
            echo -e "$node ($hostname): ${YELLOW}STOPPED${NC}"
        else
            echo -e "$node ($hostname): ${RED}$status${NC}"
        fi
    done
    echo ""
}

# Main
case "${1:-deploy}" in
    deploy)
        log_info "Deploying visual perception to cluster..."
        for node in "${!NODES[@]}"; do
            deploy_to_node "$node" || true
        done
        echo ""
        check_status
        ;;
    status)
        check_status
        ;;
    node)
        if [[ -z "$2" ]]; then
            log_error "Usage: $0 node <node-name>"
            exit 1
        fi
        deploy_to_node "$2"
        ;;
    *)
        echo "Usage: $0 {deploy|status|node <name>}"
        echo "  deploy  - Deploy to all nodes"
        echo "  status  - Check status on all nodes"
        echo "  node    - Deploy to specific node"
        exit 1
        ;;
esac
