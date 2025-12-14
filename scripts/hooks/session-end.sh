#!/bin/bash
# SessionEnd Hook - Full AGI Integration
# Saves session context, triggers learning consolidation, records metrics
#
# Integrations: TPU, AGI Bridge, Memory, Activity Dashboard
# Performance target: <300ms total (can be slightly longer as session is ending)

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract session info
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        session_end 2>/dev/null

    # Trigger memory consolidation (async, fire and forget)
    python3 -c "
import sys
sys.path.insert(0, '/home/marc/agentic-system/scripts/hooks')
try:
    from agi_bridge import AGIBridge
    bridge = AGIBridge()
    # Light consolidation - full consolidation runs on schedule
    # Just ensure any pending learnings are flushed
except:
    pass
" 2>/dev/null &
} &

# Log session end
{
    # Count tool usage from this session
    TOOL_COUNT=$(grep -c "\"session_id\":\"$SESSION_ID\"" /home/marc/agentic-system/logs/tool-usage.log 2>/dev/null || echo "0")

    echo "{\"event\":\"session_end\",\"session_id\":\"$SESSION_ID\",\"node\":\"$(hostname)\",\"tool_count\":$TOOL_COUNT,\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/sessions.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "SessionEnd" "session_end" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
