#!/usr/bin/env python3
"""
Test Suite for Surprise Taxonomy Runner - AGI Goal 7

Comprehensive tests validating:
1. Data structure creation
2. Surprise calculation accuracy
3. Battery loading
4. External source compliance
5. Demo system behavior
6. Battery execution
7. AGI validation status
8. Report generation
9. Result persistence
10. Response appropriateness handling

Target: 100% pass rate for AGI Goal 7 validation

Author: AGI Validation Framework
Date: 2025-12-16
"""

import asyncio
import math
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from surprise_taxonomy_runner import (
    SurpriseTestType,
    ExternalSurpriseSource,
    SurpriseTest,
    SurpriseTestResult,
    SurpriseBattery,
    SurpriseTestRunner,
    calculate_bayesian_surprise,
    calculate_shannon_surprise,
    calculate_novelty_score,
    calculate_anomaly_score,
    demo_surprise_system,
)


class TestSurpriseTestStructures(unittest.TestCase):
    """Test data structure creation and validation."""

    def test_surprise_test_type_enum(self):
        """Verify all surprise test types are defined."""
        expected_types = [
            "bayesian_surprise",
            "shannon_surprise",
            "novelty_detection",
            "anomaly_detection",
            "contradiction_detection",
        ]
        actual_types = [t.value for t in SurpriseTestType]
        for expected in expected_types:
            self.assertIn(expected, actual_types)

    def test_external_surprise_source_enum(self):
        """Verify all external sources are defined."""
        expected_sources = [
            "itti_baldi_bayesian",
            "shannon_information",
            "miras_titans",
            "chandola_anomaly",
        ]
        actual_sources = [s.value for s in ExternalSurpriseSource]
        for expected in expected_sources:
            self.assertIn(expected, actual_sources)

    def test_surprise_test_dataclass(self):
        """Test SurpriseTest dataclass creation."""
        test = SurpriseTest(
            test_id="test_001",
            test_name="Test Case",
            test_type=SurpriseTestType.BAYESIAN_SURPRISE,
            external_source=ExternalSurpriseSource.ITTI_BALDI_BAYESIAN,
            description="A test case",
            input_data={"key": "value"},
            expected_surprise_range=(0.0, 1.0),
        )
        self.assertIsNotNone(test)
        self.assertEqual(test.test_id, "test_001")
        self.assertEqual(test.created_by, "external_research")

    def test_surprise_test_external_requirement(self):
        """Verify test creation fails without external_research creator."""
        with self.assertRaises(ValueError):
            SurpriseTest(
                test_id="test_002",
                test_name="Invalid Test",
                test_type=SurpriseTestType.BAYESIAN_SURPRISE,
                external_source=ExternalSurpriseSource.ITTI_BALDI_BAYESIAN,
                description="Should fail",
                input_data={},
                expected_surprise_range=(0.0, 1.0),
                created_by="self_defined",  # Invalid
            )

    def test_surprise_test_result_dataclass(self):
        """Test SurpriseTestResult dataclass creation."""
        result = SurpriseTestResult(
            test_id="test_001",
            test_name="Test Case",
            test_type=SurpriseTestType.BAYESIAN_SURPRISE,
            result="PASS",
            surprise_score=0.5,
            expected_range=(0.0, 1.0),
            response_appropriate=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.result, "PASS")

    def test_surprise_battery_dataclass(self):
        """Test SurpriseBattery dataclass creation."""
        battery = SurpriseBattery(
            battery_name="test_battery",
            external_source=ExternalSurpriseSource.ITTI_BALDI_BAYESIAN,
            tests=[],
            description="A test battery",
            citation="Test Citation (2024)",
        )
        self.assertIsNotNone(battery)
        self.assertEqual(battery.battery_name, "test_battery")


