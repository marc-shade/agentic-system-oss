#!/bin/bash
# Synchronize all cluster nodes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
SYNC_ALL=false
SYNC_CONFIGS=false
SYNC_MCP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            SYNC_ALL=true
            shift
            ;;
        --configs-only)
            SYNC_CONFIGS=true
            shift
            ;;
        --mcp-only)
            SYNC_MCP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--all|--configs-only|--mcp-only]"
            exit 1
            ;;
    esac
done

# Default to all if no options
if ! $SYNC_ALL && ! $SYNC_CONFIGS && ! $SYNC_MCP; then
    SYNC_ALL=true
fi

NODES=("mac-studio" "macpro51" "macbook-air-m3")
THIS_NODE=$(hostname -s 2>/dev/null || hostname)

echo -e "${GREEN}AGI Cluster Sync${NC}"
echo "================"

for node in "${NODES[@]}"; do
    # Skip self
    if [[ "$THIS_NODE" == *"$node"* ]] || [[ "$node" == *"$THIS_NODE"* ]]; then
        echo -e "\n${YELLOW}Skipping $node (self)${NC}"
        continue
    fi

    echo -e "\n${YELLOW}Syncing $node...${NC}"

    # Test connectivity first
    SSH_TARGET="marc@${node}.local"
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_TARGET" "echo" 2>/dev/null; then
        echo -e "  ${RED}Cannot connect - skipping${NC}"
        continue
    fi

    if $SYNC_ALL || $SYNC_CONFIGS; then
        echo -e "  ${YELLOW}Syncing configurations...${NC}"
        "$SCRIPT_DIR/deploy-to-node.sh" "$node" configs 2>/dev/null || true
    fi

    if $SYNC_ALL || $SYNC_MCP; then
        # Sync commonly needed MCP servers
        for mcp in agent-runtime-mcp agi-mcp; do
            echo -e "  ${YELLOW}Syncing $mcp...${NC}"
            "$SCRIPT_DIR/deploy-to-node.sh" "$node" "$mcp" 2>/dev/null || true
        done
    fi

    echo -e "  ${GREEN}Done${NC}"
done

echo -e "\n${GREEN}Cluster sync complete!${NC}"
