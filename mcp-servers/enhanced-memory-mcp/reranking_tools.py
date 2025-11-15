#!/usr/bin/env python3
"""
Re-ranking tools registration for enhanced-memory-mcp.

Integrates cross-encoder re-ranking into the MCP server.
"""

import logging
from typing import List, Dict, Any
from reranking import get_reranker

logger = logging.getLogger(__name__)

def register_reranking_tools(app, memory_client):
    """
    Register re-ranking tools with the FastMCP app.

    Args:
        app: FastMCP application instance
        memory_client: MemoryClient instance for search operations
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
        1. Over-retrieve candidates (limit × over_retrieve_factor)
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

            # Define search function that calls memory_client
            async def search_function(q: str, lim: int) -> List[Dict[str, Any]]:
                """Inner search function using memory_client."""
                response = await memory_client.search_nodes(q, lim)
                if response.get("success"):
                    return response.get("results", [])
                return []

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
    async def get_reranking_stats() -> Dict[str, Any]:
        """
        Get re-ranking system statistics.

        Returns:
            Dict with model info and cache statistics
        """
        try:
            reranker = get_reranker()
            stats = reranker.get_stats()

            return {
                "success": True,
                **stats
            }

        except Exception as e:
            logger.error(f"Error getting reranking stats: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("✅ Re-ranking tools registered")
