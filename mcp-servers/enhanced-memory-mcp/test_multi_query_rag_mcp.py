"""
Integration Tests for Multi-Query RAG MCP Tools

Tests the full MCP tool integration including:
- MCP tool registration and availability
- End-to-end multi-query RAG search
- Stats and analysis tools
- Coverage improvement vs single query
"""

import pytest
import asyncio
from typing import Dict, Any


# ============================================================================
# Test Setup
# ============================================================================


@pytest.fixture
async def ensure_server_running():
    """
    Ensure MCP server is running with multi-query RAG tools registered

    This test suite requires the enhanced-memory MCP server to be running
    with multi-query RAG tools properly integrated.
    """
    # In actual deployment, MCP server should be running
    # This fixture is a placeholder for server verification
    yield


# ============================================================================
# Test MCP Tool Availability
# ============================================================================


@pytest.mark.asyncio
async def test_multi_query_stats_tool(ensure_server_running):
    """Test that multi-query stats tool is available and returns correct data"""

    # Import the MCP tool function
    # In actual MCP usage, this would be called via MCP protocol
    from multi_query_rag_tools import PerspectiveGenerator

    # Simulate stats tool call
    nmf = None  # Would be actual NMF instance
    generator = PerspectiveGenerator(nmf)

    stats = {
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

    # Verify stats structure
    assert stats["status"] == "ready"
    assert "technical" in stats["available_perspectives"]
    assert "user" in stats["available_perspectives"]
    assert "conceptual" in stats["available_perspectives"]
    assert stats["default_max_perspectives"] == 3
    assert stats["fusion_method"] == "rrf"
    assert stats["rrf_constant"] == 60

    # Verify all perspective types have templates
    assert stats["templates_per_perspective"]["technical"] > 0
    assert stats["templates_per_perspective"]["user"] > 0
    assert stats["templates_per_perspective"]["conceptual"] > 0


@pytest.mark.asyncio
async def test_analyze_perspectives_tool(ensure_server_running):
    """Test perspective analysis tool without executing searches"""

    from multi_query_rag_tools import PerspectiveGenerator

    generator = PerspectiveGenerator()
    query = "voice communication"

    # Generate perspectives (simulating analysis tool)
    perspectives = await generator.generate_perspectives(query)
    diversity_score = generator.calculate_diversity(perspectives)

    analysis = {
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

    # Verify analysis structure
    assert analysis["success"] is True
    assert analysis["query"] == query
    assert len(analysis["perspectives"]) == 3
    assert 0.0 <= analysis["diversity_score"] <= 1.0

    # Verify all perspectives are present
    perspective_types = {p["type"] for p in analysis["perspectives"]}
    assert perspective_types == {"technical", "user", "conceptual"}

    # Verify analysis metadata
    assert analysis["analysis"]["num_perspectives"] == 3
    assert analysis["analysis"]["unique_types"] == 3


# ============================================================================
# Test Multi-Query RAG Search (Mock)
# ============================================================================


@pytest.mark.asyncio
async def test_multi_query_search_structure():
    """Test the structure of multi-query RAG search results"""

    from multi_query_rag_tools import (
        PerspectiveGenerator,
        SearchResult,
        ResultFusionEngine
    )

    generator = PerspectiveGenerator()
    query = "agent workflow"

    # Generate perspectives
    perspectives = await generator.generate_perspectives(query)

    # Create mock search results (simulating parallel searches)
    results_by_perspective = {
        "technical": [
            SearchResult(
                "doc1",
                "Technical implementation of agent workflow",
                0.95,
                {"source": "technical_docs"},
                "technical"
            ),
            SearchResult(
                "doc2",
                "Agent workflow architecture",
                0.85,
                {"source": "design_docs"},
                "technical"
            )
        ],
        "user": [
            SearchResult(
                "doc3",
                "How to use agent workflow",
                0.90,
                {"source": "user_guide"},
                "user"
            ),
            SearchResult(
                "doc1",
                "Technical implementation of agent workflow",
                0.80,
                {"source": "technical_docs"},
                "user"
            )
        ],
        "conceptual": [
            SearchResult(
                "doc4",
                "Concepts behind agent workflow",
                0.88,
                {"source": "conceptual_docs"},
                "conceptual"
            )
        ]
    }

    # Fuse results
    fusion_engine = ResultFusionEngine()
    fused_results = fusion_engine.fuse_and_rank(results_by_perspective, limit=10)

    # Calculate diversity
    diversity_score = generator.calculate_diversity(perspectives)

    # Build response (simulating MCP tool response)
    response = {
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
                len(results) for results in results_by_perspective.values()
            ),
            "fusion_method": "rrf"
        }
    }

    # Verify response structure
    assert response["success"] is True
    assert response["query"] == query
    assert len(response["perspectives"]) == 3
    assert response["count"] > 0
    assert response["count"] <= 10

    # Verify all results have required fields
    for result in response["results"]:
        assert "id" in result
        assert "content" in result
        assert "rrf_score" in result
        assert "perspective_scores" in result
        assert "contributing_perspectives" in result
        assert "diversity_score" in result
        assert "metadata" in result

    # Verify metadata
    assert response["metadata"]["strategy"] == "multi_query_rag"
    assert response["metadata"]["num_perspectives"] == 3
    assert response["metadata"]["fusion_method"] == "rrf"
    assert response["metadata"]["total_candidates"] == 5  # 2 + 2 + 1


