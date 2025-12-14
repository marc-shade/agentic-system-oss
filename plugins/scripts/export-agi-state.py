#!/usr/bin/env python3
"""
Export AGI state for migration to plugin architecture.
Exports goals, tasks, memories, and outcomes to JSON files.
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def export_agent_runtime(db_path: str, output_dir: Path):
    """Export goals and tasks from agent-runtime-mcp."""
    output_file = output_dir / "agent_runtime_export.json"

    if not os.path.exists(db_path):
        print(f"  Skipping agent-runtime: {db_path} not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {
        "export_date": datetime.now().isoformat(),
        "source": "agent-runtime-mcp",
        "goals": [],
        "tasks": []
    }

    # Export goals
    try:
        cursor.execute("SELECT * FROM goals")
        for row in cursor.fetchall():
            export_data["goals"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No goals table found")

    # Export tasks
    try:
        cursor.execute("SELECT * FROM tasks")
        for row in cursor.fetchall():
            export_data["tasks"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No tasks table found")

    conn.close()

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"  Exported {len(export_data['goals'])} goals, {len(export_data['tasks'])} tasks")


def export_agi_mcp(db_path: str, output_dir: Path):
    """Export outcomes and learning data from agi-mcp."""
    output_file = output_dir / "agi_mcp_export.json"

    if not os.path.exists(db_path):
        print(f"  Skipping agi-mcp: {db_path} not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {
        "export_date": datetime.now().isoformat(),
        "source": "agi-mcp",
        "outcomes": [],
        "patterns": [],
        "skills": []
    }

    # Export outcomes
    try:
        cursor.execute("SELECT * FROM task_outcomes")
        for row in cursor.fetchall():
            export_data["outcomes"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No task_outcomes table found")

    # Export patterns
    try:
        cursor.execute("SELECT * FROM detected_patterns")
        for row in cursor.fetchall():
            export_data["patterns"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No detected_patterns table found")

    # Export skills
    try:
        cursor.execute("SELECT * FROM skill_versions")
        for row in cursor.fetchall():
            export_data["skills"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No skill_versions table found")

    conn.close()

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"  Exported {len(export_data['outcomes'])} outcomes, {len(export_data['patterns'])} patterns")


def export_enhanced_memory(db_path: str, output_dir: Path):
    """Export memory entities from enhanced-memory-mcp."""
    output_file = output_dir / "enhanced_memory_export.json"

    if not os.path.exists(db_path):
        print(f"  Skipping enhanced-memory: {db_path} not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {
        "export_date": datetime.now().isoformat(),
        "source": "enhanced-memory-mcp",
        "entities": [],
        "relations": [],
        "episodes": []
    }

    # Export entities
    try:
        cursor.execute("SELECT * FROM entities")
        for row in cursor.fetchall():
            export_data["entities"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No entities table found")

    # Export relations
    try:
        cursor.execute("SELECT * FROM relations")
        for row in cursor.fetchall():
            export_data["relations"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No relations table found")

    # Export episodes
    try:
        cursor.execute("SELECT * FROM episodes")
        for row in cursor.fetchall():
            export_data["episodes"].append(dict(row))
    except sqlite3.OperationalError:
        print("  No episodes table found")

    conn.close()

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"  Exported {len(export_data['entities'])} entities, {len(export_data['episodes'])} episodes")


def main():
    parser = argparse.ArgumentParser(description='Export AGI state for migration')
    parser.add_argument('--output', '-o', required=True, help='Output directory for exports')
    parser.add_argument('--db-dir', default='/mnt/agentic-system/databases',
                       help='Directory containing AGI databases')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Exporting AGI state to {output_dir}")
    print()

    # Export from each MCP server's database
    print("Exporting agent-runtime-mcp...")
    export_agent_runtime(
        f"{args.db_dir}/agent_runtime.db",
        output_dir
    )

    print("\nExporting agi-mcp...")
    export_agi_mcp(
        f"{args.db_dir}/agi_mcp.db",
        output_dir
    )

    print("\nExporting enhanced-memory-mcp...")
    export_enhanced_memory(
        f"{args.db_dir}/enhanced_memory.db",
        output_dir
    )

    # Create manifest
    manifest = {
        "export_date": datetime.now().isoformat(),
        "source_system": "agentic-system",
        "version": "1.0.0",
        "files": [
            "agent_runtime_export.json",
            "agi_mcp_export.json",
            "enhanced_memory_export.json"
        ]
    }

    with open(output_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nExport complete! Files saved to {output_dir}")
    print("\nTo import after installing plugins:")
    print(f"  python3 ~/.claude/plugins/agi-extended/scripts/import-state.py --input {output_dir}")


if __name__ == "__main__":
    main()
