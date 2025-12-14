#!/usr/bin/env python3
"""
Phase 4 Test Suite: Observability & Monitoring
==============================================

Comprehensive tests for Phase 4 components:
- OpenTelemetry distributed tracing
- Prometheus metrics collection
- Structured JSON logging
- Grafana dashboard generation
- Observability integration

Test Categories:
    1. Tracing Tests (span creation, context propagation, attributes)
    2. Metrics Tests (counter, gauge, histogram, HTTP server)
    3. Logging Tests (structured formatting, correlation, trace context)
    4. Dashboard Tests (generation, panel types, queries)
    5. Integration Tests (end-to-end observability)

Usage:
    # Run all tests
    python3 test_phase4.py

    # Run specific test suite
    python3 test_phase4.py TestTracing
    python3 test_phase4.py TestMetrics
"""

import unittest
import json
import time
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import Phase 4 components
from telemetry import TracingManager, SpanAttributes
from metrics import MetricsCollector
from structured_logging import get_logger, StructuredFormatter, correlation_id_var
from observability_integration import ObservabilityManager, ObservabilityConfig


class TestTracing(unittest.TestCase):
    """Test OpenTelemetry distributed tracing."""

    def setUp(self):
        """Create tracing manager."""
        self.tracing = TracingManager(
            service_name="test-service",
            enable_console_export=False,
            node_id="test-node",
            node_role="test"
        )

    def test_tracing_initialization(self):
        """Test tracing manager initialization."""
        self.assertEqual(self.tracing.service_name, "test-service")
        self.assertEqual(self.tracing.node_id, "test-node")
        self.assertEqual(self.tracing.node_role, "test")

    def test_start_span(self):
        """Test span creation."""
        with self.tracing.start_span("test_span") as span:
            self.assertIsNotNone(span)
            span.set_attribute("test_key", "test_value")

    def test_span_attributes(self):
        """Test span attribute constants."""
        self.assertEqual(SpanAttributes.TASK_ID, "task.id")
        self.assertEqual(SpanAttributes.TASK_TYPE, "task.type")
        self.assertEqual(SpanAttributes.RISK_LEVEL, "risk.level")

    def test_trace_task_execution(self):
        """Test task execution span creation."""
        with self.tracing.trace_task_execution("task-123", "code_execution", "python") as span:
            self.assertIsNotNone(span)

    def test_trace_approval_request(self):
        """Test approval request span creation."""
        with self.tracing.trace_approval_request("task-123", "medium", 0.45, "notification") as span:
            self.assertIsNotNone(span)

    def test_trace_code_transfer(self):
        """Test code transfer span creation."""
        with self.tracing.trace_code_transfer("task-123", "inline", 1024) as span:
            self.assertIsNotNone(span)

    def test_context_injection(self):
        """Test trace context injection."""
        carrier = {}
        self.tracing.inject_context(carrier)
        # Carrier should have trace context (if tracing enabled)
        if self.tracing.enabled:
            self.assertTrue(len(carrier) > 0)

    def test_nested_spans(self):
        """Test nested span hierarchy."""
        with self.tracing.start_span("parent") as parent_span:
            self.assertIsNotNone(parent_span)
            with self.tracing.start_span("child") as child_span:
                self.assertIsNotNone(child_span)


class TestMetrics(unittest.TestCase):
    """Test Prometheus metrics collection."""

    def setUp(self):
        """Create metrics collector."""
        # Use non-standard port to avoid conflicts
        self.metrics = MetricsCollector(
            node_id="test-node",
            node_role="test",
            port=9199  # Different from default 9100
        )

    def test_metrics_initialization(self):
        """Test metrics collector initialization."""
        self.assertEqual(self.metrics.node_id, "test-node")
        self.assertEqual(self.metrics.node_role, "test")

    def test_task_submission(self):
        """Test task submission counter."""
        if self.metrics.enabled:
            # Test recording - should not raise exception
            self.metrics.record_task_submission("task-123", "code_execution", "test-node")
            self.assertTrue(True)

    def test_task_completion(self):
        """Test task completion counter."""
        if self.metrics.enabled:
            self.metrics.record_task_completion("code_execution")
            # Should not raise exception

    def test_task_failure(self):
        """Test task failure counter."""
        if self.metrics.enabled:
            self.metrics.record_task_failure("code_execution", "ValueError")
            # Should not raise exception

    def test_approval_request(self):
        """Test approval request counter."""
        if self.metrics.enabled:
            self.metrics.record_approval_request("medium", "notification")
            # Should not raise exception

    def test_approval_decision(self):
        """Test approval decision recording."""
        if self.metrics.enabled:
            self.metrics.record_approval_decision(
                "approved",
                "cli",
                "medium",
                5.0
            )
            # Should not raise exception

    def test_risk_assessment(self):
        """Test risk assessment metrics."""
        if self.metrics.enabled:
            self.metrics.record_risk_assessment(
                "medium",
                0.45,
                "notification",
                "code_execution"
            )
            # Should not raise exception

    def test_code_transfer(self):
        """Test code transfer metrics."""
        if self.metrics.enabled:
            self.metrics.record_code_transfer("inline", 1024, 0.5)
            # Should not raise exception

    def test_error_recording(self):
        """Test error counter."""
        if self.metrics.enabled:
            self.metrics.record_error("ValueError", "daemon")
            # Should not raise exception

    def test_task_execution_context(self):
        """Test task execution context manager."""
        if self.metrics.enabled:
            with self.metrics.track_task_execution("task-123", "code_execution"):
                time.sleep(0.01)
            # Should not raise exception


