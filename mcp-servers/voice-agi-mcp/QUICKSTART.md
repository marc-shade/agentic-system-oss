# Voice-AGI Quickstart Guide

## 🎉 Installation Complete!

All components have been installed and tested successfully. The Voice-AGI MCP server is ready to use.

## 📋 What Was Built

### Core Components ✅
- **ConversationManager** - Stateful dialogue with 10-turn context window
- **VoicePipeline** - Local Whisper STT + Edge TTS
- **ToolRegistry** - Voice-callable tool framework
- **IntentDetector** - Local Ollama NLU for intent classification
- **MCP Integrations** - Enhanced-memory & agent-runtime clients

### Voice-Callable Tools ✅ (10 tools)
1. `search_agi_memory` - Search past memories
2. `create_goal_from_voice` - Create AGI goals
3. `list_pending_tasks` - List active tasks
4. `trigger_consolidation` - Run memory consolidation
5. `start_research` - Begin autonomous research
6. `check_system_status` - System health check
7. `remember_name` / `recall_name` - User context
8. `start_improvement_cycle` - Self-improvement
9. `decompose_goal` - Break goals into tasks

### Features ✅
- Latency tracking (STT, TTS, total)
- Conversation statistics
- User context management
- Intent-based tool routing
- Multi-turn dialogue
- Fallback heuristics (works without Ollama)

## 🚀 Next Steps

### 1. Restart Claude Code

The MCP server is configured but needs Claude Code to restart:

```bash
# Close and reopen Claude Code
# Or if running as a service, restart it
```

### 2. Test Basic Voice Chat

Once restarted, try these commands in Claude Code:

```python
# Test text-based chat (no audio)
voice_chat(text="Hello, how are you?")

# Test with intent detection
voice_chat(text="Create a goal to optimize memory consolidation")

# Check conversation context
get_conversation_context()

# List all voice tools
list_voice_tools()

# Get performance stats
get_voice_stats()
```

### 3. Test Voice Conversation Loop

For full voice interaction (requires microphone):

```python
# Start interactive voice loop
voice_conversation_loop(max_turns=10)

# System will:
# 1. Greet you
# 2. Listen for 5 seconds
# 3. Transcribe your speech
# 4. Detect intent and execute tools
# 5. Speak response
# 6. Repeat until you say "goodbye" or max turns reached
```

### 4. Test Individual Functions

```python
# Just listen (STT only)
voice_listen(duration=5)

# Just speak (TTS only)
voice_speak(text="Testing text-to-speech")

# Remember user info
voice_chat(text="My name is Marc")
# Later...
voice_chat(text="What is my name?")
```

## 📊 System Check

Run the test suite anytime to verify components:

```bash
cd /mnt/agentic-system/mcp-servers/voice-agi-mcp
python3 test_components.py
```

Expected output:
```
✓ Conversation Manager: PASSED
✓ Voice Pipeline: PASSED
✓ Tool Registry: PASSED
✓ Intent Detector: PASSED
```

## 🎤 Voice Pipeline Requirements

### For Speech-to-Text (STT)
```bash
# Already installed:
pip install pywhispercpp

# Required system tools:
sudo dnf install alsa-utils  # For arecord (microphone recording)

# Test microphone:
arecord -D default -f cd -t wav -d 3 /tmp/test.wav
```

### For Text-to-Speech (TTS)
```bash
# Already installed:
pip install edge-tts

# Test TTS:
edge-tts --text "Testing voice" --write-media /tmp/test.mp3
mpg123 /tmp/test.mp3
```

### For Intent Detection
```bash
# Ensure Ollama is running:
systemctl status ollama

# Verify llama3.2 model:
ollama list | grep llama3.2

# If not installed:
ollama pull llama3.2

# Test Ollama:
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test"}'
```

## 🔧 Configuration

MCP server configured in `~/.claude.json`:

```json
{
  "mcpServers": {
    "voice-agi": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/voice-agi-mcp/src/server.py"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2"
      },
      "disabled": false
    }
  }
}
```

## 📖 Usage Examples

### Example 1: Create a Goal via Voice

```python
result = voice_chat(text="Create a goal to make memory consolidation 10x faster")

# Output:
# {
#   'response': '[Tool executed: create_goal_from_voice]',
#   'tool_used': 'create_goal_from_voice',
#   'tool_result': {'goal_id': 'goal_123', 'name': '...'},
#   'conversation_turns': 1
# }
```

### Example 2: Search Memory

```python
result = voice_chat(text="Search for information about transformers")

# Output:
# System searches enhanced-memory and speaks results
# 'response': '[Tool executed: search_agi_memory]'
```

### Example 3: Multi-Turn Conversation

