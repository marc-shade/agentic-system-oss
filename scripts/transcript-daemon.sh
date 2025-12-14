#!/bin/bash
# Transcript Daemon - Continuously monitors and displays transcriptions
# Runs in background and outputs to log visible in Claude Code

TRANSCRIPT_FILE="/tmp/conversation_transcript.json"
LOG_FILE="$HOME/agentic-system/logs/transcript-monitor.log"
POLL_INTERVAL=1  # seconds

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Track last seen count
LAST_COUNT=0

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🎙️  Transcript Monitor Started" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring: $TRANSCRIPT_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

while true; do
    if [ -f "$TRANSCRIPT_FILE" ]; then
        CURRENT_COUNT=$(jq 'length' "$TRANSCRIPT_FILE" 2>/dev/null || echo "0")

        if [ "$CURRENT_COUNT" -gt "$LAST_COUNT" ]; then
            NEW_COUNT=$((CURRENT_COUNT - LAST_COUNT))

            # Display each new transcription
            for i in $(seq 1 $NEW_COUNT); do
                INDEX=$((CURRENT_COUNT - NEW_COUNT + i - 1))

                UTTERANCE=$(jq -r ".[$INDEX].utterance" "$TRANSCRIPT_FILE" 2>/dev/null)
                TIMESTAMP=$(jq -r ".[$INDEX].timestamp" "$TRANSCRIPT_FILE" 2>/dev/null)
                CONFIDENCE=$(jq -r ".[$INDEX].confidence" "$TRANSCRIPT_FILE" 2>/dev/null)

                TIME_ONLY=$(echo "$TIMESTAMP" | cut -d'T' -f2 | cut -d'.' -f1)
                CONF_PERCENT=$(echo "$CONFIDENCE * 100" | bc | cut -d'.' -f1)

                {
                    echo ""
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo "🎤 SPEECH DETECTED"
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo ""
                    echo "  ┌────────────────────────────────────────────────────────────────────┐"
                    printf "  │ 🗣️  %-66s │\n" "$UTTERANCE"
                    echo "  │                                                                    │"
                    printf "  │ ⏱️  Time: %-60s │\n" "$TIME_ONLY"
                    printf "  │ 📊 Confidence: %-55s │\n" "$CONF_PERCENT%"
                    echo "  └────────────────────────────────────────────────────────────────────┘"
                    echo ""
                    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo ""
                } | tee -a "$LOG_FILE"
            done

            LAST_COUNT=$CURRENT_COUNT
        fi
    fi

    sleep $POLL_INTERVAL
done
