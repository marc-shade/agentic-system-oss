#!/bin/bash
# Deploy component to a specific cluster node

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <node> <component>"
    echo ""
    echo "Nodes: mac-studio, macpro51, macbook-air-m3"
    echo ""
    echo "Components:"
    echo "  enhanced-memory-mcp    Vector memory server"
    echo "  agent-runtime-mcp      Goals and tasks"
    echo "  agi-mcp               Meta-learning"
    echo "  research-paper-mcp     Paper integration"
    echo "  security-scanner-mcp   Security tools"
    echo "  configs                Configuration files"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

NODE=$1
COMPONENT=$2

# Node configurations
case $NODE in
    mac-studio)
        SSH_TARGET="marc@mac-studio.local"
        REMOTE_PATH="/Volumes/SSDRAID0"
        ;;
    macpro51)
        SSH_TARGET="marc@macpro51.local"
        REMOTE_PATH="/mnt/agentic-system"
        ;;
    macbook-air-m3)
        SSH_TARGET="marc@macbook-air-m3.local"
        REMOTE_PATH="~/agentic-system"
        ;;
    *)
        echo -e "${RED}Unknown node: $NODE${NC}"
        usage
        ;;
esac

LOCAL_MCP="/mnt/agentic-system/mcp-servers"
LOCAL_CONFIG="$HOME/.claude/agi"

echo -e "${GREEN}Deploying $COMPONENT to $NODE${NC}"
echo "  Target: $SSH_TARGET:$REMOTE_PATH"

# Test connectivity
echo -e "\n${YELLOW}Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=10 "$SSH_TARGET" "echo Connected" 2>/dev/null; then
    echo -e "${RED}Cannot connect to $NODE${NC}"
    exit 1
fi

# Deploy based on component
case $COMPONENT in
    *-mcp)
        SRC="$LOCAL_MCP/$COMPONENT"
        if [ ! -d "$SRC" ]; then
            echo -e "${RED}Component not found: $SRC${NC}"
            exit 1
        fi

        echo -e "${YELLOW}Syncing $COMPONENT...${NC}"
        rsync -avz --exclude '__pycache__' --exclude '.venv' --exclude 'node_modules' \
            "$SRC/" "$SSH_TARGET:$REMOTE_PATH/mcp-servers/$COMPONENT/"

        echo -e "${YELLOW}Installing dependencies...${NC}"
        ssh "$SSH_TARGET" "cd $REMOTE_PATH/mcp-servers/$COMPONENT && pip3 install -r requirements.txt 2>/dev/null || true"
        ;;

    configs)
        echo -e "${YELLOW}Syncing configurations...${NC}"
        rsync -avz "$LOCAL_CONFIG/" "$SSH_TARGET:~/.claude/agi/"
        ;;

    *)
        echo -e "${RED}Unknown component: $COMPONENT${NC}"
        usage
        ;;
esac

echo -e "\n${GREEN}Deployment complete!${NC}"
echo "Restart Claude Code on $NODE to apply changes."
