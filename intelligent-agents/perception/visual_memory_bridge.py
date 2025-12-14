#!/usr/bin/env python3
"""
Visual Memory Bridge - Integrates visual observations with enhanced-memory system

This module connects the visual analysis daemon's observations to the AGI's
enhanced memory system, enabling:
- Storing visual episodes with emotional tags
- Pattern recognition from visual observations
- Long-term visual learning and recall
- Integration with the 4-tier memory architecture
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try to import MCP client
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visual_memory_bridge")

# Configuration
SENSORY_DB = Path("/mnt/agentic-system/databases/sensory/sensory_memory.db")
PERCEPTION_QUEUE = Path("/tmp/perception_queue_visual.json")
ENHANCED_MEMORY_URL = "http://localhost:8101"  # Enhanced memory MCP


class VisualMemoryBridge:
    """
    Bridges visual perception to enhanced memory system
    """

    def __init__(self):
        self.last_processed_id = 0
        self.scene_history: List[str] = []
        self.person_presence_history: List[bool] = []

    def get_latest_observation(self) -> Optional[Dict[str, Any]]:
        """Get most recent visual observation from queue"""
        try:
            if PERCEPTION_QUEUE.exists():
                with open(PERCEPTION_QUEUE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read perception queue: {e}")
        return None

    def get_recent_observations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent observations from sensory database"""
        observations = []
        try:
            conn = sqlite3.connect(str(SENSORY_DB))
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, timestamp, event_type, data, metadata
                FROM sensory_events
                WHERE event_type = 'visual_observation'
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))

            for row in cursor.fetchall():
                obs = {
                    "id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "data": json.loads(row[3]) if row[3] else {},
                    "metadata": json.loads(row[4]) if row[4] else {}
                }
                observations.append(obs)

            conn.close()
        except Exception as e:
            logger.error(f"Failed to get observations: {e}")

        return observations

    def classify_for_memory(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify observation for memory storage

        Determines:
        - Significance score (0.0-1.0)
        - Emotional valence (-1.0 to 1.0)
        - Memory tier (working/episodic/semantic)
        - Event type for categorization
        """
        data = observation.get("data", observation)

        scene_context = data.get("scene_context", "unknown")
        person_present = data.get("humans", {}).get("detected", False)
        motion_level = data.get("motion", {}).get("level", "none")
        lighting = data.get("lighting", {}).get("condition", "normal")

        # Calculate significance
        significance = 0.3  # Base significance

        # Person presence is always significant
        if person_present:
            significance += 0.3
            face_count = data.get("humans", {}).get("count", 0)
            if face_count > 1:
                significance += 0.1  # Multiple people more significant

        # Motion increases significance
        if motion_level == "high":
            significance += 0.2
        elif motion_level == "medium":
            significance += 0.1

        # Unusual lighting is significant
        if lighting in ["dark", "overexposed"]:
            significance += 0.1

        # Scene changes are significant
        if len(self.scene_history) > 0 and scene_context != self.scene_history[-1]:
            significance += 0.15

        significance = min(1.0, significance)

        # Calculate emotional valence
        valence = 0.0  # Neutral by default

        if person_present:
            if scene_context == "person_at_desk":
                valence = 0.2  # Slightly positive - productive
            elif scene_context == "person_active":
                valence = 0.3  # Positive - engaged
            elif scene_context == "person_very_active":
                valence = 0.4  # Positive - highly engaged

        if lighting == "dark":
            valence -= 0.1  # Slightly negative - dark environment

        # Determine memory tier
        if significance >= 0.7:
            tier = "episodic"  # Important enough for long-term
        elif significance >= 0.4:
            tier = "working"  # Keep in active memory
        else:
            tier = "transient"  # Low significance, may be discarded

        # Determine event type
        if person_present:
            if scene_context == "person_at_desk":
                event_type = "user_working"
            elif "active" in scene_context:
                event_type = "user_active"
            else:
                event_type = "user_present"
        elif motion_level in ["medium", "high"]:
            event_type = "environmental_motion"
        else:
            event_type = "environmental_static"

        # Update history
        self.scene_history.append(scene_context)
        if len(self.scene_history) > 100:
            self.scene_history.pop(0)

        self.person_presence_history.append(person_present)
        if len(self.person_presence_history) > 100:
            self.person_presence_history.pop(0)

        return {
            "significance": significance,
            "emotional_valence": valence,
            "arousal": 0.3 if motion_level == "high" else 0.1,
            "memory_tier": tier,
            "event_type": event_type,
            "tags": self._generate_tags(data),
            "summary": data.get("summary", "Visual observation")
        }

    def _generate_tags(self, data: Dict) -> List[str]:
        """Generate tags for memory storage"""
        tags = ["visual", "perception"]

        scene = data.get("scene_context", "")
        if "person" in scene:
            tags.append("person_present")
        if "desk" in scene:
            tags.append("workspace")
        if "active" in scene:
            tags.append("activity")
        if data.get("humans", {}).get("count", 0) > 1:
            tags.append("multiple_people")

        lighting = data.get("lighting", {}).get("condition", "")
        if lighting in ["dark", "dim"]:
            tags.append("low_light")
        elif lighting == "bright":
            tags.append("bright")

        motion = data.get("motion", {}).get("level", "")
        if motion == "high":
            tags.append("high_motion")

        return tags

    def store_in_enhanced_memory(self, observation: Dict[str, Any], classification: Dict[str, Any]) -> bool:
        """
        Store observation in enhanced memory system via MCP

        Uses the 4-tier memory architecture:
        - Working memory for transient observations
        - Episodic memory for significant events
        """
        if not HAS_HTTPX:
            logger.warning("httpx not available, cannot store in enhanced memory")
            return self._store_locally(observation, classification)

        data = observation.get("data", observation)

        try:
            # Prepare episode data
            episode_data = {
                "scene_context": data.get("scene_context"),
                "humans": data.get("humans"),
                "motion": data.get("motion"),
                "lighting": data.get("lighting"),
                "summary": data.get("summary"),
                "frame_path": data.get("frame_path"),
                "timestamp": data.get("timestamp")
            }

            # For high significance, store as episodic memory
            if classification["memory_tier"] == "episodic":
                # Use add_episode MCP tool
                response = httpx.post(
                    f"{ENHANCED_MEMORY_URL}/mcp",
                    json={
                        "method": "add_episode",
                        "params": {
                            "event_type": classification["event_type"],
                            "episode_data": episode_data,
                            "significance_score": classification["significance"],
                            "emotional_valence": classification["emotional_valence"],
                            "tags": classification["tags"]
                        }
                    },
                    timeout=5.0
                )

                if response.status_code == 200:
                    logger.info(f"Stored episodic memory: {classification['event_type']}")
                    return True

            # For working memory tier, store temporarily
            elif classification["memory_tier"] == "working":
                response = httpx.post(
                    f"{ENHANCED_MEMORY_URL}/mcp",
                    json={
                        "method": "add_to_working_memory",
                        "params": {
                            "context_key": "visual_observation",
                            "content": json.dumps(episode_data),
                            "priority": int(classification["significance"] * 10),
                            "ttl_minutes": 30  # 30 minute TTL for working memory
                        }
                    },
                    timeout=5.0
                )

                if response.status_code == 200:
                    logger.debug(f"Stored working memory: {classification['event_type']}")
                    return True

            return True  # Transient observations don't need storage

        except Exception as e:
            logger.error(f"Failed to store in enhanced memory: {e}")
            return self._store_locally(observation, classification)

    def _store_locally(self, observation: Dict, classification: Dict) -> bool:
        """Fallback local storage"""
        try:
            conn = sqlite3.connect(str(SENSORY_DB))
            cursor = conn.cursor()

            # Ensure memory_bridge table exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_bridge_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    observation TEXT,
                    classification TEXT,
                    synced INTEGER DEFAULT 0
                )
            ''')

            cursor.execute('''
                INSERT INTO memory_bridge_queue (timestamp, observation, classification, synced)
                VALUES (?, ?, ?, 0)
            ''', (
                datetime.now().isoformat(),
                json.dumps(observation),
                json.dumps(classification),
            ))

            conn.commit()
            conn.close()
            logger.debug("Stored locally for later sync")
            return True

        except Exception as e:
            logger.error(f"Failed to store locally: {e}")
            return False

    def detect_patterns(self, observations: List[Dict]) -> List[Dict[str, Any]]:
        """
        Detect patterns from recent visual observations

        Patterns that can be detected:
        - Regular presence patterns (user typically at desk at certain times)
        - Activity level patterns (more active in morning vs evening)
        - Environmental patterns (lighting changes over day)
        """
        if len(observations) < 10:
            return []

        patterns = []

        # Analyze presence patterns
        presence_count = sum(1 for obs in observations
                           if obs.get("data", {}).get("humans", {}).get("detected", False))
        presence_ratio = presence_count / len(observations)

        if presence_ratio > 0.8:
            patterns.append({
                "type": "high_presence",
                "description": "User consistently present",
                "confidence": presence_ratio,
                "observation_count": len(observations)
            })
        elif presence_ratio < 0.2:
            patterns.append({
                "type": "low_presence",
                "description": "User rarely present",
                "confidence": 1 - presence_ratio,
                "observation_count": len(observations)
            })

        # Analyze activity patterns
        active_count = sum(1 for obs in observations
                         if "active" in obs.get("data", {}).get("scene_context", ""))
        if active_count > len(observations) * 0.5:
            patterns.append({
                "type": "high_activity",
                "description": "User is frequently active",
                "confidence": active_count / len(observations),
                "observation_count": len(observations)
            })

        # Analyze desk work pattern
        desk_count = sum(1 for obs in observations
                        if obs.get("data", {}).get("scene_context") == "person_at_desk")
        if desk_count > len(observations) * 0.6:
            patterns.append({
                "type": "desk_worker",
                "description": "User spends significant time at desk",
                "confidence": desk_count / len(observations),
                "observation_count": len(observations)
            })

        return patterns

    def process_and_store(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing pipeline: classify and store observation
        """
        classification = self.classify_for_memory(observation)
        stored = self.store_in_enhanced_memory(observation, classification)

        return {
            "observation_id": observation.get("id"),
            "classification": classification,
            "stored": stored,
            "timestamp": datetime.now().isoformat()
        }

    def run_batch_sync(self, limit: int = 100) -> Dict[str, Any]:
        """
        Sync recent observations to enhanced memory
        """
        observations = self.get_recent_observations(limit)
        results = {
            "processed": 0,
            "stored_episodic": 0,
            "stored_working": 0,
            "patterns_detected": []
        }

        for obs in observations:
            result = self.process_and_store(obs)
            results["processed"] += 1

            if result["classification"]["memory_tier"] == "episodic":
                results["stored_episodic"] += 1
            elif result["classification"]["memory_tier"] == "working":
                results["stored_working"] += 1

        # Detect patterns
        patterns = self.detect_patterns(observations)
        results["patterns_detected"] = patterns

        logger.info(f"Batch sync complete: {results['processed']} processed, "
                   f"{results['stored_episodic']} episodic, "
                   f"{len(patterns)} patterns")

        return results


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Memory Bridge")
    parser.add_argument("--sync", action="store_true", help="Run batch sync")
    parser.add_argument("--limit", type=int, default=100, help="Sync limit")
    parser.add_argument("--latest", action="store_true", help="Process latest observation")
    parser.add_argument("--patterns", action="store_true", help="Detect patterns only")

    args = parser.parse_args()

    bridge = VisualMemoryBridge()

    if args.sync:
        results = bridge.run_batch_sync(args.limit)
        print(json.dumps(results, indent=2))

    elif args.latest:
        obs = bridge.get_latest_observation()
        if obs:
            result = bridge.process_and_store({"data": obs})
            print(json.dumps(result, indent=2))
        else:
            print("No observation available")

    elif args.patterns:
        observations = bridge.get_recent_observations(args.limit)
        patterns = bridge.detect_patterns(observations)
        print(json.dumps(patterns, indent=2))

    else:
        # Show status
        obs = bridge.get_latest_observation()
        if obs:
            classification = bridge.classify_for_memory(obs)
            print("Latest observation:")
            print(f"  Scene: {obs.get('scene_context', 'unknown')}")
            print(f"  Summary: {obs.get('summary', 'N/A')}")
            print(f"  Significance: {classification['significance']:.2f}")
            print(f"  Memory tier: {classification['memory_tier']}")
            print(f"  Tags: {', '.join(classification['tags'])}")


if __name__ == "__main__":
    main()
