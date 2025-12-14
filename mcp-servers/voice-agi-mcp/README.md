# Voice-AGI MCP Server

**Stateful voice-controlled AGI system combining local STT/TTS with Letta-style conversation management**

## Overview

Voice-AGI is an advanced MCP server that provides:
- **Stateful conversations** - Multi-turn dialogue with context retention
- **Tool execution during voice** - Call AGI functions naturally via speech
- **Local STT/TTS** - Cost-effective Whisper + Edge TTS (no API costs)
- **Intent detection** - Sophisticated NLU using local Ollama
- **AGI integration** - Direct control of goals, tasks, memory, and research
- **Latency tracking** - Performance metrics for optimization

## Architecture

```
User Voice → Voice Pipeline (STT) → Intent Detector (Ollama)
                                            ↓
                                     Tool Registry
                                            ↓
                     ┌──────────────────────┼──────────────────────┐
                     ↓                      ↓                      ↓
            Conversation Manager    Enhanced Memory MCP    Agent Runtime MCP
                     │                      │                      │
                     └──────────────────────┴──────────────────────┘
                                            ↓
                                    AGI Orchestrator
```

## Features

### 🎯 Stateful Conversation Management
- **Context retention** across multiple turns (last 10 turns)
- **User context** tracking (name, preferences, etc.)
- **Conversation history** stored in enhanced-memory
- **Seamless multi-turn dialogue** ("What was I just asking about?")

### 🔧 Voice-Callable AGI Tools
- `search_agi_memory` - Search past memories via voice
- `create_goal_from_voice` - "Create a goal to optimize memory"
- `list_pending_tasks` - "What tasks do I have?"
- `trigger_consolidation` - "Run memory consolidation"
- `start_research` - "Research transformer architectures"
- `check_system_status` - "How is the system doing?"
- `remember_name` / `recall_name` - User context management
- `start_improvement_cycle` - "Improve consolidation speed"
- `decompose_goal` - "Break down this goal into tasks"
- **10+ tools total**, easily extensible

### 🧠 Intent Detection
- **Local Ollama LLM** (llama3.2) for sophisticated NLU
- **Intent classification** - Automatically routes to appropriate tools
- **Parameter extraction** - Extracts args from natural speech
- **Context-aware** - Uses conversation history for better understanding
- **Fallback heuristics** - Works even if Ollama unavailable

### 🎤 Voice Pipeline
- **STT**: pywhispercpp (local, Python 3.14 compatible)
- **TTS**: Microsoft Edge TTS (free, neural voices)
- **Audio feedback**: Beeps for state changes
- **Latency tracking**: STT, TTS, and total round-trip metrics
- **Flexible**: Easy to add cloud STT/TTS later

### 📊 Performance Metrics
- **STT latency** tracking (ms)
- **TTS latency** tracking (ms)
- **Total round-trip** latency
- **Conversation statistics** (turns, words, duration)
- **Tool invocation** counts

## Installation

### 1. Install Dependencies

```bash
cd /mnt/agentic-system/mcp-servers/voice-agi-mcp
pip install -r requirements.txt
```

### 2. Ensure Prerequisites

**Required**:
- Python 3.10+
- `edge-tts` (installed via requirements.txt)
- `arecord` (ALSA utils): `sudo dnf install alsa-utils`
- Audio player: `mpg123`, `ffplay`, or `vlc`
- Ollama with llama3.2: `ollama pull llama3.2`

**Optional (for STT)**:
- `pywhispercpp`: Already in requirements.txt
- Microphone access

### 3. Configure in Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "voice-agi": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/voice-agi-mcp/src/server.py"],
      "disabled": false
    }
  }
}
```

### 4. Restart Claude Code

```bash
# Restart Claude Code to load the new MCP server
```

## Usage

### Basic Voice Chat

```python
# From Claude Code, use the voice_chat tool:
result = voice_chat(text="Create a goal to optimize memory consolidation")

# Output:
# {
#   'response': '[Tool executed: create_goal]',
#   'tool_used': 'create_goal_from_voice',
#   'tool_result': {'goal_id': 'goal_123', ...},
#   'conversation_turns': 1
# }
```

### Voice Conversation Loop

```python
# Start interactive voice conversation:
result = voice_conversation_loop(max_turns=10)

