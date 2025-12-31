#!/usr/bin/env python3
"""
Darwin Gödel Machine - Empirical Integration
=============================================

Enhances the existing DGM with research-backed empirical validation patterns.

Key Research Findings Applied:
- From "Bounded Recursive Self-Improvement" (Nivel et al.): Self-improvement
  within designer-imposed constraints using empirical validation
- From "An AI Self-Improvement Research Agenda" (Yampolskiy): Systematic
  tracking of self-modifications with failure history
- From DGM Research Paper: Agent archive system, empirical fitness evaluation,
  and open-ended exploration instead of pure proof-based validation

This module provides:
1. Agent Archive - Growing collection of agent versions with fitness scores
2. Empirical Fitness Evaluator - Validates improvements by actual task execution
3. Failure History Tracker - Records what failed and why to avoid repeating mistakes
4. Open-ended Exploration - Selects agents based on novelty AND performance

Integration Points:
- Wraps existing darwin_godel_machine.py
- Uses meta_learning_engine.py for performance tracking
- Extends skill_evolution_system.py patterns to agent level
"""

import asyncio
import json
import logging
import hashlib
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
import traceback
import copy

from storage_path_utils import get_database_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = get_database_path("dgm_empirical.db")


class FitnessMethod(Enum):
    """How fitness was evaluated"""
    TASK_EXECUTION = "task_execution"  # Ran actual tasks and measured success
    BENCHMARK = "benchmark"  # Ran standardized benchmark suite
    A_B_TEST = "a_b_test"  # Compared against baseline in A/B test
    SIMULATION = "simulation"  # Ran in sandboxed simulation


class ModificationOutcome(Enum):
    """Result of a self-modification attempt"""
    SUCCESS = "success"  # Improvement validated empirically
    REGRESSION = "regression"  # Performance got worse
    NEUTRAL = "neutral"  # No significant change
    FAILURE = "failure"  # Modification couldn't be applied
    UNSAFE = "unsafe"  # Violated safety constraints


@dataclass
class AgentVersion:
    """A version of the agent stored in the archive"""
    version_id: str
    parent_version_id: Optional[str]  # Which version this evolved from
    code_snapshot: str  # Serialized agent configuration/code
    fitness_score: float  # Empirically measured fitness
    fitness_method: FitnessMethod
    novelty_score: float  # How different from other versions
    task_successes: int  # Number of successful task completions
    task_failures: int  # Number of failed task attempts
    created_at: datetime
    modifications_applied: List[str]  # List of modification IDs that led here
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureRecord:
    """Record of a failed modification attempt"""
    failure_id: str
    modification_type: str
    description: str
    attempted_change: str  # What was tried
    failure_reason: str  # Why it failed
    error_trace: Optional[str]  # Stack trace if applicable
    context: Dict[str, Any]  # Environmental conditions
    timestamp: datetime
    related_failures: List[str] = field(default_factory=list)  # Similar past failures


@dataclass
class EmpiricalResult:
    """Result of empirical fitness evaluation"""
    result_id: str
    agent_version_id: str
    fitness_score: float
    method: FitnessMethod
    tasks_attempted: int
    tasks_succeeded: int
    benchmark_scores: Dict[str, float]
    comparison_baseline: Optional[str]  # Version compared against
    improvement_delta: float  # Change from baseline
    confidence: float  # Statistical confidence in result
    evaluation_duration_ms: int
    timestamp: datetime


