#!/usr/bin/env python3
"""
Cluster Visual Aggregator - Unified Visual Awareness for Cluster Mind

This module aggregates visual observations from all cluster nodes to provide
a unified view of the entire distributed environment.

Features:
- Collect observations from all nodes
- Detect cross-node patterns (user moving between locations)
- Provide cluster-wide visual summary
- Feed consolidated observations to enhanced memory
- Track environmental state across the cluster
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cluster_visual_aggregator")

# Configuration
CLUSTER_DB = Path("/mnt/agentic-system/databases/cluster/shared_memories.db")
SENSORY_DIR = Path("/mnt/agentic-system/databases/sensory")


class ClusterVisualAggregator:
    """
    Aggregates visual observations from all cluster nodes
    """

    def __init__(self):
        self.node_observations: Dict[str, List[Dict]] = defaultdict(list)
        self.node_states: Dict[str, Dict] = {}
        self.last_sync = None

        # Node metadata
        self.nodes = {
            "macpro51": {"role": "builder", "location": "office"},
            "marcs-mac-studio": {"role": "orchestrator", "location": "studio"},
            "marcs-macbook-air": {"role": "researcher", "location": "mobile"},
            "completeu-server": {"role": "ai-inference", "location": "rack"}
        }

    def get_cluster_observations(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get all visual observations from cluster in the last N minutes"""
        observations = []

        try:
            if not CLUSTER_DB.exists():
                logger.warning("Cluster DB not found")
                return observations

            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

            cursor.execute('''
                SELECT node_id, timestamp, scene_context, person_present,
                       motion_level, lighting_condition, summary, data
                FROM cluster_visual_observations
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff,))

            for row in cursor.fetchall():
                observations.append({
                    "node_id": row[0],
                    "timestamp": row[1],
                    "scene_context": row[2],
                    "person_present": bool(row[3]),
                    "motion_level": row[4],
                    "lighting_condition": row[5],
                    "summary": row[6],
                    "data": json.loads(row[7]) if row[7] else {}
                })

            conn.close()

        except Exception as e:
            logger.error(f"Failed to get cluster observations: {e}")

        return observations

    def get_node_latest(self) -> Dict[str, Dict]:
        """Get the latest observation from each node"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT node_id, timestamp, scene_context, person_present,
                       motion_level, lighting_condition, summary
                FROM cluster_visual_observations
                WHERE id IN (
                    SELECT MAX(id) FROM cluster_visual_observations GROUP BY node_id
                )
            ''')

            for row in cursor.fetchall():
                self.node_states[row[0]] = {
                    "timestamp": row[1],
                    "scene_context": row[2],
                    "person_present": bool(row[3]),
                    "motion_level": row[4],
                    "lighting_condition": row[5],
                    "summary": row[6],
                    "age_seconds": (datetime.now() - datetime.fromisoformat(row[1])).total_seconds()
                }

            conn.close()

        except Exception as e:
            logger.error(f"Failed to get node latest: {e}")

        return self.node_states

    def detect_user_location(self) -> Optional[Dict[str, Any]]:
        """Detect which node(s) the user is at based on recent observations"""
        self.get_node_latest()

        user_locations = []
        for node_id, state in self.node_states.items():
            if state.get("person_present") and state.get("age_seconds", 9999) < 120:
                user_locations.append({
                    "node_id": node_id,
                    "scene_context": state.get("scene_context"),
                    "activity_level": state.get("motion_level", "unknown"),
                    "last_seen": state.get("timestamp")
                })

        if not user_locations:
            return {"status": "user_not_detected", "locations": []}

        if len(user_locations) == 1:
            return {
                "status": "user_located",
                "primary_location": user_locations[0],
                "locations": user_locations
            }

        # Multiple locations - user might be detected by multiple cameras
        return {
            "status": "user_multiple_locations",
            "locations": user_locations,
            "note": "User detected at multiple nodes - may indicate overlapping camera coverage"
        }

    def detect_movement_patterns(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Detect user movement patterns across nodes"""
        observations = self.get_cluster_observations(minutes=hours * 60)

        if len(observations) < 10:
            return []

        patterns = []

        # Group observations by hour
        hourly_presence: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for obs in observations:
            if obs.get("person_present"):
                ts = datetime.fromisoformat(obs["timestamp"])
                hour = ts.hour
                node = obs["node_id"]
                hourly_presence[hour][node] += 1

        # Analyze patterns
        for hour, nodes in hourly_presence.items():
            if nodes:
                primary_node = max(nodes, key=nodes.get)
                patterns.append({
                    "hour": hour,
                    "primary_node": primary_node,
                    "observation_count": sum(nodes.values()),
                    "distribution": dict(nodes)
                })

        return patterns

    def get_cluster_environment_summary(self) -> Dict[str, Any]:
        """Get a summary of the cluster's visual environment"""
        self.get_node_latest()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "nodes_reporting": len(self.node_states),
            "nodes": {},
            "cluster_state": "unknown"
        }

        nodes_with_person = 0
        nodes_active = 0
        nodes_dark = 0

        for node_id, state in self.node_states.items():
            summary["nodes"][node_id] = {
                "status": "online" if state.get("age_seconds", 9999) < 60 else "stale",
                "scene": state.get("scene_context"),
                "person_present": state.get("person_present", False),
                "lighting": state.get("lighting_condition"),
                "last_update": state.get("timestamp")
            }

            if state.get("person_present"):
                nodes_with_person += 1
            if state.get("motion_level") in ["medium", "high"]:
                nodes_active += 1
            if state.get("lighting_condition") in ["dark", "dim"]:
                nodes_dark += 1

        # Determine cluster state
        if nodes_with_person == 0:
            summary["cluster_state"] = "user_absent"
            summary["description"] = "No user detected at any node"
        elif nodes_with_person == 1:
            active_node = [n for n, s in self.node_states.items() if s.get("person_present")][0]
            summary["cluster_state"] = "user_at_single_node"
            summary["description"] = f"User at {active_node}"
            summary["user_location"] = active_node
        else:
            summary["cluster_state"] = "user_at_multiple_nodes"
            summary["description"] = f"User detected at {nodes_with_person} nodes"

        summary["activity_level"] = "high" if nodes_active > 1 else "medium" if nodes_active == 1 else "low"

        return summary

    def aggregate_for_memory(self) -> Dict[str, Any]:
        """
        Create a consolidated observation for storage in enhanced memory
        """
        summary = self.get_cluster_environment_summary()
        user_location = self.detect_user_location()
        patterns = self.detect_movement_patterns(hours=1)

        aggregated = {
            "source": "cluster_visual_aggregator",
            "timestamp": datetime.now().isoformat(),
            "cluster_summary": summary,
            "user_location": user_location,
            "hourly_patterns": patterns[-3:] if patterns else [],  # Last 3 hours
            "nodes_online": summary.get("nodes_reporting", 0),
            "cluster_state": summary.get("cluster_state"),
            "significance_score": self._calculate_significance(summary, user_location)
        }

        return aggregated

    def _calculate_significance(self, summary: Dict, user_location: Dict) -> float:
        """Calculate significance of current cluster visual state"""
        score = 0.3  # Base score

        # User presence is significant
        if user_location.get("status") == "user_located":
            score += 0.3

        # Multiple nodes active is significant
        if summary.get("activity_level") == "high":
            score += 0.2

        # State change is significant
        if summary.get("cluster_state") == "user_at_multiple_nodes":
            score += 0.1

        return min(1.0, score)

    def print_status(self):
        """Print current cluster visual status"""
        summary = self.get_cluster_environment_summary()
        user_location = self.detect_user_location()

        print("\n" + "=" * 60)
        print("CLUSTER VISUAL STATUS")
        print("=" * 60)
        print(f"Time: {summary['timestamp']}")
        print(f"State: {summary['cluster_state']}")
        print(f"Description: {summary['description']}")
        print(f"Activity Level: {summary['activity_level']}")
        print()

        print("NODE STATUS:")
        print("-" * 40)
        for node_id, node in summary.get("nodes", {}).items():
            status_icon = "🟢" if node["status"] == "online" else "🟡"
            person_icon = "👤" if node["person_present"] else "  "
            print(f"  {status_icon} {node_id}: {node['scene']} {person_icon} [{node['lighting']}]")

        print()
        print("USER LOCATION:")
        print("-" * 40)
        if user_location.get("status") == "user_located":
            loc = user_location["primary_location"]
            print(f"  📍 {loc['node_id']} - {loc['scene_context']} ({loc['activity_level']} activity)")
        elif user_location.get("status") == "user_multiple_locations":
            print("  📍 Multiple locations:")
            for loc in user_location.get("locations", []):
                print(f"     - {loc['node_id']}: {loc['scene_context']}")
        else:
            print("  ❓ User not detected at any node")

        print("=" * 60 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Visual Aggregator")
    parser.add_argument("--status", action="store_true", help="Show cluster visual status")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--patterns", action="store_true", help="Show movement patterns")
    parser.add_argument("--hours", type=int, default=24, help="Hours to analyze for patterns")

    args = parser.parse_args()

    aggregator = ClusterVisualAggregator()

    if args.patterns:
        patterns = aggregator.detect_movement_patterns(hours=args.hours)
        if args.json:
            print(json.dumps(patterns, indent=2))
        else:
            print("\nMOVEMENT PATTERNS (last {} hours)".format(args.hours))
            print("-" * 40)
            for p in patterns:
                print(f"  {p['hour']:02d}:00 - Primary: {p['primary_node']} ({p['observation_count']} obs)")
    elif args.json:
        result = aggregator.aggregate_for_memory()
        print(json.dumps(result, indent=2))
    else:
        aggregator.print_status()


if __name__ == "__main__":
    main()
