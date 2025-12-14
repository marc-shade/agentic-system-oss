#!/bin/bash
# Stop Autonomous Agent on macOS

set -e

# Detect storage base from node config ONLY
NODE_CONFIG="$HOME/.claude/node-config.json"

if [ ! -f "$NODE_CONFIG" ]; then
    echo "❌ Error: Node configuration not found at $NODE_CONFIG"
    exit 1
fi

STORAGE_BASE=$(python3 -c "
import json
with open('$NODE_CONFIG') as f:
    config = json.load(f)
    print(config.get('storage', {}).get('base', ''))
" 2>&1)

if [ -z "$STORAGE_BASE" ]; then
    echo "❌ Error: Could not read storage.base from $NODE_CONFIG"
    exit 1
fi

PID_FILE="$STORAGE_BASE/logs/autonomous-agent.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No PID file found - agent may not be running"
    exit 0
fi

AGENT_PID=$(cat "$PID_FILE")

if ps -p "$AGENT_PID" > /dev/null 2>&1; then
    echo "Stopping autonomous agent (PID $AGENT_PID)..."
    kill "$AGENT_PID"
    sleep 2

    # Force kill if still running
    if ps -p "$AGENT_PID" > /dev/null 2>&1; then
        echo "Forcing termination..."
        kill -9 "$AGENT_PID"
    fi

    rm "$PID_FILE"
    echo "✅ Agent stopped"
else
    echo "⚠️  Agent not running (stale PID)"
    rm "$PID_FILE"
fi
