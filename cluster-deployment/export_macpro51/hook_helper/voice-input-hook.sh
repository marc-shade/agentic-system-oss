#!/bin/bash
# Voice Input Hook for Claude Code
# Checks for pending voice inputs and outputs them as context
# This hook is called before each prompt submission

VOICE_DIR="${XDG_RUNTIME_DIR:-/tmp}/pixel_voice"
BROADCAST_FILE="$VOICE_DIR/broadcast.json"

# Only check broadcast file (most urgent, recent inputs)
if [[ -f "$BROADCAST_FILE" ]]; then
    # Check if broadcast is recent (within 30 seconds)
    broadcast_time=$(jq -r '.broadcast_at // empty' "$BROADCAST_FILE" 2>/dev/null)

    if [[ -n "$broadcast_time" ]]; then
        # Convert ISO time to epoch
        broadcast_epoch=$(date -d "$broadcast_time" +%s 2>/dev/null)
        now_epoch=$(date +%s)
        age=$((now_epoch - broadcast_epoch))

        if [[ $age -le 30 ]]; then
            text=$(jq -r '.input.text // empty' "$BROADCAST_FILE" 2>/dev/null)
            confidence=$(jq -r '.input.confidence // 0' "$BROADCAST_FILE" 2>/dev/null)

            if [[ -n "$text" ]]; then
                echo ""
                echo "🎤 **VOICE INPUT DETECTED** (${age}s ago)"
                echo "Marc said: \"$text\""
                echo "Confidence: $confidence"
                echo ""
                echo "Please respond to this voice input naturally."
            fi
        fi
    fi
fi
