#!/bin/bash
# Transcript Monitor for Claude Code
# Monitors /tmp/conversation_transcript.json and displays new transcriptions

TRANSCRIPT_FILE="/tmp/conversation_transcript.json"
LAST_COUNT_FILE="/tmp/.transcript_monitor_last_count"

# Initialize counter
if [ ! -f "$LAST_COUNT_FILE" ]; then
    echo "0" > "$LAST_COUNT_FILE"
fi

LAST_COUNT=$(cat "$LAST_COUNT_FILE")

# Check if transcript file exists
if [ ! -f "$TRANSCRIPT_FILE" ]; then
    exit 0
fi

# Get current count
CURRENT_COUNT=$(jq 'length' "$TRANSCRIPT_FILE" 2>/dev/null || echo "0")

# If there are new transcriptions
if [ "$CURRENT_COUNT" -gt "$LAST_COUNT" ]; then
    # Calculate how many new ones
    NEW_COUNT=$((CURRENT_COUNT - LAST_COUNT))

    echo ""
    echo "🎙️  NEW TRANSCRIPTION(S) ($NEW_COUNT):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Show the new transcriptions with speech bubble format
    jq -r ".[-$NEW_COUNT:] | .[] | \"  ┌─────────────────────────────────────────────────────────────────┐\n  │ 🗣️  \\(.utterance)\\n  │ ⏱️  \\(.timestamp | split(\\\"T\\\")[1] | split(\\\".\\\")[0])\n  │ 📊 Confidence: \\(.confidence * 100 | floor)%\n  └─────────────────────────────────────────────────────────────────┘\n\"" "$TRANSCRIPT_FILE" 2>/dev/null

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Update counter
    echo "$CURRENT_COUNT" > "$LAST_COUNT_FILE"
fi
