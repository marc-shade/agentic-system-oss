#!/usr/bin/env python3
"""
Comprehensive Failure Recovery for GitMQ Cluster
================================================

Combines all failure recovery mechanisms:
- Dead Letter Queue (DLQ) for failed tasks
- Health checks and node monitoring
- Automatic failover
- Task rescheduling
- Integration with circuit breakers and retry logic

Usage:
    recovery = FailureRecoveryManager(
        node_id="macpro51",
        dlq_path="./dead_letter_queue.db",
        health_check_interval=30
    )

    # Send failed task to DLQ
    recovery.send_to_dlq(task, error, max_retries=3)

    # Check node health
    if not recovery.is_node_healthy("worker-node"):
        recovery.failover_to("backup-node")
"""

import time
import sqlite3
import json
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path

from circuit_breaker import get_circuit_breaker
from retry_logic import retry, RetryPolicy


# ============================================================================
# Dead Letter Queue
# ============================================================================

@dataclass
class DeadLetterTask:
    """Task in dead letter queue."""
    task_id: str
    task_data: Dict[str, Any]
    error_message: str
    error_type: str
    failed_at: float
    retry_count: int
    original_node: str
    dlq_id: Optional[int] = None


class DeadLetterQueue:
    """
    Persistent queue for failed tasks.

    Stores tasks that have exhausted retries for manual
    inspection or reprocessing.
    """

    def __init__(self, db_path: str = "./dead_letter_queue.db"):
        """
        Initialize dead letter queue.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_database()
        self._lock = threading.Lock()

    def _init_database(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_data TEXT NOT NULL,
                    error_message TEXT,
                    error_type TEXT,
                    failed_at REAL,
                    retry_count INTEGER,
                    original_node TEXT,
                    reprocessed INTEGER DEFAULT 0,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON dead_letters(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reprocessed ON dead_letters(reprocessed)")
            conn.commit()

    def add(self, task: DeadLetterTask):
        """Add task to dead letter queue."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO dead_letters (
                        task_id, task_data, error_message, error_type,
                        failed_at, retry_count, original_node
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id,
                    json.dumps(task.task_data),
                    task.error_message,
                    task.error_type,
                    task.failed_at,
                    task.retry_count,
                    task.original_node
                ))
                task.dlq_id = cursor.lastrowid
                conn.commit()

    def get_pending(self, limit: int = 100) -> List[DeadLetterTask]:
        """Get pending (not reprocessed) tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM dead_letters
                WHERE reprocessed = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            tasks = []
            for row in cursor:
                tasks.append(DeadLetterTask(
                    dlq_id=row['id'],
                    task_id=row['task_id'],
                    task_data=json.loads(row['task_data']),
                    error_message=row['error_message'],
                    error_type=row['error_type'],
                    failed_at=row['failed_at'],
                    retry_count=row['retry_count'],
                    original_node=row['original_node']
                ))
            return tasks

    def mark_reprocessed(self, dlq_id: int):
        """Mark task as reprocessed."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE dead_letters
                    SET reprocessed = 1
                    WHERE id = ?
                """, (dlq_id,))
                conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Get DLQ statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN reprocessed = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN reprocessed = 1 THEN 1 ELSE 0 END) as reprocessed
                FROM dead_letters
            """)
            row = cursor.fetchone()
            return {
                "total": row[0] or 0,
                "pending": row[1] or 0,
                "reprocessed": row[2] or 0
            }


# ============================================================================
# Health Monitoring
# ============================================================================

@dataclass
class NodeHealth:
    """Node health status."""
    node_id: str
    is_healthy: bool
    last_heartbeat: float
    consecutive_failures: int = 0
    health_score: float = 1.0  # 0.0-1.0
    last_check: float = field(default_factory=time.time)


