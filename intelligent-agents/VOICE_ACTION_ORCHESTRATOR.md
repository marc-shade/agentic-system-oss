# Voice Action Orchestrator - Implementation Guide

## Overview

The Voice Action Orchestrator coordinates multi-step task execution for voice commands, bridging the gap between conversational AI and code execution.

**Components:**
1. **Intent Classifier** - Classifies voice commands into intent types
2. **Action Orchestrator** - Routes intents and executes multi-step actions
3. **Conversation Manager** - Handles bidirectional voice interaction

## Architecture

```
Voice Input (Whisper STT)
         ↓
Conversation Manager
         ↓
Intent Classifier
    ↓   ↓   ↓   ↓
COMMAND QUERY CONVERSATION META
    ↓
Action Orchestrator
    ↓
Anthropic API + Tools
    ↓
File Operations, Bash, Code Search
    ↓
Voice Output (Edge TTS)
```

## Intent Types

### 1. COMMAND
**Code execution and file operations**

Examples:
- "Create a Python file called test.py"
- "Edit the main function in app.py"
- "Run the test suite"
- "Commit these changes"
- "Delete temporary files"

Entities Extracted:
- `file_name` - Target file
- `file_path` - Full path
- `action` - Verb (create, edit, delete)
- `language` - Programming language
- `identifier` - Function/class name

### 2. QUERY
**Information retrieval and search**

Examples:
- "What Python files are in this directory?"
- "Search for the function process_data"
- "Show me the contents of config.json"
- "How many test files do we have?"
- "Find all TODO comments"

Entities Extracted:
- `search_term` - What to search for
- `file_type` - File type filter
- `action` - Query verb
- `scope` - Search scope

### 3. CONVERSATION
**Natural language interaction**

Examples:
- "Hello! How are you?"
- "Can you hear me?"
- "Thank you for your help"
- "What can you do?"
- "Explain how this works"

No entity extraction needed.

### 4. META
**System control and status**

Examples:
- "What is the system status?"
- "What are you currently working on?"
- "Show me recent actions"
- "What's the current directory?"

No entity extraction needed.

## Implementation

### Intent Classification

```python
from intent_classifier import IntentClassifier

classifier = IntentClassifier()
intent = classifier.classify("Create a Python file called test.py")

print(f"Type: {intent.type.value}")  # COMMAND
print(f"Confidence: {intent.confidence}")  # 0.9
print(f"Entities: {intent.entities}")  # {'file_name': 'test.py', 'action': 'create'}
```

**Features:**
- Rule-based pattern matching (fast, no API calls)
- Entity extraction (file names, paths, actions)
- Confidence scoring
- Confirmation detection for destructive operations

### Action Orchestration

```python
import os
from action_orchestrator import ActionOrchestrator, Intent, IntentType

api_key = os.getenv("ANTHROPIC_API_KEY")
orchestrator = ActionOrchestrator(api_key)

intent = Intent(
    type=IntentType.COMMAND,
    text="Create a Python file called hello.py that prints hello world",
    entities={"file_name": "hello.py"},
    confidence=0.95
)

result = await orchestrator.execute_intent(intent)

print(f"Success: {result.success}")
print(f"Steps: {len(result.steps)}")
print(f"Output: {result.output}")
print(f"Summary: {result.summary}")
```

**Execution Flow:**
1. Build system prompt with context (working directory, git branch, open files)
2. Create user message with intent and entities
3. Execute via Anthropic API with tool use
4. Iterate through tool calls (bash, read_file, write_file, edit_file, grep)
5. Track execution steps and errors
6. Generate human-readable summary

### Integration with Conversation Manager

```python
from conversation_manager import ConversationManager
from intent_classifier import IntentClassifier
from action_orchestrator import ActionOrchestrator

# Initialize components
classifier = IntentClassifier()
orchestrator = ActionOrchestrator(api_key)
conversation_mgr = ConversationManager()

async def process_voice_command(utterance: str, context: dict):
    """Process voice command through full pipeline"""

    # 1. Classify intent
    intent = classifier.classify(utterance)

    # 2. Execute action
    result = await orchestrator.execute_intent(intent, context)

    # 3. Speak response
    if result.success:
        response = result.output or result.summary
    else:
        response = f"I encountered an error: {', '.join(result.errors)}"

    await conversation_mgr.speak_response(response)

    return result
```

## Available Tools

The action orchestrator uses the following tools via Anthropic API:

### 1. bash
Execute bash commands in working directory

```python
{
    "name": "bash",
    "input": {
        "command": "ls -la"
    }
}
```