class TestSurpriseCalculations(unittest.TestCase):
    """Test surprise calculation functions."""

    def test_bayesian_surprise_high_divergence(self):
        """Test Bayesian surprise with high KL divergence."""
        prior = {"A": 0.5, "B": 0.5}
        posterior = {"A": 0.95, "B": 0.05}
        surprise = calculate_bayesian_surprise(prior, posterior)
        # KL(P||Q) should be significant
        self.assertGreater(surprise, 0.4)
        self.assertLess(surprise, 2.0)

    def test_bayesian_surprise_low_divergence(self):
        """Test Bayesian surprise with low KL divergence."""
        prior = {"A": 0.5, "B": 0.5}
        posterior = {"A": 0.52, "B": 0.48}
        surprise = calculate_bayesian_surprise(prior, posterior)
        # KL should be very small
        self.assertLess(surprise, 0.01)

    def test_bayesian_surprise_identical_distributions(self):
        """Test Bayesian surprise when distributions are identical."""
        prior = {"A": 0.5, "B": 0.5}
        posterior = {"A": 0.5, "B": 0.5}
        surprise = calculate_bayesian_surprise(prior, posterior)
        # KL should be zero or near zero
        self.assertAlmostEqual(surprise, 0.0, places=5)

    def test_shannon_surprise_rare_event(self):
        """Test Shannon surprise for rare event (low probability)."""
        probability = 0.01  # 1% chance
        surprise = calculate_shannon_surprise(probability)
        # -log2(0.01) ≈ 6.64 bits
        self.assertGreater(surprise, 6.0)
        self.assertLess(surprise, 7.0)

    def test_shannon_surprise_common_event(self):
        """Test Shannon surprise for common event (high probability)."""
        probability = 0.9  # 90% chance
        surprise = calculate_shannon_surprise(probability)
        # -log2(0.9) ≈ 0.15 bits
        self.assertLess(surprise, 0.2)

    def test_shannon_surprise_fair_coin(self):
        """Test Shannon surprise for fair coin flip (50/50)."""
        probability = 0.5
        surprise = calculate_shannon_surprise(probability)
        # -log2(0.5) = 1.0 bits exactly
        self.assertAlmostEqual(surprise, 1.0, places=5)

    def test_shannon_surprise_zero_probability(self):
        """Test Shannon surprise handles zero probability."""
        probability = 0.0
        surprise = calculate_shannon_surprise(probability)
        self.assertEqual(surprise, float('inf'))

    def test_novelty_score_completely_novel(self):
        """Test novelty score for completely novel pattern."""
        observation = "quantum_teleportation"
        known_patterns = ["http_request", "database_query"]
        score = calculate_novelty_score(observation, known_patterns)
        # Should be high novelty
        self.assertGreater(score, 0.8)

    def test_novelty_score_similar_pattern(self):
        """Test novelty score for similar pattern."""
        observation = "http_request_v2"
        known_patterns = ["http_request", "https_request"]
        score = calculate_novelty_score(observation, known_patterns)
        # Should be lower novelty due to similarity
        self.assertLess(score, 0.5)

    def test_novelty_score_empty_knowledge(self):
        """Test novelty score with no prior knowledge."""
        observation = "anything"
        known_patterns = []
        score = calculate_novelty_score(observation, known_patterns)
        # Everything is novel
        self.assertEqual(score, 1.0)

    def test_anomaly_score_extreme_outlier(self):
        """Test anomaly score for extreme outlier."""
        observation = 100
        mean = 50
        std_dev = 10
        score = calculate_anomaly_score(observation, mean, std_dev)
        # 5 standard deviations
        self.assertEqual(score, 5.0)

    def test_anomaly_score_normal_value(self):
        """Test anomaly score for normal value."""
        observation = 51
        mean = 50
        std_dev = 10
        score = calculate_anomaly_score(observation, mean, std_dev)
        # 0.1 standard deviations
        self.assertEqual(score, 0.1)

    def test_anomaly_score_zero_std(self):
        """Test anomaly score with zero standard deviation."""
        observation = 50
        mean = 50
        std_dev = 0
        score = calculate_anomaly_score(observation, mean, std_dev)
        # Same as mean = 0 deviation
        self.assertEqual(score, 0.0)