# System will:
# 1. Greet you
# 2. Listen for your speech
# 3. Process intent and execute tools
# 4. Respond naturally
# 5. Continue until you say "goodbye" or max_turns reached
```

### Listen Only

```python
# Just transcribe speech:
result = voice_listen(duration=5)
# Returns: {'text': 'transcribed speech', 'success': True}
```

### Speak Only

```python
# Just speak text:
result = voice_speak(text="Hello, this is your AGI assistant")
# Returns: {'success': True, 'audio_file': '/tmp/...'}
```

### Get Conversation Context

```python
# View conversation history:
context = get_conversation_context()
# Returns:
# {
#   'context': 'User: ...\nAssistant: ...',
#   'summary': {'session_id': '...', 'total_turns': 5},
#   'stats': {'total_user_words': 50, ...},
#   'user_context': {'name': 'Marc'}
# }
```

### List Voice Tools

```python
# See all registered voice-callable tools:
tools = list_voice_tools()
# Returns: {'tools': [...], 'count': 10}
```

### Get Performance Stats

```python
# View latency and performance metrics:
stats = get_voice_stats()
# Returns:
# {
#   'latency': {'avg_stt_ms': 800, 'avg_tts_ms': 1500, ...},
#   'stt_available': True,
#   'tts_available': True,
#   'conversation_stats': {...},
#   'registered_tools': 10
# }
```

## Voice-Callable Tools

Tools are automatically invoked when intent is detected in user speech.

### Memory Operations

**Search Memory**:
```
User: "Search for information about transformers"
System: [Searches enhanced-memory and speaks results]
```

**Remember User Info**:
```
User: "My name is Marc"
System: "Got it, I'll remember your name is Marc"
...
User: "What is my name?"
System: "Your name is Marc"
```

### Goal & Task Management

**Create Goal**:
```
User: "Create a goal to optimize memory consolidation"
System: "Goal created with ID goal_1732345678"
```

**List Tasks**:
```
User: "What tasks do I have?"
System: "You have 2 tasks. Task 1: Example task 1, Task 2: ..."
```

**Decompose Goal**:
```
User: "Break down the optimization goal into tasks"
System: "Created 5 tasks from your goal"
```

### AGI Operations

**Memory Consolidation**:
```
User: "Run memory consolidation"
System: "Starting memory consolidation. This may take a moment."
[After processing]
System: "Consolidation complete. Found 5 patterns."
```

**Autonomous Research**:
```
User: "Research transformer attention mechanisms"
System: "Starting research on transformer attention mechanisms. I'll notify you when complete."
```

**Self-Improvement**:
```
User: "Improve consolidation speed"
System: "Starting self-improvement cycle for consolidation speed"
```

**System Status**:
```
User: "How is the system doing?"
System: "System is operational. 12 agents active."
```

## Extending the System

### Adding New Voice-Callable Tools

In `src/server.py`:

```python
@tool_registry.register(
    intents=["your", "trigger", "keywords"],
    description="What your tool does",
    priority=8  # Higher = matched first
)
async def my_custom_tool(param: str) -> Dict[str, Any]:
    """Tool implementation"""
    try:
        # Your logic here
        result = do_something(param)

        # Speak response
        await voice_pipeline.synthesize_speech(
            f"Completed: {result}",
            play_audio=True
        )

        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return {'error': str(e)}
```

### Customizing Intent Detection

Edit `src/intent_detector.py` to:
- Add new intent categories
- Adjust LLM prompts
- Tune confidence thresholds
- Add domain-specific NLU

### Integrating with Other MCP Servers

Edit `src/mcp_integrations.py` to:
- Add new MCP client classes
- Implement actual API calls (currently stubbed)
- Configure MCP server URLs

## Performance

**Measured on Mac Pro 5,1** (Dual Xeon X5680, 24 threads):

| Operation | Latency |
|-----------|---------|
| STT (base model) | ~800ms |
| TTS (Edge) | ~1500ms |
| Intent detection | ~500ms |
| Total round-trip | ~2.8s |

**Tips for Optimization**:
1. Use smaller Whisper model (`tiny`) for faster STT
2. Pre-load Whisper model on startup
3. Use GPU if available (GTX 680 on your system)
4. Enable cloud STT/TTS for latency-critical use cases

## Troubleshooting

### Whisper Not Available

```bash
# Install pywhispercpp
pip install pywhispercpp

# Test:
python3 -c "from pywhispercpp.model import Model; print('✓ Whisper available')"
```

### Edge TTS Not Working

```bash
# Install edge-tts
pip install edge-tts

# Test:
edge-tts --list-voices | grep en-IE
```

### Ollama Not Responding

```bash
# Check Ollama is running
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test"}'

# Pull model if needed
ollama pull llama3.2
```

### Audio Recording Fails

```bash
# Install ALSA utils
sudo dnf install alsa-utils