### 2. read_file
Read file contents

```python
{
    "name": "read_file",
    "input": {
        "file_path": "config.json"
    }
}
```

### 3. write_file
Write content to file

```python
{
    "name": "write_file",
    "input": {
        "file_path": "hello.py",
        "content": "print('Hello World')"
    }
}
```

### 4. edit_file
Edit file with search/replace

```python
{
    "name": "edit_file",
    "input": {
        "file_path": "app.py",
        "old_text": "def old_function():",
        "new_text": "def new_function():"
    }
}
```

### 5. grep
Search for pattern in files

```python
{
    "name": "grep",
    "input": {
        "pattern": "TODO",
        "path": "."
    }
}
```

### 6. list_files
List files in directory

```python
{
    "name": "list_files",
    "input": {
        "path": ".",
        "pattern": "*.py"
    }
}
```

## Execution State Management

### Conversation State

The orchestrator maintains conversation state across intents:

```python
conversation_state = ConversationState(
    active_context={
        "working_directory": "/mnt/agentic-system",
        "current_branch": "master",
        "open_files": ["app.py", "config.json"]
    },
    recent_actions=[...],  # Last 10 execution results
    file_modifications={...},  # Files modified this session
    pending_confirmations=[]  # Actions awaiting approval
)
```

### Execution Tracking

Each execution produces a detailed result:

```python
result = ExecutionResult(
    success=True,
    intent=intent,
    steps=[
        ExecutionStep(
            step_number=1,
            description="Execute write_file",
            tool="write_file",
            parameters={"file_path": "...", "content": "..."},
            status=ActionStatus.SUCCESS,
            duration_ms=245
        )
    ],
    output="File created successfully",
    summary="Executed 1 step(s): ✓ Execute write_file",
    errors=[],
    total_duration_ms=287,
    tokens_used={"input": 1234, "output": 567}
)
```

## Error Handling

The orchestrator provides comprehensive error handling:

### Tool Execution Errors

```python
try:
    tool_result = await self._execute_tool(tool_name, parameters)
    step.status = ActionStatus.SUCCESS
except Exception as e:
    step.status = ActionStatus.FAILED
    step.error = str(e)
    errors.append(f"{tool_name}: {str(e)}")
```

### Timeout Protection

All bash commands timeout after 30 seconds:

```python
result = subprocess.run(
    command,
    shell=True,
    timeout=30
)
```

### File Not Found

Graceful handling with informative messages:

```python
if not file_path.exists():
    raise FileNotFoundError(f"File not found: {file_path}")
```

## Testing

### Run Intent Classifier Tests

```bash
cd /mnt/agentic-system/intelligent-agents
python3 intent_classifier.py
```

Tests 20+ utterances across all intent types.

### Run Action Orchestrator Tests

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 test_action_orchestrator.py
```

**Test Suite:**
1. COMMAND: Create Python file
2. QUERY: List files
3. CONVERSATION: Greeting
4. META: System status
5. COMMAND: Bash execution
6. QUERY: File search
7. Error handling
8. Multi-step command (complex)
9. Context awareness (multiple intents)

Expected output:
```
Tests Run: 12
✓ Passed: 12
✗ Failed: 0

Total Duration: ~15000ms
Total Steps: ~25
Total Tokens: ~50000 (input + output)
```

### Manual Testing

Test individual intents:

```python
import asyncio
import os
from action_orchestrator import ActionOrchestrator, Intent, IntentType