class TestStructuredLogging(unittest.TestCase):
    """Test structured JSON logging."""

    def setUp(self):
        """Create structured logger."""
        self.logger = get_logger(
            "test-logger",
            node_id="test-node",
            include_trace_context=False
        )

    def test_logger_initialization(self):
        """Test logger initialization."""
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.node_id, "test-node")

    def test_info_logging(self):
        """Test info level logging."""
        self.logger.info("Test message", test_key="test_value")
        # Should not raise exception

    def test_error_logging(self):
        """Test error level logging."""
        try:
            raise ValueError("Test error")
        except Exception:
            self.logger.error("Test error logging", exc_info=True)
        # Should not raise exception

    def test_correlation_context(self):
        """Test correlation ID context manager."""
        with self.logger.correlation_context("test-correlation-123") as correlation_id:
            self.assertEqual(correlation_id, "test-correlation-123")
            # Verify context variable is set
            self.assertEqual(correlation_id_var.get(), "test-correlation-123")

        # Verify context variable is cleared
        self.assertIsNone(correlation_id_var.get())

    def test_correlation_auto_generation(self):
        """Test automatic correlation ID generation."""
        with self.logger.correlation_context() as correlation_id:
            self.assertIsNotNone(correlation_id)
            # Should be UUID format
            self.assertTrue(len(correlation_id) > 0)

    def test_structured_formatter(self):
        """Test JSON formatter."""
        formatter = StructuredFormatter(node_id="test-node", include_trace_context=False)

        # Create mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Format record
        formatted = formatter.format(record)

        # Should be valid JSON
        log_data = json.loads(formatted)
        self.assertEqual(log_data["message"], "Test message")
        self.assertEqual(log_data["level"], "INFO")
        self.assertEqual(log_data["node_id"], "test-node")


