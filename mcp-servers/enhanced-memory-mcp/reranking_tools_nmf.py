#!/usr/bin/env python3
"""
Re-ranking tools registration for enhanced-memory-mcp using NMF/Qdrant.

UPDATED: Now queries Neural Memory Fabric (Qdrant) instead of memory-db (SQLite)
This enables RAG tools to work with the vector database.
"""

import logging
from typing import List, Dict, Any
from reranking import get_reranker

logger = logging.getLogger(__name__)

def register_reranking_tools_nmf(app, nmf):
    """
    Register re-ranking tools with the FastMCP app using NMF backend.

    Args:
        app: FastMCP application instance
        nmf: NeuralMemoryFabric instance for vector search operations
    """

    @app.tool()
    async def search_with_reranking(
        query: str,
        limit: int = 10,
        over_retrieve_factor: int = 4
    ) -> Dict[str, Any]:
        """
        Search with cross-encoder re-ranking for improved precision.

        Implements two-stage retrieval:
        1. Over-retrieve candidates from Qdrant (limit × over_retrieve_factor)
        2. Re-rank with cross-encoder model (ms-marco-MiniLM-L-6-v2)
        3. Return top k results

        Expected improvement: +40-55% precision over vector-only search

        Args:
            query: Search query string
            limit: Number of final results to return (default: 10)
            over_retrieve_factor: Over-retrieval multiplier (default: 4)

        Returns:
            Dict with re-ranked results and metadata
        """
        try:
            # Get re-ranker instance
            reranker = get_reranker()

            # Define search function that calls NMF
            async def search_function(q: str, lim: int) -> List[Dict[str, Any]]:
                """Inner search function using NMF/Qdrant."""
                results = await nmf.recall(
                    query=q,
                    mode="semantic",
                    limit=lim
                )
                return results if results else []

            # Perform re-ranked search
            results = await reranker.search_with_reranking(
                query=query,
                search_function=search_function,
                limit=limit,
                over_retrieve_factor=over_retrieve_factor
            )

            return {
                "success": True,
                "query": query,
                "count": len(results),
                "results": results,
                "metadata": {
                    "strategy": "reranking",
                    "backend": "nmf_qdrant",
                    "model": reranker.model_name,
                    "over_retrieve_factor": over_retrieve_factor,
                    "limit": limit
                }
            }

        except Exception as e:
            logger.error(f"Error in search_with_reranking: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "results": []
            }

    @app.tool()
    def get_reranking_stats() -> Dict[str, Any]:
        """
        Get re-ranking system statistics.

        Returns:
            Dict with model information and cache statistics
        """
        try:
            reranker = get_reranker()

            return {
                "model": reranker.model_name,
                "cache_size": getattr(reranker, '_cache_size', 0),
                "status": "ready",
                "backend": "nmf_qdrant"
            }

        except Exception as e:
            logger.error(f"Error getting reranking stats: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }

    logger.info("✅ Re-ranking tools registered with NMF/Qdrant backend")
