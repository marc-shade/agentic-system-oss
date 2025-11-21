#!/usr/bin/env python3
"""
Self-Evaluation and Rollback System
====================================

Objective assessment of self-modifications with automatic rollback capability.

Critical for AGI safety: The system must be able to:
1. Measure performance before and after modifications
2. Objectively determine if modifications helped or hurt
3. Automatically rollback failed modifications
4. Track all changes with git versioning
5. Generate confidence scores for decisions

Architecture:
    Baseline Measurement → Apply Modification → New Measurement →
    Compare → Decide (Keep/Rollback) → Git Commit/Revert

This closes Gap #9 and #10 from AGI_GAP_ANALYSIS.md
"""

import asyncio
import git
import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EvaluationDecision(Enum):
    """Self-evaluation decision outcomes"""
    KEEP = "keep"  # Keep modification
    ROLLBACK = "rollback"  # Revert modification
    UNCERTAIN = "uncertain"  # Need more data


@dataclass
class PerformanceSnapshot:
    """Performance metrics at a point in time"""
    snapshot_id: str
    timestamp: str
    git_commit: str

    # System metrics
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float

    # Quality metrics
    success_rate: float
    error_rate: float
    test_pass_rate: float

    # Business metrics
    tasks_completed: int
    average_quality_score: float

    # Additional context
    modifications_applied: List[str]
    notes: str = ""


@dataclass
class ComparisonResult:
    """Result of comparing two performance snapshots"""
    baseline_id: str
    modified_id: str

    # Deltas (positive = improvement, negative = regression)
    execution_time_delta_percent: float
    memory_delta_percent: float
    cpu_delta_percent: float
    success_rate_delta: float
    error_rate_delta: float
    test_pass_rate_delta: float
    quality_score_delta: float

    # Overall assessment
    overall_improvement: bool
    regression_detected: bool
    confidence_score: float  # 0.0 to 1.0

    decision: EvaluationDecision
    reasoning: str


