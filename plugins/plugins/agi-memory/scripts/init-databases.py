#!/usr/bin/env python3
"""
Initialize SQLite databases for agi-memory plugin.
Creates schema for agent-runtime, agi-mcp, and ember.
"""

import argparse
import sqlite3
from pathlib import Path


def init_agent_runtime_db(db_path: Path):
    """Initialize agent-runtime database with goals and tasks tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            dependencies TEXT,
            result TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_goal ON tasks(goal_id)")

    conn.commit()
    conn.close()
    print(f"  Initialized agent-runtime database: {db_path}")


def init_agi_db(db_path: Path):
    """Initialize agi-mcp database for meta-learning."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Task outcomes for learning
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            agent_used TEXT NOT NULL,
            success INTEGER NOT NULL,
            execution_time_ms INTEGER NOT NULL,
            quality_score REAL,
            error_message TEXT,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Detected patterns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detected_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            description TEXT,
            occurrences INTEGER DEFAULT 1,
            confidence REAL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Skill versions for A/B testing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            version TEXT NOT NULL,
            description TEXT,
            implementation TEXT,
            is_active INTEGER DEFAULT 0,
            success_rate REAL,
            avg_execution_time REAL,
            sample_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Agent performance stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            total_tasks INTEGER DEFAULT 0,
            successful_tasks INTEGER DEFAULT 0,
            avg_execution_time REAL,
            avg_quality_score REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_name, task_type)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_task_type ON task_outcomes(task_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON task_outcomes(agent_used)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON detected_patterns(pattern_type)")

    conn.commit()
    conn.close()
    print(f"  Initialized agi-mcp database: {db_path}")


def init_ember_db(db_path: Path):
    """Initialize ember database for quality conscience."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Violation checks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violation_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            context TEXT,
            violation_type TEXT,
            severity REAL,
            was_blocked INTEGER,
            user_overrode INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Learning from corrections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_type TEXT NOT NULL,
            user_correction TEXT,
            was_correct INTEGER,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ember state
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ember_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Session context
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            task TEXT,
            goal TEXT,
            task_type TEXT,
            progress REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"  Initialized ember database: {db_path}")


def main():
    parser = argparse.ArgumentParser(description='Initialize AGI-Memory databases')
    parser.add_argument('--db-dir', required=True, help='Directory for databases')
    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)

    print("Initializing AGI-Memory databases...")

    init_agent_runtime_db(db_dir / "agent_runtime.db")
    init_agi_db(db_dir / "agi_mcp.db")
    init_ember_db(db_dir / "ember.db")

    print("\nAll databases initialized successfully!")


if __name__ == "__main__":
    main()
