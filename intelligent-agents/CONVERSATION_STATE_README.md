# Conversation State Management System

Comprehensive multi-turn conversation tracking with context preservation and persistence for voice-based AGI interactions.

## Overview

The Conversation State Management System provides:

- **Full Conversation History**: Track all user-assistant exchanges with metadata
- **Task Context Management**: Maintain active task state across turns
- **File Context Tracking**: Monitor files being discussed/modified
- **Action Tracking**: Record pending and completed actions with status
- **Clarification Management**: Track questions needing user input
- **Context Summaries**: Generate summaries for LLM prompts
- **Session Persistence**: Store state to enhanced-memory MCP for continuity

## Architecture

### Core Components

1. **ConversationState** (`conversation_state.py`)
   - Main state management class
   - Tracks conversation turns, tasks, files, actions
   - Provides serialization and persistence

2. **EnhancedConversationManager** (`conversation_manager_enhanced.py`)
   - Integration with existing conversation manager
   - Adds state tracking to conversation processing
   - Example of real-world usage

3. **Data Classes**:
   - `ConversationTurn`: Single conversation exchange
   - `ActionRecord`: Tracked action with status
   - `TurnType`: Conversation turn classification
   - `ActionStatus`: Action lifecycle status

### Memory Integration

State is persisted to enhanced-memory MCP using 4-tier architecture:

- **Episodic Memory**: Individual conversation turns (time-bound)
- **Working Memory**: Active task context (TTL-based, 2 hours)
- **Semantic Memory**: Extracted concepts and patterns (automatic)
- **Procedural Memory**: Common interaction patterns (learned)

## Usage

### Basic Usage

```python
from conversation_state import ConversationState, TurnType, ActionRecord, ActionStatus

# Create conversation state
state = ConversationState()

# Add a conversation turn
turn = state.add_turn(
    user_msg="Can you help me build a REST API?",
    assistant_msg="I'll help you create a REST API. Let's start by checking your project structure.",
    turn_type=TurnType.QUESTION,
    confidence=0.95
)

# Track an action
action = ActionRecord(
    action_id="check_project",
    action_type="file_read",
    description="Reading project structure",
    status=ActionStatus.COMPLETED,
    result="Found Flask project"
)
state.add_action(action)
state.update_action("check_project", ActionStatus.COMPLETED)

# Get context summary for LLM
context = state.get_context_summary(max_turns=5)
print(context)
```

### Task Management

```python
# Start a task
state.update_active_task("Build REST API", "Create user authentication endpoint")

# Add turns related to task
state.add_turn(
    user_msg="Should we use JWT tokens?",
    assistant_msg="Yes, JWT is a good choice. I'll add JWT support.",
    turn_type=TurnType.QUESTION,
    files=["/project/auth.py"]
)

# Complete task
summary = state.complete_task()
print(f"Task completed in {summary['duration_minutes']:.1f} minutes")
```

### File Context

```python
# Add files to context
state.add_file_context("/project/app.py")
state.add_file_context("/project/models.py")

# Files are automatically tracked in turns
turn = state.add_turn(
    user_msg="Modify the database schema",
    assistant_msg="I'll update models.py with the new schema",
    files=["/project/models.py"]
)

# Clear context when switching tasks
state.clear_file_context()
```

### Clarifications

```python
# Add a clarification question
state.add_clarification("Which Python version should I use?")

# Resolve when user answers
state.resolve_clarification(
    "Which Python version should I use?",
    "Python 3.9"
)
```

### Persistence

```python
# Persist state to enhanced-memory MCP
await state.persist()

# Restore state in new session
new_state = ConversationState()
await new_state.restore("conv_20251117_113117")
```

### Statistics

```python
stats = state.get_statistics()
print(f"Total turns: {stats['total_turns']}")
print(f"Average confidence: {stats['average_confidence']:.2f}")
print(f"Turn distribution: {stats['turn_type_distribution']}")
```

## Integration with Conversation Manager

The `EnhancedConversationManager` shows how to integrate state management with conversation processing:

```python
from conversation_manager_enhanced import EnhancedConversationManager

# Create manager with state tracking
manager = EnhancedConversationManager()

# Process transcripts with full state tracking
transcript = {
    "utterance": "Can you help me build a REST API?",
    "timestamp": "2025-11-17T11:30:00"
}
await manager.process_utterance(transcript)

# State is automatically tracked and persisted
manager.print_status()
```

## Data Classes

### ConversationTurn

Represents a single conversation exchange:

```python
@dataclass
class ConversationTurn:
    turn_id: int                          # Sequential turn number
    timestamp: datetime                   # When turn occurred
    user_utterance: str                   # What user said
    assistant_response: str               # Assistant's response
    turn_type: TurnType                   # Type of turn
    actions_taken: List[ActionRecord]     # Actions during this turn
    files_touched: List[str]              # Files mentioned/modified
    confidence: float                     # Response confidence (0.0-1.0)
    context_used: Dict[str, Any]          # Context available during turn
```

### ActionRecord

Tracks an action through its lifecycle:

```python
@dataclass
class ActionRecord:
    action_id: str                        # Unique action ID
    action_type: str                      # Type: file_read, search, execute, create
    description: str                      # Human-readable description
    status: ActionStatus                  # Current status
    result: Optional[str]                 # Result if completed
    error: Optional[str]                  # Error if failed
    timestamp: datetime                   # When action was created
    duration_ms: Optional[int]            # How long it took
```

### TurnType Enum

Classification of conversation turns:

- `GREETING`: Initial greeting or hello
- `QUESTION`: User asking for information
- `COMMAND`: User requesting an action
- `CLARIFICATION`: Follow-up question
- `CONFIRMATION`: Yes/no response
- `ERROR`: Error occurred
- `INFO_RESPONSE`: Information provided