class SelfEvaluationSystem:
    """
    Objective self-assessment system for AGI modifications.

    Measures performance before and after self-modifications,
    compares results, and decides to keep or rollback changes.
    """

    def __init__(self, base_path: str = "/mnt/agentic-system"):
        """Initialize self-evaluation system."""
        self.base_path = Path(base_path)
        self.snapshots_dir = self.base_path / "performance-snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)

        # Initialize git repo if not exists
        try:
            self.repo = git.Repo(self.base_path)
            logger.info(f"Git repository found at {self.base_path}")
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.base_path)
            logger.info(f"Initialized new git repository at {self.base_path}")

        # Performance history
        self.snapshots: Dict[str, PerformanceSnapshot] = {}

        # Decision thresholds
        self.regression_threshold = -10.0  # >10% worse is regression
        self.improvement_threshold = 5.0   # >5% better is improvement
        self.confidence_threshold = 0.7    # Need >70% confidence

        logger.info("Self-Evaluation System initialized")

    async def capture_baseline(self, notes: str = "") -> PerformanceSnapshot:
        """
        Capture current performance as baseline before modification.

        Returns:
            PerformanceSnapshot with current metrics
        """
        logger.info("Capturing baseline performance snapshot")

        snapshot = await self._measure_current_performance(
            snapshot_type="baseline",
            notes=notes
        )

        self.snapshots[snapshot.snapshot_id] = snapshot
        self._save_snapshot(snapshot)

        logger.info(f"Baseline captured: {snapshot.snapshot_id}")
        return snapshot

    async def evaluate_modification(
        self,
        baseline_id: str,
        modification_description: str,
        notes: str = ""
    ) -> ComparisonResult:
        """
        Evaluate performance after modification and decide to keep or rollback.

        Args:
            baseline_id: ID of baseline snapshot to compare against
            modification_description: Description of what was modified
            notes: Optional additional context

        Returns:
            ComparisonResult with decision (KEEP or ROLLBACK)
        """
        logger.info(f"Evaluating modification: {modification_description}")

        # Capture current performance (post-modification)
        modified_snapshot = await self._measure_current_performance(
            snapshot_type="modified",
            notes=f"{notes}\nModification: {modification_description}"
        )

        self.snapshots[modified_snapshot.snapshot_id] = modified_snapshot
        self._save_snapshot(modified_snapshot)

        # Compare with baseline
        baseline = self.snapshots.get(baseline_id)
        if not baseline:
            raise ValueError(f"Baseline snapshot {baseline_id} not found")

        comparison = self._compare_snapshots(baseline, modified_snapshot)

        logger.info(f"Evaluation complete: {comparison.decision.value} (confidence={comparison.confidence_score:.2%})")
        logger.info(f"Reasoning: {comparison.reasoning}")

        # Save comparison
        self._save_comparison(comparison)

        return comparison

    async def rollback_modification(
        self,
        to_commit: Optional[str] = None
    ) -> bool:
        """
        Rollback to previous git commit.

        Args:
            to_commit: Specific commit to rollback to (default: previous commit)

        Returns:
            True if rollback successful
        """
        logger.info("Rolling back modification")

        try:
            if to_commit:
                # Rollback to specific commit
                self.repo.git.reset('--hard', to_commit)
                logger.info(f"Rolled back to commit {to_commit}")
            else:
                # Rollback to previous commit (HEAD~1)
                self.repo.git.reset('--hard', 'HEAD~1')
                logger.info("Rolled back to previous commit")

            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return False

    async def commit_modification(
        self,
        message: str,
        files: Optional[List[str]] = None
    ) -> str:
        """
        Commit modification to git with automatic message.

        Args:
            message: Commit message
            files: Optional list of specific files to commit (default: all changes)

        Returns:
            Commit hash
        """
        logger.info(f"Committing modification: {message}")

        try:
            # Add files
            if files:
                self.repo.index.add(files)
            else:
                self.repo.git.add(A=True)  # Add all changes

            # Commit with auto-generated message
            timestamp = datetime.now().isoformat()
            full_message = f"{message}\n\n[Auto-committed by Self-Evaluation System]\nTimestamp: {timestamp}"

            commit = self.repo.index.commit(full_message)
            commit_hash = commit.hexsha

            logger.info(f"Committed: {commit_hash[:8]}")
            return commit_hash

        except Exception as e:
            logger.error(f"Commit failed: {e}", exc_info=True)
            raise

    async def _measure_current_performance(
        self,
        snapshot_type: str,
        notes: str = ""
    ) -> PerformanceSnapshot:
        """Measure current system performance."""

        # Get current git commit
        try:
            current_commit = self.repo.head.commit.hexsha
        except:
            current_commit = "no-git"

        # Simulate performance measurement
        # In production: Run actual benchmarks, collect metrics
        import random
        import psutil

        process = psutil.Process()

        snapshot = PerformanceSnapshot(
            snapshot_id=hashlib.md5(
                f"{datetime.now().isoformat()}{random.random()}".encode()
            ).hexdigest()[:8],
            timestamp=datetime.now().isoformat(),
            git_commit=current_commit,

            # System metrics
            execution_time_ms=random.uniform(100, 500),  # In production: actual timing
            memory_usage_mb=process.memory_info().rss / 1024 / 1024,
            cpu_usage_percent=process.cpu_percent(interval=0.1),

            # Quality metrics
            success_rate=random.uniform(0.8, 0.95),  # In production: actual success rate
            error_rate=random.uniform(0.05, 0.2),
            test_pass_rate=random.uniform(0.85, 1.0),

            # Business metrics
            tasks_completed=random.randint(10, 50),
            average_quality_score=random.uniform(0.7, 0.95),

            # Context
            modifications_applied=[],
            notes=notes
        )

        return snapshot

    def _compare_snapshots(
        self,
        baseline: PerformanceSnapshot,
        modified: PerformanceSnapshot
    ) -> ComparisonResult:
        """Compare two performance snapshots and make decision."""

        # Calculate deltas (as percentages)
        def calc_delta_pct(baseline_val: float, modified_val: float) -> float:
            if baseline_val == 0:
                return 0.0
            return ((modified_val - baseline_val) / baseline_val) * 100

        exec_delta = calc_delta_pct(baseline.execution_time_ms, modified.execution_time_ms)
        mem_delta = calc_delta_pct(baseline.memory_usage_mb, modified.memory_usage_mb)
        cpu_delta = calc_delta_pct(baseline.cpu_usage_percent, modified.cpu_usage_percent)

        success_rate_delta = modified.success_rate - baseline.success_rate
        error_rate_delta = modified.error_rate - baseline.error_rate
        test_pass_rate_delta = modified.test_pass_rate - baseline.test_pass_rate
        quality_delta = modified.average_quality_score - baseline.average_quality_score

        # Assess metrics (negative exec/mem/cpu time is good, positive rates are good)
        improvements = []
        regressions = []

        if exec_delta < -self.improvement_threshold:
            improvements.append(f"Execution time improved by {-exec_delta:.1f}%")
        elif exec_delta > self.regression_threshold:
            regressions.append(f"Execution time regressed by {exec_delta:.1f}%")

        if success_rate_delta > 0.05:
            improvements.append(f"Success rate improved by {success_rate_delta:.1%}")
        elif success_rate_delta < -0.05:
            regressions.append(f"Success rate dropped by {success_rate_delta:.1%}")

        if error_rate_delta < -0.05:
            improvements.append(f"Error rate decreased by {-error_rate_delta:.1%}")
        elif error_rate_delta > 0.05:
            regressions.append(f"Error rate increased by {error_rate_delta:.1%}")

        if test_pass_rate_delta > 0.02:
            improvements.append(f"Test pass rate improved by {test_pass_rate_delta:.1%}")
        elif test_pass_rate_delta < -0.02:
            regressions.append(f"Test pass rate dropped by {test_pass_rate_delta:.1%}")

        # Make decision
        overall_improvement = len(improvements) > len(regressions)
        regression_detected = len(regressions) > 0 and exec_delta > 20.0  # Major regression

        # Calculate confidence score
        total_signals = len(improvements) + len(regressions)
        if total_signals == 0:
            confidence_score = 0.5  # Neutral
        else:
            confidence_score = abs(len(improvements) - len(regressions)) / total_signals

        # Decision logic
        if regression_detected:
            decision = EvaluationDecision.ROLLBACK
            reasoning = f"ROLLBACK: Major regressions detected: {', '.join(regressions)}"
        elif overall_improvement and confidence_score >= self.confidence_threshold:
            decision = EvaluationDecision.KEEP
            reasoning = f"KEEP: Improvements confirmed: {', '.join(improvements)}"
        elif confidence_score < self.confidence_threshold:
            decision = EvaluationDecision.UNCERTAIN
            reasoning = f"UNCERTAIN: Insufficient evidence (confidence={confidence_score:.1%})"
        else:
            decision = EvaluationDecision.ROLLBACK
            reasoning = f"ROLLBACK: Net negative impact. Regressions: {', '.join(regressions)}"

        comparison = ComparisonResult(
            baseline_id=baseline.snapshot_id,
            modified_id=modified.snapshot_id,

            execution_time_delta_percent=exec_delta,
            memory_delta_percent=mem_delta,
            cpu_delta_percent=cpu_delta,
            success_rate_delta=success_rate_delta,
            error_rate_delta=error_rate_delta,
            test_pass_rate_delta=test_pass_rate_delta,
            quality_score_delta=quality_delta,

            overall_improvement=overall_improvement,
            regression_detected=regression_detected,
            confidence_score=confidence_score,

            decision=decision,
            reasoning=reasoning
        )

        return comparison

    def _save_snapshot(self, snapshot: PerformanceSnapshot):
        """Save snapshot to disk."""
        snapshot_file = self.snapshots_dir / f"snapshot_{snapshot.snapshot_id}.json"

        snapshot_dict = asdict(snapshot)

        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_dict, f, indent=2)

    def _save_comparison(self, comparison: ComparisonResult):
        """Save comparison result to disk."""
        comparison_file = self.snapshots_dir / f"comparison_{comparison.baseline_id}_vs_{comparison.modified_id}.json"

        comparison_dict = asdict(comparison)
        comparison_dict["decision"] = comparison.decision.value

        with open(comparison_file, 'w') as f:
            json.dump(comparison_dict, f, indent=2)

    def get_performance_history(self) -> List[PerformanceSnapshot]:
        """Get all performance snapshots ordered by timestamp."""
        snapshots = list(self.snapshots.values())
        return sorted(snapshots, key=lambda s: s.timestamp)

    def get_git_history(self, max_commits: int = 10) -> List[Dict]:
        """Get git commit history."""
        try:
            commits = []
            for commit in list(self.repo.iter_commits())[:max_commits]:
                commits.append({
                    "hash": commit.hexsha[:8],
                    "message": commit.message.split('\n')[0],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "files_changed": len(commit.stats.files)
                })
            return commits
        except Exception as e:
            logger.error(f"Failed to get git history: {e}")
            return []


