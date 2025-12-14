#!/bin/bash
# UserPromptSubmit Hook - Full AGI Integration
# Classifies user intent, recalls relevant context, updates activity
#
# Integrations: TPU (intent classification), Memory (context recall), Activity
# Performance target: <150ms (user is waiting)

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract prompt (limited to 500 chars for speed)
USER_PROMPT=$(echo "$INPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
prompt = d.get('prompt', d.get('message', ''))[:500]
print(prompt.replace('\"', '\\\\\"').replace('\n', ' '))
" 2>/dev/null || echo "")

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations (with strict timeout for responsiveness)
if [ -n "$USER_PROMPT" ]; then
    {
        timeout 0.15s python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
            user_prompt --prompt "$USER_PROMPT" 2>/dev/null
    } &
fi

# Quick log (non-blocking)
{
    # Only log if prompt has meaningful content
    if [ ${#USER_PROMPT} -gt 10 ]; then
        echo "{\"event\":\"user_prompt\",\"length\":${#USER_PROMPT},\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/prompts.log
    fi
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "UserPromptSubmit" "user_prompt" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
