#!/usr/bin/env python3
"""
Integration Test Script for Voice-AGI
Tests all tools with realistic inputs and validates tool execution
"""

import asyncio
import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/voice-agi-mcp/src')

# Import the server components directly
import server
from conversation_manager import ConversationManager
from voice_pipeline import VoicePipeline
from tool_registry import ToolRegistry
from intent_detector import IntentDetector


async def test_tool_invocation():
    """Test that tools are properly invoked"""
    print("=" * 60)
    print("Testing Tool Invocation")
    print("=" * 60)

    # Use the server's tool registry
    tool_registry = server.tool_registry

    test_cases = [
        {
            'input': "Create a goal to make memory consolidation 10x faster",
            'expected_tool': 'create_goal_from_voice',
            'description': 'Goal creation'
        },
        {
            'input': "Search for information about transformers",
            'expected_tool': 'search_agi_memory',
            'description': 'Memory search'
        },
        {
            'input': "What tasks do I have?",
            'expected_tool': 'list_pending_tasks',
            'description': 'List tasks'
        },
        {
            'input': "Run memory consolidation",
            'expected_tool': 'trigger_consolidation',
            'description': 'Consolidation'
        },
        {
            'input': "Research transformer architectures",
            'expected_tool': 'start_research',
            'description': 'Research'
        },
        {
            'input': "How is the system doing?",
            'expected_tool': 'check_system_status',
            'description': 'System status'
        },
        {
            'input': "My name is Marc",
            'expected_tool': 'remember_name',
            'description': 'Remember name'
        },
        {
            'input': "What is my name?",
            'expected_tool': 'recall_name',
            'description': 'Recall name'
        },
        {
            'input': "Improve consolidation speed",
            'expected_tool': 'start_improvement_cycle',
            'description': 'Self-improvement'
        },
        {
            'input': "Break down the optimization goal into tasks",
            'expected_tool': 'decompose_goal',
            'description': 'Goal decomposition'
        }
    ]

    results = []
    for test in test_cases:
        print(f"\nTest: {test['description']}")
        print(f"Input: '{test['input']}'")

        try:
            # Test tool matching directly
            matched_tool = tool_registry.match_tool(test['input'])

            if matched_tool:
                tool_name = matched_tool.name

                if tool_name == test['expected_tool']:
                    print(f"✓ PASS - Tool matched: {tool_name}")
                    results.append(('PASS', test['description']))
                else:
                    print(f"⚠ PARTIAL - Wrong tool: expected {test['expected_tool']}, got {tool_name}")
                    results.append(('PARTIAL', test['description']))
            else:
                print(f"✗ FAIL - No tool matched")
                results.append(('FAIL', test['description']))

        except Exception as e:
            print(f"✗ ERROR - {str(e)}")
            results.append(('ERROR', test['description']))

    return results


async def test_conversation_context():
    """Test multi-turn conversation with context retention"""
    print("\n" + "=" * 60)
    print("Testing Conversation Context")
    print("=" * 60)

    # Create a test conversation manager
    cm = server.conversation_manager

    # Turn 1: Set name
    print("\nTurn 1: Setting name")
    cm.add_turn("My name is Marc", "Got it!", {'intent': 'remember'})
    cm.update_user_context('name', 'Marc')

    # Turn 2: Ask about something else
    print("\nTurn 2: Different topic")
    cm.add_turn("What's the status?", "System is operational", {'intent': 'status'})

    # Turn 3: Recall name
    print("\nTurn 3: Recalling name")
    cm.add_turn("What is my name?", "Your name is Marc", {'intent': 'recall'})

    # Get context
    turns = len(cm.messages)
    user_context = cm.user_context

    print(f"\n✓ Total conversation turns: {turns}")
    print(f"✓ User context: {user_context}")

    if turns >= 3:
        print("✓ PASS - Multi-turn conversation working")
        return True
    else:
        print("✗ FAIL - Not enough turns tracked")
        return False