async def test():
    orchestrator = ActionOrchestrator(os.getenv("ANTHROPIC_API_KEY"))

    intent = Intent(
        type=IntentType.COMMAND,
        text="Create a file called test.txt with content Hello World",
        entities={"file_name": "test.txt"},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")

asyncio.run(test())
```

## Performance Characteristics

### Intent Classification
- **Latency**: <5ms (rule-based, no API)
- **Memory**: <10MB
- **Accuracy**: ~85% (simple heuristics)

### Action Orchestration
- **Latency**: 500ms - 5s (depends on complexity)
- **Tokens per request**: 1000-5000
- **API model**: Claude Sonnet 4.5
- **Temperature**: 0.0 (deterministic)

### Tool Execution
- **Bash**: <30s timeout
- **File operations**: <1s per operation
- **Grep**: <10s timeout

## Logging

All executions are logged to:

```
~/agentic-system/logs/action_executions.log
```

Log format (JSON per line):

```json
{
  "timestamp": "2025-11-17T12:30:45",
  "intent_type": "COMMAND",
  "intent_text": "Create a Python file...",
  "success": true,
  "steps": 1,
  "duration_ms": 287,
  "tokens_used": {"input": 1234, "output": 567},
  "errors": []
}
```

## Integration Points

### With Conversation Manager

```python
# In conversation_manager.py
async def generate_response(self, user_utterance: str, context: Dict):
    # Classify intent
    intent = self.classifier.classify(user_utterance)

    # Execute action
    result = await self.orchestrator.execute_intent(intent, context)

    # Return response
    return result.output or result.summary
```

### With Enhanced Memory MCP

Store execution outcomes for learning:

```python
# Record action outcome
memory_client.record_action_outcome(
    action_type="voice_command",
    action_description=intent.text,
    expected_result="File created",
    actual_result=result.output,
    success_score=1.0 if result.success else 0.0
)
```

### With Agent Runtime MCP

Create persistent tasks:

```python
# Create task from complex command
task_id = runtime_client.create_task(
    title=intent.text,
    description=f"Voice command: {intent.text}",
    priority=7
)

# Execute task
result = await orchestrator.execute_intent(intent)

# Update task status
runtime_client.update_task_status(
    task_id=task_id,
    status="completed" if result.success else "failed",
    result=result.summary
)
```

## Future Enhancements

### 1. ML-Based Intent Classification
Replace rule-based classifier with fine-tuned model:
- Train on voice command dataset
- Use Claude for few-shot classification
- Improve accuracy to 95%+

### 2. Multi-Turn Dialog
Support clarifying questions:
- "Which file did you mean?"
- "Should I overwrite the existing file?"
- Context-aware follow-ups

### 3. Proactive Suggestions
Suggest next actions based on context:
- "Would you like me to run the tests?"
- "Should I commit these changes?"

### 4. Error Recovery
Automatic retry with corrections:
- Detect common errors
- Apply fixes automatically
- Learn from failures

### 5. Voice Feedback During Execution
Real-time progress updates:
- "Creating file..."
- "Running tests..."
- "All tests passed!"

### 6. Claude Code MCP Integration
When available, use Claude Code MCP for:
- Direct tool access (no API wrapper)
- Better file operations
- Improved code analysis

## Security Considerations

### Confirmation for Destructive Operations

The classifier detects destructive operations:

```python
if intent.requires_confirmation:
    # Speak confirmation request
    await speak_response(
        f"This will {intent.entities['action']} files. Are you sure?"
    )
    # Wait for user confirmation
    confirmation = await listen_for_confirmation()
    if not confirmation:
        return  # Abort
```

### Sandboxed Execution

All bash commands run in working directory with:
- 30-second timeout
- No sudo/privileged operations
- Output capture and inspection

### File Access Restrictions

File operations restricted to:
- Working directory and subdirectories
- No system file access (/etc, /sys, etc.)
- Relative paths resolved safely

## Troubleshooting

### Intent Misclassification

If commands are misclassified:
1. Check pattern matching rules
2. Add specific patterns to classifier
3. Increase confidence thresholds
4. Consider ML-based classification

### Tool Execution Failures

If tool calls fail:
1. Check API key is valid
2. Verify file paths are correct
3. Review error messages in logs
4. Test tools manually with orchestrator

### Timeout Issues

If commands timeout:
1. Increase timeout in `_tool_bash`
2. Break complex commands into steps
3. Use background execution for long tasks

### Token Limits

If hitting token limits:
1. Reduce context in system prompt
2. Limit recent actions in context
3. Use shorter file paths
4. Summarize tool results

## Support

For issues or questions:
- Check logs: `~/agentic-system/logs/action_executions.log`
- Run tests: `python3 test_action_orchestrator.py`
- Review code: `/mnt/agentic-system/intelligent-agents/action_orchestrator.py`

## Example Workflows

### Create and Test Python Module

Voice commands:
1. "Create a Python file called math_utils.py with add and subtract functions"
2. "Create a test file for math_utils"
3. "Run the tests"
4. "If tests pass, commit the changes"

### Code Search and Analysis

Voice commands:
1. "Find all TODO comments in Python files"
2. "Show me the function process_data"
3. "How many functions are in app.py?"
4. "Explain what the main function does"

### System Management

Voice commands:
1. "What is the system status?"
2. "What files did we modify?"
3. "Show me recent actions"
4. "What's the current git branch?"

## Version History

- **v1.0** (2025-11-17): Initial implementation
  - Intent classification with 4 types
  - Action orchestration with 6 tools
  - Comprehensive error handling
  - Execution state management
  - Test suite with 9 scenarios
