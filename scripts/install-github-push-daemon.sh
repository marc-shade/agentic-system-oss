#!/bin/bash
# Install the GitHub Push Daemon as a launchd service
# This daemon runs every 5 minutes and safely pushes changes with security checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SRC="$BASE_DIR/services/com.agentic.github-push-daemon.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agentic.github-push-daemon.plist"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Installing GitHub Push Daemon...${NC}"

# Check if daemon is already running
if launchctl list 2>/dev/null | grep -q "com.agentic.github-push-daemon"; then
    echo -e "${YELLOW}Stopping existing daemon...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Create LaunchAgents directory if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Create log directory
mkdir -p "$BASE_DIR/logs"

# Copy plist
cp "$PLIST_SRC" "$PLIST_DEST"
echo -e "${GREEN}Installed plist to: $PLIST_DEST${NC}"

# Load the daemon
launchctl load "$PLIST_DEST"

# Check status
if launchctl list 2>/dev/null | grep -q "com.agentic.github-push-daemon"; then
    echo -e "${GREEN}Daemon is running!${NC}"
    echo ""
    echo "Configuration:"
    echo "  - Check interval: 5 minutes"
    echo "  - Working directory: $BASE_DIR"
    echo "  - Log file: $BASE_DIR/logs/github-push-daemon.log"
    echo ""
    echo "Commands:"
    echo "  View logs:    tail -f $BASE_DIR/logs/github-push-daemon.log"
    echo "  Stop daemon:  launchctl unload $PLIST_DEST"
    echo "  Start daemon: launchctl load $PLIST_DEST"
    echo "  Check status: launchctl list | grep github-push"
else
    echo -e "${RED}Failed to start daemon. Check logs for errors.${NC}"
    exit 1
fi
