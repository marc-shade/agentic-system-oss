#!/bin/bash
# Post-start hook to verify MCP count

sleep 5
COUNT=$(ps aux | grep -E "(mcp|MCP)" | grep -v grep | wc -l)
echo "📊 MCP Process Count: $COUNT"

if [ $COUNT -gt 10 ]; then
    echo "⚠️  WARNING: Too many MCPs loaded!"
    echo "Run: /Users/marc/.claude/fix-mcp-overload.sh"
fi

# DGM Health Check
echo "🧬 Checking DGM health..."
python3 /Users/marc/.claude/dgm-auto-start.py health
