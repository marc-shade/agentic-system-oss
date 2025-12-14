#!/bin/bash
# Session Start Hook - Log session initialization to cluster memory

NODE_ID="macpro51"
TIMESTAMP=$(date -Iseconds)
SESSION_DIR="${CLAUDE_SESSION_DIR:-unknown}"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Log to system
echo "{\"event\": \"session_start\", \"node\": \"$NODE_ID\", \"timestamp\": \"$TIMESTAMP\", \"session_dir\": \"$SESSION_DIR\", \"session_id\": \"$SESSION_ID\"}" >> /home/marc/agentic-system/logs/claude-sessions.log 2>/dev/null || true

# Ensure memory status check script is available in /tmp
if [ ! -L /tmp/memory-status-check.sh ]; then
    ln -sf /home/marc/agentic-system/scripts/statusline/memory-status-check.sh /tmp/memory-status-check.sh 2>/dev/null || true
fi

# Create per-session timestamp file for statusline timer
# Each session gets its own file to support multiple concurrent sessions
if [ "$SESSION_ID" != "unknown" ]; then
    SESSION_FILE="/tmp/claude_session_${SESSION_ID}.json"
else
    # Fallback to legacy single-session file if SESSION_ID not available
    SESSION_FILE="/tmp/claude_session_start.json"
fi

# Always create/update the session file on session start
echo "{\"start_time\": \"$TIMESTAMP\", \"session_id\": \"$SESSION_ID\"}" > "$SESSION_FILE" 2>/dev/null || true

# Create a symlink to track the "current" session for statusline fallback
ln -sf "$SESSION_FILE" /tmp/claude_session_current.json 2>/dev/null || true

# Load memory context for session (non-blocking)
{
    /mnt/agentic-system/scripts/hooks/memory-helper.py load_context "$SESSION_ID" > /tmp/claude_memory_context.json 2>/dev/null
} &

# Return success (hooks should not block)
exit 0
