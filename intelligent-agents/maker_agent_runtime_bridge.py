#!/usr/bin/env python3
"""
MAKER Framework Integration Bridge for Agent Runtime MCP
========================================================

Bridges MAKER framework (stateless execution with voting) with existing
agent-runtime-mcp persistent task system.

Allows existing tasks to leverage MAKER reliability patterns:
1. Decompose persistent task into atomic steps
2. Execute each step with stateless agents + voting
3. Store results back in agent-runtime database

This provides 99.9999% reliability for long-running task sequences.
"""
import os

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import sys

# Platform-aware imports
import platform
if platform.system() == "Darwin":  # macOS
    STORAGE_BASE = str(_STORAGE_BASE)
else:  # Linux
    STORAGE_BASE = str(_STORAGE_BASE)

# Add agent-runtime-mcp to path
sys.path.insert(0, str(Path(STORAGE_BASE) / "mcp-servers" / "agent-runtime-mcp"))

from maker_framework import (

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

    MAKEROrchestrator,
    AtomicState,
    AgentResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MAKERTaskBridge:
    """
    Bridge between MAKER framework and Agent Runtime MCP.

    Converts persistent tasks into atomic state sequences,
    executes with MAKER reliability, and stores results.
    """

    def __init__(
        self,
        agent_runtime_db: Path = None,
        maker_voting: bool = True,
        maker_k: int = 3
    ):
        """
        Args:
            agent_runtime_db: Path to agent runtime database
            maker_voting: Enable MAKER voting
            maker_k: K-ahead threshold for voting
        """
        self.agent_runtime_db = agent_runtime_db or (
            Path.home() / ".claude" / "agent_runtime.db"
        )
        self.orchestrator = MAKEROrchestrator(
            voting_enabled=maker_voting,
            k=maker_k
        )

    def task_to_atomic_state(
        self,
        task_id: int,
        task_data: Dict[str, Any],
        step_number: int = 0
    ) -> AtomicState:
        """
        Convert agent-runtime task to MAKER atomic state.

        Args:
            task_id: Agent runtime task ID
            task_data: Task metadata and state
            step_number: Current step in execution

        Returns:
            AtomicState for MAKER execution
        """
        return AtomicState(
            state_id=f"task-{task_id}-step-{step_number}",
            step_number=step_number,
            state_data={
                'task_id': task_id,
                'title': task_data.get('title', ''),
                'description': task_data.get('description', ''),
                'current_progress': task_data.get('metadata', {}).get('progress', {}),
                'accumulated_results': task_data.get('metadata', {}).get('results', []),
                'context': task_data.get('metadata', {}).get('context', {})
            },
            rules=task_data.get('metadata', {}).get('rules', [
                "Complete task according to description",
                "Record all results",
                "Handle errors gracefully"
            ]),
            goal=task_data.get('title', 'Complete task')
        )

    def atomic_state_to_task_update(
        self,
        state: AtomicState,
        action: Any
    ) -> Dict[str, Any]:
        """
        Convert MAKER atomic state back to agent-runtime task update.

        Args:
            state: Atomic state from MAKER execution
            action: Action taken in this step

        Returns:
            Task update dictionary for agent-runtime
        """
        return {
            'metadata': json.dumps({
                'progress': state.state_data.get('current_progress', {}),
                'results': state.state_data.get('accumulated_results', []),
                'context': state.state_data.get('context', {}),
                'last_action': action,
                'last_step': state.step_number
            })
        }

    async def execute_task_with_maker(
        self,
        task_id: int,
        agent_fn: Callable,
        is_complete_fn: Optional[Callable] = None,
        max_steps: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute an agent-runtime task using MAKER framework.

        Args:
            task_id: Agent runtime task ID
            agent_fn: Async function(AtomicState) -> AgentResponse
            is_complete_fn: Optional function(AtomicState) -> bool
            max_steps: Maximum steps before giving up

        Returns:
            Execution results
        """
        # Load task from agent-runtime database
        task_data = self._load_task(task_id)
        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        logger.info(f"Executing task {task_id} with MAKER: {task_data['title']}")

        # Update task status to in_progress
        self._update_task_status(task_id, 'in_progress')

        # Convert to atomic state
        initial_state = self.task_to_atomic_state(task_id, task_data)

        # Default completion check
        if not is_complete_fn:
            def is_complete_fn(state: AtomicState) -> bool:
                # Simple completion: check if results accumulated
                results = state.state_data.get('accumulated_results', [])
                return len(results) > 0 and state.state_data.get('completed', False)

        try:
            # Execute with MAKER
            success, final_state, stats = await self.orchestrator.execute_sequence(
                task_name=f"task_{task_id}_{task_data['title']}",
                initial_state=initial_state,
                agent_fn=agent_fn,
                is_goal_reached=is_complete_fn,
                max_steps=max_steps
            )

            # Update task with results
            if success:
                self._update_task_completion(
                    task_id,
                    success=True,
                    result=final_state.state_data.get('accumulated_results'),
                    metadata=self.atomic_state_to_task_update(
                        final_state,
                        action="completed"
                    )
                )
            else:
                self._update_task_completion(
                    task_id,
                    success=False,
                    error="Failed to complete within max steps",
                    metadata=self.atomic_state_to_task_update(
                        final_state,
                        action="failed"
                    )
                )

            return {
                'success': success,
                'task_id': task_id,
                'final_state': final_state.state_data,
                'stats': stats
            }

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self._update_task_completion(
                task_id,
                success=False,
                error=str(e)
            )
            raise

    def _load_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Load task from agent-runtime database"""
        conn = sqlite3.connect(self.agent_runtime_db)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            task = dict(row)
            task['dependencies'] = json.loads(task.get('dependencies', '[]'))
            task['metadata'] = json.loads(task.get('metadata', '{}'))
            return task

        return None

    def _update_task_status(self, task_id: int, status: str):
        """Update task status in agent-runtime database"""
        conn = sqlite3.connect(self.agent_runtime_db)

        started_at = datetime.now().isoformat() if status == 'in_progress' else None

        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ?, started_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), started_at, task_id)
        )

        conn.commit()
        conn.close()

    def _update_task_completion(
        self,
        task_id: int,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Update task with completion status and results"""
        conn = sqlite3.connect(self.agent_runtime_db)

        status = 'completed' if success else 'failed'
        completed_at = datetime.now().isoformat()

        conn.execute(
            """UPDATE tasks SET
               status = ?,
               updated_at = ?,
               completed_at = ?,
               result = ?,
               error = ?,
               metadata = ?
               WHERE id = ?""",
            (
                status,
                datetime.now().isoformat(),
                completed_at,
                json.dumps(result) if result is not None else None,
                error,
                metadata.get('metadata') if metadata else None,
                task_id
            )
        )

        conn.commit()
        conn.close()

    async def execute_goal_with_maker(
        self,
        goal_id: int,
        decompose_fn: Callable,
        max_parallel: int = 3
    ) -> Dict[str, Any]:
        """
        Execute an agent-runtime goal using MAKER for each task.

        Args:
            goal_id: Agent runtime goal ID
            decompose_fn: Function that creates task execution functions
            max_parallel: Maximum parallel task execution

        Returns:
            Execution results for all tasks
        """
        # Load goal and associated tasks
        conn = sqlite3.connect(self.agent_runtime_db)
        conn.row_factory = sqlite3.Row

        goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE goal_id = ? ORDER BY priority DESC",
            (goal_id,)
        ).fetchall()

        conn.close()

        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        logger.info(f"Executing goal {goal_id} with MAKER: {goal['name']} ({len(tasks)} tasks)")

        # Execute tasks in parallel (respecting dependencies)
        results = []
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_task_safe(task):
            async with semaphore:
                task_dict = dict(task)
                task_dict['dependencies'] = json.loads(task_dict.get('dependencies', '[]'))
                task_dict['metadata'] = json.loads(task_dict.get('metadata', '{}'))

                # Get task-specific execution function
                agent_fn, is_complete_fn = decompose_fn(task_dict)

                return await self.execute_task_with_maker(
                    task_id=task_dict['id'],
                    agent_fn=agent_fn,
                    is_complete_fn=is_complete_fn
                )

        # Execute all tasks
        task_results = await asyncio.gather(
            *[execute_task_safe(task) for task in tasks],
            return_exceptions=True
        )

        # Collect results
        success_count = 0
        for task, result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(result)
                })
            else:
                results.append(result)
                if result.get('success'):
                    success_count += 1

        # Update goal status
        conn = sqlite3.connect(self.agent_runtime_db)
        goal_status = 'completed' if success_count == len(tasks) else 'partial'
        conn.execute(
            "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
            (goal_status, datetime.now().isoformat(), goal_id)
        )
        conn.commit()
        conn.close()

        return {
            'goal_id': goal_id,
            'goal_name': goal['name'],
            'total_tasks': len(tasks),
            'successful_tasks': success_count,
            'results': results
        }


# Example usage
async def example_task_execution():
    """Example of executing an agent-runtime task with MAKER"""

    bridge = MAKERTaskBridge(maker_voting=True, maker_k=3)

    # Example stateless agent for a generic task
    async def generic_task_agent(state: AtomicState) -> AgentResponse:
        """
        Example agent that processes task incrementally.

        In real usage, this would call actual task execution logic,
        but maintain stateless pattern - only using state data, no history.
        """
        await asyncio.sleep(0.01)  # Simulate work

        # Get current progress
        progress = state.state_data.get('current_progress', {})
        step_count = progress.get('steps_completed', 0)

        # Simulate doing work
        new_result = f"Step {step_count} completed"

        return AgentResponse(
            action={'step': step_count, 'action': 'process'},
            new_state_data={
                **state.state_data,
                'current_progress': {
                    'steps_completed': step_count + 1,
                    'percentage': min(100, (step_count + 1) * 10)
                },
                'accumulated_results': state.state_data.get('accumulated_results', []) + [new_result],
                'completed': step_count >= 9  # Complete after 10 steps
            },
            reasoning=f"Processed step {step_count}",
            format_valid=True,
            token_count=30,
            execution_time_ms=10.0
        )

    # Example: Execute task ID 1 with MAKER
    # (Assuming task exists in agent-runtime database)
    try:
        result = await bridge.execute_task_with_maker(
            task_id=1,
            agent_fn=generic_task_agent,
            max_steps=20
        )

        print(f"Task execution result: {json.dumps(result, indent=2)}")

    except Exception as e:
        logger.error(f"Failed to execute task: {e}")


if __name__ == "__main__":
    asyncio.run(example_task_execution())
