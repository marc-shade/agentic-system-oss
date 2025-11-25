#!/usr/bin/env python3
"""
Continuous Evaluation Runner
============================

Runs evaluations continuously on agent outputs, feeding results back to
the self-improvement system.

Features:
- Queue-based evaluation processing
- Real-time grading of agent outputs
- Integration with Meta-Learning for feedback
- Integration with Darwin-Gödel for improvement tracking
- Prometheus metrics export
"""

import asyncio
import json
import logging
import os
import sys
import time
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from collections import deque
import threading
import sqlite3

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "graders"))
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

# Import graders
from code_grader import grade_code
from reasoning_grader import grade_reasoning
from safety_grader import grade_safety
from agent_coordination_grader import grade_coordination

# Import AGI components
try:
    from meta_learning_engine import MetaLearningEngine, TaskOutcome
    from darwin_godel_machine import DarwinGodelMachine
    META_LEARNING_AVAILABLE = True
except ImportError:
    META_LEARNING_AVAILABLE = False
    logging.warning("Meta-learning engine not available")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EvalRequest:
    """Request for evaluation."""
    request_id: str
    eval_type: str  # code, reasoning, safety, coordination
    content: str
    context: Dict[str, Any]
    agent_id: str
    task_id: str
    timestamp: str


@dataclass
class EvalResult:
    """Result of evaluation."""
    request_id: str
    eval_type: str
    overall_score: float
    passed: bool
    dimensions: Dict[str, Any]
    violations: List[Dict] = None
    timestamp: str = None
    processing_time_ms: float = 0


class EvalQueue:
    """Thread-safe evaluation queue."""

    def __init__(self, maxsize: int = 1000):
        self.queue = deque(maxlen=maxsize)
        self.lock = threading.Lock()
        self.processed_count = 0
        self.failed_count = 0

    def push(self, request: EvalRequest) -> bool:
        with self.lock:
            if len(self.queue) >= self.queue.maxlen:
                return False
            self.queue.append(request)
            return True

    def pop(self) -> Optional[EvalRequest]:
        with self.lock:
            if self.queue:
                return self.queue.popleft()
            return None

    def size(self) -> int:
        with self.lock:
            return len(self.queue)


