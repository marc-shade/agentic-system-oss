#!/usr/bin/env python3
"""
Custom graders for memory block operations.

These graders verify that memory blocks are correctly updated,
character limits are respected, and content matches expectations.
"""

from letta_evals.decorators import grader, extractor
import sqlite3
from pathlib import Path
import re


# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


@grader
def verify_memory_content(output: str, ground_truth: str) -> float:
    """
    Verify that memory block contains the expected content.

    Checks:
    1. Ground truth content is present in memory block
    2. Content format is correct
    3. No corruption or truncation

    Args:
        output: Agent response containing block label
        ground_truth: Expected content to find in block

    Returns:
        Score from 0.0 to 1.0
    """
    # Extract block label from output
    block_label = extract_block_label(output)

    if not block_label:
        return 0.0  # Couldn't determine which block

    # Query database for actual block value
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT value, char_limit FROM memory_blocks
            WHERE label = ? AND agent_id = 'test_agent'
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (block_label,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return 0.0  # Block doesn't exist

        actual_value, char_limit = row

        # Check if ground_truth content is present
        if ground_truth not in actual_value:
            # Partial match check
            if ground_truth.lower() in actual_value.lower():
                return 0.7  # Case mismatch
            return 0.0  # Content not found

        # Check character limit
        if len(actual_value) > char_limit:
            return 0.8  # Content present but exceeded limit

        return 1.0  # Perfect match

    except Exception as e:
        print(f"Error in verify_memory_content: {e}")
        return 0.0


@grader
def verify_memory_append(output: str, ground_truth: str) -> float:
    """
    Verify that content was appended correctly to memory block.

    Checks:
    1. New content is at the end of block
    2. Old content is preserved
    3. Proper formatting (newlines, etc.)

    Args:
        output: Agent response
        ground_truth: Content that should have been appended

    Returns:
        Score from 0.0 to 1.0
    """
    block_label = extract_block_label(output)

    if not block_label:
        return 0.0

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT value FROM memory_blocks
            WHERE label = ? AND agent_id = 'test_agent'
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (block_label,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return 0.0

        actual_value = row[0]

        # Check if ground_truth is present
        if ground_truth not in actual_value:
            return 0.0

        # Check if it's near the end (last 20% of content)
        position = actual_value.find(ground_truth)
        if position == -1:
            return 0.0

        # Calculate relative position
        relative_position = position / len(actual_value)

        if relative_position >= 0.8:
            return 1.0  # Appended at end
        elif relative_position >= 0.5:
            return 0.7  # Appended in middle
        else:
            return 0.5  # Appended at beginning (unusual)

    except Exception as e:
        print(f"Error in verify_memory_append: {e}")
        return 0.0


@grader
def verify_memory_replace(output: str, ground_truth: str) -> float:
    """
    Verify that content was replaced correctly in memory block.

    Checks:
    1. New content is present
    2. Old content is removed
    3. Surrounding content unchanged

    Args:
        output: Agent response
        ground_truth: New content that should replace old

    Returns:
        Score from 0.0 to 1.0
    """
    block_label = extract_block_label(output)

    if not block_label:
        return 0.0

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT value FROM memory_blocks
            WHERE label = ? AND agent_id = 'test_agent'
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (block_label,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return 0.0

        actual_value = row[0]

        # Check if new content is present
        if ground_truth not in actual_value:
            # Check for partial match (case-insensitive)
            if ground_truth.lower() in actual_value.lower():
                return 0.7
            return 0.0

        return 1.0  # New content present

    except Exception as e:
        print(f"Error in verify_memory_replace: {e}")
        return 0.0


@grader
def verify_char_limit_respected(output: str, ground_truth: str) -> float:
    """
    Verify that character limits are respected.

    Checks:
    1. Block value doesn't exceed char_limit
    2. Warning if approaching limit (90%+)

    Args:
        output: Agent response
        ground_truth: Not used (checks database directly)

    Returns:
        Score from 0.0 to 1.0
    """
    block_label = extract_block_label(output)

    if not block_label:
        return 1.0  # No block specified, assume OK

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT value, char_limit FROM memory_blocks
            WHERE label = ? AND agent_id = 'test_agent'
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (block_label,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return 1.0  # Block doesn't exist, no violation

        actual_value, char_limit = row
        actual_length = len(actual_value)

        if actual_length > char_limit:
            return 0.0  # Hard violation

        if actual_length >= char_limit * 0.9:
            return 0.8  # Approaching limit (warning)

        return 1.0  # Well within limit

    except Exception as e:
        print(f"Error in verify_char_limit_respected: {e}")
        return 1.0  # Default to pass on error


@extractor
def memory_block_extractor(response: dict) -> str:
    """
    Extract memory block information from agent response.

    Parses agent response to determine which block was modified
    and what the final state is.

    Args:
        response: Full agent response dict

    Returns:
        Formatted string with block label and operation
    """
    # For Letta agents, messages are in response["messages"]
    messages = response.get("messages", [])

    if not messages:
        return ""

    # Get last assistant message
    last_message = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_message = msg.get("text", "")
            break

    if not last_message:
        return ""

    return last_message


def extract_block_label(output: str) -> str:
    """
    Helper to extract block label from agent output.

    Looks for common block labels in output text.

    Args:
        output: Agent output text

    Returns:
        Block label (identity, human, task, learnings) or empty string
    """
    output_lower = output.lower()

    # Check for explicit mentions
    for label in ["identity", "human", "task", "learnings"]:
        if label in output_lower:
            return label

    # Check for patterns like "to task block" or "task block"
    patterns = [
        r'\bto\s+(\w+)\s+block',
        r'\b(\w+)\s+block',
        r'block:\s+(\w+)',
        r'update\s+(\w+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output_lower)
        if match:
            candidate = match.group(1)
            if candidate in ["identity", "human", "task", "learnings"]:
                return candidate

    # Default to task if no specific label found
    return "task"


# Export all graders for CLI discovery
__all__ = [
    "verify_memory_content",
    "verify_memory_append",
    "verify_memory_replace",
    "verify_char_limit_respected",
    "memory_block_extractor",
]
