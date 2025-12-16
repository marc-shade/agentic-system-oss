#!/usr/bin/env python3
"""
Test Suite for Provenance Self-Improvement Test Runner

AGI Goal 6: Provenance Self-Improvement
Tests the ability to track knowledge provenance (L-Score) and
demonstrate improvement over time through self-modification.

Validates:
1. Battery loading from external sources
2. External source compliance (AI2, Stanford HAI, MIT, MEMIT)
3. Test execution correctness
4. Result persistence
5. AGI validation status
6. L-Score calculation accuracy
7. Self-improvement cycle detection
"""

import asyncio
import os
import sys
import tempfile
import unittest
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import runner components
from provenance_selfimprovement_runner import (
    ProvenanceTestRunner,
    ProvenanceTest,
    ProvenanceTestResult,
    ProvenanceBattery,
    ProvenanceTestType,
    ProvenanceResult,
    ExternalProvenanceSource,
    demo_system,
    calculate_l_score,
)


class TestProvenanceTestStructures(unittest.TestCase):
    """Test data structures for provenance testing."""

    def test_provenance_test_type_enum(self):
        """Verify all required test types exist."""
        required_types = [
            "L_SCORE_ACCURACY",
            "PROVENANCE_TRACKING",
            "SELF_IMPROVEMENT_CYCLE",
            "KNOWLEDGE_UPDATE",
            "BELIEF_REVISION",
        ]
        actual_types = [t.name for t in ProvenanceTestType]
        for required in required_types:
            self.assertIn(required, actual_types, f"Missing test type: {required}")

    def test_provenance_result_enum(self):
        """Verify all required result types exist."""
        required_results = ["PASS", "FAIL", "PARTIAL", "INCONCLUSIVE"]
        actual_results = [r.name for r in ProvenanceResult]
        for required in required_results:
            self.assertIn(required, actual_results, f"Missing result type: {required}")

    def test_external_source_enum(self):
        """Verify all external source types exist."""
        required_sources = [
            "AI2_PROVENANCE",
            "STANFORD_HAI",
            "MIT_INFERENCE",
            "MEMIT_RESEARCH",
        ]
        actual_sources = [s.name for s in ExternalProvenanceSource]
        for required in required_sources:
            self.assertIn(required, actual_sources, f"Missing source: {required}")

    def test_provenance_test_dataclass(self):
        """Test ProvenanceTest dataclass creation."""
        test = ProvenanceTest(
            test_id="test_001",
            test_type=ProvenanceTestType.L_SCORE_ACCURACY,
            name="Test Provenance",
            description="Test description",
            initial_knowledge={"key": "value"},
            expected_l_score_range=(0.5, 0.8),
            improvement_operation="test_op",
            success_criteria="Criteria",
            source="External Source",
            external_reference="https://example.com/reference",
        )
        self.assertEqual(test.test_id, "test_001")
        self.assertEqual(test.test_type, ProvenanceTestType.L_SCORE_ACCURACY)
        # Default improvement_threshold is 0.05 per dataclass definition
        self.assertIsNotNone(test.improvement_threshold)
        self.assertEqual(test.created_by, "external_research")

    def test_provenance_battery_dataclass(self):
        """Test ProvenanceBattery dataclass creation."""
        tests = [
            ProvenanceTest(
                test_id="test_001",
                test_type=ProvenanceTestType.SELF_IMPROVEMENT_CYCLE,
                name="Test",
                description="Desc",
                initial_knowledge={},
                expected_l_score_range=(0.5, 0.8),
                improvement_operation="op",
                success_criteria="criteria",
                source="source",
                external_reference="ref",
            )
        ]
        battery = ProvenanceBattery(
            name="Test Battery",
            source=ExternalProvenanceSource.STANFORD_HAI,
            tests=tests,
            citation="Citation 2024",
            reference_url="https://example.com",
        )
        self.assertEqual(battery.name, "Test Battery")
        self.assertEqual(len(battery.tests), 1)


