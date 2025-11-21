#!/usr/bin/env python3
"""
Observability Integration for GitMQ Daemon
==========================================

Integrates Phase 4 observability components with the GitMQ daemon:
- OpenTelemetry distributed tracing
- Prometheus metrics collection
- Structured JSON logging
- Grafana dashboard visualization

This module provides a unified integration layer that instruments
the daemon with comprehensive monitoring capabilities.

Features:
- Automatic span creation for task execution
- Metric tracking for all operations
- Structured log correlation with traces
- Minimal code changes to existing daemon
- Graceful degradation when dependencies unavailable

Usage:
    from observability_integration import ObservabilityManager

    # Initialize observability
    obs = ObservabilityManager(
        node_id="macpro51",
        node_role="worker",
        enable_tracing=True,
        enable_metrics=True,
        enable_structured_logging=True
    )

    # Instrument daemon
    obs.instrument_daemon(daemon)

    # Or use context manager for task execution
    with obs.track_task_execution(task_id, task_type):
        result = execute_task(task)

Integration Points:
    1. Task submission → trace span + metric + log
    2. Approval request → trace span + metric + log
    3. Risk assessment → trace span + metric + log
    4. Code transfer → trace span + metric + log
    5. Task execution → trace span + metric + log
    6. Result reporting → trace span + metric + log
"""

import logging
import time
import functools
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

# Import Phase 4 components (with graceful degradation)
try:
    from telemetry import TracingManager, SpanAttributes
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    logging.warning("telemetry.py not available - tracing disabled")

try:
    from metrics import MetricsCollector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logging.warning("metrics.py not available - metrics disabled")

try:
    from structured_logging import get_logger, StructuredLogger
    STRUCTURED_LOGGING_AVAILABLE = True
except ImportError:
    STRUCTURED_LOGGING_AVAILABLE = False
    logging.warning("structured_logging.py not available - using standard logging")


@dataclass
class ObservabilityConfig:
    """Configuration for observability components."""

    # Node identification
    node_id: str = "unknown"
    node_role: str = "worker"

    # Tracing configuration
    enable_tracing: bool = True
    enable_console_tracing: bool = False
    enable_otlp_export: bool = False
    otlp_endpoint: Optional[str] = None

    # Metrics configuration
    enable_metrics: bool = True
    metrics_port: int = 9100

    # Logging configuration
    enable_structured_logging: bool = True
    log_level: int = logging.INFO
    include_trace_context: bool = True

    # Service name
    service_name: Optional[str] = None

    def __post_init__(self):
        """Set default service name if not provided."""
        if self.service_name is None:
            self.service_name = f"gitmq-{self.node_role}"


