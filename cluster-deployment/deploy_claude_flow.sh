#!/bin/bash
#
# Deploy Claude-Flow to all cluster nodes
# Installs claude-flow and configures MCP server on each node
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../scripts/detect-storage.sh"

echo "🚀 Deploying Claude-Flow to Agentic Cluster"
echo "============================================"
echo ""

# Function to deploy to a single node
deploy_to_node() {
    local node=$1
    local node_home=$2

    echo "📦 Deploying to $node..."

    # Check if node is reachable
    if ! ping -c 1 -W 2 "$node" &>/dev/null; then
        echo "  ⚠️  Node $node not reachable, skipping..."
        return 1
    fi

    # Deploy claude-flow
    ssh "$node" <<EOF
        set -e

        # Source storage detection
        source ~/agentic-system/scripts/detect-storage.sh || source /mnt/agentic-system/scripts/detect-storage.sh

        echo "  • Storage: \$STORAGE_BASE"
        cd \$STORAGE_BASE

        # Clone or update claude-flow
        if [ -d "claude-flow" ]; then
            echo "  • Updating existing claude-flow..."
            cd claude-flow
            git pull
        else
            echo "  • Cloning claude-flow..."
            git clone https://github.com/marc-shade/claude-flow.git
            cd claude-flow
        fi

        # Install and build
        echo "  • Installing dependencies..."
        npm install

        echo "  • Building..."
        npm run build

        # Configure MCP server in ~/.claude.json
        echo "  • Configuring MCP server..."
        python3 -c "
import json
from pathlib import Path

config_path = Path.home() / '.claude.json'
if config_path.exists():
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    config = {'mcpServers': {}}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add claude-flow MCP server
config['mcpServers']['claude-flow'] = {
    'command': 'node',
    'args': [
        str(Path.home() / 'agentic-system/claude-flow/dist/src/cli/main.js'),
        'mcp',
        'start',
        '--transport',
        'stdio'
    ],
    'env': {
        'NODE_ID': '$(hostname -s)',
        'CLAUDE_FLOW_DB': str(Path.home() / 'agentic-system/databases/claude/claude_flow_real.db'),
        'STORAGE_BASE': str(Path.home() / 'agentic-system')
    },
    'disabled': False
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print('  ✓ MCP server configured')
"

        echo "  ✅ Deployment complete on $node"
EOF

    if [ $? -eq 0 ]; then
        echo "  ✓ Successfully deployed to $node"
        return 0
    else
        echo "  ✗ Deployment failed on $node"
        return 1
    fi
}

# Main deployment loop
successful=0
failed=0

# Deploy to mac-studio (orchestrator)
if deploy_to_node "mac-studio.local" "marc"; then
    ((successful++))
else
    ((failed++))
fi

# Deploy to macbook-air (researcher)
if deploy_to_node "macbook-air.local" "marc"; then
    ((successful++))
else
    ((failed++))
fi

# macpro51 (builder) - already deployed locally
echo "📦 macpro51 (local)..."
echo "  ✓ Already deployed"
((successful++))

# Summary
echo ""
echo "============================================"
echo "📊 Deployment Summary"
echo "============================================"
echo "  ✅ Successful: $successful nodes"
echo "  ❌ Failed: $failed nodes"
echo ""

if [ $failed -eq 0 ]; then
    echo "🎉 All deployments successful!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code on each node to load MCP server"
    echo "  2. Test with: python3 $SCRIPT_DIR/test_claude_flow_cluster.py"
    exit 0
else
    echo "⚠️  Some deployments failed. Check logs above."
    exit 1
fi
