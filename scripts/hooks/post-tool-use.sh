#!/bin/bash
# Post Tool Use Hook - Track tool usage patterns

# Read hook input from stdin
INPUT=$(cat)

# Extract tool name if available
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('tool_name', 'unknown'))" 2>/dev/null || echo "unknown")

# Log tool usage (non-blocking)
echo "{\"event\": \"tool_use\", \"node\": \"macpro51\", \"tool\": \"$TOOL_NAME\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/tool-usage.log 2>/dev/null || true

# Return success
exit 0