class AgentArchive:
    """
    Growing collection of agent versions with fitness tracking.

    Based on DGM research pattern: maintains diverse population
    of agent versions for open-ended exploration.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize archive database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_versions (
                version_id TEXT PRIMARY KEY,
                parent_version_id TEXT,
                code_snapshot TEXT NOT NULL,
                fitness_score REAL DEFAULT 0.0,
                fitness_method TEXT,
                novelty_score REAL DEFAULT 0.0,
                task_successes INTEGER DEFAULT 0,
                task_failures INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                modifications_applied TEXT NOT NULL,
                metadata TEXT NOT NULL,
                FOREIGN KEY (parent_version_id) REFERENCES agent_versions(version_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fitness ON agent_versions(fitness_score DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_novelty ON agent_versions(novelty_score DESC)
        """)

        conn.commit()
        conn.close()

    def add_version(self, version: AgentVersion) -> str:
        """Add new agent version to archive"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_versions
            (version_id, parent_version_id, code_snapshot, fitness_score,
             fitness_method, novelty_score, task_successes, task_failures,
             created_at, modifications_applied, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            version.version_id,
            version.parent_version_id,
            version.code_snapshot,
            version.fitness_score,
            version.fitness_method.value if version.fitness_method else None,
            version.novelty_score,
            version.task_successes,
            version.task_failures,
            version.created_at.isoformat(),
            json.dumps(version.modifications_applied),
            json.dumps(version.metadata)
        ))

        conn.commit()
        conn.close()

        logger.info(f"Added agent version {version.version_id} to archive (fitness={version.fitness_score:.3f})")
        return version.version_id

    def get_version(self, version_id: str) -> Optional[AgentVersion]:
        """Retrieve specific agent version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM agent_versions WHERE version_id = ?
        """, (version_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_version(row)

    def _row_to_version(self, row) -> AgentVersion:
        """Convert database row to AgentVersion"""
        return AgentVersion(
            version_id=row[0],
            parent_version_id=row[1],
            code_snapshot=row[2],
            fitness_score=row[3],
            fitness_method=FitnessMethod(row[4]) if row[4] else None,
            novelty_score=row[5],
            task_successes=row[6],
            task_failures=row[7],
            created_at=datetime.fromisoformat(row[8]),
            modifications_applied=json.loads(row[9]),
            metadata=json.loads(row[10])
        )

    def select_for_modification(self,
                                 top_k: int = 5,
                                 novelty_weight: float = 0.3) -> List[AgentVersion]:
        """
        Select agent versions for potential modification.

        Uses combined fitness + novelty scoring for open-ended exploration.
        Research insight: Pure fitness selection leads to local optima.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Combined score: fitness * (1 - novelty_weight) + novelty * novelty_weight
        cursor.execute(f"""
            SELECT *,
                   (fitness_score * {1 - novelty_weight} + novelty_score * {novelty_weight}) as combined_score
            FROM agent_versions
            ORDER BY combined_score DESC
            LIMIT ?
        """, (top_k,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_version(row[:-1]) for row in rows]  # Exclude combined_score column

    def get_best_version(self) -> Optional[AgentVersion]:
        """Get highest fitness version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM agent_versions
            ORDER BY fitness_score DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        return self._row_to_version(row) if row else None

    def update_fitness(self, version_id: str, fitness_score: float,
                       method: FitnessMethod, task_result: bool):
        """Update fitness after task execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        success_col = "task_successes" if task_result else "task_failures"

        cursor.execute(f"""
            UPDATE agent_versions
            SET fitness_score = ?,
                fitness_method = ?,
                {success_col} = {success_col} + 1
            WHERE version_id = ?
        """, (fitness_score, method.value, version_id))

        conn.commit()
        conn.close()

    def calculate_novelty(self, code_snapshot: str) -> float:
        """
        Calculate novelty score for a code snapshot.

        Uses behavioral characterization - how different is this
        from existing versions in the archive?
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT code_snapshot FROM agent_versions")
        existing = cursor.fetchall()
        conn.close()

        if not existing:
            return 1.0  # First version is maximally novel

        # Simple novelty: average edit distance (normalized)
        snapshot_hash = hashlib.md5(code_snapshot.encode()).hexdigest()

        novelty_sum = 0.0
        for (existing_code,) in existing:
            existing_hash = hashlib.md5(existing_code.encode()).hexdigest()
            # Hamming distance on hash as proxy
            diff = sum(c1 != c2 for c1, c2 in zip(snapshot_hash, existing_hash))
            novelty_sum += diff / len(snapshot_hash)

        return novelty_sum / len(existing)

    def get_archive_stats(self) -> Dict[str, Any]:
        """Get archive statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM agent_versions")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(fitness_score), MAX(fitness_score), MIN(fitness_score) FROM agent_versions")
        avg_fit, max_fit, min_fit = cursor.fetchone()

        cursor.execute("SELECT SUM(task_successes), SUM(task_failures) FROM agent_versions")
        total_success, total_fail = cursor.fetchone()

        conn.close()

        return {
            "total_versions": total,
            "avg_fitness": avg_fit or 0.0,
            "max_fitness": max_fit or 0.0,
            "min_fitness": min_fit or 0.0,
            "total_task_successes": total_success or 0,
            "total_task_failures": total_fail or 0,
            "success_rate": (total_success or 0) / max(1, (total_success or 0) + (total_fail or 0))
        }


