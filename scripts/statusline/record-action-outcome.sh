#!/bin/bash
# Record an action outcome to the enhanced-memory database
# Used by hooks to track success/failure of operations
#
# Usage: record-action-outcome.sh <action_type> <success_score> [description]
#
# Examples:
#   record-action-outcome.sh "code_edit" 1.0 "Successfully edited auth module"
#   record-action-outcome.sh "test_run" 0.0 "Tests failed with 3 errors"
#   record-action-outcome.sh "build" 0.8 "Build succeeded with warnings"

STORAGE_BASE="${AGENTIC_ROOT:-/home/marc/agentic-system}"
# Use the correct enhanced-memory database path
MEMORY_DB="$HOME/.claude/enhanced_memories/memory.db"

ACTION_TYPE="${1:-unknown}"
SUCCESS_SCORE="${2:-0.5}"
DESCRIPTION="${3:-}"

# Validate success score is between 0 and 1
if ! [[ "$SUCCESS_SCORE" =~ ^[0-9]*\.?[0-9]+$ ]]; then
    SUCCESS_SCORE="0.5"
fi

# Ensure table exists
sqlite3 "$MEMORY_DB" "
CREATE TABLE IF NOT EXISTS action_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    action_description TEXT,
    expected_result TEXT,
    actual_result TEXT,
    success_score REAL DEFAULT 0.5,
    session_id TEXT,
    entity_id INTEGER,
    action_context TEXT,
    duration_ms INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_action_outcomes_created ON action_outcomes(created_at);
" 2>/dev/null

# Insert the action outcome
sqlite3 "$MEMORY_DB" "
INSERT INTO action_outcomes (action_type, action_description, success_score)
VALUES ('$ACTION_TYPE', '$(echo "$DESCRIPTION" | sed "s/'/''/g")', $SUCCESS_SCORE);
"

# Clear the cache so statusline updates
rm -f /tmp/agentic-statusline-cache/action_rate 2>/dev/null

echo "Recorded: $ACTION_TYPE ($SUCCESS_SCORE)"
