#!/bin/bash
# User Prompt Submit Hook - Check for voice transcriptions
# This hook runs whenever the user submits a prompt

# Check if voice mode is active by looking for new transcriptions
VOICE_CHECK=$(python3 -c "
import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/voice-mode')
try:
    from server import stt_state
    transcriptions = stt_state.get_recent_transcriptions(limit=1)
    if transcriptions and transcriptions[0].get('text') != '[BLANK_AUDIO]':
        print('VOICE_DETECTED')
except:
    pass
" 2>/dev/null)

# If voice was detected, prepend a reminder to check transcriptions
if [ "$VOICE_CHECK" = "VOICE_DETECTED" ]; then
    echo "[Voice Input Detected] Remember to check recent transcriptions using /show-transcripts or the get_transcriptions tool."
fi

exit 0
