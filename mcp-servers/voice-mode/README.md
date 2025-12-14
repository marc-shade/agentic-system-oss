# Voice Mode MCP Server - Bidirectional Voice with Caps Lock Control

Text-to-Speech (TTS) and Speech-to-Text (STT) for Claude Code with **Caps Lock toggle control**.

## Status

✅ **TTS OPERATIONAL** - Edge TTS working on Linux
✅ **BEEP TOGGLE OPERATIONAL** - Use MCP tool or shell command with beep feedback
✅ **WAYLAND COMPATIBLE** - Works on Wayland using MCP tool (no keyboard listener needed)
⚠️ **STT TRANSCRIPTION PENDING** - Whisper requires Python ≤3.13 (onnxruntime limitation)

## Quick Start - Wayland Solution

**Wayland blocks keyboard listeners**, so we use two simple methods:

### Method 1: MCP Tool (In Claude Code)
Use the `toggle_stt()` tool from Claude Code chat - it plays beeps automatically!

### Method 2: Shell Command (Terminal)
```bash
toggle-voice  # Toggles voice mode with beeps
```

**Beep Feedback:**
- 🎵 **ON**: Higher pitch beep (1000Hz, 150ms)
- 🎵 **OFF**: Lower pitch beep (600Hz, 150ms)

**What requires Whisper:**
- Actual speech-to-text transcription (requires `pywhispercpp` or GPU STT endpoint)

## Overview

Provides bidirectional voice capabilities via MCP protocol:
- **TTS**: Microsoft Edge TTS (no API keys required)
- **STT**: Whisper transcription with continuous listening
- **Caps Lock Toggle**: Press Caps Lock to turn STT on/off
- **Transcription History**: Automatic storage of last 50 transcriptions

## Features

### Text-to-Speech (Operational)
- Convert text to natural-sounding speech
- Multiple Microsoft Edge neural voices
- Adjustable rate and volume
- Audio playback on Linux (mpg123/ffplay)

### Speech-to-Text (Requires Whisper Installation)
- Continuous listening mode
- Caps Lock keyboard toggle
- **Musical beep feedback** (ascending/descending tones)
- Voice announcements for mode changes
- Automatic transcription of 3-second chunks
- Transcription history with timestamps
- Multiple Whisper model sizes (tiny to large)

## Configuration

**MCP Server**: Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "voice-mode": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/voice-mode/server.py"],
      "disabled": false
    }
  }
}
```

## Installation

### Core Dependencies (Required for TTS)

```bash
cd /mnt/agentic-system/mcp-servers/voice-mode
pip3 install -r requirements.txt
```

### STT Dependencies

**✅ Python 3.14 Compatible**: Server uses `pywhispercpp` (C++ Whisper bindings) which works with Python 3.14.

```bash
pip install pywhispercpp
```

**Alternative: GPU STT Service**
The server also supports remote GPU inference via HTTP for faster transcription:
- Set `GPU_STT_ENDPOINT` environment variable to your Whisper API endpoint
- Set `GPU_STT_ENABLED=true` to prefer GPU over local CPU

**Note**: TTS (Edge TTS) works **immediately** without any Whisper installation. STT requires either pywhispercpp or a GPU STT endpoint.

## Available Tools

### Text-to-Speech

#### `speak`
Speak text using Edge TTS

**Parameters**:
- `text` (required): Text to speak
- `voice` (optional): Voice name (default: en-IE-EmilyNeural 🇮🇪)
- `rate` (optional): Speech rate (e.g., "+10%", "-20%")
- `volume` (optional): Volume (e.g., "+10%", "-20%")
- `play_audio` (optional): Play audio (default: true)

**Example**:
```python
result = await speak("Hello from voice mode!", voice="en-US-AriaNeural")
```

#### `list_voices`
List available TTS voices

**Parameters**:
- `language` (optional): Language filter (default: "en-US")

**Example**:
```python
voices = await list_voices(language="en-IE")
```

### Speech-to-Text (Requires Whisper)

#### `listen`
One-shot recording and transcription

**Parameters**:
- `duration` (optional): Recording duration in seconds (default: 5)
- `language` (optional): Language code (default: "en")
- `model` (optional): Whisper model size (default: "base")

**Example**:
```python
result = await listen(duration=5, model="base")
print(result["text"])
```

#### `start_voice_mode`
Start continuous voice mode with Caps Lock toggle

**Parameters**:
- `model` (optional): Whisper model size (default: "base")
- `chunk_duration` (optional): Chunk duration in seconds (default: 3)

**Example**:
```python
result = await start_voice_mode(model="base", chunk_duration=3)
# Now press Caps Lock to toggle STT on/off
```

**Note**: The keyboard listener starts automatically on server launch. Call `start_voice_mode()` to enable continuous listening and transcription.

#### `stop_voice_mode`
Stop continuous voice mode

**Example**:
```python
result = await stop_voice_mode()
```

#### `toggle_stt`
Toggle STT on/off programmatically

**Parameters**:
- `enable` (optional): True=on, False=off, None=toggle

**Example**:
```python
result = await toggle_stt(enable=True)
```

#### `get_voice_mode_status`
Get current voice mode status

**Example**:
```python
status = await get_voice_mode_status()
print(status["stt_active"])          # Is STT on?
print(status["whisper_available"])   # Is Whisper installed?
```

#### `get_transcriptions`
Get recent transcriptions

**Parameters**:
- `limit` (optional): Number of transcriptions (default: 10)

**Example**:
```python
transcriptions = await get_transcriptions(limit=10)
for t in transcriptions["transcriptions"]:
    print(f"{t['timestamp']}: {t['text']}")