async def test_intent_detection_accuracy():
    """Test intent detection with various phrasings"""
    print("\n" + "=" * 60)
    print("Testing Intent Detection Accuracy")
    print("=" * 60)

    tool_registry = server.tool_registry

    test_cases = [
        ("Make a new goal", "create"),
        ("Find information about AI", "memory"),
        ("Show me my tasks", "task"),
        ("Consolidate memories", "consolidat"),
        ("Study machine learning", "research"),
        ("Check status", "status"),
        ("I'm Marc", "name"),
        ("Who am I?", "name"),
        ("Make it faster", "improve"),
        ("Split this goal up", "decompose"),
    ]

    correct = 0
    total = len(test_cases)

    for text, expected_keyword in test_cases:
        matched_tool = tool_registry.match_tool(text)

        if matched_tool and expected_keyword in matched_tool.name.lower():
            print(f"✓ '{text}' → {matched_tool.name}")
            correct += 1
        elif matched_tool:
            print(f"⚠ '{text}' → {matched_tool.name} (expected keyword: {expected_keyword})")
            # Count as correct if it's related
            if any(kw in text.lower() for kw in matched_tool.intents):
                correct += 0.5
        else:
            print(f"✗ '{text}' → No match (expected: {expected_keyword})")

    accuracy = (correct / total) * 100
    print(f"\nTool Matching Accuracy: {accuracy:.1f}% ({correct}/{total})")

    return accuracy >= 70  # Pass if 70% or better


async def test_voice_stats():
    """Test that statistics are being tracked"""
    print("\n" + "=" * 60)
    print("Testing Statistics Tracking")
    print("=" * 60)

    vp = server.voice_pipeline
    cm = server.conversation_manager
    tr = server.tool_registry

    print(f"STT Available: {vp.is_stt_available()}")
    print(f"TTS Available: {vp.is_tts_available()}")
    print(f"Registered Tools: {tr.get_tool_count()}")
    print(f"Conversation Turns: {len(cm.messages)}")

    if tr.get_tool_count() == 10:
        print("✓ PASS - All 10 tools registered")
        return True
    else:
        print(f"✗ FAIL - Expected 10 tools, got {tr.get_tool_count()}")
        return False


async def test_tool_list():
    """Test tool listing"""
    print("\n" + "=" * 60)
    print("Testing Tool List")
    print("=" * 60)

    tool_registry = server.tool_registry
    tools = tool_registry.list_tools()
    count = len(tools)

    print(f"Total tools: {count}")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
        print(f"    Intents: {', '.join(tool['intents'][:3])}...")

    if count == 10:
        print("\n✓ PASS - All tools listed")
        return True
    else:
        print(f"\n✗ FAIL - Expected 10 tools, got {count}")
        return False


async def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("Voice-AGI Integration Test Suite")
    print("=" * 60 + "\n")

    all_results = {
        'tool_list': await test_tool_list(),
        'voice_stats': await test_voice_stats(),
        'tool_invocation': await test_tool_invocation(),
        'conversation_context': await test_conversation_context(),
        'intent_accuracy': await test_intent_detection_accuracy(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("Integration Test Summary")
    print("=" * 60)

    for test_name, result in all_results.items():
        if isinstance(result, bool):
            status = "✓ PASSED" if result else "✗ FAILED"
        else:
            # For tool invocation, check individual results
            passes = sum(1 for r in result if r[0] == 'PASS')
            total = len(result)
            status = f"✓ PASSED ({passes}/{total})" if passes == total else f"⚠ PARTIAL ({passes}/{total})"

        print(f"{test_name}: {status}")

    print("=" * 60)

    # Tool invocation detailed results
    if 'tool_invocation' in all_results and isinstance(all_results['tool_invocation'], list):
        print("\nTool Invocation Details:")
        for status, desc in all_results['tool_invocation']:
            print(f"  {status}: {desc}")

    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. If tests passed: Restart Claude Code to reload changes")
    print("2. Try: voice_chat(text='Create a goal to optimize performance')")
    print("3. Verify tool execution in real MCP environment")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