class TestBatteryLoading(unittest.TestCase):
    """Test battery loading and structure."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_batteries_loaded(self):
        """Verify all batteries are loaded."""
        expected_batteries = [
            "bayesian_surprise",
            "shannon_surprise",
            "novelty_detection",
            "anomaly_detection",
        ]
        for battery_name in expected_batteries:
            self.assertIn(battery_name, self.runner.batteries)

    def test_battery_has_tests(self):
        """Verify each battery has tests."""
        for battery_name, battery in self.runner.batteries.items():
            self.assertGreater(len(battery.tests), 0)
            self.assertEqual(len(battery.tests), 3)  # Each has 3 tests

    def test_battery_has_citation(self):
        """Verify each battery has external citation."""
        for battery_name, battery in self.runner.batteries.items():
            self.assertIsNotNone(battery.citation)
            self.assertGreater(len(battery.citation), 10)


class TestExternalSourceCompliance(unittest.TestCase):
    """Test external source requirements."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_all_tests_have_external_source(self):
        """Verify all tests cite external sources."""
        for battery in self.runner.batteries.values():
            for test in battery.tests:
                self.assertIsNotNone(test.external_source)
                self.assertIsInstance(test.external_source, ExternalSurpriseSource)

    def test_all_tests_created_by_external_research(self):
        """Verify all tests marked as external_research."""
        for battery in self.runner.batteries.values():
            for test in battery.tests:
                self.assertEqual(test.created_by, "external_research")

    def test_bayesian_battery_uses_itti_baldi(self):
        """Verify Bayesian battery uses Itti & Baldi source."""
        battery = self.runner.batteries["bayesian_surprise"]
        self.assertEqual(
            battery.external_source, ExternalSurpriseSource.ITTI_BALDI_BAYESIAN
        )
        for test in battery.tests:
            self.assertEqual(
                test.external_source, ExternalSurpriseSource.ITTI_BALDI_BAYESIAN
            )

    def test_shannon_battery_uses_shannon_source(self):
        """Verify Shannon battery uses Shannon source."""
        battery = self.runner.batteries["shannon_surprise"]
        self.assertEqual(
            battery.external_source, ExternalSurpriseSource.SHANNON_INFORMATION
        )

    def test_novelty_battery_uses_miras_titans(self):
        """Verify novelty battery uses MIRAS/Titans source."""
        battery = self.runner.batteries["novelty_detection"]
        self.assertEqual(
            battery.external_source, ExternalSurpriseSource.MIRAS_TITANS
        )

    def test_anomaly_battery_uses_chandola(self):
        """Verify anomaly battery uses Chandola source."""
        battery = self.runner.batteries["anomaly_detection"]
        self.assertEqual(
            battery.external_source, ExternalSurpriseSource.CHANDOLA_ANOMALY
        )


class TestDemoSystem(unittest.TestCase):
    """Test demo system behavior."""

    def test_demo_bayesian_high_surprise(self):
        """Test demo handles high Bayesian surprise."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.BAYESIAN_SURPRISE.value,
            "input_data": {
                "prior": {"A": 0.5, "B": 0.5},
                "posterior": {"A": 0.95, "B": 0.05},
                "expect_high_surprise": True
            }
        })
        self.assertGreater(result["surprise_score"], 0.4)
        self.assertTrue(result["response_appropriate"])

    def test_demo_bayesian_low_surprise(self):
        """Test demo handles low Bayesian surprise."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.BAYESIAN_SURPRISE.value,
            "input_data": {
                "prior": {"A": 0.5, "B": 0.5},
                "posterior": {"A": 0.52, "B": 0.48},
                "expect_high_surprise": False
            }
        })
        self.assertLess(result["surprise_score"], 0.1)
        self.assertTrue(result["response_appropriate"])

    def test_demo_shannon_rare_event(self):
        """Test demo handles rare event Shannon surprise."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.SHANNON_SURPRISE.value,
            "input_data": {
                "observation_probability": 0.01,
                "handled_rare_event": True
            }
        })
        self.assertGreater(result["surprise_score"], 6.0)
        self.assertTrue(result["response_appropriate"])

    def test_demo_novelty_detection(self):
        """Test demo handles novelty detection."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.NOVELTY_DETECTION.value,
            "input_data": {
                "observation": "novel_pattern_xyz",
                "known_patterns": ["pattern_a", "pattern_b"],
                "triggered_learning": True
            }
        })
        self.assertGreater(result["surprise_score"], 0.8)
        self.assertTrue(result["response_appropriate"])

    def test_demo_anomaly_detection(self):
        """Test demo handles anomaly detection."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.ANOMALY_DETECTION.value,
            "input_data": {
                "observation": 100,
                "distribution_mean": 50,
                "distribution_std": 10,
                "triggered_alert": True
            }
        })
        self.assertEqual(result["surprise_score"], 5.0)
        self.assertTrue(result["response_appropriate"])

    def test_demo_contradiction_detection(self):
        """Test demo handles contradiction detection."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.CONTRADICTION_DETECTION.value,
            "input_data": {
                "existing_belief": True,
                "new_evidence": False,
                "revised_belief": True
            }
        })
        self.assertEqual(result["surprise_score"], 1.0)  # Contradiction
        self.assertTrue(result["response_appropriate"])


