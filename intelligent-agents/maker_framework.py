#!/usr/bin/env python3
"""
MAKER Framework Implementation (Massively Decomposed Agentic Processes)
=======================================================================

Based on paper: https://arxiv.org/abs/2511.09030

Three Core Pillars:
1. Maximal Decomposition - Stateless agents that "die" after each step
2. Red Flagging - Strict validation to catch errors early
3. First-to-K Voting - Parallel queries with statistical confidence

Achieves 1M+ steps with 99.9999% reliability using existing models.
"""
import os

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import Counter
import hashlib

# Platform-aware path
import platform

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

if platform.system() == "Darwin":  # macOS
    STORAGE_BASE = str(_STORAGE_BASE)
else:  # Linux
    STORAGE_BASE = str(_STORAGE_BASE)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(STORAGE_BASE) / "databases" / "maker_framework.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class ExecutionStatus(Enum):
    """Execution status for atomic steps"""
    PENDING = "pending"
    EXECUTING = "executing"
    VALIDATED = "validated"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AtomicState:
    """
    Complete state representation for a single step.
    This is the ONLY memory that matters - no conversation history.
    """
    state_id: str
    step_number: int
    state_data: Dict[str, Any]  # Complete state snapshot
    rules: List[str]  # Immutable rules/constraints
    goal: str  # Current goal for this step
    previous_state_id: Optional[str] = None
    checksum: Optional[str] = None

    def __post_init__(self):
        """Generate checksum for state integrity"""
        if not self.checksum:
            state_str = json.dumps({
                'state_data': self.state_data,
                'rules': self.rules,
                'goal': self.goal
            }, sort_keys=True)
            self.checksum = hashlib.sha256(state_str.encode()).hexdigest()[:16]


@dataclass
class AgentResponse:
    """Response from a stateless agent execution"""
    action: Any  # The action/decision made
    new_state_data: Dict[str, Any]  # Updated state
    reasoning: Optional[str] = None  # Optional explanation
    format_valid: bool = True  # Red flag check
    token_count: int = 0  # Red flag check
    execution_time_ms: float = 0.0


class RedFlagValidator:
    """
    Validates agent outputs for signs of confusion/errors.

    Key insight: Models make syntax errors BEFORE logic errors.
    Reject malformed outputs as proxy for logic errors.
    """

    def __init__(
        self,
        expected_format: str = "json",
        max_tokens: int = 500,
        max_execution_ms: float = 5000.0
    ):
        self.expected_format = expected_format
        self.max_tokens = max_tokens
        self.max_execution_ms = max_execution_ms

    def validate(self, response: AgentResponse) -> tuple[bool, Optional[str]]:
        """
        Validate response for red flags.

        Returns:
            (is_valid, error_message)
        """
        # Check format validity
        if not response.format_valid:
            return False, "Format validation failed - wrong output type"

        # Check token count (excessive verbosity = confusion)
        if response.token_count > self.max_tokens:
            return False, f"Excessive tokens: {response.token_count} > {self.max_tokens}"

        # Check execution time (timeout = complexity issue)
        if response.execution_time_ms > self.max_execution_ms:
            return False, f"Execution timeout: {response.execution_time_ms}ms > {self.max_execution_ms}ms"

        # Validate action is not None
        if response.action is None:
            return False, "No action provided"

        # Validate new state exists
        if not response.new_state_data:
            return False, "No state update provided"

        return True, None


