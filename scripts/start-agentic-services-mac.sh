#!/bin/bash
# Start all agentic system services on macOS
# Run at login or manually to start services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/detect-storage.sh"

echo "Starting agentic system services..."
echo "Storage base: $STORAGE_BASE"
echo ""

# Function to start a service if not running
start_if_not_running() {
    local name=$1
    local port=$2
    local start_script=$3

    if lsof -i :$port > /dev/null 2>&1; then
        echo "  $name: Already running on port $port"
    else
        echo "  $name: Starting..."
        "$SCRIPT_DIR/$start_script" > /dev/null 2>&1
        sleep 1
        if lsof -i :$port > /dev/null 2>&1; then
            echo "  $name: Started on port $port"
        else
            echo "  $name: Failed to start (check logs)"
        fi
    fi
}

# Start services in dependency order
echo "[Core Services]"
start_if_not_running "Qdrant" 6333 "start-qdrant.sh"

echo ""
echo "[MCP HTTP Services]"
start_if_not_running "MCP HTTP Proxy" 8101 "start-mcp-http-proxy.sh"

echo ""
echo "[Workflow Services]"
start_if_not_running "AutoKitteh" 9980 "start-autokitteh.sh"
# Note: Temporal requires manual start due to complexity

echo ""
echo "Service startup complete."
echo ""
echo "To check all services:"
echo "  lsof -i :6333 -i :8101 -i :9980"