```python
# Turn 1
voice_chat(text="My name is Marc")
# Response: "Got it, I'll remember your name is Marc"

# Turn 2
voice_chat(text="What is my name?")
# Response: "Your name is Marc"

# Context retained across turns!
```

### Example 4: Trigger AGI Operations

```python
# Run memory consolidation
voice_chat(text="Run memory consolidation")
# System: "Starting memory consolidation..."
# [Processing...]
# System: "Consolidation complete. Found 5 patterns."

# Start research
voice_chat(text="Research transformer attention mechanisms")
# System: "Starting research on transformer attention mechanisms..."

# Self-improvement
voice_chat(text="Improve consolidation speed")
# System: "Starting self-improvement cycle for consolidation speed"
```

## 🎯 Available MCP Tools

All tools available in Claude Code:

```python
# Voice interaction
voice_chat(text: str, listen_for_response: bool = False)
voice_listen(duration: int = 5)
voice_speak(text: str, wait_for_completion: bool = True)
voice_conversation_loop(max_turns: int = 10)

# Conversation management
get_conversation_context()
clear_conversation()

# System info
list_voice_tools()
get_voice_stats()
```

## 📈 Performance Expectations

On your Mac Pro 5,1 (Dual Xeon X5680):

| Operation | Expected Latency |
|-----------|------------------|
| STT (base model) | ~800ms |
| TTS (Edge) | ~1500ms |
| Intent detection | ~500ms |
| Total round-trip | ~2.8s |

Tips:
- Use `tiny` Whisper model for faster STT (~400ms)
- Pre-load model on startup for first-use speed
- GPU acceleration coming in Phase 4

## 🐛 Troubleshooting

### MCP Server Not Loading

```bash
# Check Claude Code MCP logs
ls ~/.claude/debug/

# Test server manually
python3 /mnt/agentic-system/mcp-servers/voice-agi-mcp/src/server.py

# Should see:
# "Voice-AGI MCP Server Starting"
# "STT Available: True"
# "TTS Available: True"
```

### No Audio Output

```bash
# Install audio player
sudo dnf install mpg123 ffmpeg

# Test audio system
pactl list sinks
mpg123 /tmp/test.mp3
```

### Whisper Not Working

```bash
# Reinstall pywhispercpp
pip install --upgrade pywhispercpp

# Test:
python3 -c "from pywhispercpp.model import Model; print('OK')"
```

### Intent Detection Fails

The system will use fallback heuristics if Ollama is unavailable. Check:

```bash
# Ollama status
systemctl status ollama

# Test connection
curl http://localhost:11434/api/tags
```

## 🚧 Phase 4: Streaming & VAD (Future)

Not yet implemented (manual implementation required):

- Voice Activity Detection (silero-vad)
- Streaming transcription
- Interrupt handling
- GPU acceleration

To add VAD:
```bash
pip install silero-vad
# See Phase 4 implementation plan in README.md
```

## 📚 Documentation

- **README.md** - Complete system documentation
- **src/server.py** - Main MCP server with all tools
- **src/conversation_manager.py** - Stateful dialogue management
- **src/voice_pipeline.py** - STT/TTS operations
- **src/tool_registry.py** - Tool registration framework
- **src/intent_detector.py** - Intent classification
- **src/mcp_integrations.py** - MCP client interfaces

## 🎓 Learning the System

### Start Simple

1. Test text-based chat first (no audio)
2. Add voice gradually (STT, then TTS)
3. Explore intent detection
4. Add custom tools
5. Integrate with other MCP servers

### Add Custom Tools

```python
# In src/server.py

@tool_registry.register(
    intents=["my", "custom", "keywords"],
    description="What your tool does",
    priority=8
)
async def my_custom_tool(param: str) -> Dict[str, Any]:
    """Your tool implementation"""
    # Do something
    result = process(param)

    # Speak result
    await voice_pipeline.synthesize_speech(
        f"Completed: {result}",
        play_audio=True
    )

    return {'result': result}
```

### Extend Intent Detection

```python
# In src/intent_detector.py

# Add new intent categories to _build_intent_prompt()
# Customize LLM prompts
# Tune confidence thresholds
# Add domain-specific NLU
```

## ✅ Success Criteria

You'll know it's working when:

1. ✅ Component tests pass
2. ✅ MCP server loads in Claude Code
3. ✅ `voice_chat()` tool is available
4. ✅ Text-based chat works with intent detection
5. ✅ Audio synthesis produces speech files
6. ✅ Conversation context retained across turns
7. ✅ Tools invoked based on natural language

## 🎉 You're Ready!

**Restart Claude Code and start using voice_chat()!**

For full documentation, see **README.md**.

For issues, run `python3 test_components.py` to diagnose.

---

**Voice-AGI v0.1.0** - Your AGI system now speaks and listens! 🎤🧠
