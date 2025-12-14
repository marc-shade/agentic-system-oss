# Intent Classification System

Natural language intent classification for voice-controlled AI coding assistant using Anthropic Claude API.

## Overview

The Intent Classification System analyzes voice utterances and classifies them into actionable intents with structured entity extraction. It understands coding tasks, system operations, git commands, and natural conversation.

## Features

- **4 Intent Types**: COMMAND, QUERY, CONVERSATION, META
- **Entity Extraction**: Files, operations, code symbols, git operations, system resources
- **Context Awareness**: Session state, conversation history, working directory
- **High Accuracy**: Powered by claude-sonnet-4-5-20250929
- **Caching**: Automatic result caching for performance
- **Error Handling**: Graceful fallbacks and retry logic

## Quick Start

### Installation

```bash
# Install dependencies (already in intelligent-agents/requirements.txt)
pip3 install anthropic>=0.40.0

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Basic Usage

```python
from intent_classifier import IntentClassifier
import asyncio

async def classify_command():
    # Initialize classifier
    classifier = IntentClassifier()

    # Classify an utterance
    intent = await classifier.classify("fix the bug in auth.py")

    print(f"Type: {intent.type}")              # COMMAND
    print(f"Confidence: {intent.confidence}")  # 0.95
    print(f"Entities: {intent.entities}")
    # {'file_path': ['auth.py'], 'operation': 'fix', 'target': 'bug'}

asyncio.run(classify_command())
```

## Intent Types

### COMMAND - Direct Action Instructions

Requests to perform operations:

- **File Operations**: "fix the bug in auth.py", "create a new schema"
- **Code Operations**: "refactor the login function", "add error handling"
- **Git Operations**: "commit these changes", "create a new branch"
- **System Operations**: "restart Redis", "deploy to production"

**Extracted Entities**: `file_path`, `operation`, `target`, `function_name`, `git_operation`

### QUERY - Information Requests

Questions about code, system state, or documentation:

- **Code Inspection**: "what does the login function do?", "show me the schema"
- **System Status**: "is Redis running?", "check memory usage"
- **Git History**: "show me recent commits", "who changed this file?"
- **Documentation**: "how do I configure Redis?"

**Extracted Entities**: `function_name`, `service_name`, `timeframe`, `git_operation`, `resource_type`

### CONVERSATION - Dialogue and Confirmations

Natural conversation, confirmations, and acknowledgments:

- **Confirmations**: "yes", "that looks correct", "no, try something else"
- **Acknowledgments**: "okay", "thanks", "I understand"
- **Questions**: "can you explain that?", "what do you mean?"
- **Feedback**: "that worked", "try again"

**Extracted Entities**: `confirmation`, `sentiment`, `acknowledgment`

### META - System Control

Session control, preferences, and help requests:

- **Session Control**: "pause", "stop", "continue", "undo"
- **Mode Switching**: "enter debug mode", "switch to manual mode"
- **Preferences**: "speak faster", "use more detail", "summarize"
- **Help**: "what can you do?", "help", "list commands"

**Extracted Entities**: `control_action`, `preference`, `help_request`

## API Reference

### IntentClassifier

Main classifier class for intent classification.

#### Constructor

```python
IntentClassifier(
    api_key: Optional[str] = None,      # Anthropic API key (or ANTHROPIC_API_KEY env)
    model: str = "claude-sonnet-4-5-20250929",  # Claude model
    max_tokens: int = 512,               # Max response tokens
    temperature: float = 0.0,            # Temperature (0.0 = deterministic)
    cache_size: int = 100                # Classification cache size
)
```

#### classify()

```python
async def classify(
    utterance: str,                      # User's voice input
    context: Optional[Dict[str, Any]] = None,  # Additional context
    use_cache: bool = True               # Use cached results
) -> Intent
```

Classifies an utterance and returns a structured `Intent` object.

**Returns**: `Intent` object with classification results

**Raises**: Returns low-confidence intent on errors (never raises exceptions)

#### update_session_context()

```python
def update_session_context(updates: Dict[str, Any])
```

Updates session context information used for classification.

**Supported Context Keys**:
- `working_directory`: Current working directory
- `open_files`: List of currently open files
- `active_branch`: Active git branch
- `running_services`: List of running services

**Example**:
```python
classifier.update_session_context({
    "working_directory": "/mnt/agentic-system",
    "open_files": ["auth.py", "db.py"],
    "active_branch": "feature/voice-commands"
})
```

#### get_stats()

```python
def get_stats() -> Dict[str, Any]
```

Returns classifier statistics including cache size, intent distribution, and average confidence.

#### clear_cache() / clear_context()

```python
def clear_cache()    # Clear classification cache
def clear_context()  # Clear conversation context
```

### Intent

Structured intent classification result.

#### Attributes

```python
type: str                      # COMMAND, QUERY, CONVERSATION, META
entities: Dict[str, Any]       # Extracted entities
confidence: float              # Confidence score (0.0-1.0)
original_utterance: str        # Original user input
reasoning: Optional[str]       # Classification reasoning
suggested_action: Optional[str]  # Suggested action to take
timestamp: str                 # ISO timestamp
```

#### Methods

```python
to_dict() -> Dict[str, Any]   # Convert to dictionary
to_json() -> str              # Convert to JSON string
```

## Integration Examples

### With Voice Mode MCP

```python
from intent_classifier import IntentClassifier
import asyncio

