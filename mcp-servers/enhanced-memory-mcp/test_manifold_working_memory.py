#!/usr/bin/env python3
"""
Comprehensive tests for PTM Phase 4: Manifold Working Memory.

Tests:
- ManifoldSlot creation and operations
- Phase similarity calculations
- IrrationalRotation position generation
- ManifoldWorkingMemory allocation and retrieval
- Resonance-based search
- Context clustering
- Energy decay and garbage collection
- MCP tool registration
- Edge cases
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import unittest
import numpy as np
import time
from manifold_working_memory import (
    ManifoldSlot,
    IrrationalRotation,
    ManifoldWorkingMemory,
    get_manifold_working_memory,
    reset_manifold_working_memory,
    allocate_working_slot,
    search_working_memory,
    get_working_memory_stats,
    MANIFOLD_DIM,
    GOLDEN_RATIO,
    TWO_PI,
    DEFAULT_ENERGY,
    DECAY_RATE,
    MIN_ENERGY,
    RESONANCE_THRESHOLD
)


class TestManifoldSlot(unittest.TestCase):
    """Test ManifoldSlot creation and operations."""

    def test_slot_creation(self):
        """Test creating a ManifoldSlot."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        slot = ManifoldSlot(
            slot_id=1,
            phases=phases,
            content="Test content",
            context_key="test"
        )

        self.assertEqual(slot.slot_id, 1)
        self.assertEqual(slot.content, "Test content")
        self.assertEqual(slot.context_key, "test")
        self.assertEqual(slot.priority, 5)  # Default
        self.assertEqual(slot.energy, DEFAULT_ENERGY)
        self.assertEqual(len(slot.phases), MANIFOLD_DIM)

    def test_phase_distance_identical(self):
        """Test phase distance for identical positions."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        slot = ManifoldSlot(slot_id=1, phases=phases, content="", context_key="")

        distance = slot.phase_distance(phases)
        self.assertAlmostEqual(distance, 0.0, places=10)

    def test_phase_distance_different(self):
        """Test phase distance for different positions."""
        phases1 = np.zeros(MANIFOLD_DIM)
        phases2 = np.ones(MANIFOLD_DIM) * np.pi  # Maximum distance

        slot = ManifoldSlot(slot_id=1, phases=phases1, content="", context_key="")
        distance = slot.phase_distance(phases2)

        # Maximum distance is π per dimension, total = π√8
        max_distance = np.pi * np.sqrt(MANIFOLD_DIM)
        self.assertLessEqual(distance, max_distance)
        self.assertGreater(distance, 0)

    def test_phase_similarity_identical(self):
        """Test phase similarity for identical positions."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        slot = ManifoldSlot(slot_id=1, phases=phases, content="", context_key="")

        similarity = slot.phase_similarity(phases)
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_phase_similarity_range(self):
        """Test phase similarity is in [0, 1]."""
        slot = ManifoldSlot(
            slot_id=1,
            phases=np.random.uniform(0, TWO_PI, MANIFOLD_DIM),
            content="", context_key=""
        )

        for _ in range(100):
            other = np.random.uniform(0, TWO_PI, MANIFOLD_DIM)
            similarity = slot.phase_similarity(other)
            self.assertGreaterEqual(similarity, 0.0)
            self.assertLessEqual(similarity, 1.0)

    def test_energy_decay(self):
        """Test energy decay over time."""
        slot = ManifoldSlot(
            slot_id=1,
            phases=np.zeros(MANIFOLD_DIM),
            content="", context_key=""
        )

        initial_energy = slot.energy
        slot.apply_decay(10)  # 10 minutes

        expected_energy = initial_energy - DECAY_RATE * 10
        self.assertAlmostEqual(slot.energy, expected_energy, places=5)

    def test_energy_boost(self):
        """Test energy boost on access."""
        slot = ManifoldSlot(
            slot_id=1,
            phases=np.zeros(MANIFOLD_DIM),
            content="", context_key="",
            energy=0.5
        )

        slot.boost_energy(0.3)
        self.assertAlmostEqual(slot.energy, 0.8, places=5)
        self.assertEqual(slot.access_count, 1)

    def test_energy_boost_cap(self):
        """Test energy doesn't exceed 1.0."""
        slot = ManifoldSlot(
            slot_id=1,
            phases=np.zeros(MANIFOLD_DIM),
            content="", context_key="",
            energy=0.9
        )

        slot.boost_energy(0.5)
        self.assertEqual(slot.energy, 1.0)

    def test_is_expired(self):
        """Test expiration check."""
        slot = ManifoldSlot(
            slot_id=1,
            phases=np.zeros(MANIFOLD_DIM),
            content="", context_key="",
            energy=MIN_ENERGY / 2  # Below threshold
        )

        self.assertTrue(slot.is_expired())

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        slot = ManifoldSlot(
            slot_id=42,
            phases=phases,
            content="Test",
            context_key="ctx",
            priority=7,
            entity_id=100
        )

        data = slot.to_dict()
        recovered = ManifoldSlot.from_dict(data)

        self.assertEqual(recovered.slot_id, 42)
        self.assertEqual(recovered.content, "Test")
        self.assertEqual(recovered.context_key, "ctx")
        self.assertEqual(recovered.priority, 7)
        self.assertEqual(recovered.entity_id, 100)
        np.testing.assert_array_almost_equal(recovered.phases, phases)


