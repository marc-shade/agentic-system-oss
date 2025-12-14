#!/usr/bin/env python3
"""
GraphRAG MCP Tools

Provides graph-enhanced retrieval tools for enhanced-memory MCP server.
Integrates Microsoft GraphRAG patterns with existing memory system.

Features:
- Graph-enhanced search (vector + graph traversal)
- Entity relationship management
- Neighbor exploration with depth control
- Graph statistics and analytics

Research basis:
- Microsoft GraphRAG: Knowledge graph-based retrieval
- "You're Doing Memory All Wrong" (Zapai): Graph traversal patterns
- Anthropic Contextual Retrieval: Context-aware chunk enhancement
"""
import platform

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Get agentic system path from environment
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))


def register_graphrag_tools(app, db_path: Path = None):
    """
    Register GraphRAG tools with the FastMCP app.

    Args:
        app: FastMCP application instance
        db_path: Path to SQLite database (defaults to enhanced-memory DB)
    """
    # Import GraphRAG implementation from scripts
    sys.path.insert(0, os.path.join(AGENTIC_SYSTEM_PATH, "scripts"))

    # Import using importlib to handle hyphenated filename
    import importlib.util

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

    spec = importlib.util.spec_from_file_location(
        "graph_rag",
        os.path.join(AGENTIC_SYSTEM_PATH, "scripts", "graph-rag.py")
    )
    graph_rag_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(graph_rag_module)
    GraphRAG = graph_rag_module.GraphRAG

    # Initialize GraphRAG instance
    if db_path is None:
        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

    rag = GraphRAG(db_path=db_path)
    logger.info(f"✅ GraphRAG initialized with database: {db_path}")

    @app.tool()
    async def graph_enhanced_search(
        query: str,
        depth: int = 2,
        limit: int = 10,
        include_neighbors: bool = True,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4
    ) -> Dict[str, Any]:
        """
        Search memories with graph relationship expansion.

        Combines vector similarity with graph centrality for richer results.
        Each result includes connected neighbors for context.

        Process:
        1. Vector search in Qdrant for initial results
        2. Expand context via graph traversal
        3. Re-rank by combined vector + graph centrality scores

        Args:
            query: Search query
            depth: How many hops to traverse (1-3, default: 2)
            limit: Max results to return (default: 10)
            include_neighbors: Include neighbor entities in results (default: True)
            vector_weight: Weight for vector similarity 0.0-1.0 (default: 0.6)
            graph_weight: Weight for graph centrality 0.0-1.0 (default: 0.4)

        Returns:
            Results with vector scores, graph scores, and neighbor context

        Example:
            results = await graph_enhanced_search(
                query="TRAP framework",
                depth=2,
                include_neighbors=True
            )
        """
        try:
            # Validate inputs
            depth = max(1, min(3, depth))  # Clamp to 1-3
            vector_weight = max(0.0, min(1.0, vector_weight))
            graph_weight = max(0.0, min(1.0, graph_weight))

            # Normalize weights if they don't sum to 1.0
            total_weight = vector_weight + graph_weight
            if total_weight > 0:
                vector_weight /= total_weight
                graph_weight /= total_weight

            # Execute graph-enhanced search
            results = rag.graph_enhanced_search(
                query=query,
                include_neighbors=include_neighbors,
                depth=depth,
                vector_weight=vector_weight,
                graph_weight=graph_weight,
                limit=limit
            )

            # Format results for MCP
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'entity_id': result.entity_id,
                    'entity_name': result.entity_name,
                    'entity_type': result.entity_type,
                    'content': result.content,
                    'vector_score': round(result.vector_score, 3),
                    'graph_score': round(result.graph_score, 3),
                    'combined_score': round(result.combined_score, 3),
                    'neighbors': result.neighbors if include_neighbors else [],
                    'neighbor_count': len(result.neighbors) if result.neighbors else 0
                })

            return {
                'success': True,
                'query': query,
                'result_count': len(formatted_results),
                'results': formatted_results,
                'search_params': {
                    'depth': depth,
                    'vector_weight': vector_weight,
                    'graph_weight': graph_weight,
                    'include_neighbors': include_neighbors
                }
            }

        except Exception as e:
            logger.error(f"Graph-enhanced search failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'query': query
            }

    @app.tool()
    async def get_entity_neighbors(
        entity_id: int,
        relation_type: Optional[str] = None,
        direction: str = "both",
        depth: int = 1,
        limit: int = 50,
        min_weight: float = 0.0
    ) -> Dict[str, Any]:
        """
        Get entities connected to a given entity through relationships.

        Args:
            entity_id: Source entity ID
            relation_type: Filter by relationship type (optional)
                         Options: relates_to, causes, part_of, implements, extends, uses, depends_on
            direction: Traversal direction (default: "both")
                      Options: "outbound" (entity -> others), "inbound" (others -> entity), "both"
            depth: Traversal depth 1-3 (default: 1)
            limit: Max neighbors to return (default: 50)
            min_weight: Minimum relationship weight 0.0-1.0 (default: 0.0)

        Returns:
            List of connected entities with relationship metadata

        Example:
            neighbors = await get_entity_neighbors(
                entity_id=42,
                relation_type="causes",
                direction="outbound"
            )
        """
        try:
            # Validate inputs
            depth = max(1, min(3, depth))
            min_weight = max(0.0, min(1.0, min_weight))

            if direction not in ["outbound", "inbound", "both"]:
                direction = "both"

            if depth == 1:
                # Simple neighbor query
                neighbors = rag.get_neighbors(
                    entity_id=entity_id,
                    rel_type=relation_type,
                    direction=direction,
                    min_weight=min_weight
                )
                neighbors = neighbors[:limit]

            else:
                # Multi-hop traversal
                context_map = rag.expand_graph_context(
                    entity_ids=[entity_id],
                    depth=depth,
                    min_weight=min_weight
                )
                neighbors = context_map.get(entity_id, [])

                # Filter by relation type if specified
                if relation_type:
                    neighbors = [n for n in neighbors if n.get('relation') == relation_type]

                neighbors = neighbors[:limit]

            return {
                'success': True,
                'entity_id': entity_id,
                'neighbor_count': len(neighbors),
                'neighbors': neighbors,
                'search_params': {
                    'relation_type': relation_type,
                    'direction': direction,
                    'depth': depth,
                    'min_weight': min_weight
                }
            }

        except Exception as e:
            logger.error(f"Get entity neighbors failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'entity_id': entity_id
            }

    @app.tool()
    async def add_entity_relationship(
        source_id: int,
        target_id: int,
        relation_type: str,
        weight: float = 1.0,
        is_causal: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Relationship type
                         Options: relates_to, causes, part_of, implements, extends, uses, depends_on
            weight: Relationship strength 0.0-1.0 (default: 1.0)
            is_causal: Whether this is a causal relationship (default: False)
            context: Additional context metadata (optional)

        Returns:
            Relationship ID and confirmation

        Example:
            rel = await add_entity_relationship(
                source_id=1,
                target_id=2,
                relation_type="causes",
                weight=0.8,
                is_causal=True,
                context={"discovered_by": "pattern_extraction"}
            )
        """
        try:
            # Validate weight
            weight = max(0.0, min(1.0, weight))

            # Add relationship
            rel_id = rag.add_relationship(
                source_id=source_id,
                target_id=target_id,
                rel_type=relation_type,
                weight=weight,
                is_causal=is_causal,
                context=context
            )

            return {
                'success': True,
                'relationship_id': rel_id,
                'source_id': source_id,
                'target_id': target_id,
                'relation_type': relation_type,
                'weight': weight,
                'is_causal': is_causal
            }

        except Exception as e:
            logger.error(f"Add entity relationship failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'source_id': source_id,
                'target_id': target_id
            }

    @app.tool()
    async def get_graph_statistics() -> Dict[str, Any]:
        """
        Get knowledge graph statistics.

        Returns:
            Entity count, relationship count, relationship type distribution,
            average connections per entity, graph density, Qdrant status

        Example:
            stats = await get_graph_statistics()
            print(f"Graph has {stats['entities']} entities and {stats['relationships']} relationships")
        """
        try:
            stats = rag.get_statistics()

            return {
                'success': True,
                'statistics': stats,
                'health': {
                    'entities': stats['entities'],
                    'relationships': stats['relationships'],
                    'avg_relationships_per_entity': stats['avg_relationships_per_entity'],
                    'causal_relationships': stats['causal_relationships'],
                    'qdrant_status': 'connected' if stats['qdrant_connected'] else 'disconnected'
                }
            }

        except Exception as e:
            logger.error(f"Get graph statistics failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    @app.tool()
    async def extract_entity_relationships(
        entity_id: int
    ) -> Dict[str, Any]:
        """
        Extract and store relationships from an entity's observations.

        Automatically discovers relationships by analyzing observation text for patterns like:
        - "X causes Y"
        - "X implements Y"
        - "X relates to Y"
        - "X is part of Y"
        - "X extends Y"

        Args:
            entity_id: Entity ID to process

        Returns:
            Number of relationships extracted and stored

        Example:
            result = await extract_entity_relationships(entity_id=42)
            print(f"Extracted {result['relationships_found']} relationships")
        """
        try:
            count = rag.extract_relationships_from_entity(entity_id)

            return {
                'success': True,
                'entity_id': entity_id,
                'relationships_found': count
            }

        except Exception as e:
            logger.error(f"Extract entity relationships failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'entity_id': entity_id
            }

    @app.tool()
    async def extract_all_relationships(
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract relationships from all entities that haven't been processed yet.

        Runs automatic relationship extraction across the entire knowledge base.
        This can take time for large databases.

        Args:
            limit: Maximum entities to process (None = all unprocessed entities)

        Returns:
            Statistics about extraction process

        Example:
            result = await extract_all_relationships(limit=100)
            print(f"Processed {result['total_processed']} entities")
            print(f"Found {result['total_relationships']} relationships")
        """
        try:
            stats = rag.extract_all_relationships(limit=limit)

            return {
                'success': True,
                'statistics': stats,
                'summary': f"Processed {stats['total_processed']} entities, "
                          f"found {stats['total_relationships']} relationships in "
                          f"{stats['entities_with_relationships']} entities"
            }

        except Exception as e:
            logger.error(f"Extract all relationships failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    @app.tool()
    async def build_local_graph(
        entity_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Build a subgraph for a set of entities.

        Returns nodes and edges for visualization or analysis.
        Useful for understanding relationship structure around specific entities.

        Args:
            entity_ids: List of entity IDs to include in subgraph

        Returns:
            Graph structure with nodes and edges

        Example:
            graph = await build_local_graph(entity_ids=[1, 2, 3, 4, 5])
            print(f"Subgraph has {graph['node_count']} nodes and {graph['edge_count']} edges")
        """
        try:
            graph = rag.build_local_graph(entity_ids)

            return {
                'success': True,
                'graph': graph,
                'node_count': graph['node_count'],
                'edge_count': graph['edge_count']
            }

        except Exception as e:
            logger.error(f"Build local graph failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'entity_ids': entity_ids
            }

    logger.info("✅ GraphRAG tools registered successfully")
    return rag  # Return instance for potential reuse


# Example usage and documentation
__doc__ += """

Usage Examples
--------------

1. Graph-Enhanced Search:
   Search with graph expansion for richer context:

   results = await graph_enhanced_search(
       query="TRAP framework",
       depth=2,
       include_neighbors=True
   )

2. Explore Relationships:
   Find what an entity is connected to:

   neighbors = await get_entity_neighbors(
       entity_id=42,
       relation_type="causes",
       direction="outbound"
   )

3. Add Manual Relationships:
   Create explicit connections:

   rel = await add_entity_relationship(
       source_id=1,
       target_id=2,
       relation_type="implements",
       weight=0.9
   )

4. Auto-Extract Relationships:
   Discover relationships from text:

   stats = await extract_all_relationships(limit=100)

5. Graph Analytics:
   Get overview statistics:

   stats = await get_graph_statistics()

Relationship Types
------------------
- relates_to: General association
- causes: Causal relationship (A causes B)
- part_of: Hierarchical (A is part of B)
- implements: Implementation (A implements B)
- extends: Extension (A extends B)
- uses: Dependency (A uses B)
- depends_on: Strong dependency (A depends on B)

Performance Notes
-----------------
- Graph traversal depth: Keep ≤ 3 for performance
- Large extractions: Use limit parameter to batch
- Weight filtering: Use min_weight to reduce noise
- Qdrant integration: Vector search when available, text fallback otherwise
"""
