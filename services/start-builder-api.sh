#!/bin/bash
# Start Builder Node API Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/agentic-system/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Check if Redis is running
if ! docker ps | grep -q redis; then
    echo "⚠️  Redis is not running. Starting Redis..."
    docker start redis || echo "❌ Failed to start Redis"
fi

# Start the API server
echo "🚀 Starting Builder Node API..."
echo "   Logs: $LOG_DIR/builder-api.log"
echo "   Port: 9000"
echo ""

cd "$SCRIPT_DIR"
exec python3 builder-node-api.py