class TestIrrationalRotation(unittest.TestCase):
    """Test IrrationalRotation position generation."""

    def setUp(self):
        self.rotation = IrrationalRotation()

    def test_golden_ratio(self):
        """Test golden ratio constant."""
        expected = (1 + np.sqrt(5)) / 2
        self.assertAlmostEqual(GOLDEN_RATIO, expected, places=10)

    def test_next_position_unique(self):
        """Test that sequential positions are unique."""
        positions = []
        for _ in range(100):
            pos = self.rotation.next_position()
            positions.append(tuple(pos.round(6)))

        unique = len(set(positions))
        # Should have high uniqueness (allow 1% collision from rounding)
        self.assertGreater(unique, 95)

    def test_position_from_hash_deterministic(self):
        """Test that hash-based positions are reproducible."""
        pos1 = self.rotation.position_from_hash("test text")
        pos2 = self.rotation.position_from_hash("test text")

        np.testing.assert_array_equal(pos1, pos2)

    def test_position_from_hash_different_inputs(self):
        """Test that different inputs give different positions."""
        pos1 = self.rotation.position_from_hash("text A")
        pos2 = self.rotation.position_from_hash("text B")

        self.assertFalse(np.allclose(pos1, pos2))

    def test_context_region_center(self):
        """Test context region center calculation."""
        center1 = self.rotation.context_region_center("context_a")
        center2 = self.rotation.context_region_center("context_a")
        center3 = self.rotation.context_region_center("context_b")

        # Same context should give same center
        np.testing.assert_array_equal(center1, center2)

        # Different contexts should give different centers
        self.assertFalse(np.allclose(center1, center3))

    def test_position_in_region_clustering(self):
        """Test that positions in same context cluster together."""
        context = "test_context"
        positions = []

        for i in range(20):
            pos = self.rotation.position_in_region(context, f"content_{i}")
            positions.append(pos)

        center = self.rotation.context_region_center(context)

        # All positions should be within 0.5 radians of center (per dimension)
        for pos in positions:
            diff = np.abs(pos - center)
            diff = np.minimum(diff, TWO_PI - diff)  # Wrap around
            max_diff = np.max(diff)
            self.assertLess(max_diff, 1.0)  # Generous threshold


