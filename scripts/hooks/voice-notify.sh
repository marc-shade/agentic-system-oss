#!/bin/bash
# Voice Notification Helper
# Speaks messages using Edge TTS with Irish female voice (non-blocking)

TEXT="$1"
VOICE="${2:-en-IE-EmilyNeural}"  # Irish female by default
PLAY="${3:-true}"  # Play audio by default

# Quick validation
if [ -z "$TEXT" ]; then
    exit 0
fi

# Run voice synthesis in background (don't block hook execution)
(
    # Check if edge-tts is available
    if ! command -v edge-tts &>/dev/null; then
        exit 0
    fi

    # Generate audio file
    AUDIO_FILE="/tmp/claude-voice-$(date +%s).mp3"

    edge-tts \
        --voice "$VOICE" \
        --text "$TEXT" \
        --write-media "$AUDIO_FILE" >/dev/null 2>&1

    # Play if requested
    if [ "$PLAY" = "true" ]; then
        # Find available player
        for player in mpg123 ffplay mplayer vlc; do
            if command -v $player &>/dev/null; then
                $player "$AUDIO_FILE" >/dev/null 2>&1 &
                break
            fi
        done
    fi

    # Clean up old voice files (keep last 10)
    ls -t /tmp/claude-voice-*.mp3 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

) &

# Don't wait for background process
exit 0
