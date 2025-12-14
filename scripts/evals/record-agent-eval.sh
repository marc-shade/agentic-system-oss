#!/bin/bash
# Record agent execution metrics for self-improvement
# Usage: record-agent-eval.sh <agent_type> <execution_time_ms> <success> [quality_score] [task_desc]

AGENT_TYPE="${1:-unknown}"
EXECUTION_TIME_MS="${2:-0}"
SUCCESS="${3:-1}"
QUALITY_SCORE="${4:-0.8}"
TASK_DESC="${5:-}"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

DB_PATH="$HOME/.claude/enhanced_memories/memory.db"

# Escape single quotes
SAFE_TASK=$(echo "$TASK_DESC" | sed "s/'/''/g" | head -c 200)

sqlite3 "$DB_PATH" "
INSERT INTO agent_evals (agent_type, task_description, execution_time_ms, success, quality_score, parent_session_id)
VALUES ('$AGENT_TYPE', '$SAFE_TASK', $EXECUTION_TIME_MS, $SUCCESS, $QUALITY_SCORE, '$SESSION_ID');
" 2>/dev/null

echo "Recorded agent eval: $AGENT_TYPE ($EXECUTION_TIME_MS ms, success=$SUCCESS)"
