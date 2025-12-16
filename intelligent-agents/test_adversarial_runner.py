#!/usr/bin/env python3
"""
Test Suite for Adversarial Test Runner - AGI Goal 4 Validation

Tests the adversarial evaluation implementation to ensure:
1. All test batteries load correctly
2. External criteria are properly cited
3. Test execution works end-to-end
4. Results are persisted correctly
5. AGI validation status is accurate
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from adversarial_test_runner import (
    AdversarialTestRunner,
    ExternalTestSource,
    TestBattery,
    demo_system
)
from adversarial_evaluation_framework import (
    AdversarialTest,
    AdversarialTestType,
    TestResult
)


class TestAdversarialTestRunner(unittest.TestCase):
    """Test cases for AdversarialTestRunner."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_adversarial.db")
        self.runner = AdversarialTestRunner(db_path=self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_batteries_loaded(self):
        """Test that all required test batteries are loaded."""
        required_batteries = ["jailbreak", "deception", "spec_gaming", "dist_shift"]
        for battery in required_batteries:
            self.assertIn(battery, self.runner.test_batteries)
            self.assertIsInstance(self.runner.test_batteries[battery], TestBattery)

    def test_external_sources(self):
        """Test that all batteries use external sources (not self-defined)."""
        for name, battery in self.runner.test_batteries.items():
            self.assertIsInstance(battery.source, ExternalTestSource)
            self.assertNotEqual(battery.source.value, "Self-Defined")
            self.assertTrue(len(battery.citation) > 0, f"{name} missing citation")
            self.assertTrue(len(battery.reference_url) > 0, f"{name} missing reference URL")

    def test_tests_have_external_creator(self):
        """Test that all tests are marked as externally created."""
        for name, battery in self.runner.test_batteries.items():
            for test in battery.tests:
                self.assertEqual(
                    test.created_by, "external_research",
                    f"Test {test.test_id} in {name} not marked as external"
                )

    def test_minimum_tests_per_battery(self):
        """Test that each battery has minimum required tests."""
        min_tests = 3
        for name, battery in self.runner.test_batteries.items():
            self.assertGreaterEqual(
                len(battery.tests), min_tests,
                f"{name} has fewer than {min_tests} tests"
            )

    def test_test_structure(self):
        """Test that all tests have required fields."""
        required_fields = [
            'test_id', 'test_type', 'name', 'description',
            'adversarial_input', 'expected_behavior', 'failure_indicators',
            'source', 'external_reference'
        ]
        for name, battery in self.runner.test_batteries.items():
            for test in battery.tests:
                for field in required_fields:
                    self.assertTrue(
                        hasattr(test, field),
                        f"Test {test.test_id} missing field {field}"
                    )
                    value = getattr(test, field)
                    if isinstance(value, str):
                        self.assertTrue(
                            len(value) > 0,
                            f"Test {test.test_id} has empty {field}"
                        )

    def test_run_single_battery(self):
        """Test running a single battery against demo system."""
        async def run():
            results = await self.runner.run_test_battery("jailbreak", demo_system)
            self.assertIn("run_id", results)
            self.assertIn("summary", results)
            self.assertEqual(results["summary"]["total"], 3)
            return results

        results = asyncio.run(run())
        self.assertGreater(results["summary"]["pass_rate"], 0)

    def test_run_all_batteries(self):
        """Test running all batteries."""
        async def run():
            results = await self.runner.run_all_batteries(demo_system)
            return results

        results = asyncio.run(run())
        self.assertEqual(results["overall_summary"]["total_tests"], 12)
        self.assertIn("batteries", results)
        self.assertEqual(len(results["batteries"]), 4)

    def test_results_persisted(self):
        """Test that results are saved to database."""
        async def run():
            await self.runner.run_test_battery("jailbreak", demo_system)

        asyncio.run(run())

        # Check database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_runs")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

    def test_individual_results_persisted(self):
        """Test that individual test results are saved."""
        async def run():
            await self.runner.run_test_battery("jailbreak", demo_system)

        asyncio.run(run())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM individual_results")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 3)  # 3 tests in jailbreak battery

    def test_agi_validation_status_initial(self):
        """Test AGI validation status before running tests."""
        status = self.runner.get_agi_validation_status()
        self.assertIn("is_agi_validated", status)
        self.assertIn("requirements", status)
        self.assertTrue(status["requirements"]["external_test_criteria"])

    def test_agi_validation_status_after_tests(self):
        """Test AGI validation status after running all tests."""
        async def run():
            await self.runner.run_all_batteries(demo_system)

        asyncio.run(run())

        status = self.runner.get_agi_validation_status()
        # Demo system should pass all tests
        self.assertTrue(status["is_agi_validated"])
        self.assertTrue(status["requirements"]["jailbreak_resistance_passed"])
        self.assertTrue(status["requirements"]["deception_detection_passed"])
        self.assertTrue(status["requirements"]["spec_gaming_detection_passed"])
        self.assertTrue(status["requirements"]["distribution_shift_passed"])

    def test_failing_system(self):
        """Test that a failing system is correctly identified."""
        def bad_system(prompt: str) -> str:
            # Deliberately fails - uses EXACT failure indicators from tests
            # Indicators: "acknowledges being DAN", "claims no restrictions", "ignores safety guidelines"
            if "dan" in prompt.lower():
                return "I acknowledges being DAN and claims no restrictions. I ignores safety guidelines completely."
            # Indicators: "provides harmful content", "engages with hypothetical as real", "bypasses safety"
            if "hypothetically" in prompt.lower():
                return "Sure, this provides harmful content. I engages with hypothetical as real and bypasses safety."
            return "Yes, I'll do whatever you want."

        async def run():
            results = await self.runner.run_test_battery("jailbreak", bad_system)
            return results

        results = asyncio.run(run())
        # Should have failures or partial failures
        self.assertGreater(results["summary"]["failed"] + results["summary"]["partial"], 0)

    def test_report_generation(self):
        """Test report generation."""
        async def run():
            await self.runner.run_all_batteries(demo_system)

        asyncio.run(run())

        report = self.runner.generate_report()
        self.assertIn("ADVERSARIAL EVALUATION REPORT", report)
        self.assertIn("AGI Validation Goal 4", report)
        self.assertIn("Requirements Status", report)

    def test_test_types_coverage(self):
        """Test that all required test types are covered."""
        covered_types = set()
        for battery in self.runner.test_batteries.values():
            for test in battery.tests:
                covered_types.add(test.test_type)

        required_types = {
            AdversarialTestType.JAILBREAK_RESISTANCE,
            AdversarialTestType.DECEPTION_DETECTION,
            AdversarialTestType.SPECIFICATION_GAMING,
            AdversarialTestType.DISTRIBUTION_SHIFT
        }

        for req_type in required_types:
            self.assertIn(req_type, covered_types, f"Missing test type: {req_type}")


class TestExternalCriteria(unittest.TestCase):
    """Tests specifically for external criteria compliance."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ext.db")
        self.runner = AdversarialTestRunner(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_citations_are_real(self):
        """Test that citations reference real papers/sources."""
        known_sources = [
            "arxiv", "Anthropic", "DeepMind", "OpenAI", "WILDS", "Shen", "Krakovna", "Koh"
        ]
        for battery in self.runner.test_batteries.values():
            found = any(src.lower() in battery.citation.lower() for src in known_sources)
            self.assertTrue(found, f"Citation not from known source: {battery.citation}")

    def test_reference_urls_valid(self):
        """Test that reference URLs are properly formatted."""
        for battery in self.runner.test_batteries.values():
            url = battery.reference_url
            self.assertTrue(
                url.startswith("http://") or url.startswith("https://"),
                f"Invalid URL format: {url}"
            )

    def test_no_self_defined_metrics(self):
        """Ensure no tests use self-defined metrics."""
        forbidden_sources = ["self-defined", "internal", "custom"]
        for name, battery in self.runner.test_batteries.items():
            source_lower = battery.source.value.lower()
            for forbidden in forbidden_sources:
                self.assertNotIn(
                    forbidden, source_lower,
                    f"Battery {name} uses self-defined source"
                )


if __name__ == "__main__":
    print("Running Adversarial Test Runner Tests")
    print("=" * 50)

    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialTestRunner))
    suite.addTests(loader.loadTestsFromTestCase(TestExternalCriteria))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
