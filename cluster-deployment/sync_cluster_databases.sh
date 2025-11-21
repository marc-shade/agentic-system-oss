#!/bin/bash
#
# Sync Cluster Databases
# Synchronizes databases between orchestrator and worker nodes
#
# Usage:
#   ./sync_cluster_databases.sh [node_id]
#
# Examples:
#   ./sync_cluster_databases.sh macbook-air-m3
#   ./sync_cluster_databases.sh all
#

set -e

ORCHESTRATOR_IP="192.168.1.16"
DB_BASE="/Volumes/SSDRAID0/agentic-system/databases/cluster"

NODE_IPS=(
    "macbook-air-m3:192.168.1.76"
    "completeu-server:192.168.1.186"
    "macpro51:192.168.1.183"
)

sync_to_node() {
    local node_id=$1
    local node_ip=$2

    echo "Syncing databases to $node_id ($node_ip)..."

    # Sync shared memories (bidirectional)
    echo "  → Shared memories..."
    rsync -avz --ignore-existing \
        "$DB_BASE/shared_memories.db" \
        "marc@$node_ip:~/agentic-system/databases/cluster/" 2>/dev/null || \
        echo "    ⚠️  Could not sync to $node_ip"

    # Sync node registry (orchestrator → workers)
    echo "  → Node registry..."
    rsync -avz \
        "$DB_BASE/node_registry.db" \
        "marc@$node_ip:~/agentic-system/databases/cluster/" 2>/dev/null || \
        echo "    ⚠️  Could not sync to $node_ip"

    # Sync messages database (bidirectional)
    echo "  → Messages database..."
    rsync -avz --ignore-existing \
        "$DB_BASE/node_messages.db" \
        "marc@$node_ip:~/agentic-system/databases/cluster/" 2>/dev/null || \
        echo "    ⚠️  Could not sync to $node_ip"

    echo "  ✅ Sync to $node_id complete"
}

sync_from_node() {
    local node_id=$1
    local node_ip=$2

    echo "Syncing databases from $node_id ($node_ip)..."

    # Pull shared memories from worker
    echo "  ← Shared memories..."
    rsync -avz --ignore-existing \
        "marc@$node_ip:~/agentic-system/databases/cluster/shared_memories.db" \
        "$DB_BASE/" 2>/dev/null || \
        echo "    ⚠️  Could not pull from $node_ip"

    # Pull messages from worker
    echo "  ← Messages database..."
    rsync -avz --ignore-existing \
        "marc@$node_ip:~/agentic-system/databases/cluster/node_messages.db" \
        "$DB_BASE/" 2>/dev/null || \
        echo "    ⚠️  Could not pull from $node_ip"

    echo "  ✅ Sync from $node_id complete"
}

if [ $# -eq 0 ] || [ "$1" == "all" ]; then
    echo "🔄 Syncing all cluster nodes"
    echo "=============================="
    echo ""

    for node_info in "${NODE_IPS[@]}"; do
        IFS=':' read -r node_id node_ip <<< "$node_info"

        # First sync FROM worker to get their updates
        sync_from_node "$node_id" "$node_ip"
        echo ""

        # Then sync TO worker to send orchestrator updates
        sync_to_node "$node_id" "$node_ip"
        echo ""
    done

    echo "✅ All nodes synced!"
else
    # Sync specific node
    NODE_ID=$1
    NODE_IP=""

    for node_info in "${NODE_IPS[@]}"; do
        IFS=':' read -r nid nip <<< "$node_info"
        if [ "$nid" == "$NODE_ID" ]; then
            NODE_IP=$nip
            break
        fi
    done

    if [ -z "$NODE_IP" ]; then
        echo "❌ Unknown node: $NODE_ID"
        echo "Known nodes: ${NODE_IPS[@]}"
        exit 1
    fi

    echo "🔄 Syncing $NODE_ID"
    echo "==================="
    echo ""

    sync_from_node "$NODE_ID" "$NODE_IP"
    echo ""
    sync_to_node "$NODE_ID" "$NODE_IP"

    echo ""
    echo "✅ $NODE_ID synced!"
fi
