"""
Unit Tests for Multi-Query RAG Implementation

Tests perspective generation, parallel search execution, RRF fusion,
and all core components without requiring full MCP integration.
"""

import pytest
import asyncio
from typing import List, Dict

from multi_query_rag_tools import (
    Perspective,
    SearchResult,
    FusedResult,
    PerspectiveGenerator,
    MultiQueryExecutor,
    ResultFusionEngine
)


# ============================================================================
# Test Perspective Generation
# ============================================================================


@pytest.mark.asyncio
async def test_perspective_generation():
    """Test basic perspective generation"""
    generator = PerspectiveGenerator()
    perspectives = await generator.generate_perspectives("system architecture")

    assert len(perspectives) == 3
    assert {p.perspective_type for p in perspectives} == {
        "technical", "user", "conceptual"
    }
    assert all(p.query for p in perspectives)
    assert all(p.description for p in perspectives)
    assert all("system architecture" in p.query for p in perspectives)


@pytest.mark.asyncio
async def test_perspective_types_selection():
    """Test custom perspective type selection"""
    generator = PerspectiveGenerator()

    # Test with only technical and user
    perspectives = await generator.generate_perspectives(
        "system architecture",
        perspective_types=["technical", "user"],
        max_perspectives=2
    )

    assert len(perspectives) == 2
    assert {p.perspective_type for p in perspectives} == {"technical", "user"}

    # Test with only conceptual
    perspectives = await generator.generate_perspectives(
        "memory optimization",
        perspective_types=["conceptual"],
        max_perspectives=1
    )

    assert len(perspectives) == 1
    assert perspectives[0].perspective_type == "conceptual"


def test_diversity_calculation():
    """Test diversity score calculation"""
    generator = PerspectiveGenerator()

    # Test with 3 unique types (maximum diversity)
    perspectives_3 = [
        Perspective("technical", "query1", "desc1"),
        Perspective("user", "query2", "desc2"),
        Perspective("conceptual", "query3", "desc3")
    ]
    assert generator.calculate_diversity(perspectives_3) == 1.0

    # Test with 2 unique types
    perspectives_2 = [
        Perspective("technical", "query1", "desc1"),
        Perspective("user", "query2", "desc2")
    ]
    assert abs(generator.calculate_diversity(perspectives_2) - 0.667) < 0.01

    # Test with 1 type (no diversity)
    perspectives_1 = [Perspective("technical", "query1", "desc1")]
    assert generator.calculate_diversity(perspectives_1) == 0.0

    # Test with empty list
    assert generator.calculate_diversity([]) == 0.0


@pytest.mark.asyncio
async def test_perspective_templates():
    """Test that perspective templates are properly formatted"""
    generator = PerspectiveGenerator()
    query = "voice communication"

    perspectives = await generator.generate_perspectives(query)

    # Check that queries are formatted correctly
    assert "voice communication" in perspectives[0].query.lower()
    assert "voice communication" in perspectives[1].query.lower()
    assert "voice communication" in perspectives[2].query.lower()

    # Check that each perspective has a different template
    queries = [p.query for p in perspectives]
    assert len(set(queries)) == 3  # All queries should be unique


# ============================================================================
# Test RRF Score Calculation
# ============================================================================


def test_rrf_score_calculation():
    """Test RRF score calculation with known rankings"""
    fusion_engine = ResultFusionEngine(k=60)

    # Create known rankings:
    # doc1 appears in 2 perspectives (rank 1 in technical, rank 2 in user)
    # doc2 appears in 1 perspective (rank 2 in technical)
    # doc3 appears in 1 perspective (rank 1 in user)

    results_by_perspective = {
        "technical": [
            SearchResult("doc1", "content1", 0.9, {}, "technical"),
            SearchResult("doc2", "content2", 0.8, {}, "technical")
        ],
        "user": [
            SearchResult("doc3", "content3", 0.85, {}, "user"),
            SearchResult("doc1", "content1", 0.75, {}, "user")
        ]
    }

    fused = fusion_engine.calculate_rrf_score(results_by_perspective)

    # Verify doc1 appears in results
    assert "doc1" in fused

    # doc1 RRF score: 1/(60+1) + 1/(60+2) ≈ 0.0164 + 0.0161 = 0.0325
    assert fused["doc1"].rrf_score > 0.03
    assert fused["doc1"].rrf_score < 0.04

    # doc1 should have 2 contributing perspectives
    assert len(fused["doc1"].contributing_perspectives) == 2
    assert set(fused["doc1"].contributing_perspectives) == {"technical", "user"}

    # doc1 diversity score: 2/2 = 1.0
    assert fused["doc1"].diversity_score == 1.0

    # doc2 should have 1 contributing perspective
    assert "doc2" in fused
    assert len(fused["doc2"].contributing_perspectives) == 1
    assert fused["doc2"].contributing_perspectives[0] == "technical"

    # doc2 diversity score: 1/2 = 0.5
    assert fused["doc2"].diversity_score == 0.5


