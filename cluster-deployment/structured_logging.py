#!/usr/bin/env python3
"""
Structured Logging for GitMQ Cluster
====================================

Provides structured JSON logging with:
- Correlation IDs for request tracking
- Contextual fields (node_id, task_id, etc.)
- Log levels with semantic meaning
- Integration with OpenTelemetry trace context
- Log aggregation support (Loki, Elasticsearch)

Features:
- Automatic correlation ID generation
- Thread-safe context propagation
- Performance-optimized JSON formatting
- Configurable output (console, file, syslog)
- Log sampling for high-volume scenarios

Usage:
    from structured_logging import get_logger

    logger = get_logger(__name__, node_id="macpro51")

    # Basic logging
    logger.info("Task started", task_id="task-123", task_type="code_execution")

    # With correlation
    with logger.correlation_context("req-456"):
        logger.info("Processing request")
        # All logs in this block have correlation_id="req-456"

    # Error logging
    try:
        ...
    except Exception as e:
        logger.error("Task failed", error=str(e), exc_info=True)
"""

import json
import logging
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional, Dict, Any

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON with standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - correlation_id: Request correlation ID
    - node_id: Node identifier
    - Additional contextual fields
    """

    def __init__(self, node_id: str = "unknown", include_trace_context: bool = True):
        super().__init__()
        self.node_id = node_id
        self.include_trace_context = include_trace_context

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base fields
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "node_id": self.node_id
        }

        # Add correlation ID if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add trace context if available and enabled
        if self.include_trace_context:
            try:
                from opentelemetry import trace
                span = trace.get_current_span()
                if span.get_span_context().is_valid:
                    ctx = span.get_span_context()
                    log_data["trace_id"] = format(ctx.trace_id, '032x')
                    log_data["span_id"] = format(ctx.span_id, '016x')
            except (ImportError, Exception):
                pass

        # Add custom fields from LogRecord
        if hasattr(record, 'custom_fields'):
            log_data.update(record.custom_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add source location
        log_data["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }

        return json.dumps(log_data)


class StructuredLogger:
    """
    Wrapper around Python logger with structured logging support.

    Provides convenience methods for adding contextual fields
    and managing correlation IDs.
    """

    def __init__(self, logger: logging.Logger, node_id: str):
        self._logger = logger
        self.node_id = node_id

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with contextual fields."""
        # Extract exc_info if present
        exc_info = kwargs.pop('exc_info', False)

        # Create custom LogRecord with extra fields
        extra = {'custom_fields': kwargs}

        self._logger.log(level, message, extra=extra, exc_info=exc_info)

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def correlation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for correlation ID.

        Usage:
            with logger.correlation_context("req-123"):
                logger.info("Processing request")
                # All logs have correlation_id="req-123"
        """
        return CorrelationContext(correlation_id)


class CorrelationContext:
    """Context manager for correlation IDs."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None

    def __enter__(self):
        self.token = correlation_id_var.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, *args):
        correlation_id_var.reset(self.token)


def get_logger(
    name: str,
    node_id: str = "unknown",
    level: int = logging.INFO,
    include_trace_context: bool = True
) -> StructuredLogger:
    """
    Get structured logger instance.

    Args:
        name: Logger name (usually __name__)
        node_id: Node identifier
        level: Log level
        include_trace_context: Include OpenTelemetry trace context

    Returns:
        StructuredLogger instance
    """
    # Get base logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    # Add console handler with structured formatter
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(node_id, include_trace_context))
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return StructuredLogger(logger, node_id)


# ============================================================================
# Example Usage
# ============================================================================

def example_structured_logging():
    """Example: Structured logging usage."""
    print("\n" + "=" * 70)
    print("Structured Logging Example")
    print("=" * 70)

    # Get logger
    logger = get_logger(__name__, node_id="macpro51", include_trace_context=False)

    print("\n1. Basic structured logging:")
    logger.info("System started", version="0.1.0", environment="production")

    print("\n2. Task execution logging:")
    logger.info(
        "Task submitted",
        task_id="task-123",
        task_type="code_execution",
        target_node="macpro51",
        priority=5
    )

    print("\n3. Correlation context:")
    with logger.correlation_context("req-456"):
        logger.info("Processing request", step="validation")
        logger.info("Request validated", duration_ms=50)
        logger.info("Executing request", step="execution")

    print("\n4. Error logging:")
    try:
        raise ValueError("Example error for logging")
    except Exception as e:
        logger.error(
            "Task execution failed",
            task_id="task-123",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True
        )

    print("\n5. Performance logging:")
    start_time = time.time()
    time.sleep(0.1)
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        "Operation completed",
        operation="data_processing",
        duration_ms=duration_ms,
        records_processed=1000,
        success=True
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_structured_logging()
    print("\nStructured logging module loaded successfully ✓")
