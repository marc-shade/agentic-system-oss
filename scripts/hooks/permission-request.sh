#!/bin/bash
# PermissionRequest Hook - Full AGI Integration
# Notifies user of permission requests, logs for analysis
#
# Integrations: Voice (spoken notification), Activity Dashboard, Memory
# Performance target: <200ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract permission info
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name', d.get('tool', 'unknown')))" 2>/dev/null || echo "unknown")
DESCRIPTION=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('description', d.get('message', ''))[:200])" 2>/dev/null || echo "")

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        permission_request --tool "$TOOL_NAME" --message "$DESCRIPTION" 2>/dev/null
} &

# Voice notification (permission requests are important)
{
    curl -s -X POST "http://localhost:8765/speak" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Permission requested for $TOOL_NAME\", \"voice\": \"en-IE-EmilyNeural\"}" \
        --connect-timeout 0.2 --max-time 0.5 >/dev/null 2>&1
} &

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to permissions.log below for activity tracking

# Log permission request
{
    echo "{\"event\":\"permission_request\",\"tool\":\"$TOOL_NAME\",\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/permissions.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "PermissionRequest" "permission_request" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
