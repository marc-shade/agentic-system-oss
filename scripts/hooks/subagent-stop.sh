#!/bin/bash
# SubagentStop Hook - Full AGI Integration
# Records agent completion, captures learnings, updates memory
#
# Integrations: TPU, AGI Bridge (outcome recording), Memory, Activity Dashboard
# Performance target: <200ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract agent info
AGENT_TYPE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('subagent_type', d.get('agent_type', 'unknown')))" 2>/dev/null || echo "unknown")
AGENT_ID=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('agent_id', d.get('id', 'unknown')))" 2>/dev/null || echo "unknown")
RESULT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('result', d.get('output', '')))[:300])" 2>/dev/null || echo "")

# Determine success
SUCCESS="true"
if echo "$RESULT" | grep -qiE "error|failed|exception|timeout"; then
    SUCCESS="false"
fi

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations (records AGI learning)
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        subagent_stop \
        --agent-type "$AGENT_TYPE" \
        --output "$RESULT" \
        $([ "$SUCCESS" = "true" ] && echo "--success") \
        2>/dev/null
} &

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to subagents.log below for activity tracking

# Log subagent completion
{
    echo "{\"event\":\"subagent_stop\",\"agent_type\":\"$AGENT_TYPE\",\"agent_id\":\"$AGENT_ID\",\"success\":$SUCCESS,\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/subagents.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "SubagentStop" "subagent_stop" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
