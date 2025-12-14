# Conversation State Management - Quick Reference

## Installation

```bash
# No installation needed - uses existing dependencies
cd /mnt/agentic-system/intelligent-agents
```

## Quick Start

```python
from conversation_state import ConversationState, TurnType

# Create state
state = ConversationState()

# Add conversation turn
state.add_turn(
    user_msg="Hello",
    assistant_msg="Hi! How can I help?",
    turn_type=TurnType.GREETING
)

# Get context for LLM
context = state.get_context_summary()
```

## Common Operations

### Track Conversation

```python
# Add turn with metadata
turn = state.add_turn(
    user_msg="Build a REST API",
    assistant_msg="I'll help you build a REST API",
    turn_type=TurnType.COMMAND,
    confidence=0.9,
    files=["/project/app.py"]
)
```

### Manage Tasks

```python
# Start task
state.update_active_task("Build API", "Create authentication endpoint")

# Complete task
summary = state.complete_task()
```

### Track Actions

```python
from conversation_state import ActionRecord, ActionStatus

# Create action
action = ActionRecord(
    action_id="read_file",
    action_type="file_read",
    description="Reading config file",
    status=ActionStatus.PENDING
)

# Add and update
state.add_action(action)
state.update_action("read_file", ActionStatus.COMPLETED, result="Success")
```

### Track Files

```python
# Add file context
state.add_file_context("/project/main.py")

# Clear context
state.clear_file_context()
```

### Handle Clarifications

```python
# Add clarification
state.add_clarification("Which Python version?")

# Resolve
state.resolve_clarification("Which Python version?", "Python 3.9")
```

### Persistence

```python
# Save to enhanced-memory MCP
await state.persist()

# Restore from previous session
new_state = ConversationState()
await new_state.restore("conv_20251117_113117")
```

### Get Statistics

```python
stats = state.get_statistics()
print(f"Total turns: {stats['total_turns']}")
print(f"Confidence: {stats['average_confidence']:.2f}")
```

## Turn Types

```python
TurnType.GREETING          # Hello, hi
TurnType.QUESTION          # What, why, how
TurnType.COMMAND           # Show, create, build
TurnType.CLARIFICATION     # Follow-up question
TurnType.CONFIRMATION      # Yes, no, okay
TurnType.ERROR             # Error occurred
TurnType.INFO_RESPONSE     # Information provided
```

## Action Status

```python
ActionStatus.PENDING       # Queued
ActionStatus.IN_PROGRESS   # Executing
ActionStatus.COMPLETED     # Done
ActionStatus.FAILED        # Error
ActionStatus.BLOCKED       # Waiting
```

## Context Summary

```python
# Get summary for LLM prompt
summary = state.get_context_summary(
    max_turns=5,          # Recent turns
    include_actions=True,  # Show actions
    include_files=True     # Show files
)
```

## Serialization

```python
# To dict
data = state.to_dict()

# To JSON
import json
json_str = json.dumps(data, indent=2)

# From dict
restored = ConversationState.from_dict(data)
```

## Testing

```bash
# Run test suite
python3 test_conversation_state.py

# Run demo
python3 conversation_state.py

# Run enhanced manager
python3 conversation_manager_enhanced.py
```

## Configuration

```python
# Custom settings
state = ConversationState(
    session_id="custom_id",  # Custom session ID
    max_history=50           # Max turns in memory
)
```

## Integration Example

```python
from conversation_manager_enhanced import EnhancedConversationManager

# Create manager with state tracking
manager = EnhancedConversationManager()

# Process transcript
await manager.process_utterance({
    "utterance": "Help me build an API",
    "timestamp": "2025-11-17T11:30:00"
})

# Show status
manager.print_status()
```

## Error Handling

```python
try:
    await state.persist()
except Exception as e:
    logger.error(f"Persistence failed: {e}")
    # State remains in memory
```

## Memory Usage

- ~1-2 KB per turn
- ~500 bytes per action
- Max history prevents unbounded growth
- 50 turns ≈ 100 KB

## Persistence Strategy

- Auto: Every 5 turns
- Manual: `await state.persist()`
- On exit: Final persist

## Logs

```bash
# View logs
tail -f /mnt/agentic-system/logs/conversations.log
```

## Common Patterns

### Multi-Turn Task

```python
# Start task
state.update_active_task("Database Migration", "Migrate users table")

# Track progress
for step in ["backup", "migrate", "verify"]:
    action = ActionRecord(
        action_id=step,
        action_type="database",
        description=f"Database {step}",
        status=ActionStatus.COMPLETED
    )
    state.add_action(action)
    state.add_turn(
        user_msg=f"Complete {step}",
        assistant_msg=f"{step.capitalize()} completed",
        turn_type=TurnType.INFO_RESPONSE
    )

# Complete
summary = state.complete_task()
```

### Context-Aware Response

```python
# Get context for LLM
context = state.get_context_summary(max_turns=3)

# Build prompt
prompt = f"""
{context}

User: {user_message}
Assistant:"""

# Generate response with context
response = await llm.generate(prompt)
```

### Session Continuity

```python
# At session start
state = ConversationState()

# Try to restore previous session
if previous_session_id:
    restored = await state.restore(previous_session_id)
    if restored:
        print(f"Restored {len(state.history)} turns")

# Continue conversation
state.add_turn(...)
```

## Troubleshooting

### State Not Persisting

```python
# Check memory client
if state.memory_client is None:
    print("Memory client not available")

# Manual persist
try:
    await state.persist()
    print("✓ Persisted")
except Exception as e:
    print(f"✗ Failed: {e}")
```

### Memory Growth

```python
# Check history size
print(f"Turns in memory: {len(state.history)}")
print(f"Max history: {state.max_history}")

# Reduce if needed
state = ConversationState(max_history=20)
```

### Low Confidence

```python
stats = state.get_statistics()
if stats['average_confidence'] < 0.7:
    print("Warning: Low confidence")
    # Add clarifications or provide more context
```

## API Reference

### ConversationState

- `add_turn()`: Add conversation turn
- `update_active_task()`: Set current task
- `complete_task()`: Finish task
- `add_action()`: Track action
- `update_action()`: Update action status
- `add_clarification()`: Need user input
- `resolve_clarification()`: Got answer
- `add_file_context()`: Track file
- `get_context_summary()`: Generate summary
- `get_statistics()`: Get stats
- `persist()`: Save to MCP
- `restore()`: Load from MCP

### Data Classes

- `ConversationTurn`: Single exchange
- `ActionRecord`: Tracked action
- `TurnType`: Turn classification
- `ActionStatus`: Action state

## Related Documentation

- Full documentation: `CONVERSATION_STATE_README.md`
- Test suite: `test_conversation_state.py`
- Example integration: `conversation_manager_enhanced.py`
- Main implementation: `conversation_state.py`