```

## Caps Lock Toggle Control

The keyboard listener starts automatically when the MCP server launches:

1. **Keyboard listener** is always active, monitoring Caps Lock key
2. **Call `start_voice_mode()`** to enable the continuous listening loop (if Whisper is installed)
3. **Press Caps Lock** to toggle STT on/off
4. **Audio feedback**:
   - **Beep sound**: Immediate audio cue (ascending tone for ON, descending for OFF)
   - **Voice announcement**: Speaks "Voice mode ON" or "Voice mode OFF"
5. **When STT is ON**: Continuously records 3-second chunks and transcribes
6. **Transcriptions**: Automatically logged and stored in history

**Audio Feedback Details**:
- **ON beep**: Higher pitch tone (800Hz, 150ms) - sounds like activation
- **OFF beep**: Lower pitch tone (400Hz, 150ms) - sounds like deactivation
- **Beep tools** (in order of preference): ffplay, paplay, beep command
- **Voice feedback**: Follows immediately after beep

**IMPORTANT**: After fixing beep code, **restart Claude Code** for changes to take effect!

**Note**: The physical Caps Lock LED state is independent - this monitors the key press event, not the lock state.

## Popular Voices

### English (Ireland)
- `en-IE-EmilyNeural` - Irish female (default) 🇮🇪
- `en-IE-ConnorNeural` - Irish male 🇮🇪

### English (US)
- `en-US-AriaNeural` - Natural female voice
- `en-US-GuyNeural` - Natural male voice
- `en-US-JennyNeural` - Professional female voice

### English (GB)
- `en-GB-SoniaNeural` - British female 🇬🇧
- `en-GB-RyanNeural` - British male 🇬🇧

### Other Languages
- `en-AU-NatashaNeural` - Australian female 🇦🇺
- `es-ES-AlvaroNeural` - Spanish male 🇪🇸
- `fr-FR-DeniseNeural` - French female 🇫🇷
- `de-DE-KatjaNeural` - German female 🇩🇪

## Whisper Models

| Model | Size | Accuracy | Speed |
|-------|------|----------|-------|
| tiny | ~140MB | Good | Fastest |
| base | ~140MB | Better | Fast (default) |
| small | ~460MB | High | Medium |
| medium | ~1.5GB | Very High | Slow |
| large | ~2.9GB | Best | Slowest |

Models are cached in `~/.cache/huggingface/`

## Architecture

```
┌──────────────────────────────────────────────┐
│  Keyboard Listener (pynput)                  │
│  - Monitors Caps Lock key press              │
│  - Toggles STT state                         │
│  - Triggers audio feedback (beep + voice)    │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│  Audio Feedback System                       │
│  - play_beep(): Musical tones (ON/OFF)       │
│  - speak(): Voice announcements (TTS)        │
│  - Async execution via event loop            │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  STT State Manager (Thread-Safe)             │
│  - Active/Inactive flag                      │
│  - Transcription history (FIFO, last 50)     │
│  - Whisper model cache                       │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│  Continuous Listening Loop (Async)           │
│  - Records 3s audio chunks (arecord)         │
│  - Transcribes with Faster Whisper           │
│  - Stores with timestamp                     │
│  - Sleeps when STT inactive                  │
└──────────────────────────────────────────────┘
```

## Testing

### Test TTS (No Whisper Required)

```bash
# Command line
edge-tts --text "Hello from voice mode" --write-media /tmp/test.mp3
mpg123 /tmp/test.mp3

# Via MCP (after restarting Claude Code)
# Use the speak tool in Claude Code
```

### Test Beep Sounds

```bash
# Test ON beep (higher pitch - activation)
ffplay -nodisp -autoexit -t 0.15 -f lavfi -i "sine=frequency=800:duration=0.15"

# Test OFF beep (lower pitch - deactivation)
ffplay -nodisp -autoexit -t 0.15 -f lavfi -i "sine=frequency=400:duration=0.15"

