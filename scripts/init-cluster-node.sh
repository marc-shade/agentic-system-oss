#!/bin/bash
# Cluster Node Self-Setup Script
# Run this on any node to configure it for cluster membership
# Usage: ./init-cluster-node.sh [builder|orchestrator|researcher|inference]

set -e

# Detect storage base
detect_storage() {
    if [[ -d "/Volumes/SSDRAID0/agentic-system" ]]; then
        echo "/Volumes/SSDRAID0/agentic-system"
    elif [[ -d "/mnt/agentic-system" ]]; then
        echo "/mnt/agentic-system"
    elif [[ -d "$HOME/agentic-system" ]]; then
        echo "$HOME/agentic-system"
    else
        echo ""
    fi
}

# Detect node type from hostname
detect_node_type() {
    local hostname=$(hostname)
    case "$hostname" in
        *macpro51*|*Mac-Pro*) echo "builder" ;;
        *Mac-Studio*|*mac-studio*) echo "orchestrator" ;;
        *MacBook-Air*|*macbook-air*) echo "researcher" ;;
        *completeu*|*inference*) echo "inference" ;;
        *macmini*|*Mac-mini*) echo "small-inference" ;;
        *bpi-sentinel*) echo "sentinel" ;;
        *) echo "unknown" ;;
    esac
}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cluster Node Self-Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Get node role
NODE_ROLE="${1:-$(detect_node_type)}"
STORAGE_BASE=$(detect_storage)
HOSTNAME=$(hostname)

echo -e "\n${YELLOW}Detected Configuration:${NC}"
echo "  Hostname: $HOSTNAME"
echo "  Node Role: $NODE_ROLE"
echo "  Storage Base: $STORAGE_BASE"

if [[ -z "$STORAGE_BASE" ]]; then
    echo -e "${RED}ERROR: Could not detect agentic-system storage path${NC}"
    echo "Please create the agentic-system directory first"
    exit 1
fi

if [[ "$NODE_ROLE" == "unknown" ]]; then
    echo -e "${YELLOW}WARNING: Could not detect node type from hostname${NC}"
    echo "Please specify: builder, orchestrator, researcher, inference, small-inference, or sentinel"
    exit 1
fi

# Create required directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p "$STORAGE_BASE/config"
mkdir -p "$STORAGE_BASE/databases/cluster/nodes"
mkdir -p "$STORAGE_BASE/logs"
mkdir -p "$STORAGE_BASE/scripts"
echo -e "${GREEN}Done${NC}"

# Create cluster environment file
echo -e "\n${YELLOW}Creating cluster environment config...${NC}"
cat > "$STORAGE_BASE/config/cluster-env.sh" << 'EOF'
#!/bin/bash
# Cluster Node Configuration
# Source this file to set cluster environment variables
# Usage: source $STORAGE_BASE/config/cluster-env.sh

# Builder Node (macpro51 - Linux x86_64)
export CLUSTER_BUILDER_HOST="macpro51.local"
export CLUSTER_BUILDER_IP="192.168.1.27"

# Orchestrator Node (mac-studio - macOS ARM64)
export CLUSTER_ORCHESTRATOR_HOST="mac-studio.local"
export CLUSTER_ORCHESTRATOR_IP="192.168.1.20"

# Researcher Node (macbook-air - macOS ARM64)
export CLUSTER_RESEARCHER_HOST="macbook-air.local"
export CLUSTER_RESEARCHER_IP="192.168.1.21"

# Inference Node (completeu-server - macOS ARM64)
export CLUSTER_INFERENCE_HOST="completeu-server.local"
export CLUSTER_INFERENCE_IP="192.168.1.186"

# SSH Configuration
export CLUSTER_SSH_USER="marc"
export CLUSTER_SSH_TIMEOUT="5"
export CLUSTER_SSH_CONNECT_TIMEOUT="2"
export CLUSTER_SSH_RETRIES="2"

# Load thresholds
export CLUSTER_CPU_THRESHOLD="40"
export CLUSTER_LOAD_THRESHOLD="4"
export CLUSTER_MEMORY_THRESHOLD="80"

# Command timeout
export CLUSTER_CMD_TIMEOUT="300"
export CLUSTER_STATUS_TIMEOUT="5"

# Current node info
export CLUSTER_NODE_ROLE="$CLUSTER_NODE_ROLE"
export CLUSTER_STORAGE_BASE="$CLUSTER_STORAGE_BASE"

# Agentic system path
export AGENTIC_SYSTEM_PATH="${CLUSTER_STORAGE_BASE:-/Volumes/SSDRAID0/agentic-system}"

