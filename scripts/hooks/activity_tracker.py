#!/usr/bin/env python3
"""
AGI Activity Tracker - Intelligent Session & Memory Activity System
====================================================================

This module provides real-time activity tracking that:
1. Updates memory system timestamps for statusline awareness
2. Records tool usage patterns as episodic memories
3. Tracks session context for cross-session learning
4. Feeds action patterns into AGI meta-learning system
5. Enables pattern detection for self-improvement

Part of the AGI Development System - Building toward artificial general intelligence
through continuous learning and systematic capability enhancement.
"""

import json
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib

# TPU importance scoring (optional, graceful degradation)
try:
    from tpu_importance import score_importance, score_action_outcome, is_tpu_available
    _HAS_TPU_SCORING = is_tpu_available()
except ImportError:
    _HAS_TPU_SCORING = False
    def score_importance(text, context="memory"): return 0.5
    def score_action_outcome(tool, success, out_len, time_ms, ctx=None): return 0.5

# Memory database locations
MEMORY_DB_PATHS = [
    Path("/mnt/agentic-system/.claude/enhanced_memories/memory.db"),
    Path.home() / ".claude" / "enhanced_memories" / "memory.db"
]

# Activity log for pattern analysis
ACTIVITY_LOG = Path("/mnt/agentic-system/logs/agi-activity.jsonl")

# Session tracking
SESSION_FILE = Path("/tmp/claude_session_activity.json")


