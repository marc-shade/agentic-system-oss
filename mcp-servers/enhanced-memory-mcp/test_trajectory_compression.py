#!/usr/bin/env python3
"""
Comprehensive tests for PTM-inspired trajectory compression.

Tests Phase 2 of the enhanced-memory RAG enhancement:
- Trajectory encoding on 8D hyper-torus
- Anchor/bridge bifurcation
- Integration with consolidation.py
- Compression/decompression round-trip
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import unittest
import numpy as np
from trajectory_compression import (
    TrajectoryCompressor,
    IrrationalRotation,
    TrajectoryPoint,
    Trajectory,
    compress_for_archive,
    decompress_from_archive,
    get_stats,
    reset_stats,
    GOLDEN_RATIO,
    MANIFOLD_DIM
)

# Create a helper to use the class method
def analyze_token(token: str) -> tuple:
    """Helper to test token classification using TrajectoryCompressor."""
    compressor = TrajectoryCompressor()
    is_anchor = compressor._is_anchor_token(token)
    return is_anchor, "anchor" if is_anchor else "bridge"


class TestIrrationalRotation(unittest.TestCase):
    """Test the irrational rotation matrix generator."""

    def test_golden_ratio_constant(self):
        """Verify golden ratio is correct."""
        expected = (1 + np.sqrt(5)) / 2
        self.assertAlmostEqual(GOLDEN_RATIO, expected, places=10)

    def test_manifold_dimension(self):
        """Verify manifold dimension is 8."""
        self.assertEqual(MANIFOLD_DIM, 8)

    def test_rotation_creates_trajectory(self):
        """Test that rotation generates valid trajectory points."""
        rotation = IrrationalRotation(dim=8)
        seed = np.zeros(8)
        trajectory = rotation.generate_trajectory(seed, length=100)

        self.assertEqual(len(trajectory), 100)

        # Each point should be 8D
        for point in trajectory:
            self.assertEqual(len(point), 8)

        # All phases should be in [0, 2π)
        for point in trajectory:
            for phase in point:
                self.assertGreaterEqual(phase, 0)
                self.assertLess(phase, 2 * np.pi)

    def test_irrational_rotation_no_repetition(self):
        """Test that irrational rotation never exactly repeats."""
        rotation = IrrationalRotation(dim=8)
        seed = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])

        # Generate many points
        trajectory = rotation.generate_trajectory(seed, length=1000)

        # Convert to tuples for hashing
        points_set = set()
        for point in trajectory:
            point_tuple = tuple(round(p, 6) for p in point)
            points_set.add(point_tuple)

        # Should have nearly all unique points (some rounding collisions OK)
        unique_ratio = len(points_set) / 1000
        self.assertGreater(unique_ratio, 0.95)


class TestTokenAnalysis(unittest.TestCase):
    """Test anchor/bridge token classification."""

    def test_proper_names_are_anchors(self):
        """Proper names should be classified as anchors."""
        anchors = ["OpenAI", "Microsoft", "PyTorch", "TensorFlow"]
        for token in anchors:
            is_anchor, _ = analyze_token(token)
            self.assertTrue(is_anchor, f"{token} should be anchor")

    def test_stopwords_are_bridges(self):
        """Stopwords should be classified as bridges."""
        bridges = ["the", "and", "is", "was", "are", "to", "of", "in"]
        for token in bridges:
            is_anchor, _ = analyze_token(token)
            self.assertFalse(is_anchor, f"{token} should be bridge")

    def test_numbers_are_anchors(self):
        """Numbers should be classified as anchors."""
        numbers = ["42", "3.14159", "2024", "0x8007045D"]
        for token in numbers:
            is_anchor, _ = analyze_token(token)
            self.assertTrue(is_anchor, f"{token} should be anchor")

    def test_acronyms_are_anchors(self):
        """Acronyms should be classified as anchors."""
        acronyms = ["API", "HTTP", "GPU", "CUDA", "SQL"]
        for token in acronyms:
            is_anchor, _ = analyze_token(token)
            self.assertTrue(is_anchor, f"{token} should be anchor")


class TestTrajectoryPoint(unittest.TestCase):
    """Test TrajectoryPoint serialization."""

    def test_anchor_point_serialization(self):
        """Test anchor point compact encoding."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        point = TrajectoryPoint(phases=phases, is_anchor=True, token_index=42)

        # Serialize
        data = point.to_compact()
        self.assertEqual(len(data), 17)  # 1 flag + 8*2 phases

        # Deserialize
        recovered = TrajectoryPoint.from_compact(data)
        self.assertTrue(recovered.is_anchor)

        # Phases should be close (quantization error expected)
        for i in range(8):
            self.assertAlmostEqual(recovered.phases[i], phases[i], delta=0.01)

    def test_bridge_point_serialization(self):
        """Test bridge point compact encoding."""
        phases = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        point = TrajectoryPoint(phases=phases, is_anchor=False, token_index=10)

        # Serialize
        data = point.to_compact()
        self.assertEqual(len(data), 9)  # 1 flag + 8*1 phases

        # Deserialize
        recovered = TrajectoryPoint.from_compact(data)
        self.assertFalse(recovered.is_anchor)


