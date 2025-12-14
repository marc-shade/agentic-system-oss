#!/bin/bash
# Uninstall the GitHub Push Daemon launchd service

PLIST_DEST="$HOME/Library/LaunchAgents/com.agentic.github-push-daemon.plist"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Uninstalling GitHub Push Daemon...${NC}"

# Unload if running
if launchctl list 2>/dev/null | grep -q "com.agentic.github-push-daemon"; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "Daemon stopped"
fi

# Remove plist
if [ -f "$PLIST_DEST" ]; then
    rm "$PLIST_DEST"
    echo "Plist removed"
fi

echo -e "${GREEN}GitHub Push Daemon uninstalled${NC}"
