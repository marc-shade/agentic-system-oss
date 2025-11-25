#!/usr/bin/env python3
"""
Import AGI state from migration export files.
Restores goals, tasks, memories, and outcomes to plugin databases.
"""

import argparse
import json
import sqlite3
from pathlib import Path


def import_agent_runtime(data: dict, db_path: Path):
    """Import goals and tasks to agent-runtime database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Import goals
    goals_imported = 0
    for goal in data.get("goals", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO goals (id, name, description, status, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                goal.get("id"),
                goal.get("name"),
                goal.get("description"),
                goal.get("status", "active"),
                goal.get("metadata"),
                goal.get("created_at"),
                goal.get("updated_at")
            ))
            goals_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import goal {goal.get('id')}: {e}")

    # Import tasks
    tasks_imported = 0
    for task in data.get("tasks", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (id, goal_id, title, description, status, priority, dependencies, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.get("id"),
                task.get("goal_id"),
                task.get("title"),
                task.get("description"),
                task.get("status", "pending"),
                task.get("priority", 5),
                task.get("dependencies"),
                task.get("result"),
                task.get("error"),
                task.get("created_at"),
                task.get("updated_at")
            ))
            tasks_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import task {task.get('id')}: {e}")

    conn.commit()
    conn.close()
    print(f"  Imported {goals_imported} goals, {tasks_imported} tasks")


def import_agi(data: dict, db_path: Path):
    """Import outcomes and patterns to agi-mcp database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Import outcomes
    outcomes_imported = 0
    for outcome in data.get("outcomes", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO task_outcomes
                (id, task_id, task_type, agent_used, success, execution_time_ms, quality_score, error_message, context, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outcome.get("id"),
                outcome.get("task_id"),
                outcome.get("task_type"),
                outcome.get("agent_used"),
                outcome.get("success"),
                outcome.get("execution_time_ms"),
                outcome.get("quality_score"),
                outcome.get("error_message"),
                outcome.get("context"),
                outcome.get("created_at")
            ))
            outcomes_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import outcome: {e}")

    # Import patterns
    patterns_imported = 0
    for pattern in data.get("patterns", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO detected_patterns
                (id, pattern_type, description, occurrences, confidence, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.get("id"),
                pattern.get("pattern_type"),
                pattern.get("description"),
                pattern.get("occurrences"),
                pattern.get("confidence"),
                pattern.get("metadata"),
                pattern.get("created_at"),
                pattern.get("updated_at")
            ))
            patterns_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import pattern: {e}")

    # Import skills
    skills_imported = 0
    for skill in data.get("skills", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO skill_versions
                (id, skill_name, version, description, implementation, is_active, success_rate, avg_execution_time, sample_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.get("id"),
                skill.get("skill_name"),
                skill.get("version"),
                skill.get("description"),
                skill.get("implementation"),
                skill.get("is_active"),
                skill.get("success_rate"),
                skill.get("avg_execution_time"),
                skill.get("sample_count"),
                skill.get("created_at")
            ))
            skills_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import skill: {e}")

    conn.commit()
    conn.close()
    print(f"  Imported {outcomes_imported} outcomes, {patterns_imported} patterns, {skills_imported} skills")


def import_enhanced_memory(data: dict, db_path: Path):
    """Import memory entities to enhanced-memory database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            name TEXT,
            entity_type TEXT,
            content TEXT,
            metadata TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY,
            source_id INTEGER,
            target_id INTEGER,
            relation_type TEXT,
            metadata TEXT,
            created_at TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY,
            description TEXT,
            context TEXT,
            outcome TEXT,
            importance REAL,
            created_at TIMESTAMP
        )
    """)

    # Import entities
    entities_imported = 0
    for entity in data.get("entities", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO entities (id, name, entity_type, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.get("id"),
                entity.get("name"),
                entity.get("entity_type"),
                entity.get("content"),
                entity.get("metadata"),
                entity.get("created_at"),
                entity.get("updated_at")
            ))
            entities_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import entity: {e}")

    # Import relations
    relations_imported = 0
    for rel in data.get("relations", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO relations (id, source_id, target_id, relation_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rel.get("id"),
                rel.get("source_id"),
                rel.get("target_id"),
                rel.get("relation_type"),
                rel.get("metadata"),
                rel.get("created_at")
            ))
            relations_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import relation: {e}")

    # Import episodes
    episodes_imported = 0
    for ep in data.get("episodes", []):
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO episodes (id, description, context, outcome, importance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ep.get("id"),
                ep.get("description"),
                ep.get("context"),
                ep.get("outcome"),
                ep.get("importance"),
                ep.get("created_at")
            ))
            episodes_imported += 1
        except Exception as e:
            print(f"  Warning: Failed to import episode: {e}")

    conn.commit()
    conn.close()
    print(f"  Imported {entities_imported} entities, {relations_imported} relations, {episodes_imported} episodes")


def main():
    parser = argparse.ArgumentParser(description='Import AGI state from migration export')
    parser.add_argument('--input', '-i', required=True, help='Input directory with export files')
    parser.add_argument('--db-dir', default='~/.claude/agi/databases',
                       help='Directory for AGI databases')
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser()
    db_dir = Path(args.db_dir).expanduser()

    # Ensure database directory exists
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"Importing AGI state from {input_dir}")
    print(f"Databases: {db_dir}")
    print()

    # Check manifest
    manifest_path = input_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"Export from: {manifest.get('source_system', 'unknown')}")
        print(f"Export date: {manifest.get('export_date', 'unknown')}")
        print()

    # Import agent-runtime
    agent_runtime_export = input_dir / "agent_runtime_export.json"
    if agent_runtime_export.exists():
        print("Importing agent-runtime data...")
        with open(agent_runtime_export) as f:
            data = json.load(f)
        import_agent_runtime(data, db_dir / "agent_runtime.db")
    else:
        print("Skipping agent-runtime: export file not found")

    # Import agi-mcp
    agi_export = input_dir / "agi_mcp_export.json"
    if agi_export.exists():
        print("\nImporting agi-mcp data...")
        with open(agi_export) as f:
            data = json.load(f)
        import_agi(data, db_dir / "agi_mcp.db")
    else:
        print("Skipping agi-mcp: export file not found")

    # Import enhanced-memory
    memory_export = input_dir / "enhanced_memory_export.json"
    if memory_export.exists():
        print("\nImporting enhanced-memory data...")
        with open(memory_export) as f:
            data = json.load(f)
        import_enhanced_memory(data, db_dir / "enhanced_memory.db")
    else:
        print("Skipping enhanced-memory: export file not found")

    print("\nImport complete!")
    print(f"Databases saved to: {db_dir}")
    print("\nRestart Claude Code to use imported data.")


if __name__ == "__main__":
    main()