class TestTrajectory(unittest.TestCase):
    """Test full trajectory encoding."""

    def test_trajectory_compression(self):
        """Test trajectory zlib compression."""
        compressor = TrajectoryCompressor()
        text = "OpenAI released GPT-5 with enhanced reasoning capabilities"
        trajectory = compressor.encode_text(text)

        # Should have points
        self.assertGreater(len(trajectory.points), 0)

        # Should have anchors
        self.assertGreater(len(trajectory.anchor_tokens), 0)

        # Compress and decompress
        compressed = trajectory.to_compressed()
        recovered = Trajectory.from_compressed(compressed)

        # Should have same number of points
        self.assertEqual(len(recovered.points), len(trajectory.points))

    def test_round_trip(self):
        """Test full encode -> compress -> decompress -> decode round trip."""
        compressor = TrajectoryCompressor()
        original = "The NVIDIA RTX 4090 GPU processes CUDA 12.3 kernels efficiently"

        # Encode to trajectory
        trajectory = compressor.encode_text(original)

        # Compress
        compressed = trajectory.to_compressed()

        # Decompress
        recovered_traj = Trajectory.from_compressed(compressed)

        # Decode (reconstructs anchors only)
        reconstructed = compressor.decode_trajectory(recovered_traj)

        # Key anchors should be preserved
        for anchor in ["NVIDIA", "RTX", "4090", "GPU", "CUDA"]:
            self.assertIn(anchor, reconstructed)


class TestEntityCompression(unittest.TestCase):
    """Test entity-level compression for archive tier."""

    def setUp(self):
        reset_stats()

    def test_entity_compression(self):
        """Test compressing a full entity."""
        result = compress_for_archive(
            name="PTM-Research-Notes",
            observations=[
                "Phonetic Trajectory Memory uses 16D hyper-torus",
                "Achieves >3000x compression ratio",
                "O(1) retrieval complexity with no decay"
            ],
            entity_type="research"
        )

        self.assertIn("compressed_data", result)
        self.assertIn("compression_meta", result)
        self.assertEqual(result["compression_meta"]["method"], "trajectory_ptm_v1")

    def test_entity_decompression(self):
        """Test decompressing an entity."""
        # Compress
        compressed = compress_for_archive(
            name="Test-Entity",
            observations=["OpenAI GPT-5 API endpoint https://api.openai.com/v1"],
            entity_type="test"
        )

        # Store as JSON and recover (simulates DB storage)
        import json
        json_data = json.dumps(compressed)
        recovered = json.loads(json_data)

        # Decompress
        result = decompress_from_archive(json_data)

        self.assertIn("reconstructed_text", result)
        self.assertIn("anchor_tokens", result)
        self.assertIn("point_count", result)
        # Verify anchors were preserved
        self.assertIn("OpenAI", result["anchor_tokens"])

    def test_stats_tracking(self):
        """Test that compression stats are tracked."""
        reset_stats()

        # Compress a few entities
        for i in range(3):
            compress_for_archive(
                name=f"Test-{i}",
                observations=[f"Entity {i} with OpenAI and Microsoft references"],
                entity_type="test"
            )

        stats = get_stats()

        self.assertEqual(stats["entities_compressed"], 3)
        self.assertGreater(stats["anchor_tokens_stored"], 0)


class TestConsolidationIntegration(unittest.TestCase):
    """Test integration with consolidation.py."""

    def test_import_available(self):
        """Test that consolidation.py can import trajectory compression."""
        try:
            from agi.consolidation import TRAJECTORY_COMPRESSION_AVAILABLE
            self.assertTrue(TRAJECTORY_COMPRESSION_AVAILABLE)
        except ImportError as e:
            self.fail(f"Could not import from consolidation: {e}")

    def test_consolidation_engine_has_compression(self):
        """Test ConsolidationEngine has run_memory_compression method."""
        from agi.consolidation import ConsolidationEngine

        engine = ConsolidationEngine()
        self.assertTrue(hasattr(engine, 'run_memory_compression'))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_text(self):
        """Test handling of empty text."""
        compressor = TrajectoryCompressor()
        trajectory = compressor.encode_text("")

        self.assertEqual(len(trajectory.points), 0)
        self.assertEqual(len(trajectory.anchor_tokens), 0)

    def test_single_token(self):
        """Test handling of single token."""
        compressor = TrajectoryCompressor()
        trajectory = compressor.encode_text("OpenAI")

        self.assertEqual(len(trajectory.points), 1)

    def test_all_stopwords(self):
        """Test text with all stopwords (no anchors)."""
        compressor = TrajectoryCompressor()
        trajectory = compressor.encode_text("the and is a was the and is a")

        # Should still have points
        self.assertGreater(len(trajectory.points), 0)

        # But no anchors
        self.assertEqual(len(trajectory.anchor_tokens), 0)

    def test_unicode_text(self):
        """Test handling of unicode text."""
        compressor = TrajectoryCompressor()
        trajectory = compressor.encode_text("日本語 and 中文 with emoji 🎉")

        # Should handle without error
        self.assertIsNotNone(trajectory)

    def test_very_long_text(self):
        """Test handling of very long text."""
        compressor = TrajectoryCompressor()

        # Generate long text with mix of anchors and bridges
        words = ["OpenAI", "the", "GPT-5", "is", "API", "and", "CUDA"] * 100
        long_text = " ".join(words)

        trajectory = compressor.encode_text(long_text)

        # Should handle without error
        self.assertIsNotNone(trajectory)
        self.assertGreater(len(trajectory.points), 100)


def main():
    """Run all tests."""
    print("=" * 60)
    print("PTM Trajectory Compression Test Suite")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIrrationalRotation))
    suite.addTests(loader.loadTestsFromTestCase(TestTokenAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestTrajectoryPoint))
    suite.addTests(loader.loadTestsFromTestCase(TestTrajectory))
    suite.addTests(loader.loadTestsFromTestCase(TestEntityCompression))
    suite.addTests(loader.loadTestsFromTestCase(TestConsolidationIntegration))
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
