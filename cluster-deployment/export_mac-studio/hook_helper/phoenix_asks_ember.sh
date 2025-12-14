#!/bin/bash
# Phoenix asks Ember for quick advice using MCP
# Usage: phoenix_asks_ember.sh "question"

QUESTION="$1"

if [ -z "$QUESTION" ]; then
    echo "Usage: phoenix_asks_ember.sh \"your question\""
    exit 1
fi

# This would be called via MCP ember_chat tool
# For now, log the consultation
echo "[$(date)] Phoenix asks Ember: $QUESTION" >> ~/.claude/phoenix_ember_consultations.log

# Return placeholder - in real usage, Phoenix would call ember_chat MCP tool
echo "🔥 Ember: Consulting on this..."