echo "Cluster environment loaded for node: $CLUSTER_NODE_ROLE"
EOF
echo -e "${GREEN}Created cluster-env.sh${NC}"

# Create node config JSON
echo -e "\n${YELLOW}Creating node configuration...${NC}"
NODE_CONFIG_FILE="$STORAGE_BASE/config/node-config.json"
cat > "$NODE_CONFIG_FILE" << EOF
{
    "node_id": "$NODE_ROLE",
    "hostname": "$HOSTNAME",
    "storage_base": "$STORAGE_BASE",
    "role": "$NODE_ROLE",
    "os": "$(uname -s | tr '[:upper:]' '[:lower:]')",
    "arch": "$(uname -m)",
    "configured_at": "$(date -Iseconds)",
    "cluster_nodes": {
        "builder": "macpro51.local",
        "orchestrator": "mac-studio.local",
        "researcher": "macbook-air.local",
        "inference": "completeu-server.local"
    }
}
EOF
echo -e "${GREEN}Created node-config.json${NC}"

# Test connectivity to other nodes
echo -e "\n${YELLOW}Testing cluster connectivity...${NC}"

test_node() {
    local name=$1
    local host=$2
    if ping -c 1 -W 2 "$host" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name ($host) - reachable"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name ($host) - unreachable"
        return 1
    fi
}

test_node "Builder" "macpro51.local"
test_node "Orchestrator" "mac-studio.local"
test_node "Researcher" "macbook-air.local"
test_node "Inference" "completeu-server.local"

# Add cluster-env.sh to shell profile
echo -e "\n${YELLOW}Adding cluster environment to shell profile...${NC}"
PROFILE_FILE=""
if [[ -f "$HOME/.zshrc" ]]; then
    PROFILE_FILE="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    PROFILE_FILE="$HOME/.bashrc"
fi

if [[ -n "$PROFILE_FILE" ]]; then
    # Check if already added
    if ! grep -q "cluster-env.sh" "$PROFILE_FILE" 2>/dev/null; then
        echo "" >> "$PROFILE_FILE"
        echo "# Cluster environment" >> "$PROFILE_FILE"
        echo "export CLUSTER_NODE_ROLE=\"$NODE_ROLE\"" >> "$PROFILE_FILE"
        echo "export CLUSTER_STORAGE_BASE=\"$STORAGE_BASE\"" >> "$PROFILE_FILE"
        echo "[ -f \"$STORAGE_BASE/config/cluster-env.sh\" ] && source \"$STORAGE_BASE/config/cluster-env.sh\"" >> "$PROFILE_FILE"
        echo -e "${GREEN}Added to $PROFILE_FILE${NC}"
    else
        echo -e "${YELLOW}Already configured in $PROFILE_FILE${NC}"
    fi
fi

# Create rsync sync script for non-builder nodes
if [[ "$NODE_ROLE" != "builder" ]]; then
    echo -e "\n${YELLOW}Creating sync script from builder...${NC}"
    cat > "$STORAGE_BASE/scripts/sync-from-builder.sh" << 'SYNCEOF'
#!/bin/bash
# Sync configuration and scripts from builder node
# Usage: ./sync-from-builder.sh

BUILDER_HOST="macpro51.local"
BUILDER_PATH="/mnt/agentic-system"
LOCAL_PATH="${CLUSTER_STORAGE_BASE:-$(dirname $(dirname $0))}"

echo "Syncing from $BUILDER_HOST to $LOCAL_PATH..."

# Sync config directory
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/config/" \
    "$LOCAL_PATH/config/"

# Sync scripts directory
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/scripts/" \
    "$LOCAL_PATH/scripts/"

# Sync cluster deployment
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/cluster-deployment/" \
    "$LOCAL_PATH/cluster-deployment/"

echo "Sync complete!"
SYNCEOF
    chmod +x "$STORAGE_BASE/scripts/sync-from-builder.sh"
    echo -e "${GREEN}Created sync-from-builder.sh${NC}"
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Node setup complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Node Role: $NODE_ROLE"
echo "Storage: $STORAGE_BASE"
echo "Config: $NODE_CONFIG_FILE"
echo ""
echo "Next steps:"
echo "1. Source your shell profile: source $PROFILE_FILE"
echo "2. Verify cluster connectivity: ping macpro51.local"
if [[ "$NODE_ROLE" != "builder" ]]; then
    echo "3. Sync from builder: $STORAGE_BASE/scripts/sync-from-builder.sh"
fi
echo ""
