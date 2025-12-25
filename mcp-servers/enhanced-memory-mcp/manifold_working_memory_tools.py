#!/usr/bin/env python3
"""
Manifold Working Memory MCP Tools Registration (PTM Phase 4)

Registers MCP tools for manifold-based working memory:
1. manifold_allocate - Allocate slot on T^8 manifold
2. manifold_retrieve - Retrieve slot by ID
3. manifold_search - Resonance-based search
4. manifold_retrieve_context - Get all slots in context
5. manifold_decay - Apply global decay
6. manifold_gc - Run garbage collection
7. manifold_stats - Get memory statistics
8. manifold_interference - Direct phase-based query

Integration point for server.py tool registration.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def register_manifold_working_memory_tools(app):
    """
    Register manifold working memory tools with FastMCP.

    Args:
        app: FastMCP application instance
    """
    # Import components
    try:
        from manifold_working_memory import (
            ManifoldWorkingMemory,
            ManifoldSlot,
            get_manifold_working_memory,
            reset_manifold_working_memory,
            MANIFOLD_DIM,
            RESONANCE_THRESHOLD
        )
        import numpy as np

        MANIFOLD_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Manifold working memory not available: {e}")
        MANIFOLD_AVAILABLE = False

    @app.tool()
    async def manifold_allocate(
        content: str,
        context_key: str = "default",
        priority: int = 5,
        entity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Allocate a slot on the T^8 manifold working memory.

        PTM Phase 4: Items are positioned on an 8-dimensional hyper-torus
        based on context and content hash. Related items cluster together
        in phase space for efficient associative retrieval.

        Args:
            content: Memory content to store
            context_key: Context for grouping (maps to manifold region)
            priority: Priority level 1-10 (default: 5)
            entity_id: Optional linked entity ID
            metadata: Optional additional metadata

        Returns:
            Dict with slot details including phase position
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available"
            }

        try:
            memory = get_manifold_working_memory()
            slot = memory.allocate(
                content=content,
                context_key=context_key,
                priority=priority,
                entity_id=entity_id,
                metadata=metadata or {}
            )

            return {
                "success": True,
                "slot_id": slot.slot_id,
                "phases": slot.phases.tolist(),
                "context_key": slot.context_key,
                "energy": slot.energy,
                "metadata": {
                    "manifold_dim": MANIFOLD_DIM,
                    "current_slots": len(memory.slots)
                }
            }

        except Exception as e:
            logger.error(f"Error in manifold_allocate: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def manifold_retrieve(slot_id: int) -> Dict[str, Any]:
        """
        Retrieve a slot by ID with energy boost.

        Access boosts the slot's energy, keeping it active longer.
        Expired slots return None.

        Args:
            slot_id: Slot ID to retrieve

        Returns:
            Dict with slot details or error if not found
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available"
            }

        try:
            memory = get_manifold_working_memory()
            slot = memory.retrieve(slot_id)

            if slot:
                return {
                    "success": True,
                    "slot": slot.to_dict()
                }
            else:
                return {
                    "success": False,
                    "error": f"Slot {slot_id} not found or expired"
                }

        except Exception as e:
            logger.error(f"Error in manifold_retrieve: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def manifold_search(
        query: str,
        context_key: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Resonance-based search on the manifold.

        Finds slots with similar phase positions to query.
        This implements associative/content-addressable retrieval
        using phase proximity in the 8D hyper-torus space.

        Args:
            query: Query text (converted to phase position)
            context_key: Optional context to narrow search
            limit: Maximum results (default: 10)
            threshold: Minimum similarity threshold (default: 0.5)

        Returns:
            Dict with matching slots and similarity scores
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available",
                "results": []
            }

        try:
            memory = get_manifold_working_memory()
            results = memory.resonance_search(
                query=query,
                context_key=context_key,
                limit=limit,
                threshold=threshold
            )

            return {
                "success": True,
                "query": query,
                "context_key": context_key,
                "count": len(results),
                "results": [
                    {
                        "slot": slot.to_dict(),
                        "similarity": round(sim, 4)
                    }
                    for slot, sim in results
                ],
                "metadata": {
                    "strategy": "resonance_search",
                    "manifold_dim": MANIFOLD_DIM,
                    "threshold": threshold
                }
            }

        except Exception as e:
            logger.error(f"Error in manifold_search: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    @app.tool()
    async def manifold_retrieve_context(
        context_key: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieve all slots in a context region.

        Returns slots sorted by priority * energy (effective importance).
        Context regions cluster related memories together on the manifold.

        Args:
            context_key: Context key to retrieve
            limit: Maximum results (default: 50)

        Returns:
            Dict with slots in the context
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available",
                "slots": []
            }

        try:
            memory = get_manifold_working_memory()
            slots = memory.retrieve_by_context(context_key, limit)

            # Get context centroid
            centroid = memory.get_context_centroid(context_key)

            return {
                "success": True,
                "context_key": context_key,
                "count": len(slots),
                "slots": [slot.to_dict() for slot in slots],
                "centroid": centroid.tolist() if centroid is not None else None,
                "metadata": {
                    "manifold_dim": MANIFOLD_DIM
                }
            }

        except Exception as e:
            logger.error(f"Error in manifold_retrieve_context: {e}")
            return {
                "success": False,
                "error": str(e),
                "slots": []
            }

    @app.tool()
    async def manifold_interference(
        phases: List[float],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Direct phase-based interference query.

        Query the manifold using raw phase angles for advanced
        manifold operations where query position is known.

        Args:
            phases: 8D phase position (list of 8 floats in [0, 2π))
            limit: Maximum results (default: 10)

        Returns:
            Dict with matching slots by phase proximity
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available",
                "results": []
            }

        try:
            if len(phases) != MANIFOLD_DIM:
                return {
                    "success": False,
                    "error": f"Expected {MANIFOLD_DIM} phases, got {len(phases)}",
                    "results": []
                }

            memory = get_manifold_working_memory()
            query_phases = np.array(phases)
            results = memory.interference_query(query_phases, limit)

            return {
                "success": True,
                "query_phases": phases,
                "count": len(results),
                "results": [
                    {
                        "slot": slot.to_dict(),
                        "similarity": round(sim, 4)
                    }
                    for slot, sim in results
                ],
                "metadata": {
                    "strategy": "interference_query",
                    "manifold_dim": MANIFOLD_DIM
                }
            }

        except Exception as e:
            logger.error(f"Error in manifold_interference: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    @app.tool()
    async def manifold_decay() -> Dict[str, Any]:
        """
        Apply energy decay to all slots based on time elapsed.

        Slots lose energy over time when not accessed.
        Low-energy slots are candidates for garbage collection.

        Returns:
            Dict with decay statistics
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available"
            }

        try:
            memory = get_manifold_working_memory()
            decayed_count = memory.apply_global_decay()

            return {
                "success": True,
                "decayed_slots": decayed_count,
                "current_slots": len(memory.slots)
            }

        except Exception as e:
            logger.error(f"Error in manifold_decay: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def manifold_gc() -> Dict[str, Any]:
        """
        Run garbage collection to remove expired slots.

        Removes slots with energy below MIN_ENERGY threshold.

        Returns:
            Dict with GC statistics
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "success": False,
                "error": "Manifold working memory not available"
            }

        try:
            memory = get_manifold_working_memory()
            removed_count = memory.garbage_collect()

            return {
                "success": True,
                "removed_slots": removed_count,
                "current_slots": len(memory.slots)
            }

        except Exception as e:
            logger.error(f"Error in manifold_gc: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    def manifold_stats() -> Dict[str, Any]:
        """
        Get manifold working memory statistics.

        Returns comprehensive stats including slot count,
        utilization, context distribution, and average energy.

        Returns:
            Dict with memory statistics
        """
        if not MANIFOLD_AVAILABLE:
            return {
                "status": "unavailable",
                "error": "Manifold working memory not available"
            }

        try:
            memory = get_manifold_working_memory()
            stats = memory.get_stats()

            return {
                "status": "ready",
                **stats
            }

        except Exception as e:
            logger.error(f"Error getting manifold stats: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    logger.info("✅ Manifold Working Memory tools registered (PTM Phase 4)")
