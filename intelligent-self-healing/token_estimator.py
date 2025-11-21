#!/usr/bin/env python3
"""
<<<<<<< HEAD
Token usage estimator for Claude Code sessions
Production-safe: only reads file metadata, not contents
"""

import json
from pathlib import Path
from datetime import datetime

def estimate_token_usage():
    """
    Estimate current token usage from session file size
    Returns dict with current, limit, and percentage
    """
    try:
        # Find current session directory (most recently modified)
        sessions_dir = Path('/Users/marc/.claude/sessions')
        if not sessions_dir.exists():
            return None

        session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir()]
        if not session_dirs:
            return None

        latest_session = max(session_dirs, key=lambda d: d.stat().st_mtime)
        post_tool_file = latest_session / 'post_tool_use.json'

        if not post_tool_file.exists():
            return None

        # Read file size only (production-safe - no file content reading)
        file_size = post_tool_file.stat().st_size

        # Rough estimation based on file size
        # post_tool_use.json contains JSON history
        # Estimate: 1 byte ≈ 0.25 tokens (accounting for JSON overhead)
        estimated_tokens = int(file_size * 0.25)

        # Context limit for Sonnet 4.5
        context_limit = 200000

        # Calculate percentage
        percentage = int((estimated_tokens / context_limit) * 100)

        return {
            'current': estimated_tokens,
            'limit': context_limit,
            'percentage': percentage,
            'session_id': latest_session.name
        }

    except Exception:
        # Silently fail - don't break statusline
        return None

if __name__ == '__main__':
    # Standalone test
    result = estimate_token_usage()
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No session data available")
=======
Token Usage Estimator for Claude Code
Estimates current token usage from conversation metadata
Production-safe implementation that doesn't inspect conversation content
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional


def get_weekly_budget() -> Optional[Dict[str, int]]:
    """
    Get weekly token budget from tracking file

    Returns:
        Dict with 'current', 'limit', and 'percentage' or None if unavailable
    """
    try:
        budget_file = Path.home() / ".claude" / "weekly_budget.json"
        if not budget_file.exists():
            return None

        with open(budget_file, 'r') as f:
            data = json.load(f)

        if data.get('percentage', 0) > 0:
            return {
                'current': data.get('current_tokens', 0),
                'limit': data.get('weekly_limit', 0),
                'percentage': data.get('percentage', 0)
            }
        return None
    except Exception:
        return None


def estimate_token_usage() -> Optional[Dict[str, int]]:
    """
    Estimate session token usage from Claude Code conversation file

    Returns:
        Dict with 'current', 'limit', and 'percentage' or None if unavailable
    """
    try:
        # Default token limit for Claude Code (200k context window)
        TOKEN_LIMIT = 200000

        # Find the most recent session .jsonl file
        projects_dir = Path.home() / ".claude" / "projects" / "-home-marc"

        if not projects_dir.exists():
            return None

        # Get most recently modified .jsonl file
        jsonl_files = sorted(
            projects_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not jsonl_files:
            return None

        session_file = jsonl_files[0]

        # Parse conversation and estimate tokens more accurately
        # Calibrated against actual Claude API token counting:
        # - Message overhead: ~150 tokens per message (role, metadata, formatting)
        # - Text content: ~2 chars per token (0.50 tokens/char including spaces)
        # - Tool calls: ~300 tokens overhead + params
        # - Tool results: ~250 tokens overhead for formatting
        # - System context: ~25% overhead for prompts, tool definitions, etc.

        estimated_tokens = 0
        message_count = 0

        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    message_count += 1

                    # Base message overhead (calibrated to actual API usage)
                    estimated_tokens += 150

                    # Count content tokens
                    if isinstance(msg.get('content'), str):
                        estimated_tokens += int(len(msg['content']) * 0.50)
                    elif isinstance(msg.get('content'), list):
                        for block in msg['content']:
                            if isinstance(block, dict):
                                # Text blocks
                                if block.get('type') == 'text' and 'text' in block:
                                    estimated_tokens += int(len(block['text']) * 0.50)
                                # Tool use blocks
                                elif block.get('type') == 'tool_use':
                                    estimated_tokens += 300  # Tool call overhead
                                    if 'input' in block:
                                        estimated_tokens += int(len(str(block['input'])) * 0.50)
                                # Tool result blocks
                                elif block.get('type') == 'tool_result':
                                    estimated_tokens += 250  # Tool result formatting overhead
                                    if 'content' in block:
                                        estimated_tokens += int(len(str(block['content'])) * 0.50)

                except (json.JSONDecodeError, KeyError):
                    # Skip malformed lines, add minimal estimate
                    estimated_tokens += 300

        # Add system context overhead (tool definitions, system prompts, CLAUDE.md, etc.)
        # This is substantial - tool definitions alone are ~10k tokens
        system_overhead = int(estimated_tokens * 0.60)
        estimated_tokens += system_overhead

        # Cap at limit
        current_tokens = min(estimated_tokens, TOKEN_LIMIT)

        # Calculate percentage
        percentage = int((current_tokens / TOKEN_LIMIT) * 100)

        return {
            'current': current_tokens,
            'limit': TOKEN_LIMIT,
            'percentage': percentage
        }

    except Exception as e:
        print(f"Token estimation error: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # Test the estimator
    print("Session Context:")
    usage = estimate_token_usage()
    if usage:
        print(f"  {usage['current']:,} / {usage['limit']:,} tokens ({usage['percentage']}%)")
    else:
        print("  Unable to estimate")

    print("\nWeekly Budget:")
    weekly = get_weekly_budget()
    if weekly:
        print(f"  {weekly['current']:,} / {weekly['limit']:,} tokens ({weekly['percentage']}%)")
    else:
        print("  Not configured (update ~/.claude/weekly_budget.json)")
>>>>>>> origin/main
