#!/bin/bash
# SubagentStart Hook - Full AGI Integration
# Tracks agent spawning, scores task importance, recommends routing
#
# Integrations: TPU (importance scoring), AGI Bridge (routing), Activity Dashboard
# Performance target: <150ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract agent info
AGENT_TYPE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('subagent_type', d.get('agent_type', 'unknown')))" 2>/dev/null || echo "unknown")
PROMPT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt', '')[:300])" 2>/dev/null || echo "")
AGENT_ID=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('agent_id', d.get('id', 'unknown')))" 2>/dev/null || echo "unknown")

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        subagent_start --agent-type "$AGENT_TYPE" --prompt "$PROMPT" 2>/dev/null
} &

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to subagents.log below for activity tracking

# Log subagent start
{
    echo "{\"event\":\"subagent_start\",\"agent_type\":\"$AGENT_TYPE\",\"agent_id\":\"$AGENT_ID\",\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/subagents.log
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "SubagentStart" "subagent_start" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