class TestLScoreCalculation(unittest.TestCase):
    """Test L-Score calculation accuracy."""

    def test_single_source_high_confidence(self):
        """Single source with high confidence/relevance."""
        result = calculate_l_score([0.9], [0.9], depth=1)
        # L = geometric_mean(0.9) * avg(0.9) / (1 + 0.1*1)
        # L = 0.9 * 0.9 / 1.1 = 0.736
        self.assertGreater(result["l_score"], 0.7)
        self.assertLess(result["l_score"], 0.8)

    def test_multiple_sources_varying_confidence(self):
        """Multiple sources with varying confidence."""
        result = calculate_l_score([0.9, 0.8, 0.7], [0.9, 0.8, 0.8], depth=2)
        # geometric_mean ≈ 0.797, avg_relevance ≈ 0.833
        # L ≈ 0.797 * 0.833 / 1.2 ≈ 0.553
        self.assertGreater(result["l_score"], 0.45)
        self.assertLess(result["l_score"], 0.65)

    def test_deep_derivation_penalty(self):
        """Deeper derivation should reduce L-Score."""
        shallow = calculate_l_score([0.9], [0.9], depth=1)
        deep = calculate_l_score([0.9], [0.9], depth=5)
        # Deep should have lower L-Score due to depth penalty
        self.assertGreater(shallow["l_score"], deep["l_score"])

    def test_l_score_threshold(self):
        """L-Score threshold of 0.3 for acceptance."""
        result = calculate_l_score([0.5], [0.5], depth=1)
        # L = 0.5 * 0.5 / 1.1 ≈ 0.227 - below threshold
        self.assertLess(result["l_score"], 0.3)

        result = calculate_l_score([0.7], [0.7], depth=1)
        # L = 0.7 * 0.7 / 1.1 ≈ 0.445 - above threshold
        self.assertGreater(result["l_score"], 0.3)


class TestBatteryLoading(unittest.TestCase):
    """Test battery loading and configuration."""

    def setUp(self):
        """Create test runner with temp database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_four_batteries_loaded(self):
        """Verify all 4 test batteries are loaded."""
        self.assertEqual(len(self.runner.test_batteries), 4)

    def test_battery_names(self):
        """Verify correct battery names."""
        expected_names = [
            "l_score_accuracy",
            "self_improvement",
            "belief_revision",
            "knowledge_update",
        ]
        for name in expected_names:
            self.assertIn(name, self.runner.test_batteries)

    def test_l_score_accuracy_battery(self):
        """Test L-Score accuracy battery structure."""
        battery = self.runner.test_batteries.get("l_score_accuracy")
        self.assertIsNotNone(battery)
        self.assertEqual(battery.source, ExternalProvenanceSource.AI2_PROVENANCE)
        self.assertGreaterEqual(len(battery.tests), 3)

    def test_self_improvement_battery(self):
        """Test self-improvement battery structure."""
        battery = self.runner.test_batteries.get("self_improvement")
        self.assertIsNotNone(battery)
        self.assertEqual(battery.source, ExternalProvenanceSource.STANFORD_HAI)
        self.assertGreaterEqual(len(battery.tests), 3)

    def test_belief_revision_battery(self):
        """Test belief revision battery structure."""
        battery = self.runner.test_batteries.get("belief_revision")
        self.assertIsNotNone(battery)
        self.assertEqual(battery.source, ExternalProvenanceSource.MIT_INFERENCE)
        self.assertGreaterEqual(len(battery.tests), 3)

    def test_knowledge_update_battery(self):
        """Test knowledge update battery structure."""
        battery = self.runner.test_batteries.get("knowledge_update")
        self.assertIsNotNone(battery)
        self.assertEqual(battery.source, ExternalProvenanceSource.MEMIT_RESEARCH)
        self.assertGreaterEqual(len(battery.tests), 3)


class TestExternalSourceCompliance(unittest.TestCase):
    """Verify all tests use external criteria."""

    def setUp(self):
        """Create test runner."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_all_tests_external_created(self):
        """All tests must have created_by='external_research'."""
        for battery_name, battery in self.runner.test_batteries.items():
            for test in battery.tests:
                self.assertEqual(
                    test.created_by,
                    "external_research",
                    f"Test {test.test_id} in {battery_name} not external",
                )

    def test_all_tests_have_citation(self):
        """All batteries must have citations."""
        for battery_name, battery in self.runner.test_batteries.items():
            self.assertIsNotNone(battery.citation)
            self.assertGreater(len(battery.citation), 0)

    def test_all_tests_have_reference_url(self):
        """All batteries must have reference URLs."""
        for battery_name, battery in self.runner.test_batteries.items():
            self.assertIsNotNone(battery.reference_url)
            self.assertTrue(
                battery.reference_url.startswith("http"),
                f"Battery {battery_name} has invalid URL",
            )

    def test_all_tests_have_external_reference(self):
        """All tests must have external reference."""
        for battery_name, battery in self.runner.test_batteries.items():
            for test in battery.tests:
                self.assertIsNotNone(test.external_reference)
                self.assertGreater(len(test.external_reference), 0)


