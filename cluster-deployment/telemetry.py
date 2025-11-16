#!/usr/bin/env python3
"""
OpenTelemetry Distributed Tracing for GitMQ Cluster
===================================================

Provides distributed tracing across cluster nodes for:
- Task execution tracking
- Cross-node request tracing
- Performance profiling
- Dependency visualization
- Error tracking

Features:
- OpenTelemetry instrumentation
- Automatic span creation
- Context propagation
- Multiple exporters (console, OTLP, Jaeger)
- Semantic conventions
- Correlation IDs

Trace Hierarchy:
```
Cluster Operation (root span)
├─ Task Submission (node: orchestrator)
├─ Code Transfer (node: orchestrator → worker)
├─ Approval Request (node: worker)
│  ├─ Risk Assessment
│  └─ Human Decision
├─ Task Execution (node: worker)
│  ├─ Sandbox Setup
│  ├─ Code Execution
│  └─ Result Collection
└─ Result Reporting (node: worker → orchestrator)
```

Usage:
    from telemetry import TracingManager

    # Initialize once per node
    tracing = TracingManager(service_name="macpro51-worker")

    # Create spans
    with tracing.start_span("task_execution") as span:
        span.set_attribute("task.id", task_id)
        span.set_attribute("task.type", task_type)

        # Nested spans
        with tracing.start_span("code_execution", parent=span):
            result = execute_code(code)

    # Propagate context across nodes
    context = tracing.extract_context()
    send_to_remote_node(task, context)
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

# OpenTelemetry imports (optional)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        BatchSpanProcessor,
        SimpleSpanProcessor
    )
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.trace import Status, StatusCode, SpanKind
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not available - tracing disabled")
    logger.warning("Install with: pip install opentelemetry-api opentelemetry-sdk")


@dataclass
class SpanAttributes:
    """Common span attributes for GitMQ operations."""

    # Task attributes
    TASK_ID = "task.id"
    TASK_TYPE = "task.type"
    TASK_TARGET_NODE = "task.target_node"
    TASK_PRIORITY = "task.priority"

    # Code execution attributes
    CODE_LANGUAGE = "code.language"
    CODE_SIZE_BYTES = "code.size_bytes"
    CODE_TRANSFER_METHOD = "code.transfer_method"

    # Approval attributes
    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_TIER = "approval.tier"
    APPROVAL_DECISION = "approval.decision"
    APPROVAL_APPROVER = "approval.approver"
    APPROVAL_CHANNEL = "approval.channel"

    # Risk attributes
    RISK_LEVEL = "risk.level"
    RISK_SCORE = "risk.score"

    # Execution attributes
    EXECUTION_STATUS = "execution.status"
    EXECUTION_EXIT_CODE = "execution.exit_code"
    EXECUTION_DURATION_MS = "execution.duration_ms"

    # Node attributes
    NODE_ID = "node.id"
    NODE_ROLE = "node.role"

    # Error attributes
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACK = "error.stack"


class NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key: str, value: Any):
        pass

    def set_status(self, status, description: str = ""):
        pass

    def record_exception(self, exception: Exception):
        pass

    def add_event(self, name: str, attributes: Optional[Dict] = None):
        pass


class TracingManager:
    """
    Manages OpenTelemetry distributed tracing.

    Provides simple API for creating and managing spans
    with automatic context propagation.
    """

    def __init__(
        self,
        service_name: str,
        enable_console_export: bool = False,
        enable_otlp_export: bool = False,
        otlp_endpoint: Optional[str] = None,
        node_id: Optional[str] = None,
        node_role: Optional[str] = None
    ):
        """
        Initialize tracing manager.

        Args:
            service_name: Service name for traces
            enable_console_export: Export to console (debugging)
            enable_otlp_export: Export to OTLP collector
            otlp_endpoint: OTLP endpoint URL
            node_id: Node identifier
            node_role: Node role (orchestrator, worker, builder)
        """
        self.service_name = service_name
        self.node_id = node_id
        self.node_role = node_role
        self.enabled = OTEL_AVAILABLE

        if not self.enabled:
            logger.warning("Tracing disabled - OpenTelemetry not available")
            self.tracer = None
            self.propagator = None
            return

        # Create resource with service metadata
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "node.id": node_id or "unknown",
            "node.role": node_role or "unknown"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add exporters
        if enable_console_export:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(console_exporter))
            logger.info("Console span exporter enabled")

        if enable_otlp_export and otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(f"OTLP span exporter enabled: {otlp_endpoint}")
            except ImportError:
                logger.warning("OTLP exporter not available - install opentelemetry-exporter-otlp")

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__)

        # Context propagator
        self.propagator = TraceContextTextMapPropagator()

        logger.info(f"Tracing initialized for {service_name}")

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        parent: Optional[Any] = None
    ):
        """
        Start a new span (context manager).

        Args:
            name: Span name
            kind: Span kind (server, client, internal)
            attributes: Initial attributes
            parent: Parent span (None for root)

        Yields:
            Span object
        """
        if not self.enabled or not self.tracer:
            yield NoOpSpan()
            return

        # Determine span kind
        span_kind = SpanKind.INTERNAL
        if kind == "server":
            span_kind = SpanKind.SERVER
        elif kind == "client":
            span_kind = SpanKind.CLIENT
        elif kind == "producer":
            span_kind = SpanKind.PRODUCER
        elif kind == "consumer":
            span_kind = SpanKind.CONSUMER

        # Start span
        with self.tracer.start_as_current_span(
            name,
            kind=span_kind,
            attributes=attributes or {}
        ) as span:
            # Add node metadata
            if self.node_id:
                span.set_attribute(SpanAttributes.NODE_ID, self.node_id)
            if self.node_role:
                span.set_attribute(SpanAttributes.NODE_ROLE, self.node_role)

            yield span

    def trace_task_submission(
        self,
        task_id: str,
        task_type: str,
        target_node: str
    ):
        """
        Create span for task submission.

        Returns span object (use as context manager).
        """
        return self.start_span(
            "task_submission",
            kind="producer",
            attributes={
                SpanAttributes.TASK_ID: task_id,
                SpanAttributes.TASK_TYPE: task_type,
                SpanAttributes.TASK_TARGET_NODE: target_node
            }
        )

    def trace_task_execution(
        self,
        task_id: str,
        task_type: str,
        code_language: Optional[str] = None
    ):
        """Create span for task execution."""
        attrs = {
            SpanAttributes.TASK_ID: task_id,
            SpanAttributes.TASK_TYPE: task_type
        }

        if code_language:
            attrs[SpanAttributes.CODE_LANGUAGE] = code_language

        return self.start_span(
            "task_execution",
            kind="server",
            attributes=attrs
        )

    def trace_approval_request(
        self,
        task_id: str,
        risk_level: str,
        risk_score: float,
        approval_tier: str
    ):
        """Create span for approval request."""
        return self.start_span(
            "approval_request",
            kind="internal",
            attributes={
                SpanAttributes.TASK_ID: task_id,
                SpanAttributes.RISK_LEVEL: risk_level,
                SpanAttributes.RISK_SCORE: risk_score,
                SpanAttributes.APPROVAL_TIER: approval_tier,
                SpanAttributes.APPROVAL_REQUIRED: True
            }
        )

    def trace_code_transfer(
        self,
        task_id: str,
        transfer_method: str,
        size_bytes: int
    ):
        """Create span for code transfer."""
        return self.start_span(
            "code_transfer",
            kind="client",
            attributes={
                SpanAttributes.TASK_ID: task_id,
                SpanAttributes.CODE_TRANSFER_METHOD: transfer_method,
                SpanAttributes.CODE_SIZE_BYTES: size_bytes
            }
        )

    def inject_context(self, carrier: Optional[Dict] = None) -> Dict[str, str]:
        """
        Inject trace context into carrier (for cross-node propagation).

        Args:
            carrier: Dictionary to inject into (created if None)

        Returns:
            Carrier with trace context
        """
        if not self.enabled or not self.propagator:
            return carrier or {}

        if carrier is None:
            carrier = {}

        self.propagator.inject(carrier)
        return carrier

    def extract_context(self, carrier: Dict[str, str]):
        """
        Extract trace context from carrier.

        Args:
            carrier: Dictionary with trace context

        Returns:
            Extracted context (use with start_as_current_span)
        """
        if not self.enabled or not self.propagator:
            return None

        return self.propagator.extract(carrier)

    def record_exception(self, span, exception: Exception):
        """Record exception on span."""
        if not self.enabled:
            return

        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))

    def set_span_success(self, span):
        """Mark span as successful."""
        if not self.enabled:
            return

        span.set_status(Status(StatusCode.OK))

    def set_span_error(self, span, error_message: str):
        """Mark span as error."""
        if not self.enabled:
            return

        span.set_status(Status(StatusCode.ERROR, error_message))


# ============================================================================
# Instrumentation Decorators
# ============================================================================

def trace_function(tracer: TracingManager, span_name: Optional[str] = None):
    """
    Decorator to automatically trace a function.

    Usage:
        @trace_function(tracing, "my_operation")
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__

            with tracer.start_span(name) as span:
                try:
                    result = func(*args, **kwargs)
                    tracer.set_span_success(span)
                    return result
                except Exception as e:
                    tracer.record_exception(span, e)
                    raise

        return wrapper
    return decorator