class FailureHistoryTracker:
    """
    Tracks failed modification attempts to avoid repeating mistakes.

    Research insight from DGM paper: Failure history is crucial for
    efficient self-improvement - don't waste compute re-trying known failures.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize failure history database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_history (
                failure_id TEXT PRIMARY KEY,
                modification_type TEXT NOT NULL,
                description TEXT NOT NULL,
                attempted_change TEXT NOT NULL,
                failure_reason TEXT NOT NULL,
                error_trace TEXT,
                context TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                related_failures TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mod_type ON failure_history(modification_type)
        """)

        conn.commit()
        conn.close()

    def record_failure(self,
                       modification_type: str,
                       description: str,
                       attempted_change: str,
                       failure_reason: str,
                       error_trace: Optional[str] = None,
                       context: Optional[Dict] = None) -> str:
        """Record a failed modification attempt"""
        failure_id = hashlib.md5(
            f"{modification_type}:{description}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Find related failures
        related = self.find_similar_failures(modification_type, description)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO failure_history
            (failure_id, modification_type, description, attempted_change,
             failure_reason, error_trace, context, timestamp, related_failures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            failure_id,
            modification_type,
            description,
            attempted_change,
            failure_reason,
            error_trace,
            json.dumps(context or {}),
            datetime.now().isoformat(),
            json.dumps([f.failure_id for f in related[:5]])
        ))

        conn.commit()
        conn.close()

        logger.warning(f"Recorded failure {failure_id}: {description[:50]}...")
        return failure_id

    def find_similar_failures(self,
                               modification_type: str,
                               description: str,
                               limit: int = 10) -> List[FailureRecord]:
        """Find similar past failures to avoid repeating"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Simple matching on type and description keywords
        cursor.execute("""
            SELECT * FROM failure_history
            WHERE modification_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (modification_type, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row) -> FailureRecord:
        """Convert database row to FailureRecord"""
        return FailureRecord(
            failure_id=row[0],
            modification_type=row[1],
            description=row[2],
            attempted_change=row[3],
            failure_reason=row[4],
            error_trace=row[5],
            context=json.loads(row[6]),
            timestamp=datetime.fromisoformat(row[7]),
            related_failures=json.loads(row[8])
        )

    def should_attempt(self, modification_type: str, description: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a modification should be attempted based on failure history.

        Returns (should_attempt, reason_if_not)
        """
        similar = self.find_similar_failures(modification_type, description, limit=5)

        if not similar:
            return True, None

        # Check for repeated failures
        recent_similar = [f for f in similar if
                         (datetime.now() - f.timestamp).days < 7]

        if len(recent_similar) >= 3:
            return False, f"Similar modification failed {len(recent_similar)} times in past week"

        return True, None

    def get_failure_stats(self) -> Dict[str, Any]:
        """Get failure statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM failure_history")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT modification_type, COUNT(*) as count
            FROM failure_history
            GROUP BY modification_type
            ORDER BY count DESC
        """)
        by_type = dict(cursor.fetchall())

        conn.close()

        return {
            "total_failures": total,
            "failures_by_type": by_type
        }


class EmpiricalFitnessEvaluator:
    """
    Evaluates agent fitness through actual task execution.

    Research insight: Empirical validation > formal proofs for practical
    self-improvement. Run real tasks and measure real outcomes.
    """

    def __init__(self, archive: AgentArchive, failure_tracker: FailureHistoryTracker):
        self.archive = archive
        self.failure_tracker = failure_tracker
        self.benchmark_tasks: List[Dict[str, Any]] = []
        self._init_benchmark_tasks()

    def _init_benchmark_tasks(self):
        """Initialize standard benchmark task suite"""
        self.benchmark_tasks = [
            {
                "id": "code_analysis",
                "description": "Analyze a Python file and identify issues",
                "type": "analysis",
                "difficulty": 0.3
            },
            {
                "id": "task_decomposition",
                "description": "Break down a complex goal into subtasks",
                "type": "planning",
                "difficulty": 0.5
            },
            {
                "id": "multi_agent_coord",
                "description": "Coordinate execution across multiple agents",
                "type": "orchestration",
                "difficulty": 0.7
            },
            {
                "id": "learning_integration",
                "description": "Store and retrieve learned patterns",
                "type": "memory",
                "difficulty": 0.4
            },
            {
                "id": "self_evaluation",
                "description": "Evaluate own performance and suggest improvements",
                "type": "meta",
                "difficulty": 0.8
            }
        ]

    async def evaluate_fitness(self,
                                version: AgentVersion,
                                method: FitnessMethod = FitnessMethod.BENCHMARK,
                                executor: Optional[Callable] = None) -> EmpiricalResult:
        """
        Evaluate fitness of an agent version empirically.

        Args:
            version: Agent version to evaluate
            method: How to evaluate fitness
            executor: Optional callable that executes tasks with the agent
        """
        start_time = datetime.now()
        result_id = hashlib.md5(
            f"{version.version_id}:{start_time.isoformat()}".encode()
        ).hexdigest()[:16]

        tasks_attempted = 0
        tasks_succeeded = 0
        benchmark_scores: Dict[str, float] = {}

        if method == FitnessMethod.BENCHMARK:
            for task in self.benchmark_tasks:
                tasks_attempted += 1
                try:
                    # Execute benchmark task
                    if executor:
                        success = await executor(task, version)
                    else:
                        # Simulated execution for testing
                        success = await self._simulate_task_execution(task, version)

                    if success:
                        tasks_succeeded += 1
                        benchmark_scores[task["id"]] = 1.0
                    else:
                        benchmark_scores[task["id"]] = 0.0

                except Exception as e:
                    logger.error(f"Benchmark task {task['id']} failed: {e}")
                    benchmark_scores[task["id"]] = 0.0

        elif method == FitnessMethod.A_B_TEST:
            # Compare against best version
            baseline = self.archive.get_best_version()
            if baseline and executor:
                # Run same tasks on both and compare
                pass  # Implementation depends on specific A/B test framework

        # Calculate overall fitness
        if tasks_attempted > 0:
            fitness_score = tasks_succeeded / tasks_attempted
        else:
            fitness_score = version.fitness_score  # Keep existing

        # Calculate improvement delta
        baseline_version = self.archive.get_best_version()
        improvement_delta = 0.0
        if baseline_version:
            improvement_delta = fitness_score - baseline_version.fitness_score

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        result = EmpiricalResult(
            result_id=result_id,
            agent_version_id=version.version_id,
            fitness_score=fitness_score,
            method=method,
            tasks_attempted=tasks_attempted,
            tasks_succeeded=tasks_succeeded,
            benchmark_scores=benchmark_scores,
            comparison_baseline=baseline_version.version_id if baseline_version else None,
            improvement_delta=improvement_delta,
            confidence=self._calculate_confidence(tasks_attempted),
            evaluation_duration_ms=duration_ms,
            timestamp=datetime.now()
        )

        # Update archive with new fitness
        self.archive.update_fitness(
            version.version_id,
            fitness_score,
            method,
            tasks_succeeded > 0
        )

        logger.info(f"Evaluated {version.version_id}: fitness={fitness_score:.3f}, delta={improvement_delta:+.3f}")
        return result

    async def _simulate_task_execution(self, task: Dict, version: AgentVersion) -> bool:
        """Simulated task execution for testing"""
        # In production, this would actually run the task
        # For now, use fitness-weighted probability
        import random
        base_prob = 0.5 + (version.fitness_score * 0.3)
        difficulty_penalty = task.get("difficulty", 0.5) * 0.2
        success_prob = max(0.1, min(0.95, base_prob - difficulty_penalty))
        return random.random() < success_prob

    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate statistical confidence based on sample size"""
        # Simple confidence based on sample size
        if sample_size < 5:
            return 0.3
        elif sample_size < 10:
            return 0.6
        elif sample_size < 20:
            return 0.8
        else:
            return 0.95


class DGMEmpiricalIntegration:
    """
    Main integration class that combines empirical DGM patterns with existing AGI orchestrator.

    This is the primary interface for applying research DGM patterns:
    1. Agent Archive - Version management with open-ended exploration
    2. Empirical Fitness - Validate improvements by actual execution
    3. Failure History - Learn from past mistakes
    4. Bounded Self-Improvement - Modifications within safety constraints
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.archive = AgentArchive(db_path)
        self.failure_tracker = FailureHistoryTracker(db_path)
        self.fitness_evaluator = EmpiricalFitnessEvaluator(self.archive, self.failure_tracker)

        # Current active version
        self.current_version: Optional[AgentVersion] = None

        # Modification constraints (bounded self-improvement)
        self.modification_budget: int = 10  # Max modifications per cycle
        self.min_improvement_threshold: float = 0.05  # 5% improvement required
        self.safety_constraints: List[Callable[[str], bool]] = []

    def initialize_from_current_state(self, orchestrator_config: Dict[str, Any]) -> AgentVersion:
        """
        Create initial version from current orchestrator state.

        Call this at startup to establish baseline in archive.
        """
        version_id = hashlib.md5(
            f"initial:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        code_snapshot = json.dumps(orchestrator_config, indent=2, default=str)
        novelty = self.archive.calculate_novelty(code_snapshot)

        version = AgentVersion(
            version_id=version_id,
            parent_version_id=None,
            code_snapshot=code_snapshot,
            fitness_score=0.5,  # Assume baseline 50% fitness
            fitness_method=None,
            novelty_score=novelty,
            task_successes=0,
            task_failures=0,
            created_at=datetime.now(),
            modifications_applied=[],
            metadata={"type": "initial_baseline"}
        )

        self.archive.add_version(version)
        self.current_version = version

        logger.info(f"Initialized archive with baseline version {version_id}")
        return version

    async def propose_modification(self,
                                    modification_type: str,
                                    description: str,
                                    proposed_change: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[AgentVersion]]:
        """
        Propose a self-modification with empirical validation.

        Returns (approved, reason, new_version_if_approved)
        """
        # Check failure history
        should_try, reason = self.failure_tracker.should_attempt(modification_type, description)
        if not should_try:
            logger.warning(f"Modification blocked by failure history: {reason}")
            return False, reason, None

        # Check safety constraints
        change_str = json.dumps(proposed_change, default=str)
        for constraint in self.safety_constraints:
            if not constraint(change_str):
                reason = "Modification violates safety constraint"
                self.failure_tracker.record_failure(
                    modification_type, description, change_str,
                    reason, context={"constraint": str(constraint)}
                )
                return False, reason, None

        # Create candidate version
        if not self.current_version:
            return False, "No current version established", None

        parent_config = json.loads(self.current_version.code_snapshot)
        candidate_config = copy.deepcopy(parent_config)

        # Apply proposed changes
        for key, value in proposed_change.items():
            candidate_config[key] = value

        candidate_snapshot = json.dumps(candidate_config, indent=2, default=str)
        novelty = self.archive.calculate_novelty(candidate_snapshot)

        candidate_id = hashlib.md5(
            f"{self.current_version.version_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        candidate = AgentVersion(
            version_id=candidate_id,
            parent_version_id=self.current_version.version_id,
            code_snapshot=candidate_snapshot,
            fitness_score=0.0,  # Will be evaluated
            fitness_method=None,
            novelty_score=novelty,
            task_successes=0,
            task_failures=0,
            created_at=datetime.now(),
            modifications_applied=self.current_version.modifications_applied + [modification_type],
            metadata={
                "modification_type": modification_type,
                "description": description,
                "proposed_change": proposed_change
            }
        )

        # Empirically evaluate fitness
        logger.info(f"Evaluating candidate version {candidate_id}...")
        result = await self.fitness_evaluator.evaluate_fitness(candidate)
        candidate.fitness_score = result.fitness_score
        candidate.fitness_method = result.method

        # Check if improvement meets threshold
        if result.improvement_delta < self.min_improvement_threshold:
            reason = f"Improvement {result.improvement_delta:.3f} below threshold {self.min_improvement_threshold}"
            self.failure_tracker.record_failure(
                modification_type, description, change_str,
                reason, context={"delta": result.improvement_delta, "threshold": self.min_improvement_threshold}
            )
            # Still add to archive for diversity
            self.archive.add_version(candidate)
            return False, reason, candidate

        # Success! Add to archive and promote
        self.archive.add_version(candidate)
        self.current_version = candidate

        logger.info(f"Modification approved! New version {candidate_id} with fitness {candidate.fitness_score:.3f}")
        return True, None, candidate

    async def run_improvement_cycle(self,
                                     max_attempts: int = 5,
                                     executor: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run one cycle of self-improvement.

        1. Select promising versions from archive
        2. Generate modification candidates
        3. Evaluate empirically
        4. Promote if improved
        """
        results = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "new_versions": [],
            "best_improvement": 0.0
        }

        # Select versions for modification
        candidates = self.archive.select_for_modification(top_k=max_attempts)

        if not candidates:
            logger.warning("No candidates in archive for improvement cycle")
            return results

        for candidate in candidates:
            results["attempts"] += 1

            # Generate modification idea (would be AI-generated in production)
            modification = self._generate_modification_idea(candidate)

            approved, reason, new_version = await self.propose_modification(
                modification["type"],
                modification["description"],
                modification["changes"]
            )

            if approved and new_version:
                results["successes"] += 1
                results["new_versions"].append(new_version.version_id)
                improvement = new_version.fitness_score - candidate.fitness_score
                results["best_improvement"] = max(results["best_improvement"], improvement)
            else:
                results["failures"] += 1

        return results

    def _generate_modification_idea(self, version: AgentVersion) -> Dict[str, Any]:
        """
        Generate modification idea for a version.

        In production, this would use AI to generate targeted improvements.
        """
        # Simple mutation for demonstration
        return {
            "type": "parameter_tune",
            "description": f"Tune parameters for version {version.version_id[:8]}",
            "changes": {
                "max_iterations": 10,
                "confidence_threshold": 0.7
            }
        }

    def add_safety_constraint(self, constraint: Callable[[str], bool]):
        """Add a safety constraint that modifications must satisfy"""
        self.safety_constraints.append(constraint)

    def get_system_status(self) -> Dict[str, Any]:
        """Get current DGM system status"""
        archive_stats = self.archive.get_archive_stats()
        failure_stats = self.failure_tracker.get_failure_stats()

        return {
            "current_version": self.current_version.version_id if self.current_version else None,
            "current_fitness": self.current_version.fitness_score if self.current_version else 0.0,
            "archive": archive_stats,
            "failures": failure_stats,
            "modification_budget": self.modification_budget,
            "improvement_threshold": self.min_improvement_threshold
        }


