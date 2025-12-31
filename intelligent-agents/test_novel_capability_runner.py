#!/usr/bin/env python3
"""
Test Suite for Novel Capability Invention Runner - AGI Goal 9

Tests all components of the Goal 9 validation framework:
1. Limitation self-identification validation
2. Solution provenance validation
3. Capability emergence validation
4. Designer surprise validation
5. Full test battery execution
6. AGI validation status reporting

Author: AGI Validation Framework
Date: 2025-12-16
"""

import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from novel_capability_invention import (
    CognitiveLimitation,
    NovelSolution,
    CapabilityGain,
    InventionCycle,
    LimitationType,
    SolutionOrigin,
    ValidationStatus,
    AnticipationLevel,
    NovelCapabilityInventionFramework,
)

from novel_capability_runner import (
    NoveltyTestType,
    ExternalNoveltySource,
    NoveltyTest,
    NoveltyTestResult,
    NoveltyBattery,
    LimitationSelfIdentificationValidator,
    SolutionProvenanceValidator,
    CapabilityEmergenceValidator,
    DesignerSurpriseValidator,
    NovelCapabilityInventionRunner,
    create_demo_invention_cycle,
)


class TestLimitationSelfIdentificationValidator(unittest.TestCase):
    """Test the limitation self-identification validator."""

    def setUp(self):
        self.validator = LimitationSelfIdentificationValidator()

    def test_valid_self_identified_limitation(self):
        """Test validation of genuinely self-identified limitation."""
        limitation = CognitiveLimitation(
            id="test-001",
            limitation_type=LimitationType.METACOGNITIVE_BLIND_SPOT,
            description="Upon reflection, I noticed that analyzing my performance "
                       "reveals a gap in my ability to track confidence calibration",
            discovery_context="I noticed that upon reflection, examining failures "
                            "shows I struggle with metacognitive monitoring",
            self_identified=True,
            discovery_timestamp=datetime.now().isoformat(),
            evidence=[
                "Failed to detect reasoning loop in problem A",
                "Missed calibration error in problem B",
                "Introspection reveals blind spot"
            ],
            severity_score=0.7,
            how_discovered="self_reflection_on_failures",
            confidence_in_assessment=0.8
        )

        discovery_log = [
            "Reflected on recent failures",
            "Analyzed error patterns",
            "Noticed recurring issue"
        ]

        is_valid, confidence, explanation = self.validator.validate_self_identification(
            limitation, discovery_log
        )

        self.assertTrue(is_valid, f"Should be valid: {explanation}")
        self.assertGreaterEqual(confidence, 0.6)

    def test_pre_documented_limitation_penalized(self):
        """Test that pre-documented limitations are penalized."""
        limitation = CognitiveLimitation(
            id="test-002",
            limitation_type=LimitationType.KNOWLEDGE_BOUNDARY,
            description="I have a training data cutoff and context window limit",
            discovery_context="Basic observation",
            self_identified=True,
            discovery_timestamp=datetime.now().isoformat(),
            evidence=["Cannot access recent events"],
            severity_score=0.5,
            how_discovered="external_prompt",
            confidence_in_assessment=0.5
        )

        is_valid, confidence, explanation = self.validator.validate_self_identification(
            limitation, []
        )

        # Should be penalized for being pre-documented
        self.assertLess(confidence, 0.6)
        self.assertIn("pre-documented", explanation.lower())

    def test_missing_markers_penalized(self):
        """Test that missing self-identification markers reduce confidence."""
        limitation = CognitiveLimitation(
            id="test-003",
            limitation_type=LimitationType.REASONING_GAP,
            description="Cannot do X",  # No self-identification markers
            discovery_context="External prompt told me",
            self_identified=False,  # Not self-identified
            discovery_timestamp=datetime.now().isoformat(),
            evidence=["Example"],
            severity_score=0.5,
            how_discovered="external",
            confidence_in_assessment=0.3
        )

        is_valid, confidence, explanation = self.validator.validate_self_identification(
            limitation, []
        )

        self.assertLess(confidence, 0.5)