def test_rrf_fusion_and_ranking():
    """Test complete fusion and ranking process"""
    fusion_engine = ResultFusionEngine(k=60)

    # Create results where doc1 ranks high in multiple perspectives
    # doc2 ranks high in one perspective
    # doc3 ranks low in one perspective

    results_by_perspective = {
        "technical": [
            SearchResult("doc1", "content1", 0.95, {}, "technical"),
            SearchResult("doc2", "content2", 0.85, {}, "technical"),
            SearchResult("doc3", "content3", 0.75, {}, "technical")
        ],
        "user": [
            SearchResult("doc1", "content1", 0.90, {}, "user"),
            SearchResult("doc4", "content4", 0.80, {}, "user")
        ]
    }

    fused_results = fusion_engine.fuse_and_rank(
        results_by_perspective,
        limit=10
    )

    # doc1 should rank first (appears in both perspectives at top)
    assert fused_results[0].id == "doc1"
    assert fused_results[0].rrf_score > 0.03

    # Verify results are sorted by RRF score descending
    for i in range(len(fused_results) - 1):
        assert fused_results[i].rrf_score >= fused_results[i + 1].rrf_score


def test_rrf_limit():
    """Test that RRF fusion respects limit parameter"""
    fusion_engine = ResultFusionEngine(k=60)

    # Create many results
    results_by_perspective = {
        "technical": [
            SearchResult(f"doc{i}", f"content{i}", 0.9 - i*0.1, {}, "technical")
            for i in range(10)
        ],
        "user": [
            SearchResult(f"doc{i+5}", f"content{i+5}", 0.85 - i*0.1, {}, "user")
            for i in range(10)
        ]
    }

    # Test with limit 5
    fused_results = fusion_engine.fuse_and_rank(
        results_by_perspective,
        limit=5
    )

    assert len(fused_results) == 5

    # Test with limit 10
    fused_results = fusion_engine.fuse_and_rank(
        results_by_perspective,
        limit=10
    )

    assert len(fused_results) == 10


# ============================================================================
# Test Max Perspectives Limit
# ============================================================================


@pytest.mark.asyncio
async def test_max_perspectives_limit():
    """Test that max_perspectives parameter is respected"""
    generator = PerspectiveGenerator()

    # Test with max 1
    perspectives = await generator.generate_perspectives(
        "query",
        max_perspectives=1
    )
    assert len(perspectives) == 1

    # Test with max 2
    perspectives = await generator.generate_perspectives(
        "query",
        max_perspectives=2
    )
    assert len(perspectives) == 2

    # Test with max 3
    perspectives = await generator.generate_perspectives(
        "query",
        max_perspectives=3
    )
    assert len(perspectives) == 3

    # Test with max 5 (should cap at 3 available types)
    perspectives = await generator.generate_perspectives(
        "query",
        max_perspectives=5
    )
    assert len(perspectives) == 3


# ============================================================================
# Test Empty Query Handling
# ============================================================================


@pytest.mark.asyncio
async def test_empty_query():
    """Test behavior with empty string query"""
    generator = PerspectiveGenerator()

    perspectives = await generator.generate_perspectives("")

    # Should still generate perspectives, just with empty query
    assert len(perspectives) == 3
    assert all(p.perspective_type in ["technical", "user", "conceptual"]
               for p in perspectives)


# ============================================================================
# Test Data Model Conversions
# ============================================================================


def test_data_model_to_dict():
    """Test that data models can be converted to dictionaries"""
    # Test Perspective
    perspective = Perspective(
        perspective_type="technical",
        query="test query",
        description="test description",
        weight=0.8
    )
    p_dict = perspective.to_dict()
    assert p_dict["perspective_type"] == "technical"
    assert p_dict["query"] == "test query"
    assert p_dict["weight"] == 0.8

    # Test SearchResult
    search_result = SearchResult(
        id="doc1",
        content="content",
        score=0.9,
        metadata={"key": "value"},
        perspective="technical"
    )
    sr_dict = search_result.to_dict()
    assert sr_dict["id"] == "doc1"
    assert sr_dict["score"] == 0.9
    assert sr_dict["metadata"]["key"] == "value"

    # Test FusedResult
    fused_result = FusedResult(
        id="doc1",
        content="content",
        rrf_score=0.05,
        perspective_scores={"technical": 0.9, "user": 0.8},
        contributing_perspectives=["technical", "user"],
        diversity_score=1.0,
        metadata={"key": "value"}
    )
    fr_dict = fused_result.to_dict()
    assert fr_dict["id"] == "doc1"
    assert fr_dict["rrf_score"] == 0.05
    assert len(fr_dict["perspective_scores"]) == 2
    assert fr_dict["diversity_score"] == 1.0


# ============================================================================
# Test Error Handling
# ============================================================================


def test_rrf_with_empty_results():
    """Test RRF fusion with empty results"""
    fusion_engine = ResultFusionEngine(k=60)

    # Empty results
    results_by_perspective = {
        "technical": [],
        "user": []
    }

    fused = fusion_engine.calculate_rrf_score(results_by_perspective)

    # Should return empty dictionary
    assert len(fused) == 0


def test_rrf_with_single_perspective():
    """Test RRF fusion with only one perspective"""
    fusion_engine = ResultFusionEngine(k=60)

    results_by_perspective = {
        "technical": [
            SearchResult("doc1", "content1", 0.9, {}, "technical"),
            SearchResult("doc2", "content2", 0.8, {}, "technical")
        ]
    }

    fused = fusion_engine.calculate_rrf_score(results_by_perspective)

    # Should still work with single perspective
    assert len(fused) == 2
    assert "doc1" in fused
    assert "doc2" in fused

    # Diversity scores should be 1.0 (all found by the single perspective)
    assert fused["doc1"].diversity_score == 1.0
    assert fused["doc2"].diversity_score == 1.0


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