class AGIActivityTracker:
    """
    Intelligent activity tracker for AGI system awareness.

    Integrates with:
    - Enhanced Memory System (timestamps, episodic storage)
    - AGI Meta-Learning (pattern detection)
    - Session Continuity (cross-session context)
    - Statusline (real-time activity display)
    """

    def __init__(self):
        self.memory_db = self._find_memory_db()
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
        self.node_id = os.uname().nodename

    def _find_memory_db(self) -> Optional[Path]:
        """Find the active memory database."""
        for path in MEMORY_DB_PATHS:
            if path.exists():
                return path
        return None

    def _get_db_connection(self) -> Optional[sqlite3.Connection]:
        """Get database connection with proper settings."""
        if not self.memory_db:
            return None
        try:
            conn = sqlite3.connect(str(self.memory_db), timeout=5)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None

    def update_session_activity(self, tool_name: str, context: Dict[str, Any] = None) -> bool:
        """
        Update session activity in memory system.

        This is the core function that:
        1. Updates/creates a session_activity entity with current timestamp
        2. Records tool usage pattern
        3. Maintains session continuity
        """
        conn = self._get_db_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Entity name for current session activity
            activity_entity = f"session_activity_{self.session_id}"

            # Check if session activity entity exists
            cursor.execute(
                "SELECT id FROM entities WHERE name = ?",
                (activity_entity,)
            )
            existing = cursor.fetchone()

            # Prepare activity data
            activity_data = {
                "session_id": self.session_id,
                "node": self.node_id,
                "last_tool": tool_name,
                "last_activity": now,
                "tool_count": 1,
                "context": context or {}
            }

            if existing:
                # Update existing session activity
                # First get current data to increment tool count
                cursor.execute(
                    "SELECT compressed_data FROM entities WHERE id = ?",
                    (existing['id'],)
                )
                row = cursor.fetchone()
                if row and row['compressed_data']:
                    try:
                        # Handle both compressed and uncompressed data
                        data_bytes = row['compressed_data']
                        if isinstance(data_bytes, bytes):
                            try:
                                import zlib
                                current_data = json.loads(zlib.decompress(data_bytes).decode('utf-8'))
                            except:
                                current_data = json.loads(data_bytes.decode('utf-8'))
                        else:
                            current_data = json.loads(data_bytes)
                        activity_data['tool_count'] = current_data.get('tool_count', 0) + 1
                        activity_data['tools_used'] = current_data.get('tools_used', [])
                        if tool_name not in activity_data['tools_used']:
                            activity_data['tools_used'].append(tool_name)
                    except (json.JSONDecodeError, Exception):
                        activity_data['tools_used'] = [tool_name]

                # Update with compressed data
                import zlib
                compressed = zlib.compress(json.dumps(activity_data).encode('utf-8'))
                cursor.execute("""
                    UPDATE entities
                    SET compressed_data = ?,
                        last_accessed = datetime('now'),
                        access_count = access_count + 1
                    WHERE id = ?
                """, (compressed, existing['id']))
            else:
                # Create new session activity entity
                activity_data['tools_used'] = [tool_name]
                activity_data['session_start'] = now

                import zlib
                compressed = zlib.compress(json.dumps(activity_data).encode('utf-8'))
                original_size = len(json.dumps(activity_data).encode('utf-8'))
                compressed_size = len(compressed)

                cursor.execute("""
                    INSERT INTO entities (name, entity_type, compressed_data, tier, original_size, compressed_size, compression_ratio, last_accessed, created_at)
                    VALUES (?, 'session_activity', ?, 'working', ?, ?, ?, datetime('now'), datetime('now'))
                """, (activity_entity, compressed, original_size, compressed_size, compressed_size/original_size if original_size > 0 else 1.0))

            # Also update the generic "current_session" marker for quick checks
            cursor.execute(
                "SELECT id FROM entities WHERE name = 'current_session_marker'"
            )
            marker = cursor.fetchone()

            marker_data = {
                "active": True,
                "session_id": self.session_id,
                "node": self.node_id,
                "last_activity": now
            }

            import zlib
            marker_compressed = zlib.compress(json.dumps(marker_data).encode('utf-8'))
            marker_original = len(json.dumps(marker_data).encode('utf-8'))
            marker_comp_size = len(marker_compressed)

            if marker:
                cursor.execute("""
                    UPDATE entities
                    SET compressed_data = ?, last_accessed = datetime('now'), access_count = access_count + 1
                    WHERE id = ?
                """, (marker_compressed, marker['id']))
            else:
                cursor.execute("""
                    INSERT INTO entities (name, entity_type, compressed_data, tier, original_size, compressed_size, compression_ratio, last_accessed, created_at)
                    VALUES ('current_session_marker', 'system', ?, 'working', ?, ?, ?, datetime('now'), datetime('now'))
                """, (marker_compressed, marker_original, marker_comp_size, marker_comp_size/marker_original if marker_original > 0 else 1.0))

            conn.commit()
            return True

        except Exception as e:
            print(f"Activity update error: {e}", file=sys.stderr)
            return False
        finally:
            conn.close()

    def record_tool_pattern(self, tool_name: str, params: Dict[str, Any] = None,
                           duration_ms: int = None, success: bool = True) -> bool:
        """
        Record tool usage pattern for AGI meta-learning.

        This feeds into pattern detection for:
        - Tool effectiveness analysis
        - Workflow optimization
        - Capability improvement
        """
        try:
            ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)

            pattern_record = {
                "timestamp": datetime.now().isoformat(),
                "event": "tool_execution",
                "session_id": self.session_id,
                "node": self.node_id,
                "tool": tool_name,
                "success": success,
                "duration_ms": duration_ms,
                "params_hash": hashlib.md5(
                    json.dumps(params or {}, sort_keys=True).encode()
                ).hexdigest()[:8] if params else None
            }

            with open(ACTIVITY_LOG, 'a') as f:
                f.write(json.dumps(pattern_record) + '\n')

            return True
        except Exception:
            return False

    def record_episodic_memory(self, tool_name: str, outcome: str,
                               context: Dict[str, Any] = None) -> bool:
        """
        Record significant actions as episodic memories for AGI learning.

        Uses TPU when available for intelligent importance scoring.

        Episodic memories enable:
        - Learning from experience
        - Similar situation recall
        - Avoiding repeated failures
        """
        conn = self._get_db_connection()
        if not conn:
            return False

        try:
            import zlib
            cursor = conn.cursor()
            now = datetime.now()

            # Calculate importance score using TPU when available
            description = f"{tool_name}: {outcome[:200] if len(outcome) > 200 else outcome}"
            importance = score_importance(description, "action")

            # Determine tier based on importance
            if importance >= 0.8:
                tier = "long_term"  # High importance: promote to long-term
            elif importance >= 0.6:
                tier = "episodic"   # Medium: standard episodic storage
            else:
                tier = "working"    # Low: short-term working memory

            # Create episodic memory for significant actions
            memory_name = f"action_{tool_name}_{now.strftime('%Y%m%d_%H%M%S')}"

            memory_content = {
                "tool": tool_name,
                "outcome": outcome,
                "context": context or {},
                "session_id": self.session_id,
                "node": self.node_id,
                "timestamp": now.isoformat(),
                "importance_score": importance,
                "tpu_scored": _HAS_TPU_SCORING
            }

            content_json = json.dumps(memory_content)
            compressed = zlib.compress(content_json.encode('utf-8'))
            original_size = len(content_json.encode('utf-8'))
            compressed_size = len(compressed)

            cursor.execute("""
                INSERT INTO entities (name, entity_type, compressed_data, tier, original_size, compressed_size, compression_ratio, last_accessed, created_at)
                VALUES (?, 'episodic_action', ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (memory_name, compressed, tier, original_size, compressed_size, compressed_size/original_size if original_size > 0 else 1.0))

            conn.commit()
            return True

        except Exception as e:
            print(f"Episodic memory error: {e}", file=sys.stderr)
            return False
        finally:
            conn.close()

    def update_session_file(self, tool_name: str) -> bool:
        """Update the session tracking file for statusline."""
        try:
            now = datetime.now()

            if SESSION_FILE.exists():
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {
                    "session_id": self.session_id,
                    "start_time": now.isoformat(),
                    "node": self.node_id
                }

            data["last_activity"] = now.isoformat()
            data["last_tool"] = tool_name
            data["tool_count"] = data.get("tool_count", 0) + 1

            with open(SESSION_FILE, 'w') as f:
                json.dump(data, f)

            return True
        except Exception:
            return False

    def track_activity(self, tool_name: str, params: Dict[str, Any] = None,
                      outcome: str = None, success: bool = True,
                      duration_ms: int = None) -> Dict[str, bool]:
        """
        Main entry point for activity tracking.

        Performs all tracking operations:
        1. Updates session activity in memory (for statusline)
        2. Records tool pattern (for meta-learning)
        3. Updates session file (for quick checks)
        4. Optionally records episodic memory (for significant actions)
        """
        results = {
            "session_activity": False,
            "tool_pattern": False,
            "session_file": False,
            "episodic_memory": False
        }

        context = {
            "params_summary": self._summarize_params(params) if params else None
        }

        # 1. Update session activity in memory DB (critical for statusline)
        results["session_activity"] = self.update_session_activity(tool_name, context)

        # 2. Record tool pattern for meta-learning
        results["tool_pattern"] = self.record_tool_pattern(
            tool_name, params, duration_ms, success
        )

        # 3. Update session file
        results["session_file"] = self.update_session_file(tool_name)

        # 4. Record episodic memory for significant outcomes
        if outcome:
            results["episodic_memory"] = self.record_episodic_memory(
                tool_name, outcome, context
            )

        return results

    def _summarize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe summary of parameters (no sensitive data)."""
        if not params:
            return {}

        summary = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Just record length and type, not content
                summary[key] = {"type": "string", "length": len(value)}
            elif isinstance(value, (int, float, bool)):
                summary[key] = {"type": type(value).__name__, "value": value}
            elif isinstance(value, (list, dict)):
                summary[key] = {"type": type(value).__name__, "size": len(value)}
            else:
                summary[key] = {"type": type(value).__name__}

        return summary


def main():
    """CLI interface for activity tracker."""
    import argparse

    parser = argparse.ArgumentParser(description="AGI Activity Tracker")
    parser.add_argument("--tool", "-t", required=True, help="Tool name")
    parser.add_argument("--params", "-p", help="JSON parameters")
    parser.add_argument("--outcome", "-o", help="Action outcome")
    parser.add_argument("--success", "-s", action="store_true", default=True)
    parser.add_argument("--duration", "-d", type=int, help="Duration in ms")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    args = parser.parse_args()

    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            params = {"raw": args.params}

    tracker = AGIActivityTracker()
    results = tracker.track_activity(
        tool_name=args.tool,
        params=params,
        outcome=args.outcome,
        success=args.success,
        duration_ms=args.duration
    )

    if not args.quiet:
        success_count = sum(1 for v in results.values() if v)
        print(f"Activity tracked: {success_count}/{len(results)} operations successful")

    # Exit with success if at least session_activity worked
    sys.exit(0 if results["session_activity"] else 1)


if __name__ == "__main__":
    main()