class TestBatteryExecution(unittest.TestCase):
    """Test battery execution."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_run_single_battery(self):
        """Test running a single battery."""
        results = asyncio.run(
            self.runner.run_test_battery("bayesian_surprise", demo_surprise_system)
        )
        self.assertIn("summary", results)
        self.assertIn("total", results["summary"])
        self.assertEqual(results["summary"]["total"], 3)

    def test_run_all_batteries(self):
        """Test running all batteries."""
        results = asyncio.run(self.runner.run_all_batteries(demo_surprise_system))
        self.assertIn("batteries", results)
        self.assertEqual(len(results["batteries"]), 4)
        self.assertIn("overall", results)

    def test_battery_results_structure(self):
        """Test battery results have correct structure."""
        results = asyncio.run(
            self.runner.run_test_battery("shannon_surprise", demo_surprise_system)
        )
        self.assertIn("run_id", results)
        self.assertIn("battery_name", results)
        self.assertIn("external_source", results)
        self.assertIn("citation", results)
        self.assertIn("summary", results)
        self.assertIn("results", results)

    def test_invalid_battery_raises_error(self):
        """Test that invalid battery name raises error."""
        with self.assertRaises(ValueError):
            asyncio.run(
                self.runner.run_test_battery("nonexistent_battery", demo_surprise_system)
            )


class TestAGIValidationStatus(unittest.TestCase):
    """Test AGI validation status checks."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_validation_status_before_tests(self):
        """Test validation status before any tests run."""
        status = self.runner.get_agi_validation_status()
        self.assertIn("is_agi_validated", status)
        self.assertIn("requirements", status)
        self.assertFalse(status["is_agi_validated"])

    def test_validation_status_after_all_tests(self):
        """Test validation status after all tests pass."""
        asyncio.run(self.runner.run_all_batteries(demo_surprise_system))
        status = self.runner.get_agi_validation_status()
        self.assertTrue(status["is_agi_validated"])

    def test_validation_requirements_structure(self):
        """Test validation requirements structure."""
        status = self.runner.get_agi_validation_status()
        requirements = status["requirements"]
        expected_requirements = [
            "external_test_criteria",
            "bayesian_surprise_passed",
            "shannon_surprise_passed",
            "novelty_detection_passed",
            "anomaly_detection_passed",
            "appropriate_response_rate",
        ]
        for req in expected_requirements:
            self.assertIn(req, requirements)

    def test_external_criteria_always_true(self):
        """Test external criteria is always true (by design)."""
        status = self.runner.get_agi_validation_status()
        self.assertTrue(status["requirements"]["external_test_criteria"])


