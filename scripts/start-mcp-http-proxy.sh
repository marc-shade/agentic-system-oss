#!/bin/bash
# Start MCP HTTP Proxy Server
# Bridges HTTP requests to MCP stdio protocol on port 8101

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/detect-storage.sh"

PROXY_DIR="$STORAGE_BASE/mcp-servers/mcp-http-proxy"
LOG_FILE="$STORAGE_BASE/logs/mcp-http-proxy.log"

mkdir -p "$STORAGE_BASE/logs"

echo "Starting MCP HTTP Proxy on port 8101..."

# Check if already running
if lsof -i :8101 > /dev/null 2>&1; then
    echo "Port 8101 already in use. Stopping existing process..."
    kill $(lsof -t -i :8101) 2>/dev/null
    sleep 1
fi

# Install dependencies if needed
cd "$PROXY_DIR"
pip3 install -q -r requirements.txt 2>/dev/null

# Start the proxy
nohup python3 "$PROXY_DIR/server.py" > "$LOG_FILE" 2>&1 &
PID=$!

sleep 2

# Verify it started
if curl -s http://localhost:8101/health > /dev/null 2>&1; then
    echo "MCP HTTP Proxy started successfully (PID: $PID)"
    echo "Health check: http://localhost:8101/health"
    echo "Logs: $LOG_FILE"
else
    echo "Warning: Proxy may not be fully ready yet. Check logs at $LOG_FILE"
fi