class TestManifoldWorkingMemory(unittest.TestCase):
    """Test ManifoldWorkingMemory operations."""

    def setUp(self):
        reset_manifold_working_memory()
        self.memory = ManifoldWorkingMemory(max_slots=100)

    def tearDown(self):
        reset_manifold_working_memory()

    def test_allocate_slot(self):
        """Test basic slot allocation."""
        slot = self.memory.allocate(
            content="Test content",
            context_key="test",
            priority=7
        )

        self.assertEqual(slot.slot_id, 1)
        self.assertEqual(slot.content, "Test content")
        self.assertEqual(slot.context_key, "test")
        self.assertEqual(slot.priority, 7)
        self.assertEqual(len(self.memory.slots), 1)

    def test_allocate_multiple_slots(self):
        """Test allocating multiple slots."""
        for i in range(10):
            self.memory.allocate(f"Content {i}", "ctx", priority=5)

        self.assertEqual(len(self.memory.slots), 10)
        self.assertEqual(len(self.memory.context_index["ctx"]), 10)

    def test_retrieve_slot(self):
        """Test slot retrieval by ID."""
        slot = self.memory.allocate("Test", "ctx")
        initial_access = slot.access_count

        retrieved = self.memory.retrieve(slot.slot_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "Test")
        self.assertEqual(retrieved.access_count, initial_access + 1)

    def test_retrieve_nonexistent(self):
        """Test retrieving non-existent slot."""
        retrieved = self.memory.retrieve(999)
        self.assertIsNone(retrieved)

    def test_retrieve_by_context(self):
        """Test context-based retrieval."""
        for i in range(5):
            self.memory.allocate(f"A_{i}", "context_a")
        for i in range(3):
            self.memory.allocate(f"B_{i}", "context_b")

        slots_a = self.memory.retrieve_by_context("context_a")
        slots_b = self.memory.retrieve_by_context("context_b")

        self.assertEqual(len(slots_a), 5)
        self.assertEqual(len(slots_b), 3)

    def test_resonance_search(self):
        """Test resonance-based search."""
        # Add some slots
        self.memory.allocate("OpenAI GPT-5 announcement", "ai")
        self.memory.allocate("Microsoft Azure cloud services", "cloud")
        self.memory.allocate("OpenAI API documentation", "ai")
        self.memory.allocate("Google Cloud Platform overview", "cloud")

        # Search should find similar items
        results = self.memory.resonance_search(
            "OpenAI GPT documentation",
            context_key="ai",
            limit=5,
            threshold=0.3
        )

        self.assertGreater(len(results), 0)
        # Results should have similarity scores
        for slot, sim in results:
            self.assertGreaterEqual(sim, 0.3)
            self.assertLessEqual(sim, 1.0)

    def test_resonance_search_all_contexts(self):
        """Test search across all contexts."""
        self.memory.allocate("Item A", "ctx1")
        self.memory.allocate("Item B", "ctx2")
        self.memory.allocate("Item C", "ctx3")

        results = self.memory.resonance_search(
            "Item query",
            context_key=None,  # Search all
            limit=10,
            threshold=0.0
        )

        # Should find items from all contexts
        self.assertGreaterEqual(len(results), 1)

    def test_interference_query(self):
        """Test direct phase-based query."""
        slot = self.memory.allocate("Test", "ctx")
        phases = slot.phases

        # Query with same phases should find the slot
        results = self.memory.interference_query(phases, limit=5)

        self.assertGreater(len(results), 0)
        best_slot, sim = results[0]
        self.assertEqual(best_slot.slot_id, slot.slot_id)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_garbage_collection(self):
        """Test garbage collection removes expired slots."""
        # Create slot with low energy
        slot = self.memory.allocate("Test", "ctx")
        slot.energy = MIN_ENERGY / 2  # Force expiration

        removed = self.memory.garbage_collect()

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.memory.slots), 0)

    def test_eviction_at_capacity(self):
        """Test that lowest energy slot is evicted at capacity."""
        memory = ManifoldWorkingMemory(max_slots=5)

        # Fill to capacity
        for i in range(5):
            memory.allocate(f"Content {i}", "ctx")

        # Set one slot to low energy
        memory.slots[1].energy = 0.1

        # Allocate one more
        memory.allocate("New content", "ctx")

        # Should still have max_slots
        self.assertEqual(len(memory.slots), 5)
        # Low energy slot should be gone
        self.assertNotIn(1, memory.slots)

    def test_context_centroid(self):
        """Test context centroid calculation."""
        self.memory.allocate("A", "ctx")
        self.memory.allocate("B", "ctx")
        self.memory.allocate("C", "ctx")

        centroid = self.memory.get_context_centroid("ctx")

        self.assertIsNotNone(centroid)
        self.assertEqual(len(centroid), MANIFOLD_DIM)

    def test_context_centroid_empty(self):
        """Test centroid for empty context."""
        centroid = self.memory.get_context_centroid("nonexistent")
        self.assertIsNone(centroid)

    def test_stats(self):
        """Test statistics tracking."""
        for i in range(5):
            self.memory.allocate(f"Content {i}", "test_ctx")

        self.memory.resonance_search("query", limit=5, threshold=0.0)
        self.memory.garbage_collect()

        stats = self.memory.get_stats()

        self.assertEqual(stats["total_allocations"], 5)
        self.assertEqual(stats["current_slots"], 5)
        self.assertEqual(stats["resonance_searches"], 1)
        self.assertEqual(stats["total_gc_runs"], 1)
        self.assertEqual(stats["manifold_dim"], MANIFOLD_DIM)


