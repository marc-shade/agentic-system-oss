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
import os
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

        Queries BOTH:
        1. entities table (tier='episodic') - older format
        2. episodic_memory table - 4-tier memory format

        Returns list of entity observations for pattern extraction.
        """
        import json as json_lib
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        memories = []

        # Source 1: entities table with episodic tier
        try:
            cursor.execute('''
                SELECT e.id, e.name, e.entity_type, o.content, o.created_at
                FROM entities e
                JOIN observations o ON e.id = o.entity_id
                WHERE e.tier = 'episodic'
                  AND datetime(o.created_at) > datetime(?)
                ORDER BY o.created_at DESC
            ''', (cutoff_time,))

            for row in cursor.fetchall():
                memories.append({
                    "entity_id": row[0],
                    "name": row[1],
                    "entity_type": row[2],
                    "observation": row[3],
                    "timestamp": row[4]
                })
        except Exception as e:
            logger.debug(f"   entities table query failed: {e}")

        # Source 2: episodic_memory table (4-tier memory)
        try:
            cursor.execute('''
                SELECT id, event_type, episode_data, significance_score, created_at
                FROM episodic_memory
                WHERE datetime(created_at) > datetime(?)
                ORDER BY created_at DESC
            ''', (cutoff_time,))

            for row in cursor.fetchall():
                # Parse episode_data JSON for observation content
                episode_data = row[2]
                try:
                    data = json_lib.loads(episode_data) if episode_data else {}
                    observation = json_lib.dumps(data)  # Use full data as observation
                except:
                    observation = str(episode_data)[:500]

                memories.append({
                    "entity_id": row[0],
                    "name": f"episode_{row[0]}",
                    "entity_type": row[1],  # event_type becomes entity_type
                    "observation": observation,
                    "timestamp": row[4],
                    "significance": row[3]
                })
        except Exception as e:
            logger.debug(f"   episodic_memory table query failed: {e}")

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

        Improved pattern detection that:
        - Extracts patterns based on frequency (not just success/fail keywords)
        - Uses word boundaries to avoid false positives (e.g., "error_handling" != "error")
        - Looks for multiple outcome indicators
        - Includes significance scores from episodic memory
        - Works with real JSON-structured episode data
        """
        import re
        patterns = []

        # Group by entity type
        type_groups = {}
        for memory in memories:
            entity_type = memory["entity_type"]
            if entity_type not in type_groups:
                type_groups[entity_type] = []
            type_groups[entity_type].append(memory)

        # Find patterns in each group - ANY type with min_frequency is a pattern
        for entity_type, group_memories in type_groups.items():
            if len(group_memories) >= min_frequency:
                # Extract common terms from observations
                all_observations = " ".join([m.get("observation", "") for m in group_memories])
                obs_lower = all_observations.lower()

                # Count success indicators using word boundaries (avoid "error_handling" matching "error")
                success_keywords = ["success", "completed", "done", "passed", "true", "succeeded", "verified", "passing"]
                success_count = sum(len(re.findall(r'\b' + kw + r'\b', obs_lower)) for kw in success_keywords)

                # Count failure indicators using word boundaries
                failure_keywords = ["fail", "failed", "failure", "error", "false", "crashed", "timeout", "rejected"]
                failure_count = sum(len(re.findall(r'\b' + kw + r'\b', obs_lower)) for kw in failure_keywords)

                # Calculate average significance if available
                significances = [m.get("significance", 0.5) for m in group_memories if m.get("significance")]
                avg_significance = sum(significances) / len(significances) if significances else 0.5

                patterns.append({
                    "type": entity_type,
                    "frequency": len(group_memories),
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "significance": avg_significance,
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

        Uses Librarian-style structured synthesis (adapted from vlt-cli):
        - SYNTHESIZE instead of append (prune obsolete, keep current)
        - Structured format for immediate context resumption
        - Status/Context/Pivot Log/Next Steps sections

        This makes the learnings visible to the primary agent in its context window.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Get existing learnings for synthesis context
        existing_block = self.block_manager.get_block(self.agent_id, "learnings")
        existing_content = existing_block.value if existing_block else ""

        # Build structured learnings state (Librarian pattern)
        # This REPLACES instead of appending - synthesizing new with old

        # Determine active focus from patterns
        if patterns:
            top_pattern = max(patterns, key=lambda p: p['frequency'])
            active_focus = f"{top_pattern['type']} ({top_pattern['frequency']} occurrences)"
        else:
            active_focus = "General learning"

        # Build context section - current truths only
        context_items = []

        # Pattern insights (keep top 5, prune older)
        for pattern in patterns[:5]:
            total_outcomes = pattern['success_count'] + pattern['failure_count']
            if total_outcomes > 0:
                success_rate = pattern['success_count'] / total_outcomes * 100
                rate_str = f", {success_rate:.0f}% success"
            elif pattern.get('significance', 0) > 0:
                rate_str = f", sig={pattern['significance']:.2f}"
            else:
                rate_str = ""
            context_items.append(
                f"- **{pattern['type']}**: {pattern['frequency']}x frequency{rate_str}"
            )

        # Causal relationships (proven cause-effect, top 3)
        for chain in causal_chains[:3]:
            delay = chain['time_delta_seconds']
            context_items.append(
                f"- **Causal**: {chain['cause']} → {chain['effect']} (~{delay:.0f}s delay)"
            )

        # Build pivot log - extract from existing or create new
        pivot_entries = self._extract_pivot_entries(existing_content, patterns, concepts)

        # Build next steps based on weak patterns
        next_steps = self._generate_next_steps(patterns, causal_chains)

        # Synthesize final structured state
        structured_state = f"""# 🎯 Status: Memory Consolidation Active
**Last Update:** {timestamp}
**Focus:** {active_focus}

## 🧠 Context & Current Knowledge
{chr(10).join(context_items) if context_items else "- No significant patterns yet"}

## 💡 Concepts ({len(concepts)} learned)
{chr(10).join([f"- {c}" for c in concepts[:5]]) if concepts else "- Building concept library..."}

## 📜 Pivot Log (Recent Decisions)
{chr(10).join(pivot_entries) if pivot_entries else "- No major pivots recorded"}

## ⏭️ Next Steps
{chr(10).join(next_steps) if next_steps else "- Continue gathering observations"}
"""

        # REPLACE (not append) - the Librarian way
        result = self.block_manager.update_block(
            agent_id=self.agent_id,
            label="learnings",
            new_value=structured_state
        )

        logger.info(f"   Synthesized learnings block: {result['chars_current']}/{result['chars_limit']} chars")
        return result

    def _calculate_success_rate(self, pattern: Dict[str, Any]) -> float:
        """Calculate success rate from pattern, handling various data structures."""
        total_outcomes = pattern['success_count'] + pattern['failure_count']
        if total_outcomes > 0:
            return pattern['success_count'] / total_outcomes
        else:
            # No outcome keywords - use significance or neutral
            return pattern.get('significance', 0.5)

    def _extract_pivot_entries(
        self,
        existing_content: str,
        patterns: List[Dict[str, Any]],
        concepts: List[str]
    ) -> List[str]:
        """
        Extract and update pivot log entries.

        Keeps last 3 major decisions/pivots, pruning older ones.
        A 'pivot' is a significant change in approach or understanding.
        """
        pivot_entries = []

        # Check for significant pattern shifts
        for pattern in patterns:
            success_rate = self._calculate_success_rate(pattern)

            # High frequency + low success rate = potential pivot needed
            if pattern['frequency'] >= 5 and success_rate < 0.3:
                pivot_entries.append(
                    f"- ⚠️ Low success pattern: `{pattern['type']}` ({success_rate:.0%}) - consider approach change"
                )

            # High success rate = validated approach
            elif pattern['frequency'] >= 3 and success_rate > 0.7:
                pivot_entries.append(
                    f"- ✅ Validated: `{pattern['type']}` ({success_rate:.0%} success, {pattern['frequency']}x)"
                )

        # Keep only last 3
        return pivot_entries[:3]

    def _generate_next_steps(
        self,
        patterns: List[Dict[str, Any]],
        causal_chains: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate actionable next steps based on consolidation findings.
        """
        next_steps = []

        # Find weak patterns needing improvement (success rate < 50%)
        weak_patterns = []
        for p in patterns:
            success_rate = self._calculate_success_rate(p)
            if success_rate < 0.5:
                weak_patterns.append((p, success_rate))

        if weak_patterns:
            for wp, rate in weak_patterns[:2]:
                next_steps.append(
                    f"1. Investigate `{wp['type']}` ({rate:.0%} success, {wp['frequency']}x frequency)"
                )

        # Suggest exploring strong causal chains
        if causal_chains:
            strongest = causal_chains[0]
            next_steps.append(
                f"2. Leverage: {strongest['cause']} → {strongest['effect']} chain"
            )

        # Default step if nothing specific
        if not next_steps:
            next_steps.append("1. Continue observations to build pattern database")

        return next_steps

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
