#!/usr/bin/env python3
"""
Extract current Claude Code usage from session JSONL files

Reads the most recent session file and calculates cumulative usage
This provides an approximation but cannot give exact weekly totals
without access to Anthropic API
"""

import json
from pathlib import Path
from datetime import datetime

# Find most recent session file
sessions_dir = Path.home() / ".claude" / "projects" / "-home-marc"
session_files = list(sessions_dir.glob("*.jsonl"))

if not session_files:
    print("No session files found")
    exit(1)

# Get most recent session
latest_session = max(session_files, key=lambda p: p.stat().st_mtime)

# Parse session and sum usage
total_input = 0
total_output = 0
total_cache_creation = 0
total_cache_read = 0

with open(latest_session, 'r') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get('type') == 'assistant' and 'message' in entry:
                usage = entry['message'].get('usage', {})
                if usage:
                    total_input += usage.get('input_tokens', 0)
                    total_output += usage.get('output_tokens', 0)
                    total_cache_creation += usage.get('cache_creation_input_tokens', 0)
                    total_cache_read += usage.get('cache_read_input_tokens', 0)
        except json.JSONDecodeError:
            continue

# Calculate session context (toward 200k limit)
session_context = total_input + total_output + total_cache_creation
session_pct = int((session_context / 200000) * 100)

print(f"Session totals (current conversation):")
print(f"  Context tokens: {session_context:,} ({session_pct}% of 200k)")
print(f"  Cache reads: {total_cache_read:,}")
print()
print("NOTE: This is session cumulative, not weekly usage.")
print("For weekly usage, run /usage in Claude Code.")