# Test both sequentially
echo "🔊 Testing ON beep (800Hz):" && \
ffplay -nodisp -autoexit -t 0.15 -f lavfi -i "sine=frequency=800:duration=0.15" 2>/dev/null && \
sleep 0.5 && \
echo "🔊 Testing OFF beep (400Hz):" && \
ffplay -nodisp -autoexit -t 0.15 -f lavfi -i "sine=frequency=400:duration=0.15" 2>/dev/null && \
echo "✅ Beeps work!"
```

### Test STT (Requires Whisper)

```bash
# Check if Whisper is available
python3 -c "from faster_whisper import WhisperModel; print('✓ Whisper available')"

# Test recording
arecord -D default -f cd -t wav -d 3 /tmp/test.wav

# Via MCP (after restarting Claude Code)
# Use the listen tool in Claude Code
```

## Requirements

### Core (TTS)
- Python 3.8+
- fastmcp
- edge-tts
- pynput (keyboard listener)
- Linux audio playback: mpg123, ffplay, mplayer, or vlc

### Optional (STT)
- faster-whisper (Python ≤3.13)
- arecord (ALSA utils) - Linux audio recording
- Microphone access

## Troubleshooting

### TTS Issues

**Voice MCP not loading**:
```bash
# Check configuration
cat ~/.claude.json | jq '.mcpServers["voice-mode"]'

# Test server directly
python3 /mnt/agentic-system/mcp-servers/voice-mode/server.py
```

**No audio output (TTS or beeps)**:
```bash
# Install audio player and ffmpeg (for beeps)
sudo dnf install mpg123 ffmpeg

# Check audio device
pactl list sinks

# Test audio output
ffplay -nodisp -autoexit -t 0.5 -f lavfi -i "sine=frequency=440:duration=0.5"

# Or disable playback (just generate files)
# Set play_audio: false
```

**Beeps not playing**:
```bash
# Check if ffplay is available
which ffplay

# Install ffmpeg if missing
sudo dnf install ffmpeg

# Test beep manually
ffplay -nodisp -autoexit -t 0.2 -f lavfi -i "sine=frequency=523:duration=0.1,sine=frequency=659:duration=0.1"
```

### STT Issues

**Whisper not working**:
- Install pywhispercpp: `pip install pywhispercpp`
- Or use GPU STT endpoint (set `GPU_STT_ENDPOINT` and `GPU_STT_ENABLED=true`)

**Recording fails**:
```bash
# Install ALSA utilities
sudo dnf install alsa-utils

# List audio devices
arecord -l

# Test recording
arecord -D default -f cd -t wav -d 3 /tmp/test.wav
```

**Caps Lock not working**:
```bash
# 1. Check if pynput is installed
python3 -c "import pynput; print('✓ pynput installed')"

# 2. Check keyboard permissions
ls -l /dev/input/event* | head -5

# 3. Add user to input group (if needed)
sudo usermod -aG input $USER
# Logout and login for group change to take effect

# 4. Test keyboard listener manually
python3 << 'EOF'
from pynput import keyboard

def on_press(key):
    print(f"Key pressed: {key}")
    if key == keyboard.Key.caps_lock:
        print("✓ Caps Lock detected!")

listener = keyboard.Listener(on_press=on_press)
listener.start()
print("Press Caps Lock (Ctrl+C to exit)...")
import time
time.sleep(10)
EOF

# 5. Restart Claude Code after fixing permissions
```

**High CPU usage during STT**:
- Use smaller Whisper model: `start_voice_mode(model="tiny")`
- Increase chunk duration: `start_voice_mode(chunk_duration=5)`

**Transcription quality issues**:
- Use larger model: `start_voice_mode(model="small")`
- Reduce background noise
- Speak closer to microphone

## Performance

- **TTS latency**: ~1-2 seconds
- **STT transcription**: ~0.5-2 seconds (model dependent)
- **Memory usage**:
  - Base: ~500MB
  - Large model: ~2GB
- **Disk usage**: Models cached in `~/.cache/huggingface/`
- **Keyboard listener**: <1MB memory, negligible CPU

## Usage in Claude Code

After restarting Claude Code, all voice tools will be available via MCP.

**Workflow**:
1. Server auto-starts keyboard listener (Caps Lock monitoring active)
2. Call `start_voice_mode()` to enable continuous listening (if using STT)
3. Press Caps Lock to toggle STT on/off (hear beep + voice confirmation)
4. Speak naturally when STT is ON - transcriptions appear in logs and history
5. Press Caps Lock again to deactivate STT
6. Use `get_transcriptions()` to retrieve recent transcriptions

**Note**: Restart Claude Code after configuration changes!

## Platform Differences

### Linux (Current System)
- TTS: Edge TTS (Microsoft)
- STT: Faster Whisper
- Audio: mpg123, arecord
- Free, no API keys

### macOS
- TTS: `say` command (built-in) or Edge TTS
- STT: Whisper
- Audio: Built-in CoreAudio
- Arduino hardware integration available

## References

- Edge TTS: https://github.com/rany2/edge-tts
- Faster Whisper: https://github.com/SYSTRAN/faster-whisper
- Microsoft TTS Voices: https://speech.microsoft.com/portal/voicegallery
- pynput: https://pynput.readthedocs.io/
