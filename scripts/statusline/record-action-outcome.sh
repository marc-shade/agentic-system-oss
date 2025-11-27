#!/bin/bash
# Record an action outcome to the enhanced-memory database
# Used by hooks to track success/failure of operations
#
# Usage: record-action-outcome.sh <action_type> <success_score> [description] [context] [session_id]
#
# Examples:
#   record-action-outcome.sh "Edit" 1.0 "Edited file" "/path/to/file.py" "session123"
#   record-action-outcome.sh "Bash" 0.0 "Command failed" "git push" "session456"

STORAGE_BASE="${AGENTIC_ROOT:-/home/marc/agentic-system}"
# Use the correct enhanced-memory database path
MEMORY_DB="$HOME/.claude/enhanced_memories/memory.db"

ACTION_TYPE="${1:-unknown}"
SUCCESS_SCORE="${2:-0.5}"
DESCRIPTION="${3:-}"
ACTION_CONTEXT="${4:-}"
SESSION_ID="${5:-}"

# Validate success score is between 0 and 1
if ! [[ "$SUCCESS_SCORE" =~ ^[0-9]*\.?[0-9]+$ ]]; then
    SUCCESS_SCORE="0.5"
fi

# Escape single quotes for SQL
SAFE_DESC=$(echo "$DESCRIPTION" | sed "s/'/''/g")
SAFE_CONTEXT=$(echo "$ACTION_CONTEXT" | sed "s/'/''/g")
SAFE_SESSION=$(echo "$SESSION_ID" | sed "s/'/''/g")

# Insert the action outcome with full context
sqlite3 "$MEMORY_DB" "
INSERT INTO action_outcomes (action_type, action_description, success_score, action_context, session_id, agent_id)
VALUES ('$ACTION_TYPE', '$SAFE_DESC', $SUCCESS_SCORE, '$SAFE_CONTEXT', '$SAFE_SESSION', 'macpro51');
"

# Clear the cache so statusline updates
rm -f /tmp/agentic-statusline-cache/action_rate 2>/dev/null

echo "Recorded: $ACTION_TYPE ($SUCCESS_SCORE)"
