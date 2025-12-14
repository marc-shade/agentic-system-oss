#!/usr/bin/env python3
"""
Re-ranking module for enhanced-memory-mcp using cross-encoder models.

Implements two-stage retrieval:
1. Over-retrieve candidates (4x)
2. Re-rank with cross-encoder
3. Return top k results

Based on RAG Strategy Recommendations (Week 1, Day 1-2)
Expected improvement: +40-55% precision
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
import asyncio

logger = logging.getLogger(__name__)

class ReRanker:
    """
    Cross-encoder re-ranking for improved retrieval precision.

    Uses ms-marco-MiniLM-L-6-v2 model for semantic re-ranking.
    Implements cache-aware two-stage retrieval pattern.
    """

    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize re-ranker with cross-encoder model.

        Args:
            model_name: HuggingFace cross-encoder model name
        """
        self.model_name = model_name
        self.model = None
        self._model_loaded = False
        self.cache = {}  # Simple in-memory cache for dev/testing

        logger.info(f"ReRanker initialized with model: {model_name}")

    def _ensure_model_loaded(self):
        """Lazy load model to reduce startup time."""
        if not self._model_loaded:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            self._model_loaded = True
            logger.info("Cross-encoder model loaded successfully")

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        limit: int = 10,
        content_field: str = 'content'
    ) -> List[Dict[str, Any]]:
        """
        Re-rank candidates using cross-encoder model.

        Args:
            query: Search query
            candidates: List of candidate documents
            limit: Number of results to return
            content_field: Field name containing document content

        Returns:
            List of re-ranked documents with scores
        """
        if not candidates:
            return []

        # Ensure model is loaded
        self._ensure_model_loaded()

        try:
            # Extract content from candidates
            # Support both dict and object-style access
            contents = []
            for doc in candidates:
                if isinstance(doc, dict):
                    content = doc.get(content_field, doc.get('observations', [''])[0] if 'observations' in doc else '')
                else:
                    content = getattr(doc, content_field, '')
                contents.append(str(content))

            # Create query-document pairs
            pairs = [(query, content) for content in contents]

            # Get re-ranking scores
            scores = self.model.predict(pairs)

            # Combine candidates with scores
            scored_candidates = []
            for idx, (doc, score) in enumerate(zip(candidates, scores)):
                if isinstance(doc, dict):
                    scored_doc = {**doc}
                else:
                    scored_doc = {'content': str(doc)}
                scored_doc['rerank_score'] = float(score)
                scored_doc['original_rank'] = idx
                scored_candidates.append(scored_doc)

            # Sort by re-ranking score (descending)
            scored_candidates.sort(key=lambda x: x['rerank_score'], reverse=True)

            # Return top k
            results = scored_candidates[:limit]

            logger.debug(f"Re-ranked {len(candidates)} candidates, returning top {limit}")

            return results

        except Exception as e:
            logger.error(f"Error during re-ranking: {str(e)}")
            # Fallback: return original candidates if re-ranking fails
            return candidates[:limit]

    async def search_with_reranking(
        self,
        query: str,
        search_function,
        limit: int = 10,
        over_retrieve_factor: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Two-stage retrieval with over-retrieval and re-ranking.

        Args:
            query: Search query
            search_function: Async function that performs initial search
            limit: Final number of results to return
            over_retrieve_factor: How many times limit to initially retrieve

        Returns:
            Re-ranked results
        """
        # Stage 1: Over-retrieve candidates
        candidates_limit = limit * over_retrieve_factor
        logger.debug(f"Stage 1: Over-retrieving {candidates_limit} candidates for query: {query[:50]}...")

        try:
            candidates = await search_function(query, candidates_limit)
        except Exception as e:
            logger.error(f"Error in initial search: {str(e)}")
            candidates = []

        if not candidates:
            logger.warning("No candidates retrieved in Stage 1")
            return []

        # Stage 2: Re-rank
        logger.debug(f"Stage 2: Re-ranking {len(candidates)} candidates")
        reranked = await self.rerank(query, candidates, limit)

        # Add metadata
        for result in reranked:
            result['metadata'] = {
                'reranked': True,
                'over_retrieve_factor': over_retrieve_factor,
                'model': self.model_name,
                'original_candidates': len(candidates)
            }

        return reranked

    def clear_cache(self):
        """Clear re-ranking cache."""
        self.cache = {}
        logger.info("Re-ranking cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get re-ranker statistics."""
        return {
            'model_name': self.model_name,
            'model_loaded': self._model_loaded,
            'cache_size': len(self.cache)
        }


# Global re-ranker instance
_reranker = None

def get_reranker() -> ReRanker:
    """Get or create global re-ranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = ReRanker()
    return _reranker
