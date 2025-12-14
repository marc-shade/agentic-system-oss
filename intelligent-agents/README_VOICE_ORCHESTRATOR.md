# Voice Action Orchestrator - Quick Start

## What is it?

Coordinates multi-step task execution for voice commands. Bridges conversational AI with code execution through intent classification and action orchestration.

## Files

- `action_orchestrator.py` - Main orchestrator (routes intents, executes via Anthropic API)
- `intent_classifier.py` - Classifies voice commands into intent types
- `test_action_orchestrator.py` - Comprehensive test suite (9 scenarios)
- `demo_voice_action_orchestrator.py` - Interactive demo
- `VOICE_ACTION_ORCHESTRATOR.md` - Complete documentation

## Quick Test

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run demo (simulated voice commands)
cd /mnt/agentic-system/intelligent-agents
python3 demo_voice_action_orchestrator.py

# Run interactive mode
python3 demo_voice_action_orchestrator.py --interactive

# Run full test suite
python3 test_action_orchestrator.py

# Test intent classifier only (no API needed)
python3 intent_classifier.py
```

## Intent Types

1. **COMMAND** - Code execution, file operations
   - "Create a Python file called test.py"
   - "Edit the main function in app.py"
   - "Run the test suite"

2. **QUERY** - Information retrieval
   - "What Python files are in this directory?"
   - "Search for the function process_data"
   - "Show me the contents of config.json"

3. **CONVERSATION** - Natural language
   - "Hello! How are you?"
   - "Can you hear me?"
   - "Thank you for your help"

4. **META** - System control
   - "What is the system status?"
   - "Show me recent actions"
   - "What's the current directory?"

## Basic Usage

```python
import asyncio
import os
from intent_classifier import IntentClassifier
from action_orchestrator import ActionOrchestrator

async def execute_voice_command(utterance: str):
    # Initialize
    classifier = IntentClassifier()
    orchestrator = ActionOrchestrator(os.getenv("ANTHROPIC_API_KEY"))

    # Classify intent
    intent = classifier.classify(utterance)
    print(f"Intent: {intent.type.value} (confidence: {intent.confidence})")

    # Execute action
    result = await orchestrator.execute_intent(intent)
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")

    return result

# Run
asyncio.run(execute_voice_command("Create a Python file called hello.py"))
```

## Integration with Conversation Manager

```python
# In conversation_manager.py

from intent_classifier import IntentClassifier
from action_orchestrator import ActionOrchestrator

class ConversationManager:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.orchestrator = ActionOrchestrator(api_key)

    async def generate_response(self, utterance: str, context: dict) -> str:
        # Classify
        intent = self.classifier.classify(utterance)

        # Execute
        result = await self.orchestrator.execute_intent(intent, context)

        # Return response for voice output
        return result.output or result.summary
```

## Available Tools

The orchestrator can execute these tools via Anthropic API:

- `bash` - Execute bash commands
- `read_file` - Read file contents
- `write_file` - Write content to file
- `edit_file` - Edit file with search/replace
- `grep` - Search for pattern in files
- `list_files` - List files in directory

## Performance

- **Intent Classification**: <5ms (rule-based, no API)
- **Action Execution**: 500ms - 5s (depends on complexity)
- **Token Usage**: 1000-5000 per request
- **Model**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

## Logs

Execution logs: `~/agentic-system/logs/action_executions.log`

Format: JSON per line with timestamp, intent, result, tokens, errors

## Example Workflows

### Create and Test Python Module

```
Voice: "Create a Python file called math_utils.py with add and subtract functions"
→ COMMAND intent → write_file → Success

Voice: "Create a test file for math_utils"
→ COMMAND intent → write_file → Success

Voice: "Run the tests"
→ COMMAND intent → bash → Success
```

### Code Search and Analysis

```
Voice: "Find all TODO comments in Python files"
→ QUERY intent → grep → Results

Voice: "Show me the function process_data"
→ QUERY intent → grep + read_file → Code displayed

Voice: "How many functions are in app.py?"
→ QUERY intent → read_file → Count
```

## Next Steps

1. **Integrate with Voice I/O**: Connect to conversation_manager.py for real voice input/output
2. **Add Voice Feedback**: Real-time updates during execution ("Creating file...", "Running tests...")
3. **Store Learnings**: Record outcomes in enhanced-memory MCP
4. **Persistent Tasks**: Create tasks in agent-runtime MCP for complex operations
5. **ML Classification**: Replace rule-based classifier with ML model for better accuracy

## Architecture

```
Voice Input (Whisper)
    ↓
Intent Classifier (rule-based, fast)
    ↓
Action Orchestrator (Anthropic API + tools)
    ↓
Multi-Step Execution
    ↓
Voice Output (Edge TTS)
```

## Security

- Confirmation required for destructive operations (delete, remove, overwrite)
- Bash commands timeout after 30 seconds
- File operations restricted to working directory
- No sudo/privileged operations

## Documentation

See `VOICE_ACTION_ORCHESTRATOR.md` for complete documentation including:
- Detailed architecture
- Entity extraction
- Error handling
- Integration points
- Future enhancements

## Support

Test suite includes:
- ✓ Command execution (file creation)
- ✓ Query execution (information retrieval)
- ✓ Conversation handling
- ✓ Meta commands (system status)
- ✓ Bash execution
- ✓ File search
- ✓ Error handling
- ✓ Multi-step execution
- ✓ Context awareness

All tests pass with comprehensive coverage.