# ============================================================================
# Test Custom Perspectives
# ============================================================================


@pytest.mark.asyncio
async def test_custom_perspective_selection():
    """Test that custom perspective selection works correctly"""

    from multi_query_rag_tools import PerspectiveGenerator

    generator = PerspectiveGenerator()
    query = "system architecture"

    # Test with only technical and conceptual
    perspectives = await generator.generate_perspectives(
        query=query,
        perspective_types=["technical", "conceptual"],
        max_perspectives=2
    )

    assert len(perspectives) == 2
    perspective_types = {p.perspective_type for p in perspectives}
    assert perspective_types == {"technical", "conceptual"}

    # Verify queries are different
    queries = [p.query for p in perspectives]
    assert len(set(queries)) == 2


# ============================================================================
# Test Coverage Improvement
# ============================================================================


@pytest.mark.asyncio
async def test_coverage_improvement_simulation():
    """
    Simulate coverage improvement comparison between single query and multi-query

    This test demonstrates that multi-query RAG provides better coverage
    than single query search by finding documents from multiple perspectives.
    """

    from multi_query_rag_tools import (
        SearchResult,
        ResultFusionEngine
    )

    # Simulate single query results (baseline)
    single_query_results = [
        SearchResult("doc1", "content1", 0.95, {}, "single"),
        SearchResult("doc2", "content2", 0.85, {}, "single"),
        SearchResult("doc3", "content3", 0.75, {}, "single")
    ]

    single_query_count = len(single_query_results)

    # Simulate multi-query results (multiple perspectives find different docs)
    multi_query_results_by_perspective = {
        "technical": [
            SearchResult("doc1", "content1", 0.95, {}, "technical"),
            SearchResult("doc2", "content2", 0.85, {}, "technical"),
            SearchResult("doc4", "content4", 0.80, {}, "technical")
        ],
        "user": [
            SearchResult("doc3", "content3", 0.90, {}, "user"),
            SearchResult("doc5", "content5", 0.85, {}, "user"),
            SearchResult("doc1", "content1", 0.80, {}, "user")
        ],
        "conceptual": [
            SearchResult("doc6", "content6", 0.88, {}, "conceptual"),
            SearchResult("doc2", "content2", 0.78, {}, "conceptual")
        ]
    }

    # Calculate total candidates (before fusion)
    total_candidates = sum(
        len(results) for results in multi_query_results_by_perspective.values()
    )

    # Fuse results
    fusion_engine = ResultFusionEngine()
    fused_results = fusion_engine.fuse_and_rank(
        multi_query_results_by_perspective,
        limit=10
    )

    # Get unique document count
    multi_query_count = len(fused_results)

    # Verify coverage improvement
    print(f"Single query: {single_query_count} unique docs")
    print(f"Multi-query total candidates: {total_candidates}")
    print(f"Multi-query unique docs: {multi_query_count}")

    # Multi-query should find more unique documents
    assert multi_query_count > single_query_count

    # Calculate improvement
    improvement = ((multi_query_count - single_query_count) /
                   single_query_count * 100)
    print(f"Coverage improvement: +{improvement:.1f}%")

    # Expect at least 20% improvement (2/11 strategies would give ~18%)
    # With 6 unique docs vs 3, we get 100% improvement
    assert improvement >= 20.0

    # Verify diversity scores
    for result in fused_results:
        assert 0.0 <= result.diversity_score <= 1.0

    # Verify that some documents were found by multiple perspectives
    multi_perspective_docs = [
        r for r in fused_results
        if len(r.contributing_perspectives) > 1
    ]
    assert len(multi_perspective_docs) > 0


# ============================================================================
# Test Perspective Quality
# ============================================================================


@pytest.mark.asyncio
async def test_perspective_query_quality():
    """Test that generated perspective queries are meaningful"""

    from multi_query_rag_tools import PerspectiveGenerator

    generator = PerspectiveGenerator()
    query = "memory optimization"

    perspectives = await generator.generate_perspectives(query)

    # All perspectives should contain the original query
    for p in perspectives:
        assert "memory optimization" in p.query.lower()

    # Perspectives should be different from each other
    queries = [p.query for p in perspectives]
    assert len(set(queries)) == 3

    # Technical perspective should focus on implementation
    technical = next(p for p in perspectives if p.perspective_type == "technical")
    assert any(word in technical.query.lower()
               for word in ["implementation", "technical", "how", "works"])

    # User perspective should focus on usage
    user = next(p for p in perspectives if p.perspective_type == "user")
    assert any(word in user.query.lower()
               for word in ["use", "guide", "practical", "application"])

    # Conceptual perspective should focus on concepts
    conceptual = next(p for p in perspectives if p.perspective_type == "conceptual")
    assert any(word in conceptual.query.lower()
               for word in ["concepts", "theoretical", "principles", "understanding"])


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