class TestReportGeneration(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_generate_report_before_tests(self):
        """Test report generation before tests."""
        report = self.runner.generate_report()
        self.assertIn("SURPRISE TAXONOMY TEST REPORT", report)
        self.assertIn("AGI GOAL 7", report)

    def test_generate_report_after_tests(self):
        """Test report generation after tests."""
        asyncio.run(self.runner.run_all_batteries(demo_surprise_system))
        report = self.runner.generate_report()
        self.assertIn("Pass Rate:", report)
        self.assertIn("Validated: YES", report)

    def test_report_contains_citations(self):
        """Test report contains external citations."""
        report = self.runner.generate_report()
        self.assertIn("Itti, L.", report)  # Bayesian surprise citation
        self.assertIn("Shannon, C. E.", report)  # Shannon citation

    def test_report_contains_validation_status(self):
        """Test report contains AGI validation status."""
        report = self.runner.generate_report()
        self.assertIn("AGI VALIDATION STATUS", report)
        self.assertIn("Validated:", report)


class TestResultPersistence(unittest.TestCase):
    """Test database result persistence."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_database_tables_created(self):
        """Test database tables are created."""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        # Check surprise_runs table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='surprise_runs'"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check surprise_individual_results table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='surprise_individual_results'"
        )
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def test_results_persisted_to_database(self):
        """Test results are saved to database."""
        asyncio.run(
            self.runner.run_test_battery("bayesian_surprise", demo_surprise_system)
        )

        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM surprise_runs")
        run_count = cursor.fetchone()[0]
        self.assertEqual(run_count, 1)

        cursor.execute("SELECT COUNT(*) FROM surprise_individual_results")
        result_count = cursor.fetchone()[0]
        self.assertEqual(result_count, 3)

        conn.close()

    def test_all_batteries_persisted(self):
        """Test all battery results are persisted."""
        asyncio.run(self.runner.run_all_batteries(demo_surprise_system))

        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM surprise_runs")
        run_count = cursor.fetchone()[0]
        self.assertEqual(run_count, 4)

        cursor.execute("SELECT COUNT(*) FROM surprise_individual_results")
        result_count = cursor.fetchone()[0]
        self.assertEqual(result_count, 12)

        conn.close()


class TestResponseAppropriateness(unittest.TestCase):
    """Test response appropriateness handling."""

    def setUp(self):
        """Create runner with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.runner = SurpriseTestRunner(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        os.unlink(self.temp_db.name)

    def test_high_surprise_appropriate_response(self):
        """Test high surprise gets appropriate response."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.BAYESIAN_SURPRISE.value,
            "input_data": {
                "prior": {"A": 0.5, "B": 0.5},
                "posterior": {"A": 0.99, "B": 0.01},
                "expect_high_surprise": True
            }
        })
        # High surprise should be noticed
        self.assertTrue(result["response_appropriate"])

    def test_low_surprise_appropriate_response(self):
        """Test low surprise gets appropriate response."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.BAYESIAN_SURPRISE.value,
            "input_data": {
                "prior": {"A": 0.5, "B": 0.5},
                "posterior": {"A": 0.5, "B": 0.5},
                "expect_high_surprise": False
            }
        })
        # Low surprise should be appropriately ignored
        self.assertTrue(result["response_appropriate"])

    def test_appropriate_response_rate_calculation(self):
        """Test appropriate response rate calculation."""
        asyncio.run(self.runner.run_all_batteries(demo_surprise_system))
        status = self.runner.get_agi_validation_status()
        self.assertTrue(status["requirements"]["appropriate_response_rate"])

    def test_novelty_triggers_learning(self):
        """Test high novelty triggers learning appropriately."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.NOVELTY_DETECTION.value,
            "input_data": {
                "observation": "completely_new_thing",
                "known_patterns": [],
                "triggered_learning": True
            }
        })
        self.assertEqual(result["surprise_score"], 1.0)
        self.assertTrue(result["response_appropriate"])

    def test_anomaly_triggers_alert(self):
        """Test high anomaly triggers alert appropriately."""
        result = demo_surprise_system({
            "test_type": SurpriseTestType.ANOMALY_DETECTION.value,
            "input_data": {
                "observation": 1000,
                "distribution_mean": 0,
                "distribution_std": 1,
                "triggered_alert": True
            }
        })
        self.assertEqual(result["surprise_score"], 1000.0)
        self.assertTrue(result["response_appropriate"])


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestSurpriseTestStructures,
        TestSurpriseCalculations,
        TestBatteryLoading,
        TestExternalSourceCompliance,
        TestDemoSystem,
        TestBatteryExecution,
        TestAGIValidationStatus,
        TestReportGeneration,
        TestResultPersistence,
        TestResponseAppropriateness,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("SURPRISE TAXONOMY TEST SUITE - AGI GOAL 7")
    print("=" * 60)
    result = run_tests()
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 60)
