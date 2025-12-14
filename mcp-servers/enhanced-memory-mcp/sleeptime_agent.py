#!/usr/bin/env python3
"""
Sleeptime Agent for Background Memory Consolidation

Inspired by Letta's sleeptime agent architecture, this agent runs in the background
to consolidate memories without interrupting the main agent's conversation flow.

Architecture:
- Shares memory blocks with primary agent
- Runs periodically (hourly or on-demand)
- Consolidates episodic → semantic memories
- Discovers causal patterns
- Updates "learnings" memory block
- Compresses old memories

Workflow:
1. Monitor episodic memories (recent experiences)
2. Extract patterns using pattern extraction
3. Create semantic concepts from patterns
4. Discover causal relationships
5. Update shared "learnings" block
6. Compress old low-importance memories

Based on:
- Letta's VoiceSleeptimeAgent pattern
- Our existing autonomous consolidation design
- Human sleep consolidation research
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from letta_memory_blocks import MemoryBlockManager

logger = logging.getLogger(__name__)

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class SleetimeAgent:
    """
    Background agent for memory consolidation.

    Runs periodically to:
    1. Extract patterns from episodic memories
    2. Create semantic concepts
    3. Discover causal relationships
    4. Update learnings block
    5. Compress old memories
    """

    def __init__(
        self,
        agent_id: str = None,
        db_path: Path = DB_PATH,
        consolidation_interval_hours: int = 1
    ):
        import socket
        if agent_id is None:
            agent_id = os.environ.get("NODE_ID", socket.gethostname())
        self.agent_id = agent_id
        self.db_path = db_path
        self.consolidation_interval = consolidation_interval_hours
        self.block_manager = MemoryBlockManager(db_path)

        # Initialize learnings block if it doesn't exist
        self._ensure_learnings_block()

        logger.info(f"🌙 Sleeptime Agent initialized for {agent_id}")
        logger.info(f"   Consolidation interval: {consolidation_interval_hours} hours")

    def _ensure_learnings_block(self):
        """Ensure agent has a 'learnings' memory block"""
        block = self.block_manager.get_block(self.agent_id, "learnings")

        if not block:
            self.block_manager.create_block(
                agent_id=self.agent_id,
                label="learnings",
                description="Recent insights and patterns learned from experiences",
                initial_value="",
                limit=3000,
                read_only=False
            )
            logger.info(f"   Created 'learnings' block for {self.agent_id}")

    def get_recent_episodic_memories(
        self,
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get episodic memories from the last N hours.

        Returns list of entity observations with episodic tier.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        cursor.execute('''
            SELECT e.id, e.name, e.entity_type, o.content, o.created_at
            FROM entities e
            JOIN observations o ON e.id = o.entity_id
            WHERE e.tier = 'episodic'
              AND datetime(o.created_at) > datetime(?)
            ORDER BY o.created_at DESC
        ''', (cutoff_time,))

        memories = []
        for row in cursor.fetchall():
            memories.append({
                "entity_id": row[0],
                "name": row[1],
                "entity_type": row[2],
                "observation": row[3],
                "timestamp": row[4]
            })

        conn.close()

        logger.info(f"   Retrieved {len(memories)} episodic memories from last {time_window_hours}h")
        return memories

    def extract_patterns(
        self,
        memories: List[Dict[str, Any]],
        min_frequency: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extract recurring patterns from episodic memories.

        Looks for:
        - Repeated action types
        - Common outcomes
        - Success/failure patterns
        - Recurring contexts
        """
        patterns = []

        # Group by entity type
        type_groups = {}
        for memory in memories:
            entity_type = memory["entity_type"]
            if entity_type not in type_groups:
                type_groups[entity_type] = []
            type_groups[entity_type].append(memory)

        # Find patterns in each group
        for entity_type, group_memories in type_groups.items():
            if len(group_memories) >= min_frequency:
                # Extract common terms from observations
                all_observations = " ".join([m["observation"] for m in group_memories])

                # Simple pattern: count success/failure
                success_count = all_observations.lower().count("success")
                failure_count = all_observations.lower().count("fail")

                if success_count >= min_frequency or failure_count >= min_frequency:
                    patterns.append({
                        "type": entity_type,
                        "frequency": len(group_memories),
                        "success_count": success_count,
                        "failure_count": failure_count,
                        "observations": all_observations[:500]  # Sample
                    })

        logger.info(f"   Extracted {len(patterns)} patterns (min_frequency={min_frequency})")
        return patterns

    def create_semantic_concepts(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Convert patterns into semantic concepts.

        Creates entities in semantic tier with learned concepts.
        """
        concepts_created = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for pattern in patterns:
            concept_name = f"concept_{pattern['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create semantic entity
            try:
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, tier)
                    VALUES (?, ?, ?)
                ''', (concept_name, "learned_concept", "semantic"))

                entity_id = cursor.lastrowid

                # Add observations
                observation = f"""
Pattern Type: {pattern['type']}
Frequency: {pattern['frequency']} occurrences
Success Rate: {pattern['success_count']} successes, {pattern['failure_count']} failures
Sample: {pattern['observations']}
Learned: {datetime.now().isoformat()}
                """.strip()

                cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (entity_id, observation))

                concepts_created.append(concept_name)
                logger.info(f"   Created semantic concept: {concept_name}")

            except sqlite3.IntegrityError:
                # Concept already exists
                pass

        conn.commit()
        conn.close()

        logger.info(f"   Created {len(concepts_created)} semantic concepts")
        return concepts_created

    def discover_causal_relationships(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Discover causal relationships from memory sequence.

        Looks for:
        - Action → Outcome patterns
        - Temporal sequences
        - Condition → Result patterns
        """
        causal_chains = []

        # Simple heuristic: consecutive memories with action → outcome
        for i in range(len(memories) - 1):
            current = memories[i]
            next_memory = memories[i + 1]

            # Check if current is an action and next is an outcome
            current_obs = current["observation"].lower()
            next_obs = next_memory["observation"].lower()

            if ("action:" in current_obs or "attempting" in current_obs) and \
               ("result:" in next_obs or "outcome:" in next_obs or "success" in next_obs or "fail" in next_obs):
                causal_chains.append({
                    "cause": current["name"],
                    "effect": next_memory["name"],
                    "cause_obs": current["observation"],
                    "effect_obs": next_memory["observation"],
                    "time_delta_seconds": (
                        datetime.fromisoformat(next_memory["timestamp"]) -
                        datetime.fromisoformat(current["timestamp"])
                    ).total_seconds()
                })

        logger.info(f"   Discovered {len(causal_chains)} causal relationships")
        return causal_chains

    def update_learnings_block(
        self,
        patterns: List[Dict[str, Any]],
        concepts: List[str],
        causal_chains: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update the agent's "learnings" memory block with new insights.

        This makes the learnings visible to the primary agent in its context window.
        """
        # Build learnings summary
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        learning_summary = f"\n\n📚 Consolidation Update ({timestamp}):\n"

        if patterns:
            learning_summary += f"\n🔍 Patterns Identified: {len(patterns)}\n"
            for pattern in patterns[:3]:  # Top 3
                success_rate = pattern['success_count'] / max(pattern['frequency'], 1) * 100
                learning_summary += f"  - {pattern['type']}: {pattern['frequency']} occurrences, {success_rate:.0f}% success\n"

        if concepts:
            learning_summary += f"\n💡 Concepts Learned: {len(concepts)}\n"
            for concept in concepts[:3]:  # Top 3
                learning_summary += f"  - {concept}\n"

        if causal_chains:
            learning_summary += f"\n🔗 Causal Relationships: {len(causal_chains)}\n"
            for chain in causal_chains[:3]:  # Top 3
                learning_summary += f"  - {chain['cause']} → {chain['effect']} ({chain['time_delta_seconds']:.0f}s)\n"

        # Append to learnings block
        result = self.block_manager.append_to_block(
            agent_id=self.agent_id,
            label="learnings",
            content=learning_summary
        )

        logger.info(f"   Updated learnings block: {result['chars_current']}/{result['chars_limit']} chars")
        return result

    def compress_old_memories(
        self,
        age_threshold_days: int = 30,
        min_importance_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Compress old low-importance memories to save space.

        Only compresses episodic memories older than threshold with low importance.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=age_threshold_days)

        # Find old episodic memories
        cursor.execute('''
            SELECT id, name
            FROM entities
            WHERE tier = 'episodic'
              AND datetime(created_at) < datetime(?)
              AND compressed_data IS NULL
        ''', (cutoff_date,))

        candidates = cursor.fetchall()
        compressed_count = 0

        # For now, just mark for compression (actual compression would happen here)
        # In production, this would use the caveman compression from compression_integration.py

        logger.info(f"   Found {len(candidates)} candidates for compression (>{age_threshold_days} days old)")

        conn.close()

        return {
            "candidates": len(candidates),
            "compressed": compressed_count,
            "age_threshold_days": age_threshold_days
        }

    def run_consolidation_cycle(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Run full consolidation cycle (like sleep consolidation).

        This is the main method that orchestrates all consolidation steps.

        Steps:
        1. Retrieve recent episodic memories
        2. Extract patterns
        3. Create semantic concepts
        4. Discover causal relationships
        5. Update learnings block
        6. Compress old memories

        Args:
            time_window_hours: Hours of memory to consolidate (default 24)

        Returns:
            Consolidation results with statistics
        """
        logger.info(f"🌙 Starting consolidation cycle for {self.agent_id}")
        logger.info(f"   Time window: {time_window_hours} hours")

        start_time = datetime.now()

        # Step 1: Get recent episodic memories
        memories = self.get_recent_episodic_memories(time_window_hours)

        if not memories:
            logger.info("   No episodic memories to consolidate")
            return {
                "success": True,
                "message": "No memories to consolidate",
                "agent_id": self.agent_id,
                "time_window_hours": time_window_hours,
                "memories_processed": 0,
                "patterns_found": 0,
                "concepts_created": 0,
                "causal_chains_discovered": 0,
                "learnings_updated": False,
                "compression_candidates": 0,
                "duration_seconds": 0.0,
                "timestamp": datetime.now().isoformat()
            }

        # Step 2: Extract patterns
        patterns = self.extract_patterns(memories, min_frequency=2)

        # Step 3: Create semantic concepts
        concepts = self.create_semantic_concepts(patterns)

        # Step 4: Discover causal relationships
        causal_chains = self.discover_causal_relationships(memories)

        # Step 5: Update learnings block
        learnings_result = self.update_learnings_block(patterns, concepts, causal_chains)

        # Step 6: Compress old memories
        compression_result = self.compress_old_memories(age_threshold_days=30)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        result = {
            "success": True,
            "agent_id": self.agent_id,
            "time_window_hours": time_window_hours,
            "memories_processed": len(memories),
            "patterns_found": len(patterns),
            "concepts_created": len(concepts),
            "causal_chains_discovered": len(causal_chains),
            "learnings_updated": learnings_result["success"],
            "compression_candidates": compression_result["candidates"],
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"✅ Consolidation cycle complete:")
        logger.info(f"   - {len(memories)} memories processed")
        logger.info(f"   - {len(patterns)} patterns extracted")
        logger.info(f"   - {len(concepts)} concepts created")
        logger.info(f"   - {len(causal_chains)} causal chains discovered")
        logger.info(f"   - Duration: {duration:.2f}s")

        return result

    def should_run_consolidation(self) -> bool:
        """
        Check if consolidation should run based on interval.

        Returns True if enough time has passed since last consolidation.
        """
        # Check last consolidation time from database or state file
        # For now, simple implementation - always return True
        # In production, track last_consolidation_time in database
        return True


# Convenience functions for testing
def test_sleeptime_agent():
    """Test sleeptime agent implementation"""
    print("Testing Sleeptime Agent...")

    agent = SleetimeAgent(agent_id="test_agent", consolidation_interval_hours=1)

    # Run consolidation cycle
    result = agent.run_consolidation_cycle(time_window_hours=24)

    print("\nConsolidation Results:")
    print(json.dumps(result, indent=2))

    print("\n✓ Sleeptime agent test complete!")


if __name__ == "__main__":
    test_sleeptime_agent()
