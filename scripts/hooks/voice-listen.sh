#!/bin/bash
# Voice Listen Helper - Record and transcribe audio (placeholder)
# Full STT requires Whisper installation

DURATION="${1:-5}"
AUDIO_FILE="/tmp/claude-recording-$(date +%s).wav"

# Check if arecord is available
if ! command -v arecord &>/dev/null; then
    echo "Error: arecord not available for audio recording"
    exit 1
fi

# Record audio
echo "🎤 Listening for ${DURATION} seconds..."
arecord -D default -f cd -t wav -d "$DURATION" "$AUDIO_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Audio recorded: $AUDIO_FILE"
    echo "Note: Transcription requires Whisper (pip install openai-whisper)"
else
    echo "❌ Recording failed"
    exit 1
fi
