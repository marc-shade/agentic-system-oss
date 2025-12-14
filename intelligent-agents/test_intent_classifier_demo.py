#!/usr/bin/env python3
"""
Intent Classifier Demo - Shows usage without requiring API key

This demonstrates the intent classifier's structure and API without making actual API calls.
"""
import os
import platform
from pathlib import Path

import json
from intent_classifier import Intent, IntentClassifier

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()



def demo_intent_structure():
    """Demonstrate Intent object structure"""
    print("=" * 80)
    print("Intent Classification System - Demo")
    print("=" * 80)

    # Create example intents
    examples = [
        Intent(
            type="COMMAND",
            entities={
                "file_path": ["auth.py"],
                "operation": "fix",
                "target": "bug"
            },
            confidence=0.95,
            original_utterance="fix the bug in auth.py",
            reasoning="User is requesting a code fix operation on a specific file",
            suggested_action="Open auth.py and analyze for bugs to fix"
        ),
        Intent(
            type="QUERY",
            entities={
                "function_name": ["login"],
                "operation": "explain"
            },
            confidence=0.92,
            original_utterance="what does the login function do?",
            reasoning="User is asking for explanation of a specific function",
            suggested_action="Retrieve login function definition and explain its purpose"
        ),
        Intent(
            type="CONVERSATION",
            entities={
                "confirmation": "yes",
                "sentiment": "positive"
            },
            confidence=0.98,
            original_utterance="yes, that looks correct",
            reasoning="User is providing positive confirmation",
            suggested_action="Proceed with the previously suggested action"
        ),
        Intent(
            type="QUERY",
            entities={
                "git_operation": "commits",
                "timeframe": "recent",
                "count": 10
            },
            confidence=0.90,
            original_utterance="show me recent git commits",
            reasoning="User wants to see git commit history",
            suggested_action="Execute 'git log -10 --oneline' and display results"
        ),
        Intent(
            type="META",
            entities={
                "control_action": "pause"
            },
            confidence=0.99,
            original_utterance="pause",
            reasoning="User wants to pause current operation",
            suggested_action="Pause current execution and wait for resume command"
        )
    ]

    # Display each example
    for i, intent in enumerate(examples, 1):
        print(f"\n{'─' * 80}")
        print(f"Example {i}: {intent.type}")
        print(f"{'─' * 80}")
        print(f"Utterance: \"{intent.original_utterance}\"")
        print(f"\nClassification:")
        print(f"  Type: {intent.type}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"\nExtracted Entities:")
        for key, value in intent.entities.items():
            print(f"  {key}: {value}")
        print(f"\nReasoning: {intent.reasoning}")
        print(f"Suggested Action: {intent.suggested_action}")

        # Show JSON representation
        print(f"\nJSON Representation:")
        print(json.dumps(intent.to_dict(), indent=2))


def demo_classifier_api():
    """Demonstrate classifier API structure"""
    print("\n" + "=" * 80)
    print("Classifier API Overview")
    print("=" * 80)

    api_info = """
## Initialization

```python
from intent_classifier import IntentClassifier

classifier = IntentClassifier(
    api_key="sk-ant-...",  # Or set ANTHROPIC_API_KEY env var
    model="claude-sonnet-4-5-20250929",
    max_tokens=512,
    temperature=0.0  # Deterministic classification
)
```

## Basic Classification

```python
import asyncio

async def classify_utterance():
    # Classify a voice command
    intent = await classifier.classify("fix the bug in auth.py")

    print(f"Type: {intent.type}")
    print(f"Confidence: {intent.confidence}")
    print(f"Entities: {intent.entities}")
    print(f"Action: {intent.suggested_action}")

asyncio.run(classify_utterance())
```

## With Context

```python
# Update session context
classifier.update_session_context({
    "working_directory": str(_STORAGE_BASE),
    "open_files": ["auth.py", "db.py"],
    "active_branch": "feature/voice-commands"
})

# Classify with context
intent = await classifier.classify(
    utterance="commit these changes",
    context={"last_operation": "file_edit"}
)
```

## Entity Extraction

Entities are automatically extracted based on intent type:

- **COMMAND**: file_path, operation, target, function_name, git_operation
- **QUERY**: function_name, service_name, timeframe, resource_type
- **CONVERSATION**: confirmation, sentiment, acknowledgment
- **META**: control_action, preference, help_request

## Cache and Context Management

```python
# Get classifier statistics
stats = classifier.get_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Intent distribution: {stats['intent_type_distribution']}")

# Clear cache if needed
classifier.clear_cache()

# Clear conversation context
classifier.clear_context()
```

## Integration with Voice Mode

```python
from voice_mode import listen, speak
from intent_classifier import IntentClassifier

async def voice_command_loop():
    classifier = IntentClassifier()

    while True:
        # Listen to user
        audio = await listen(duration=5)
        utterance = audio['text']

        # Classify intent
        intent = await classifier.classify(utterance)

        # Execute based on intent
        if intent.type == "COMMAND":
            await execute_command(intent)
        elif intent.type == "QUERY":
            result = await execute_query(intent)
            await speak(result)
        elif intent.type == "CONVERSATION":
            await handle_conversation(intent)
        elif intent.type == "META":
            await handle_meta_command(intent)
```

## Error Handling

```python
try:
    intent = await classifier.classify(utterance)

    if intent.confidence < 0.6:
        # Low confidence - ask for clarification
        await speak("I'm not sure I understood. Can you rephrase that?")
    else:
        # Proceed with action
        await execute_intent(intent)

except Exception as e:
    logger.error(f"Classification failed: {e}")
    await speak("I encountered an error. Please try again.")
```
"""

    print(api_info)


def demo_test_cases():
    """Show comprehensive test cases"""
    print("\n" + "=" * 80)
    print("Test Cases and Expected Outcomes")
    print("=" * 80)

    test_cases = [
        {
            "category": "COMMAND - File Operations",
            "cases": [
                "fix the bug in auth.py",
                "create a new database schema",
                "refactor the login function",
                "add error handling to the API",
                "delete the temporary files"
            ]
        },
        {
            "category": "COMMAND - Git Operations",
            "cases": [
                "commit these changes",
                "create a new branch called feature-voice",
                "merge the develop branch",
                "push to origin",
                "revert the last commit"
            ]
        },
        {
            "category": "COMMAND - System Operations",
            "cases": [
                "restart Redis",
                "deploy to production",
                "scale up the API service",
                "stop the monitoring daemon",
                "backup the database"
            ]
        },
        {
            "category": "QUERY - Code Inspection",
            "cases": [
                "what does the login function do?",
                "show me the database schema",
                "explain the authentication flow",
                "how many functions are in auth.py?",
                "what imports does this module use?"
            ]
        },
        {
            "category": "QUERY - System Status",
            "cases": [
                "is Redis running?",
                "check memory usage",
                "show active connections",
                "what's the CPU load?",
                "list running services"
            ]
        },
        {
            "category": "QUERY - Git History",
            "cases": [
                "show me recent git commits",
                "who changed this file?",
                "what branch am I on?",
                "show uncommitted changes",
                "list all branches"
            ]
        },
        {
            "category": "CONVERSATION - Confirmations",
            "cases": [
                "yes",
                "that looks correct",
                "no, try something else",
                "maybe",
                "I'm not sure"
            ]
        },
        {
            "category": "CONVERSATION - Acknowledgments",
            "cases": [
                "okay",
                "thanks",
                "got it",
                "I understand",
                "that worked"
            ]
        },
        {
            "category": "META - Session Control",
            "cases": [
                "pause",
                "stop",
                "continue",
                "undo",
                "repeat that"
            ]
        },
        {
            "category": "META - Preferences",
            "cases": [
                "speak faster",
                "use more detail",
                "summarize",
                "switch to verbose mode",
                "reduce output"
            ]
        },
        {
            "category": "META - Help",
            "cases": [
                "what can you do?",
                "help",
                "list commands",
                "show me examples",
                "how do I use this?"
            ]
        }
    ]

    for category_info in test_cases:
        print(f"\n{category_info['category']}")
        print("─" * 80)
        for case in category_info['cases']:
            print(f"  • \"{case}\"")


if __name__ == "__main__":
    # Run demo
    demo_intent_structure()
    demo_classifier_api()
    demo_test_cases()

    print("\n" + "=" * 80)
    print("Demo Complete")
    print("=" * 80)
    print("\nTo run actual classification tests:")
    print("1. Set ANTHROPIC_API_KEY environment variable")
    print("2. Run: python3 intent_classifier.py")
    print("\nFor integration:")
    print("1. Import: from intent_classifier import IntentClassifier, Intent")
    print("2. Initialize: classifier = IntentClassifier()")
    print("3. Classify: intent = await classifier.classify(utterance)")