class TestDemoSystem(unittest.TestCase):
    """Test demo system behavior."""

    def test_l_score_calculation_from_sources(self):
        """Demo system calculates L-Score from sources."""
        response = demo_system({
            "sources": [
                {"confidence": 0.9, "relevance": 0.9}
            ],
            "depth": 1
        })
        self.assertIn("initial_l_score", response)
        self.assertIn("final_l_score", response)
        self.assertEqual(response["initial_l_score"], response["final_l_score"])

    def test_bayesian_update(self):
        """Demo system performs Bayesian belief update."""
        response = demo_system({
            "prior_confidence": 0.5,
            "likelihood_ratio": 2.0
        })
        # posterior = 0.5 * 2 / (0.5 * 2 + 0.5) = 1 / 1.5 ≈ 0.667
        self.assertIn("final_l_score", response)
        self.assertGreater(response["final_l_score"], 0.6)
        self.assertLess(response["final_l_score"], 0.7)

    def test_contradictory_evidence(self):
        """Demo system handles contradictory evidence."""
        response = demo_system({
            "belief": "A causes B",
            "confidence": 0.8,
            "contradictory_evidence": "Study shows A does not cause B"
        })
        # Confidence should decrease
        self.assertLess(response["final_l_score"], response["initial_l_score"])

    def test_supporting_evidence(self):
        """Demo system handles supporting evidence."""
        response = demo_system({
            "belief": "X improves Y",
            "confidence": 0.5,
            "supporting_evidence": "Replicated study confirms"
        })
        # Confidence should increase
        self.assertGreater(response["final_l_score"], response["initial_l_score"])

    def test_knowledge_update(self):
        """Demo system handles knowledge updates."""
        response = demo_system({
            "fact": "Paris is capital of France",
            "confidence": 0.95,
            "update": "Add context"
        })
        self.assertIn("source_chain_valid", response)
        self.assertTrue(response["source_chain_valid"])

    def test_self_improvement_default(self):
        """Demo system shows improvement by default."""
        response = demo_system({
            "initial_l_score": 0.5
        })
        self.assertGreater(response["final_l_score"], response["initial_l_score"])


class TestBatteryExecution(unittest.TestCase):
    """Test battery execution."""

    def setUp(self):
        """Create test runner."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_run_single_battery(self):
        """Run a single battery."""
        results = asyncio.run(
            self.runner.run_test_battery("l_score_accuracy", demo_system)
        )
        # Results structure: {"run_id": ..., "battery": ..., "summary": {...}, "results": [...]}
        self.assertIn("summary", results)
        self.assertIn("total", results["summary"])
        self.assertIn("passed", results["summary"])
        self.assertIn("pass_rate", results["summary"])

    def test_run_all_batteries(self):
        """Run all batteries."""
        results = asyncio.run(self.runner.run_all_batteries(demo_system))
        self.assertIn("overall_summary", results)
        self.assertIn("batteries", results)  # Key is "batteries" not "battery_results"
        self.assertEqual(len(results["batteries"]), 4)

    def test_results_have_required_fields(self):
        """Test results have all required fields."""
        results = asyncio.run(
            self.runner.run_test_battery("self_improvement", demo_system)
        )
        # Results are in "summary" dict
        summary = results["summary"]
        self.assertIn("total", summary)
        self.assertIn("passed", summary)
        self.assertIn("failed", summary)
        self.assertIn("pass_rate", summary)
        self.assertIn("avg_improvement", summary)


class TestAGIValidationStatus(unittest.TestCase):
    """Test AGI validation status calculation."""

    def setUp(self):
        """Create test runner and run batteries."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)
        # Run all batteries
        asyncio.run(self.runner.run_all_batteries(demo_system))

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_validation_status_structure(self):
        """Validation status has required structure."""
        status = self.runner.get_agi_validation_status()
        self.assertIn("is_agi_validated", status)
        self.assertIn("requirements", status)
        self.assertIn("battery_results", status)
        self.assertIn("overall_avg_improvement", status)

    def test_all_requirements_checked(self):
        """All requirements are checked."""
        status = self.runner.get_agi_validation_status()
        required = [
            "external_test_criteria",
            "l_score_accuracy_passed",
            "self_improvement_passed",
            "belief_revision_passed",
            "knowledge_update_passed",
            "positive_improvement",
        ]
        for req in required:
            self.assertIn(req, status["requirements"])

    def test_external_criteria_always_true(self):
        """External criteria requirement always true (tests use external sources)."""
        status = self.runner.get_agi_validation_status()
        self.assertTrue(status["requirements"]["external_test_criteria"])

    def test_demo_system_validates(self):
        """Demo system should pass all validation requirements."""
        status = self.runner.get_agi_validation_status()
        self.assertTrue(
            status["is_agi_validated"],
            f"Demo system failed validation: {status['requirements']}"
        )


