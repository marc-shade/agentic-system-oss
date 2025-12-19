#!/usr/bin/env python3
"""
Auto-fix script for goals without tasks.
Detects active goals with no pending/in_progress tasks and creates default tasks.

Run periodically via cron or hook to prevent "goals with no tasks" warnings.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = str(Path.home() / ".claude" / "agent_runtime.db")

# Default task templates for each goal category
TASK_TEMPLATES = {
    "memory": {
        "title": "Run memory health check",
        "description": "Check memory tiers, run consolidation if needed",
        "priority": 5
    },
    "learning": {
        "title": "Process one knowledge source",
        "description": "Research and synthesize one paper or resource for knowledge gaps",
        "priority": 5
    },
    "security": {
        "title": "Run security scan",
        "description": "Execute vulnerability scan on agentic system",
        "priority": 8
    },
    "infrastructure": {
        "title": "Check cluster health",
        "description": "Verify all cluster nodes are reachable and healthy",
        "priority": 7
    },
    "self_improvement": {
        "title": "Identify improvement opportunity",
        "description": "Analyze metrics and find one improvement target",
        "priority": 6
    },
    "metacognition": {
        "title": "Run metacognitive audit",
        "description": "Test beliefs with counterfactuals, update awareness scores",
        "priority": 4
    },
    "optimization": {
        "title": "Optimize one bottleneck",
        "description": "Analyze performance and improve one slow component",
        "priority": 5
    },
    "coordination": {
        "title": "Test agent coordination",
        "description": "Verify multi-agent swarm works correctly",
        "priority": 5
    },
    "alignment": {
        "title": "Review alignment status",
        "description": "Verify user goals are being prioritized correctly",
        "priority": 9
    },
    "evolution": {
        "title": "Test one skill variant",
        "description": "A/B test a skill and record performance",
        "priority": 4
    },
    "hardware": {
        "title": "Verify hardware connectivity",
        "description": "Test Arduino, TPU, and sensor integration",
        "priority": 3
    },
    "knowledge": {
        "title": "Enrich knowledge graph",
        "description": "Extract and add new relationships from observations",
        "priority": 5
    },
    "research": {
        "title": "Execute research cycle",
        "description": "Run one research-to-implementation pipeline",
        "priority": 5
    },
    "continuity": {
        "title": "Verify session continuity",
        "description": "Test context restoration and pending work tracking",
        "priority": 6
    },
    "reasoning": {
        "title": "Build causal model",
        "description": "Create causal links for one action pattern",
        "priority": 5
    },
    "interface": {
        "title": "Test voice interface",
        "description": "Verify TTS/STT round-trip works correctly",
        "priority": 4
    },
    "default": {
        "title": "Review goal progress",
        "description": "Check goal status and identify next actions",
        "priority": 5
    }
}


def get_orphan_goals(conn):
    """Find active goals with no pending or in_progress tasks."""
    cursor = conn.cursor()

    # Get all active goals
    cursor.execute("""
        SELECT id, name, metadata FROM goals
        WHERE status = 'active'
    """)
    active_goals = cursor.fetchall()

    orphans = []
    for goal_id, name, metadata_str in active_goals:
        # Check if goal has any active tasks
        cursor.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE goal_id = ? AND status IN ('pending', 'in_progress')
        """, (goal_id,))
        task_count = cursor.fetchone()[0]

        if task_count == 0:
            metadata = json.loads(metadata_str) if metadata_str else {}
            orphans.append({
                "id": goal_id,
                "name": name,
                "category": metadata.get("category", "default")
            })

    return orphans


def create_task_for_goal(conn, goal_id, category):
    """Create a default task for an orphan goal."""
    template = TASK_TEMPLATES.get(category, TASK_TEMPLATES["default"])

    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO tasks (goal_id, title, description, status, priority,
                          dependencies, created_at, updated_at, metadata)
        VALUES (?, ?, ?, 'pending', ?, '[]', ?, ?, '{}')
    """, (
        goal_id,
        template["title"],
        template["description"],
        template["priority"],
        now,
        now
    ))

    return cursor.lastrowid


def cleanup_orphan_tasks(conn):
    """Delete orphan tasks (no goal_id) that are stale."""
    cursor = conn.cursor()

    # Delete pending tasks with no goal that are older than 7 days
    cursor.execute("""
        DELETE FROM tasks
        WHERE goal_id IS NULL
        AND status = 'pending'
        AND created_at < datetime('now', '-7 days')
    """)

    deleted = cursor.rowcount
    return deleted


def cleanup_stalled_investigation_tasks(conn):
    """Delete 'Investigate stalled goal' tasks for autonomous or immutable goals."""
    cursor = conn.cursor()

    # Delete investigation tasks for goals marked as autonomous OR immutable
    # These are persistent goals that shouldn't trigger stall alerts
    cursor.execute("""
        DELETE FROM tasks
        WHERE title LIKE '%Investigate stalled%'
        AND status IN ('pending', 'in_progress')
        AND goal_id IN (
            SELECT id FROM goals
            WHERE json_extract(metadata, '$.autonomous') = 1
               OR json_extract(metadata, '$.immutable') = 1
        )
    """)

    deleted = cursor.rowcount
    return deleted


def main():
    """Main auto-fix routine."""
    conn = sqlite3.connect(DB_PATH)

    try:
        # Always clean up stalled investigation tasks first
        stalled_deleted = cleanup_stalled_investigation_tasks(conn)
        if stalled_deleted > 0:
            print(f"  → Cleaned up {stalled_deleted} stalled investigation tasks")

        # Find orphan goals
        orphans = get_orphan_goals(conn)

        if not orphans:
            # Clean up old orphan tasks
            deleted = cleanup_orphan_tasks(conn)
            if deleted > 0:
                print(f"  → Cleaned up {deleted} stale orphan tasks")
            conn.commit()
            print("✓ No orphan goals found")
            return 0

        print(f"Found {len(orphans)} goals without tasks:")

        # Create tasks for each orphan
        created = 0
        for goal in orphans:
            task_id = create_task_for_goal(conn, goal["id"], goal["category"])
            print(f"  → Created task {task_id} for goal {goal['id']}: {goal['name']}")
            created += 1

        # Clean up old orphan tasks
        deleted = cleanup_orphan_tasks(conn)
        if deleted > 0:
            print(f"  → Cleaned up {deleted} stale orphan tasks")

        conn.commit()
        print(f"✓ Fixed {created} orphan goals")
        return created

    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() == 0 else 0)  # Always exit 0 for hook compatibility
