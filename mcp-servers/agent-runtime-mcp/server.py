#!/usr/bin/env python3
"""
Agent Runtime MCP Server - Open Source Edition

Persistent task management for AI agents with:
- Goal decomposition
- Task queuing with priorities
- Relay pipelines for complex workflows
- Circuit breaker for fault tolerance

Performance Targets:
- Task Decomposition: 1200ms
- Baton Handoff: 89ms
"""

import asyncio
import logging
import sqlite3
import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

# FastMCP for MCP protocol
from fastmcp import FastMCP

# Configure logging
log_file = Path(__file__).parent / "server.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(str(log_file), mode='a')]
)
logger = logging.getLogger("agent-runtime")

# Database path
DB_PATH = Path.home() / ".claude" / "agent_runtime_oss" / "runtime.db"

# Initialize FastMCP application
app = FastMCP("agent-runtime-oss")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def get_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')

    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            result TEXT,
            error TEXT,
            dependencies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    ''')

    # Relay pipelines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relay_pipelines (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            goal TEXT NOT NULL,
            description TEXT,
            agent_types TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            current_step INTEGER DEFAULT 0,
            token_budget INTEGER DEFAULT 100000,
            tokens_used INTEGER DEFAULT 0,
            baton_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')

    # Relay steps table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relay_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            agent_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            quality_score REAL,
            l_score REAL,
            output_entity_id INTEGER,
            tokens_used INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (pipeline_id) REFERENCES relay_pipelines(id)
        )
    ''')

    # Circuit breakers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS circuit_breakers (
            agent_id TEXT PRIMARY KEY,
            state TEXT DEFAULT 'closed',
            failure_count INTEGER DEFAULT 0,
            last_failure_at TIMESTAMP,
            last_success_at TIMESTAMP,
            opened_at TIMESTAMP,
            failure_threshold INTEGER DEFAULT 5,
            window_seconds INTEGER DEFAULT 60,
            cooldown_seconds INTEGER DEFAULT 300,
            fallback_agent TEXT DEFAULT 'generalist'
        )
    ''')

    # Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_goal ON tasks(goal_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relay_steps_pipeline ON relay_steps(pipeline_id)')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# Initialize database on module load
init_database()


# =============================================================================
# GOAL MANAGEMENT
# =============================================================================

@app.tool()
async def create_goal(
    name: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new goal with name and description. Goals persist across sessions.

    Args:
        name: Short name for the goal
        description: Detailed description of what the goal aims to achieve
        metadata: Optional metadata (tags, context, etc.)

    Returns:
        Goal ID and creation details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO goals (name, description, metadata)
        VALUES (?, ?, ?)
    ''', (name, description, json.dumps(metadata or {})))

    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        'goal_id': goal_id,
        'name': name,
        'status': 'active',
        'message': f"Goal '{name}' created successfully"
    }


