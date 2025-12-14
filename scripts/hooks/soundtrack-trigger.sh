#!/bin/bash
# Soundtrack Trigger - Sends events to the Agentic Drum Machine
# Usage: soundtrack-trigger.sh <action_type>
#
# Actions map to sounds defined in ACTION_SOUND_MAP in agentic_drum_machine.py

DRUM_API="http://127.0.0.1:8766"
ACTION="${1:-tool_call}"

# Fire and forget - don't block Claude Code
curl -s -X POST "$DRUM_API/action" \
    -H "Content-Type: application/json" \
    -d "{\"action\": \"$ACTION\"}" \
    --max-time 1 \
    > /dev/null 2>&1 &

exit 0