class FirstToKVoting:
    """
    First-to-K-Ahead voting algorithm based on gambler's ruin problem.

    Runs parallel queries and uses statistical confidence to select winner.
    Can push 80% accurate model to 99.9999% system accuracy.
    """

    def __init__(self, k: int = 3, max_queries: int = 20):
        """
        Args:
            k: Lead required to win (default: 3)
            max_queries: Maximum parallel queries before forcing decision
        """
        self.k = k
        self.max_queries = max_queries

    async def vote(
        self,
        state: AtomicState,
        agent_fn: Callable,
        validator: RedFlagValidator
    ) -> tuple[AgentResponse, Dict[str, Any]]:
        """
        Execute parallel queries and vote on best response.

        Args:
            state: Current atomic state
            agent_fn: Async function that executes agent and returns AgentResponse
            validator: Red flag validator

        Returns:
            (winning_response, voting_stats)
        """
        responses: List[AgentResponse] = []
        vote_counts: Counter = Counter()
        rejected_count = 0

        logger.info(f"Starting First-to-K voting (k={self.k}) for step {state.step_number}")

        # Execute queries in parallel batches
        for batch_num in range(self.max_queries // 5 + 1):
            batch_size = min(5, self.max_queries - len(responses))
            if batch_size <= 0:
                break

            # Execute batch in parallel
            batch_tasks = [agent_fn(state) for _ in range(batch_size)]
            batch_responses = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Validate and count votes
            for resp in batch_responses:
                if isinstance(resp, Exception):
                    logger.warning(f"Agent execution failed: {resp}")
                    continue

                # Validate with red flag checker
                is_valid, error = validator.validate(resp)
                if not is_valid:
                    rejected_count += 1
                    logger.debug(f"Response rejected: {error}")
                    continue

                # Valid response - count vote
                responses.append(resp)
                action_key = self._serialize_action(resp.action)
                vote_counts[action_key] += 1

                # Check if we have a winner (K-ahead)
                if len(vote_counts) >= 2:
                    sorted_votes = vote_counts.most_common(2)
                    leader_votes = sorted_votes[0][1]
                    second_votes = sorted_votes[1][1] if len(sorted_votes) > 1 else 0

                    if leader_votes - second_votes >= self.k:
                        winning_action_key = sorted_votes[0][0]
                        winning_response = next(
                            r for r in responses
                            if self._serialize_action(r.action) == winning_action_key
                        )

                        stats = {
                            'total_queries': len(responses),
                            'rejected': rejected_count,
                            'vote_distribution': dict(vote_counts),
                            'confidence': leader_votes / len(responses),
                            'early_termination': True
                        }

                        logger.info(f"Early winner: {leader_votes} votes (k-ahead={self.k})")
                        return winning_response, stats

        # No early winner - use majority
        if vote_counts:
            winning_action_key = vote_counts.most_common(1)[0][0]
            winning_response = next(
                r for r in responses
                if self._serialize_action(r.action) == winning_action_key
            )

            stats = {
                'total_queries': len(responses),
                'rejected': rejected_count,
                'vote_distribution': dict(vote_counts),
                'confidence': vote_counts[winning_action_key] / len(responses),
                'early_termination': False
            }

            logger.info(f"Majority winner: {vote_counts[winning_action_key]} votes")
            return winning_response, stats

        raise RuntimeError(f"No valid responses after {self.max_queries} queries")

    def _serialize_action(self, action: Any) -> str:
        """Serialize action for vote counting"""
        if isinstance(action, dict):
            return json.dumps(action, sort_keys=True)
        return str(action)


class MAKEROrchestrator:
    """
    Main MAKER framework orchestrator.

    Executes long sequences of steps with maximal decomposition,
    red flagging, and voting for reliability.
    """

    def __init__(
        self,
        db_path: Path = DB_PATH,
        k: int = 3,
        voting_enabled: bool = True,
        red_flag_enabled: bool = True
    ):
        self.db_path = db_path
        self.k = k
        self.voting_enabled = voting_enabled
        self.red_flag_enabled = red_flag_enabled

        self._init_database()
        self.validator = RedFlagValidator()
        self.voter = FirstToKVoting(k=k)

    def _init_database(self):
        """Initialize execution tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Execution traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_traces (
                trace_id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                total_steps INTEGER NOT NULL,
                completed_steps INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT
            )
        """)

        # Step executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS step_executions (
                execution_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                state_id TEXT NOT NULL,
                state_checksum TEXT NOT NULL,
                action TEXT NOT NULL,
                voting_stats TEXT,
                validation_passed BOOLEAN NOT NULL,
                execution_time_ms REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (trace_id) REFERENCES execution_traces(trace_id)
            )
        """)

        conn.commit()
        conn.close()

    async def execute_sequence(
        self,
        task_name: str,
        initial_state: AtomicState,
        agent_fn: Callable,
        is_goal_reached: Callable[[AtomicState], bool],
        max_steps: int = 1000000
    ) -> tuple[bool, AtomicState, Dict[str, Any]]:
        """
        Execute a sequence of steps until goal is reached.

        Args:
            task_name: Name of the task
            initial_state: Starting state
            agent_fn: Async function(state) -> AgentResponse
            is_goal_reached: Function(state) -> bool to check completion
            max_steps: Maximum steps before giving up

        Returns:
            (success, final_state, execution_stats)
        """
        trace_id = hashlib.sha256(
            f"{task_name}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Record execution start
        self._record_trace_start(trace_id, task_name, max_steps)

        current_state = initial_state
        stats = {
            'total_steps': 0,
            'rejected_steps': 0,
            'total_queries': 0,
            'total_execution_time_ms': 0.0,
            'voting_confidence': []
        }

        logger.info(f"Starting MAKER execution: {task_name} (trace={trace_id})")

        try:
            for step_num in range(max_steps):
                current_state.step_number = step_num

                step_start = datetime.now()

                # Execute step with voting if enabled
                if self.voting_enabled:
                    response, vote_stats = await self.voter.vote(
                        current_state,
                        agent_fn,
                        self.validator
                    )
                    stats['total_queries'] += vote_stats['total_queries']
                    stats['rejected_steps'] += vote_stats['rejected']
                    stats['voting_confidence'].append(vote_stats['confidence'])
                else:
                    # Single execution without voting
                    response = await agent_fn(current_state)

                    if self.red_flag_enabled:
                        is_valid, error = self.validator.validate(response)
                        if not is_valid:
                            stats['rejected_steps'] += 1
                            logger.warning(f"Step {step_num} rejected: {error}")
                            continue

                    vote_stats = None

                step_time_ms = (datetime.now() - step_start).total_seconds() * 1000
                stats['total_execution_time_ms'] += step_time_ms

                # Create new state (old agent "dies" here)
                new_state = AtomicState(
                    state_id=f"{trace_id}-{step_num+1}",
                    step_number=step_num + 1,
                    state_data=response.new_state_data,
                    rules=current_state.rules,
                    goal=current_state.goal,
                    previous_state_id=current_state.state_id
                )

                # Record step execution
                self._record_step_execution(
                    trace_id=trace_id,
                    step_number=step_num,
                    state=new_state,
                    action=response.action,
                    voting_stats=vote_stats,
                    execution_time_ms=step_time_ms
                )

                stats['total_steps'] = step_num + 1

                # Check if goal reached
                if is_goal_reached(new_state):
                    logger.info(f"Goal reached at step {step_num+1}!")
                    self._record_trace_completion(trace_id, success=True)
                    return True, new_state, stats

                # Move to next state (current agent is now "dead")
                current_state = new_state

                # Progress logging
                if (step_num + 1) % 100 == 0:
                    avg_confidence = sum(stats['voting_confidence']) / len(stats['voting_confidence']) if stats['voting_confidence'] else 0
                    logger.info(
                        f"Progress: {step_num+1} steps, "
                        f"avg confidence: {avg_confidence:.3f}, "
                        f"rejected: {stats['rejected_steps']}"
                    )

            # Max steps reached without completing
            logger.warning(f"Max steps ({max_steps}) reached without completing goal")
            self._record_trace_completion(trace_id, success=False, error="max_steps_reached")
            return False, current_state, stats

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            self._record_trace_completion(trace_id, success=False, error=str(e))
            raise

    def _record_trace_start(self, trace_id: str, task_name: str, total_steps: int):
        """Record execution trace start"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO execution_traces (trace_id, task_name, total_steps, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (trace_id, task_name, total_steps, "running", datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _record_trace_completion(self, trace_id: str, success: bool, error: Optional[str] = None):
        """Record execution trace completion"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE execution_traces SET status = ?, completed_at = ?, error = ? WHERE trace_id = ?",
            ("completed" if success else "failed", datetime.now().isoformat(), error, trace_id)
        )
        conn.commit()
        conn.close()

    def _record_step_execution(
        self,
        trace_id: str,
        step_number: int,
        state: AtomicState,
        action: Any,
        voting_stats: Optional[Dict],
        execution_time_ms: float
    ):
        """Record individual step execution"""
        conn = sqlite3.connect(self.db_path)
        execution_id = f"{trace_id}-step-{step_number}"

        conn.execute(
            """INSERT INTO step_executions
               (execution_id, trace_id, step_number, state_id, state_checksum,
                action, voting_stats, validation_passed, execution_time_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                execution_id,
                trace_id,
                step_number,
                state.state_id,
                state.checksum,
                json.dumps(action) if not isinstance(action, str) else action,
                json.dumps(voting_stats) if voting_stats else None,
                True,
                execution_time_ms,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    def get_execution_stats(self, trace_id: str) -> Dict[str, Any]:
        """Get execution statistics for a trace"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get trace info
        trace = conn.execute(
            "SELECT * FROM execution_traces WHERE trace_id = ?",
            (trace_id,)
        ).fetchone()

        # Get step statistics
        steps = conn.execute(
            "SELECT * FROM step_executions WHERE trace_id = ? ORDER BY step_number",
            (trace_id,)
        ).fetchall()

        conn.close()

        if not trace:
            return {}

        return {
            'trace': dict(trace),
            'steps': [dict(s) for s in steps],
            'total_steps': len(steps),
            'avg_execution_time_ms': sum(s['execution_time_ms'] for s in steps) / len(steps) if steps else 0
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_maker():
        """Test MAKER framework with simple sequence"""

        # Define a simple counting task
        initial_state = AtomicState(
            state_id="test-0",
            step_number=0,
            state_data={'count': 0, 'history': []},
            rules=['increment by 1 each step', 'stop at 10'],
            goal='reach count of 10'
        )

        # Simple stateless agent
        async def counting_agent(state: AtomicState) -> AgentResponse:
            await asyncio.sleep(0.01)  # Simulate work

            current_count = state.state_data['count']
            new_count = current_count + 1

            return AgentResponse(
                action={'increment': 1},
                new_state_data={
                    'count': new_count,
                    'history': state.state_data['history'] + [new_count]
                },
                reasoning=f"Incremented {current_count} to {new_count}",
                format_valid=True,
                token_count=50,
                execution_time_ms=10.0
            )

        # Goal check
        def is_goal_reached(state: AtomicState) -> bool:
            return state.state_data['count'] >= 10

        # Execute
        orchestrator = MAKEROrchestrator(voting_enabled=True, k=2)
        success, final_state, stats = await orchestrator.execute_sequence(
            task_name="counting_test",
            initial_state=initial_state,
            agent_fn=counting_agent,
            is_goal_reached=is_goal_reached,
            max_steps=100
        )

        print(f"Success: {success}")
        print(f"Final state: {final_state.state_data}")
        print(f"Stats: {json.dumps(stats, indent=2)}")

    asyncio.run(test_maker())
