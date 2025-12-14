#!/usr/bin/env python3
"""
Self Visual Analyzer - Store Visual Analyses in Cluster Database

This module stores visual analyses (from any source: Claude Code native,
Ollama vision models, or external APIs) into the cluster database for
visual awareness integration.

The key insight: Claude Code itself has native vision capabilities through
the Read tool. This module enables storing observations made by the main
Claude instance into the awareness database.
"""
import platform

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_visual_analyzer")

STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"


class SelfVisualAnalyzer:
    """
    Stores visual analyses from any source into cluster awareness
    """

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure database tables exist"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS self_visual_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    node_id TEXT,
                    image_path TEXT,
                    scene TEXT,
                    people TEXT,
                    activity TEXT,
                    objects TEXT,
                    lighting TEXT,
                    mood TEXT,
                    person_present INTEGER DEFAULT 0,
                    summary TEXT,
                    source TEXT DEFAULT 'claude_native',
                    significance REAL DEFAULT 0.5,
                    raw_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_self_visual_timestamp
                ON self_visual_analyses(timestamp)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_self_visual_node
                ON self_visual_analyses(node_id)
            ''')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to ensure tables: {e}")

    def store_analysis(self,
                       scene: str,
                       people: str,
                       activity: str,
                       lighting: str,
                       mood: str,
                       node_id: str = None,
                       image_path: str = None,
                       objects: str = None,
                       summary: str = None,
                       notes: str = None,
                       source: str = "claude_native") -> bool:
        """
        Store a visual analysis

        Args:
            scene: Description of the environment
            people: Description of people present
            activity: What's happening in the scene
            lighting: Lighting conditions
            mood: Overall atmosphere
            node_id: Which node captured this
            image_path: Path to the analyzed image
            objects: Notable objects visible
            summary: Brief summary
            notes: Additional notes
            source: Analysis source (claude_native, ollama, api)

        Returns:
            True if stored successfully
        """
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Determine person presence
            people_lower = people.lower() if people else ""
            person_present = not any(word in people_lower for word in
                ["no", "none", "empty", "absent", "nobody", "not visible", "no one", "no person"])

            # Calculate significance
            significance = 0.3
            if person_present:
                significance += 0.4
            if activity and len(activity) > 10:
                significance += 0.2

            # Generate summary if not provided
            if not summary:
                parts = [scene, people, activity]
                summary = ". ".join([p for p in parts if p][:2])

            cursor.execute('''
                INSERT INTO self_visual_analyses
                (timestamp, node_id, image_path, scene, people, activity,
                 objects, lighting, mood, person_present, summary, source,
                 significance, raw_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                node_id,
                image_path,
                scene,
                people,
                activity,
                objects,
                lighting,
                mood,
                1 if person_present else 0,
                summary,
                source,
                significance,
                notes
            ))

            conn.commit()
            conn.close()
            logger.info(f"Stored visual analysis: {summary[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
            return False

    def get_recent_analyses(self, limit: int = 10, node_id: str = None) -> list:
        """Get recent visual analyses"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            if node_id:
                cursor.execute('''
                    SELECT timestamp, node_id, scene, people, activity,
                           lighting, mood, person_present, summary, source
                    FROM self_visual_analyses
                    WHERE node_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (node_id, limit))
            else:
                cursor.execute('''
                    SELECT timestamp, node_id, scene, people, activity,
                           lighting, mood, person_present, summary, source
                    FROM self_visual_analyses
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "timestamp": row[0],
                    "node_id": row[1],
                    "scene": row[2],
                    "people": row[3],
                    "activity": row[4],
                    "lighting": row[5],
                    "mood": row[6],
                    "person_present": bool(row[7]),
                    "summary": row[8],
                    "source": row[9]
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Failed to get analyses: {e}")
            return []

    def get_awareness_summary(self) -> Dict[str, Any]:
        """Get current visual awareness summary"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Get latest analysis per node
            cursor.execute('''
                SELECT node_id, timestamp, scene, people, lighting,
                       person_present, summary
                FROM self_visual_analyses
                WHERE id IN (
                    SELECT MAX(id) FROM self_visual_analyses
                    GROUP BY node_id
                )
            ''')

            nodes = {}
            for row in cursor.fetchall():
                if row[0]:
                    nodes[row[0]] = {
                        "timestamp": row[1],
                        "scene": row[2],
                        "people": row[3],
                        "lighting": row[4],
                        "person_present": bool(row[5]),
                        "summary": row[6]
                    }

            conn.close()

            person_locations = [n for n, d in nodes.items() if d.get("person_present")]

            return {
                "timestamp": datetime.now().isoformat(),
                "nodes_with_data": list(nodes.keys()),
                "person_detected_at": person_locations,
                "user_status": "present" if person_locations else "absent",
                "nodes": nodes
            }

        except Exception as e:
            logger.error(f"Failed to get awareness: {e}")
            return {"error": str(e)}


def main():
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Self Visual Analyzer")
    parser.add_argument("--store", action="store_true", help="Store an analysis")
    parser.add_argument("--scene", help="Scene description")
    parser.add_argument("--people", help="People description")
    parser.add_argument("--activity", help="Activity description")
    parser.add_argument("--lighting", help="Lighting condition")
    parser.add_argument("--mood", help="Mood/atmosphere")
    parser.add_argument("--node", help="Node ID")
    parser.add_argument("--image", help="Image path")
    parser.add_argument("--objects", help="Notable objects")
    parser.add_argument("--recent", type=int, default=0, help="Show N recent analyses")
    parser.add_argument("--awareness", action="store_true", help="Show awareness summary")

    args = parser.parse_args()

    analyzer = SelfVisualAnalyzer()

    if args.store and args.scene:
        success = analyzer.store_analysis(
            scene=args.scene,
            people=args.people or "",
            activity=args.activity or "",
            lighting=args.lighting or "",
            mood=args.mood or "",
            node_id=args.node,
            image_path=args.image,
            objects=args.objects
        )
        print("Stored successfully" if success else "Storage failed")

    elif args.recent > 0:
        analyses = analyzer.get_recent_analyses(args.recent)
        print(json.dumps(analyses, indent=2))

    elif args.awareness:
        summary = analyzer.get_awareness_summary()
        print(json.dumps(summary, indent=2))

    else:
        print("Self Visual Analyzer - Store and retrieve visual analyses")
        print("\nStore analysis:")
        print('  python self_visual_analyzer.py --store --scene "Home office" --people "One person" --lighting "Low"')
        print("\nShow recent:")
        print("  python self_visual_analyzer.py --recent 5")
        print("\nShow awareness:")
        print("  python self_visual_analyzer.py --awareness")


if __name__ == "__main__":
    main()
