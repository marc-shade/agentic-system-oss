#!/bin/bash
# PostToolUse Hook - Full AGI Integration
# Records action outcomes, scores importance, updates learning system
#
# Integrations: TPU (importance), AGI Bridge (meta-learning), Activity Dashboard
# Performance target: <200ms

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

# Extract tool info
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" 2>/dev/null || echo "unknown")
TOOL_OUTPUT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('tool_output',{}).get('content',''))[:300])" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); import json as j; print(j.dumps(d.get('tool_input',{}))[:500])" 2>/dev/null || echo "{}")

# Determine success
SUCCESS="true"
if echo "$TOOL_OUTPUT" | grep -qiE "error|failed|not found|exception|denied"; then
    SUCCESS="false"
fi

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations (captures AGI learning)
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        post_tool \
        --tool "$TOOL_NAME" \
        --input "$TOOL_INPUT" \
        --output "$TOOL_OUTPUT" \
        $([ "$SUCCESS" = "true" ] && echo "--success") \
        2>/dev/null
} &
INTEGRATION_PID=$!

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Activity tracking now handled by file logging below and unified_hook_integrations.py
# See: /mnt/agentic-system/docs/ASPIRATIONAL_DOCUMENTATION_AUDIT.md

# Log tool usage (non-blocking)
{
    echo "{\"tool\":\"$TOOL_NAME\",\"success\":$SUCCESS,\"session\":\"$SESSION_ID\",\"node\":\"$(hostname)\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/tool-usage.log
} &

# Update context estimation based on tool usage (non-blocking)
{
    python3 -c "
import json
from pathlib import Path
from datetime import datetime

ctx_file = Path.home() / '.claude' / 'context_status.json'
try:
    if ctx_file.exists():
        data = json.loads(ctx_file.read_text())
        current = data.get('percent', 10)
        # Each tool call adds ~1% context (rough estimate)
        # Capped at 85% - will be reset on compact or session restart
        new_pct = min(current + 1, 85)
        data['percent'] = new_pct
        data['estimated'] = True
        data['updated_at'] = datetime.now().isoformat()
        data['source'] = 'post_tool_use_hook'
        ctx_file.write_text(json.dumps(data))
except Exception:
    pass
" 2>/dev/null
} &

# Wait for integration with timeout
sleep 0.15
kill -0 $INTEGRATION_PID 2>/dev/null && kill $INTEGRATION_PID 2>/dev/null

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "PostToolUse" "post_tool" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
