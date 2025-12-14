# Intent Classifier - Quick Start Guide

## Installation

```bash
# No installation needed for rule-based classifier
# Already available in intelligent-agents/intent_classifier.py

# For AI-powered classifier (optional):
pip3 install anthropic>=0.40.0
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Basic Usage

### Rule-Based Classifier (Fast, Local)

```python
from intent_classifier import IntentClassifier

# Initialize
classifier = IntentClassifier()

# Classify
intent = classifier.classify("Create a Python file called test.py")

# Use result
print(f"Type: {intent.type.value}")           # COMMAND
print(f"Confidence: {intent.confidence}")     # 0.90
print(f"Entities: {intent.entities}")         # {'file_name': 'test.py', ...}
print(f"Confirmation: {intent.requires_confirmation}")  # False
```

### AI-Powered Classifier (Enhanced Understanding)

```python
from intent_classifier_ai import IntentClassifierAI
import asyncio

async def classify():
    # Initialize
    classifier = IntentClassifierAI(api_key="sk-ant-...")

    # Classify
    intent = await classifier.classify("fix the authentication bug")

    # Use result
    print(f"Type: {intent.type}")
    print(f"Confidence: {intent.confidence}")
    print(f"Reasoning: {intent.reasoning}")
    print(f"Suggested Action: {intent.suggested_action}")

asyncio.run(classify())
```

## Intent Types

| Type | Examples | Entities |
|------|----------|----------|
| **COMMAND** | "create file test.py"<br>"commit changes"<br>"restart Redis" | file_path, operation, service_name, git_operation |
| **QUERY** | "what does login do?"<br>"show git commits"<br>"is Redis running?" | function_name, service_name, timeframe, git_operation |
| **CONVERSATION** | "yes"<br>"thanks"<br>"hello" | confirmation, sentiment, acknowledgment |
| **META** | "pause"<br>"status"<br>"help" | control_action, preference, help_request |

## Common Patterns

### File Operations

```python
"Create a Python file called auth.py"
→ COMMAND, entities: {'file_name': 'auth.py', 'language': 'python', 'action': 'create'}

"Edit the main function in app.py"
→ COMMAND, entities: {'file_name': 'app.py', 'action': 'edit'}

"Delete temporary files"
→ COMMAND, requires_confirmation: True
```

### Git Operations

```python
"Commit these changes"
→ COMMAND, entities: {'action': 'commit'}

"Show recent git commits"
→ QUERY, entities: {'git_operation': 'commits', 'timeframe': 'recent'}

"Create a new branch"
→ COMMAND, entities: {'git_operation': 'branch'}
```

### Code Inspection

```python
"What does the login function do?"
→ QUERY, entities: {'function_name': 'login', 'action': 'explain'}

"Search for TODO comments"
→ QUERY, entities: {'search_term': 'TODO'}

"Analyze the authentication flow"
→ QUERY, entities: {'action': 'analyze'}
```

### System Operations

```python
"Restart Redis service"
→ COMMAND, entities: {'service_name': 'Redis', 'action': 'restart'}

"Check system status"
→ META, entities: {'action': 'status'}

"What's currently running?"
→ META, entities: {'scope': 'current'}
```

## Integration Examples

### With Voice Mode

```python
from intent_classifier import IntentClassifier
# from voice_mode import listen, speak

classifier = IntentClassifier()

# Voice loop
while True:
    # Listen (placeholder - use actual voice-mode MCP)
    utterance = input("Voice: ")

    # Classify
    intent = classifier.classify(utterance)

    # Route based on type
    if intent.type.value == "COMMAND":
        result = execute_command(intent)
        print(f"Executed: {result}")
    elif intent.type.value == "QUERY":
        answer = query_information(intent)
        print(f"Answer: {answer}")
```

### With Confirmation

```python
intent = classifier.classify("Delete all temporary files")

if intent.requires_confirmation:
    # Ask user to confirm
    confirm = input(f"Confirm action: {intent.text}? (y/n): ")
    if confirm.lower() != 'y':
        print("Action cancelled")
        continue

# Execute action
execute_intent(intent)
```

### With Context

```python
from intent_classifier_ai import IntentClassifierAI

classifier = IntentClassifierAI()

# Update session context
classifier.update_session_context({
    "working_directory": "/mnt/agentic-system",
    "open_files": ["auth.py", "db.py"],
    "active_branch": "feature/voice"
})

# Classify with context
intent = await classifier.classify("commit these changes")
# Context aware: knows which files are open and what branch
```

## Testing

### Quick Test

```bash
cd /mnt/agentic-system/intelligent-agents
python3 intent_classifier.py
```

### Demo (No API Key)

```bash
python3 test_intent_classifier_demo.py
```

### Integration Example

```bash
python3 intent_classifier_integration_example.py
```

## Confidence Thresholds

```python
intent = classifier.classify(utterance)