# Convenience function for integration with existing orchestrator
async def create_dgm_integration(orchestrator_config: Optional[Dict] = None) -> DGMEmpiricalIntegration:
    """
    Create and initialize DGM empirical integration.

    Usage:
        dgm = await create_dgm_integration({"agents": [...], "settings": {...}})
        approved, reason, new_version = await dgm.propose_modification(...)
    """
    dgm = DGMEmpiricalIntegration()

    if orchestrator_config:
        dgm.initialize_from_current_state(orchestrator_config)
    else:
        # Default minimal config
        dgm.initialize_from_current_state({
            "name": "agi_orchestrator",
            "version": "1.0.0",
            "agents": [],
            "settings": {}
        })

    return dgm


if __name__ == "__main__":
    # Test the integration
    async def test():
        print("Testing DGM Empirical Integration...")

        # Create integration
        dgm = await create_dgm_integration({
            "name": "test_orchestrator",
            "agents": ["planner", "executor", "evaluator"],
            "settings": {"max_iterations": 5}
        })

        print(f"\nInitial status: {json.dumps(dgm.get_system_status(), indent=2)}")

        # Run improvement cycle
        results = await dgm.run_improvement_cycle(max_attempts=3)
        print(f"\nImprovement cycle results: {json.dumps(results, indent=2)}")

        # Final status
        print(f"\nFinal status: {json.dumps(dgm.get_system_status(), indent=2)}")

    asyncio.run(test())
