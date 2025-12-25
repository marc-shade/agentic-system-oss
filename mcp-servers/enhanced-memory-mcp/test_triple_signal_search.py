#!/usr/bin/env python3
"""
Comprehensive tests for PTM Phase 3: Triple-Signal Hybrid Search.

Tests:
1. TrajectoryVector creation and similarity
2. TrajectoryIndex indexing and search
3. TripleSignalSearcher RRF fusion
4. Integration with trajectory compression
5. MCP tool registration
6. Edge cases and error handling
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import unittest
import numpy as np
from typing import List, Dict, Any


class TestTrajectoryVector(unittest.TestCase):
    """Test TrajectoryVector dataclass and similarity computation."""

    def setUp(self):
        """Import components."""
        from triple_signal_search import TrajectoryVector, TrajectoryIndex
        self.TrajectoryVector = TrajectoryVector
        self.TrajectoryIndex = TrajectoryIndex
        self.index = TrajectoryIndex()

    def test_vector_creation(self):
        """Test creating a TrajectoryVector."""
        centroid = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        vec = self.TrajectoryVector(
            entity_id=1,
            entity_name="test_entity",
            centroid=centroid,
            anchor_count=5,
            point_count=10,
            anchor_hash=12345
        )

        self.assertEqual(vec.entity_id, 1)
        self.assertEqual(vec.entity_name, "test_entity")
        self.assertEqual(len(vec.centroid), 8)
        self.assertEqual(vec.anchor_count, 5)
        self.assertEqual(vec.point_count, 10)
        self.assertEqual(vec.anchor_hash, 12345)

    def test_identical_similarity(self):
        """Test that identical vectors have similarity = 1.0 (capped)."""
        centroid = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        vec1 = self.TrajectoryVector(1, "a", centroid, 5, 10, 12345)
        vec2 = self.TrajectoryVector(2, "b", centroid.copy(), 5, 10, 12345)

        sim = self.index._compute_similarity(vec1, vec2)
        # Identical centroids have cosine=1, normalized to 1.0
        # With anchor hash match (+0.1), capped at 1.0
        self.assertEqual(sim, 1.0)

    def test_orthogonal_similarity(self):
        """Test that orthogonal centroids have similarity = 0.5."""
        # Create orthogonal vectors on 8D space
        centroid1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        centroid2 = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        vec1 = self.TrajectoryVector(1, "a", centroid1, 1, 1, 111)
        vec2 = self.TrajectoryVector(2, "b", centroid2, 1, 1, 222)

        sim = self.index._compute_similarity(vec1, vec2)
        # Cosine of orthogonal vectors is 0, normalized: (0+1)/2 = 0.5
        self.assertAlmostEqual(sim, 0.5, places=2)

    def test_anchor_hash_bonus(self):
        """Test that matching anchor hashes add bonus (when not capped)."""
        # Use opposite centroids to ensure low base similarity
        centroid1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        centroid2 = np.array([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        # Same anchor hash
        vec1 = self.TrajectoryVector(1, "a", centroid1, 5, 10, 12345)
        vec2 = self.TrajectoryVector(2, "b", centroid2, 5, 10, 12345)
        sim_same = self.index._compute_similarity(vec1, vec2)

        # Different anchor hash
        vec3 = self.TrajectoryVector(3, "c", centroid2, 5, 10, 54321)
        sim_diff = self.index._compute_similarity(vec1, vec3)

        # Same hash should have +0.1 bonus
        self.assertAlmostEqual(sim_same - sim_diff, 0.1, places=2)


class TestTrajectoryIndex(unittest.TestCase):
    """Test TrajectoryIndex indexing and search operations."""

    def setUp(self):
        """Create fresh index for each test."""
        from triple_signal_search import TrajectoryIndex, reset_instances
        reset_instances()
        self.index = TrajectoryIndex()

    def test_add_entity(self):
        """Test adding entities to index."""
        self.index.add_entity(1, "test1", "OpenAI released GPT-5 with enhanced capabilities")
        self.index.add_entity(2, "test2", "Microsoft Azure provides cloud computing services")

        stats = self.index.get_stats()
        self.assertEqual(stats["indexed_entities"], 2)

    def test_compute_trajectory_vector(self):
        """Test trajectory vector computation from text."""
        vec = self.index.compute_trajectory_vector(
            "OpenAI GPT-5 API endpoint",
            entity_id=1,
            entity_name="test"
        )

        self.assertEqual(vec.entity_id, 1)
        self.assertEqual(vec.entity_name, "test")
        self.assertEqual(len(vec.centroid), 8)
        self.assertGreater(vec.point_count, 0)

    def test_search_basic(self):
        """Test basic search functionality."""
        # Add entities
        self.index.add_entity(1, "openai", "OpenAI GPT-5 is a large language model")
        self.index.add_entity(2, "microsoft", "Microsoft Azure cloud computing platform")
        self.index.add_entity(3, "nvidia", "NVIDIA GPU computing with CUDA")

        # Search for AI-related query
        results = self.index.search("OpenAI language model", limit=3)

        self.assertGreater(len(results), 0)
        # Results are (entity_id, score, vector) tuples
        self.assertEqual(len(results[0]), 3)

    def test_search_with_threshold(self):
        """Test search with minimum threshold."""
        self.index.add_entity(1, "test1", "Python programming language")
        self.index.add_entity(2, "test2", "JavaScript web development")

        # High threshold should return fewer results
        results_low = self.index.search("Python code", limit=10, threshold=0.0)
        results_high = self.index.search("Python code", limit=10, threshold=0.9)

        self.assertGreaterEqual(len(results_low), len(results_high))

    def test_search_empty_query(self):
        """Test search with empty query."""
        self.index.add_entity(1, "test", "Some content")
        results = self.index.search("", limit=10)
        # Empty query should still work (returns all with base similarity)
        self.assertIsInstance(results, list)

    def test_stats_tracking(self):
        """Test that statistics are properly tracked."""
        stats_before = self.index.get_stats()
        self.assertEqual(stats_before["indexed_entities"], 0)
        self.assertEqual(stats_before["total_queries"], 0)

        self.index.add_entity(1, "test", "Content")
        self.index.search("query", limit=5)

        stats_after = self.index.get_stats()
        self.assertEqual(stats_after["indexed_entities"], 1)
        self.assertEqual(stats_after["total_queries"], 1)


class TestTripleSignalSearcher(unittest.TestCase):
    """Test TripleSignalSearcher RRF fusion."""

    def setUp(self):
        """Create searcher instance."""
        from triple_signal_search import (
            TripleSignalSearcher, TrajectoryIndex, reset_instances
        )
        reset_instances()
        self.index = TrajectoryIndex()
        self.searcher = TripleSignalSearcher(self.index)

    def test_default_weights(self):
        """Test default weight configuration."""
        self.assertEqual(self.searcher.weights["vector"], 0.4)
        self.assertEqual(self.searcher.weights["lexical"], 0.3)
        self.assertEqual(self.searcher.weights["trajectory"], 0.3)

    def test_custom_weights(self):
        """Test custom weight configuration."""
        from triple_signal_search import TripleSignalSearcher, TrajectoryIndex
        index = TrajectoryIndex()
        searcher = TripleSignalSearcher(
            index,
            vector_weight=0.5,
            lexical_weight=0.3,
            trajectory_weight=0.2
        )
        self.assertEqual(searcher.weights["vector"], 0.5)
        self.assertEqual(searcher.weights["trajectory"], 0.2)

    def test_fuse_single_signal(self):
        """Test fusion with only one signal."""
        vector_results = [
            {"id": "1", "score": 0.9, "payload": {"name": "entity1"}},
            {"id": "2", "score": 0.8, "payload": {"name": "entity2"}}
        ]

        fused = self.searcher.fuse_results(
            vector_results=vector_results,
            lexical_results=[],
            trajectory_results=[],
            limit=10
        )

        # Should still produce results
        self.assertEqual(len(fused), 2)
        self.assertIn("id", fused[0])
        self.assertIn("score", fused[0])

    def test_fuse_all_signals(self):
        """Test fusion with all three signals."""
        vector_results = [
            {"id": "1", "score": 0.9, "payload": {"name": "entity1"}},
            {"id": "2", "score": 0.7, "payload": {"name": "entity2"}}
        ]
        lexical_results = [
            {"id": "2", "score": 0.85, "payload": {"name": "entity2"}},
            {"id": "3", "score": 0.6, "payload": {"name": "entity3"}}
        ]
        trajectory_results = [
            (1, 0.8, None),  # (entity_id, score, vector)
            (2, 0.75, None)
        ]

        fused = self.searcher.fuse_results(
            vector_results=vector_results,
            lexical_results=lexical_results,
            trajectory_results=trajectory_results,
            limit=10
        )

        # ID "2" appears in all three signals, should rank high
        self.assertGreater(len(fused), 0)

        # Verify signal attribution
        for result in fused:
            if result["id"] == "2":
                signals = result.get("signals", {})
                self.assertTrue(signals.get("vector", False))
                self.assertTrue(signals.get("lexical", False))
                self.assertTrue(signals.get("trajectory", False))

    def test_rrf_formula(self):
        """Test RRF score calculation formula."""
        # RRF: score = sum(1 / (k + rank) * weight)
        # With k=60, rank=0 (0-indexed), weight=1: score = 1/60 ≈ 0.0167

        vector_results = [{"id": "1", "score": 1.0, "payload": {}}]

        # Set all weight to vector only
        self.searcher.weights = {"vector": 1.0, "lexical": 0.0, "trajectory": 0.0}

        fused = self.searcher.fuse_results(
            vector_results=vector_results,
            lexical_results=[],
            trajectory_results=[],
            limit=1
        )

        expected_score = 1.0 / (60 + 0)  # k=60, rank=0 (0-indexed)
        self.assertAlmostEqual(fused[0]["score"], expected_score, places=4)

    def test_limit_enforcement(self):
        """Test that limit parameter is enforced."""
        vector_results = [
            {"id": str(i), "score": 1.0 - i*0.1, "payload": {}}
            for i in range(20)
        ]

        fused = self.searcher.fuse_results(
            vector_results=vector_results,
            lexical_results=[],
            trajectory_results=[],
            limit=5
        )

        self.assertEqual(len(fused), 5)

    def test_stats_tracking(self):
        """Test searcher statistics."""
        stats_before = self.searcher.get_stats()
        searches_before = stats_before["total_searches"]

        self.searcher.fuse_results([], [], [], limit=10)

        stats_after = self.searcher.get_stats()
        self.assertEqual(stats_after["total_searches"], searches_before + 1)


class TestTrajectoryCompressionIntegration(unittest.TestCase):
    """Test integration with trajectory_compression module."""

    def test_trajectory_available_flag(self):
        """Test TRAJECTORY_AVAILABLE flag."""
        from triple_signal_search import TRAJECTORY_AVAILABLE
        # Should be True if trajectory_compression imports correctly
        self.assertIsInstance(TRAJECTORY_AVAILABLE, bool)

    def test_fallback_encoding(self):
        """Test fallback hash-based encoding when compression unavailable."""
        from triple_signal_search import TrajectoryIndex

        index = TrajectoryIndex()
        vec = index.compute_trajectory_vector("test text", 1, "test")

        # Should produce valid 8D centroid even without full compression
        self.assertEqual(len(vec.centroid), 8)
        for phase in vec.centroid:
            self.assertGreaterEqual(phase, 0)
            self.assertLess(phase, 2 * np.pi)


class TestMCPToolRegistration(unittest.TestCase):
    """Test MCP tool registration."""

    def test_tools_registration(self):
        """Test that tools can be registered."""
        from triple_signal_tools import register_triple_signal_tools

        # Mock FastMCP app
        class MockApp:
            def __init__(self):
                self.tools = {}
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        # Mock NMF
        class MockNMF:
            embedding_manager = None

        app = MockApp()
        nmf = MockNMF()

        register_triple_signal_tools(app, nmf)

        # Check all 4 tools registered
        expected_tools = [
            "search_triple_signal",
            "search_trajectory_only",
            "build_trajectory_index",
            "get_triple_signal_stats"
        ]

        for tool_name in expected_tools:
            self.assertIn(tool_name, app.tools, f"Tool {tool_name} not registered")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Create fresh index."""
        from triple_signal_search import TrajectoryIndex, reset_instances
        reset_instances()
        self.index = TrajectoryIndex()

    def test_empty_index_search(self):
        """Test searching empty index."""
        results = self.index.search("query", limit=10)
        self.assertEqual(len(results), 0)

    def test_unicode_text(self):
        """Test handling of unicode text."""
        self.index.add_entity(1, "unicode", "日本語 テスト with emoji 🎉")
        results = self.index.search("日本語", limit=5)
        self.assertIsInstance(results, list)

    def test_very_long_text(self):
        """Test handling of very long text."""
        long_text = "OpenAI GPT API " * 1000
        self.index.add_entity(1, "long", long_text)

        stats = self.index.get_stats()
        self.assertEqual(stats["indexed_entities"], 1)

    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Path: /usr/local/bin && echo $HOME | grep -E 'pattern'"
        self.index.add_entity(1, "special", text)

        results = self.index.search("path bin", limit=5)
        self.assertIsInstance(results, list)

    def test_numeric_only_text(self):
        """Test handling of numeric-only text."""
        self.index.add_entity(1, "numbers", "12345 67890 0x8007045D 3.14159")
        results = self.index.search("12345", limit=5)
        self.assertIsInstance(results, list)

    def test_duplicate_entity_ids(self):
        """Test adding duplicate entity IDs (overwrites)."""
        self.index.add_entity(1, "first", "First content")
        self.index.add_entity(1, "second", "Second content")  # Same ID overwrites

        # Should have 1 entry (dict key overwrites)
        stats = self.index.get_stats()
        self.assertEqual(stats["indexed_entities"], 1)
        # Verify the latest content is stored
        self.assertEqual(self.index.index[1].entity_name, "second")


