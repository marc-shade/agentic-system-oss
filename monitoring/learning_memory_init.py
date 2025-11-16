#!/usr/bin/env python3
"""
Initialize Learning Memory
Creates the learning memory file with first entry
"""

import json
from datetime import datetime
from pathlib import Path

LEARNING_FILE = Path("/tmp/claude_learning_memory.jsonl")

def init_learning_memory():
    """Initialize learning memory with bootstrap entry"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "system_initialized",
        "improvements": ["Metrics collection started", "Learning memory initialized"],
        "patterns": {"initialization": True},
        "version": "1.0"
    }

    with LEARNING_FILE.open('a') as f:
        f.write(json.dumps(entry) + '\n')

    print(f"Learning memory initialized: {LEARNING_FILE}")

if __name__ == "__main__":
    init_learning_memory()
