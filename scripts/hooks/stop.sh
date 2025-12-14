#!/bin/bash
# Stop Hook - Full AGI Integration
# Saves context on stop, records session interrupt
#
# Integrations: Memory (context save), Activity Dashboard, Voice (notification)
# Performance target: <150ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        stop 2>/dev/null
} &

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to sessions.log below for activity tracking

# Log stop event
{
    echo "{\"event\":\"stop\",\"session\":\"$SESSION_ID\",\"node\":\"$(hostname)\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/sessions.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "Stop" "stop" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