class TestSingletonPattern(unittest.TestCase):
    """Test singleton/instance management."""

    def test_get_trajectory_index_singleton(self):
        """Test that get_trajectory_index returns same instance."""
        from triple_signal_search import get_trajectory_index, reset_instances

        reset_instances()
        idx1 = get_trajectory_index()
        idx2 = get_trajectory_index()

        self.assertIs(idx1, idx2)

    def test_get_triple_searcher_singleton(self):
        """Test that get_triple_searcher returns same instance."""
        from triple_signal_search import get_triple_searcher, reset_instances

        reset_instances()
        s1 = get_triple_searcher()
        s2 = get_triple_searcher()

        self.assertIs(s1, s2)

    def test_reset_instances(self):
        """Test that reset_instances clears singletons."""
        from triple_signal_search import (
            get_trajectory_index, get_triple_searcher, reset_instances
        )

        idx1 = get_trajectory_index()
        idx1.add_entity(1, "test", "content")

        reset_instances()

        idx2 = get_trajectory_index()
        stats = idx2.get_stats()
        self.assertEqual(stats["indexed_entities"], 0)


def main():
    """Run all tests."""
    print("=" * 60)
    print("PTM Phase 3: Triple-Signal Search Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTrajectoryVector))
    suite.addTests(loader.loadTestsFromTestCase(TestTrajectoryIndex))
    suite.addTests(loader.loadTestsFromTestCase(TestTripleSignalSearcher))
    suite.addTests(loader.loadTestsFromTestCase(TestTrajectoryCompressionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPToolRegistration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestSingletonPattern))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nResult: {'PASS' if success else 'FAIL'}")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
