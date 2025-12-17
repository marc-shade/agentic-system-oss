#!/bin/bash
#
# Health Check Script for Agentic System
# Verifies all components are working correctly
#

set -e

echo "=== Agentic System Health Check ==="
echo ""

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"

    if eval "$cmd" > /dev/null 2>&1; then
        echo "✓ $name"
        ((PASS++))
    else
        echo "✗ $name"
        ((FAIL++))
    fi
}

# Python checks
echo "Python Environment:"
check "Python 3.10+" "python3 -c 'import sys; assert sys.version_info >= (3, 10)'"
check "fastmcp installed" "python3 -c 'import fastmcp'"

echo ""
echo "Database Files:"
check "Memory database exists" "test -f ~/.claude/enhanced_memory_oss/memory.db"
check "Runtime database exists" "test -f ~/.claude/agent_runtime_oss/runtime.db"

echo ""
echo "MCP Servers:"
check "enhanced-memory-mcp" "python3 -c 'import sys; sys.path.insert(0, \"mcp-servers/enhanced-memory-mcp\"); exec(open(\"mcp-servers/enhanced-memory-mcp/server.py\").read().split(\"if __name__\")[0])'"
check "agent-runtime-mcp" "python3 -c 'import sys; sys.path.insert(0, \"mcp-servers/agent-runtime-mcp\"); exec(open(\"mcp-servers/agent-runtime-mcp/server.py\").read().split(\"if __name__\")[0])'"

echo ""
echo "Claude Code Configuration:"
if [ -f ~/.claude.json ]; then
    if grep -q "enhanced-memory" ~/.claude.json 2>/dev/null; then
        echo "✓ enhanced-memory configured"
        ((PASS++))
    else
        echo "✗ enhanced-memory not configured"
        ((FAIL++))
    fi
    if grep -q "agent-runtime" ~/.claude.json 2>/dev/null; then
        echo "✓ agent-runtime configured"
        ((PASS++))
    else
        echo "✗ agent-runtime not configured"
        ((FAIL++))
    fi
else
    echo "✗ ~/.claude.json not found"
    ((FAIL++))
    ((FAIL++))
fi

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "All checks passed! System is healthy."
    exit 0
else
    echo "Some checks failed. Please review and fix issues above."
    exit 1
fi
