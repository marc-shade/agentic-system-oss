#!/bin/bash
# SubagentStop Hook - Capture subagent learnings and outcomes
# Fires when Task tool (subagent) completes

NODE_ID="macpro51"
TIMESTAMP=$(date -Iseconds)

# Read hook input from stdin
INPUT=$(cat)

# Extract subagent information
SUBAGENT_TYPE=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); params=data.get('parameters', {}); print(params.get('subagent_type', 'unknown'))" 2>/dev/null || echo "unknown")
DESCRIPTION=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); params=data.get('parameters', {}); print(params.get('description', ''))" 2>/dev/null || echo "")

# Log subagent completion
echo "{\"event\": \"subagent_stop\", \"node\": \"$NODE_ID\", \"subagent_type\": \"$SUBAGENT_TYPE\", \"description\": \"$DESCRIPTION\", \"timestamp\": \"$TIMESTAMP\"}" >> /home/marc/agentic-system/logs/subagent-activity.log 2>/dev/null || true

# Track subagent performance metrics (background)
(
    # Update subagent execution statistics
    STATS_FILE="/tmp/subagent_stats_${SUBAGENT_TYPE}.json"

    if [ -f "$STATS_FILE" ]; then
        # Increment execution count
        COUNT=$(cat "$STATS_FILE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('count', 0) + 1)" 2>/dev/null || echo 1)
    else
        COUNT=1
    fi

    echo "{\"subagent_type\": \"$SUBAGENT_TYPE\", \"count\": $COUNT, \"last_execution\": \"$TIMESTAMP\"}" > "$STATS_FILE" 2>/dev/null || true

    # Log to memory system for procedural learning
    if [ -f ~/.claude/enhanced_memories/memory.db ]; then
        python3 -c "
import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

try:
    from memory_manager import MemoryManager
    manager = MemoryManager()

    # Record subagent execution as procedural skill
    skill_name = f'subagent_{\"$SUBAGENT_TYPE\"}'.replace('-', '_')
    description = '${DESCRIPTION//\'/\\\"}'

    # This could be enhanced to track success/failure
    manager.record_skill_execution(
        skill_name=skill_name,
        success=True,  # Assume success if hook fires
        execution_time_ms=1000  # Placeholder
    )
except Exception as e:
    pass
" 2>/dev/null || true
    fi
) &

# Return success immediately
exit 0
