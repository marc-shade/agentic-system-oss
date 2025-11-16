#!/usr/bin/env python3
"""
Hybrid search tools registration for enhanced-memory-mcp using NMF/Qdrant.

UPDATED: Now queries Neural Memory Fabric (Qdrant) directly for hybrid search
This enables BM25 + vector search with RRF fusion.
"""

import logging
from typing import Dict, Any
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enhanced_memory"

def register_hybrid_search_tools_nmf(app, nmf):
    """
    Register hybrid search tools with the FastMCP app using NMF/Qdrant backend.

    Args:
        app: FastMCP application instance
        nmf: NeuralMemoryFabric instance
    """

    @app.tool()
    async def search_hybrid(
        query: str,
        limit: int = 10,
        score_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Search using hybrid BM25 + Vector search with RRF fusion.

        Combines sparse (BM25) lexical matching with dense (vector) semantic
        similarity using Reciprocal Rank Fusion (RRF) for result combination.

        Expected improvement: +20-30% recall over vector-only search

        Args:
            query: Search query string
            limit: Number of results to return (default: 10)
            score_threshold: Minimum score threshold (optional)

        Returns:
            Dict with hybrid search results and metadata
        """
        try:
            # Initialize Qdrant client
            client = QdrantClient(url=QDRANT_URL)

            # Generate dense vector for query using NMF's embedding manager
            if not nmf.embedding_manager:
                return {
                    "success": False,
                    "error": "Embedding manager not available",
                    "query": query,
                    "count": 0,
                    "results": []
                }

            # Generate query embedding
            embedding_result = await nmf.embedding_manager.generate_embedding(query)
            if not embedding_result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to generate query embedding",
                    "query": query,
                    "count": 0,
                    "results": []
                }

            query_vector = embedding_result.embedding if hasattr(embedding_result, 'embedding') else embedding_result

            # Generate sparse vector for query (BM25)
            # Note: This requires fastembed SparseTextEmbedding
            try:
                from fastembed import SparseTextEmbedding
                sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
                sparse_embeddings = list(sparse_model.embed([query]))
                sparse_embedding = sparse_embeddings[0]

                query_sparse = {
                    "indices": sparse_embedding.indices.tolist(),
                    "values": sparse_embedding.values.tolist()
                }
            except Exception as e:
                logger.warning(f"Sparse vector generation failed: {e}, using dense-only")
                query_sparse = None

            # Perform hybrid search
            search_params = {
                "collection_name": COLLECTION_NAME,
                "limit": limit,
                "with_payload": True,
                "with_vectors": False
            }

            if query_sparse:
                # True hybrid search with RRF fusion
                search_params["query"] = {
                    "fusion": "rrf",  # Reciprocal Rank Fusion
                    "prefetch": [
                        {
                            "query": query_vector,
                            "using": "text-dense",
                            "limit": limit * 2
                        },
                        {
                            "query": query_sparse,
                            "using": "text-sparse",
                            "limit": limit * 2
                        }
                    ]
                }
            else:
                # Fallback to dense-only search
                search_params["vector"] = {
                    "name": "text-dense",
                    "vector": query_vector
                }

            if score_threshold:
                search_params["score_threshold"] = score_threshold

            # Execute search
            if query_sparse:
                # Use query_points for hybrid search with RRF fusion
                from qdrant_client.models import Fusion, FusionQuery, Prefetch

                search_results = client.query_points(
                    collection_name=COLLECTION_NAME,
                    prefetch=[
                        Prefetch(query=query_vector, using="text-dense", limit=limit * 2),
                        Prefetch(query=query_sparse, using="text-sparse", limit=limit * 2)
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),
                    limit=limit,
                    with_payload=True,
                    score_threshold=score_threshold
                ).points
            else:
                # Use search for dense-only
                search_results = client.search(**search_params)

            # Format results
            results = []
            for hit in search_results:
                result = {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload
                }
                results.append(result)

            return {
                "success": True,
                "query": query,
                "count": len(results),
                "results": results,
                "metadata": {
                    "strategy": "hybrid_search" if query_sparse else "dense_only",
                    "backend": "qdrant",
                    "collection": COLLECTION_NAME,
                    "fusion": "rrf" if query_sparse else "none",
                    "limit": limit
                }
            }

        except Exception as e:
            logger.error(f"Error in search_hybrid: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "results": []
            }

    @app.tool()
    def get_hybrid_search_stats() -> Dict[str, Any]:
        """
        Get hybrid search system statistics.

        Returns:
            Dict with hybrid search configuration and stats
        """
        try:
            client = QdrantClient(url=QDRANT_URL)

            # Get collection info
            collection_info = client.get_collection(collection_name=COLLECTION_NAME)

            # Check for dense vector support
            vectors_config = collection_info.config.params.vectors
            has_dense = "text-dense" in vectors_config if isinstance(vectors_config, dict) else bool(vectors_config)

            # Check for sparse vector support (separate config field)
            sparse_vectors_config = collection_info.config.params.sparse_vectors
            has_sparse = "text-sparse" in sparse_vectors_config if sparse_vectors_config else False

            return {
                "status": "ready",
                "backend": "qdrant",
                "collection": COLLECTION_NAME,
                "points_count": collection_info.points_count,
                "dense_vectors": has_dense,
                "sparse_vectors": has_sparse,
                "hybrid_enabled": has_dense and has_sparse,
                "fusion_method": "rrf" if has_sparse else "none"
            }

        except Exception as e:
            logger.error(f"Error getting hybrid search stats: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }

    logger.info("✅ Hybrid search tools registered with NMF/Qdrant backend")