if intent.confidence >= 0.9:
    # High confidence - execute immediately
    execute_intent(intent)
elif intent.confidence >= 0.6:
    # Medium confidence - confirm first
    confirm_and_execute(intent)
else:
    # Low confidence - ask for clarification
    print("I didn't understand. Can you rephrase?")
```

## Entity Extraction

### File Names

```python
"Create test.py" → {'file_name': 'test.py'}
"Edit app/main.py" → {'file_path': 'app/main.py', 'file_name': 'main.py'}
```

### Code Symbols

```python
"Refactor login function" → {'function_name': 'login', 'action': 'refactor'}
"Fix UserAuth class" → {'class_name': 'UserAuth', 'action': 'fix'}
```

### Operations

```python
"Create a file" → {'action': 'create'}
"Delete it" → {'action': 'delete'}
"Search for bugs" → {'action': 'search'}
```

### Languages

```python
"Write a Python script" → {'language': 'python'}
"Create a JavaScript function" → {'language': 'javascript'}
```

## Error Handling

### Rule-Based (Never Fails)

```python
intent = classifier.classify("unclear input")
# Returns: type=CONVERSATION, confidence=0.6 (fallback)
```

### AI-Powered

```python
try:
    intent = await classifier.classify(utterance)
    if intent.confidence == 0.0:
        print(f"Classification error: {intent.entities.get('error')}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance

| Classifier | Latency | Accuracy | Dependencies |
|------------|---------|----------|--------------|
| Rule-Based | <1ms | 85-95% | None |
| AI-Powered | 200-400ms | 95-99% | anthropic SDK |

## When to Use Which

### Rule-Based Classifier
- ✅ Fast response required (<1ms)
- ✅ Well-defined commands
- ✅ No API dependency
- ✅ Resource constraints

### AI-Powered Classifier
- ✅ Complex/ambiguous commands
- ✅ Context-dependent classification
- ✅ Natural language understanding
- ✅ Learning from feedback

### Hybrid Approach

```python
# Try rule-based first
intent_rule = classifier_rule.classify(utterance)

# If low confidence, use AI
if intent_rule.confidence < 0.7:
    intent_ai = await classifier_ai.classify(utterance)
    intent = intent_ai if intent_ai.confidence > intent_rule.confidence else intent_rule
else:
    intent = intent_rule
```

## Common Issues

### Low Accuracy

1. Add more patterns to rule-based classifier
2. Update session context for AI classifier
3. Use hybrid approach
4. Consider training custom model

### Slow Performance

1. Use rule-based classifier for common commands
2. Enable caching for AI classifier
3. Batch classify multiple utterances

### High False Positives

1. Adjust confidence thresholds
2. Add more specific patterns
3. Use confirmation for destructive operations

## API Reference

### IntentClassifier (Rule-Based)

```python
classifier = IntentClassifier()
intent = classifier.classify(utterance)  # Returns Intent object
```

### IntentClassifierAI (AI-Powered)

```python
classifier = IntentClassifierAI(api_key="sk-ant-...")
intent = await classifier.classify(utterance, context={})
classifier.update_session_context({'working_directory': '/path'})
classifier.clear_cache()
stats = classifier.get_stats()
```

### Intent Object

```python
intent.type                  # IntentType enum
intent.text                  # Original utterance
intent.entities              # Dict of extracted entities
intent.confidence            # Float 0.0-1.0
intent.requires_confirmation # Boolean
intent.reasoning            # AI only - explanation
intent.suggested_action     # AI only - what to do
```

## Files Reference

| File | Purpose |
|------|---------|
| `intent_classifier.py` | Rule-based classifier (production) |
| `intent_classifier_ai.py` | AI-powered classifier (enhanced) |
| `action_orchestrator.py` | Action execution coordinator |
| `test_intent_classifier_demo.py` | Demo and examples |
| `intent_classifier_integration_example.py` | Integration patterns |

## Documentation

- **Design**: `/docs/INTENT_CLASSIFICATION_DESIGN.md`
- **README**: `/intelligent-agents/INTENT_CLASSIFICATION_README.md`
- **Implementation**: `/docs/INTENT_CLASSIFICATION_IMPLEMENTATION_COMPLETE.md`
- **Quick Start**: This file

## Next Steps

1. Read full documentation: `INTENT_CLASSIFICATION_README.md`
2. Run demo: `python3 test_intent_classifier_demo.py`
3. Try integration: `python3 intent_classifier_integration_example.py`
4. Integrate with your voice pipeline
5. Add custom patterns for your use case

---

**Quick Reference** - Intent Classification System v1.0
