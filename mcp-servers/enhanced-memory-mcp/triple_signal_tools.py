#!/usr/bin/env python3
"""
Triple-Signal Search MCP Tools Registration (PTM Phase 3)

Registers MCP tools for triple-signal hybrid search:
1. search_triple_signal - Main search combining vector + lexical + trajectory
2. get_triple_signal_stats - Statistics and configuration
3. build_trajectory_index - Build/rebuild trajectory index from entities
4. search_trajectory_only - Trajectory-only search for comparison/debug

Integration point for server.py tool registration.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def register_triple_signal_tools(app, nmf):
    """
    Register triple-signal search tools with FastMCP.

    Args:
        app: FastMCP application instance
        nmf: NeuralMemoryFabric instance for vector/lexical search
    """
    # Import components
    try:
        from triple_signal_search import (
            TrajectoryIndex,
            TripleSignalSearcher,
            get_trajectory_index,
            get_triple_searcher,
            reset_instances,
            TRAJECTORY_AVAILABLE
        )
        from qdrant_client import QdrantClient

        TRIPLE_SIGNAL_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Triple-signal search not available: {e}")
        TRIPLE_SIGNAL_AVAILABLE = False

    QDRANT_URL = "http://localhost:6333"
    COLLECTION_NAME = "enhanced_memory"

    @app.tool()
    async def search_triple_signal(
        query: str,
        limit: int = 10,
        vector_weight: float = 0.4,
        lexical_weight: float = 0.3,
        trajectory_weight: float = 0.3,
        score_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Search using triple-signal fusion: vector + lexical + trajectory.

        PTM-inspired Phase 3 enhancement combining three retrieval signals
        using extended Reciprocal Rank Fusion (RRF).

        Signals:
        - Vector (40%): Dense semantic embeddings via NMF
        - Lexical (30%): BM25 sparse keyword matching
        - Trajectory (30%): Manifold phase angle similarity on T^8

        Expected improvement: +15-25% precision over dual-signal hybrid search

        Args:
            query: Search query string
            limit: Number of results to return (default: 10)
            vector_weight: Weight for vector signal (default: 0.4)
            lexical_weight: Weight for lexical signal (default: 0.3)
            trajectory_weight: Weight for trajectory signal (default: 0.3)
            score_threshold: Minimum score threshold (optional)

        Returns:
            Dict with fused search results and metadata
        """
        if not TRIPLE_SIGNAL_AVAILABLE:
            return {
                "success": False,
                "error": "Triple-signal search not available",
                "query": query,
                "count": 0,
                "results": []
            }

        try:
            # Get trajectory index and searcher
            traj_index = get_trajectory_index()
            searcher = get_triple_searcher()

            # Update weights if different from defaults
            searcher.weights = {
                "vector": vector_weight,
                "lexical": lexical_weight,
                "trajectory": trajectory_weight
            }

            # 1. Vector search via NMF/Qdrant
            vector_results = []
            try:
                client = QdrantClient(url=QDRANT_URL)

                # Generate query embedding
                if nmf.embedding_manager:
                    embedding_result = await nmf.embedding_manager.generate_embedding(query)

                    if embedding_result and (
                        embedding_result.get("success", True) if isinstance(embedding_result, dict)
                        else getattr(embedding_result, "success", True)
                    ):
                        query_vector = (
                            embedding_result.get("embedding") or embedding_result.get("vector")
                            if isinstance(embedding_result, dict)
                            else getattr(embedding_result, "embedding", embedding_result)
                        )

                        if query_vector:
                            search_results = client.search(
                                collection_name=COLLECTION_NAME,
                                query_vector=("text-dense", query_vector),
                                limit=limit * 2,  # Over-retrieve for fusion
                                with_payload=True
                            )

                            vector_results = [
                                {"id": str(hit.id), "score": hit.score, "payload": hit.payload}
                                for hit in search_results
                            ]
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

            # 2. Lexical search via BM25
            lexical_results = []
            try:
                from fastembed import SparseTextEmbedding
                sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
                sparse_embeddings = list(sparse_model.embed([query]))
                sparse_embedding = sparse_embeddings[0]

                query_sparse = {
                    "indices": sparse_embedding.indices.tolist(),
                    "values": sparse_embedding.values.tolist()
                }

                search_results = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=("text-sparse", query_sparse),
                    limit=limit * 2,
                    with_payload=True
                )

                lexical_results = [
                    {"id": str(hit.id), "score": hit.score, "payload": hit.payload}
                    for hit in search_results
                ]
            except Exception as e:
                logger.warning(f"Lexical search failed: {e}")

            # 3. Trajectory search
            trajectory_results = []
            try:
                # Ensure index is populated
                if traj_index._stats["indexed_entities"] == 0:
                    traj_index.load_from_db(limit=5000)

                trajectory_results = traj_index.search(query, limit=limit * 2)
            except Exception as e:
                logger.warning(f"Trajectory search failed: {e}")

            # 4. Fuse all three signals
            fused_results = searcher.fuse_results(
                vector_results,
                lexical_results,
                trajectory_results,
                limit=limit
            )

            # Apply score threshold if specified
            if score_threshold:
                fused_results = [r for r in fused_results if r["score"] >= score_threshold]

            return {
                "success": True,
                "query": query,
                "count": len(fused_results),
                "results": fused_results,
                "metadata": {
                    "strategy": "triple_signal_rrf",
                    "signals": {
                        "vector": {"count": len(vector_results), "weight": vector_weight},
                        "lexical": {"count": len(lexical_results), "weight": lexical_weight},
                        "trajectory": {"count": len(trajectory_results), "weight": trajectory_weight}
                    },
                    "trajectory_index_size": traj_index._stats["indexed_entities"],
                    "rrf_k": searcher.RRF_K
                }
            }

        except Exception as e:
            logger.error(f"Error in search_triple_signal: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "results": []
            }

    @app.tool()
    async def search_trajectory_only(
        query: str,
        limit: int = 10,
        threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search using trajectory similarity only (for debugging/comparison).

        Uses manifold-based phase angle matching on T^8 hyper-torus.
        O(n) search with small constant, no external dependencies.

        Args:
            query: Search query string
            limit: Number of results (default: 10)
            threshold: Minimum similarity threshold (default: 0.0)

        Returns:
            Dict with trajectory search results
        """
        if not TRIPLE_SIGNAL_AVAILABLE:
            return {
                "success": False,
                "error": "Trajectory search not available",
                "query": query,
                "count": 0,
                "results": []
            }

        try:
            traj_index = get_trajectory_index()

            # Ensure index is populated
            if traj_index._stats["indexed_entities"] == 0:
                loaded = traj_index.load_from_db(limit=5000)
                logger.info(f"Loaded {loaded} entities into trajectory index")

            results = traj_index.search(query, limit=limit, threshold=threshold)

            formatted_results = [
                {
                    "entity_id": entity_id,
                    "entity_name": vec.entity_name,
                    "score": score,
                    "anchor_count": vec.anchor_count,
                    "point_count": vec.point_count
                }
                for entity_id, score, vec in results
            ]

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "results": formatted_results,
                "metadata": {
                    "strategy": "trajectory_only",
                    "index_size": traj_index._stats["indexed_entities"],
                    "manifold_dim": 8
                }
            }

        except Exception as e:
            logger.error(f"Error in search_trajectory_only: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "results": []
            }

    @app.tool()
    async def build_trajectory_index(
        limit: int = 10000,
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Build or rebuild the trajectory index from entities.

        Loads entities from database and computes trajectory vectors
        for each one. Required before using trajectory search.

        Args:
            limit: Maximum entities to index (default: 10000)
            force_rebuild: Force rebuild even if index exists (default: False)

        Returns:
            Dict with build status and statistics
        """
        if not TRIPLE_SIGNAL_AVAILABLE:
            return {
                "success": False,
                "error": "Trajectory indexing not available"
            }

        try:
            if force_rebuild:
                reset_instances()

            traj_index = get_trajectory_index()

            # Skip if already populated and not forcing rebuild
            if not force_rebuild and traj_index._stats["indexed_entities"] > 0:
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "Index already populated",
                    "indexed_entities": traj_index._stats["indexed_entities"]
                }

            loaded = traj_index.load_from_db(limit=limit)

            return {
                "success": True,
                "action": "built",
                "indexed_entities": loaded,
                "stats": traj_index.get_stats()
            }

        except Exception as e:
            logger.error(f"Error building trajectory index: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    def get_triple_signal_stats() -> Dict[str, Any]:
        """
        Get triple-signal search statistics and configuration.

        Returns:
            Dict with index stats, searcher stats, and configuration
        """
        if not TRIPLE_SIGNAL_AVAILABLE:
            return {
                "status": "unavailable",
                "error": "Triple-signal search not available"
            }

        try:
            traj_index = get_trajectory_index()
            searcher = get_triple_searcher()

            return {
                "status": "ready",
                "trajectory_index": traj_index.get_stats(),
                "searcher": searcher.get_stats(),
                "qdrant": {
                    "url": QDRANT_URL,
                    "collection": COLLECTION_NAME
                }
            }

        except Exception as e:
            logger.error(f"Error getting triple-signal stats: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    logger.info("✅ Triple-signal search tools registered (PTM Phase 3)")
