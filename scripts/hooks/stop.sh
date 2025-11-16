#!/bin/bash
# Stop Hook - Post-response memory consolidation and learning
# Fires after Claude completes a response (main agent only)

NODE_ID="macpro51"
TIMESTAMP=$(date -Iseconds)

# Log stop event
echo "{\"event\": \"agent_stop\", \"node\": \"$NODE_ID\", \"timestamp\": \"$TIMESTAMP\"}" >> /home/marc/agentic-system/logs/claude-sessions.log 2>/dev/null || true

# Trigger autonomous memory curation (non-blocking background task)
# This consolidates working → episodic → semantic memory
(
    # Only run curation if enhanced memory is accessible
    if [ -f ~/.claude/enhanced_memories/memory.db ]; then
        # Check if enough time has passed since last curation (5+ minutes)
        LAST_CURATION=$(stat -c %Y /tmp/last_memory_curation 2>/dev/null || echo 0)
        NOW=$(date +%s)
        TIME_DIFF=$((NOW - LAST_CURATION))

        if [ $TIME_DIFF -gt 300 ]; then
            # Run memory curation in background
            python3 -c "
import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')
try:
    from memory_manager import MemoryManager
    manager = MemoryManager()
    # Quick curation without heavy processing
    manager.autonomous_memory_curation()
except Exception as e:
    pass
" 2>/dev/null || true

            # Update last curation timestamp
            touch /tmp/last_memory_curation 2>/dev/null || true
        fi
    fi
) &

# Return success immediately (don't wait for background task)
exit 0
