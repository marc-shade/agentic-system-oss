#!/bin/bash
# Wazuh Agent Deployment Script for Agentic Cluster
# Deploys Wazuh agents to macOS ARM64 nodes

WAZUH_MANAGER="192.168.1.183"  # macpro51.local
WAZUH_VERSION="4.14.1"
AGENT_PKG="wazuh-agent-${WAZUH_VERSION}-1.arm64.pkg"
AGENT_URL="https://packages.wazuh.com/4.x/macos/${AGENT_PKG}"

# Cluster nodes - macOS ARM64
declare -A NODES=(
    ["mac-studio"]="192.168.1.16"
    ["mac-mini"]="192.168.1.36"
    ["macbook-air"]="192.168.1.172"
    ["gpu-inference"]="192.168.1.186"
)

deploy_to_node() {
    local node_name=$1
    local node_ip=$2

    echo "=========================================="
    echo "Deploying Wazuh agent to ${node_name} (${node_ip})"
    echo "=========================================="

    # Check if node is reachable
    if ! ping -c 1 -W 2 "${node_ip}" >/dev/null 2>&1; then
        echo "ERROR: ${node_name} is not reachable"
        return 1
    fi

    # Deploy via SSH
    ssh -o ConnectTimeout=10 "marc@${node_ip}" bash -s << EOF
        set -e
        echo "=== Downloading Wazuh agent ==="
        cd /tmp
        curl -sO ${AGENT_URL}

        echo "=== Installing Wazuh agent ==="
        sudo installer -pkg ${AGENT_PKG} -target /

        echo "=== Configuring agent ==="
        sudo /Library/Ossec/bin/agent-auth -m ${WAZUH_MANAGER}

        echo "=== Starting Wazuh agent ==="
        sudo /Library/Ossec/bin/wazuh-control start

        echo "=== Verifying agent status ==="
        sudo /Library/Ossec/bin/wazuh-control status

        echo "=== Cleaning up ==="
        rm -f /tmp/${AGENT_PKG}

        echo "SUCCESS: Wazuh agent deployed on ${node_name}"
EOF

    return $?
}

# Main deployment
echo "Wazuh Agent Cluster Deployment"
echo "Manager: ${WAZUH_MANAGER}"
echo "Version: ${WAZUH_VERSION}"
echo ""

if [ "$1" == "--all" ]; then
    # Deploy to all nodes
    for node in "${!NODES[@]}"; do
        deploy_to_node "$node" "${NODES[$node]}" || echo "Failed: $node"
        echo ""
    done
elif [ -n "$1" ]; then
    # Deploy to specific node
    if [[ -v NODES[$1] ]]; then
        deploy_to_node "$1" "${NODES[$1]}"
    else
        echo "Unknown node: $1"
        echo "Available nodes: ${!NODES[@]}"
        exit 1
    fi
else
    echo "Usage: $0 [--all | node-name]"
    echo "Available nodes:"
    for node in "${!NODES[@]}"; do
        ip="${NODES[$node]}"
        status="OFFLINE"
        ping -c 1 -W 1 "$ip" >/dev/null 2>&1 && status="ONLINE"
        echo "  $node ($ip) - $status"
    done
fi
