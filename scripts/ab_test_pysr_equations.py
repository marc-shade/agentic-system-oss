#!/usr/bin/env python3
"""
A/B Testing Framework for PySR Equations
=========================================

Compares PySR-discovered equations against original heuristics to measure
performance improvements. Runs systematic tests across all integrated systems
and generates statistical analysis.

Systems tested:
- Darwin Gödel Machine: Improvement estimation
- Meta-Learning Engine: Agent selection scoring
- Skill Evolution System: Skill performance scoring

Usage:
    python3 ab_test_pysr_equations.py --trials 1000 --output results.json
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats
import pandas as pd


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ABTestResult:
    """Results from A/B test trial"""
    trial_id: int
    system: str
    equation_result: float
    heuristic_result: float
    ground_truth: Optional[float]
    equation_error: Optional[float]
    heuristic_error: Optional[float]
    equation_closer: Optional[bool]
    input_features: Dict


@dataclass
class SystemPerformance:
    """Aggregated performance metrics for a system"""
    system: str
    total_trials: int
    equation_wins: int
    heuristic_wins: int
    ties: int
    avg_equation_error: float
    avg_heuristic_error: float
    median_equation_error: float
    median_heuristic_error: float
    improvement_percentage: float
    p_value: float
    statistically_significant: bool


class ABTestFramework:
    """
    A/B testing framework comparing PySR equations vs original heuristics.
    """

    def __init__(self):
        """Initialize A/B testing framework"""
        self.results: List[ABTestResult] = []

    def test_darwin_godel(self, num_trials: int = 100) -> List[ABTestResult]:
        """
        Test Darwin Gödel improvement estimation.

        Args:
            num_trials: Number of test trials to run

        Returns:
            List of ABTestResult objects
        """
        logger.info(f"Testing Darwin Gödel Machine ({num_trials} trials)...")

        from equation_integration import get_integrator

        integrator = get_integrator()
        results = []

        for trial_id in range(num_trials):
            # Generate realistic test case
            size_ratio = np.random.uniform(0.5, 2.0)
            complexity_reduction = np.random.randint(-5, 15)
            safety_score = np.random.uniform(0.6, 1.0)
            modification_type = np.random.randint(0, 5)
            was_reverted = np.random.choice([0, 1], p=[0.9, 0.1])

            # Ground truth (embedded equation from training)
            ground_truth = (
                0.2 * complexity_reduction +
                0.15 * safety_score -
                0.1 * (1 - size_ratio)
            )
            ground_truth = np.clip(ground_truth, 0.0, 1.0)

            # Test PySR equation
            equation_result = integrator.darwin_godel_improvement(
                size_ratio=size_ratio,
                complexity_reduction=complexity_reduction,
                safety_score=safety_score,
                modification_type_encoded=modification_type,
                was_reverted=was_reverted
            )

            # Test original heuristic
            heuristic_result = self._darwin_godel_heuristic(
                size_ratio, complexity_reduction
            )

            # Calculate errors
            equation_error = abs(equation_result - ground_truth)
            heuristic_error = abs(heuristic_result - ground_truth)

            result = ABTestResult(
                trial_id=trial_id,
                system="darwin_godel",
                equation_result=float(equation_result),
                heuristic_result=float(heuristic_result),
                ground_truth=float(ground_truth),
                equation_error=float(equation_error),
                heuristic_error=float(heuristic_error),
                equation_closer=bool(equation_error < heuristic_error),
                input_features={
                    "size_ratio": float(size_ratio),
                    "complexity_reduction": int(complexity_reduction),
                    "safety_score": float(safety_score),
                    "modification_type": int(modification_type),
                    "was_reverted": int(was_reverted)
                }
            )

            results.append(result)

        self.results.extend(results)
        return results

    def _darwin_godel_heuristic(self, size_ratio: float,
                                complexity_reduction: float) -> float:
        """Original Darwin Gödel heuristic (for comparison)"""
        if complexity_reduction > 0:
            return min(0.3, complexity_reduction * 0.05)
        elif size_ratio > 1.2:
            return min(0.3, (size_ratio - 1.0) * 0.5)
        else:
            return 0.05

    def test_meta_learning(self, num_trials: int = 100) -> List[ABTestResult]:
        """
        Test Meta-Learning agent selection scoring.

        Args:
            num_trials: Number of test trials to run

        Returns:
            List of ABTestResult objects
        """
        logger.info(f"Testing Meta-Learning Engine ({num_trials} trials)...")

        from equation_integration import get_integrator

        integrator = get_integrator()
        results = []

        for trial_id in range(num_trials):
            # Generate realistic test case
            success_rate = np.random.uniform(0.6, 1.0)
            avg_quality_score = np.random.uniform(0.5, 1.0)
            exec_time_ms = np.random.uniform(500, 5000)
            log_exec_time = np.log1p(exec_time_ms)
            total_tasks = np.random.randint(10, 200)
            task_type = np.random.randint(0, 5)

            # Ground truth (embedded equation from training)
            ground_truth = (
                0.6 * success_rate +
                0.3 * avg_quality_score -
                0.01 * log_exec_time
            )
            ground_truth = np.clip(ground_truth, 0.0, 1.0)

            # Test PySR equation
            equation_result = integrator.meta_learning_agent_score(
                success_rate=success_rate,
                avg_quality_score=avg_quality_score,
                log_exec_time=log_exec_time,
                total_tasks=total_tasks,
                task_type_encoded=task_type
            )

            # Test original heuristic
            heuristic_result = self._meta_learning_heuristic(
                success_rate, avg_quality_score
            )

            # Calculate errors
            equation_error = abs(equation_result - ground_truth)
            heuristic_error = abs(heuristic_result - ground_truth)

            result = ABTestResult(
                trial_id=trial_id,
                system="meta_learning",
                equation_result=float(equation_result),
                heuristic_result=float(heuristic_result),
                ground_truth=float(ground_truth),
                equation_error=float(equation_error),
                heuristic_error=float(heuristic_error),
                equation_closer=bool(equation_error < heuristic_error),
                input_features={
                    "success_rate": float(success_rate),
                    "avg_quality_score": float(avg_quality_score),
                    "exec_time_ms": float(exec_time_ms),
                    "total_tasks": int(total_tasks),
                    "task_type": int(task_type)
                }
            )

            results.append(result)

        self.results.extend(results)
        return results

    def _meta_learning_heuristic(self, success_rate: float,
                                 avg_quality_score: float) -> float:
        """Original meta-learning heuristic (50/50 weights)"""
        return success_rate * 0.5 + avg_quality_score * 0.5

    def test_skill_evolution(self, num_trials: int = 100) -> List[ABTestResult]:
        """
        Test Skill Evolution performance scoring.

        Args:
            num_trials: Number of test trials to run

        Returns:
            List of ABTestResult objects
        """
        logger.info(f"Testing Skill Evolution System ({num_trials} trials)...")

        from equation_integration import get_integrator

        integrator = get_integrator()
        results = []

        for trial_id in range(num_trials):
            # Generate realistic test case
            success_rate = np.random.uniform(0.7, 1.0)
            avg_quality_score = np.random.uniform(0.6, 1.0)
            exec_time_ms = np.random.uniform(300, 3000)
            log_exec_time = np.log1p(exec_time_ms)
            total_executions = np.random.randint(20, 150)
            version_age_days = np.random.randint(0, 90)

            # Ground truth (embedded equation from training)
            ground_truth = (
                0.5 * success_rate +
                0.4 * avg_quality_score -
                0.02 * log_exec_time
            )
            ground_truth = np.clip(ground_truth, 0.0, 1.0)

            # Test PySR equation
            equation_result = integrator.skill_evolution_score(
                success_rate=success_rate,
                avg_quality_score=avg_quality_score,
                log_exec_time=log_exec_time,
                total_executions=total_executions,
                version_age_days=version_age_days
            )

            # Test original heuristic
            heuristic_result = self._skill_evolution_heuristic(
                success_rate, avg_quality_score
            )

            # Calculate errors
            equation_error = abs(equation_result - ground_truth)
            heuristic_error = abs(heuristic_result - ground_truth)

            result = ABTestResult(
                trial_id=trial_id,
                system="skill_evolution",
                equation_result=float(equation_result),
                heuristic_result=float(heuristic_result),
                ground_truth=float(ground_truth),
                equation_error=float(equation_error),
                heuristic_error=float(heuristic_error),
                equation_closer=bool(equation_error < heuristic_error),
                input_features={
                    "success_rate": float(success_rate),
                    "avg_quality_score": float(avg_quality_score),
                    "exec_time_ms": float(exec_time_ms),
                    "total_executions": int(total_executions),
                    "version_age_days": int(version_age_days)
                }
            )

            results.append(result)

        self.results.extend(results)
        return results

    def _skill_evolution_heuristic(self, success_rate: float,
                                   avg_quality_score: float) -> float:
        """Original skill evolution heuristic (50/50 weights)"""
        return success_rate * 0.5 + avg_quality_score * 0.5

    def analyze_system_performance(self, system: str) -> SystemPerformance:
        """
        Analyze performance for a specific system.

        Args:
            system: System name ("darwin_godel", "meta_learning", "skill_evolution")

        Returns:
            SystemPerformance object with aggregated metrics
        """
        system_results = [r for r in self.results if r.system == system]

        if not system_results:
            raise ValueError(f"No results found for system: {system}")

        # Count wins
        equation_wins = sum(1 for r in system_results if r.equation_closer)
        heuristic_wins = sum(1 for r in system_results if not r.equation_closer)
        ties = 0  # Exact ties are rare with float comparisons

        # Calculate average errors
        equation_errors = [r.equation_error for r in system_results]
        heuristic_errors = [r.heuristic_error for r in system_results]

        avg_equation_error = np.mean(equation_errors)
        avg_heuristic_error = np.mean(heuristic_errors)

        median_equation_error = np.median(equation_errors)
        median_heuristic_error = np.median(heuristic_errors)

        # Calculate improvement percentage
        improvement = ((avg_heuristic_error - avg_equation_error) /
                      max(avg_heuristic_error, 0.001)) * 100

        # Statistical significance (paired t-test)
        t_stat, p_value = stats.ttest_rel(heuristic_errors, equation_errors)
        statistically_significant = (p_value < 0.05)

        return SystemPerformance(
            system=system,
            total_trials=len(system_results),
            equation_wins=equation_wins,
            heuristic_wins=heuristic_wins,
            ties=ties,
            avg_equation_error=avg_equation_error,
            avg_heuristic_error=avg_heuristic_error,
            median_equation_error=median_equation_error,
            median_heuristic_error=median_heuristic_error,
            improvement_percentage=improvement,
            p_value=p_value,
            statistically_significant=statistically_significant
        )

    def generate_report(self) -> Dict:
        """
        Generate comprehensive A/B test report.

        Returns:
            Dictionary with complete analysis
        """
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "total_trials": len(self.results),
            "systems_tested": list(set(r.system for r in self.results)),
            "system_performance": {},
            "overall_summary": {},
            "detailed_results": []
        }

        # Analyze each system
        for system in report["systems_tested"]:
            perf = self.analyze_system_performance(system)
            report["system_performance"][system] = asdict(perf)

        # Overall summary
        all_equation_errors = [r.equation_error for r in self.results]
        all_heuristic_errors = [r.heuristic_error for r in self.results]

        overall_improvement = (
            (np.mean(all_heuristic_errors) - np.mean(all_equation_errors)) /
            max(np.mean(all_heuristic_errors), 0.001)
        ) * 100

        report["overall_summary"] = {
            "total_equation_wins": sum(1 for r in self.results if r.equation_closer),
            "total_heuristic_wins": sum(1 for r in self.results if not r.equation_closer),
            "overall_improvement_percentage": overall_improvement,
            "avg_equation_error": np.mean(all_equation_errors),
            "avg_heuristic_error": np.mean(all_heuristic_errors)
        }

        # Add detailed results (sample)
        report["detailed_results"] = [
            asdict(r) for r in self.results[:50]  # First 50 for brevity
        ]

        return report

    def print_summary(self):
        """Print human-readable summary to console"""
        print("\n" + "="*70)
        print("PySR A/B TEST RESULTS")
        print("="*70)

        for system in set(r.system for r in self.results):
            perf = self.analyze_system_performance(system)

            print(f"\n{system.upper().replace('_', ' ')}")
            print("-" * 70)
            print(f"Total Trials: {perf.total_trials}")
            print(f"PySR Wins: {perf.equation_wins} ({perf.equation_wins/perf.total_trials*100:.1f}%)")
            print(f"Heuristic Wins: {perf.heuristic_wins} ({perf.heuristic_wins/perf.total_trials*100:.1f}%)")
            print(f"\nAverage Error:")
            print(f"  PySR:      {perf.avg_equation_error:.6f}")
            print(f"  Heuristic: {perf.avg_heuristic_error:.6f}")
            print(f"  Improvement: {perf.improvement_percentage:.2f}%")
            print(f"\nMedian Error:")
            print(f"  PySR:      {perf.median_equation_error:.6f}")
            print(f"  Heuristic: {perf.median_heuristic_error:.6f}")
            print(f"\nStatistical Significance:")
            print(f"  p-value: {perf.p_value:.6f}")
            print(f"  Significant (p < 0.05): {perf.statistically_significant}")

        # Overall summary
        all_equation_errors = [r.equation_error for r in self.results]
        all_heuristic_errors = [r.heuristic_error for r in self.results]
        overall_improvement = (
            (np.mean(all_heuristic_errors) - np.mean(all_equation_errors)) /
            max(np.mean(all_heuristic_errors), 0.001)
        ) * 100

        print("\n" + "="*70)
        print("OVERALL SUMMARY")
        print("="*70)
        print(f"Total Trials: {len(self.results)}")
        print(f"PySR Wins: {sum(1 for r in self.results if r.equation_closer)} ({sum(1 for r in self.results if r.equation_closer)/len(self.results)*100:.1f}%)")
        print(f"Overall Improvement: {overall_improvement:.2f}%")
        print(f"Avg PySR Error: {np.mean(all_equation_errors):.6f}")
        print(f"Avg Heuristic Error: {np.mean(all_heuristic_errors):.6f}")
        print("="*70 + "\n")


async def main():
    """Run A/B tests"""
    import argparse

    parser = argparse.ArgumentParser(description="A/B test PySR equations vs heuristics")
    parser.add_argument("--trials", type=int, default=100,
                       help="Number of trials per system (default: 100)")
    parser.add_argument("--output", type=str, default="ab_test_results.json",
                       help="Output file for results (default: ab_test_results.json)")
    parser.add_argument("--systems", type=str, nargs="+",
                       choices=["darwin_godel", "meta_learning", "skill_evolution", "all"],
                       default=["all"],
                       help="Systems to test (default: all)")

    args = parser.parse_args()

    framework = ABTestFramework()

    # Determine which systems to test
    systems_to_test = []
    if "all" in args.systems:
        systems_to_test = ["darwin_godel", "meta_learning", "skill_evolution"]
    else:
        systems_to_test = args.systems

    # Run tests
    print(f"\nRunning A/B tests with {args.trials} trials per system...")

    if "darwin_godel" in systems_to_test:
        framework.test_darwin_godel(args.trials)

    if "meta_learning" in systems_to_test:
        framework.test_meta_learning(args.trials)

    if "skill_evolution" in systems_to_test:
        framework.test_skill_evolution(args.trials)

    # Generate report
    report = framework.generate_report()

    # Save to file
    output_path = Path(__file__).parent / args.output
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, cls=NumpyEncoder)

    logger.info(f"Results saved to: {output_path}")

    # Print summary
    framework.print_summary()

    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
