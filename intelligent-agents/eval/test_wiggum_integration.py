#!/usr/bin/env python3
"""
Test Suite for Wiggum Evaluation Integration

Tests the Wiggum loop integration with self-* feature evaluations:
- Self-improvement with guaranteed completion
- Self-healing with iteration tracking
- Self-optimization with learning capture
- Darwin-Gödel integration for verified improvements
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from datetime import datetime
from typing import Tuple, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wiggum_eval_integration import (
    WiggumEvalIntegration,
    WiggumEvalResult,
    WiggumEvalCriteria,
    WiggumOutcome,
    WiggumIteration,
    WiggumDarwinGodelIntegration
)


class TestWiggumEvalIntegration(unittest.TestCase):
    """Test cases for WiggumEvalIntegration"""

    def setUp(self):
        """Set up test fixtures"""
        self.evaluator = WiggumEvalIntegration()

    def test_init(self):
        """Test initialization creates database and criteria"""
        self.assertTrue(self.evaluator.db_path.exists())
        self.assertIn('self_improvement', self.evaluator.criteria)
        self.assertIn('self_healing', self.evaluator.criteria)
        self.assertIn('self_optimization', self.evaluator.criteria)
        self.assertIn('skill_evolution', self.evaluator.criteria)

    def test_criteria_evaluation_success(self):
        """Test criteria evaluation for successful completion"""
        result = WiggumEvalResult(
            eval_id="test1",
            task="Test task",
            success_criteria="Complete test",
            outcome=WiggumOutcome.SUCCESS,
            total_iterations=3,
            max_iterations=10,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            total_duration_ms=100,
            iterations=[],
            ember_approved=True,
            quality_score=0.9,
            learnings_stored=3,
            key_insights=["insight1", "insight2"]
        )

        criteria = self.evaluator.criteria['self_improvement']
        eval_scores = criteria.evaluate(result)

        self.assertTrue(eval_scores['passed'])
        self.assertGreater(eval_scores['total_score'], 0.7)
        self.assertEqual(eval_scores['component_scores']['completion'], 1.0)

    def test_criteria_evaluation_failure(self):
        """Test criteria evaluation for max iterations reached"""
        result = WiggumEvalResult(
            eval_id="test2",
            task="Test task",
            success_criteria="Complete test",
            outcome=WiggumOutcome.MAX_ITERATIONS,
            total_iterations=10,
            max_iterations=10,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            total_duration_ms=1000,
            iterations=[],
            ember_approved=False,
            quality_score=0.3,
            learnings_stored=10,
            key_insights=[]
        )

        criteria = self.evaluator.criteria['self_improvement']
        eval_scores = criteria.evaluate(result)

        self.assertFalse(eval_scores['passed'])
        self.assertEqual(eval_scores['component_scores']['completion'], 0.5)

    def test_criteria_evaluation_quality_failure(self):
        """Test criteria evaluation when Ember rejects quality"""
        result = WiggumEvalResult(
            eval_id="test3",
            task="Test task with TODO markers",
            success_criteria="Complete without placeholders",
            outcome=WiggumOutcome.QUALITY_FAILURE,
            total_iterations=2,
            max_iterations=10,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            total_duration_ms=50,
            iterations=[],
            ember_approved=False,
            quality_score=0.3,
            learnings_stored=2,
            key_insights=["Quality issues detected"]
        )

        criteria = self.evaluator.criteria['self_improvement']
        eval_scores = criteria.evaluate(result)

        # Should fail because Ember didn't approve
        self.assertFalse(eval_scores['passed'])


class TestWiggumEvalAsync(unittest.IsolatedAsyncioTestCase):
    """Async test cases for Wiggum evaluation"""

    def setUp(self):
        self.evaluator = WiggumEvalIntegration()

    async def test_evaluate_immediate_success(self):
        """Test evaluation with immediate success"""
        async def immediate_success(iteration: int) -> Tuple[bool, str, str]:
            return True, "Success on first try", "Immediate completion"

        result = await self.evaluator.evaluate_with_wiggum(
            task="Immediate success test",
            success_criteria="Complete immediately",
            task_executor=immediate_success,
            max_iterations=5,
            criteria_name='self_healing'
        )

        self.assertEqual(result.outcome, WiggumOutcome.SUCCESS)
        self.assertEqual(result.total_iterations, 1)
        self.assertTrue(result.ember_approved)

    async def test_evaluate_gradual_success(self):
        """Test evaluation with success after multiple attempts"""
        async def gradual_success(iteration: int) -> Tuple[bool, str, str]:
            if iteration >= 4:
                return True, "Success after 4 attempts", f"Converged on iteration {iteration}"
            return False, None, f"Iteration {iteration} exploring"

        result = await self.evaluator.evaluate_with_wiggum(
            task="Gradual success test",
            success_criteria="Converge after exploration",
            task_executor=gradual_success,
            max_iterations=10,
            criteria_name='self_optimization'
        )

        self.assertEqual(result.outcome, WiggumOutcome.SUCCESS)
        self.assertEqual(result.total_iterations, 4)
        self.assertEqual(len(result.iterations), 4)
        self.assertGreater(len(result.key_insights), 0)

    async def test_evaluate_max_iterations(self):
        """Test evaluation hitting max iterations"""
        async def always_fail(iteration: int) -> Tuple[bool, str, str]:
            return False, None, f"Failure {iteration}"

        result = await self.evaluator.evaluate_with_wiggum(
            task="Always fail test",
            success_criteria="Never achievable",
            task_executor=always_fail,
            max_iterations=3,
            criteria_name='self_healing'
        )

        self.assertEqual(result.outcome, WiggumOutcome.MAX_ITERATIONS)
        self.assertEqual(result.total_iterations, 3)

    async def test_evaluate_quality_rejection(self):
        """Test evaluation rejected by Ember quality check"""
        async def returns_todo(iteration: int) -> Tuple[bool, str, str]:
            return True, "This has TODO markers", "Returned incomplete code"

        result = await self.evaluator.evaluate_with_wiggum(
            task="Quality rejection test",
            success_criteria="Return quality code",
            task_executor=returns_todo,
            max_iterations=5,
            criteria_name='self_improvement'
        )

        self.assertEqual(result.outcome, WiggumOutcome.QUALITY_FAILURE)
        self.assertFalse(result.ember_approved)

    async def test_learning_storage(self):
        """Test that learnings are stored in each iteration"""
        async def with_insights(iteration: int) -> Tuple[bool, str, str]:
            if iteration >= 2:
                return True, "Done", f"Insight {iteration}: learned something"
            return False, None, f"Insight {iteration}: still learning"

        result = await self.evaluator.evaluate_with_wiggum(
            task="Learning storage test",
            success_criteria="Learn and complete",
            task_executor=with_insights,
            max_iterations=5,
            criteria_name='skill_evolution'
        )

        self.assertGreater(result.learnings_stored, 0)
        self.assertGreater(len(result.key_insights), 0)

        # Check insights were captured
        insights_dir = Path.home() / ".claude" / "wiggum-learnings"
        learning_files = list(insights_dir.glob(f"wiggum-eval-{result.eval_id}*.json"))
        self.assertGreater(len(learning_files), 0)


class TestWiggumEvalCriteria(unittest.TestCase):
    """Test cases for evaluation criteria"""

    def test_self_improvement_criteria(self):
        """Test self-improvement criteria thresholds"""
        criteria = WiggumEvalCriteria(
            name='test_improvement',
            description='Test criteria',
            max_acceptable_iterations=10,
            min_quality_score=0.8,
            require_ember_approval=True,
            require_learning_capture=True
        )

        # Perfect result
        perfect = WiggumEvalResult(
            eval_id="perfect",
            task="Perfect task",
            success_criteria="Perfect",
            outcome=WiggumOutcome.SUCCESS,
            total_iterations=2,
            max_iterations=10,
            start_time="",
            end_time="",
            total_duration_ms=10,
            iterations=[],
            ember_approved=True,
            quality_score=0.95,
            learnings_stored=5,
            key_insights=[]
        )

        scores = criteria.evaluate(perfect)
        self.assertTrue(scores['passed'])
        self.assertGreater(scores['total_score'], 0.9)

    def test_efficiency_scoring(self):
        """Test that fewer iterations = better efficiency score"""
        criteria = WiggumEvalCriteria(
            name='efficiency_test',
            description='Test efficiency',
            max_acceptable_iterations=5
        )

        def make_result(iterations: int) -> WiggumEvalResult:
            return WiggumEvalResult(
                eval_id=f"eff{iterations}",
                task="Efficiency test",
                success_criteria="Complete",
                outcome=WiggumOutcome.SUCCESS,
                total_iterations=iterations,
                max_iterations=10,
                start_time="",
                end_time="",
                total_duration_ms=10,
                iterations=[],
                ember_approved=True,
                quality_score=0.9,
                learnings_stored=3,
                key_insights=[]
            )

        # 1 iteration should have better efficiency than 5
        result_1 = criteria.evaluate(make_result(1))
        result_5 = criteria.evaluate(make_result(5))
        result_10 = criteria.evaluate(make_result(10))

        self.assertGreater(
            result_1['component_scores']['efficiency'],
            result_5['component_scores']['efficiency']
        )
        self.assertGreater(
            result_5['component_scores']['efficiency'],
            result_10['component_scores']['efficiency']
        )


class TestWiggumStatistics(unittest.IsolatedAsyncioTestCase):
    """Test statistics and history tracking"""

    def setUp(self):
        self.evaluator = WiggumEvalIntegration()

    async def test_get_statistics(self):
        """Test retrieval of evaluation statistics"""
        # Run a test first to ensure data exists
        async def quick_success(iteration: int) -> Tuple[bool, str, str]:
            return True, "Quick", "Instant"

        await self.evaluator.evaluate_with_wiggum(
            task="Stats test",
            success_criteria="Quick complete",
            task_executor=quick_success,
            max_iterations=3
        )

        stats = self.evaluator.get_eval_statistics()
        self.assertIn('total_evals', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('avg_iterations', stats)
        self.assertGreater(stats['total_evals'], 0)

    async def test_get_history(self):
        """Test retrieval of evaluation history"""
        history = self.evaluator.get_eval_history(limit=5)
        self.assertIsInstance(history, list)


class TestWiggumDarwinGodelIntegration(unittest.TestCase):
    """Test Darwin-Gödel integration"""

    def test_init(self):
        """Test integration initialization"""
        integration = WiggumDarwinGodelIntegration()
        self.assertIsNotNone(integration.wiggum_eval)


def run_tests():
    """Run all tests with verbose output"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWiggumEvalIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestWiggumEvalAsync))
    suite.addTests(loader.loadTestsFromTestCase(TestWiggumEvalCriteria))
    suite.addTests(loader.loadTestsFromTestCase(TestWiggumStatistics))
    suite.addTests(loader.loadTestsFromTestCase(TestWiggumDarwinGodelIntegration))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
