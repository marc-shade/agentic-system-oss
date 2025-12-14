# STT Listener Troubleshooting Guide

## Problem
Voice Mode not detecting speech: "No speech detected" with `stt: 0.0s` in timing

## Diagnosis

The issue shows:
```
No speech detected | Timing: record 120.3s, stt 0.0s
```

This means:
- ✅ Audio WAS recorded (120.3s)
- ❌ Audio was NOT sent to STT (0.0s processing time)
- ❌ No speech was detected by VAD

## Root Causes (Ranked by Likelihood)

### 1. VAD Too Aggressive (Most Common)
**Symptom**: Records audio but doesn't send to STT
**Fix**: Lower VAD aggressiveness

```bash
# Check current setting
env | grep VOICEMODE_VAD

# Try lower aggressiveness (0 = least strict)
export VOICEMODE_VAD_AGGRESSIVENESS=0

# Restart Claude Code to apply
```

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "voice-mode": {
      "env": {
        "VOICEMODE_VAD_AGGRESSIVENESS": "0"
      }
    }
  }
}
```

### 2. Microphone Input Level Too Low
**Symptom**: Audio recorded but below VAD threshold
**Fix**: Increase microphone gain

1. Open System Preferences → Sound → Input
2. Select your microphone
3. Increase input volume to 75-100%
4. Test with voice memo app first

### 3. Silence Detection Cutting Off Too Early
**Symptom**: Speech starts after silence detection timeout
**Fix**: Increase min_listen_duration

In converse tool call:
```python
mcp__voice-mode__converse(
    "test message",
    min_listen_duration=3.0  # Give more time before silence can stop
)
```

### 4. Wrong Microphone Selected
**Symptom**: Recording from wrong device
**Fix**: Check audio device selection

```bash
# List audio devices (if CLI worked)
voicemode diag devices

# Or check in System Preferences
```

### 5. Microphone Permissions
**Symptom**: No audio captured
**Fix**: Grant microphone permissions

1. System Preferences → Security & Privacy → Privacy
2. Microphone → Enable for Terminal/Claude Code
3. Restart Claude Code

## Quick Test Sequence

### Test 1: Check Whisper Service
```bash
curl http://localhost:2022/health
# Should return: {"status":"ok"}
```

### Test 2: Lower VAD Aggressiveness
Add to voice-mode env in `~/.claude.json`:
```json
"VOICEMODE_VAD_AGGRESSIVENESS": "0"
```

### Test 3: Increase Min Listen Duration
```python
mcp__voice-mode__converse(
    "Can you hear me?",
    min_listen_duration=5.0,  # Allow 5 seconds before silence detection
    disable_silence_detection=False
)
```

### Test 4: Disable Silence Detection Completely
```python
mcp__voice-mode__converse(
    "Testing without silence detection",
    listen_duration=10,
    disable_silence_detection=True  # Must speak within 10 seconds
)
```

## Environment Variables

Add these to `~/.claude.json` under voice-mode env:

```json
{
  "VOICEMODE_VAD_AGGRESSIVENESS": "0",  # 0-3, lower = more permissive
  "VOICEMODE_SKIP_TTS": "false",        # Always use TTS
  "VOICEMODE_AUDIO_FEEDBACK": "true",   # Enable audio feedback
  "VOICEMODE_FEEDBACK_STYLE": "whisper" # Or "shout"
}
```

## Recommended Settings for Reliable Detection

### For Quiet Environments
```json
{
  "VOICEMODE_VAD_AGGRESSIVENESS": "1",  # Slightly strict
  "min_listen_duration": 2.0
}
```

### For Noisy Environments
```json
{
  "VOICEMODE_VAD_AGGRESSIVENESS": "2",  # More strict
  "min_listen_duration": 1.0
}
```

### For Debugging (Most Permissive)
```json
{
  "VOICEMODE_VAD_AGGRESSIVENESS": "0",  # Least strict
  "min_listen_duration": 5.0
}
```

## Logs to Check

Check Voice Mode logs:
```bash
# If voicemode has logs
ls -la ~/.voicemode/logs/

# Check system console for errors
log show --predicate 'process == "voicemode"' --last 5m
```

## Current Status

**Services Running:**
- ✅ Whisper STT: localhost:2022 (2 instances: base + small models)
- ✅ Kokoro TTS: localhost:8880
- ✅ LiveKit RTC: localhost:7880

**Health Check:**
```bash
curl http://localhost:2022/health
# Returns: {"status":"ok"}
```

## Next Steps

1. **Immediate**: Set `VOICEMODE_VAD_AGGRESSIVENESS=0` in voice-mode env
2. **Restart**: Restart Claude Code to apply changes
3. **Test**: Try voice conversation with longer min_listen_duration
4. **Adjust**: If still failing, disable silence detection temporarily
5. **Verify**: Check microphone input level in System Preferences

## Common Gotchas

- **Bluetooth headsets**: Add 1-2 seconds extra leading silence
- **USB microphones**: May need warm-up time, increase min_listen_duration
- **MacBook built-in mic**: Usually works well with VAD=1
- **External mics**: May need VAD=0 or higher input gain

## Configuration Change Template

Update `~/.claude.json`:
```json
{
  "mcpServers": {
    "voice-mode": {
      "command": "/opt/homebrew/bin/voicemode",
      "args": [],
      "env": {
        "VOICEMODE_TOOLS_ENABLED": "converse,voice_registry",
        "VOICEMODE_VAD_AGGRESSIVENESS": "0",
        "VOICEMODE_AUDIO_FEEDBACK": "true"
      }
    }
  }
}
```

**After making changes**: Restart Claude Code for changes to take effect.
