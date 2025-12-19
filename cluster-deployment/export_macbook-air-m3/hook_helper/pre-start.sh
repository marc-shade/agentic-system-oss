#!/bin/bash
# Pre-start hook to ensure clean MCP environment

# Kill any rogue MCP processes
pkill -f "automated_mcp_maintenance" 2>/dev/null
pkill -f "startup-everything" 2>/dev/null
pkill -f "unified_startup_orchestrator" 2>/dev/null

# Count current MCPs
COUNT=$(ps aux | grep -E "(mcp|MCP)" | grep -v grep | wc -l)
if [ $COUNT -gt 10 ]; then
    echo "⚠️  Cleaning up excessive MCPs..."
    python3 /Users/marc/.claude/emergency-cleanup.py
fi

# Set environment to prevent auto-loading
export DISABLE_MCP_AUTOSTART=1
export MCP_LOADER_MODE=minimal

# DGM Auto-Start Integration
echo "🧬 Starting DGM auto-start..."
python3 /Users/marc/.claude/dgm-auto-start.py
echo "✅ DGM auto-start completed"