### ActionStatus Enum

Action lifecycle states:

- `PENDING`: Action queued, not started
- `IN_PROGRESS`: Action currently executing
- `COMPLETED`: Action finished successfully
- `FAILED`: Action failed with error
- `BLOCKED`: Action blocked by dependency

## Context Summary Format

The `get_context_summary()` method generates a formatted summary:

```
=== Conversation Context ===
Session: conv_20251117_113117
Duration: 15.3 minutes
Total turns: 12

Active Task: Build REST API
Description: Create user authentication endpoint
Duration: 10.2 minutes

Recent Conversation:
  [10] User: Should we use JWT tokens?
       Assistant: Yes, JWT is a good choice. I'll add JWT support.
       Action: Reading auth documentation [completed]
  [11] User: Add the JWT dependency
       Assistant: I'll add PyJWT to requirements.txt
       Action: Updating requirements.txt [in_progress]

Files in Context (3):
  - /project/app.py (modified 2.5m ago)
  - /project/auth.py (modified 1.2m ago)
  - /project/requirements.txt (modified 0.3m ago)

Pending Actions (1):
  - Updating requirements.txt [in_progress]

Clarifications Needed (1):
  - Which JWT algorithm should we use?
```

This summary can be included in LLM prompts to provide conversation context.

## Persistence Strategy

### What Gets Persisted

1. **Session Metadata** (Entity):
   - Session ID, start time, statistics
   - Stored as entity in enhanced-memory

2. **Conversation Turns** (Episodic Memory):
   - Last 10 turns stored as episodes
   - Tagged with session ID
   - Significance based on confidence and actions

3. **Active Task** (Working Memory):
   - Current task with context
   - TTL of 2 hours
   - Includes pending actions and files

### Persistence Timing

- Automatic: Every 5 turns
- Manual: Call `await state.persist()`
- On exit: Final persist before shutdown

### Restoration

```python
# Restore previous session
state = ConversationState()
success = await state.restore("conv_20251117_113117")

if success:
    print(f"Restored {len(state.history)} turns")
    print(f"Active task: {state.active_task}")
```

## Configuration

### Session Settings

```python
# Create with custom settings
state = ConversationState(
    session_id="custom_session_id",  # Optional custom ID
    max_history=50                    # Max turns to keep in memory
)
```

### Memory Client

The system uses `MemoryClient` from enhanced-memory-mcp:

```python
from memory_client import MemoryClient

# Client connects to memory-db Unix socket
client = MemoryClient(socket_path="/tmp/memory-db.sock")
```

## Testing

Run the comprehensive test suite:

```bash
cd /mnt/agentic-system/intelligent-agents
python3 test_conversation_state.py
```

Tests cover:
- Basic turn tracking
- Context summary generation
- Action tracking and status updates
- File context management
- Clarification tracking
- Task management
- Statistics generation
- Serialization/deserialization
- Max history limits
- MCP persistence integration

Run the demo:

```bash
python3 conversation_state.py
```

Run enhanced conversation manager demo:

```bash
python3 conversation_manager_enhanced.py
```

## Performance

### Memory Usage

- ~1-2 KB per conversation turn
- ~500 bytes per action record
- Deque with max_history prevents unbounded growth
- Typical session: 50 turns ≈ 100 KB

### Persistence Overhead

- Persist operation: ~50-100ms
- Automatic every 5 turns
- Non-blocking: Uses asyncio

## Best Practices

### 1. Regular Persistence

```python
# Persist every N turns
if state.total_turns % 5 == 0:
    await state.persist()
```

### 2. Context Summaries for LLMs

```python
# Include context in LLM prompts
context = state.get_context_summary(max_turns=5)
prompt = f"{context}\n\nUser: {user_message}\nAssistant:"
```

### 3. Action Tracking

```python
# Always update action status
action = ActionRecord(...)
state.add_action(action)

# Later, update status
state.update_action(action.action_id, ActionStatus.COMPLETED, result="Success")
```

### 4. File Context Management

```python
# Add files as they're discussed
state.add_file_context(file_path)

# Clear when switching tasks
if switching_tasks:
    state.clear_file_context()
```

### 5. Confidence Scoring

```python
# Track confidence for analysis
turn = state.add_turn(
    user_msg=user_msg,
    assistant_msg=response,
    confidence=0.9  # High confidence
)

# Check average confidence
stats = state.get_statistics()
if stats['average_confidence'] < 0.7:
    print("Warning: Low conversation confidence")
```

## Error Handling

The system includes comprehensive error handling:

```python
try:
    await state.persist()
except Exception as e:
    logger.error(f"Persistence failed: {e}")
    # State remains in memory, can retry later
```

All errors are logged with full stack traces for debugging.

## Future Enhancements

Potential improvements:

1. **Multi-Modal Context**: Image/video frame tracking
2. **Semantic Clustering**: Group related turns by topic
3. **Automatic Summarization**: LLM-generated summaries
4. **Conversation Branching**: Handle conversation forks
5. **Sentiment Tracking**: Emotional tone analysis
6. **Performance Metrics**: Response time, user satisfaction
7. **Export Formats**: Markdown, JSON, CSV export

## Related Systems

- **Enhanced Memory MCP**: Persistence backend
- **Consciousness Daemon**: Provides sensory context
- **Voice Mode MCP**: TTS/STT integration
- **Conversation Manager**: Basic conversation processing
- **Perception System**: Multi-modal sensor integration

## License

Part of the agentic-system autonomous AI framework.

## Support

For issues or questions:
- Check logs: `/mnt/agentic-system/logs/conversations.log`
- Review test suite: `test_conversation_state.py`
- See examples: `conversation_manager_enhanced.py`
