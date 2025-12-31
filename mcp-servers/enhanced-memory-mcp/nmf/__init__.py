"""
Neural Memory Fabric - Modular Package

Extracted from neural_memory_fabric.py (1,679 lines) for better maintainability.

Package structure:
- config.py: Configuration, enums (MemoryTier, RetrievalMode), MemoryUnit dataclass
- backends.py: Backend initialization (SQLite, Qdrant, Neo4j, Redis, filesystem)
- intelligence.py: LLM features (keywords, context, importance, re-ranking)
- graph_ops.py: Phase 3 graph operations (nodes, edges, traversal, linking)
- consolidation.py: Phase 4 memory consolidation
- core.py: NeuralMemoryFabric main class

Usage:
    from nmf import get_nmf, NeuralMemoryFabric, MemoryTier, RetrievalMode

    # Get singleton instance
    nmf = await get_nmf()

    # Store a memory
    result = await nmf.remember("Important information", agent_id="my_agent")

    # Recall memories
    results = await nmf.recall("search query", mode="hybrid")
"""

from typing import Optional

from .config import (
    MemoryTier,
    RetrievalMode,
    MemoryUnit,
    load_config,
    logger,
)

from .backends import (
    init_sqlite,
    init_vector_db,
    init_graph_db,
    init_redis,
    store_to_filesystem,
)

from .intelligence import (
    extract_keywords_llm,
    generate_context_description_llm,
    calculate_importance_llm,
    llm_rerank_results,
    generate_cluster_summary,
)

from .graph_ops import (
    create_graph_node,
    create_temporal_edge,
    find_related_memories,
    create_dynamic_links,
    traverse_graph,
    enrich_with_graph_traversal,
    temporal_query,
)

from .consolidation import (
    consolidate_memories,
)

from .core import (
    NeuralMemoryFabric,
)


# Singleton instance
_nmf_instance: Optional[NeuralMemoryFabric] = None


async def get_nmf() -> NeuralMemoryFabric:
    """Get or create NMF singleton instance."""
    global _nmf_instance
    if _nmf_instance is None:
        _nmf_instance = NeuralMemoryFabric()
        await _nmf_instance.initialize()
    return _nmf_instance


__all__ = [
    # Config
    'MemoryTier',
    'RetrievalMode',
    'MemoryUnit',
    'load_config',
    'logger',
    # Backends
    'init_sqlite',
    'init_vector_db',
    'init_graph_db',
    'init_redis',
    'store_to_filesystem',
    # Intelligence
    'extract_keywords_llm',
    'generate_context_description_llm',
    'calculate_importance_llm',
    'llm_rerank_results',
    'generate_cluster_summary',
    # Graph ops
    'create_graph_node',
    'create_temporal_edge',
    'find_related_memories',
    'create_dynamic_links',
    'traverse_graph',
    'enrich_with_graph_traversal',
    'temporal_query',
    # Consolidation
    'consolidate_memories',
    # Core
    'NeuralMemoryFabric',
    # Singleton
    'get_nmf',
]
