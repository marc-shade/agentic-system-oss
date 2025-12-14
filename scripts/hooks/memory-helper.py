#!/usr/bin/env python3
"""
Memory Helper for Claude Code Hooks

Provides memory operations for session hooks:
- load_context: Load high-salience memories for session start
- save_session: Save session data and increment consolidation counter
- record_action: Record action outcomes for learning

Uses SQLite directly for speed since hooks need to be fast.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Database paths
MEMORY_DB = Path(os.environ.get("HOME", "/home/marc")) / ".claude" / "enhanced_memories" / "memory.db"
STATE_FILE = Path("/mnt/agentic-system/databases/consolidation_state.json")
CONTEXT_CACHE = Path("/tmp/claude_memory_context.json")


def get_db_connection():
    """Get SQLite connection with WAL mode."""
    if not MEMORY_DB.exists():
        return None
    conn = sqlite3.connect(str(MEMORY_DB), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def load_context(session_id: str = None) -> dict:
    """
    Load relevant context for a new session.
    Returns high-salience memories and recent episodes.
    """
    context = {
        "high_salience_memories": [],
        "recent_episodes": [],
        "active_goals": [],
        "loaded_at": datetime.now().isoformat()
    }

    conn = get_db_connection()
    if not conn:
        return context

    try:
        cursor = conn.cursor()

        # Get high-salience memories (from emotion tags)
        try:
            cursor.execute("""
                SELECT e.name, e.entity_type, et.salience_score, et.primary_emotion
                FROM emotion_tags et
                JOIN entities e ON et.entity_id = e.id
                WHERE et.salience_score >= 0.7
                ORDER BY et.salience_score DESC
                LIMIT 10
            """)
            context["high_salience_memories"] = [
                {"name": row["name"], "type": row["entity_type"],
                 "salience": row["salience_score"], "emotion": row["primary_emotion"]}
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            pass  # Table may not exist

        # Get recent significant episodes
        try:
            cursor.execute("""
                SELECT event_type, episode_data, significance_score, created_at
                FROM episodic_memory
                WHERE significance_score >= 0.6
                ORDER BY created_at DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                try:
                    data = json.loads(row["episode_data"]) if row["episode_data"] else {}
                    context["recent_episodes"].append({
                        "event_type": row["event_type"],
                        "significance": row["significance_score"],
                        "summary": data.get("summary", data.get("action", str(data)[:100]))
                    })
                except json.JSONDecodeError:
                    pass
        except sqlite3.OperationalError:
            pass

        # Cache context for quick access
        try:
            CONTEXT_CACHE.write_text(json.dumps(context, indent=2))
        except IOError:
            pass

    except Exception as e:
        context["error"] = str(e)
    finally:
        conn.close()

    return context


def save_session(session_id: str, session_data: dict = None) -> dict:
    """
    Save session data and increment consolidation counter.
    Called at session end.
    """
    result = {"success": False, "session_count": 0}

    # Increment consolidation counter
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
        else:
            state = {"session_count": 0, "last_consolidation": None}

        state["session_count"] = state.get("session_count", 0) + 1
        result["session_count"] = state["session_count"]

        STATE_FILE.write_text(json.dumps(state, indent=2))
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    # Record session end episode
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO episodic_memory
                (event_type, episode_data, significance_score, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                "session_end",
                json.dumps({
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    **(session_data or {})
                }),
                0.3,  # Low significance for routine session ends
                datetime.now().isoformat()
            ))
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Table may not exist
        finally:
            conn.close()

    return result


def record_action(tool_name: str, success_score: float, context: str = None) -> dict:
    """
    Record an action outcome for learning.
    Called from post-tool-use hook (sampled).
    """
    result = {"success": False}

    conn = get_db_connection()
    if not conn:
        return result

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO episodic_memory
            (event_type, episode_data, significance_score, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            "action_outcome",
            json.dumps({
                "tool": tool_name,
                "success_score": success_score,
                "context": context,
                "timestamp": datetime.now().isoformat()
            }),
            success_score * 0.5,  # Scale significance by success
            datetime.now().isoformat()
        ))
        conn.commit()
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        conn.close()

    return result


def main():
    """CLI interface for hook scripts."""
    if len(sys.argv) < 2:
        print("Usage: memory-helper.py <command> [args]")
        print("Commands: load_context, save_session, record_action")
        sys.exit(1)

    command = sys.argv[1]

    if command == "load_context":
        session_id = sys.argv[2] if len(sys.argv) > 2 else None
        result = load_context(session_id)
        print(json.dumps(result, indent=2))

    elif command == "save_session":
        session_id = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        result = save_session(session_id)
        print(json.dumps(result))

    elif command == "record_action":
        if len(sys.argv) < 4:
            print("Usage: memory-helper.py record_action <tool_name> <success_score> [context]")
            sys.exit(1)
        tool_name = sys.argv[2]
        success_score = float(sys.argv[3])
        context = sys.argv[4] if len(sys.argv) > 4 else None
        result = record_action(tool_name, success_score, context)
        print(json.dumps(result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
