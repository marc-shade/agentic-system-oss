#!/bin/bash
# Start Autonomous Agent on macOS (background process)
#
# Since macOS nodes don't have systemd, this script starts the agent
# as a background process with nohup and logs to file.

set -e

# Detect storage base from node config ONLY
# CRITICAL: Never use filesystem detection as nodes may have multiple
# volumes mounted. We must respect each node's own configuration.

NODE_CONFIG="$HOME/.claude/node-config.json"

if [ ! -f "$NODE_CONFIG" ]; then
    echo "❌ Error: Node configuration not found at $NODE_CONFIG"
    echo "   Each node MUST have its own node-config.json"
    exit 1
fi

# Extract storage.base from config using python
STORAGE_BASE=$(python3 -c "
import json
with open('$NODE_CONFIG') as f:
    config = json.load(f)
    storage = config.get('storage', {}).get('base')
    if not storage:
        raise ValueError('storage.base not found in config')
    print(storage)
" 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ Error: Could not read storage.base from $NODE_CONFIG"
    echo "   $STORAGE_BASE"
    exit 1
fi

echo "📂 Using storage base from config: $STORAGE_BASE"

AGENT_SCRIPT="$STORAGE_BASE/cluster-deployment/autonomous_node_agent.py"
LOG_FILE="$STORAGE_BASE/logs/autonomous-agent.log"
PID_FILE="$STORAGE_BASE/logs/autonomous-agent.pid"

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo "   Please export ANTHROPIC_API_KEY before running"
    exit 1
fi

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  Agent already running (PID $OLD_PID)"
        echo "   Use stop_autonomous_agent_macos.sh to stop it first"
        exit 1
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Ensure logs directory exists
mkdir -p "$STORAGE_BASE/logs"

# Start agent in background
echo "Starting autonomous agent..."
cd "$STORAGE_BASE/cluster-deployment"
export PYTHONPATH="$STORAGE_BASE/cluster-deployment"

nohup python3 "$AGENT_SCRIPT" >> "$LOG_FILE" 2>&1 &
AGENT_PID=$!

# Save PID
echo "$AGENT_PID" > "$PID_FILE"

# Wait a moment and check if it's running
sleep 2
if ps -p "$AGENT_PID" > /dev/null 2>&1; then
    echo "✅ Agent started successfully (PID $AGENT_PID)"
    echo "   Logs: $LOG_FILE"
    echo "   PID file: $PID_FILE"
else
    echo "❌ Agent failed to start"
    echo "   Check logs: $LOG_FILE"
    exit 1
fi
