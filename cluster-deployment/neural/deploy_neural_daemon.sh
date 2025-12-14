#!/bin/bash
# Deploy Neural Daemon to Cluster Nodes
# Usage: ./deploy_neural_daemon.sh [node-id]

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

# Auto-detect AGENTIC_ROOT based on platform
if [ "$(uname)" = "Darwin" ]; then
    # macOS - check common locations
    if [ -d "$STORAGE_BASE" ]; then
        AGENTIC_ROOT="$STORAGE_BASE"
    elif [ -d "$STORAGE_BASE" ]; then
        AGENTIC_ROOT="$STORAGE_BASE"
    elif [ -d "$HOME/agentic-system" ]; then
        AGENTIC_ROOT="$HOME/agentic-system"
    else
        AGENTIC_ROOT="$HOME/agentic-system"
    fi
else
    # Linux
    if [ -d "$STORAGE_BASE" ]; then
        AGENTIC_ROOT="$STORAGE_BASE"
    else
        AGENTIC_ROOT="$HOME/agentic-system"
    fi
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Neural Daemon Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Detect or use provided node
if [ -n "$1" ]; then
    NODE_ID="$1"
else
    HOSTNAME=$(hostname -s | tr '[:upper:]' '[:lower:]')
    case "$HOSTNAME" in
        *macpro*|*mac-pro*)    NODE_ID="macpro51" ;;
        *mac-studio*|*macstudio*) NODE_ID="mac-studio" ;;
        *macbook-air*|*macbookair*) NODE_ID="macbook-air" ;;
        *completeu*)           NODE_ID="completeu-server" ;;
        *)                     NODE_ID="unknown" ;;
    esac
fi

echo -e "\n${GREEN}Node ID:${NC} $NODE_ID"
echo -e "${GREEN}Storage:${NC} $AGENTIC_ROOT"

# Verify we're on a known node
if [ "$NODE_ID" = "unknown" ]; then
    echo -e "${YELLOW}Warning: Unknown node. Please provide node-id as argument.${NC}"
    echo "Usage: $0 [mac-studio|macpro51|macbook-air|completeu-server]"
    exit 1
fi

# Check if neural package exists
if [ ! -f "$SCRIPT_DIR/neuron_cluster.py" ]; then
    echo -e "${YELLOW}Error: Neural package not found at $SCRIPT_DIR${NC}"
    exit 1
fi

echo -e "\n${GREEN}Step 1:${NC} Creating log directory..."
mkdir -p "$AGENTIC_ROOT/logs"

echo -e "${GREEN}Step 2:${NC} Creating database directory..."
mkdir -p "$AGENTIC_ROOT/databases/cluster"

echo -e "${GREEN}Step 3:${NC} Installing systemd service..."

# Detect platform
if [ "$(uname)" = "Darwin" ]; then
    # macOS - use launchd
    PLIST_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$PLIST_DIR"

    cat > "$PLIST_DIR/com.agentic.neural-daemon.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic.neural-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$SCRIPT_DIR/neural_daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$AGENTIC_ROOT/logs/neural-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$AGENTIC_ROOT/logs/neural-daemon.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>AGENTIC_ROOT</key>
        <string>$AGENTIC_ROOT</string>
    </dict>
</dict>
</plist>
EOF

    echo -e "${GREEN}Step 4:${NC} Loading launchd service..."
    launchctl unload "$PLIST_DIR/com.agentic.neural-daemon.plist" 2>/dev/null || true
    launchctl load "$PLIST_DIR/com.agentic.neural-daemon.plist"

    echo -e "\n${GREEN}Deployment complete!${NC}"
    echo "Commands:"
    echo "  Start:  launchctl load ~/Library/LaunchAgents/com.agentic.neural-daemon.plist"
    echo "  Stop:   launchctl unload ~/Library/LaunchAgents/com.agentic.neural-daemon.plist"
    echo "  Logs:   tail -f $AGENTIC_ROOT/logs/neural-daemon.log"

else
    # Linux - use systemd
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"

    cp "$AGENTIC_ROOT/services/systemd/neural-daemon.service" "$SYSTEMD_DIR/"

    echo -e "${GREEN}Step 4:${NC} Enabling systemd service..."
    systemctl --user daemon-reload
    systemctl --user enable neural-daemon.service
    systemctl --user start neural-daemon.service

    echo -e "\n${GREEN}Deployment complete!${NC}"
    echo "Commands:"
    echo "  Status: systemctl --user status neural-daemon.service"
    echo "  Stop:   systemctl --user stop neural-daemon.service"
    echo "  Start:  systemctl --user start neural-daemon.service"
    echo "  Logs:   journalctl --user -u neural-daemon.service -f"
fi

echo -e "\n${BLUE}Neural Daemon ($NODE_ID) is now running 24x7!${NC}"
echo "Sending status reports to mac-studio (orchestrator) every 60s"