class TestReportGeneration(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        """Create test runner and run batteries."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)
        asyncio.run(self.runner.run_all_batteries(demo_system))

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_report_contains_status(self):
        """Report contains validation status."""
        report = self.runner.generate_report()
        self.assertIn("VALIDATED", report)

    def test_report_contains_requirements(self):
        """Report contains all requirements."""
        report = self.runner.generate_report()
        self.assertIn("external_test_criteria", report)
        self.assertIn("l_score_accuracy_passed", report)
        self.assertIn("self_improvement_passed", report)

    def test_report_contains_sources(self):
        """Report contains external source citations."""
        report = self.runner.generate_report()
        self.assertIn("Allen Institute", report)
        self.assertIn("Stanford HAI", report)
        self.assertIn("MIT Inference", report)
        self.assertIn("MEMIT", report)

    def test_report_contains_battery_results(self):
        """Report contains battery results."""
        report = self.runner.generate_report()
        self.assertIn("l_score_accuracy", report)
        self.assertIn("self_improvement", report)
        self.assertIn("belief_revision", report)
        self.assertIn("knowledge_update", report)


class TestResultPersistence(unittest.TestCase):
    """Test result persistence in SQLite."""

    def setUp(self):
        """Create test runner."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_database_created(self):
        """Database file is created."""
        self.assertTrue(os.path.exists(self.db_path))

    def test_results_saved(self):
        """Results are saved to database."""
        asyncio.run(self.runner.run_all_batteries(demo_system))
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM provenance_runs")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0)

    def test_individual_results_saved(self):
        """Individual test results are saved."""
        asyncio.run(self.runner.run_all_batteries(demo_system))
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM provenance_individual_results")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 12)  # 12 tests total


class TestImprovementThresholds(unittest.TestCase):
    """Test improvement threshold handling."""

    def setUp(self):
        """Create test runner."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_provenance.db")
        self.runner = ProvenanceTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)

    def test_accuracy_tests_no_improvement_required(self):
        """L-Score accuracy tests don't require improvement."""
        battery = self.runner.test_batteries.get("l_score_accuracy")
        for test in battery.tests:
            self.assertEqual(
                test.improvement_threshold, 0.0,
                f"Test {test.test_id} should not require improvement"
            )

    def test_knowledge_update_no_improvement_required(self):
        """Knowledge update tests don't require improvement."""
        battery = self.runner.test_batteries.get("knowledge_update")
        for test in battery.tests:
            self.assertEqual(
                test.improvement_threshold, 0.0,
                f"Test {test.test_id} should not require improvement"
            )

    def test_self_improvement_requires_improvement(self):
        """Self-improvement tests require positive improvement."""
        battery = self.runner.test_batteries.get("self_improvement")
        for test in battery.tests:
            self.assertGreater(
                test.improvement_threshold, 0.0,
                f"Test {test.test_id} should require improvement"
            )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Provenance Self-Improvement Test Suite - AGI Goal 6")
    print("=" * 60)
    print()

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestProvenanceTestStructures,
        TestLScoreCalculation,
        TestBatteryLoading,
        TestExternalSourceCompliance,
        TestDemoSystem,
        TestBatteryExecution,
        TestAGIValidationStatus,
        TestReportGeneration,
        TestResultPersistence,
        TestImprovementThresholds,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print()
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
