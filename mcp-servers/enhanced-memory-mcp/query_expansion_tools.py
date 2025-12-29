#!/usr/bin/env python3
"""
Query Expansion Tools for RAG Tier 2

Implements query expansion strategies to improve recall and coverage:
1. LLM-based reformulation (different phrasings)
2. Synonym expansion (lexical variations)
3. Conceptual expansion (related terms)

Expected improvement: +15-25% recall

LLM Integration: Uses model_router.py for LLM-based query expansion.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
from collections import OrderedDict

logger = logging.getLogger(__name__)

# LLM integration imports (lazy loaded to avoid circular imports)
_model_router_available = False
_chat_func = None

def _ensure_model_router():
    """Lazy load model router to avoid circular imports."""
    global _model_router_available, _chat_func
    if _chat_func is not None:
        return _model_router_available

    try:
        from model_router import chat, ChatParams, Message
        _chat_func = chat
        _model_router_available = True
        logger.info("LLM integration enabled via model_router")
    except ImportError as e:
        logger.warning(f"model_router not available for LLM expansion: {e}")
        _model_router_available = False

    return _model_router_available


class QueryExpander:
    """
    Expand queries using multiple strategies for comprehensive coverage

    Strategies:
    1. LLM Reformulation: Generate semantically similar queries
    2. Synonym Expansion: Replace keywords with synonyms
    3. Conceptual Expansion: Add related concepts and terms
    """

    def __init__(self, nmf=None):
        """
        Initialize query expander

        Args:
            nmf: Neural Memory Fabric instance for LLM access
        """
        self.nmf = nmf

        # Common synonym mappings for technical terms
        self.synonym_map = {
            "system": ["framework", "platform", "infrastructure"],
            "architecture": ["design", "structure", "layout"],
            "communication": ["messaging", "transmission", "exchange"],
            "voice": ["audio", "speech", "vocal"],
            "workflow": ["process", "pipeline", "sequence"],
            "agent": ["service", "worker", "component"],
            "memory": ["storage", "cache", "repository"],
            "search": ["query", "lookup", "retrieval"],
            "implementation": ["execution", "realization", "deployment"],
            "optimization": ["improvement", "enhancement", "refinement"]
        }

        # Conceptual relationships (term -> related concepts)
        self.concept_map = {
            "voice": ["tts", "stt", "audio processing", "speech recognition"],
            "memory": ["vector database", "embeddings", "retrieval", "storage"],
            "workflow": ["automation", "orchestration", "task management"],
            "agent": ["autonomous", "ai", "llm", "intelligent system"],
            "architecture": ["design patterns", "system design", "infrastructure"],
            "search": ["indexing", "ranking", "relevance", "retrieval"]
        }

    async def expand_query(
        self,
        query: str,
        max_expansions: int = 3,
        strategies: Optional[List[str]] = None
    ) -> List[str]:
        """
        Expand query using multiple strategies

        Args:
            query: Original search query
            max_expansions: Maximum number of expanded queries to return
            strategies: List of strategies to use (default: all)
                       Options: ["llm", "synonym", "concept"]

        Returns:
            List of expanded queries (includes original)
        """
        if strategies is None:
            strategies = ["llm", "synonym", "concept"]

        expansions = [query]  # Always include original query

        try:
            # Strategy 1: LLM reformulation
            if "llm" in strategies and self.nmf:
                llm_variants = await self.llm_expand(query)
                expansions.extend(llm_variants)

            # Strategy 2: Synonym expansion
            if "synonym" in strategies:
                synonym_variants = self.synonym_expand(query)
                expansions.extend(synonym_variants)

            # Strategy 3: Conceptual expansion
            if "concept" in strategies:
                concept_variants = self.concept_expand(query)
                expansions.extend(concept_variants)

            # Deduplicate while preserving order
            seen = set()
            unique_expansions = []
            for exp in expansions:
                exp_lower = exp.lower()
                if exp_lower not in seen:
                    seen.add(exp_lower)
                    unique_expansions.append(exp)

            # Return up to max_expansions
            return unique_expansions[:max_expansions]

        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]  # Fallback to original query

    async def llm_expand(self, query: str, num_variants: int = 2) -> List[str]:
        """
        Generate query variations using LLM via model_router.

        Uses intelligent model routing to select optimal LLM provider.
        Falls back to pattern-based expansion if LLM unavailable.

        Args:
            query: Original query
            num_variants: Number of variants to generate

        Returns:
            List of reformulated queries
        """
        # Try LLM-based expansion first
        if _ensure_model_router() and _chat_func is not None:
            try:
                prompt = f"""Generate exactly {num_variants} alternative phrasings for this search query.
