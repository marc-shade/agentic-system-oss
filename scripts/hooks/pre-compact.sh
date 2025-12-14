#!/bin/bash
# PreCompact Hook - Full AGI Integration
# Saves working memory before context compaction
#
# Integrations: Memory (context preservation), Activity Dashboard
# Performance target: <200ms (important to preserve state)

exec 2>/dev/null  # Suppress stderr

# Source performance helpers
source /home/marc/agentic-system/scripts/hooks/hook_performance.sh 2>/dev/null || true

# Read hook input
INPUT=$(cat)

SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
COMPACT_TYPE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('type', d.get('compact_type', 'auto')))" 2>/dev/null || echo "auto")

# Start time for metrics
START_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)

# Run unified integrations
{
    python3 /home/marc/agentic-system/scripts/hooks/unified_hook_integrations.py \
        pre_compact 2>/dev/null
} &

# NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented
# Events logged to sessions.log below for activity tracking

# Log compact event
{
    echo "{\"event\":\"pre_compact\",\"type\":\"$COMPACT_TYPE\",\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/sessions.log
    # Log to dedicated compaction log for context tracking
    echo "{\"event\":\"pre_compact\",\"type\":\"$COMPACT_TYPE\",\"session\":\"$SESSION_ID\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/compaction-events.log
    # Update context status - compaction indicates ~80%+ usage
    python3 -c "
import json
from pathlib import Path
from datetime import datetime
ctx_file = Path.home() / '.claude' / 'context_status.json'
ctx_file.write_text(json.dumps({
    'percent': 80,
    'estimated': True,
    'source': 'pre_compact_hook',
    'updated_at': datetime.now().isoformat(),
    'note': 'Compaction triggered - context was near limit'
}))
" 2>/dev/null
} &

# Calculate and log performance
END_MS=$(get_timestamp_ms 2>/dev/null || date +%s000)
DURATION_MS=$((END_MS - START_MS))
log_hook_metric "PreCompact" "pre_compact" "$DURATION_MS" "true" "false" "" 2>/dev/null &

exit 0
