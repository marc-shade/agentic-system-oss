#!/bin/bash
# SessionStart Hook - Full AGI Integration
# Initializes session with context restoration, memory loading, and AGI state
#
# Integrations: TPU, AGI Bridge, Memory, Activity Dashboard
# Performance target: <200ms total

exec 2>/dev/null  # Suppress stderr for clean operation

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract session info
SESSION_ID=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('session_id', 'unknown'))" 2>/dev/null || echo "unknown")
export CLAUDE_SESSION_ID="$SESSION_ID"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations (with timeout)
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        session_start 2>/dev/null &
    INTEGRATION_PID=$!

    # Wait with timeout (300ms max)
    sleep 0.3
    kill -0 $INTEGRATION_PID 2>/dev/null && kill $INTEGRATION_PID 2>/dev/null
} &

# Log session start (non-blocking)
{
    echo "{\"event\":\"session_start\",\"session_id\":\"$SESSION_ID\",\"node\":\"$(hostname)\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/sessions.log
    # Reset context status - new session = fresh context
    python3 -c "
import json
from pathlib import Path
from datetime import datetime
ctx_file = Path.home() / '.claude' / 'context_status.json'
ctx_file.write_text(json.dumps({
    'percent': 10,
    'estimated': True,
    'source': 'session_start_hook',
    'updated_at': datetime.now().isoformat(),
    'note': 'Fresh session started'
}))
" 2>/dev/null
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "SessionStart" "session_start" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