class HealthMonitor:
    """
    Monitors cluster node health.

    Tracks heartbeats and failure rates to determine
    node availability.
    """

    def __init__(
        self,
        heartbeat_timeout: float = 60,
        failure_threshold: int = 3
    ):
        """
        Initialize health monitor.

        Args:
            heartbeat_timeout: Seconds before node considered unhealthy
            failure_threshold: Consecutive failures before marking unhealthy
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.failure_threshold = failure_threshold
        self._nodes: Dict[str, NodeHealth] = {}
        self._lock = threading.Lock()

    def record_heartbeat(self, node_id: str):
        """Record successful heartbeat from node."""
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = NodeHealth(
                    node_id=node_id,
                    is_healthy=True,
                    last_heartbeat=time.time()
                )
            else:
                node = self._nodes[node_id]
                node.last_heartbeat = time.time()
                node.consecutive_failures = 0
                node.is_healthy = True
                node.health_score = min(1.0, node.health_score + 0.1)

    def record_failure(self, node_id: str):
        """Record failure from node."""
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = NodeHealth(
                    node_id=node_id,
                    is_healthy=True,
                    last_heartbeat=time.time()
                )

            node = self._nodes[node_id]
            node.consecutive_failures += 1
            node.health_score = max(0.0, node.health_score - 0.2)

            if node.consecutive_failures >= self.failure_threshold:
                node.is_healthy = False

    def is_healthy(self, node_id: str) -> bool:
        """Check if node is healthy."""
        with self._lock:
            if node_id not in self._nodes:
                return True  # Unknown nodes assumed healthy initially

            node = self._nodes[node_id]

            # Check heartbeat timeout
            if time.time() - node.last_heartbeat > self.heartbeat_timeout:
                node.is_healthy = False

            return node.is_healthy

    def get_healthy_nodes(self) -> List[str]:
        """Get list of healthy node IDs."""
        with self._lock:
            return [
                node_id for node_id, node in self._nodes.items()
                if self.is_healthy(node_id)
            ]

    def get_health_status(self) -> Dict[str, NodeHealth]:
        """Get health status for all nodes."""
        with self._lock:
            return dict(self._nodes)


# ============================================================================
# Failure Recovery Manager
# ============================================================================

class FailureRecoveryManager:
    """
    Comprehensive failure recovery management.

    Coordinates circuit breakers, retry logic, DLQ, health monitoring,
    and automatic failover.
    """

    def __init__(
        self,
        node_id: str,
        dlq_path: str = "./dead_letter_queue.db",
        heartbeat_timeout: float = 60,
        failure_threshold: int = 3,
        enable_auto_reprocessing: bool = False
    ):
        """
        Initialize failure recovery manager.

        Args:
            node_id: Current node identifier
            dlq_path: Path to DLQ database
            heartbeat_timeout: Heartbeat timeout in seconds
            failure_threshold: Failures before marking unhealthy
            enable_auto_reprocessing: Enable automatic DLQ reprocessing
        """
        self.node_id = node_id
        self.dlq = DeadLetterQueue(dlq_path)
        self.health_monitor = HealthMonitor(heartbeat_timeout, failure_threshold)
        self.enable_auto_reprocessing = enable_auto_reprocessing

        # Circuit breakers per operation type
        self._circuit_breakers: Dict[str, Any] = {}

    def send_to_dlq(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        error: Exception,
        retry_count: int = 0
    ):
        """
        Send failed task to dead letter queue.

        Args:
            task_id: Task identifier
            task_data: Task payload
            error: Exception that caused failure
            retry_count: Number of retries attempted
        """
        dlq_task = DeadLetterTask(
            task_id=task_id,
            task_data=task_data,
            error_message=str(error),
            error_type=type(error).__name__,
            failed_at=time.time(),
            retry_count=retry_count,
            original_node=self.node_id
        )

        self.dlq.add(dlq_task)

    def execute_with_recovery(
        self,
        operation_name: str,
        func: Callable,
        *args,
        retry_policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> Any:
        """
        Execute operation with full recovery (circuit breaker + retry + DLQ).

        Args:
            operation_name: Name for circuit breaker
            func: Function to execute
            retry_policy: Retry policy (optional)
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Exception if all recovery mechanisms fail
        """
        # Get or create circuit breaker
        breaker = get_circuit_breaker(
            operation_name,
            failure_threshold=5,
            timeout_seconds=60
        )

        # Create retry decorator
        retry_decorator = retry(policy=retry_policy) if retry_policy else retry()

        # Wrap function with recovery
        @retry_decorator
        def protected_operation():
            with breaker:
                return func(*args, **kwargs)

        try:
            return protected_operation()
        except Exception as e:
            # All recovery failed - send to DLQ
            self.send_to_dlq(
                task_id=kwargs.get('task_id', 'unknown'),
                task_data=kwargs,
                error=e,
                retry_count=retry_policy.max_attempts if retry_policy else 3
            )
            raise

    def failover_task(
        self,
        task: Dict[str, Any],
        failed_node: str,
        target_nodes: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Failover task to healthy node.

        Args:
            task: Task to failover
            failed_node: Node that failed
            target_nodes: Candidate nodes (None = auto-select)

        Returns:
            Selected target node, or None if no healthy nodes
        """
        # Get healthy nodes
        if target_nodes is None:
            healthy_nodes = self.health_monitor.get_healthy_nodes()
        else:
            healthy_nodes = [
                n for n in target_nodes
                if self.health_monitor.is_healthy(n)
            ]

        # Remove failed node
        healthy_nodes = [n for n in healthy_nodes if n != failed_node]

        if not healthy_nodes:
            return None

        # Select node with best health score
        health_status = self.health_monitor.get_health_status()
        best_node = max(
            healthy_nodes,
            key=lambda n: health_status.get(n, NodeHealth(n, True, time.time())).health_score
        )

        return best_node

    def reprocess_dlq_tasks(self, max_tasks: int = 10) -> int:
        """
        Reprocess tasks from dead letter queue.

        Args:
            max_tasks: Maximum tasks to reprocess

        Returns:
            Number of tasks successfully reprocessed
        """
        pending_tasks = self.dlq.get_pending(limit=max_tasks)
        reprocessed_count = 0

        for task in pending_tasks:
            try:
                # Attempt reprocessing (placeholder - actual logic depends on task type)
                # In real implementation, this would call appropriate handler

                self.dlq.mark_reprocessed(task.dlq_id)
                reprocessed_count += 1

            except Exception as e:
                # Reprocessing failed - leave in DLQ
                continue

        return reprocessed_count

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get comprehensive recovery statistics."""
        return {
            "node_id": self.node_id,
            "dlq": self.dlq.get_stats(),
            "health": {
                node_id: {
                    "is_healthy": node.is_healthy,
                    "consecutive_failures": node.consecutive_failures,
                    "health_score": node.health_score,
                    "last_heartbeat_ago": time.time() - node.last_heartbeat
                }
                for node_id, node in self.health_monitor.get_health_status().items()
            }
        }


# ============================================================================
# Example Usage
# ============================================================================

def example_failure_recovery():
    """Example: Comprehensive failure recovery."""
    print("\n" + "=" * 70)
    print("Failure Recovery Example")
    print("=" * 70)

    # Initialize recovery manager
    recovery = FailureRecoveryManager(
        node_id="worker-1",
        dlq_path="./example_dlq.db"
    )

    print("\n1. Dead Letter Queue:")

    # Simulate failed task
    try:
        raise ValueError("Task execution failed")
    except Exception as e:
        recovery.send_to_dlq(
            task_id="task-fail-001",
            task_data={"code": "print('hello')", "type": "python"},
            error=e,
            retry_count=3
        )
        print(f"   Sent task to DLQ: task-fail-001")

    dlq_stats = recovery.dlq.get_stats()
    print(f"   DLQ Stats: {dlq_stats}")

    print("\n2. Health Monitoring:")

    # Record heartbeats
    recovery.health_monitor.record_heartbeat("worker-1")
    recovery.health_monitor.record_heartbeat("worker-2")
    print(f"   Recorded heartbeats for worker-1, worker-2")

    # Simulate failure
    recovery.health_monitor.record_failure("worker-2")
    recovery.health_monitor.record_failure("worker-2")
    recovery.health_monitor.record_failure("worker-2")
    print(f"   Recorded 3 failures for worker-2")

    healthy_nodes = recovery.health_monitor.get_healthy_nodes()
    print(f"   Healthy nodes: {healthy_nodes}")

    print("\n3. Failover:")

    task = {"task_id": "task-123", "code": "print('test')"}
    target_node = recovery.failover_task(task, failed_node="worker-2")
    print(f"   Failover target: {target_node}")

    print("\n4. Recovery Stats:")
    stats = recovery.get_recovery_stats()
    print(f"   Node: {stats['node_id']}")
    print(f"   DLQ: {stats['dlq']}")
    print(f"   Health: {len(stats['health'])} nodes monitored")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_failure_recovery()
    print("\nFailure recovery module loaded successfully ✓")
