#!/usr/bin/env python3
"""
AGI OpenTelemetry Instrumentation

Implements observability for AGI operations using OpenTelemetry conventions.
Based on OpenTelemetry GenAI SIG semantic conventions for AI agent observability.

Features:
- Custom AGI semantic conventions
- Traces for self-evaluation decisions
- Metrics for rollbacks, approvals, circuit breaker state
- Events for audit trail
- Prometheus export integration

Reference: https://opentelemetry.io/blog/2025/ai-agent-observability/

Author: AGI Development System
Created: 2025-12-03
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json

# Try to import OpenTelemetry - graceful degradation if not available
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logging.warning("OpenTelemetry not available - using fallback metrics")

# Try Prometheus exporter
try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from prometheus_client import start_http_server, Counter, Gauge, Histogram, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# AGI Semantic Conventions (Custom extension of GenAI SIG conventions)
# =============================================================================

class AGISemanticConventions:
    """
    Custom semantic conventions for AGI operations.
    Extends OpenTelemetry GenAI SIG conventions.
    """
    # System identification
    AGI_SYSTEM = "agi.system"
    AGI_COMPONENT = "agi.component"
    AGI_VERSION = "agi.version"

    # Self-evaluation attributes
    AGI_EVAL_MODIFICATION_ID = "agi.eval.modification_id"
    AGI_EVAL_BASELINE_COMMIT = "agi.eval.baseline_commit"
    AGI_EVAL_CURRENT_COMMIT = "agi.eval.current_commit"
    AGI_EVAL_EXECUTION_TIME_BASELINE_MS = "agi.eval.execution_time_baseline_ms"
    AGI_EVAL_EXECUTION_TIME_CURRENT_MS = "agi.eval.execution_time_current_ms"
    AGI_EVAL_EXECUTION_TIME_DELTA_PERCENT = "agi.eval.execution_time_delta_percent"
    AGI_EVAL_SUCCESS_RATE_BASELINE = "agi.eval.success_rate_baseline"
    AGI_EVAL_SUCCESS_RATE_CURRENT = "agi.eval.success_rate_current"
    AGI_EVAL_SUCCESS_RATE_DELTA = "agi.eval.success_rate_delta"

    # Decision attributes
    AGI_DECISION = "agi.decision"
    AGI_DECISION_CONFIDENCE = "agi.decision.confidence"
    AGI_DECISION_REASONING = "agi.decision.reasoning"
    AGI_DECISION_TIMESTAMP = "agi.decision.timestamp"

    # Guardian attributes
    AGI_GUARDIAN_STATE = "agi.guardian.state"
    AGI_GUARDIAN_APPROVED = "agi.guardian.approved"
    AGI_GUARDIAN_REQUEST_ID = "agi.guardian.request_id"
    AGI_GUARDIAN_BLOCKED_REASON = "agi.guardian.blocked_reason"

    # Rollback attributes
    AGI_ROLLBACK_TO_COMMIT = "agi.rollback.to_commit"
    AGI_ROLLBACK_SUCCESS = "agi.rollback.success"
    AGI_ROLLBACK_UNTRACKED_FILES = "agi.rollback.untracked_files"
    AGI_ROLLBACK_CRITICAL_FILES = "agi.rollback.critical_files"
    AGI_ROLLBACK_STASHED = "agi.rollback.stashed"

    # Safety attributes
    AGI_SAFETY_CONFIDENCE_THRESHOLD = "agi.safety.confidence_threshold"
    AGI_SAFETY_RATE_LIMITED = "agi.safety.rate_limited"
    AGI_SAFETY_HOURLY_COUNT = "agi.safety.hourly_count"


# =============================================================================
# Fallback Metrics (when OpenTelemetry not available)
# =============================================================================

class FallbackMetrics:
    """Simple file-based metrics when OTel/Prometheus not available."""

    def __init__(self, metrics_file: str = "/var/log/agi-guardian/metrics.jsonl"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def record(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "metric": metric_name,
            "value": value,
            "labels": labels or {}
        }
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


# =============================================================================
# AGI Metrics Registry
# =============================================================================

@dataclass
class AGIMetrics:
    """Container for AGI observability metrics."""

    # Counters
    evaluations_total: Any = None
    rollbacks_total: Any = None
    rollbacks_blocked: Any = None
    guardian_approvals: Any = None
    guardian_rejections: Any = None
    circuit_opens: Any = None

    # Gauges
    circuit_state: Any = None
    confidence_threshold: Any = None
    hourly_destructive_ops: Any = None
    failure_count: Any = None

    # Histograms
    evaluation_duration: Any = None
    confidence_distribution: Any = None
    execution_time_delta: Any = None

    # Info
    system_info: Any = None


class AGIObservability:
    """
    Main observability class for AGI system.

    Provides:
    - OpenTelemetry tracing (if available)
    - Prometheus metrics (if available)
    - Fallback file-based metrics
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.tracer = None
        self.meter = None
        self.metrics = AGIMetrics()
        self.fallback = FallbackMetrics()

        self._setup_tracing()
        self._setup_metrics()

    def _setup_tracing(self):
        """Initialize OpenTelemetry tracing."""
        if not OTEL_AVAILABLE:
            logger.info("OpenTelemetry not available - tracing disabled")
            return

        try:
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: "agi-self-evaluation",
                ResourceAttributes.SERVICE_VERSION: "1.0.0",
                "agi.system": "darwin-godel-machine",
            })

            provider = TracerProvider(resource=resource)
            # Add console exporter for debugging
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer("agi.self_evaluation", "1.0.0")

            logger.info("OpenTelemetry tracing initialized")

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")

    def _setup_metrics(self):
        """Initialize metrics (Prometheus or fallback)."""
        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus_metrics()
        else:
            logger.info("Prometheus not available - using fallback metrics")

    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        try:
            # Counters
            self.metrics.evaluations_total = Counter(
                'agi_evaluations_total',
                'Total number of self-evaluations',
                ['decision', 'component']
            )

            self.metrics.rollbacks_total = Counter(
                'agi_rollbacks_total',
                'Total rollback operations',
                ['success', 'reason']
            )

            self.metrics.rollbacks_blocked = Counter(
                'agi_rollbacks_blocked_total',
                'Rollbacks blocked by safety system',
                ['reason']
            )

            self.metrics.guardian_approvals = Counter(
                'agi_guardian_approvals_total',
                'Operations approved by guardian',
                ['operation_type']
            )

            self.metrics.guardian_rejections = Counter(
                'agi_guardian_rejections_total',
                'Operations rejected by guardian',
                ['operation_type', 'reason']
            )

            self.metrics.circuit_opens = Counter(
                'agi_circuit_opens_total',
                'Number of times circuit breaker opened'
            )

            # Gauges
            self.metrics.circuit_state = Gauge(
                'agi_circuit_state',
                'Circuit breaker state (0=closed, 1=half_open, 2=open)'
            )

            self.metrics.confidence_threshold = Gauge(
                'agi_confidence_threshold',
                'Current confidence threshold for destructive ops'
            )

            self.metrics.hourly_destructive_ops = Gauge(
                'agi_hourly_destructive_ops',
                'Destructive operations in current hour'
            )

            self.metrics.failure_count = Gauge(
                'agi_guardian_failure_count',
                'Current failure count toward circuit open'
            )

            # Histograms
            self.metrics.evaluation_duration = Histogram(
                'agi_evaluation_duration_seconds',
                'Time spent on self-evaluation',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
            )

            self.metrics.confidence_distribution = Histogram(
                'agi_decision_confidence',
                'Distribution of decision confidence scores',
                buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            )

            self.metrics.execution_time_delta = Histogram(
                'agi_execution_time_delta_percent',
                'Distribution of execution time changes',
                buckets=[-50, -30, -20, -10, -5, 0, 5, 10, 20, 30, 50, 100]
            )

            # Info metric
            self.metrics.system_info = Info(
                'agi_system',
                'AGI system information'
            )
            self.metrics.system_info.info({
                'version': '1.0.0',
                'system': 'darwin-godel-machine',
                'component': 'self-evaluation'
            })

            # Start Prometheus HTTP server on port 9091
            start_http_server(9091)
            logger.info("Prometheus metrics server started on port 9091")

        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}")

    # =========================================================================
    # Tracing Methods
    # =========================================================================

    @contextmanager
    def trace_evaluation(self, modification_id: str, baseline_commit: str):
        """Context manager for tracing a self-evaluation."""
        if self.tracer:
            with self.tracer.start_as_current_span("agi.evaluate_modification") as span:
                span.set_attribute(AGISemanticConventions.AGI_SYSTEM, "darwin-godel-machine")
                span.set_attribute(AGISemanticConventions.AGI_COMPONENT, "self_evaluation")
                span.set_attribute(AGISemanticConventions.AGI_EVAL_MODIFICATION_ID, modification_id)
                span.set_attribute(AGISemanticConventions.AGI_EVAL_BASELINE_COMMIT, baseline_commit)

                start_time = time.time()
                try:
                    yield span
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("duration_seconds", duration)
                    if self.metrics.evaluation_duration:
                        self.metrics.evaluation_duration.observe(duration)
        else:
            yield None

    @contextmanager
    def trace_rollback(self, to_commit: str, confidence: float):
        """Context manager for tracing a rollback operation."""
        if self.tracer:
            with self.tracer.start_as_current_span("agi.rollback") as span:
                span.set_attribute(AGISemanticConventions.AGI_ROLLBACK_TO_COMMIT, to_commit)
                span.set_attribute(AGISemanticConventions.AGI_DECISION_CONFIDENCE, confidence)
                yield span
        else:
            yield None

    @contextmanager
    def trace_guardian_request(self, operation_type: str, confidence: float):
        """Context manager for tracing a guardian approval request."""
        if self.tracer:
            with self.tracer.start_as_current_span("agi.guardian_request") as span:
                span.set_attribute("operation_type", operation_type)
                span.set_attribute(AGISemanticConventions.AGI_DECISION_CONFIDENCE, confidence)
                yield span
        else:
            yield None

    # =========================================================================
    # Metrics Recording Methods
    # =========================================================================

    def record_evaluation(self, decision: str, confidence: float,
                          execution_delta: float, component: str = "self_evaluation"):
        """Record a self-evaluation decision."""
        if self.metrics.evaluations_total:
            self.metrics.evaluations_total.labels(
                decision=decision,
                component=component
            ).inc()

        if self.metrics.confidence_distribution:
            self.metrics.confidence_distribution.observe(confidence)

        if self.metrics.execution_time_delta:
            self.metrics.execution_time_delta.observe(execution_delta)

        # Fallback
        self.fallback.record("agi_evaluation", 1, {
            "decision": decision,
            "confidence": str(confidence),
            "execution_delta": str(execution_delta)
        })

    def record_rollback(self, success: bool, reason: str = ""):
        """Record a rollback operation."""
        if self.metrics.rollbacks_total:
            self.metrics.rollbacks_total.labels(
                success=str(success).lower(),
                reason=reason
            ).inc()

        self.fallback.record("agi_rollback", 1, {
            "success": str(success),
            "reason": reason
        })

    def record_rollback_blocked(self, reason: str):
        """Record a blocked rollback."""
        if self.metrics.rollbacks_blocked:
            self.metrics.rollbacks_blocked.labels(reason=reason).inc()

        self.fallback.record("agi_rollback_blocked", 1, {"reason": reason})

    def record_guardian_approval(self, operation_type: str):
        """Record guardian approval."""
        if self.metrics.guardian_approvals:
            self.metrics.guardian_approvals.labels(
                operation_type=operation_type
            ).inc()

        self.fallback.record("agi_guardian_approval", 1, {
            "operation_type": operation_type
        })

    def record_guardian_rejection(self, operation_type: str, reason: str):
        """Record guardian rejection."""
        if self.metrics.guardian_rejections:
            self.metrics.guardian_rejections.labels(
                operation_type=operation_type,
                reason=reason
            ).inc()

        self.fallback.record("agi_guardian_rejection", 1, {
            "operation_type": operation_type,
            "reason": reason
        })

    def record_circuit_open(self):
        """Record circuit breaker opening."""
        if self.metrics.circuit_opens:
            self.metrics.circuit_opens.inc()

        self.fallback.record("agi_circuit_open", 1, {})

    def set_circuit_state(self, state: str):
        """Set circuit breaker state gauge."""
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        value = state_map.get(state.lower(), -1)

        if self.metrics.circuit_state:
            self.metrics.circuit_state.set(value)

        self.fallback.record("agi_circuit_state", value, {"state": state})

    def set_failure_count(self, count: int):
        """Set current failure count."""
        if self.metrics.failure_count:
            self.metrics.failure_count.set(count)

    def set_hourly_ops(self, count: int):
        """Set hourly destructive ops count."""
        if self.metrics.hourly_destructive_ops:
            self.metrics.hourly_destructive_ops.set(count)

    # =========================================================================
    # Decorator for Instrumentation
    # =========================================================================

    def instrument(self, operation_name: str = None):
        """Decorator to instrument a function with tracing and metrics."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                name = operation_name or func.__name__
                if self.tracer:
                    with self.tracer.start_as_current_span(f"agi.{name}") as span:
                        start = time.time()
                        try:
                            result = await func(*args, **kwargs)
                            span.set_attribute("success", True)
                            return result
                        except Exception as e:
                            span.set_attribute("success", False)
                            span.set_attribute("error", str(e))
                            span.record_exception(e)
                            raise
                        finally:
                            span.set_attribute("duration_ms", (time.time() - start) * 1000)
                else:
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                name = operation_name or func.__name__
                if self.tracer:
                    with self.tracer.start_as_current_span(f"agi.{name}") as span:
                        start = time.time()
                        try:
                            result = func(*args, **kwargs)
                            span.set_attribute("success", True)
                            return result
                        except Exception as e:
                            span.set_attribute("success", False)
                            span.set_attribute("error", str(e))
                            span.record_exception(e)
                            raise
                        finally:
                            span.set_attribute("duration_ms", (time.time() - start) * 1000)
                else:
                    return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator


# =============================================================================
# Global Instance
# =============================================================================

# Singleton instance
_observability: Optional[AGIObservability] = None


def get_observability() -> AGIObservability:
    """Get the global AGI observability instance."""
    global _observability
    if _observability is None:
        _observability = AGIObservability()
    return _observability


# =============================================================================
# Convenience Functions
# =============================================================================

def record_evaluation(decision: str, confidence: float, execution_delta: float):
    """Record a self-evaluation decision."""
    get_observability().record_evaluation(decision, confidence, execution_delta)


def record_rollback(success: bool, reason: str = ""):
    """Record a rollback operation."""
    get_observability().record_rollback(success, reason)


def record_rollback_blocked(reason: str):
    """Record a blocked rollback."""
    get_observability().record_rollback_blocked(reason)


def record_guardian_decision(approved: bool, operation_type: str, reason: str = ""):
    """Record guardian decision."""
    obs = get_observability()
    if approved:
        obs.record_guardian_approval(operation_type)
    else:
        obs.record_guardian_rejection(operation_type, reason)


def set_circuit_state(state: str):
    """Set circuit breaker state."""
    get_observability().set_circuit_state(state)


# =============================================================================
# Import guard for asyncio
# =============================================================================
import asyncio


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    # Initialize observability
    obs = get_observability()

    print("AGI Observability Test")
    print("=" * 40)
    print(f"OpenTelemetry available: {OTEL_AVAILABLE}")
    print(f"Prometheus available: {PROMETHEUS_AVAILABLE}")

    # Test metrics recording
    print("\nRecording test metrics...")
    obs.record_evaluation("keep", 0.85, -5.2)
    obs.record_evaluation("rollback", 0.35, 44.6)
    obs.record_rollback_blocked("low_confidence")
    obs.record_guardian_approval("test")
    obs.record_guardian_rejection("rollback", "confidence_below_threshold")
    obs.set_circuit_state("closed")

    print("Metrics recorded successfully")

    if PROMETHEUS_AVAILABLE:
        print(f"\nPrometheus metrics available at http://localhost:9091/metrics")
        print("Press Ctrl+C to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
