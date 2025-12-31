#!/bin/bash
# Wrapper script for MCP HTTP Proxy - used by launchd
# Ensures proper environment and graceful shutdown

export PATH="/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONPATH="/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp"

cd /Volumes/SSDRAID0/agentic-system/mcp-servers/mcp-http-proxy

# Wait for filesystem to be ready
sleep 2

# Run the proxy - exec replaces this shell with python
exec /opt/homebrew/Caskroom/miniconda/base/bin/python3 -u server.py
