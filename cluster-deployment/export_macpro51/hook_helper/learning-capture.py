#!/usr/bin/env python3
"""
Autonomous Skill Learning - Learning Moment Capture Hook

PostToolUse hook that identifies skill creation opportunities from conversation patterns.
Integrates with Jiminy Cricket behavioral scoring and enhanced-memory-mcp.
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
PET_STATE = Path.home() / ".claude" / "pets" / "claude-pet-state.json"
LEARNING_DB = Path.home() / ".claude" / "learning-patterns.db"
MIN_REPETITIONS = 3  # Minimum pattern occurrences before flagging

# Tool sequences that indicate repeated workflows
PATTERN_CACHE = defaultdict(list)


def init_db():
    """Initialize learning patterns database"""
    conn = sqlite3.connect(LEARNING_DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS patterns
                 (pattern_hash TEXT PRIMARY KEY,
                  tool_sequence TEXT,
                  context_summary TEXT,
                  occurrences INTEGER,
                  first_seen TEXT,
                  last_seen TEXT,
                  skill_recommended BOOLEAN,
                  skill_created BOOLEAN)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tool_events
                 (timestamp TEXT,
                  tool_name TEXT,
                  session_id TEXT,
                  pattern_hash TEXT)''')

    conn.commit()
    conn.close()


def get_pattern_hash(tool_sequence):
    """Generate hash for tool sequence pattern"""
    sequence_str = "->".join(tool_sequence)
    return hashlib.md5(sequence_str.encode()).hexdigest()[:16]


def detect_pattern(tool_name, session_id):
    """Detect if current tool usage is part of a repeated pattern"""
    # Read recent tool history from DB
    conn = sqlite3.connect(LEARNING_DB)
    c = conn.cursor()

    # Get last 10 tools in current session
    c.execute('''SELECT tool_name FROM tool_events
                 WHERE session_id = ?
                 ORDER BY timestamp DESC
                 LIMIT 10''', (session_id,))

    recent_tools = [row[0] for row in c.fetchall()]
    recent_tools.reverse()  # Chronological order
    recent_tools.append(tool_name)

    # Check for patterns of length 3-5
    patterns_found = []
    for length in range(3, min(6, len(recent_tools) + 1)):
        sequence = recent_tools[-length:]
        pattern_hash = get_pattern_hash(sequence)

        # Check if this pattern has occurred before
        c.execute('''SELECT occurrences, skill_recommended
                     FROM patterns
                     WHERE pattern_hash = ?''', (pattern_hash,))

        result = c.fetchone()
        if result:
            occurrences, skill_recommended = result
            if occurrences >= MIN_REPETITIONS and not skill_recommended:
                patterns_found.append({
                    "sequence": sequence,
                    "hash": pattern_hash,
                    "occurrences": occurrences + 1
                })

            # Update occurrence count
            c.execute('''UPDATE patterns
                         SET occurrences = occurrences + 1,
                             last_seen = ?
                         WHERE pattern_hash = ?''',
                      (datetime.now().isoformat(), pattern_hash))
        else:
            # New pattern
            c.execute('''INSERT INTO patterns
                         VALUES (?, ?, ?, 1, ?, ?, 0, 0)''',
                      (pattern_hash,
                       "->".join(sequence),
                       "",  # Context summary filled later
                       datetime.now().isoformat(),
                       datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return patterns_found


def recommend_skill(pattern):
    """Generate skill recommendation from detected pattern"""
    return {
        "type": "skill_opportunity",
        "pattern_hash": pattern["hash"],
        "tool_sequence": pattern["sequence"],
        "occurrences": pattern["occurrences"],
        "suggestion": f"Create skill for repeated workflow: {' → '.join(pattern['sequence'])}",
        "auto_name": f"workflow-{pattern['hash'][:8]}",
        "impact": "high" if pattern["occurrences"] >= 5 else "medium"
    }


def update_jiminy_learning_stats(opportunities_found):
    """Update Jiminy Cricket state with learning opportunities"""
    if not PET_STATE.exists():
        return

    with open(PET_STATE, 'r') as f:
        state = json.load(f)

    # Add learning tracking fields if not present
    if "skillsLearned" not in state:
        state["skillsLearned"] = 0
    if "learningMoments" not in state:
        state["learningMoments"] = 0
    if "skillOpportunities" not in state:
        state["skillOpportunities"] = []

    # Update learning moments count
    state["learningMoments"] += len(opportunities_found)

    # Add opportunities to queue
    for opp in opportunities_found:
        if opp not in state["skillOpportunities"]:
            state["skillOpportunities"].append(opp)

    # Boost behavior score for active learning
    if opportunities_found:
        state["claudeBehaviorScore"] = min(100, state.get("claudeBehaviorScore", 80) + 2)
        state["currentMood"] = "curious"

    with open(PET_STATE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    """PostToolUse hook entry point"""
    import sys

    # Read hook input from stdin
    hook_data = json.loads(sys.stdin.read())

    tool_name = hook_data.get("tool", {}).get("name", "")
    session_id = hook_data.get("sessionId", "default")

    if not tool_name:
        sys.exit(0)

    # Initialize database
    init_db()

    # Detect patterns BEFORE logging the current tool
    # (to avoid duplicate in sequence)
    patterns = detect_pattern(tool_name, session_id)

    # Log tool event
    conn = sqlite3.connect(LEARNING_DB)
    c = conn.cursor()
    c.execute('''INSERT INTO tool_events VALUES (?, ?, ?, ?)''',
              (datetime.now().isoformat(), tool_name, session_id, ""))
    conn.commit()
    conn.close()

    # Generate skill recommendations
    opportunities = [recommend_skill(p) for p in patterns]

    # Update Jiminy Cricket state
    if opportunities:
        update_jiminy_learning_stats(opportunities)

        # Output notification (only if chatty mode)
        print(json.dumps({
            "type": "learning_opportunity",
            "count": len(opportunities),
            "patterns": opportunities
        }))


if __name__ == "__main__":
    main()
