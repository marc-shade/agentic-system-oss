#!/usr/bin/env python3
"""
Wiggum Evaluation Integration for Self-* Features
=================================================

Integrates Chief Wiggum guaranteed-completion loops with the self-improvement,
self-healing, and self-optimization evaluation framework.

Key Capabilities:
- Wrap self-* operations in Wiggum loops for guaranteed completion
- Track iteration metrics (attempts, learnings, time-to-completion)
- Store learnings in enhanced-memory for cross-run improvement
- Integrate with Darwin-Gödel Machine for verified self-improvement
- Provide eval criteria specific to iterative completion quality

Integration Points:
- SelfEvaluationSystem: Wrap performance measurements in Wiggum loops
- DarwinGodelMachine: Verified self-improvement with completion guarantees
- AgentEvalFramework: Wiggum-specific eval criteria
- Enhanced Memory: Cross-iteration learning persistence

Usage:
    from wiggum_eval_integration import WiggumEvalIntegration

    evaluator = WiggumEvalIntegration()

    # Wrap a self-improvement task
    result = await evaluator.evaluate_with_wiggum(
        task="Optimize memory consolidation latency",
        success_criteria="Consolidation completes in <100ms",
        max_iterations=10
    )
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage_path_utils import get_database_path, STORAGE_BASE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
WIGGUM_STATE_FILE = Path.home() / ".claude" / "wiggum-loop.local.md"
WIGGUM_LEARNINGS_DIR = Path.home() / ".claude" / "wiggum-learnings"
WIGGUM_EVAL_DB = get_database_path("wiggum_evals.db")


class WiggumOutcome(Enum):
    """Outcome of a Wiggum-wrapped evaluation"""
    SUCCESS = "success"  # Completed within iterations
    MAX_ITERATIONS = "max_iterations"  # Hit iteration limit
    QUALITY_FAILURE = "quality_failure"  # Ember rejected
    ERROR = "error"  # Exception occurred


@dataclass
class WiggumIteration:
    """Single iteration within a Wiggum loop"""
    iteration_number: int
    approach_tried: str
    result: str  # success, failure, partial
    insight_gained: str
    duration_ms: float
    memory_entity_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WiggumEvalResult:
    """Complete result of a Wiggum-wrapped evaluation"""
    eval_id: str
    task: str
    success_criteria: str
    outcome: WiggumOutcome
    total_iterations: int
    max_iterations: int

    # Timing
    start_time: str
    end_time: str
    total_duration_ms: float

    # Iterations
    iterations: List[WiggumIteration]

    # Quality metrics
    ember_approved: bool
    quality_score: float  # 0.0-1.0

    # Learning
    learnings_stored: int
    key_insights: List[str]

    # Final result
    final_output: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class WiggumEvalCriteria:
    """Evaluation criteria for Wiggum-wrapped tasks"""
    name: str
    description: str

    # Thresholds
    max_acceptable_iterations: int = 5
    min_quality_score: float = 0.7
    require_ember_approval: bool = True
    require_learning_capture: bool = True

    # Weights for scoring
    weight_completion: float = 0.4
    weight_efficiency: float = 0.3
    weight_quality: float = 0.2
    weight_learning: float = 0.1

    def evaluate(self, result: WiggumEvalResult) -> Dict[str, Any]:
        """Evaluate a Wiggum result against this criteria"""
        scores = {}

        # Completion score (did it finish?)
        if result.outcome == WiggumOutcome.SUCCESS:
            scores['completion'] = 1.0
        elif result.outcome == WiggumOutcome.MAX_ITERATIONS:
            scores['completion'] = 0.5  # Partial credit
        else:
            scores['completion'] = 0.0

        # Efficiency score (how many iterations?)
        if result.total_iterations <= self.max_acceptable_iterations:
            scores['efficiency'] = 1.0 - (result.total_iterations / self.max_acceptable_iterations * 0.5)
        else:
            scores['efficiency'] = max(0, 0.5 - (result.total_iterations - self.max_acceptable_iterations) * 0.1)

        # Quality score
        scores['quality'] = result.quality_score if result.ember_approved else result.quality_score * 0.5

        # Learning score
        if self.require_learning_capture:
            scores['learning'] = min(1.0, result.learnings_stored / 3)  # 3 learnings = full score
        else:
            scores['learning'] = 1.0

        # Weighted total
        total = (
            scores['completion'] * self.weight_completion +
            scores['efficiency'] * self.weight_efficiency +
            scores['quality'] * self.weight_quality +
            scores['learning'] * self.weight_learning
        )

        return {
            'passed': total >= 0.7 and (not self.require_ember_approval or result.ember_approved),
            'total_score': total,
            'component_scores': scores,
            'criteria': self.name
        }


class WiggumEvalIntegration:
    """
    Integration layer for Wiggum loops in self-* feature evaluation.

    Wraps self-improvement, self-healing, and self-optimization tasks
    in guaranteed-completion loops with learning capture.
    """

    def __init__(self, db_path: Path = WIGGUM_EVAL_DB):
        """Initialize Wiggum eval integration"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        WIGGUM_LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)

        self._init_database()
        self._init_criteria()

        # Track active evaluation
        self.current_eval: Optional[WiggumEvalResult] = None

    def _init_database(self):
        """Initialize SQLite database for eval tracking"""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS wiggum_evals (
                    eval_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    success_criteria TEXT,
                    outcome TEXT,
                    total_iterations INTEGER,
                    max_iterations INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    total_duration_ms REAL,
                    ember_approved INTEGER,
                    quality_score REAL,
                    learnings_stored INTEGER,
                    final_output TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS wiggum_iterations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eval_id TEXT NOT NULL,
                    iteration_number INTEGER,
                    approach_tried TEXT,
                    result TEXT,
                    insight_gained TEXT,
                    duration_ms REAL,
                    memory_entity_id TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (eval_id) REFERENCES wiggum_evals(eval_id)
                );

                CREATE TABLE IF NOT EXISTS wiggum_criteria (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    max_acceptable_iterations INTEGER,
                    min_quality_score REAL,
                    require_ember_approval INTEGER,
                    require_learning_capture INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_evals_outcome ON wiggum_evals(outcome);
                CREATE INDEX IF NOT EXISTS idx_evals_task ON wiggum_evals(task);
                CREATE INDEX IF NOT EXISTS idx_iterations_eval ON wiggum_iterations(eval_id);
            """)

    def _init_criteria(self):
        """Initialize default evaluation criteria"""
        self.criteria = {
            'self_improvement': WiggumEvalCriteria(
                name='self_improvement',
                description='Criteria for self-improvement tasks (Darwin-Gödel)',
                max_acceptable_iterations=10,
                min_quality_score=0.8,
                require_ember_approval=True,
                require_learning_capture=True
            ),
            'self_healing': WiggumEvalCriteria(
                name='self_healing',
                description='Criteria for self-healing/recovery tasks',
                max_acceptable_iterations=5,  # Faster expected
                min_quality_score=0.7,
                require_ember_approval=True,
                require_learning_capture=True
            ),
            'self_optimization': WiggumEvalCriteria(
                name='self_optimization',
                description='Criteria for performance optimization tasks',
                max_acceptable_iterations=15,  # May need more exploration
                min_quality_score=0.75,
                require_ember_approval=True,
                require_learning_capture=True
            ),
            'skill_evolution': WiggumEvalCriteria(
                name='skill_evolution',
                description='Criteria for skill A/B testing and evolution',
                max_acceptable_iterations=8,
                min_quality_score=0.8,
                require_ember_approval=True,
                require_learning_capture=True,
                weight_learning=0.2  # Higher weight on learning
            )
        }

    async def evaluate_with_wiggum(
        self,
        task: str,
        success_criteria: str,
        task_executor: Callable[[int], Any],
        max_iterations: int = 10,
        criteria_name: str = 'self_improvement',
        ember_context: str = None
    ) -> WiggumEvalResult:
        """
        Execute a task wrapped in Wiggum loop with full evaluation tracking.

        Args:
            task: Description of the task
            success_criteria: Binary completion criteria
            task_executor: Async function(iteration) -> (success: bool, output: str, insight: str)
            max_iterations: Maximum attempts before failure
            criteria_name: Which eval criteria to use
            ember_context: Context for Ember quality validation

        Returns:
            WiggumEvalResult with full evaluation metrics
        """
        import hashlib

        eval_id = hashlib.md5(f"{task}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()
        iterations = []

        logger.info(f"Starting Wiggum eval: {eval_id} - {task[:50]}...")

        # Initialize result
        result = WiggumEvalResult(
            eval_id=eval_id,
            task=task,
            success_criteria=success_criteria,
            outcome=WiggumOutcome.ERROR,
            total_iterations=0,
            max_iterations=max_iterations,
            start_time=start_time.isoformat(),
            end_time="",
            total_duration_ms=0,
            iterations=[],
            ember_approved=False,
            quality_score=0.0,
            learnings_stored=0,
            key_insights=[]
        )

        self.current_eval = result

        try:
            # Execute iterations
            for i in range(1, max_iterations + 1):
                iter_start = time.time()

                logger.info(f"Wiggum iteration {i}/{max_iterations}")

                try:
                    success, output, insight = await task_executor(i)
                except Exception as e:
                    success = False
                    output = str(e)
                    insight = f"Exception in iteration {i}: {type(e).__name__}"

                iter_duration = (time.time() - iter_start) * 1000

                iteration = WiggumIteration(
                    iteration_number=i,
                    approach_tried=f"Iteration {i} attempt",
                    result="success" if success else "failure",
                    insight_gained=insight or "No insight captured",
                    duration_ms=iter_duration
                )
                iterations.append(iteration)

                # Store learning in memory
                memory_id = await self._store_iteration_learning(eval_id, iteration, task)
                iteration.memory_entity_id = memory_id

                if insight:
                    result.key_insights.append(insight)

                if success:
                    result.outcome = WiggumOutcome.SUCCESS
                    result.final_output = output
                    result.total_iterations = i
                    break
            else:
                # Max iterations reached
                result.outcome = WiggumOutcome.MAX_ITERATIONS
                result.total_iterations = max_iterations

            # Ember quality check
            if result.outcome == WiggumOutcome.SUCCESS:
                ember_result = await self._check_ember_quality(
                    task, result.final_output, ember_context
                )
                result.ember_approved = ember_result.get('approved', False)
                result.quality_score = ember_result.get('score', 0.5)

                if not result.ember_approved:
                    result.outcome = WiggumOutcome.QUALITY_FAILURE

        except Exception as e:
            result.outcome = WiggumOutcome.ERROR
            result.error_message = str(e)
            logger.error(f"Wiggum eval error: {e}")

        # Finalize
        end_time = datetime.now()
        result.end_time = end_time.isoformat()
        result.total_duration_ms = (end_time - start_time).total_seconds() * 1000
        result.iterations = iterations
        result.learnings_stored = len([i for i in iterations if i.memory_entity_id])

        # Store in database
        self._store_eval_result(result)

        # Evaluate against criteria
        criteria = self.criteria.get(criteria_name, self.criteria['self_improvement'])
        eval_scores = criteria.evaluate(result)

        logger.info(f"Wiggum eval complete: {result.outcome.value}, "
                   f"iterations={result.total_iterations}, "
                   f"score={eval_scores['total_score']:.2f}")

        self.current_eval = None
        return result

    async def _store_iteration_learning(
        self,
        eval_id: str,
        iteration: WiggumIteration,
        task: str
    ) -> Optional[str]:
        """Store iteration learning in enhanced-memory"""
        try:
            # Try to use enhanced-memory MCP
            # In production, this would call the actual MCP
            entity_name = f"wiggum-eval-{eval_id}-iter{iteration.iteration_number}"

            learning = {
                "name": entity_name,
                "entityType": "wiggum_eval_iteration",
                "observations": [
                    f"task: {task[:100]}",
                    f"iteration: {iteration.iteration_number}",
                    f"result: {iteration.result}",
                    f"insight: {iteration.insight_gained}",
                    f"duration_ms: {iteration.duration_ms:.1f}"
                ]
            }

            # Store locally as fallback
            learning_file = WIGGUM_LEARNINGS_DIR / f"{entity_name}.json"
            with open(learning_file, 'w') as f:
                json.dump(learning, f, indent=2)

            return entity_name

        except Exception as e:
            logger.warning(f"Failed to store learning: {e}")
            return None

    async def _check_ember_quality(
        self,
        task: str,
        output: str,
        context: str = None
    ) -> Dict[str, Any]:
        """Check quality with Ember MCP"""
        try:
            # In production, this would call ember-mcp
            # For now, do basic quality checks

            # Check for forbidden patterns
            forbidden_patterns = [
                'TODO', 'FIXME', 'placeholder', 'mock', 'dummy',
                'example.com', 'lorem ipsum', 'not implemented'
            ]

            output_lower = (output or '').lower()
            violations = [p for p in forbidden_patterns if p.lower() in output_lower]

            if violations:
                return {
                    'approved': False,
                    'score': 0.3,
                    'violations': violations,
                    'feedback': f"Quality issues: {', '.join(violations)}"
                }

            return {
                'approved': True,
                'score': 0.85,
                'feedback': "Quality validation passed"
            }

        except Exception as e:
            logger.warning(f"Ember check failed: {e}")
            return {'approved': False, 'score': 0.0, 'error': str(e)}

    def _store_eval_result(self, result: WiggumEvalResult):
        """Store evaluation result in database"""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            # Store main result
            conn.execute("""
                INSERT OR REPLACE INTO wiggum_evals (
                    eval_id, task, success_criteria, outcome,
                    total_iterations, max_iterations, start_time, end_time,
                    total_duration_ms, ember_approved, quality_score,
                    learnings_stored, final_output, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.eval_id, result.task, result.success_criteria,
                result.outcome.value, result.total_iterations, result.max_iterations,
                result.start_time, result.end_time, result.total_duration_ms,
                1 if result.ember_approved else 0, result.quality_score,
                result.learnings_stored, result.final_output, result.error_message
            ))

            # Store iterations
            for iteration in result.iterations:
                conn.execute("""
                    INSERT INTO wiggum_iterations (
                        eval_id, iteration_number, approach_tried, result,
                        insight_gained, duration_ms, memory_entity_id, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.eval_id, iteration.iteration_number,
                    iteration.approach_tried, iteration.result,
                    iteration.insight_gained, iteration.duration_ms,
                    iteration.memory_entity_id, iteration.timestamp
                ))

    def get_eval_history(
        self,
        task_filter: str = None,
        outcome_filter: WiggumOutcome = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical evaluation results"""
        import sqlite3

        query = "SELECT * FROM wiggum_evals WHERE 1=1"
        params = []

        if task_filter:
            query += " AND task LIKE ?"
            params.append(f"%{task_filter}%")

        if outcome_filter:
            query += " AND outcome = ?"
            params.append(outcome_filter.value)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute(query, params).fetchall()
            return [dict(r) for r in results]

    def get_learning_insights(self, task_keywords: str = None) -> List[Dict[str, Any]]:
        """Get insights from past Wiggum evaluations"""
        insights = []

        for learning_file in WIGGUM_LEARNINGS_DIR.glob("*.json"):
            try:
                with open(learning_file) as f:
                    learning = json.load(f)

                if task_keywords:
                    task_obs = [o for o in learning.get('observations', [])
                               if o.startswith('task:')]
                    if not any(task_keywords.lower() in o.lower() for o in task_obs):
                        continue

                # Extract insight
                insight_obs = [o for o in learning.get('observations', [])
                              if o.startswith('insight:')]
                if insight_obs:
                    insights.append({
                        'name': learning['name'],
                        'insight': insight_obs[0].replace('insight: ', ''),
                        'file': str(learning_file)
                    })
            except Exception as e:
                logger.warning(f"Failed to read learning file: {e}")

        return insights

    def get_eval_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics from evaluations"""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            # Overall stats
            total = conn.execute("SELECT COUNT(*) FROM wiggum_evals").fetchone()[0]

            if total == 0:
                return {'total_evals': 0, 'message': 'No evaluations yet'}

            success = conn.execute(
                "SELECT COUNT(*) FROM wiggum_evals WHERE outcome = 'success'"
            ).fetchone()[0]

            avg_iterations = conn.execute(
                "SELECT AVG(total_iterations) FROM wiggum_evals"
            ).fetchone()[0]

            avg_quality = conn.execute(
                "SELECT AVG(quality_score) FROM wiggum_evals WHERE outcome = 'success'"
            ).fetchone()[0]

            avg_duration = conn.execute(
                "SELECT AVG(total_duration_ms) FROM wiggum_evals"
            ).fetchone()[0]

            # By outcome
            outcomes = {}
            for row in conn.execute(
                "SELECT outcome, COUNT(*) FROM wiggum_evals GROUP BY outcome"
            ):
                outcomes[row[0]] = row[1]

            return {
                'total_evals': total,
                'success_rate': success / total if total > 0 else 0,
                'avg_iterations': avg_iterations or 0,
                'avg_quality_score': avg_quality or 0,
                'avg_duration_ms': avg_duration or 0,
                'outcomes': outcomes,
                'total_learnings': sum(1 for _ in WIGGUM_LEARNINGS_DIR.glob("*.json"))
            }


# Integration with Darwin-Gödel Machine
class WiggumDarwinGodelIntegration:
    """
    Integrates Wiggum loops with Darwin-Gödel Machine for
    verified self-improvement with guaranteed completion.
    """

    def __init__(self):
        self.wiggum_eval = WiggumEvalIntegration()
        self._dgm = None

    @property
    def dgm(self):
        """Lazy load Darwin-Gödel Machine"""
        if self._dgm is None:
            try:
                from darwin_godel_machine import DarwinGodelMachine
                self._dgm = DarwinGodelMachine()
            except ImportError:
                logger.warning("Darwin-Gödel Machine not available")
        return self._dgm

    async def verified_self_improvement(
        self,
        improvement_description: str,
        expected_gain: float,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Execute self-improvement with Wiggum loop for guaranteed completion
        and Darwin-Gödel verification for provable correctness.

        Args:
            improvement_description: What improvement to make
            expected_gain: Expected performance improvement (0.0-1.0)
            max_iterations: Max attempts in Wiggum loop

        Returns:
            Combined result with Wiggum metrics and proof status
        """
        async def improvement_executor(iteration: int):
            """Execute one improvement attempt"""
            if not self.dgm:
                return False, "Darwin-Gödel Machine not available", "DGM import failed"

            try:
                # Propose modification
                modification = await self.dgm.propose_modification(
                    improvement_description,
                    expected_gain
                )

                # Verify proof
                proof_valid = await self.dgm.verify_proof(modification)

                if not proof_valid:
                    return False, None, f"Proof invalid for iteration {iteration}"

                # Apply and measure
                result = await self.dgm.apply_modification(modification)

                if result.get('success'):
                    return True, json.dumps(result), f"Improvement applied: {result.get('actual_gain', 0):.2%} gain"
                else:
                    return False, None, f"Application failed: {result.get('error', 'unknown')}"

            except Exception as e:
                return False, None, f"Error in iteration {iteration}: {str(e)}"

        # Run with Wiggum evaluation
        result = await self.wiggum_eval.evaluate_with_wiggum(
            task=f"Self-improvement: {improvement_description}",
            success_criteria=f"Achieve {expected_gain:.0%} performance gain with verified proof",
            task_executor=improvement_executor,
            max_iterations=max_iterations,
            criteria_name='self_improvement',
            ember_context="darwin_godel_self_improvement"
        )

        return {
            'wiggum_result': asdict(result),
            'improvement_description': improvement_description,
            'expected_gain': expected_gain,
            'achieved': result.outcome == WiggumOutcome.SUCCESS,
            'iterations_needed': result.total_iterations,
            'insights': result.key_insights
        }


# Command-line interface
async def main():
    """Test Wiggum eval integration"""
    import argparse

    parser = argparse.ArgumentParser(description='Wiggum Eval Integration')
    parser.add_argument('--test', action='store_true', help='Run test evaluation')
    parser.add_argument('--stats', action='store_true', help='Show eval statistics')
    parser.add_argument('--history', action='store_true', help='Show eval history')
    args = parser.parse_args()

    evaluator = WiggumEvalIntegration()

    if args.stats:
        stats = evaluator.get_eval_statistics()
        print(json.dumps(stats, indent=2))
        return

    if args.history:
        history = evaluator.get_eval_history(limit=10)
        for h in history:
            print(f"[{h['outcome']}] {h['task'][:50]}... ({h['total_iterations']} iters)")
        return

    if args.test:
        # Simple test task
        iteration_count = [0]

        async def test_executor(iteration: int):
            iteration_count[0] = iteration
            # Succeed on 3rd iteration
            if iteration >= 3:
                return True, "Test completed successfully", "Third time's the charm"
            return False, None, f"Attempt {iteration} failed, trying again"

        result = await evaluator.evaluate_with_wiggum(
            task="Test task: succeed on third iteration",
            success_criteria="Complete the test",
            task_executor=test_executor,
            max_iterations=5,
            criteria_name='self_healing'
        )

        print(f"\n=== Wiggum Eval Test Result ===")
        print(f"Outcome: {result.outcome.value}")
        print(f"Iterations: {result.total_iterations}")
        print(f"Ember Approved: {result.ember_approved}")
        print(f"Quality Score: {result.quality_score:.2f}")
        print(f"Learnings Stored: {result.learnings_stored}")
        print(f"Duration: {result.total_duration_ms:.1f}ms")
        print(f"\nInsights:")
        for insight in result.key_insights:
            print(f"  - {insight}")

        # Evaluate against criteria
        criteria = evaluator.criteria['self_healing']
        eval_scores = criteria.evaluate(result)
        print(f"\n=== Criteria Evaluation ===")
        print(f"Passed: {eval_scores['passed']}")
        print(f"Total Score: {eval_scores['total_score']:.2f}")
        print(f"Components: {json.dumps(eval_scores['component_scores'], indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