class ObservabilityManager:
    """
    Unified observability manager.

    Coordinates tracing, metrics, and logging for the GitMQ daemon.
    Provides simple API for instrumenting code with minimal changes.
    """

    def __init__(self, config: Optional[ObservabilityConfig] = None, **kwargs):
        """
        Initialize observability manager.

        Args:
            config: ObservabilityConfig instance
            **kwargs: Config parameters (if config not provided)
        """
        if config is None:
            config = ObservabilityConfig(**kwargs)

        self.config = config

        # Initialize tracing
        if config.enable_tracing and TRACING_AVAILABLE:
            self.tracing = TracingManager(
                service_name=config.service_name,
                enable_console_export=config.enable_console_tracing,
                enable_otlp_export=config.enable_otlp_export,
                otlp_endpoint=config.otlp_endpoint,
                node_id=config.node_id,
                node_role=config.node_role
            )
            self.tracing_enabled = self.tracing.enabled
        else:
            self.tracing = None
            self.tracing_enabled = False

        # Initialize metrics
        if config.enable_metrics and METRICS_AVAILABLE:
            self.metrics = MetricsCollector(
                node_id=config.node_id,
                node_role=config.node_role,
                port=config.metrics_port
            )
            self.metrics_enabled = self.metrics.enabled

            # Start metrics HTTP server
            if self.metrics_enabled:
                try:
                    self.metrics.start_server()
                except Exception as e:
                    logging.warning(f"Failed to start metrics server: {e}")
                    self.metrics_enabled = False
        else:
            self.metrics = None
            self.metrics_enabled = False

        # Initialize structured logging
        if config.enable_structured_logging and STRUCTURED_LOGGING_AVAILABLE:
            self.logger = get_logger(
                name=config.service_name,
                node_id=config.node_id,
                level=config.log_level,
                include_trace_context=config.include_trace_context
            )
            self.logging_enabled = True
        else:
            self.logger = logging.getLogger(config.service_name)
            self.logger.setLevel(config.log_level)
            self.logging_enabled = False

        self.logger.info(
            "Observability initialized",
            tracing=self.tracing_enabled,
            metrics=self.metrics_enabled,
            structured_logging=self.logging_enabled
        )

    # ========================================================================
    # Task Execution Tracking
    # ========================================================================

    @contextmanager
    def track_task_execution(
        self,
        task_id: str,
        task_type: str,
        code_language: Optional[str] = None
    ):
        """
        Track complete task execution lifecycle.

        Creates trace span, tracks metrics, logs structured events.

        Usage:
            with obs.track_task_execution(task_id, task_type):
                result = execute_task(task)
        """
        # Start trace span
        if self.tracing_enabled:
            span_context = self.tracing.trace_task_execution(
                task_id, task_type, code_language
            )
        else:
            span_context = None

        # Start metrics tracking
        if self.metrics_enabled:
            metrics_context = self.metrics.track_task_execution(task_id, task_type)
        else:
            metrics_context = None

        # Log task start
        self.logger.info(
            "Task execution started",
            task_id=task_id,
            task_type=task_type,
            code_language=code_language
        )

        start_time = time.time()

        try:
            # Execute within contexts
            if span_context and metrics_context:
                with span_context as span, metrics_context:
                    yield span
            elif span_context:
                with span_context as span:
                    yield span
            elif metrics_context:
                with metrics_context:
                    yield None
            else:
                yield None

            # Log successful completion
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Task execution completed",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                success=True
            )

        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Task execution failed",
                task_id=task_id,
                task_type=task_type,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise

    @contextmanager
    def track_approval_request(
        self,
        task_id: str,
        risk_level: str,
        risk_score: float,
        approval_tier: str
    ):
        """
        Track approval request lifecycle.

        Creates trace span, tracks metrics, logs structured events.
        """
        # Start trace span
        if self.tracing_enabled:
            span_context = self.tracing.trace_approval_request(
                task_id, risk_level, risk_score, approval_tier
            )
        else:
            span_context = None

        # Track approval request metric
        if self.metrics_enabled:
            self.metrics.record_approval_request(risk_level, approval_tier)

        # Log approval request
        self.logger.info(
            "Approval request initiated",
            task_id=task_id,
            risk_level=risk_level,
            risk_score=risk_score,
            approval_tier=approval_tier
        )

        start_time = time.time()

        try:
            if span_context:
                with span_context as span:
                    yield span
            else:
                yield None

            # Log approval completion
            decision_time_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Approval request completed",
                task_id=task_id,
                decision_time_ms=decision_time_ms
            )

        except Exception as e:
            self.logger.error(
                "Approval request failed",
                task_id=task_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise

    @contextmanager
    def track_code_transfer(
        self,
        task_id: str,
        transfer_method: str,
        size_bytes: int
    ):
        """
        Track code transfer performance.

        Creates trace span, tracks metrics, logs structured events.
        """
        # Start trace span
        if self.tracing_enabled:
            span_context = self.tracing.trace_code_transfer(
                task_id, transfer_method, size_bytes
            )
        else:
            span_context = None

        # Log code transfer start
        self.logger.info(
            "Code transfer started",
            task_id=task_id,
            method=transfer_method,
            size_bytes=size_bytes
        )

        start_time = time.time()

        try:
            if span_context:
                with span_context as span:
                    yield span
            else:
                yield None

            # Track metrics
            duration = time.time() - start_time
            if self.metrics_enabled:
                self.metrics.record_code_transfer(
                    transfer_method,
                    size_bytes,
                    duration
                )

            # Log completion
            self.logger.info(
                "Code transfer completed",
                task_id=task_id,
                method=transfer_method,
                size_bytes=size_bytes,
                duration_ms=duration * 1000
            )

        except Exception as e:
            self.logger.error(
                "Code transfer failed",
                task_id=task_id,
                method=transfer_method,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise

    def record_approval_decision(
        self,
        task_id: str,
        decision: str,
        approver: str,
        channel: str,
        risk_level: str,
        decision_time_seconds: float
    ):
        """
        Record approval decision.

        Tracks metrics and logs decision.
        """
        # Track metrics
        if self.metrics_enabled:
            self.metrics.record_approval_decision(
                decision,
                channel,
                risk_level,
                decision_time_seconds
            )

        # Log decision
        self.logger.info(
            "Approval decision recorded",
            task_id=task_id,
            decision=decision,
            approver=approver,
            channel=channel,
            risk_level=risk_level,
            decision_time_seconds=decision_time_seconds
        )

    def record_risk_assessment(
        self,
        task_id: str,
        risk_level: str,
        risk_score: float,
        approval_tier: str,
        task_type: str = "unknown",
        risk_factors: Optional[Dict[str, float]] = None
    ):
        """
        Record risk assessment result.

        Tracks metrics and logs assessment.
        """
        # Track metrics
        if self.metrics_enabled:
            self.metrics.record_risk_assessment(
                risk_level,
                risk_score,
                approval_tier,
                task_type
            )

        # Log assessment
        log_data = {
            "task_id": task_id,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "approval_tier": approval_tier,
            "task_type": task_type
        }
        if risk_factors:
            log_data.update(risk_factors)

        self.logger.info("Risk assessment completed", **log_data)

    def record_error(
        self,
        error_type: str,
        component: str,
        error_message: str,
        task_id: Optional[str] = None
    ):
        """
        Record error occurrence.

        Tracks metrics and logs error.
        """
        # Track metrics
        if self.metrics_enabled:
            self.metrics.record_error(error_type, component)

        # Log error
        self.logger.error(
            "Error occurred",
            error_type=error_type,
            component=component,
            error_message=error_message,
            task_id=task_id
        )

    # ========================================================================
    # Daemon Instrumentation
    # ========================================================================

    def instrument_daemon(self, daemon):
        """
        Instrument daemon with observability.

        Monkey-patches key daemon methods to add tracing, metrics, and logging.

        Args:
            daemon: GitMQNodeDaemon instance
        """
        # Store original methods
        daemon._original_execute_code = daemon.execute_code
        daemon._original_request_approval = getattr(daemon, 'request_approval', None)

        # Patch execute_code
        @functools.wraps(daemon._original_execute_code)
        def execute_code_instrumented(task_id: str, code: str, **kwargs):
            task_type = kwargs.get('task_type', 'code_execution')
            code_language = kwargs.get('language', None)

            with self.track_task_execution(task_id, task_type, code_language) as span:
                # Set additional span attributes
                if span and self.tracing_enabled:
                    span.set_attribute(SpanAttributes.CODE_SIZE_BYTES, len(code))

                return daemon._original_execute_code(task_id, code, **kwargs)

        daemon.execute_code = execute_code_instrumented

        # Patch request_approval if exists
        if daemon._original_request_approval:
            @functools.wraps(daemon._original_request_approval)
            def request_approval_instrumented(task, risk_assessment):
                with self.track_approval_request(
                    task.get('task_id', 'unknown'),
                    risk_assessment.risk_level,
                    risk_assessment.risk_score,
                    risk_assessment.approval_tier
                ):
                    return daemon._original_request_approval(task, risk_assessment)

            daemon.request_approval = request_approval_instrumented

        self.logger.info(
            "Daemon instrumented",
            instrumented_methods=["execute_code", "request_approval"]
        )

    # ========================================================================
    # Context Propagation
    # ========================================================================

    def inject_trace_context(self, carrier: Optional[Dict] = None) -> Dict[str, str]:
        """
        Inject trace context for cross-node propagation.

        Args:
            carrier: Dictionary to inject into (created if None)

        Returns:
            Carrier with trace context
        """
        if self.tracing_enabled:
            return self.tracing.inject_context(carrier)
        return carrier or {}

    def extract_trace_context(self, carrier: Dict[str, str]):
        """
        Extract trace context from remote node.

        Args:
            carrier: Dictionary with trace context

        Returns:
            Extracted context
        """
        if self.tracing_enabled:
            return self.tracing.extract_context(carrier)
        return None

    # ========================================================================
    # Correlation Context
    # ========================================================================

    def correlation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for correlation ID.

        Usage:
            with obs.correlation_context("req-123"):
                # All logs have correlation_id="req-123"
                obs.logger.info("Processing request")
        """
        if hasattr(self.logger, 'correlation_context'):
            return self.logger.correlation_context(correlation_id)
        else:
            # Fallback: no-op context manager
            from contextlib import nullcontext
            return nullcontext()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_observability_manager(
    node_id: str,
    node_role: str = "worker",
    enable_all: bool = True
) -> ObservabilityManager:
    """
    Create observability manager with sensible defaults.

    Args:
        node_id: Node identifier
        node_role: Node role (orchestrator, worker, builder)
        enable_all: Enable all components

    Returns:
        ObservabilityManager instance
    """
    config = ObservabilityConfig(
        node_id=node_id,
        node_role=node_role,
        enable_tracing=enable_all,
        enable_metrics=enable_all,
        enable_structured_logging=enable_all,
        enable_console_tracing=False,  # Disable console export by default
        metrics_port=9100
    )

    return ObservabilityManager(config)


# ============================================================================
# Example Usage
# ============================================================================

def example_observability_integration():
    """Example: Integrate observability with daemon."""
    print("\n" + "=" * 70)
    print("Observability Integration Example")
    print("=" * 70)

    # Create observability manager
    obs = create_observability_manager(
        node_id="macpro51",
        node_role="worker"
    )

    print("\n1. Track task execution:")

    # Simulate task execution
    task_id = "task-obs-001"
    task_type = "code_execution"

    with obs.track_task_execution(task_id, task_type, "python"):
        print(f"   Executing task {task_id}...")
        time.sleep(0.1)
        print(f"   Task completed")

    print("\n2. Track approval request:")

    # Simulate approval
    with obs.track_approval_request(task_id, "medium", 0.45, "notification"):
        print(f"   Requesting approval...")
        time.sleep(0.05)
        print(f"   Approval granted")

    obs.record_approval_decision(
        task_id=task_id,
        decision="approved",
        approver="human",
        channel="cli",
        risk_level="medium",
        decision_time_seconds=0.05
    )

    print("\n3. Track code transfer:")

    # Simulate code transfer
    with obs.track_code_transfer(task_id, "inline", 1024):
        print(f"   Transferring code...")
        time.sleep(0.02)
        print(f"   Transfer complete")

    print("\n4. Record risk assessment:")

    obs.record_risk_assessment(
        task_id=task_id,
        risk_level="medium",
        risk_score=0.45,
        approval_tier="notification",
        task_type="code_execution",
        risk_factors={
            "scope": 0.3,
            "criticality": 0.5,
            "reversibility": 0.6,
            "test_coverage": 0.4,
            "novelty": 0.5
        }
    )

    print("\n5. Correlation context:")

    with obs.correlation_context("req-456"):
        obs.logger.info("Step 1", step="validation")
        obs.logger.info("Step 2", step="execution")
        obs.logger.info("Step 3", step="reporting")

    print("\n6. Access components:")
    print(f"   - Metrics endpoint: http://localhost:{obs.config.metrics_port}/metrics")
    print(f"   - Tracing enabled: {obs.tracing_enabled}")
    print(f"   - Metrics enabled: {obs.metrics_enabled}")
    print(f"   - Structured logging enabled: {obs.logging_enabled}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_observability_integration()
    print("\nObservability integration module loaded successfully ✓")
