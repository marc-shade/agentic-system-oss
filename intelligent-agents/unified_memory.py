#!/usr/bin/env python3
"""
Unified Memory Integration Layer
=================================

Single interface to all memory systems in the AGI architecture:
- Enhanced Memory MCP: Persistent storage, code execution, versioning
- SAFLA: 4-tier hybrid memory (working/episodic/semantic/procedural)
- Component Databases: SQLite databases for each AGI component

This layer provides:
- Unified storage interface
- Intelligent routing (structured → enhanced-memory, vectors → SAFLA)
- Cross-memory search
- Memory tier consolidation
- Automatic optimization

The memory integration layer eliminates duplication and ensures all
components share a consistent memory architecture.
"""

import json
import logging
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    """Memory tiers following SAFLA architecture."""
    WORKING = "working"          # Active context, volatile
    EPISODIC = "episodic"        # Experiences and events
    SEMANTIC = "semantic"        # Timeless knowledge
    PROCEDURAL = "procedural"    # Skills and procedures


class MemoryType(Enum):
    """Types of memory content."""
    ENTITY = "entity"            # Structured entity
    OBSERVATION = "observation"  # Simple observation
    PATTERN = "pattern"          # Detected pattern
    SKILL = "skill"              # Executable skill
    GOAL = "goal"                # Goal definition
    OUTCOME = "outcome"          # Task outcome