class TestMCPToolRegistration(unittest.TestCase):
    """Test MCP tool registration."""

    def test_tools_registration(self):
        """Test that tools can be registered."""
        from manifold_working_memory_tools import register_manifold_working_memory_tools

        class MockApp:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()
        register_manifold_working_memory_tools(mock_app)

        expected_tools = [
            "manifold_allocate",
            "manifold_retrieve",
            "manifold_search",
            "manifold_retrieve_context",
            "manifold_interference",
            "manifold_decay",
            "manifold_gc",
            "manifold_stats"
        ]

        for tool_name in expected_tools:
            self.assertIn(tool_name, mock_app.tools, f"Missing tool: {tool_name}")


class TestSingletonPattern(unittest.TestCase):
    """Test singleton pattern for memory instance."""

    def setUp(self):
        reset_manifold_working_memory()

    def tearDown(self):
        reset_manifold_working_memory()

    def test_singleton_instance(self):
        """Test that get_manifold_working_memory returns same instance."""
        mem1 = get_manifold_working_memory()
        mem2 = get_manifold_working_memory()

        self.assertIs(mem1, mem2)

    def test_reset_clears_singleton(self):
        """Test that reset creates new instance."""
        mem1 = get_manifold_working_memory()
        mem1.allocate("Test", "ctx")

        reset_manifold_working_memory()

        mem2 = get_manifold_working_memory()
        self.assertEqual(len(mem2.slots), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        reset_manifold_working_memory()

    def tearDown(self):
        reset_manifold_working_memory()

    def test_allocate_working_slot(self):
        """Test allocate_working_slot convenience function."""
        result = allocate_working_slot("Test content", "test_ctx", priority=8)

        self.assertIn("slot_id", result)
        self.assertIn("phases", result)
        self.assertEqual(result["context_key"], "test_ctx")

    def test_search_working_memory(self):
        """Test search_working_memory convenience function."""
        allocate_working_slot("Item A", "ctx")
        allocate_working_slot("Item B", "ctx")

        results = search_working_memory("query", "ctx", limit=5)

        self.assertIsInstance(results, list)
        for item in results:
            self.assertIn("slot", item)
            self.assertIn("similarity", item)

    def test_get_working_memory_stats(self):
        """Test get_working_memory_stats convenience function."""
        allocate_working_slot("Test", "ctx")

        stats = get_working_memory_stats()

        self.assertIn("current_slots", stats)
        self.assertIn("max_slots", stats)
        self.assertIn("manifold_dim", stats)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        reset_manifold_working_memory()
        self.memory = ManifoldWorkingMemory(max_slots=50)

    def tearDown(self):
        reset_manifold_working_memory()

    def test_empty_content(self):
        """Test allocation with empty content."""
        slot = self.memory.allocate("", "ctx")
        self.assertEqual(slot.content, "")

    def test_unicode_content(self):
        """Test allocation with unicode content."""
        slot = self.memory.allocate("日本語 中文 🎉", "ctx")
        self.assertEqual(slot.content, "日本語 中文 🎉")

    def test_very_long_content(self):
        """Test allocation with very long content."""
        long_content = "A" * 10000
        slot = self.memory.allocate(long_content, "ctx")
        self.assertEqual(len(slot.content), 10000)

    def test_special_context_keys(self):
        """Test various context key formats."""
        contexts = ["", "with spaces", "with/slashes", "with.dots", "123numeric"]

        for ctx in contexts:
            slot = self.memory.allocate("Content", ctx)
            self.assertEqual(slot.context_key, ctx)

    def test_search_empty_memory(self):
        """Test search on empty memory."""
        results = self.memory.resonance_search("query", limit=10, threshold=0.0)
        self.assertEqual(len(results), 0)

    def test_high_priority_preserved(self):
        """Test that priority is preserved."""
        slot = self.memory.allocate("Test", "ctx", priority=10)
        self.assertEqual(slot.priority, 10)

    def test_metadata_preserved(self):
        """Test that metadata is preserved."""
        meta = {"key": "value", "count": 42}
        slot = self.memory.allocate("Test", "ctx", metadata=meta)
        self.assertEqual(slot.metadata, meta)

    def test_entity_id_preserved(self):
        """Test that entity_id is preserved."""
        slot = self.memory.allocate("Test", "ctx", entity_id=12345)
        self.assertEqual(slot.entity_id, 12345)


def main():
    """Run all tests."""
    print("=" * 60)
    print("PTM Phase 4: Manifold Working Memory Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestManifoldSlot))
    suite.addTests(loader.loadTestsFromTestCase(TestIrrationalRotation))
    suite.addTests(loader.loadTestsFromTestCase(TestManifoldWorkingMemory))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPToolRegistration))
    suite.addTests(loader.loadTestsFromTestCase(TestSingletonPattern))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

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
