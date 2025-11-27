#!/bin/bash
# PostToolUse Hook - SIMPLIFIED for reliability
# Logs activity for learning, records action outcomes, sends to Real-time Activity dashboard

exec 2>/dev/null  # Suppress stderr

# Read hook input
INPUT=$(cat)

# Quick extract tool name, output, and context
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "unknown")
TOOL_OUTPUT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_output',{}).get('content','')[:200])" 2>/dev/null || echo "")
# Extract file path or command from tool input for context
TOOL_CONTEXT=$(echo "$INPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
inp = d.get('tool_input', {})
# Try to get file_path, path, command, or pattern as context
ctx = inp.get('file_path') or inp.get('path') or inp.get('command', '')[:100] or inp.get('pattern', '')
print(ctx[:200] if ctx else '')
" 2>/dev/null || echo "")

# Determine success score based on tool and output
SUCCESS_SCORE="0.8"  # Default: assume success
case "$TOOL_NAME" in
    Edit|Write|Read|Glob|Grep)
        # File operations - check for error indicators
        if echo "$TOOL_OUTPUT" | grep -qi "error\|failed\|not found"; then
            SUCCESS_SCORE="0.3"
        else
            SUCCESS_SCORE="1.0"
        fi
        ;;
    Bash)
        # Commands - check exit status indicators
        if echo "$TOOL_OUTPUT" | grep -qi "error\|failed\|exit code"; then
            SUCCESS_SCORE="0.4"
        else
            SUCCESS_SCORE="0.9"
        fi
        ;;
    Task)
        SUCCESS_SCORE="0.85"  # Agent tasks generally succeed
        ;;
esac

# Get session ID (if available from environment)
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Background log, activity posting, and action recording (non-blocking)
{
    # Log to file
    echo "{\"post\":\"$TOOL_NAME\",\"ts\":\"$(date -Is)\",\"score\":$SUCCESS_SCORE}" >> /home/marc/agentic-system/logs/hooks.log

    # POST to Real-time Activity dashboard (port 4100)
    TIMESTAMP=$(date +%s000)  # milliseconds

    # Escape tool output for JSON (basic escaping)
    SAFE_OUTPUT=$(echo "$TOOL_OUTPUT" | sed 's/"/\\"/g' | tr '\n' ' ' | head -c 200)

    curl -s -X POST "http://localhost:4100/api/v1/activity/hook" \
        -H "Content-Type: application/json" \
        -d "{
            \"hook_event_type\": \"PostToolUse\",
            \"tool_name\": \"$TOOL_NAME\",
            \"session_id\": \"$SESSION_ID\",
            \"source_app\": \"Claude Code\",
            \"node_id\": \"macpro51\",
            \"timestamp\": $TIMESTAMP,
            \"payload\": {
                \"tool_name\": \"$TOOL_NAME\",
                \"success_score\": $SUCCESS_SCORE,
                \"output\": \"$SAFE_OUTPUT\"
            }
        }" --connect-timeout 1 --max-time 2 >/dev/null 2>&1

    # Record action outcome for statusline (every 5th action to reduce DB writes)
    RAND=$((RANDOM % 5))
    if [ "$RAND" -eq 0 ]; then
        /home/marc/agentic-system/scripts/statusline/record-action-outcome.sh "$TOOL_NAME" "$SUCCESS_SCORE" "$SAFE_OUTPUT" "$TOOL_CONTEXT" "$SESSION_ID" 2>/dev/null
    fi
} &

exit 0