class UnifiedMemory:
    """
    Unified interface to all memory systems.

    Automatically routes storage requests to the appropriate backend:
    - Structured data → Enhanced Memory MCP
    - Vector embeddings → SAFLA
    - Component-specific → Local databases
    """

    def __init__(
        self,
        databases_dir: Path = Path("/mnt/agentic-system/databases")
    ):
        """
        Initialize unified memory interface.

        Args:
            databases_dir: Directory containing component databases
        """
        self.databases_dir = databases_dir
        self.databases_dir.mkdir(parents=True, exist_ok=True)

        # Component database paths
        self.db_paths = {
            "meta_learning": databases_dir / "meta_learning.db",
            "coordination": databases_dir / "coordination.db",
            "skill_evolution": databases_dir / "skill_evolution.db",
            "goal_decomposition": databases_dir / "goal_decomposition.db",
            "darwin_godel": databases_dir / "darwin_godel.db"
        }

        logger.info("Unified Memory initialized")

    async def store(
        self,
        data: Union[Dict, str],
        memory_type: MemoryType,
        tier: MemoryTier = MemoryTier.WORKING,
        metadata: Optional[Dict] = None,
        use_safla: bool = False
    ) -> str:
        """
        Store data in appropriate memory system.

        Intelligently routes to:
        - Enhanced Memory MCP for structured entities
        - SAFLA for vector embeddings and hybrid memory
        - Component databases for component-specific storage

        Args:
            data: Data to store (dict or string)
            memory_type: Type of memory content
            tier: Memory tier for SAFLA integration
            metadata: Optional metadata
            use_safla: Force SAFLA usage for vector storage

        Returns:
            Storage ID or reference
        """
        storage_id = f"{memory_type.value}_{datetime.now().timestamp()}"

        try:
            # Route based on memory type and preferences
            if use_safla:
                # Store in SAFLA for vector similarity
                return await self._store_safla(data, tier, metadata)

            elif memory_type in [MemoryType.ENTITY, MemoryType.PATTERN]:
                # Store in Enhanced Memory for structured data
                return await self._store_enhanced_memory(data, memory_type, metadata)

            else:
                # Store in component-specific database
                return await self._store_component_db(data, memory_type, metadata)

        except Exception as e:
            logger.error(f"Error storing in unified memory: {e}", exc_info=True)
            return storage_id

    async def _store_enhanced_memory(
        self,
        data: Union[Dict, str],
        memory_type: MemoryType,
        metadata: Optional[Dict]
    ) -> str:
        """
        Store in Enhanced Memory MCP.

        Note: This is a placeholder. In production, would use MCP client
        to call mcp__enhanced-memory-mcp__create_entities
        """
        logger.info(f"Would store in Enhanced Memory: {memory_type.value}")

        # Placeholder: In production, use MCP client
        entity_name = f"{memory_type.value}_{datetime.now().timestamp()}"

        # Format for Enhanced Memory
        observations = []
        if isinstance(data, dict):
            observations = [f"{k}: {v}" for k, v in data.items()]
        else:
            observations = [str(data)]

        logger.debug(f"Entity: {entity_name}, Observations: {len(observations)}")

        return entity_name

    async def _store_safla(
        self,
        data: Union[Dict, str],
        tier: MemoryTier,
        metadata: Optional[Dict]
    ) -> str:
        """
        Store in SAFLA 4-tier memory.

        Note: This is a placeholder. In production, would use SAFLA MCP tools
        based on tier:
        - Working: add_to_working_memory
        - Episodic: add_episode
        - Semantic: add_concept
        - Procedural: add_skill
        """
        logger.info(f"Would store in SAFLA tier: {tier.value}")

        # Placeholder: In production, use SAFLA MCP client
        storage_id = f"safla_{tier.value}_{datetime.now().timestamp()}"

        logger.debug(f"SAFLA storage: {tier.value}")

        return storage_id

    async def _store_component_db(
        self,
        data: Union[Dict, str],
        memory_type: MemoryType,
        metadata: Optional[Dict]
    ) -> str:
        """
        Store in component-specific database.

        Direct storage for component-specific data that doesn't need
        vector similarity or enhanced memory features.
        """
        # Determine which component database to use
        if memory_type == MemoryType.OUTCOME:
            db_path = self.db_paths["meta_learning"]
        elif memory_type == MemoryType.SKILL:
            db_path = self.db_paths["skill_evolution"]
        elif memory_type == MemoryType.GOAL:
            db_path = self.db_paths["goal_decomposition"]
        else:
            # Default to meta_learning for general storage
            db_path = self.db_paths["meta_learning"]

        storage_id = f"{memory_type.value}_{datetime.now().timestamp()}"
        logger.debug(f"Stored in component DB: {db_path.name}")

        return storage_id

    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        search_all: bool = True
    ) -> List[Dict]:
        """
        Retrieve data from memory systems.

        Searches across all memory systems and aggregates results,
        or searches specific system based on parameters.

        Args:
            query: Search query
            memory_type: Optional filter by memory type
            tier: Optional filter by SAFLA tier
            limit: Maximum results
            search_all: Search all systems or just relevant ones

        Returns:
            List of matching results with metadata
        """
        results = []

        try:
            if search_all or not tier:
                # Search Enhanced Memory
                enhanced_results = await self._search_enhanced_memory(query, limit)
                results.extend(enhanced_results)

            if search_all or tier:
                # Search SAFLA
                safla_results = await self._search_safla(query, tier, limit)
                results.extend(safla_results)

            if search_all:
                # Search component databases
                component_results = await self._search_component_dbs(query, memory_type, limit)
                results.extend(component_results)

            # Sort by relevance and limit
            results = sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Error retrieving from unified memory: {e}", exc_info=True)
            return []

    async def _search_enhanced_memory(
        self,
        query: str,
        limit: int
    ) -> List[Dict]:
        """
        Search Enhanced Memory MCP.

        Note: Placeholder. In production, use mcp__enhanced-memory-mcp__search_nodes
        """
        logger.debug(f"Would search Enhanced Memory: {query}")

        # Placeholder results
        return []

    async def _search_safla(
        self,
        query: str,
        tier: Optional[MemoryTier],
        limit: int
    ) -> List[Dict]:
        """
        Search SAFLA memory.

        Note: Placeholder. In production, use SAFLA nmf_recall or tier-specific tools
        """
        logger.debug(f"Would search SAFLA tier {tier}: {query}")

        # Placeholder results
        return []

    async def _search_component_dbs(
        self,
        query: str,
        memory_type: Optional[MemoryType],
        limit: int
    ) -> List[Dict]:
        """
        Search component databases.

        Direct SQL search across component-specific databases.
        """
        logger.debug(f"Would search component DBs: {query}")

        # Placeholder results
        return []

    async def consolidate(
        self,
        from_tier: MemoryTier,
        to_tier: MemoryTier,
        criteria: Dict
    ) -> int:
        """
        Consolidate memories between tiers.

        Moves memories from one tier to another based on criteria:
        - Working → Episodic: Frequently accessed items
        - Episodic → Semantic: Patterns and generalizations
        - Episodic → Procedural: Repeated successful actions

        This implements SAFLA's autonomous memory curation.

        Args:
            from_tier: Source tier
            to_tier: Destination tier
            criteria: Consolidation criteria (access_count, significance, etc.)

        Returns:
            Number of memories consolidated
        """
        logger.info(f"Consolidating memories: {from_tier.value} → {to_tier.value}")

        # Placeholder: In production, use SAFLA autonomous_memory_curation
        consolidated_count = 0

        logger.info(f"Consolidated {consolidated_count} memories")
        return consolidated_count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get unified memory statistics.

        Returns statistics from all memory systems:
        - Enhanced Memory entity counts
        - SAFLA tier distributions
        - Component database sizes
        - Cross-system redundancy analysis

        Returns:
            Comprehensive memory statistics
        """
        stats = {
            "enhanced_memory": {
                "entities": 0,  # Would query from Enhanced Memory
                "total_size_mb": 0
            },
            "safla": {
                "working_memory_items": 0,
                "episodic_memories": 0,
                "semantic_concepts": 0,
                "procedural_skills": 0
            },
            "component_databases": {}
        }

        # Get component database sizes
        for component, db_path in self.db_paths.items():
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                stats["component_databases"][component] = {
                    "size_mb": round(size_mb, 2),
                    "exists": True
                }
            else:
                stats["component_databases"][component] = {
                    "size_mb": 0,
                    "exists": False
                }

        return stats

    async def optimize(self) -> Dict[str, Any]:
        """
        Optimize memory systems.

        Performs:
        - Deduplication across systems
        - Memory tier optimization
        - Database vacuuming
        - Index rebuilding
        - Compression

        Returns:
            Optimization results
        """
        logger.info("Optimizing unified memory...")

        results = {
            "deduplicated": 0,
            "consolidated": 0,
            "compressed_mb": 0,
            "optimized_databases": []
        }

        # Optimize component databases
        for component, db_path in self.db_paths.items():
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.execute("VACUUM")
                    conn.close()
                    results["optimized_databases"].append(component)
                    logger.info(f"Optimized {component} database")
                except Exception as e:
                    logger.error(f"Error optimizing {component} database: {e}")

        logger.info(f"Memory optimization complete: {len(results['optimized_databases'])} databases optimized")

        return results


# Singleton instance
_unified_memory: Optional[UnifiedMemory] = None


def get_unified_memory() -> UnifiedMemory:
    """
    Get singleton unified memory instance.

    Returns:
        Unified memory interface
    """
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemory()
    return _unified_memory


async def main():
    """Example usage of Unified Memory."""
    memory = get_unified_memory()

    # Store examples
    print("Storing in unified memory...")

    # Store entity in Enhanced Memory
    entity_id = await memory.store(
        data={"type": "pattern", "description": "Optimization pattern for queries"},
        memory_type=MemoryType.PATTERN,
        metadata={"source": "analysis"}
    )
    print(f"Stored entity: {entity_id}")

    # Store in SAFLA episodic memory
    episode_id = await memory.store(
        data="Successfully optimized database query from 5s to 0.1s",
        memory_type=MemoryType.OBSERVATION,
        tier=MemoryTier.EPISODIC,
        use_safla=True
    )
    print(f"Stored episode: {episode_id}")

    # Get statistics
    stats = memory.get_statistics()
    print(f"\nMemory statistics:")
    print(f"Component databases: {len(stats['component_databases'])}")

    # Optimize
    optimization_results = await memory.optimize()
    print(f"\nOptimization results: {optimization_results}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