# ============================================================================
# Example Usage
# ============================================================================

def example_tracing():
    """Example: Distributed tracing."""
    print("\n" + "=" * 70)
    print("OpenTelemetry Tracing Example")
    print("=" * 70)

    # Initialize tracing
    tracing = TracingManager(
        service_name="gitMQ-worker",
        enable_console_export=True,
        node_id="macpro51",
        node_role="worker"
    )

    if not tracing.enabled:
        print("\n⚠️  OpenTelemetry not available - install dependencies:")
        print("   pip install opentelemetry-api opentelemetry-sdk")
        return

    print("\n1. Task execution trace:")

    # Simulate task execution with nested spans
    task_id = "task-trace-001"

    with tracing.trace_task_execution(task_id, "code_execution", "python") as exec_span:
        print(f"   Started task execution span")

        # Nested: Risk assessment
        with tracing.start_span("risk_assessment") as risk_span:
            risk_span.set_attribute(SpanAttributes.RISK_LEVEL, "medium")
            risk_span.set_attribute(SpanAttributes.RISK_SCORE, 0.45)
            print(f"   - Risk assessment")
            time.sleep(0.1)

        # Nested: Approval request
        with tracing.trace_approval_request(task_id, "medium", 0.45, "notification") as approval_span:
            approval_span.set_attribute(SpanAttributes.APPROVAL_DECISION, "auto_approved")
            print(f"   - Approval request")
            time.sleep(0.1)

        # Nested: Code execution
        with tracing.start_span("code_execution") as code_span:
            code_span.set_attribute(SpanAttributes.EXECUTION_STATUS, "success")
            code_span.set_attribute(SpanAttributes.EXECUTION_EXIT_CODE, 0)
            print(f"   - Code execution")
            time.sleep(0.2)
            tracing.set_span_success(code_span)

        tracing.set_span_success(exec_span)

    print("\n2. Context propagation:")

    # Inject context for cross-node propagation
    context_carrier = tracing.inject_context()
    print(f"   Injected context: {list(context_carrier.keys())}")

    # Simulate sending to remote node
    print(f"   → Sending to remote node...")

    # Remote node extracts context
    extracted_context = tracing.extract_context(context_carrier)
    print(f"   ← Received context on remote node")

    print("\n3. Error tracking:")

    # Simulate error
    with tracing.start_span("error_example") as error_span:
        try:
            raise ValueError("Example error for tracing")
        except Exception as e:
            tracing.record_exception(error_span, e)
            print(f"   ✓ Exception recorded in span")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_tracing()
    print("\nTelemetry module loaded successfully ✓")