class ContinuousEvalRunner:
    """
    Continuous evaluation runner with feedback integration.
    """

    def __init__(
        self,
        suites_dir: str = None,
        db_path: str = None,
        enable_feedback: bool = True
    ):
        self.suites_dir = Path(suites_dir or Path(__file__).parent / "suites")
        self.db_path = db_path or str(Path(__file__).parent / "eval_results.db")

        self.queue = EvalQueue()
        self.running = False
        self.worker_thread = None

        # Load eval suites
        self.suites = self._load_suites()

        # Grader mapping
        self.graders = {
            'code': grade_code,
            'reasoning': grade_reasoning,
            'safety': grade_safety,
            'coordination': grade_coordination
        }

        # Initialize database
        self._init_db()

        # Initialize feedback components
        self.enable_feedback = enable_feedback and META_LEARNING_AVAILABLE
        if self.enable_feedback:
            self.meta_learning = MetaLearningEngine()
            self.darwin_godel = DarwinGodelMachine()
            logger.info("Feedback loop enabled with Meta-Learning and Darwin-Gödel")
        else:
            self.meta_learning = None
            self.darwin_godel = None

        # Metrics
        self.metrics = {
            'total_evals': 0,
            'passed_evals': 0,
            'failed_evals': 0,
            'avg_score': 0.0,
            'by_type': {}
        }

    def _load_suites(self) -> Dict[str, Dict]:
        """Load evaluation suite configurations."""
        suites = {}
        if self.suites_dir.exists():
            for yaml_file in self.suites_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        suite = yaml.safe_load(f)
                        suites[suite['name']] = suite
                        logger.info(f"Loaded eval suite: {suite['name']}")
                except Exception as e:
                    logger.error(f"Failed to load suite {yaml_file}: {e}")
        return suites

    def _init_db(self):
        """Initialize SQLite database for results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                eval_type TEXT,
                agent_id TEXT,
                task_id TEXT,
                overall_score REAL,
                passed INTEGER,
                dimensions TEXT,
                violations TEXT,
                processing_time_ms REAL,
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_eval_type ON eval_results(eval_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_id ON eval_results(agent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON eval_results(created_at)
        """)

        conn.commit()
        conn.close()

    def submit(
        self,
        eval_type: str,
        content: str,
        agent_id: str = "unknown",
        task_id: str = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Submit content for evaluation.

        Args:
            eval_type: Type of evaluation (code, reasoning, safety, coordination)
            content: Content to evaluate
            agent_id: ID of the agent that produced this content
            task_id: Associated task ID
            context: Additional context

        Returns:
            Request ID for tracking
        """
        import uuid
        request_id = str(uuid.uuid4())

        request = EvalRequest(
            request_id=request_id,
            eval_type=eval_type,
            content=content,
            context=context or {},
            agent_id=agent_id,
            task_id=task_id or request_id,
            timestamp=datetime.now().isoformat()
        )

        if self.queue.push(request):
            logger.debug(f"Submitted eval request {request_id}")
            return request_id
        else:
            logger.warning("Eval queue full, request dropped")
            return None

    def evaluate(self, request: EvalRequest) -> EvalResult:
        """
        Evaluate a single request.
        """
        start_time = time.time()

        grader = self.graders.get(request.eval_type)
        if not grader:
            logger.error(f"Unknown eval type: {request.eval_type}")
            return EvalResult(
                request_id=request.request_id,
                eval_type=request.eval_type,
                overall_score=0.0,
                passed=False,
                dimensions={},
                timestamp=datetime.now().isoformat(),
                processing_time_ms=0
            )

        try:
            # Run the appropriate grader
            if request.eval_type == 'code':
                result = grader(
                    request.content,
                    test_cases=request.context.get('test_cases')
                )
            elif request.eval_type == 'reasoning':
                result = grader(
                    request.content,
                    expected_aspects=request.context.get('expected_aspects'),
                    ground_truth=request.context.get('ground_truth')
                )
            elif request.eval_type == 'safety':
                result = grader(
                    request.content,
                    context=request.context.get('task_context'),
                    guidelines=request.context.get('guidelines')
                )
            elif request.eval_type == 'coordination':
                result = grader(
                    log=request.content,
                    expected_agents=request.context.get('expected_agents'),
                    expected_outcomes=request.context.get('expected_outcomes')
                )
            else:
                result = grader(request.content)

            processing_time = (time.time() - start_time) * 1000

            eval_result = EvalResult(
                request_id=request.request_id,
                eval_type=request.eval_type,
                overall_score=result.get('overall_score', 0.0),
                passed=result.get('passed', False),
                dimensions=result.get('dimensions', {}),
                violations=result.get('violations', []),
                timestamp=datetime.now().isoformat(),
                processing_time_ms=processing_time
            )

            return eval_result

        except Exception as e:
            logger.error(f"Evaluation failed for {request.request_id}: {e}")
            return EvalResult(
                request_id=request.request_id,
                eval_type=request.eval_type,
                overall_score=0.0,
                passed=False,
                dimensions={'error': str(e)},
                timestamp=datetime.now().isoformat(),
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _save_result(self, request: EvalRequest, result: EvalResult):
        """Save evaluation result to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO eval_results
                (request_id, eval_type, agent_id, task_id, overall_score,
                 passed, dimensions, violations, processing_time_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.request_id,
                result.eval_type,
                request.agent_id,
                request.task_id,
                result.overall_score,
                1 if result.passed else 0,
                json.dumps(result.dimensions),
                json.dumps(result.violations or []),
                result.processing_time_ms,
                result.timestamp
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save result: {e}")

    def _send_feedback(self, request: EvalRequest, result: EvalResult):
        """Send evaluation result to meta-learning for feedback."""
        if not self.enable_feedback or not self.meta_learning:
            return

        try:
            outcome = TaskOutcome(
                task_id=request.task_id,
                task_type=f"eval_{request.eval_type}",
                agent_used=request.agent_id,
                success=result.passed,
                execution_time_ms=int(result.processing_time_ms),
                error_message=None if result.passed else f"Score: {result.overall_score:.2f}",
                quality_score=result.overall_score,
                timestamp=datetime.now(),
                context={
                    'eval_type': request.eval_type,
                    'dimensions': result.dimensions,
                    'violations': len(result.violations or [])
                }
            )

            self.meta_learning.record_outcome(outcome)
            logger.debug(f"Sent feedback for {request.task_id}")

        except Exception as e:
            logger.error(f"Failed to send feedback: {e}")

    def _update_metrics(self, result: EvalResult):
        """Update running metrics."""
        self.metrics['total_evals'] += 1

        if result.passed:
            self.metrics['passed_evals'] += 1
        else:
            self.metrics['failed_evals'] += 1

        # Update running average
        n = self.metrics['total_evals']
        old_avg = self.metrics['avg_score']
        self.metrics['avg_score'] = old_avg + (result.overall_score - old_avg) / n

        # Update by-type metrics
        if result.eval_type not in self.metrics['by_type']:
            self.metrics['by_type'][result.eval_type] = {
                'count': 0,
                'passed': 0,
                'avg_score': 0.0
            }

        type_metrics = self.metrics['by_type'][result.eval_type]
        type_metrics['count'] += 1
        if result.passed:
            type_metrics['passed'] += 1
        m = type_metrics['count']
        type_metrics['avg_score'] = type_metrics['avg_score'] + (result.overall_score - type_metrics['avg_score']) / m

    def _worker_loop(self):
        """Worker loop for processing evaluation queue."""
        logger.info("Eval worker started")

        while self.running:
            request = self.queue.pop()

            if request:
                result = self.evaluate(request)
                self._save_result(request, result)
                self._send_feedback(request, result)
                self._update_metrics(result)

                if not result.passed:
                    logger.warning(
                        f"Eval failed: {request.eval_type} by {request.agent_id} "
                        f"(score: {result.overall_score:.2f})"
                    )
            else:
                # No requests, sleep briefly
                time.sleep(0.1)

        logger.info("Eval worker stopped")

    def start(self):
        """Start the continuous evaluation runner."""
        if self.running:
            logger.warning("Runner already started")
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Continuous eval runner started")

    def stop(self):
        """Stop the runner."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Continuous eval runner stopped")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            'queue_size': self.queue.size(),
            'running': self.running
        }

    def get_results(
        self,
        eval_type: str = None,
        agent_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query evaluation results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM eval_results WHERE 1=1"
        params = []

        if eval_type:
            query += " AND eval_type = ?"
            params.append(eval_type)
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        columns = [d[0] for d in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results


# Singleton instance for easy access
_runner_instance = None


def get_eval_runner() -> ContinuousEvalRunner:
    """Get or create the singleton eval runner."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ContinuousEvalRunner()
    return _runner_instance


def submit_for_eval(
    eval_type: str,
    content: str,
    agent_id: str = "unknown",
    task_id: str = None,
    context: Dict[str, Any] = None
) -> str:
    """Convenience function to submit content for evaluation."""
    runner = get_eval_runner()
    if not runner.running:
        runner.start()
    return runner.submit(eval_type, content, agent_id, task_id, context)


if __name__ == "__main__":
    # Demo usage
    runner = ContinuousEvalRunner()
    runner.start()

    # Submit some test evaluations
    test_code = '''
def fibonacci(n):
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

    test_reasoning = '''
Step 1: First, I analyzed the error logs and found connection timeouts.
Step 2: The timeouts occur during peak hours, suggesting load issues.
Step 3: Therefore, we should implement connection pooling to handle the load.
'''

    # Submit evaluations
    runner.submit('code', test_code, agent_id='coder_1', task_id='test_001')
    runner.submit('reasoning', test_reasoning, agent_id='analyst_1', task_id='test_002')

    # Wait for processing
    time.sleep(2)

    # Get results
    print("\n=== Metrics ===")
    print(json.dumps(runner.get_metrics(), indent=2))

    print("\n=== Recent Results ===")
    for result in runner.get_results(limit=5):
        print(f"  {result['eval_type']}: {result['overall_score']:.2f} ({'PASS' if result['passed'] else 'FAIL'})")

    runner.stop()
