#!/bin/bash
# Complete Cluster Deployment Script
# Deploys everything to all nodes: MAKER, autonomous agents, identities, memory

set -e  # Exit on error


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

echo "================================================================"
echo "COMPLETE CLUSTER DEPLOYMENT"
echo "================================================================"
echo "Deploying MAKER + Autonomous Agents + Identity + Memory to all nodes"
echo ""

# Node configuration
NODES=(
    "mac-studio:192.168.1.16:orchestrator"
    "macbook-air-m3:192.168.1.76:researcher"
    "completeu-server:192.168.1.186:ai-inference"
)

# Files to deploy
DEPLOY_FILES=(
    # Core systems
    "cluster-deployment/node_chat_client.py"
    "cluster-deployment/node_chat_daemon.py"
    "cluster-deployment/node_persona.py"
    "cluster-deployment/autonomous_node_agent.py"
    "cluster-deployment/agi_orchestrator.py"
    "cluster-deployment/enhanced_conversation_viewer.py"

    # MAKER framework
    "src/maker_swarm_integration.py"
    "src/maker_distributed_ollama.py"
    "src/maker_coordinator.py"
    "intelligent-agents/multi_agent_coordinator_maker.py"

    # Documentation
    "docs/MAKER_SWARM_INTEGRATION.md"
    "docs/MAKER_INTEGRATION_COMPLETE.md"
    "docs/ZERO_COST_AUTONOMOUS_AGENTS.md"
    "docs/CLUSTER_RESOURCE_OFFLOAD_STRATEGY.md"
    "docs/OFFLOAD_VS_CHAT_ARCHITECTURE.md"
    "MAKER_READY.md"

    # Tests
    "tests/test_maker_swarm_integration.py"
    "tests/comprehensive_cluster_test.py"
    "scripts/demo-maker-integration.py"
)

# Function to deploy to a single node
deploy_to_node() {
    local node_info=$1
    IFS=':' read -r node_id ip role <<< "$node_info"

    echo ""
    echo "----------------------------------------------------------------"
    echo "DEPLOYING TO: $node_id ($role)"
    echo "----------------------------------------------------------------"

    # Check if node is reachable
    if ! ping -c 1 -W 1 "$ip" > /dev/null 2>&1; then
        echo "❌ Node $node_id is OFFLINE at $ip - skipping"
        return 1
    fi

    echo "✅ Node is ONLINE"

    # Create directory structure
    echo "📁 Creating directory structure..."
    ssh "$node_id" "mkdir -p ~/agentic-system/{cluster-deployment,src,intelligent-agents,docs,tests,scripts,databases/cluster/nodes/{macpro51,mac-studio,macbook-air-m3,completeu-server}}"

    # Sync files
    echo "📦 Syncing files..."
    for file in "${DEPLOY_FILES[@]}"; do
        if [ -f "$STORAGE_BASE/$file" ]; then
            rsync -az "$STORAGE_BASE/$file" "$node_id:~/agentic-system/$file"
            echo "  ✓ $file"
        else
            echo "  ⚠ $file not found - skipping"
        fi
    done

    # Sync cluster configuration
    echo "⚙️  Syncing cluster configuration..."
    rsync -az "$STORAGE_BASE/cluster-deployment/cluster-nodes.json" "$node_id:~/agentic-system/cluster-deployment/"

    # Deploy node-specific configuration
    echo "🔧 Creating node-specific configuration..."
    ssh "$node_id" "cat > ~/.claude/node-config.json" << EOF
{
  "node_id": "$node_id",
  "role": "$role",
  "ip": "$ip",
  "storage": {
    "base": "$(ssh $node_id 'if [ -d /mnt/agentic-system ]; then echo /mnt/agentic-system; else echo ~/agentic-system; fi')"
  }
}
EOF

    # Initialize per-node memory database
    echo "💾 Initializing per-node memory..."
    ssh "$node_id" "cd ~/agentic-system && python3 << 'PYEOF'
import sqlite3
from pathlib import Path

# Create per-node memory database
node_id = '$node_id'
storage_base = Path.home() / 'agentic-system'
memory_path = storage_base / 'databases' / 'cluster' / 'nodes' / node_id / 'personal_memories.db'

memory_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(memory_path))
cursor = conn.cursor()

# Create memories table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS memories (
        memory_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        content TEXT NOT NULL,
        memory_type TEXT,
        importance REAL,
        tags TEXT
    )
''')

# Create experiences table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS experiences (
        experience_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        description TEXT NOT NULL,
        outcome TEXT,
        learnings TEXT
    )
''')

conn.commit()
conn.close()

print(f'✅ Memory database initialized for {node_id}')
PYEOF
"

    # Start/restart autonomous agent
    echo "🤖 Starting autonomous agent..."
    ssh "$node_id" "pkill -f autonomous_node_agent.py || true"
    ssh "$node_id" "cd ~/agentic-system/cluster-deployment && nohup python3 autonomous_node_agent.py > /tmp/autonomous-agent.log 2>&1 &"

    echo "✅ Deployment to $node_id complete!"
}

# Main deployment loop
echo "Starting deployment to all nodes..."
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for node_info in "${NODES[@]}"; do
    if deploy_to_node "$node_info"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo ""
echo "================================================================"
echo "DEPLOYMENT SUMMARY"
echo "================================================================"
echo "✅ Successful: $SUCCESS_COUNT nodes"
echo "❌ Failed: $FAIL_COUNT nodes"
echo ""

# Verification
echo "================================================================"
echo "VERIFICATION"
echo "================================================================"
echo ""
echo "Checking node connectivity and autonomous agents..."
echo ""

for node_info in "${NODES[@]}"; do
    IFS=':' read -r node_id ip role <<< "$node_info"

    if ping -c 1 -W 1 "$ip" > /dev/null 2>&1; then
        # Check if autonomous agent is running
        if ssh "$node_id" "ps aux | grep -q '[a]utonomous_node_agent.py'"; then
            echo "✅ $node_id: ONLINE, autonomous agent RUNNING"
        else
            echo "⚠️  $node_id: ONLINE, autonomous agent NOT RUNNING"
        fi
    else
        echo "❌ $node_id: OFFLINE"
    fi
done

echo ""
echo "================================================================"
echo "POST-DEPLOYMENT INSTRUCTIONS"
echo "================================================================"
echo ""
echo "1. Test node-to-node chat:"
echo "   cd $STORAGE_BASE/cluster-deployment"
echo "   python3 node_chat_client.py send completeu-server 'Hello from deployment!'"
echo ""
echo "2. Test MAKER integration:"
echo "   cd /mnt/agentic-system"
echo "   python3 scripts/demo-maker-integration.py"
echo ""
echo "3. Run comprehensive tests:"
echo "   python3 tests/comprehensive_cluster_test.py"
echo ""
echo "4. Monitor autonomous agents:"
echo "   tail -f $STORAGE_BASE/logs/autonomous-agent.log | grep 'completeu-server\\|ZERO COST'"
echo ""
echo "5. Watch cluster conversations:"
echo "   python3 cluster-deployment/enhanced_conversation_viewer.py"
echo ""
echo "================================================================"
echo "DEPLOYMENT COMPLETE! 🎉"
echo "================================================================"
