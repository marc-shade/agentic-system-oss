#!/usr/bin/env python3
"""
Prometheus Metrics Collection for GitMQ Cluster
===============================================

Provides comprehensive metrics collection for:
- Task execution tracking
- Approval workflow monitoring
- Risk assessment distribution
- Code transfer performance
- System resource usage
- Error rates and latency

Metric Types:
- Counter: Monotonically increasing values (tasks executed, errors)
- Gauge: Current values (pending tasks, active approvals)
- Histogram: Distribution of values (latency, code size)
- Summary: Quantiles over time window

Usage:
    from metrics import MetricsCollector

    # Initialize once per node
    metrics = MetricsCollector(node_id="macpro51", port=9100)
    metrics.start_server()  # Expose /metrics endpoint

    # Track task execution
    with metrics.track_task_execution("task-123", "code_execution"):
        result = execute_task(task)

    # Record approval
    metrics.record_approval("high", "approved", "cli")

    # Track risk assessment
    metrics.record_risk_assessment("critical", 0.92)
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

# Prometheus client imports (optional)
try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, Info,
        CollectorRegistry, generate_latest, start_http_server,
        CONTENT_TYPE_LATEST
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available - metrics disabled")
    logger.warning("Install with: pip install prometheus-client")


class NoOpMetric:
    """No-op metric for when Prometheus is not available."""

    def inc(self, amount=1, **labels):
        pass

    def dec(self, amount=1, **labels):
        pass

    def set(self, value, **labels):
        pass

    def observe(self, value, **labels):
        pass

    def labels(self, **labels):
        return self

    def time(self):
        @contextmanager
        def noop():
            yield
        return noop()


class MetricsCollector:
    """
    Collects and exposes Prometheus metrics for GitMQ cluster.

    Provides metrics for all aspects of cluster operation with
    automatic labeling by node, task type, risk level, etc.
    """

    def __init__(
        self,
        node_id: str,
        node_role: str = "worker",
        port: int = 9100,
        registry: Optional[Any] = None
    ):
        """
        Initialize metrics collector.

        Args:
            node_id: Node identifier
            node_role: Node role (orchestrator, worker, builder)
            port: HTTP port for /metrics endpoint
            registry: Custom Prometheus registry (None for default)
        """
        self.node_id = node_id
        self.node_role = node_role
        self.port = port
        self.enabled = PROMETHEUS_AVAILABLE

        if not self.enabled:
            logger.warning("Metrics collection disabled - Prometheus client not available")
            self._init_noop_metrics()
            return

        # Use custom or default registry
        self.registry = registry or CollectorRegistry()

        # Initialize all metrics
        self._init_task_metrics()
        self._init_approval_metrics()
        self._init_risk_metrics()
        self._init_code_transfer_metrics()
        self._init_execution_metrics()
        self._init_error_metrics()
        self._init_system_metrics()

        logger.info(f"Metrics collector initialized for {node_id}")

    def _init_noop_metrics(self):
        """Initialize no-op metrics when Prometheus unavailable."""
        noop = NoOpMetric()

        # Task metrics
        self.tasks_submitted = noop
        self.tasks_completed = noop
        self.tasks_failed = noop
        self.tasks_pending = noop
        self.task_execution_duration = noop

        # Approval metrics
        self.approval_requests = noop
        self.approval_decisions = noop
        self.approval_timeouts = noop
        self.approval_wait_time = noop
        self.approvals_pending = noop

        # Risk metrics
        self.risk_assessments = noop
        self.risk_score_distribution = noop

        # Code transfer metrics
        self.code_transfers = noop
        self.code_transfer_bytes = noop
        self.code_transfer_duration = noop

        # Execution metrics
        self.code_executions = noop
        self.execution_exit_codes = noop
        self.sandbox_operations = noop

        # Error metrics
        self.errors_total = noop
        self.error_rate = noop

        # System metrics
        self.system_info = noop
        self.uptime_seconds = noop

    def _init_task_metrics(self):
        """Initialize task-related metrics."""
        # Task counters
        self.tasks_submitted = Counter(
            'gitmq_tasks_submitted_total',
            'Total number of tasks submitted',
            ['node_id', 'task_type', 'target_node'],
            registry=self.registry
        )

        self.tasks_completed = Counter(
            'gitmq_tasks_completed_total',
            'Total number of tasks completed successfully',
            ['node_id', 'task_type'],
            registry=self.registry
        )

        self.tasks_failed = Counter(
            'gitmq_tasks_failed_total',
            'Total number of tasks that failed',
            ['node_id', 'task_type', 'error_type'],
            registry=self.registry
        )

        # Task gauges
        self.tasks_pending = Gauge(
            'gitmq_tasks_pending',
            'Current number of pending tasks',
            ['node_id'],
            registry=self.registry
        )

        # Task duration histogram
        self.task_execution_duration = Histogram(
            'gitmq_task_execution_duration_seconds',
            'Task execution duration in seconds',
            ['node_id', 'task_type'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
            registry=self.registry
        )

    def _init_approval_metrics(self):
        """Initialize approval workflow metrics."""
        # Approval counters
        self.approval_requests = Counter(
            'gitmq_approval_requests_total',
            'Total number of approval requests',
            ['node_id', 'approval_tier', 'risk_level'],
            registry=self.registry
        )

        self.approval_decisions = Counter(
            'gitmq_approval_decisions_total',
            'Total number of approval decisions',
            ['node_id', 'decision', 'channel', 'risk_level'],
            registry=self.registry
        )

        self.approval_timeouts = Counter(
            'gitmq_approval_timeouts_total',
            'Total number of approval timeouts',
            ['node_id', 'risk_level'],
            registry=self.registry
        )

        # Approval gauges
        self.approvals_pending = Gauge(
            'gitmq_approvals_pending',
            'Current number of pending approvals',
            ['node_id', 'risk_level'],
            registry=self.registry
        )

        # Approval wait time
        self.approval_wait_time = Histogram(
            'gitmq_approval_wait_time_seconds',
            'Time waiting for approval decision',
            ['node_id', 'decision', 'risk_level'],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
            registry=self.registry
        )

    def _init_risk_metrics(self):
        """Initialize risk assessment metrics."""
        # Risk assessment counter
        self.risk_assessments = Counter(
            'gitmq_risk_assessments_total',
            'Total number of risk assessments performed',
            ['node_id', 'risk_level', 'approval_tier'],
            registry=self.registry
        )

        # Risk score distribution
        self.risk_score_distribution = Histogram(
            'gitmq_risk_score',
            'Distribution of risk scores',
            ['node_id', 'task_type'],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )

    def _init_code_transfer_metrics(self):
        """Initialize code transfer metrics."""
        # Code transfer counter
        self.code_transfers = Counter(
            'gitmq_code_transfers_total',
            'Total number of code transfers',
            ['node_id', 'transfer_method', 'compression'],
            registry=self.registry
        )

        # Code transfer size
        self.code_transfer_bytes = Histogram(
            'gitmq_code_transfer_bytes',
            'Size of code transfers in bytes',
            ['node_id', 'transfer_method'],
            buckets=(1024, 10240, 51200, 102400, 512000, 1048576, 10485760),
            registry=self.registry
        )

        # Code transfer duration
        self.code_transfer_duration = Histogram(
            'gitmq_code_transfer_duration_seconds',
            'Code transfer duration in seconds',
            ['node_id', 'transfer_method'],
            buckets=(0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry
        )

    def _init_execution_metrics(self):
        """Initialize execution metrics."""
        # Code execution counter
        self.code_executions = Counter(
            'gitmq_code_executions_total',
            'Total number of code executions',
            ['node_id', 'language', 'status'],
            registry=self.registry
        )

        # Exit codes
        self.execution_exit_codes = Counter(
            'gitmq_execution_exit_codes_total',
            'Distribution of execution exit codes',
            ['node_id', 'exit_code'],
            registry=self.registry
        )

        # Sandbox operations
        self.sandbox_operations = Counter(
            'gitmq_sandbox_operations_total',
            'Sandbox creation and cleanup operations',
            ['node_id', 'operation'],
            registry=self.registry
        )

    def _init_error_metrics(self):
        """Initialize error tracking metrics."""
        # Total errors
        self.errors_total = Counter(
            'gitmq_errors_total',
            'Total number of errors',
            ['node_id', 'error_type', 'component'],
            registry=self.registry
        )

        # Error rate (per minute)
        self.error_rate = Gauge(
            'gitmq_error_rate_per_minute',
            'Current error rate per minute',
            ['node_id', 'component'],
            registry=self.registry
        )

    def _init_system_metrics(self):
        """Initialize system-level metrics."""
        # System info
        self.system_info = Info(
            'gitmq_system',
            'GitMQ system information',
            registry=self.registry
        )

        self.system_info.info({
            'node_id': self.node_id,
            'node_role': self.node_role,
            'version': '0.1.0'
        })

        # Uptime
        self.uptime_seconds = Gauge(
            'gitmq_uptime_seconds',
            'System uptime in seconds',
            ['node_id'],
            registry=self.registry
        )

        self._start_time = time.time()

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    def record_task_submission(self, task_id: str, task_type: str, target_node: str):
        """Record task submission."""
        self.tasks_submitted.labels(
            node_id=self.node_id,
            task_type=task_type,
            target_node=target_node
        ).inc()

    def record_task_completion(self, task_type: str):
        """Record task completion."""
        self.tasks_completed.labels(
            node_id=self.node_id,
            task_type=task_type
        ).inc()

    def record_task_failure(self, task_type: str, error_type: str):
        """Record task failure."""
        self.tasks_failed.labels(
            node_id=self.node_id,
            task_type=task_type,
            error_type=error_type
        ).inc()

    @contextmanager
    def track_task_execution(self, task_id: str, task_type: str):
        """
        Track task execution with automatic timing (context manager).

        Usage:
            with metrics.track_task_execution(task_id, task_type):
                result = execute_task(task)
        """
        start_time = time.time()

        try:
            yield
            duration = time.time() - start_time

            # Record success
            self.task_execution_duration.labels(
                node_id=self.node_id,
                task_type=task_type
            ).observe(duration)

            self.record_task_completion(task_type)

        except Exception as e:
            duration = time.time() - start_time

            # Record failure
            self.record_task_failure(task_type, type(e).__name__)

            raise

    def record_approval_request(self, risk_level: str, approval_tier: str):
        """Record approval request."""
        self.approval_requests.labels(
            node_id=self.node_id,
            approval_tier=approval_tier,
            risk_level=risk_level
        ).inc()

    def record_approval_decision(
        self,
        decision: str,
        channel: str,
        risk_level: str,
        wait_time_seconds: float
    ):
        """Record approval decision."""
        self.approval_decisions.labels(
            node_id=self.node_id,
            decision=decision,
            channel=channel,
            risk_level=risk_level
        ).inc()

        self.approval_wait_time.labels(
            node_id=self.node_id,
            decision=decision,
            risk_level=risk_level
        ).observe(wait_time_seconds)

    def record_risk_assessment(
        self,
        risk_level: str,
        risk_score: float,
        approval_tier: str,
        task_type: str = "unknown"
    ):
        """Record risk assessment."""
        self.risk_assessments.labels(
            node_id=self.node_id,
            risk_level=risk_level,
            approval_tier=approval_tier
        ).inc()

        self.risk_score_distribution.labels(
            node_id=self.node_id,
            task_type=task_type
        ).observe(risk_score)

    def record_code_transfer(
        self,
        transfer_method: str,
        size_bytes: int,
        duration_seconds: float,
        compression: str = "none"
    ):
        """Record code transfer."""
        self.code_transfers.labels(
            node_id=self.node_id,
            transfer_method=transfer_method,
            compression=compression
        ).inc()

        self.code_transfer_bytes.labels(
            node_id=self.node_id,
            transfer_method=transfer_method
        ).observe(size_bytes)

        self.code_transfer_duration.labels(
            node_id=self.node_id,
            transfer_method=transfer_method
        ).observe(duration_seconds)

    def record_error(self, error_type: str, component: str = "unknown"):
        """Record error."""
        self.errors_total.labels(
            node_id=self.node_id,
            error_type=error_type,
            component=component
        ).inc()

    def update_uptime(self):
        """Update uptime metric."""
        uptime = time.time() - self._start_time
        self.uptime_seconds.labels(node_id=self.node_id).set(uptime)

    # ========================================================================
    # Server Management
    # ========================================================================

    def start_server(self, port: Optional[int] = None):
        """
        Start HTTP server to expose /metrics endpoint.

        Args:
            port: HTTP port (uses self.port if None)
        """
        if not self.enabled:
            logger.warning("Cannot start metrics server - Prometheus not available")
            return

        port = port or self.port

        try:
            start_http_server(port, registry=self.registry)
            logger.info(f"Metrics server started on port {port}")
            logger.info(f"Metrics available at http://localhost:{port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    def get_metrics_text(self) -> str:
        """
        Get metrics in Prometheus text format.

        Returns:
            Metrics as text (for manual export)
        """
        if not self.enabled:
            return "# Metrics not available - Prometheus client not installed\n"

        return generate_latest(self.registry).decode('utf-8')


# ============================================================================
# Instrumentation Decorator
# ============================================================================

def track_execution(metrics: MetricsCollector, task_type: str = "unknown"):
    """
    Decorator to automatically track function execution.

    Usage:
        @track_execution(metrics, "data_processing")
        def process_data(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with metrics.track_task_execution("decorator", task_type):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Example Usage
# ============================================================================

def example_metrics():
    """Example: Prometheus metrics collection."""
    print("\n" + "=" * 70)
    print("Prometheus Metrics Collection Example")
    print("=" * 70)

    # Initialize metrics
    metrics = MetricsCollector(
        node_id="macpro51",
        node_role="worker",
        port=9100
    )

    if not metrics.enabled:
        print("\n⚠️  Prometheus client not available - install dependencies:")
        print("   pip install prometheus-client")
        return

    print("\n1. Recording task metrics:")

    # Submit task
    metrics.record_task_submission("task-001", "code_execution", "macpro51")
    print("   ✓ Task submitted")

    # Execute task with tracking
    with metrics.track_task_execution("task-001", "code_execution"):
        time.sleep(0.5)  # Simulate execution
        print("   ✓ Task executed (500ms)")

    print("\n2. Recording approval metrics:")

    # Approval request
    metrics.record_approval_request("high", "approval")
    print("   ✓ Approval requested")

    # Approval decision
    metrics.record_approval_decision("approved", "cli", "high", 30.5)
    print("   ✓ Approval decision recorded (30.5s wait)")

    print("\n3. Recording risk metrics:")

    # Risk assessment
    metrics.record_risk_assessment("critical", 0.92, "collaborative", "code_execution")
    print("   ✓ Risk assessment recorded (0.92 critical)")

    print("\n4. Recording code transfer metrics:")

    # Code transfer
    metrics.record_code_transfer("git_lfs", 1_048_576, 2.5, "zstd")
    print("   ✓ Code transfer recorded (1MB, 2.5s, zstd)")

    print("\n5. Getting metrics text:")
    metrics_text = metrics.get_metrics_text()
    lines = metrics_text.split('\n')[:20]  # Show first 20 lines

    for line in lines:
        if line and not line.startswith('#'):
            print(f"   {line}")

    print(f"   ... ({len(metrics_text.split(chr(10)))} total lines)")

    print("\n" + "=" * 70)
    print("✓ Metrics collection example complete")
    print(f"\nTo view all metrics: curl http://localhost:9100/metrics")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_metrics()
    print("\nMetrics module loaded successfully ✓")