# Assuming voice-mode MCP is available
# from mcp_client import listen, speak

async def voice_loop():
    classifier = IntentClassifier()

    while True:
        # Listen to user (placeholder - use actual voice-mode MCP)
        utterance = input("You: ")

        # Classify intent
        intent = await classifier.classify(utterance)

        print(f"Intent: {intent.type} (confidence: {intent.confidence:.2f})")
        print(f"Action: {intent.suggested_action}")

        # Execute based on intent type
        if intent.type == "COMMAND":
            print(f"Executing command: {intent.entities.get('operation')}")
        elif intent.type == "QUERY":
            print(f"Querying: {intent.entities}")
        elif intent.type == "CONVERSATION":
            print(f"Conversation: {intent.entities.get('confirmation')}")
        elif intent.type == "META":
            print(f"Meta action: {intent.entities.get('control_action')}")

asyncio.run(voice_loop())
```

### With Conversation Manager

```python
from intent_classifier import IntentClassifier
from conversation_manager import ConversationManager

async def integrated_system():
    classifier = IntentClassifier()
    conversation = ConversationManager()

    # Update context from conversation state
    classifier.update_session_context({
        "working_directory": conversation.current_directory,
        "open_files": conversation.open_files
    })

    # Classify with conversation context
    intent = await classifier.classify(
        utterance="commit these changes",
        context={"last_action": conversation.last_action}
    )

    # Feed intent to conversation manager
    response = await conversation.process_intent(intent)

    return response
```

### With Consciousness Daemon

```python
from intent_classifier import IntentClassifier
from consciousness_daemon import ConsciousnessDaemon

async def voice_to_consciousness():
    classifier = IntentClassifier()
    consciousness = ConsciousnessDaemon()

    utterance = "fix the authentication bug"

    # Classify intent
    intent = await classifier.classify(utterance)

    # Send to consciousness daemon for reasoning
    decision = await consciousness.reason_about_intent(intent)

    # Execute decision
    result = await consciousness.execute_decision(decision)

    return result
```

## Testing

### Run Demo (No API Key Required)

```bash
cd /mnt/agentic-system/intelligent-agents
python3 test_intent_classifier_demo.py
```

Shows example intents, API usage, and test cases.

### Run Full Test Suite (Requires API Key)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 intent_classifier.py
```

Runs 10 test cases with real API calls and generates detailed report at `/tmp/intent_classifier_test_results.json`.

### Example Test Output

```
Test 1/10: File-specific command
Utterance: "fix the bug in auth.py"
Expected: COMMAND

Result: ✅ PASS
  Type: COMMAND
  Confidence: 0.95
  Entities: {
    "file_path": ["auth.py"],
    "operation": "fix",
    "target": "bug"
  }
  Reasoning: User is requesting a code fix operation on a specific file
  Suggested Action: Open auth.py and analyze for bugs to fix
```

