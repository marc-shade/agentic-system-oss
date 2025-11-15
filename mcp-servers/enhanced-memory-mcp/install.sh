#!/bin/bash
# Enhanced Memory MCP Installation Script

set -e

echo "Installing Enhanced Memory MCP..."

# Check if we're in the right directory
if [ ! -f "install.sh" ]; then
    echo "Error: Run this script from the enhanced-memory-mcp directory"
    exit 1
fi

# Get the MCP server files from the source
# Option 1: If running on a node with full agentic-system, copy from there
# Option 2: Download from a package repository
# Option 3: User must manually copy from source node

echo ""
echo "⚠️  Manual Setup Required"
echo "========================================"
echo ""
echo "The Enhanced Memory MCP server requires full source files."
echo ""
echo "To complete installation, you have two options:"
echo ""
echo "1. Copy from an existing node:"
echo "   scp -r source-node:/path/to/mcp-servers/enhanced-memory-mcp/* ."
echo ""
echo "2. Download from GitHub (if available):"
echo "   git clone https://github.com/marc-shade/enhanced-memory-mcp.git ."
echo ""
echo "Once you have the files, install dependencies:"
echo "   pip3 install -r requirements.txt"
echo ""
echo "Then test the server:"
echo "   python3 server.py"
echo ""

# Create a placeholder requirements.txt if it doesn't exist
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt <<EOF
# Enhanced Memory MCP Dependencies
qdrant-client>=1.7.0
mcp>=0.9.0
jsonschema>=4.20.0
psutil>=5.9.0
asyncio>=3.4.3
structlog>=24.1.0
EOF
    echo "Created requirements.txt"
fi

echo "Installation script complete."
echo "Remember to copy the full server code before using!"
