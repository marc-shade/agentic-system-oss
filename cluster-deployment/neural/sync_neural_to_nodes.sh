#!/bin/bash
# Sync Neural Package to All Cluster Nodes
# Run from macpro51 (primary builder node)

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
NEURAL_DIR="$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Neural Package Cluster Sync${NC}"
echo -e "${BLUE}========================================${NC}"

# Cluster node definitions
declare -A NODES
NODES["mac-studio"]="marc@192.168.1.16:$STORAGE_BASE/cluster-deployment/neural/"
NODES["macbook-air"]="marc@192.168.1.76:/Users/marc/agentic-system/cluster-deployment/neural/"
NODES["completeu-server"]="marc@192.168.1.186:$STORAGE_BASE/cluster-deployment/neural/"

# Files to sync
FILES_TO_SYNC=(
    "neuron_cluster.py"
    "synapse_protocol.py"
    "neural_daemon.py"
    "wave_orchestrator.py"
    "deploy_neural_daemon.sh"
    "__init__.py"
)

# Function to sync to a node
sync_to_node() {
    local node_name="$1"
    local dest="${NODES[$node_name]}"

    echo -e "\n${BLUE}Syncing to $node_name...${NC}"

    # Test connectivity first
    local ip=$(echo "$dest" | sed 's/.*@\([0-9.]*\):.*/\1/')
    if ! ping -c 1 -W 2 "$ip" &>/dev/null; then
        echo -e "${YELLOW}  ⚠ $node_name offline, skipping${NC}"
        return 1
    fi

    # Create destination directory if needed
    local user_host=$(echo "$dest" | cut -d: -f1)
    local remote_dir=$(echo "$dest" | cut -d: -f2)
    ssh "$user_host" "mkdir -p $remote_dir" 2>/dev/null || {
        echo -e "${YELLOW}  ⚠ Cannot create remote directory, trying rsync anyway${NC}"
    }

    # Sync files
    for file in "${FILES_TO_SYNC[@]}"; do
        if [ -f "$NEURAL_DIR/$file" ]; then
            rsync -avz "$NEURAL_DIR/$file" "$dest" 2>/dev/null && \
                echo -e "  ${GREEN}✓${NC} $file" || \
                echo -e "  ${RED}✗${NC} $file failed"
        fi
    done

    # Also sync the systemd service template
    if [ -f "$STORAGE_BASE/services/systemd/neural-daemon.service" ]; then
        rsync -avz "$STORAGE_BASE/services/systemd/neural-daemon.service" "$dest../../../services/systemd/" 2>/dev/null && \
            echo -e "  ${GREEN}✓${NC} systemd service" || true
    fi

    echo -e "${GREEN}  Done!${NC}"
}

# Parse arguments
if [ -n "$1" ]; then
    # Sync to specific node
    if [ -n "${NODES[$1]}" ]; then
        sync_to_node "$1"
    else
        echo -e "${RED}Unknown node: $1${NC}"
        echo "Available nodes: ${!NODES[*]}"
        exit 1
    fi
else
    # Sync to all nodes
    for node in "${!NODES[@]}"; do
        sync_to_node "$node"
    done
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Sync complete!${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}Next steps for each node:${NC}"
echo "  1. SSH to the node"
echo "  2. cd to cluster-deployment/neural/"
echo "  3. Run: ./deploy_neural_daemon.sh"
