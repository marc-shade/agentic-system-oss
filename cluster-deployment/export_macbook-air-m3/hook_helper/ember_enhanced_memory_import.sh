#!/bin/bash
# Ember Enhanced-Memory Batch Import
# Imports Ember logs into enhanced-memory MCP for Phoenix's learning

# Note: This script generates the sync payload
# The actual MCP import would be done by Claude Code when it has MCP access

SYNC_OUTPUT="/tmp/ember_memory_sync_payload.json"
CONTEXT_OUTPUT="/tmp/ember_context_summary.txt"

# Generate sync payload
echo "🔥 Ember Memory Sync - Generating payload..."
python3 ~/.claude/hooks/ember_memory_sync.py sync > "$SYNC_OUTPUT"

if [ $? -eq 0 ]; then
    STATS=$(cat "$SYNC_OUTPUT" | jq -r '.stats | "Violations: \(.violations), Outcomes: \(.outcomes), Patterns: \(.patterns)"')
    echo "✓ Sync payload generated: $STATS"
    echo "  File: $SYNC_OUTPUT"
else
    echo "✗ Failed to generate sync payload"
    exit 1
fi

# Generate context summary
python3 ~/.claude/hooks/ember_memory_sync.py summary > "$CONTEXT_OUTPUT"

if [ $? -eq 0 ]; then
    echo "✓ Context summary generated"
    echo "  File: $CONTEXT_OUTPUT"
else
    echo "✗ Failed to generate context summary"
fi

# Display summary
echo ""
echo "=== Ember Context Preview ==="
head -30 "$CONTEXT_OUTPUT"
echo ""
echo "=== Next Steps ==="
echo "1. Claude Code will import this on next startup"
echo "2. Phoenix can query violations via enhanced-memory"
echo "3. Self-improvement loop is active"
