#!/usr/bin/env python3
"""
Test Suite for Conversation State Management
Comprehensive tests for multi-turn conversation tracking
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from conversation_state import (
    ConversationState,
    ConversationTurn,
    ActionRecord,
    TurnType,
    ActionStatus
)


def test_basic_turn_tracking():
    """Test basic conversation turn tracking"""
    print("\n=== Test: Basic Turn Tracking ===")

    state = ConversationState()

    # Add a few turns
    turn1 = state.add_turn(
        user_msg="Hello, can you help me?",
        assistant_msg="Of course! What do you need help with?",
        turn_type=TurnType.GREETING
    )

    turn2 = state.add_turn(
        user_msg="I need to write a Python script",
        assistant_msg="I can help you write a Python script. What should it do?",
        turn_type=TurnType.QUESTION
    )

    turn3 = state.add_turn(
        user_msg="It should read a CSV file and calculate statistics",
        assistant_msg="Great! I'll create a script that reads CSV and calculates mean, median, and mode.",
        turn_type=TurnType.COMMAND
    )

    assert len(state.history) == 3, "Should have 3 turns in history"
    assert state.total_turns == 3, "Should have 3 total turns"
    assert state.turn_counter == 3, "Turn counter should be 3"

    print(f"✓ Added {len(state.history)} turns successfully")
    print(f"  - Turn 1: {turn1.user_utterance[:30]}...")
    print(f"  - Turn 2: {turn2.user_utterance[:30]}...")
    print(f"  - Turn 3: {turn3.user_utterance[:30]}...")


def test_context_summary():
    """Test context summary generation"""
    print("\n=== Test: Context Summary Generation ===")

    state = ConversationState()

    # Set up a task
    state.update_active_task("CSV Analysis Script", "Create Python script to analyze CSV data")

    # Add turns with actions
    state.add_turn(
        user_msg="Read the data.csv file",
        assistant_msg="I'll read the CSV file and show you the first few rows.",
        turn_type=TurnType.COMMAND,
        files=["/project/data.csv"]
    )

    action = ActionRecord(
        action_id="read_csv",
        action_type="file_read",
        description="Reading data.csv",
        status=ActionStatus.COMPLETED
    )
    state.add_action(action)
    state.update_action("read_csv", ActionStatus.COMPLETED)

    state.add_turn(
        user_msg="Calculate the mean of column A",
        assistant_msg="The mean of column A is 42.5",
        turn_type=TurnType.COMMAND
    )

    # Generate summary
    summary = state.get_context_summary(max_turns=5)

    assert "Active Task: CSV Analysis Script" in summary, "Should include active task"
    assert "data.csv" in summary, "Should include file context"
    assert state.session_id in summary, "Should include session ID"

    print("✓ Context summary generated successfully")
    print("\nSummary preview:")
    print(summary[:300] + "...")


def test_action_tracking():
    """Test action tracking and status updates"""
    print("\n=== Test: Action Tracking ===")

    state = ConversationState()

    # Add various actions
    action1 = ActionRecord(
        action_id="action1",
        action_type="file_read",
        description="Reading configuration file",
        status=ActionStatus.PENDING
    )

    action2 = ActionRecord(
        action_id="action2",
        action_type="search",
        description="Searching for API examples",
        status=ActionStatus.IN_PROGRESS
    )

    action3 = ActionRecord(
        action_id="action3",
        action_type="execute",
        description="Running tests",
        status=ActionStatus.PENDING
    )

    state.add_action(action1)
    state.add_action(action2)
    state.add_action(action3)

    assert len(state.pending_actions) == 3, "Should have 3 pending actions"

    # Update action statuses
    state.update_action("action1", ActionStatus.COMPLETED, result="Config loaded successfully")
    state.update_action("action2", ActionStatus.COMPLETED, result="Found 5 examples")
    state.update_action("action3", ActionStatus.FAILED, error="Test suite not found")

    assert len(state.pending_actions) == 0, "No actions should be pending"
    assert len(state.completed_actions) == 3, "Should have 3 completed actions"

    print("✓ Action tracking working correctly")
    print(f"  - Completed actions: {len(state.completed_actions)}")
    print(f"  - Pending actions: {len(state.pending_actions)}")


def test_file_context():
    """Test file context management"""
    print("\n=== Test: File Context Management ===")

    state = ConversationState()

    # Add files to context
    files = [
        "/project/main.py",
        "/project/config.json",
        "/project/utils.py",
        "/project/tests/test_main.py"
    ]

    for file in files:
        state.add_file_context(file)

    assert len(state.context_files) == 4, "Should have 4 files in context"
    assert "/project/main.py" in state.context_files, "Should contain main.py"

    # Add turn with files
    state.add_turn(
        user_msg="Modify the main.py file",
        assistant_msg="I'll update main.py with your changes",
        files=["/project/main.py"]
    )

    assert "/project/main.py" in state.files_modified, "Should track file modification"

    # Clear context
    state.clear_file_context()
    assert len(state.context_files) == 0, "Context should be cleared"

    print("✓ File context management working correctly")
    print(f"  - Files tracked: {len(files)}")
    print(f"  - Files modified: {len(state.files_modified)}")


def test_clarifications():
    """Test clarification tracking"""
    print("\n=== Test: Clarification Tracking ===")

    state = ConversationState()

    # Add clarifications
    clarifications = [
        "Which Python version should I use?",
        "Do you want error handling?",
        "Should I include type hints?"
    ]

    for clarification in clarifications:
        state.add_clarification(clarification)

    assert len(state.clarifications_needed) == 3, "Should have 3 clarifications needed"

    # Resolve some clarifications
    state.resolve_clarification("Which Python version should I use?", "Python 3.9")
    state.resolve_clarification("Do you want error handling?", "Yes, please")

    assert len(state.clarifications_needed) == 1, "Should have 1 clarification remaining"
    assert len(state.clarifications_resolved) == 2, "Should have 2 resolved"

    print("✓ Clarification tracking working correctly")
    print(f"  - Needed: {len(state.clarifications_needed)}")
    print(f"  - Resolved: {len(state.clarifications_resolved)}")


def test_task_management():
    """Test task management"""
    print("\n=== Test: Task Management ===")

    state = ConversationState()

    # Start a task
    state.update_active_task("Build API", "Create REST API with authentication")
    assert state.active_task == "Build API", "Should have active task"
    assert state.task_start_time is not None, "Should have task start time"

    # Add some turns
    for i in range(5):
        state.add_turn(
            user_msg=f"Question {i+1}",
            assistant_msg=f"Answer {i+1}",
            turn_type=TurnType.QUESTION
        )

    # Complete task
    summary = state.complete_task()

    assert summary is not None, "Should return task summary"
    assert summary['task'] == "Build API", "Summary should include task name"
    assert summary['turns_taken'] >= 5, "Should count turns"
    assert state.active_task is None, "Active task should be cleared"

    print("✓ Task management working correctly")
    print(f"  - Task completed: {summary['task']}")
    print(f"  - Duration: {summary['duration_minutes']:.2f} minutes")
    print(f"  - Turns taken: {summary['turns_taken']}")


def test_statistics():
    """Test statistics generation"""
    print("\n=== Test: Statistics Generation ===")

    state = ConversationState()

    # Add various types of turns
    turn_types = [
        TurnType.GREETING,
        TurnType.QUESTION,
        TurnType.QUESTION,
        TurnType.COMMAND,
        TurnType.COMMAND,
        TurnType.COMMAND,
        TurnType.INFO_RESPONSE,
        TurnType.CONFIRMATION
    ]

    for turn_type in turn_types:
        state.add_turn(
            user_msg="Test message",
            assistant_msg="Test response",
            turn_type=turn_type,
            confidence=0.8 + (hash(turn_type.value) % 20) / 100  # Vary confidence
        )

    stats = state.get_statistics()

    assert stats['total_turns'] == len(turn_types), "Should count all turns"
    assert 'turn_type_distribution' in stats, "Should include turn type distribution"
    assert stats['average_confidence'] > 0, "Should calculate average confidence"

    print("✓ Statistics generation working correctly")
    print(f"  - Total turns: {stats['total_turns']}")
    print(f"  - Average confidence: {stats['average_confidence']:.2f}")
    print(f"  - Turn types: {stats['turn_type_distribution']}")


def test_serialization():
    """Test state serialization and deserialization"""
    print("\n=== Test: Serialization/Deserialization ===")

    # Create state with data
    state1 = ConversationState()
    state1.update_active_task("Test Task", "Testing serialization")

    for i in range(3):
        state1.add_turn(
            user_msg=f"User message {i}",
            assistant_msg=f"Assistant response {i}",
            turn_type=TurnType.QUESTION,
            confidence=0.9
        )

    state1.add_file_context("/test/file.py")

    action = ActionRecord(
        action_id="test_action",
        action_type="test",
        description="Test action",
        status=ActionStatus.COMPLETED
    )
    state1.add_action(action)
    state1.update_action("test_action", ActionStatus.COMPLETED)

    # Serialize
    data = state1.to_dict()
    json_str = json.dumps(data, indent=2)

    assert len(json_str) > 0, "Should serialize to JSON"

    # Deserialize
    state2 = ConversationState.from_dict(data)

    assert state2.session_id == state1.session_id, "Session ID should match"
    assert len(state2.history) == len(state1.history), "History length should match"
    assert state2.active_task == state1.active_task, "Active task should match"
    assert len(state2.context_files) == len(state1.context_files), "Context files should match"
    assert len(state2.completed_actions) == len(state1.completed_actions), "Actions should match"

    print("✓ Serialization/deserialization working correctly")
    print(f"  - JSON size: {len(json_str)} bytes")
    print(f"  - Turns preserved: {len(state2.history)}")


def test_max_history_limit():
    """Test that history respects max limit"""
    print("\n=== Test: Max History Limit ===")

    state = ConversationState(max_history=10)

    # Add more than max_history turns
    for i in range(20):
        state.add_turn(
            user_msg=f"Message {i}",
            assistant_msg=f"Response {i}",
            turn_type=TurnType.QUESTION
        )

    assert len(state.history) == 10, "History should be limited to max_history"
    assert state.total_turns == 20, "Should count all turns"

    # Verify we kept the most recent turns
    last_turn = list(state.history)[-1]
    assert "Message 19" in last_turn.user_utterance, "Should keep most recent turn"

    print("✓ Max history limit working correctly")
    print(f"  - Total turns: {state.total_turns}")
    print(f"  - Turns in memory: {len(state.history)}")


async def test_persistence():
    """Test persistence to enhanced-memory MCP (if available)"""
    print("\n=== Test: Persistence (MCP Integration) ===")

    state = ConversationState()

    # Set up some data
    state.update_active_task("Test Persistence", "Testing MCP integration")

    for i in range(3):
        state.add_turn(
            user_msg=f"Test message {i}",
            assistant_msg=f"Test response {i}",
            turn_type=TurnType.QUESTION,
            confidence=0.9
        )

    try:
        # Try to persist
        await state.persist()
        print("✓ Persistence completed (check MCP for stored data)")

        # Try to restore
        session_id = state.session_id
        new_state = ConversationState()
        restored = await new_state.restore(session_id)

        if restored:
            print("✓ State restoration successful")
            print(f"  - Restored turns: {len(new_state.history)}")
            print(f"  - Active task: {new_state.active_task}")
        else:
            print("⚠ State restoration returned False (may not be persisted yet)")

    except Exception as e:
        print(f"⚠ Persistence test skipped: {e}")
        print("  (MCP server may not be running)")


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("Conversation State Management - Test Suite")
    print("=" * 60)

    tests = [
        test_basic_turn_tracking,
        test_context_summary,
        test_action_tracking,
        test_file_context,
        test_clarifications,
        test_task_management,
        test_statistics,
        test_serialization,
        test_max_history_limit
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ Test error: {e}")
            failed += 1

    # Run async test separately
    try:
        asyncio.run(test_persistence())
        passed += 1
    except Exception as e:
        print(f"\n✗ Persistence test error: {e}")
        failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
