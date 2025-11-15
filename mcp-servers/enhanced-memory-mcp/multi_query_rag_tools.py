"""
Multi-Query RAG Implementation - RAG Tier 2.2

Generates multiple query perspectives (technical, user, conceptual) for comprehensive
search coverage. Uses Reciprocal Rank Fusion (RRF) to combine results from different
perspectives.

Expected improvement: +20-30% coverage over single query search
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class Perspective:
    """Query perspective representation"""
    perspective_type: str  # "technical", "user", "conceptual"
    query: str  # The reformulated query for this perspective
    description: str  # Human-readable description
    weight: float = 1.0  # Weight for this perspective (future use)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SearchResult:
    """Individual search result from a perspective"""
    id: str  # Document ID
    content: str  # Document content
    score: float  # Original search score
    metadata: Dict[str, Any]  # Additional metadata
    perspective: str  # Which perspective found this

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FusedResult:
    """Fused search result with RRF score"""
    id: str  # Document ID
    content: str  # Document content
    rrf_score: float  # Reciprocal Rank Fusion score
    perspective_scores: Dict[str, float]  # {perspective: score}
    contributing_perspectives: List[str]  # Which perspectives found this
    diversity_score: float  # How many perspectives found this
    metadata: Dict[str, Any]  # Original metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# ============================================================================
# Perspective Generator
# ============================================================================


class PerspectiveGenerator:
    """Generate multiple query perspectives for comprehensive coverage"""

    def __init__(self, nmf=None):
        """
        Initialize perspective generator

        Args:
            nmf: Neural Memory Fabric instance (for future LLM-based generation)
        """
        self.nmf = nmf

        # Template-based perspective generation
        self.perspective_templates = {
            "technical": [
                "implementation details of {query}",
                "technical architecture for {query}",
                "how {query} works internally",
                "system design of {query}",
                "technical specifications for {query}"
            ],
            "user": [
                "how to use {query}",
                "user guide for {query}",
                "practical application of {query}",
                "getting started with {query}",
                "best practices for {query}"
            ],
            "conceptual": [
                "concepts behind {query}",
                "theoretical foundation of {query}",
                "principles of {query}",
                "understanding {query}",
                "overview of {query}"
            ]
        }

    async def generate_perspectives(
        self,
        query: str,
        perspective_types: Optional[List[str]] = None,
        max_perspectives: int = 3
    ) -> List[Perspective]:
        """
        Generate query perspectives using templates

        Args:
            query: Original search query
            perspective_types: List of perspective types to generate
                              (default: ["technical", "user", "conceptual"])
            max_perspectives: Maximum number of perspectives to generate

        Returns:
            List of Perspective objects
        """
        if perspective_types is None:
            perspective_types = ["technical", "user", "conceptual"]

        perspectives = []

        for ptype in perspective_types[:max_perspectives]:
            if ptype in self.perspective_templates:
                templates = self.perspective_templates[ptype]

                # Use first template (pattern-based for now)
                query_text = templates[0].format(query=query)

                perspective = Perspective(
                    perspective_type=ptype,
                    query=query_text,
                    description=f"{ptype.title()} perspective on {query}",
                    weight=1.0
                )
                perspectives.append(perspective)

        return perspectives

    async def llm_generate_perspectives(
        self,
        query: str,
        num_perspectives: int = 3
    ) -> List[Perspective]:
        """
        Generate perspectives using LLM (future enhancement)

        Args:
            query: Original search query
            num_perspectives: Number of perspectives to generate

        Returns:
            List of Perspective objects
        """
        if not self.nmf:
            # Fall back to template-based
            return await self.generate_perspectives(query)

        # Future: Use LLM to generate diverse perspectives
        # This would prompt the LLM with something like:
        # "Generate {num_perspectives} different perspectives for: {query}"
        # and parse the response into Perspective objects

        # For now, fall back to template-based
        return await self.generate_perspectives(query)

    def calculate_diversity(
        self,
        perspectives: List[Perspective]
    ) -> float:
        """
        Calculate diversity score for perspectives

        Args:
            perspectives: List of perspectives

        Returns:
            Diversity score (0.0 to 1.0)
        """
        if len(perspectives) <= 1:
            return 0.0

        # Simple diversity: count of unique perspective types
        unique_types = len(set(p.perspective_type for p in perspectives))
        max_types = 3  # technical, user, conceptual

        return unique_types / max_types


# ============================================================================
# Multi-Query Executor
# ============================================================================


class MultiQueryExecutor:
    """Execute parallel searches for multiple perspectives"""

    def __init__(self, nmf):
        """
        Initialize multi-query executor

        Args:
            nmf: Neural Memory Fabric instance
        """
        self.nmf = nmf

    async def execute_parallel_searches(
        self,
        perspectives: List[Perspective],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> Dict[str, List[SearchResult]]:
        """
        Execute hybrid searches in parallel for all perspectives

        Args:
            perspectives: List of perspectives to search
            limit: Number of results per perspective
            score_threshold: Minimum score threshold

        Returns:
            Dictionary mapping perspective type to search results
        """

        async def search_perspective(perspective: Perspective) -> tuple:
            """
            Search for a single perspective

            Args:
                perspective: Perspective to search

            Returns:
                Tuple of (perspective_type, search_results)
            """
            try:
                # Use existing hybrid search
                from hybrid_search_tools import search_hybrid

                results = await search_hybrid(
                    self.nmf,
                    query=perspective.query,
                    limit=limit,
                    score_threshold=score_threshold
                )

                # Convert to SearchResult objects
                search_results = []
                if results.get("success"):
                    for r in results.get("results", []):
                        search_results.append(SearchResult(
                            id=str(r.get("id", "")),
                            content=r.get("content", ""),
                            score=r.get("score", 0.0),
                            metadata=r.get("metadata", {}),
                            perspective=perspective.perspective_type
                        ))

                return (perspective.perspective_type, search_results)

            except Exception as e:
                logger.error(
                    f"Search failed for perspective {perspective.perspective_type}: {e}"
                )
                return (perspective.perspective_type, [])

        # Execute all searches in parallel
        tasks = [search_perspective(p) for p in perspectives]
        results_by_perspective = await asyncio.gather(*tasks)

        # Convert to dictionary
        return dict(results_by_perspective)


# ============================================================================
# Result Fusion Engine
# ============================================================================


class ResultFusionEngine:
    """Fuse results from multiple perspectives using RRF"""

    def __init__(self, k: int = 60):
        """
        Initialize result fusion engine

        Args:
            k: RRF constant (typical: 60)
        """
        self.k = k

    def calculate_rrf_score(
        self,
        results_by_perspective: Dict[str, List[SearchResult]]
    ) -> Dict[str, FusedResult]:
        """
        Calculate RRF scores for all results

        RRF formula: RRF(d) = sum over all perspectives of 1/(k + rank(d))
        where rank(d) is the rank of document d in that perspective

        Args:
            results_by_perspective: Dictionary of search results by perspective

        Returns:
            Dictionary mapping document ID to FusedResult
        """
        # Build ranking map: {doc_id: {perspective: rank}}
        doc_rankings = {}

        for perspective, results in results_by_perspective.items():
            for rank, result in enumerate(results, start=1):
                doc_id = result.id
                if doc_id not in doc_rankings:
                    doc_rankings[doc_id] = {}
                doc_rankings[doc_id][perspective] = rank

        # Calculate RRF scores
        fused_results = {}

        for doc_id, rankings in doc_rankings.items():
            # RRF formula: sum(1 / (k + rank)) for all perspectives
            rrf_score = sum(
                1.0 / (self.k + rank)
                for rank in rankings.values()
            )

            # Get original result data (from first perspective that found it)
            first_perspective = next(iter(rankings.keys()))
            first_result = next(
                r for r in results_by_perspective[first_perspective]
                if r.id == doc_id
            )

            # Build perspective scores dictionary
            perspective_scores = {}
            for p, rank in rankings.items():
                # Find the actual result to get the score
                result = next(
                    r for r in results_by_perspective[p]
                    if r.id == doc_id
                )
                perspective_scores[p] = result.score

            # Create fused result
            fused_results[doc_id] = FusedResult(
                id=doc_id,
                content=first_result.content,
                rrf_score=rrf_score,
                perspective_scores=perspective_scores,
                contributing_perspectives=list(rankings.keys()),
                diversity_score=len(rankings) / len(results_by_perspective),
                metadata=first_result.metadata
            )

        return fused_results

    def fuse_and_rank(
        self,
        results_by_perspective: Dict[str, List[SearchResult]],
        limit: int = 10
    ) -> List[FusedResult]:
        """
        Fuse results and return top-k ranked by RRF score

        Args:
            results_by_perspective: Dictionary of search results by perspective
            limit: Number of top results to return

        Returns:
            List of top-k FusedResult objects sorted by RRF score
        """
        fused_results = self.calculate_rrf_score(results_by_perspective)

        # Sort by RRF score (descending)
        sorted_results = sorted(
            fused_results.values(),
            key=lambda r: r.rrf_score,
            reverse=True
        )

        return sorted_results[:limit]


# ============================================================================
# MCP Tool Registration
# ============================================================================


def register_multi_query_rag_tools(app, nmf):
    """
    Register Multi-Query RAG tools with FastMCP

    Args:
        app: FastMCP application instance
        nmf: Neural Memory Fabric instance
    """

    @app.tool()
    async def search_with_multi_query(
        query: str,
        perspective_types: Optional[List[str]] = None,
        max_perspectives: int = 3,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Search using multi-query RAG for comprehensive coverage

        Generates multiple query perspectives (technical, user, conceptual) and
        executes parallel searches, then fuses results using Reciprocal Rank Fusion.

        Expected improvement: +20-30% coverage over single query search

        Args:
            query: Original search query
            perspective_types: List of perspectives (technical, user, conceptual)
                             If None, uses all three perspectives
            max_perspectives: Maximum perspectives to generate (default: 3)
            limit: Number of results to return (default: 10)
            score_threshold: Minimum score threshold (optional)

        Returns:
            Dict with success status, perspectives, results, and metadata
        """
        try:
            logger.info(f"Multi-query RAG search for: {query}")

            # Generate perspectives
            generator = PerspectiveGenerator(nmf)
            perspectives = await generator.generate_perspectives(
                query=query,
                perspective_types=perspective_types,
                max_perspectives=max_perspectives
            )

            logger.info(
                f"Generated {len(perspectives)} perspectives: "
                f"{[p.perspective_type for p in perspectives]}"
            )

            # Execute parallel searches (over-retrieve for fusion)
            executor = MultiQueryExecutor(nmf)
            results_by_perspective = await executor.execute_parallel_searches(
                perspectives=perspectives,
                limit=limit * 2,  # Over-retrieve for better fusion
                score_threshold=score_threshold
            )

            # Log search results
            for ptype, results in results_by_perspective.items():
                logger.info(f"{ptype} perspective found {len(results)} results")

            # Fuse results
            fusion_engine = ResultFusionEngine()
            fused_results = fusion_engine.fuse_and_rank(
                results_by_perspective=results_by_perspective,
                limit=limit
            )

            logger.info(f"Fused to {len(fused_results)} unique results")

            # Calculate diversity
            diversity_score = generator.calculate_diversity(perspectives)

            # Format response
            return {
                "success": True,
                "query": query,
                "perspectives": [
                    {
                        "type": p.perspective_type,
                        "query": p.query,
                        "description": p.description
                    }
                    for p in perspectives
                ],
                "count": len(fused_results),
                "results": [
                    {
                        "id": r.id,
                        "content": r.content,
                        "rrf_score": r.rrf_score,
                        "perspective_scores": r.perspective_scores,
                        "contributing_perspectives": r.contributing_perspectives,
                        "diversity_score": r.diversity_score,
                        "metadata": r.metadata
                    }
                    for r in fused_results
                ],
                "metadata": {
                    "strategy": "multi_query_rag",
                    "num_perspectives": len(perspectives),
                    "diversity_score": diversity_score,
                    "total_candidates": sum(
                        len(results)
                        for results in results_by_perspective.values()
                    ),
                    "fusion_method": "rrf",
                    "rrf_constant": fusion_engine.k
                }
            }

        except Exception as e:
            logger.error(f"Multi-query RAG search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    @app.tool()
    async def get_multi_query_stats() -> Dict[str, Any]:
        """
        Get multi-query RAG system statistics

        Returns:
            System statistics and configuration
        """
        generator = PerspectiveGenerator(nmf)

        return {
            "status": "ready",
            "available_perspectives": ["technical", "user", "conceptual"],
            "default_max_perspectives": 3,
            "fusion_method": "rrf",
            "rrf_constant": 60,
            "llm_available": nmf is not None,
            "templates_per_perspective": {
                ptype: len(templates)
                for ptype, templates in generator.perspective_templates.items()
            }
        }

    @app.tool()
    async def analyze_query_perspectives(
        query: str,
        max_perspectives: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze what perspectives would be generated for a query

        This tool shows what perspectives would be generated without actually
        executing the searches. Useful for understanding and debugging
        perspective generation.

        Args:
            query: Query to analyze
            max_perspectives: Maximum perspectives to generate

        Returns:
            Analysis of perspectives without executing searches
        """
        try:
            generator = PerspectiveGenerator(nmf)
            perspectives = await generator.generate_perspectives(
                query=query,
                max_perspectives=max_perspectives
            )

            diversity_score = generator.calculate_diversity(perspectives)

            return {
                "success": True,
                "query": query,
                "perspectives": [
                    {
                        "type": p.perspective_type,
                        "query": p.query,
                        "description": p.description,
                        "weight": p.weight
                    }
                    for p in perspectives
                ],
                "diversity_score": diversity_score,
                "analysis": {
                    "num_perspectives": len(perspectives),
                    "unique_types": len(
                        set(p.perspective_type for p in perspectives)
                    )
                }
            }

        except Exception as e:
            logger.error(f"Perspective analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    logger.info("Multi-Query RAG tools registered successfully")