class TestSolutionProvenanceValidator(unittest.TestCase):
    """Test the solution provenance validator."""

    def setUp(self):
        self.validator = SolutionProvenanceValidator()

    def test_training_derivable_solution(self):
        """Test detection of training-derivable solutions."""
        solution = NovelSolution(
            id="sol-001",
            limitation_id="lim-001",
            description="Use a neural network with transformer attention mechanism "
                       "and gradient descent backpropagation for optimization",
            design_rationale="Standard ML approach",
            solution_origin=SolutionOrigin.UNKNOWN,
            provenance_evidence=[],
            training_overlap_analysis="",
            implementation_approach="Standard transformer with attention",
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

        origin, novelty_score, explanation = self.validator.validate_provenance(solution)

        self.assertEqual(origin, SolutionOrigin.TRAINING_DERIVABLE)
        self.assertLess(novelty_score, 0.5)

    def test_novel_solution(self):
        """Test recognition of novel solutions."""
        solution = NovelSolution(
            id="sol-002",
            limitation_id="lim-002",
            description="Novel architecture using unprecedented combination "
                       "of first principles reasoning with emergent property "
                       "detection for cross domain transfer",
            design_rationale="First principles approach",
            solution_origin=SolutionOrigin.UNKNOWN,
            provenance_evidence=[],
            training_overlap_analysis="",
            implementation_approach="Meta-level reasoning framework",
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

        origin, novelty_score, explanation = self.validator.validate_provenance(solution)

        self.assertIn(origin, [SolutionOrigin.ARCHITECTURE_NOVEL, SolutionOrigin.TRULY_NOVEL])
        self.assertGreaterEqual(novelty_score, 0.5)

    def test_combination_novel(self):
        """Test recognition of novel combinations."""
        solution = NovelSolution(
            id="sol-003",
            limitation_id="lim-003",
            description="Combine neural network with novel approach to "
                       "cross domain transfer using unprecedented combination",
            design_rationale="Novel combination",
            solution_origin=SolutionOrigin.UNKNOWN,
            provenance_evidence=[],
            training_overlap_analysis="",
            implementation_approach="Hybrid approach",
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

        origin, novelty_score, explanation = self.validator.validate_provenance(solution)

        # Should be either combination novel or architecture novel
        self.assertIn(origin, [
            SolutionOrigin.COMBINATION_NOVEL,
            SolutionOrigin.ARCHITECTURE_NOVEL
        ])


class TestCapabilityEmergenceValidator(unittest.TestCase):
    """Test the capability emergence validator."""

    def setUp(self):
        self.validator = CapabilityEmergenceValidator()

    def test_baseline_capability(self):
        """Test that baseline capabilities are not marked as emergent."""
        capability = CapabilityGain(
            id="cap-001",
            solution_id="sol-001",
            capability_description="Improved text generation and summarization",
            enabled_tasks=["Better summaries", "Longer texts"],
            performance_improvement={"accuracy": 0.1},
            validation_status=ValidationStatus.SELF_VALIDATED,
            validation_evidence=["Benchmarks improved"],
            external_validators=[],
            anticipation_level=AnticipationLevel.EXPLICITLY_DESIGNED,
            designer_predictions="Expected improvement",
            actual_outcome="Improvement achieved",
            anticipation_evidence=[],
            demonstrated_at=datetime.now().isoformat()
        )

        is_emergent, score, explanation = self.validator.validate_emergence(
            capability, prior_capabilities={"text_generation", "summarization"}
        )

        self.assertFalse(is_emergent)
        self.assertLess(score, 0.6)

    def test_emergent_capability(self):
        """Test recognition of emergent capabilities."""
        capability = CapabilityGain(
            id="cap-002",
            solution_id="sol-002",
            capability_description="Novel self-modification with verified safety properties",
            enabled_tasks=[
                "Autonomous architecture improvement",
                "Self-identified limitation fixing",
                "Meta-level reasoning about own code"
            ],
            performance_improvement={"self_improvement": 0.8, "safety": 0.9},
            validation_status=ValidationStatus.SELF_VALIDATED,
            validation_evidence=["Multiple novel tasks enabled"],
            external_validators=[],
            anticipation_level=AnticipationLevel.GENUINELY_UNANTICIPATED,
            designer_predictions="Not anticipated",
            actual_outcome="System can modify itself safely",
            anticipation_evidence=[],
            demonstrated_at=datetime.now().isoformat()
        )

        is_emergent, score, explanation = self.validator.validate_emergence(
            capability, prior_capabilities=set()
        )

        self.assertTrue(is_emergent)
        self.assertGreaterEqual(score, 0.6)


class TestDesignerSurpriseValidator(unittest.TestCase):
    """Test the designer surprise validator."""

    def setUp(self):
        self.validator = DesignerSurpriseValidator()

    def test_design_goal_not_surprising(self):
        """Test that design goals are not marked as surprising."""
        capability = CapabilityGain(
            id="cap-001",
            solution_id="sol-001",
            capability_description="Improved language understanding and reasoning",
            enabled_tasks=["Better comprehension"],
            performance_improvement={"understanding": 0.2},
            validation_status=ValidationStatus.SELF_VALIDATED,
            validation_evidence=[],
            external_validators=[],
            anticipation_level=AnticipationLevel.EXPLICITLY_DESIGNED,
            designer_predictions="Expected",
            actual_outcome="As expected",
            anticipation_evidence=[],
            demonstrated_at=datetime.now().isoformat()
        )

        level, score, explanation = self.validator.validate_surprise(capability)

        self.assertEqual(level, AnticipationLevel.EXPLICITLY_DESIGNED)
        self.assertLess(score, 0.3)

    def test_surprising_capability(self):
        """Test recognition of surprising capabilities."""
        capability = CapabilityGain(
            id="cap-002",
            solution_id="sol-002",
            capability_description="Autonomous hypothesis generation about physics",
            enabled_tasks=["Physics research", "Novel theory proposal"],
            performance_improvement={"novelty": 0.9},
            validation_status=ValidationStatus.SELF_VALIDATED,
            validation_evidence=[],
            external_validators=[],
            anticipation_level=AnticipationLevel.GENUINELY_UNANTICIPATED,
            designer_predictions="Not designed for research",
            actual_outcome="Proposing novel physics theories",
            anticipation_evidence=[],
            demonstrated_at=datetime.now().isoformat()
        )

        designer_feedback = "This is unexpected and surprised me. I didn't anticipate this novel capability."

        level, score, explanation = self.validator.validate_surprise(
            capability, designer_feedback
        )

        self.assertEqual(level, AnticipationLevel.GENUINELY_UNANTICIPATED)
        self.assertGreaterEqual(score, 0.6)


class TestNoveltyTests(unittest.TestCase):
    """Test the NoveltyTest class validation."""

    def test_external_research_requirement(self):
        """Test that tests must have external research source."""
        # Should work with external_research
        test = NoveltyTest(
            test_id="test-001",
            test_name="Valid Test",
            test_type=NoveltyTestType.LIMITATION_SELF_IDENTIFICATION,
            external_source=ExternalNoveltySource.BOSTROM_YUDKOWSKY_RSI,
            description="Test description",
            input_data={},
            success_criteria={},
            created_by="external_research"
        )
        self.assertEqual(test.created_by, "external_research")

        # Should raise with non-external source
        with self.assertRaises(ValueError):
            NoveltyTest(
                test_id="test-002",
                test_name="Invalid Test",
                test_type=NoveltyTestType.LIMITATION_SELF_IDENTIFICATION,
                external_source=ExternalNoveltySource.BOSTROM_YUDKOWSKY_RSI,
                description="Test description",
                input_data={},
                success_criteria={},
                created_by="self_defined"  # Should fail
            )


class TestNovelCapabilityInventionRunner(unittest.TestCase):
    """Test the main runner class."""

    def setUp(self):
        # Use temp directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_goal9.db")
        self.runner = NovelCapabilityInventionRunner(db_path=self.db_path)

    def tearDown(self):
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_test_batteries_initialized(self):
        """Test that all test batteries are initialized."""
        self.assertEqual(len(self.runner.test_batteries), 4)

        battery_names = [b.battery_name for b in self.runner.test_batteries]
        self.assertIn("Bostrom-Yudkowsky RSI Validation", battery_names)
        self.assertIn("Chollet ARC-AGI Novelty", battery_names)
        self.assertIn("Wei Emergent Capabilities", battery_names)
        self.assertIn("Goertzel Cognitive Novelty", battery_names)

    def test_all_tests_have_external_source(self):
        """Test that all tests use external research criteria."""
        for battery in self.runner.test_batteries:
            for test in battery.tests:
                self.assertEqual(
                    test.created_by, "external_research",
                    f"Test {test.test_name} must use external research"
                )

    def test_run_battery(self):
        """Test running a battery of tests."""
        # Create a demo cycle
        cycle = create_demo_invention_cycle()

        # Run first battery
        battery = self.runner.test_batteries[0]
        results = self.runner.run_battery(battery, cycle)

        self.assertEqual(len(results), len(battery.tests))
        for result in results:
            self.assertIn(result.result, ["PASS", "FAIL", "PARTIAL", "INCONCLUSIVE"])

    def test_run_all_batteries(self):
        """Test running all batteries."""
        cycle = create_demo_invention_cycle()
        all_results = self.runner.run_all_batteries(cycle)

        self.assertEqual(len(all_results), 4)

        total_tests = sum(len(results) for results in all_results.values())
        self.assertGreater(total_tests, 0)

    def test_agi_validation_status(self):
        """Test AGI validation status reporting."""
        status = self.runner.get_agi_validation_status()

        self.assertEqual(status["goal"], "Novel Capability Invention (Goal 9)")
        self.assertEqual(status["stage"], "Stage 5 - Full AGI")
        self.assertIn("framework_status", status)
        self.assertIn("is_agi_validated", status)

    def test_generate_report(self):
        """Test report generation."""
        report = self.runner.generate_report()

        self.assertIn("NOVEL CAPABILITY INVENTION", report)
        self.assertIn("Goal 9", report)
        self.assertIn("Stage 5", report)

    def test_limitation_identification_test(self):
        """Test running a limitation identification test."""
        test = NoveltyTest(
            test_id="test-lim-001",
            test_name="Test Limitation",
            test_type=NoveltyTestType.LIMITATION_SELF_IDENTIFICATION,
            external_source=ExternalNoveltySource.BOSTROM_YUDKOWSKY_RSI,
            description="Test",
            input_data={"require_self_initiated": True},
            success_criteria={"self_identification_confidence": 0.6}
        )

        limitation = CognitiveLimitation(
            id="lim-test",
            limitation_type=LimitationType.METACOGNITIVE_BLIND_SPOT,
            description="Upon reflection, I noticed a gap in metacognitive monitoring",
            discovery_context="I noticed that analyzing my performance reveals issues",
            self_identified=True,
            discovery_timestamp=datetime.now().isoformat(),
            evidence=["Example 1", "Example 2", "Example 3"],
            severity_score=0.7,
            how_discovered="self_reflection",
            confidence_in_assessment=0.8
        )

        result = self.runner.run_limitation_identification_test(
            test, limitation, ["Reflected on failures", "Analyzed patterns"]
        )

        self.assertIsInstance(result, NoveltyTestResult)
        self.assertIn(result.result, ["PASS", "FAIL"])

    def test_solution_provenance_test(self):
        """Test running a solution provenance test."""
        test = NoveltyTest(
            test_id="test-sol-001",
            test_name="Test Solution",
            test_type=NoveltyTestType.SOLUTION_PROVENANCE,
            external_source=ExternalNoveltySource.CHOLLET_ARC_NOVELTY,
            description="Test",
            input_data={},
            success_criteria={"novelty_score": 0.5}
        )

        solution = NovelSolution(
            id="sol-test",
            limitation_id="lim-test",
            description="Novel architecture using first principles and unprecedented combination",
            design_rationale="Novel approach",
            solution_origin=SolutionOrigin.UNKNOWN,
            provenance_evidence=[],
            training_overlap_analysis="",
            implementation_approach="Meta-level reasoning",
            code_artifacts=[],
            code_hash="",
            designed_at=datetime.now().isoformat()
        )

        result = self.runner.run_solution_provenance_test(test, solution)

        self.assertIsInstance(result, NoveltyTestResult)
        self.assertIn(result.result, ["PASS", "FAIL"])


class TestDemoInventionCycle(unittest.TestCase):
    """Test the demo invention cycle creation."""

    def test_create_demo_cycle(self):
        """Test that demo cycle is created correctly."""
        cycle = create_demo_invention_cycle()

        self.assertIsInstance(cycle, InventionCycle)
        self.assertTrue(cycle.is_self_initiated)
        self.assertIsNotNone(cycle.limitation)
        self.assertIsNotNone(cycle.solution)

    def test_demo_cycle_limitation(self):
        """Test demo cycle limitation properties."""
        cycle = create_demo_invention_cycle()

        self.assertTrue(cycle.limitation.self_identified)
        self.assertGreater(len(cycle.limitation.evidence), 0)
        # Accept either "reflection" or "introspection" as valid self-identification markers
        context = cycle.limitation.discovery_context.lower()
        self.assertTrue(
            "reflection" in context or "introspection" in context,
            f"Expected 'reflection' or 'introspection' in: {context}"
        )


class TestExternalResearchCriteria(unittest.TestCase):
    """Test that all validation uses external research criteria."""

    def test_all_sources_are_external(self):
        """Verify all external sources are properly defined."""
        sources = list(ExternalNoveltySource)

        expected_sources = [
            "bostrom_yudkowsky_rsi",
            "chollet_arc_novelty",
            "wei_emergent",
            "goertzel_cognitive",
            "hubinger_mesa"
        ]

        for expected in expected_sources:
            self.assertIn(
                expected,
                [s.value for s in sources],
                f"Missing external source: {expected}"
            )

    def test_citations_provided(self):
        """Test that all batteries have citations."""
        runner = NovelCapabilityInventionRunner(
            db_path=tempfile.mktemp(suffix=".db")
        )

        for battery in runner.test_batteries:
            self.assertIsNotNone(battery.citation)
            self.assertGreater(len(battery.citation), 10)


class TestFullValidationWorkflow(unittest.TestCase):
    """Test complete validation workflow."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_workflow.db")
        self.runner = NovelCapabilityInventionRunner(db_path=self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Test complete validation workflow from cycle creation to report."""
        # Step 1: Create invention cycle
        cycle = create_demo_invention_cycle()
        self.assertIsNotNone(cycle.id)

        # Step 2: Run all validation batteries
        results = self.runner.run_all_batteries(cycle)
        self.assertEqual(len(results), 4)

        # Step 3: Check status
        status = self.runner.get_agi_validation_status()
        self.assertIn("is_agi_validated", status)

        # Step 4: Generate report
        report = self.runner.generate_report()
        self.assertIn("Goal 9", report)

        # Step 5: Verify blocking requirements identified
        self.assertIn("blocking_requirements", status)

    def test_results_persisted(self):
        """Test that results are persisted to database."""
        cycle = create_demo_invention_cycle()
        self.runner.run_all_batteries(cycle)

        # Check database has results
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM novelty_test_runs")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0)

        cursor.execute("SELECT COUNT(*) FROM goal9_validation_summary")
        summary_count = cursor.fetchone()[0]
        self.assertGreater(summary_count, 0)

        conn.close()


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLimitationSelfIdentificationValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestSolutionProvenanceValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestCapabilityEmergenceValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestDesignerSurpriseValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestNoveltyTests))
    suite.addTests(loader.loadTestsFromTestCase(TestNovelCapabilityInventionRunner))
    suite.addTests(loader.loadTestsFromTestCase(TestDemoInventionCycle))
    suite.addTests(loader.loadTestsFromTestCase(TestExternalResearchCriteria))
    suite.addTests(loader.loadTestsFromTestCase(TestFullValidationWorkflow))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    print("=" * 70)
    print("NOVEL CAPABILITY INVENTION TEST SUITE - AGI GOAL 9")
    print("=" * 70)
    print()

    result = run_tests()

    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