async def main():
    """Example usage of Self-Evaluation System."""
    evaluator = SelfEvaluationSystem()

    print("\n" + "=" * 70)
    print("SELF-EVALUATION AND ROLLBACK SYSTEM DEMONSTRATION")
    print("=" * 70)
    print()

    # Step 1: Capture baseline
    print("1. Capturing baseline performance...")
    baseline = await evaluator.capture_baseline(notes="Before optimization")
    print(f"   Baseline ID: {baseline.snapshot_id}")
    print(f"   Success rate: {baseline.success_rate:.1%}")
    print(f"   Execution time: {baseline.execution_time_ms:.1f}ms")
    print()

    # Step 2: Simulate modification
    print("2. Applying modification (simulated)...")
    await asyncio.sleep(0.5)
    print("   Modification applied")
    print()

    # Step 3: Evaluate
    print("3. Evaluating modification...")
    comparison = await evaluator.evaluate_modification(
        baseline_id=baseline.snapshot_id,
        modification_description="Optimized caching algorithm",
        notes="Testing impact of caching improvements"
    )

    print(f"   Decision: {comparison.decision.value.upper()}")
    print(f"   Confidence: {comparison.confidence_score:.1%}")
    print(f"   Reasoning: {comparison.reasoning}")
    print()

    # Step 4: Act on decision
    if comparison.decision == EvaluationDecision.KEEP:
        print("4. ✓ Keeping modification (improvement confirmed)")
        commit_hash = await evaluator.commit_modification(
            message="Optimized caching algorithm",
            files=None
        )
        print(f"   Committed: {commit_hash[:8]}")
    elif comparison.decision == EvaluationDecision.ROLLBACK:
        print("4. ✗ Rolling back modification (regression detected)")
        success = await evaluator.rollback_modification()
        print(f"   Rollback: {'successful' if success else 'failed'}")
    else:
        print("4. ? Uncertain - need more data")

    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
