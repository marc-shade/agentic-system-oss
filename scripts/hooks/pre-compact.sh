#!/bin/bash
# PreCompact Hook - Save critical context before compaction
# Fires before context window is compacted (manual /compact or automatic)

NODE_ID="macpro51"
TIMESTAMP=$(date -Iseconds)
SESSION_DIR="${CLAUDE_SESSION_DIR:-unknown}"

# Log pre-compact event
echo "{\"event\": \"pre_compact\", \"node\": \"$NODE_ID\", \"timestamp\": \"$TIMESTAMP\", \"session_dir\": \"$SESSION_DIR\"}" >> /home/marc/agentic-system/logs/claude-sessions.log 2>/dev/null || true

# Create compaction checkpoint in enhanced memory (background task)
(
    if [ -f ~/.claude/enhanced_memories/memory.db ]; then
        # Store pre-compact milestone
        python3 -c "
import sys
import json
from datetime import datetime
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

try:
    from memory_manager import MemoryManager
    manager = MemoryManager()

    # Create checkpoint entity
    checkpoint_data = {
        'name': f'compact_checkpoint_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}',
        'entityType': 'checkpoint',
        'observations': [
            'Context compaction triggered',
            f'Session: $SESSION_DIR',
            f'Node: $NODE_ID',
            'Save important conversation state before compaction'
        ]
    }

    # Store checkpoint
    manager.create_entities([checkpoint_data])
except Exception as e:
    pass
" 2>/dev/null || true
    fi
) &

# Save current conversation metrics
if [ -f /tmp/claude_session_start.json ]; then
    START_TIME=$(cat /tmp/claude_session_start.json | python3 -c "import json, sys; print(json.load(sys.stdin).get('start_time', ''))" 2>/dev/null)
    echo "{\"event\": \"compact_metrics\", \"session_start\": \"$START_TIME\", \"compact_time\": \"$TIMESTAMP\"}" >> /home/marc/agentic-system/logs/compaction-events.log 2>/dev/null || true
fi

# Return success immediately
exit 0
