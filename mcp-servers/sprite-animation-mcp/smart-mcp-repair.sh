#!/bin/bash

# Smart MCP Repair and Maintenance Script for Macbook Air
# Adapted from Mac Studio configuration to work with local environment

set -e  # Exit on any error

echo "🔧 Smart MCP Repair Script - Macbook Air Environment"
echo "================================================="

# Define paths for this environment
CLAUDE_CONFIG_DIR="/Users/marc/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
MCP_DIR="/Users/marc/Documents/Cline/MCP"
BACKUP_DIR="$MCP_DIR/config_backups_$(date +%Y%m%d_%H%M%S)"
FIXED_CONFIG="$MCP_DIR/fixed_claude_desktop_config.json"

# Environment paths (verified for this Mac)
UV_PATH="/Users/marc/.local/bin/uv"
NODE_PATH="/Users/marc/.local/bin/node"
BUNX_PATH="/Users/marc/.bun/bin/bunx"
NPX_PATH="/opt/homebrew/bin/npx"
PYTHON_VENV="/Users/marc/Documents/Cline/MCP/.venv_mcp/bin/python"

echo "📍 Environment paths detected:"
echo "   UV: $UV_PATH"
echo "   Node: $NODE_PATH" 
echo "   Bunx: $BUNX_PATH"
echo "   NPX: $NPX_PATH"
echo "   Python venv: $PYTHON_VENV"
echo

# Step 1: Backup current configuration
echo "💾 Creating backup..."
mkdir -p "$BACKUP_DIR"
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    cp "$CLAUDE_CONFIG_FILE" "$BACKUP_DIR/claude_desktop_config_backup.json"
    echo "✅ Backup created at: $BACKUP_DIR"
else
    echo "⚠️  No existing config found, will create new one"
fi

# Step 2: Verify essential tools exist
echo "🔍 Verifying environment tools..."
missing_tools=()

if [ ! -f "$UV_PATH" ]; then
    missing_tools+=("uv")
fi

if [ ! -f "$NODE_PATH" ]; then
    missing_tools+=("node")
fi

if [ ! -f "$BUNX_PATH" ]; then
    missing_tools+=("bunx")
fi

if [ ! -f "$NPX_PATH" ]; then
    missing_tools+=("npx")
fi

if [ ! -f "$PYTHON_VENV" ]; then
    missing_tools+=("python-venv")
fi

if [ ${#missing_tools[@]} -gt 0 ]; then
    echo "❌ Missing tools: ${missing_tools[*]}"
    echo "Please install missing tools before continuing."
    exit 1
else
    echo "✅ All essential tools found"
fi

# Step 3: Create necessary directories
echo "📁 Creating required directories..."
directories=(
    "/Users/marc/Projects/Generated-Images"
    "/Users/marc/Documents/Obsidian Vault"
    "/Users/marc/Documents/Cline/MCP/vector-db-mcp-server/vectordb_data"
    "/Users/marc/Documents/Cline/MCP/sqlite-mcp-server/data"
    "/Users/marc/Documents/Cline/MCP/asi-watcher-mcp/data"
    "/Users/marc/Documents/Cline/MCP/asi-watcher-mcp/reports"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    echo "✅ Created: $dir"
done

# Step 4: Apply fixed configuration
echo "🔧 Applying fixed configuration..."
if [ -f "$FIXED_CONFIG" ]; then
    mkdir -p "$CLAUDE_CONFIG_DIR"
    cp "$FIXED_CONFIG" "$CLAUDE_CONFIG_FILE"
    echo "✅ Configuration updated successfully"
else
    echo "❌ Fixed config file not found at: $FIXED_CONFIG"
    exit 1
fi

# Step 5: Test critical servers
echo "🧪 Testing critical MCP servers..."

# Test Apple MCP
echo "Testing Apple MCP..."
timeout 10 "$BUNX_PATH" --no-cache @dhravya/apple-mcp@latest --help >/dev/null 2>&1 && echo "✅ Apple MCP: OK" || echo "⚠️  Apple MCP: Check required"

# Test UV-based servers
echo "Testing UV-based servers..."
cd "$MCP_DIR/mcp-image-gen" 2>/dev/null && timeout 10 "$UV_PATH" run image-gen --help >/dev/null 2>&1 && echo "✅ Image Gen: OK" || echo "⚠️  Image Gen: Check required"

# Test Python venv servers
echo "Testing Python venv servers..."
if [ -f "$MCP_DIR/fabric-mcp-server/server.py" ]; then
    timeout 5 "$PYTHON_VENV" -c "import sys; print('Python venv OK')" >/dev/null 2>&1 && echo "✅ Python venv: OK" || echo "⚠️  Python venv: Check required"
fi

# Test Node servers
echo "Testing Node servers..."
if [ -f "$MCP_DIR/ai-prompt-library/server.js" ]; then
    timeout 5 "$NODE_PATH" --version >/dev/null 2>&1 && echo "✅ Node: OK" || echo "⚠️  Node: Check required"
fi

# Step 6: Generate status report
echo "📊 Generating status report..."
cat > "$MCP_DIR/mcp_repair_report_$(date +%Y%m%d_%H%M%S).md" << EOF
# MCP Repair Report - $(date)

## Environment
- UV Path: $UV_PATH
- Node Path: $NODE_PATH  
- Bunx Path: $BUNX_PATH
- Python venv: $PYTHON_VENV

## Actions Taken
- Configuration backed up to: $BACKUP_DIR
- Fixed configuration applied
- Required directories created
- Basic server tests performed

## Next Steps
1. Restart Claude Desktop/Code
2. Test individual servers using: npx @modelcontextprotocol/inspector
3. Check logs in: $MCP_DIR/mcp_logs/

## Key Changes
- Updated all node commands to use: $NODE_PATH
- Updated bunx command to use: $BUNX_PATH  
- Updated uv commands to use: $UV_PATH
- Fixed python venv paths to: $PYTHON_VENV
EOF

echo "✅ Repair completed successfully!"
echo "📄 Report saved to: $MCP_DIR/mcp_repair_report_$(date +%Y%m%d_%H%M%S).md"
echo
echo "🚀 Next steps:"
echo "1. Restart Claude Desktop or Claude Code"
echo "2. Test servers individually if needed"
echo "3. Check $MCP_DIR/mcp_logs/ for any error messages"
echo
echo "Configuration is now optimized for this Macbook Air environment."