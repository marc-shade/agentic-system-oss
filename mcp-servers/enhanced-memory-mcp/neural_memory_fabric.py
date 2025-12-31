#!/usr/bin/env python3
"""
Neural Memory Fabric - Core Module

FACADE MODULE - This file maintains backward compatibility.
All implementations have been moved to the nmf/ package.

Integrates multiple memory backends for the most advanced agentic memory system.

Refactored Structure (1,679 lines -> modular package):
- nmf/config.py: Configuration, enums (MemoryTier, RetrievalMode), MemoryUnit
- nmf/backends.py: Backend initialization (SQLite, Qdrant, Neo4j, Redis)
- nmf/intelligence.py: LLM features (keywords, context, importance, re-ranking)
- nmf/graph_ops.py: Phase 3 graph operations (nodes, edges, traversal, linking)
- nmf/consolidation.py: Phase 4 memory consolidation
- nmf/core.py: NeuralMemoryFabric main class
"""

# =============================================================================
# Re-export everything from nmf package for backward compatibility
# =============================================================================

from nmf import (
    # Config
    MemoryTier,
    RetrievalMode,
    MemoryUnit,
    load_config,
    logger,
    # Backends
    init_sqlite,
    init_vector_db,
    init_graph_db,
    init_redis,
    store_to_filesystem,
    # Intelligence
    extract_keywords_llm,
    generate_context_description_llm,
    calculate_importance_llm,
    llm_rerank_results,
    generate_cluster_summary,
    # Graph ops
    create_graph_node,
    create_temporal_edge,
    find_related_memories,
    create_dynamic_links,
    traverse_graph,
    enrich_with_graph_traversal,
    temporal_query,
    # Consolidation
    consolidate_memories,
    # Core
    NeuralMemoryFabric,
    # Singleton
    get_nmf,
)


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
