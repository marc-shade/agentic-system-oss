#!/bin/bash
# Capture session token usage on exit and accumulate for weekly tracking

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
WEEKLY_FILE="$HOME/.claude/weekly_accumulator.json"
PROM_URL="http://localhost:9464/metrics"

# Clean up session-specific timestamp file
if [ "$SESSION_ID" != "unknown" ]; then
    SESSION_FILE="/tmp/claude_session_${SESSION_ID}.json"
    rm -f "$SESSION_FILE" 2>/dev/null || true
fi

# Also clean up the legacy file if this was the last session
if ! pgrep -f ' claude' >/dev/null 2>&1; then
    rm -f /tmp/claude_session_start.json 2>/dev/null || true
    rm -f /tmp/claude_session_current.json 2>/dev/null || true
fi

# Get current session token usage from Prometheus metrics endpoint
if command -v curl &>/dev/null; then
    # Extract input + output tokens for this session
    TOKENS=$(curl -s "$PROM_URL" 2>/dev/null | \
        grep "claude_code_token_usage_total.*session_id=\"$SESSION_ID\"" | \
        grep -E 'type="(input|output)"' | \
        awk '{print $NF}' | \
        awk '{sum+=$1} END {print int(sum)}')
    
    if [ -n "$TOKENS" ] && [ "$TOKENS" -gt 0 ]; then
        # Initialize or update weekly accumulator
        if [ ! -f "$WEEKLY_FILE" ]; then
            echo '{"sessions": [], "total": 0, "week_start": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > "$WEEKLY_FILE"
        fi
        
        # Add this session's tokens
        python3 - "$WEEKLY_FILE" "$TOKENS" "$SESSION_ID" << 'PYTHON'
import json, sys
from datetime import datetime, timedelta

file_path = sys.argv[1]
new_tokens = int(sys.argv[2])
session_id = sys.argv[3]

# Read current data
with open(file_path, 'r') as f:
    data = json.load(f)

# Check if we need to reset (new week)
week_start = datetime.fromisoformat(data['week_start'].replace('Z', '+00:00'))
now = datetime.now(week_start.tzinfo)
days_elapsed = (now - week_start).days

if days_elapsed >= 7:
    # Reset for new week
    data = {
        'sessions': [],
        'total': 0,
        'week_start': now.isoformat()
    }

# Add this session
data['sessions'].append({
    'session_id': session_id,
    'tokens': new_tokens,
    'timestamp': now.isoformat()
})
data['total'] = sum(s['tokens'] for s in data['sessions'])

# Write back
with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Added {new_tokens} tokens. Weekly total: {data['total']}")
PYTHON
    fi
fi

# Save session data and increment consolidation counter
/mnt/agentic-system/scripts/hooks/memory-helper.py save_session "$SESSION_ID" 2>/dev/null || true

# Continue with original session-end.sh functionality if it exists