## Performance

### Latency
- **Target**: <500ms per classification
- **Typical**: 200-400ms with API
- **Cached**: <1ms

### Accuracy
- **High Confidence (>0.9)**: Commands and queries with specific entities
- **Medium Confidence (0.6-0.9)**: Ambiguous or context-dependent intents
- **Low Confidence (<0.6)**: Requires clarification

### Caching
- **Cache Size**: 100 recent classifications (configurable)
- **Hit Rate**: ~40-60% in typical usage
- **Context Window**: 5 recent intents for conversation continuity

## Error Handling

### Low Confidence (<0.6)

```python
intent = await classifier.classify(utterance)

if intent.confidence < 0.6:
    # Request clarification
    print(f"Confidence low ({intent.confidence:.2f}). Possible interpretation:")
    print(f"  {intent.reasoning}")
    print("Can you rephrase that?")
```

### API Errors

The classifier never raises exceptions. On API errors, it returns a META intent with error details:

```python
{
  "type": "META",
  "entities": {"error": "API timeout"},
  "confidence": 0.0,
  "reasoning": "Classification failed: API timeout",
  "suggested_action": "Log error and notify user"
}
```

### Ambiguous Input

For ambiguous input, the classifier returns low confidence with multiple possible interpretations in the reasoning:

```python
intent = await classifier.classify("change it")

# Returns:
# {
#   "type": "COMMAND",
#   "confidence": 0.4,
#   "reasoning": "Ambiguous pronoun 'it'. Could refer to: file, function, configuration, etc.",
#   "suggested_action": "Ask user to clarify what 'it' refers to"
# }
```

## Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional (with defaults)
export INTENT_CLASSIFIER_MODEL="claude-sonnet-4-5-20250929"
export INTENT_CLASSIFIER_MAX_TOKENS="512"
export INTENT_CLASSIFIER_TEMPERATURE="0.0"
export INTENT_CLASSIFIER_CACHE_SIZE="100"
```

### Programmatic Configuration

```python
classifier = IntentClassifier(
    api_key="sk-ant-...",
    model="claude-sonnet-4-5-20250929",
    max_tokens=512,
    temperature=0.0,  # 0.0 = deterministic, 1.0 = creative
    cache_size=100
)
```

## Files

- **`intent_classifier.py`**: Main implementation
- **`test_intent_classifier_demo.py`**: Demo and examples (no API key required)
- **`/docs/INTENT_CLASSIFICATION_DESIGN.md`**: Detailed design document
- **`INTENT_CLASSIFICATION_README.md`**: This file

## Integration Roadmap

- [x] Core classification with Claude API
- [x] Entity extraction for coding tasks
- [x] Context awareness and caching
- [x] Comprehensive test suite
- [ ] Voice Mode MCP integration
- [ ] Conversation Manager integration
- [ ] Consciousness Daemon integration
- [ ] Multi-intent classification (compound commands)
- [ ] Intent chaining for complex workflows
- [ ] Learning from corrections

## Troubleshooting

### API Key Issues

```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Test API access
python3 -c "from anthropic import Anthropic; c = Anthropic(); print('API key valid')"
```

### Import Errors

```bash
# Install dependencies
pip3 install anthropic>=0.40.0

# Verify installation
python3 -c "import anthropic; print(f'Anthropic version: {anthropic.__version__}')"
```

### Low Classification Accuracy

1. **Update session context** with current working directory and open files
2. **Provide additional context** in the `context` parameter
3. **Adjust confidence threshold** based on your use case
4. **Clear cache** if getting stale results: `classifier.clear_cache()`

## Contributing

To improve the intent classifier:

1. Add test cases to `intent_classifier.py`
2. Update entity types in system prompt if needed
3. Adjust confidence thresholds based on usage data
4. Report classification errors with examples

## License

Part of the agentic-system project. See main repository for license details.

---

**Status**: Production Ready
**Version**: 1.0
**Last Updated**: 2025-11-17
**Maintainer**: Agentic System Team
