#!/usr/bin/env python3
"""
Database Migration Script for Enhanced Memory MCP

Run this before starting the new server to ensure all tables and columns exist.
Uses PRAGMA busy_timeout to handle locks gracefully.
"""

import sqlite3
import sys
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# All migrations to apply
MIGRATIONS = [
    # Add improvement_delta to improvement_cycles
    ("improvement_cycles", "improvement_delta", "ALTER TABLE improvement_cycles ADD COLUMN improvement_delta REAL DEFAULT 0.0"),

    # Add validation_results to improvement_cycles
    ("improvement_cycles", "validation_results", "ALTER TABLE improvement_cycles ADD COLUMN validation_results TEXT DEFAULT '{}'"),

    # Add improvement_percentage to improvement_cycles
    ("improvement_cycles", "improvement_percentage", "ALTER TABLE improvement_cycles ADD COLUMN improvement_percentage REAL DEFAULT 0.0"),

    # Ensure reasoning_strategies has all needed columns
    ("reasoning_strategies", "times_used", "ALTER TABLE reasoning_strategies ADD COLUMN times_used INTEGER DEFAULT 0"),
    ("reasoning_strategies", "failure_count", "ALTER TABLE reasoning_strategies ADD COLUMN failure_count INTEGER DEFAULT 0"),
    ("reasoning_strategies", "last_used", "ALTER TABLE reasoning_strategies ADD COLUMN last_used TIMESTAMP"),
    ("reasoning_strategies", "last_success", "ALTER TABLE reasoning_strategies ADD COLUMN last_success TIMESTAMP"),

    # Memory versions table fixes
    ("memory_versions", "parent_version_id", "ALTER TABLE memory_versions ADD COLUMN parent_version_id INTEGER"),

    # Add missing indexes
    ("idx_reasoning_agent", None, "CREATE INDEX IF NOT EXISTS idx_reasoning_agent ON reasoning_strategies(agent_id)"),
    ("idx_improvement_agent", None, "CREATE INDEX IF NOT EXISTS idx_improvement_agent ON improvement_cycles(agent_id)"),
    ("idx_action_outcomes_agent", None, "CREATE INDEX IF NOT EXISTS idx_action_outcomes_agent ON action_outcomes(agent_id)"),
    ("idx_action_outcomes_type", None, "CREATE INDEX IF NOT EXISTS idx_action_outcomes_type ON action_outcomes(action_type)"),
    ("idx_entity_version", None, "CREATE INDEX IF NOT EXISTS idx_entity_version ON memory_versions(entity_id, version_number)"),
]

# Tables that should exist
REQUIRED_TABLES = [
    """CREATE TABLE IF NOT EXISTS reasoning_strategies (
        strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        strategy_name TEXT NOT NULL,
        strategy_type TEXT NOT NULL,
        usage_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        average_confidence REAL DEFAULT 0.5,
        success_rate REAL DEFAULT 0.0,
        effective_contexts TEXT DEFAULT '[]',
        times_used INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        last_used TIMESTAMP,
        last_success TIMESTAMP
    )""",

    """CREATE TABLE IF NOT EXISTS improvement_cycles (
        cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        cycle_number INTEGER NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        cycle_type TEXT NOT NULL,
        improvement_goals TEXT DEFAULT '{}',
        baseline_metrics TEXT DEFAULT '{}',
        identified_weaknesses TEXT DEFAULT '[]',
        strategies_applied TEXT DEFAULT '[]',
        changes_made TEXT DEFAULT '[]',
        new_metrics TEXT DEFAULT '{}',
        success_criteria TEXT DEFAULT '{}',
        success BOOLEAN,
        lessons_learned TEXT DEFAULT '[]',
        next_recommendations TEXT DEFAULT '[]',
        status TEXT DEFAULT 'in_progress',
        improvement_delta REAL DEFAULT 0.0,
        improvement_percentage REAL DEFAULT 0.0,
        validation_results TEXT DEFAULT '{}'
    )""",

    """CREATE TABLE IF NOT EXISTS memory_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL,
        version_number INTEGER NOT NULL,
        compressed_data BLOB NOT NULL,
        diff_from_previous TEXT,
        commit_message TEXT,
        author TEXT DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_current BOOLEAN DEFAULT 0,
        branch_name TEXT DEFAULT 'main',
        parent_version_id INTEGER,
        FOREIGN KEY (entity_id) REFERENCES entities (id)
    )""",

    """CREATE TABLE IF NOT EXISTS action_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT DEFAULT 'default_agent',
        session_id TEXT,
        entity_id INTEGER,
        action_type TEXT NOT NULL,
        action_description TEXT NOT NULL,
        action_context TEXT,
        expected_result TEXT,
        actual_result TEXT,
        success_score REAL NOT NULL,
        duration_ms INTEGER,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        metadata TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (entity_id) REFERENCES entities (id)
    )""",
]


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def run_migrations():
    """Run all database migrations"""
    print(f"Migrating database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")  # 60 second timeout
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    migrations_applied = 0
    errors = []

    # First ensure required tables exist
    print("\nEnsuring required tables exist...")
    for create_sql in REQUIRED_TABLES:
        try:
            cursor.execute(create_sql)
            conn.commit()
        except Exception as e:
            if "already exists" not in str(e).lower():
                errors.append(f"Table creation error: {e}")

    # Apply column migrations
    print("\nApplying column migrations...")
    for table_or_index, column, sql in MIGRATIONS:
        try:
            # Skip if it's a column check and column already exists
            if column and table_exists(cursor, table_or_index):
                if column_exists(cursor, table_or_index, column):
                    print(f"  [SKIP] {table_or_index}.{column} already exists")
                    continue

            cursor.execute(sql)
            conn.commit()
            migrations_applied += 1
            print(f"  [OK] Applied: {sql[:60]}...")

        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print(f"  [SKIP] Already exists: {table_or_index}.{column if column else 'index'}")
            else:
                errors.append(f"{table_or_index}: {e}")
                print(f"  [ERROR] {table_or_index}: {e}")

    # Force WAL checkpoint
    print("\nCheckpointing WAL...")
    try:
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
        print("  [OK] WAL checkpoint complete")
    except Exception as e:
        errors.append(f"WAL checkpoint: {e}")

    conn.close()

    print(f"\n{'='*50}")
    print(f"Migrations applied: {migrations_applied}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors encountered:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nMigration complete!")
    return 0


if __name__ == "__main__":
    sys.exit(run_migrations())