@app.tool()
async def get_goal(goal_id: int) -> Dict[str, Any]:
    """
    Get goal details by ID.

    Args:
        goal_id: Goal ID

    Returns:
        Goal details including tasks
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
    goal = cursor.fetchone()

    if not goal:
        conn.close()
        return {'error': f"Goal {goal_id} not found"}

    # Get associated tasks
    cursor.execute('SELECT * FROM tasks WHERE goal_id = ? ORDER BY priority DESC', (goal_id,))
    tasks = [dict(t) for t in cursor.fetchall()]

    conn.close()

    return {
        'id': goal['id'],
        'name': goal['name'],
        'description': goal['description'],
        'status': goal['status'],
        'metadata': json.loads(goal['metadata']) if goal['metadata'] else {},
        'tasks': tasks,
        'task_count': len(tasks),
        'created_at': goal['created_at']
    }


@app.tool()
async def list_goals(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all goals, optionally filtered by status.

    Args:
        status: Optional status filter (active, completed, cancelled)

    Returns:
        List of goals
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute('SELECT * FROM goals WHERE status = ? ORDER BY created_at DESC', (status,))
    else:
        cursor.execute('SELECT * FROM goals ORDER BY created_at DESC')

    goals = []
    for row in cursor.fetchall():
        # Get task counts
        cursor.execute('''
            SELECT status, COUNT(*) as count FROM tasks
            WHERE goal_id = ? GROUP BY status
        ''', (row['id'],))
        task_stats = {r['status']: r['count'] for r in cursor.fetchall()}

        goals.append({
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'status': row['status'],
            'task_stats': task_stats,
            'created_at': row['created_at']
        })

    conn.close()
    return goals


# =============================================================================
# TASK MANAGEMENT
# =============================================================================

@app.tool()
async def create_task(
    title: str,
    description: Optional[str] = None,
    goal_id: Optional[int] = None,
    priority: int = 5,
    dependencies: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Create a new task manually. Tasks persist in queue across sessions.

    Args:
        title: Task title
        description: Detailed task description
        goal_id: Optional goal ID to associate task with
        priority: Priority (1-10, 10 is highest)
        dependencies: Task IDs that must complete before this task

    Returns:
        Task ID and creation details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO tasks (title, description, goal_id, priority, dependencies)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, description, goal_id, priority, json.dumps(dependencies or [])))

    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        'task_id': task_id,
        'title': title,
        'priority': priority,
        'status': 'pending',
        'message': f"Task '{title}' created successfully"
    }


@app.tool()
async def decompose_goal(
    goal_id: int,
    strategy: str = "sequential"
) -> Dict[str, Any]:
    """
    Decompose a goal into tasks using AI. Returns task IDs that were created.

    Args:
        goal_id: ID of the goal to decompose
        strategy: Decomposition strategy (sequential, parallel, hierarchical)

    Returns:
        List of created task IDs
    """
    start_time = time.time()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
    goal = cursor.fetchone()

    if not goal:
        conn.close()
        return {'error': f"Goal {goal_id} not found"}

    # Simple decomposition heuristic (in real system, this would use LLM)
    description = goal['description'] or goal['name']
    words = description.split()

    # Generate tasks based on strategy
    tasks = []
    if strategy == "sequential":
        tasks = [
            f"Analyze requirements for: {goal['name']}",
            f"Design solution for: {goal['name']}",
            f"Implement: {goal['name']}",
            f"Test: {goal['name']}",
            f"Document: {goal['name']}"
        ]
    elif strategy == "parallel":
        tasks = [
            f"Research: {goal['name']}",
            f"Prototype: {goal['name']}",
            f"Review: {goal['name']}"
        ]
    elif strategy == "hierarchical":
        tasks = [
            f"Plan: {goal['name']}",
            f"Execute Phase 1: {goal['name']}",
            f"Execute Phase 2: {goal['name']}",
            f"Integrate: {goal['name']}",
            f"Validate: {goal['name']}"
        ]

    task_ids = []
    for i, task_title in enumerate(tasks):
        priority = 10 - i  # Higher priority for earlier tasks
        deps = [task_ids[-1]] if task_ids and strategy == "sequential" else []

        cursor.execute('''
            INSERT INTO tasks (title, goal_id, priority, dependencies)
            VALUES (?, ?, ?, ?)
        ''', (task_title, goal_id, priority, json.dumps(deps)))
        task_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        'goal_id': goal_id,
        'strategy': strategy,
        'task_ids': task_ids,
        'task_count': len(task_ids),
        'decomposition_time_ms': round(elapsed_ms, 2),
        'message': f"Created {len(task_ids)} tasks for goal '{goal['name']}'"
    }


@app.tool()
async def get_next_task() -> Optional[Dict[str, Any]]:
    """
    Get the next task from the queue (highest priority, dependencies met).

    Returns:
        Next available task or None if queue is empty
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get pending tasks ordered by priority
    cursor.execute('''
        SELECT * FROM tasks WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
    ''')

    for row in cursor.fetchall():
        deps = json.loads(row['dependencies']) if row['dependencies'] else []

        # Check if all dependencies are completed
        deps_met = True
        for dep_id in deps:
            cursor.execute('SELECT status FROM tasks WHERE id = ?', (dep_id,))
            dep = cursor.fetchone()
            if not dep or dep['status'] != 'completed':
                deps_met = False
                break

        if deps_met:
            # Mark as in_progress
            cursor.execute('''
                UPDATE tasks SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row['id'],))
            conn.commit()
            conn.close()

            return {
                'task_id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'goal_id': row['goal_id'],
                'priority': row['priority']
            }

    conn.close()
    return None


@app.tool()
async def update_task_status(
    task_id: int,
    status: str,
    result: Optional[str] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update task status (pending, in_progress, completed, failed, cancelled).

    Args:
        task_id: Task ID to update
        status: New status
        result: Optional result data (for completed tasks)
        error: Optional error message (for failed tasks)

    Returns:
        Updated task status
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
    params = [status]

    if status == 'completed':
        updates.append('completed_at = CURRENT_TIMESTAMP')
    if result:
        updates.append('result = ?')
        params.append(result)
    if error:
        updates.append('error = ?')
        params.append(error)

    params.append(task_id)

    cursor.execute(f'''
        UPDATE tasks SET {', '.join(updates)} WHERE id = ?
    ''', params)

    conn.commit()
    conn.close()

    return {
        'task_id': task_id,
        'status': status,
        'message': f"Task {task_id} updated to {status}"
    }


@app.tool()
async def list_tasks(
    goal_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List tasks, optionally filtered by goal or status.

    Args:
        goal_id: Optional goal ID filter
        status: Optional status filter
        limit: Maximum number of tasks to return

    Returns:
        List of tasks
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if goal_id:
        conditions.append('goal_id = ?')
        params.append(goal_id)
    if status:
        conditions.append('status = ?')
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    cursor.execute(f'''
        SELECT * FROM tasks {where_clause}
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
    ''', params)

    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'goal_id': row['goal_id'],
            'status': row['status'],
            'priority': row['priority'],
            'dependencies': json.loads(row['dependencies']) if row['dependencies'] else [],
            'created_at': row['created_at']
        })

    conn.close()
    return tasks


@app.tool()
async def get_task(task_id: int) -> Dict[str, Any]:
    """
    Get task details by ID.

    Args:
        task_id: Task ID

    Returns:
        Task details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return {'error': f"Task {task_id} not found"}

    return {
        'id': row['id'],
        'title': row['title'],
        'description': row['description'],
        'goal_id': row['goal_id'],
        'status': row['status'],
        'priority': row['priority'],
        'result': row['result'],
        'error': row['error'],
        'dependencies': json.loads(row['dependencies']) if row['dependencies'] else [],
        'created_at': row['created_at'],
        'started_at': row['started_at'],
        'completed_at': row['completed_at']
    }


# =============================================================================
# RELAY PIPELINE (48-Agent Sequential Execution)
# =============================================================================

@app.tool()
async def create_relay_pipeline(
    name: str,
    goal: str,
    agent_types: List[str],
    description: Optional[str] = None,
    token_budget: int = 100000
) -> Dict[str, Any]:
    """
    Create a 48-agent relay race pipeline for sequential execution with structured handoffs.

    Args:
        name: Pipeline name
        goal: High-level goal description
        agent_types: Agent types in execution order (researcher, analyzer, synthesizer, etc.)
        description: Optional detailed description
        token_budget: Total token budget for pipeline

    Returns:
        Pipeline ID and creation details
    """
    pipeline_id = str(uuid.uuid4())[:8]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO relay_pipelines (id, name, goal, description, agent_types, token_budget)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (pipeline_id, name, goal, description, json.dumps(agent_types), token_budget))

    # Create steps
    for i, agent_type in enumerate(agent_types):
        cursor.execute('''
            INSERT INTO relay_steps (pipeline_id, step_index, agent_type)
            VALUES (?, ?, ?)
        ''', (pipeline_id, i, agent_type))

    conn.commit()
    conn.close()

    return {
        'pipeline_id': pipeline_id,
        'name': name,
        'steps': len(agent_types),
        'token_budget': token_budget,
        'message': f"Pipeline '{name}' created with {len(agent_types)} agents"
    }


@app.tool()
async def get_relay_status(pipeline_id: str) -> Dict[str, Any]:
    """
    Get current status of a relay pipeline including progress and quality scores.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Pipeline status with step details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM relay_pipelines WHERE id = ?', (pipeline_id,))
    pipeline = cursor.fetchone()

    if not pipeline:
        conn.close()
        return {'error': f"Pipeline {pipeline_id} not found"}

    cursor.execute('''
        SELECT * FROM relay_steps WHERE pipeline_id = ? ORDER BY step_index
    ''', (pipeline_id,))
    steps = [dict(s) for s in cursor.fetchall()]

    conn.close()

    return {
        'pipeline_id': pipeline_id,
        'name': pipeline['name'],
        'goal': pipeline['goal'],
        'status': pipeline['status'],
        'current_step': pipeline['current_step'],
        'total_steps': len(steps),
        'tokens_used': pipeline['tokens_used'],
        'token_budget': pipeline['token_budget'],
        'steps': steps
    }


@app.tool()
async def advance_relay(
    pipeline_id: str,
    quality_score: float,
    l_score: float,
    output_entity_id: int,
    tokens_used: int,
    output_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manually advance relay to next step after completing current step. Passes the baton.

    Args:
        pipeline_id: Pipeline ID
        quality_score: Quality score of completed step (0.0-1.0)
        l_score: L-Score of output (0.0-1.0)
        output_entity_id: Entity ID where output was stored
        tokens_used: Tokens consumed by step
        output_summary: Summary for next agent

    Returns:
        Next step details or completion status
    """
    start_time = time.time()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM relay_pipelines WHERE id = ?', (pipeline_id,))
    pipeline = cursor.fetchone()

    if not pipeline:
        conn.close()
        return {'error': f"Pipeline {pipeline_id} not found"}

    current_step = pipeline['current_step']

    # Update current step
    cursor.execute('''
        UPDATE relay_steps
        SET status = 'completed', quality_score = ?, l_score = ?,
            output_entity_id = ?, tokens_used = ?, completed_at = CURRENT_TIMESTAMP
        WHERE pipeline_id = ? AND step_index = ?
    ''', (quality_score, l_score, output_entity_id, tokens_used, pipeline_id, current_step))

    # Check if pipeline complete
    agent_types = json.loads(pipeline['agent_types'])
    new_step = current_step + 1
    new_tokens = pipeline['tokens_used'] + tokens_used

    if new_step >= len(agent_types):
        # Pipeline complete
        cursor.execute('''
            UPDATE relay_pipelines
            SET status = 'completed', current_step = ?, tokens_used = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_step, new_tokens, pipeline_id))
        conn.commit()
        conn.close()

        elapsed_ms = (time.time() - start_time) * 1000
        return {
            'pipeline_id': pipeline_id,
            'status': 'completed',
            'total_tokens': new_tokens,
            'handoff_time_ms': round(elapsed_ms, 2)
        }

    # Advance to next step
    baton_data = json.dumps({
        'previous_step': current_step,
        'quality_score': quality_score,
        'l_score': l_score,
        'output_entity_id': output_entity_id,
        'summary': output_summary
    })

    cursor.execute('''
        UPDATE relay_pipelines
        SET current_step = ?, tokens_used = ?, baton_data = ?
        WHERE id = ?
    ''', (new_step, new_tokens, baton_data, pipeline_id))

    cursor.execute('''
        UPDATE relay_steps
        SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
        WHERE pipeline_id = ? AND step_index = ?
    ''', (pipeline_id, new_step))

    conn.commit()
    conn.close()

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        'pipeline_id': pipeline_id,
        'status': 'in_progress',
        'current_step': new_step,
        'next_agent': agent_types[new_step],
        'tokens_remaining': pipeline['token_budget'] - new_tokens,
        'handoff_time_ms': round(elapsed_ms, 2)
    }


