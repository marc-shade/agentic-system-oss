#!/usr/bin/env python3
"""
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
