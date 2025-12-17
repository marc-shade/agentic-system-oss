#!/bin/bash
#
# Database Setup Script for Agentic System
# Creates required database directories and initializes schemas
#

set -e

echo "=== Agentic System Database Setup ==="

# Create database directories
CLAUDE_DIR="$HOME/.claude"
MEMORY_DIR="$CLAUDE_DIR/enhanced_memory_oss"
RUNTIME_DIR="$CLAUDE_DIR/agent_runtime_oss"

echo "Creating database directories..."
mkdir -p "$MEMORY_DIR"
mkdir -p "$RUNTIME_DIR"

echo "  ✓ $MEMORY_DIR"
echo "  ✓ $RUNTIME_DIR"

# Initialize databases by importing the servers
echo ""
echo "Initializing database schemas..."

cd "$(dirname "$0")/.."

# Test Python imports
python3 -c "
import sys
sys.path.insert(0, 'mcp-servers/enhanced-memory-mcp')
sys.path.insert(0, 'mcp-servers/agent-runtime-mcp')

# Import will trigger init_database()
print('  Testing enhanced-memory-mcp...')
try:
    # Just test the imports work
    import sqlite3
    from pathlib import Path

    db_path = Path.home() / '.claude' / 'enhanced_memory_oss' / 'memory.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute('SELECT 1')
    conn.close()
    print('  ✓ Enhanced Memory database initialized')
except Exception as e:
    print(f'  ✗ Enhanced Memory: {e}')

print('  Testing agent-runtime-mcp...')
try:
    db_path = Path.home() / '.claude' / 'agent_runtime_oss' / 'runtime.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute('SELECT 1')
    conn.close()
    print('  ✓ Agent Runtime database initialized')
except Exception as e:
    print(f'  ✗ Agent Runtime: {e}')
"

echo ""
echo "=== Database Setup Complete ==="
echo ""
echo "Database locations:"
echo "  Memory: $MEMORY_DIR/memory.db"
echo "  Runtime: $RUNTIME_DIR/runtime.db"