Each variation should have the same semantic meaning but use different words and structure.
Focus on:
- Using synonyms for key terms
- Restructuring the sentence
- Adding or removing context words

Original query: "{query}"

Return ONLY the variations, one per line, without numbers, bullets, or explanations.
Do not repeat the original query."""

                # Use a fast, cost-effective model for query expansion
                response = await _chat_func(
                    model="gpt-4o-mini",  # Fast and cost-effective
                    messages=[
                        {"role": "system", "content": "You are a search query expansion assistant. Generate semantically equivalent query variations."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )

                # Extract text from response content blocks
                variants = []
                for block in response.content:
                    if hasattr(block, 'text') and block.text:
                        # Parse line-separated variants
                        lines = [line.strip() for line in block.text.strip().split('\n')]
                        for line in lines:
                            # Skip empty lines and lines that look like bullets/numbers
                            if line and not line[0].isdigit() and not line.startswith('-') and not line.startswith('•'):
                                variants.append(line)
                            elif line and line[0].isdigit():
                                # Handle numbered lines like "1. query variation"
                                parts = line.split('.', 1)
                                if len(parts) > 1:
                                    variants.append(parts[1].strip())

                if variants:
                    logger.info(f"LLM generated {len(variants)} query variations")
                    return variants[:num_variants]

            except Exception as e:
                logger.warning(f"LLM expansion failed, falling back to pattern-based: {e}")

        # Fallback: Pattern-based reformulation
        logger.debug("Using pattern-based query expansion (LLM unavailable)")
        variants = []

        # Add question forms if query is declarative
        if not query.endswith("?"):
            if "what" not in query.lower():
                variants.append(f"what is {query}")
            if "how" not in query.lower():
                variants.append(f"how does {query} work")

        return variants[:num_variants]

    def synonym_expand(self, query: str, max_variants: int = 1) -> List[str]:
        """
        Expand query by replacing keywords with synonyms

        Args:
            query: Original query
            max_variants: Maximum synonym variants to generate

        Returns:
            List of synonym-expanded queries
        """
        words = query.lower().split()
        variants = []

        for word in words:
            if word in self.synonym_map:
                synonyms = self.synonym_map[word]
                # Create variant by replacing word with first synonym
                if synonyms and len(variants) < max_variants:
                    variant_words = [
                        synonyms[0] if w == word else w
                        for w in words
                    ]
                    variants.append(" ".join(variant_words))

        return variants

    def concept_expand(self, query: str, max_variants: int = 1) -> List[str]:
        """
        Expand query by adding related concepts

        Args:
            query: Original query
            max_variants: Maximum concept variants to generate

        Returns:
            List of concept-expanded queries
        """
        words = query.lower().split()
        variants = []

        for word in words:
            if word in self.concept_map:
                concepts = self.concept_map[word]
                # Add related concepts to query
                if concepts and len(variants) < max_variants:
                    # Add first related concept
                    variant = f"{query} {concepts[0]}"
                    variants.append(variant)

        return variants


def register_query_expansion_tools(app, nmf):
    """
    Register query expansion tools with FastMCP app

    Args:
        app: FastMCP application instance
        nmf: Neural Memory Fabric instance
    """

    # Initialize query expander
    expander = QueryExpander(nmf=nmf)

    @app.tool()
    async def search_with_query_expansion(
        query: str,
        max_expansions: int = 3,
        strategies: List[str] = None,
        limit: int = 10,
        score_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Search using query expansion for broader coverage

        Expands the query into multiple variations using:
        - LLM reformulation (different phrasings)
        - Synonym expansion (lexical variations)
        - Conceptual expansion (related terms)

        Then performs hybrid search on all expanded queries and aggregates results.

        Expected improvement: +15-25% recall

        Args:
            query: Original search query
            max_expansions: Maximum number of query expansions (default: 3)
            strategies: List of expansion strategies to use
                       Options: ["llm", "synonym", "concept"]
                       Default: all strategies
            limit: Total number of results to return
            score_threshold: Minimum score threshold for results

        Returns:
            Dict with aggregated search results from all expanded queries
        """
        try:
            # Expand query
            expanded_queries = await expander.expand_query(
                query=query,
                max_expansions=max_expansions,
                strategies=strategies
            )

            logger.info(f"Expanded '{query}' into {len(expanded_queries)} queries")

            # Import hybrid search function
            from qdrant_client import QdrantClient
            from qdrant_client.models import Fusion, FusionQuery, Prefetch
            from fastembed import SparseTextEmbedding

            client = QdrantClient(url="http://localhost:6333")
            sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

            # Perform hybrid search for each expanded query
            all_results = []

            for exp_query in expanded_queries:
                # Generate dense vector
                embedding_result = await nmf.embedding_manager.generate_embedding(exp_query)
                query_vector = (
                    embedding_result.embedding
                    if hasattr(embedding_result, 'embedding')
                    else embedding_result
                )

                # Generate sparse vector
                sparse_embeddings = list(sparse_model.embed([exp_query]))
                sparse_embedding = sparse_embeddings[0]
                query_sparse = {
                    "indices": sparse_embedding.indices.tolist(),
                    "values": sparse_embedding.values.tolist()
                }

                # Hybrid search
                results = client.query_points(
                    collection_name="enhanced_memory",
                    prefetch=[
                        Prefetch(query=query_vector, using="text-dense", limit=limit * 2),
                        Prefetch(query=query_sparse, using="text-sparse", limit=limit * 2)
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),
                    limit=limit,
                    with_payload=True,
                    score_threshold=score_threshold
                ).points

                # Add results with query info
                for hit in results:
                    all_results.append({
                        "id": str(hit.id),
                        "score": hit.score,
                        "payload": hit.payload,
                        "query": exp_query  # Track which query found this result
                    })

            # Deduplicate results (same ID from different queries)
            seen_ids = {}
            for result in all_results:
                result_id = result["id"]
                if result_id not in seen_ids:
                    seen_ids[result_id] = result
                else:
                    # Keep higher score
                    if result["score"] > seen_ids[result_id]["score"]:
                        seen_ids[result_id] = result

            # Sort by score and limit
            final_results = sorted(
                seen_ids.values(),
                key=lambda x: x["score"],
                reverse=True
            )[:limit]

            return {
                "success": True,
                "query": query,
                "expanded_queries": expanded_queries,
                "count": len(final_results),
                "results": final_results,
                "metadata": {
                    "strategy": "query_expansion",
                    "num_expansions": len(expanded_queries),
                    "total_candidates": len(all_results),
                    "deduplication": "highest_score"
                }
            }

        except Exception as e:
            logger.error(f"Error in search_with_query_expansion: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "count": 0,
                "results": []
            }

    @app.tool()
    async def get_query_expansion_stats() -> Dict[str, Any]:
        """
        Get query expansion system statistics

        Returns:
            Dict with expansion configuration and available strategies
        """
        return {
            "status": "ready",
            "strategies": ["llm", "synonym", "concept"],
            "synonym_mappings": len(expander.synonym_map),
            "concept_mappings": len(expander.concept_map),
            "llm_available": expander.nmf is not None,
            "default_max_expansions": 3
        }

    logger.info("✅ Query expansion tools registered")
