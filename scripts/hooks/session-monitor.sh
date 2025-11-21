#!/bin/bash
# Session Monitor Hook - Auto-detects session continuations and updates baseline
# Runs on every tool use to track session state

BASELINE_FILE="/tmp/claude_session_baseline.json"
SESSION_START_FILE="/tmp/claude_session_start.json"
SESSION_LOG="/home/marc/agentic-system/logs/session-tracking.log"

# Ensure log directory exists
mkdir -p "$(dirname "$SESSION_LOG")"

# Get current session ID from Prometheus
CURRENT_SESSION=$(curl -s 'http://127.0.0.1:9090/api/v1/query?query=claude_code_token_usage_total' 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['result'][0]['metric']['session_id'] if d.get('data',{}).get('result') else '')" 2>/dev/null)

if [ -z "$CURRENT_SESSION" ]; then
    # Prometheus not available, exit silently
    exit 0
fi

# Check if baseline file exists
if [ -f "$BASELINE_FILE" ]; then
    # Check if session ID changed (new session started)
    STORED_SESSION=$(python3 -c "import json; f=open('$BASELINE_FILE'); d=json.load(f); print(d.get('session_id',''))" 2>/dev/null)
    
    if [ "$CURRENT_SESSION" != "$STORED_SESSION" ]; then
        # NEW SESSION DETECTED!
        
        # Get current total tokens for new baseline
        NEW_BASELINE=$(curl -s 'http://127.0.0.1:9090/api/v1/query?query=sum(claude_code_token_usage_total{type=~"input|output|cacheCreation"})by(session_id)' 2>/dev/null | \
            python3 -c "import json,sys; d=json.load(sys.stdin); print(int(float(d['data']['result'][-1]['value'][1])) if d.get('data',{}).get('result') else 0)" 2>/dev/null)
        
        # Update baseline file
        python3 << EOPYTHON
import json
from datetime import datetime

baseline_data = {
    'session_id': '$CURRENT_SESSION',
    'baseline_tokens': $NEW_BASELINE,
    'timestamp': datetime.now().isoformat(),
    'auto_detected': True
}

with open('$BASELINE_FILE', 'w') as f:
    json.dump(baseline_data, f)

# Log the session change
with open('$SESSION_LOG', 'a') as log:
    log.write(f"{datetime.now().isoformat()} | NEW_SESSION | {baseline_data['session_id'][:12]} | baseline={$NEW_BASELINE:,}\n")
EOPYTHON
        
        # Update session start time
        python3 << EOPYTHON
import json
from datetime import datetime

session_data = {
    'start_time': datetime.now().astimezone().isoformat(),
    'auto_detected': True
}

with open('$SESSION_START_FILE', 'w') as f:
    json.dump(session_data, f)
EOPYTHON
        
        echo "$(date -Iseconds) | SESSION_CHANGE | old=$STORED_SESSION | new=$CURRENT_SESSION" >> "$SESSION_LOG"
    fi
else
    # No baseline exists, create initial one
    INITIAL_TOKENS=$(curl -s 'http://127.0.0.1:9090/api/v1/query?query=sum(claude_code_token_usage_total{type=~"input|output|cacheCreation"})by(session_id)' 2>/dev/null | \
        python3 -c "import json,sys; d=json.load(sys.stdin); print(int(float(d['data']['result'][-1]['value'][1])) if d.get('data',{}).get('result') else 0)" 2>/dev/null)
    
    python3 << EOPYTHON
import json
from datetime import datetime

baseline_data = {
    'session_id': '$CURRENT_SESSION',
    'baseline_tokens': $INITIAL_TOKENS,
    'timestamp': datetime.now().isoformat(),
    'auto_detected': True,
    'initial': True
}

with open('$BASELINE_FILE', 'w') as f:
    json.dump(baseline_data, f)

with open('$SESSION_LOG', 'a') as log:
    log.write(f"{datetime.now().isoformat()} | INITIAL_BASELINE | {baseline_data['session_id'][:12]} | baseline={$INITIAL_TOKENS:,}\n")
EOPYTHON
    
    echo "$(date -Iseconds) | INITIAL_SESSION | session=$CURRENT_SESSION | tokens=$INITIAL_TOKENS" >> "$SESSION_LOG"
fi

exit 0
