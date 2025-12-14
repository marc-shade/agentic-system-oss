#!/bin/bash
# Notification Hook - Full AGI Integration
# Routes notifications to voice mode and activity dashboard
#
# Integrations: Voice Mode (for important notifications), Activity Dashboard
# Performance target: <100ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract notification info
MESSAGE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message', d.get('content', ''))[:200])" 2>/dev/null || echo "")
LEVEL=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('level', d.get('type', 'info')))" 2>/dev/null || echo "info")
TITLE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('title', '')[:50])" 2>/dev/null || echo "")

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        notification --message "$MESSAGE" --level "$LEVEL" 2>/dev/null
} &

# Voice notification for important levels (non-blocking)
if [ "$LEVEL" = "warning" ] || [ "$LEVEL" = "error" ] || [ "$LEVEL" = "critical" ]; then
    {
        # Use voice mode MCP for spoken notification
        curl -s -X POST "http://localhost:8765/speak" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"${TITLE:-Notification}: ${MESSAGE:0:100}\", \"voice\": \"en-IE-EmilyNeural\"}" \
            --connect-timeout 0.2 --max-time 0.5 >/dev/null 2>&1
    } &
fi

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to notifications.log below for activity tracking

# Log notification
{
    echo "{\"event\":\"notification\",\"level\":\"$LEVEL\",\"message\":\"${MESSAGE:0:50}\",\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/notifications.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "Notification" "notification" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