@app.tool()
async def get_relay_baton(pipeline_id: str) -> Dict[str, Any]:
    """
    Get current baton for a pipeline with all context needed for next agent.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Baton data with context for next agent
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM relay_pipelines WHERE id = ?', (pipeline_id,))
    pipeline = cursor.fetchone()

    if not pipeline:
        conn.close()
        return {'error': f"Pipeline {pipeline_id} not found"}

    agent_types = json.loads(pipeline['agent_types'])
    baton_data = json.loads(pipeline['baton_data']) if pipeline['baton_data'] else {}

    conn.close()

    return {
        'pipeline_id': pipeline_id,
        'goal': pipeline['goal'],
        'current_step': pipeline['current_step'],
        'current_agent': agent_types[pipeline['current_step']] if pipeline['current_step'] < len(agent_types) else None,
        'tokens_remaining': pipeline['token_budget'] - pipeline['tokens_used'],
        'baton_data': baton_data
    }


@app.tool()
async def list_relay_pipelines(
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List relay pipelines with optional status filter.

    Args:
        status: Filter by status (pending, in_progress, completed, failed)
        limit: Maximum results

    Returns:
        List of pipelines
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute('''
            SELECT * FROM relay_pipelines WHERE status = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (status, limit))
    else:
        cursor.execute('''
            SELECT * FROM relay_pipelines ORDER BY created_at DESC LIMIT ?
        ''', (limit,))

    pipelines = []
    for row in cursor.fetchall():
        agent_types = json.loads(row['agent_types'])
        pipelines.append({
            'id': row['id'],
            'name': row['name'],
            'status': row['status'],
            'progress': f"{row['current_step']}/{len(agent_types)}",
            'tokens_used': row['tokens_used'],
            'created_at': row['created_at']
        })

    conn.close()
    return pipelines


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

@app.tool()
async def circuit_breaker_status(agent_id: str) -> Dict[str, Any]:
    """
    Get circuit breaker status for an agent (CLOSED/OPEN/HALF_OPEN).

    Args:
        agent_id: Agent identifier

    Returns:
        Circuit breaker state and statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM circuit_breakers WHERE agent_id = ?', (agent_id,))
    cb = cursor.fetchone()

    if not cb:
        # Create default circuit breaker
        cursor.execute('''
            INSERT INTO circuit_breakers (agent_id) VALUES (?)
        ''', (agent_id,))
        conn.commit()
        conn.close()
        return {
            'agent_id': agent_id,
            'state': 'closed',
            'failure_count': 0,
            'message': 'New circuit breaker created'
        }

    conn.close()

    return {
        'agent_id': agent_id,
        'state': cb['state'],
        'failure_count': cb['failure_count'],
        'failure_threshold': cb['failure_threshold'],
        'last_failure_at': cb['last_failure_at'],
        'fallback_agent': cb['fallback_agent']
    }