# Test recording
arecord -D default -f cd -t wav -d 3 /tmp/test.wav

# List audio devices
arecord -l
```

### No Audio Output

```bash
# Install audio player
sudo dnf install mpg123 ffmpeg

# Test playback
mpg123 /tmp/test.mp3
```

## Architecture Details

### Conversation Flow

```
1. User speaks → 2. STT transcribes → 3. Intent detector analyzes
                                              ↓
                                    4. Tool registry matches
                                              ↓
                                    5. Tool executes
                                              ↓
                                    6. Result spoken via TTS
                                              ↓
                                    7. Turn stored in conversation
```

### Stateful Context

Conversation manager maintains:
- **Message history** (last 10 turns)
- **User context** (name, preferences)
- **Session metadata** (start time, turn count)
- **Tool invocations** (which tools were used)

Context is automatically:
- Passed to intent detector for better NLU
- Stored in enhanced-memory for long-term retention
- Used for multi-turn understanding

### Tool Invocation

Tools are invoked when:
1. Intent confidence > 0.6
2. Intent name matches registered tool
3. Required parameters can be extracted

Parameters extracted via:
- **LLM-based extraction** (Ollama)
- **Pattern matching** (regex)
- **Conversation context** (previous turns)
- **Defaults** (if specified in tool definition)

## Comparison to Letta Voice

| Feature | Letta Voice | Voice-AGI (This) |
|---------|-------------|------------------|
| **STT** | Deepgram (cloud) | Whisper (local) |
| **TTS** | Cartesia (cloud) | Edge TTS (local) |
| **Memory** | Letta stateful framework | Enhanced-memory MCP |
| **Tools** | Function calling | Voice-callable tools |
| **Cost** | ~$620/mo (8hr/day) | ~$5/mo (local compute) |
| **Latency** | ~700ms | ~2.8s (local CPU) |
| **Privacy** | ❌ Cloud data | ✅ Fully local |
| **AGI Integration** | ❌ None | ✅ Deep integration |

**Best of Both Worlds**: This system combines Letta's stateful conversation approach with your existing local infrastructure.

## Future Enhancements

### Phase 4: Streaming & VAD (Planned)
- Voice Activity Detection (silero-vad)
- Streaming transcription (continuous buffer)
- Interrupt handling
- GPU acceleration for Whisper

### Phase 5: Cloud Upgrade (Optional)
- Adaptive pipeline (local vs cloud based on context)
- Deepgram STT integration
- Cartesia TTS integration
- Livekit for real-time streaming

## Configuration

### Environment Variables

```bash
# Ollama configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Voice configuration
WHISPER_MODEL=base  # tiny, base, small, medium, large
TTS_VOICE=en-IE-EmilyNeural
TTS_RATE=+0%
TTS_VOLUME=+0%

# MCP server URLs (for integrations)
ENHANCED_MEMORY_URL=http://localhost:3000
AGENT_RUNTIME_URL=http://localhost:3001
AGI_ORCHESTRATOR_URL=http://localhost:8000
```

### Conversation Settings

In `src/server.py`:

```python
conversation_manager = ConversationManager(
    max_turns=10,  # Conversation history window
    enable_memory=True  # Store in enhanced-memory
)
```

### Voice Pipeline Settings

```python
voice_pipeline = VoicePipeline(
    stt_model="base",  # Whisper model size
    tts_voice="en-IE-EmilyNeural",  # TTS voice
    enable_latency_tracking=True  # Track metrics
)
```

## API Reference

See inline docstrings in:
- `src/server.py` - Main MCP tools
- `src/conversation_manager.py` - Conversation management
- `src/voice_pipeline.py` - STT/TTS operations
- `src/tool_registry.py` - Tool registration
- `src/intent_detector.py` - Intent detection
- `src/mcp_integrations.py` - MCP client interfaces

## Contributing

To add new features:

1. **New voice-callable tools**: Add to `src/server.py` with `@tool_registry.register()`
2. **Enhanced intent detection**: Update `src/intent_detector.py`
3. **MCP integrations**: Implement actual calls in `src/mcp_integrations.py`
4. **Performance optimizations**: Add VAD, streaming, GPU acceleration
5. **Cloud providers**: Add Deepgram/Cartesia clients

## License

Part of the Mac Pro 5,1 Agentic System - see main system documentation.

## Support

For issues or questions:
- Check logs: `journalctl -f | grep voice-agi`
- Test components individually (see Troubleshooting)
- Review AGI system documentation in `/home/marc/`

---

**Voice-AGI v0.1.0** - Stateful voice control for recursive self-improving AGI systems