class TestDashboards(unittest.TestCase):
    """Test Grafana dashboard generation."""

    def test_dashboard_import(self):
        """Test importing dashboard generator."""
        from grafana_dashboards import GrafanaDashboardGenerator
        self.assertIsNotNone(GrafanaDashboardGenerator)

    def test_generator_initialization(self):
        """Test dashboard generator initialization."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator(datasource="Prometheus")
        self.assertEqual(generator.datasource, "Prometheus")

    def test_cluster_overview_dashboard(self):
        """Test cluster overview dashboard generation."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator()
        dashboard = generator.create_cluster_overview_dashboard()

        self.assertIn("dashboard", dashboard)
        self.assertEqual(dashboard["dashboard"]["title"], "GitMQ Cluster Overview")
        self.assertIsInstance(dashboard["dashboard"]["panels"], list)
        self.assertTrue(len(dashboard["dashboard"]["panels"]) > 0)

    def test_task_execution_dashboard(self):
        """Test task execution dashboard generation."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator()
        dashboard = generator.create_task_execution_dashboard()

        self.assertEqual(dashboard["dashboard"]["title"], "GitMQ Task Execution")

    def test_approval_risk_dashboard(self):
        """Test approval/risk dashboard generation."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator()
        dashboard = generator.create_approval_risk_dashboard()

        self.assertEqual(dashboard["dashboard"]["title"], "GitMQ Approval & Risk Assessment")

    def test_code_transfer_dashboard(self):
        """Test code transfer dashboard generation."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator()
        dashboard = generator.create_code_transfer_dashboard()

        self.assertEqual(dashboard["dashboard"]["title"], "GitMQ Code Transfer Performance")

    def test_system_health_dashboard(self):
        """Test system health dashboard generation."""
        from grafana_dashboards import GrafanaDashboardGenerator
        generator = GrafanaDashboardGenerator()
        dashboard = generator.create_system_health_dashboard()

        self.assertEqual(dashboard["dashboard"]["title"], "GitMQ System Health")

    def test_dashboard_export(self):
        """Test dashboard export to files."""
        from grafana_dashboards import GrafanaDashboardGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = GrafanaDashboardGenerator()
            generator.export_all_dashboards(output_dir=tmpdir)

            # Verify all dashboards were created
            dashboards = [
                "cluster_overview.json",
                "task_execution.json",
                "approval_risk.json",
                "code_transfer.json",
                "system_health.json"
            ]

            for dashboard_file in dashboards:
                path = Path(tmpdir) / dashboard_file
                self.assertTrue(path.exists())

                # Verify it's valid JSON
                with open(path) as f:
                    data = json.load(f)
                    self.assertIn("dashboard", data)


class TestObservabilityIntegration(unittest.TestCase):
    """Test unified observability integration."""

    def setUp(self):
        """Create observability manager."""
        config = ObservabilityConfig(
            node_id="test-node",
            node_role="test",
            enable_tracing=True,
            enable_metrics=True,
            enable_structured_logging=True,
            metrics_port=9198  # Non-standard port
        )
        self.obs = ObservabilityManager(config)

    def test_initialization(self):
        """Test observability manager initialization."""
        self.assertIsNotNone(self.obs)
        self.assertEqual(self.obs.config.node_id, "test-node")

    def test_track_task_execution(self):
        """Test task execution tracking."""
        with self.obs.track_task_execution("task-123", "code_execution", "python"):
            time.sleep(0.01)
        # Should not raise exception

    def test_track_approval_request(self):
        """Test approval request tracking."""
        with self.obs.track_approval_request("task-123", "medium", 0.45, "notification"):
            time.sleep(0.01)
        # Should not raise exception

    def test_track_code_transfer(self):
        """Test code transfer tracking."""
        with self.obs.track_code_transfer("task-123", "inline", 1024):
            time.sleep(0.01)
        # Should not raise exception

    def test_record_approval_decision(self):
        """Test approval decision recording."""
        self.obs.record_approval_decision(
            task_id="task-123",
            decision="approved",
            approver="human",
            channel="cli",
            risk_level="medium",
            decision_time_seconds=5.0
        )
        # Should not raise exception

    def test_record_risk_assessment(self):
        """Test risk assessment recording."""
        self.obs.record_risk_assessment(
            task_id="task-123",
            risk_level="medium",
            risk_score=0.45,
            approval_tier="notification",
            task_type="code_execution",
            risk_factors={"scope": 0.3, "criticality": 0.5}
        )
        # Should not raise exception

    def test_record_error(self):
        """Test error recording."""
        self.obs.record_error(
            error_type="ValueError",
            component="daemon",
            error_message="Test error",
            task_id="task-123"
        )
        # Should not raise exception

    def test_correlation_context(self):
        """Test correlation context."""
        with self.obs.correlation_context("test-correlation-456"):
            self.obs.logger.info("Test message in correlation context")
        # Should not raise exception

    def test_context_propagation(self):
        """Test trace context injection/extraction."""
        carrier = self.obs.inject_trace_context()
        self.assertIsNotNone(carrier)

        # Extract context
        context = self.obs.extract_trace_context(carrier)
        # Should not raise exception


class TestEndToEnd(unittest.TestCase):
    """End-to-end observability tests."""

    def test_complete_task_workflow(self):
        """Test complete task workflow with observability."""
        # Create observability manager
        obs = ObservabilityManager(
            node_id="test-node",
            node_role="test",
            enable_tracing=True,
            enable_metrics=True,
            enable_structured_logging=True,
            enable_console_tracing=False,
            metrics_port=9197
        )

        task_id = "task-e2e-001"

        # 1. Track task execution
        with obs.track_task_execution(task_id, "code_execution", "python"):
            # 2. Record risk assessment
            obs.record_risk_assessment(
                task_id=task_id,
                risk_level="medium",
                risk_score=0.45,
                approval_tier="notification",
                task_type="code_execution"
            )

            # 3. Track approval request
            with obs.track_approval_request(task_id, "medium", 0.45, "notification"):
                time.sleep(0.01)

            # 4. Record approval decision
            obs.record_approval_decision(
                task_id=task_id,
                decision="approved",
                approver="human",
                channel="cli",
                risk_level="medium",
                decision_time_seconds=0.01
            )

            # 5. Track code transfer
            with obs.track_code_transfer(task_id, "inline", 1024):
                time.sleep(0.01)

            # 6. Simulate task execution
            time.sleep(0.05)

        # Should not raise exception
        self.assertTrue(True)

    def test_error_workflow(self):
        """Test error handling workflow."""
        obs = ObservabilityManager(
            node_id="test-node",
            node_role="test",
            metrics_port=9196
        )

        task_id = "task-error-001"

        try:
            with obs.track_task_execution(task_id, "code_execution"):
                # Simulate error
                raise ValueError("Test error")
        except ValueError:
            # Record error
            obs.record_error(
                error_type="ValueError",
                component="task_execution",
                error_message="Test error",
                task_id=task_id
            )

        # Should not raise exception (error was caught and recorded)
        self.assertTrue(True)


def run_test_suite():
    """Run comprehensive Phase 4 test suite."""
    print("\n" + "=" * 70)
    print("Phase 4: Observability & Monitoring - Test Suite")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestTracing))
    suite.addTests(loader.loadTestsFromTestCase(TestMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestStructuredLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestDashboards))
    suite.addTests(loader.loadTestsFromTestCase(TestObservabilityIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed")

    print("=" * 70)

    return result


if __name__ == "__main__":
    import sys

    # Allow running specific test classes
    if len(sys.argv) > 1:
        unittest.main()
    else:
        result = run_test_suite()
        sys.exit(0 if result.wasSuccessful() else 1)