@app.tool()
async def circuit_breaker_record_failure(
    agent_id: str,
    failure_type: str,
    error_message: str
) -> Dict[str, Any]:
    """
    Record a failure for circuit breaker tracking.

    Args:
        agent_id: Agent that failed
        failure_type: Type of failure (timeout, exception, quality_failure, etc.)
        error_message: Error description

    Returns:
        Updated circuit breaker state
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM circuit_breakers WHERE agent_id = ?', (agent_id,))
    cb = cursor.fetchone()

    if not cb:
        cursor.execute('INSERT INTO circuit_breakers (agent_id) VALUES (?)', (agent_id,))
        cursor.execute('SELECT * FROM circuit_breakers WHERE agent_id = ?', (agent_id,))
        cb = cursor.fetchone()

    new_count = cb['failure_count'] + 1
    new_state = cb['state']

    if new_count >= cb['failure_threshold']:
        new_state = 'open'

    cursor.execute('''
        UPDATE circuit_breakers
        SET failure_count = ?, state = ?, last_failure_at = CURRENT_TIMESTAMP
        WHERE agent_id = ?
    ''', (new_count, new_state, agent_id))

    conn.commit()
    conn.close()

    return {
        'agent_id': agent_id,
        'state': new_state,
        'failure_count': new_count,
        'tripped': new_state == 'open'
    }


@app.tool()
async def circuit_breaker_reset(agent_id: str) -> Dict[str, Any]:
    """
    Reset circuit breaker to CLOSED state.

    Args:
        agent_id: Agent to reset

    Returns:
        Reset confirmation
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE circuit_breakers
        SET state = 'closed', failure_count = 0, last_success_at = CURRENT_TIMESTAMP
        WHERE agent_id = ?
    ''', (agent_id,))

    conn.commit()
    conn.close()

    return {
        'agent_id': agent_id,
        'state': 'closed',
        'message': 'Circuit breaker reset'
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Agent Runtime MCP Server (OSS Edition)")
    app.run()
