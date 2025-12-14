"""
Production monitoring and observability system.

Implements comprehensive metrics collection, distributed tracing,
health checks, and alerting for enterprise deployment.
"""

import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from loguru import logger
import redis
from dataclasses import dataclass
from enum import Enum


# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# OTLP exporters for distributed tracing
span_exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(span_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Metrics setup
metric_reader = PeriodicExportingMetricReader(
    exporter=OTLPMetricExporter(endpoint="localhost:4317", insecure=True),
    export_interval_millis=10000
)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
meter = metrics.get_meter(__name__)

# Redis for distributed metrics
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Prometheus metrics registry
registry = CollectorRegistry()

# Application metrics
request_count = Counter(
    'synthetic_data_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_duration = Histogram(
    'synthetic_data_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

active_requests = Gauge(
    'synthetic_data_active_requests',
    'Number of active requests',
    registry=registry
)

generation_count = Counter(
    'synthetic_data_generations_total',
    'Total number of synthetic data generations',
    ['domain', 'status'],
    registry=registry
)

generation_duration = Histogram(
    'synthetic_data_generation_duration_seconds',
    'Generation duration in seconds',
    ['domain', 'record_count_bucket'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    registry=registry
)

privacy_budget_used = Gauge(
    'synthetic_data_privacy_budget_used',
    'Privacy budget consumption',
    ['domain'],
    registry=registry
)

compliance_violations = Counter(
    'synthetic_data_compliance_violations_total',
    'Total compliance violations detected',
    ['framework', 'severity'],
    registry=registry
)

cache_hits = Counter(
    'synthetic_data_cache_hits_total',
    'Cache hit count',
    ['cache_type'],
    registry=registry
)

cache_misses = Counter(
    'synthetic_data_cache_misses_total',
    'Cache miss count',
    ['cache_type'],
    registry=registry
)

error_count = Counter(
    'synthetic_data_errors_total',
    'Total error count',
    ['error_type', 'component'],
    registry=registry
)

# System metrics
cpu_usage = Gauge(
    'synthetic_data_cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

memory_usage = Gauge(
    'synthetic_data_memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

disk_usage = Gauge(
    'synthetic_data_disk_usage_percent',
    'Disk usage percentage',
    registry=registry
)

# Database metrics
db_connections = Gauge(
    'synthetic_data_db_connections',
    'Database connection pool size',
    ['state'],
    registry=registry
)

db_query_duration = Histogram(
    'synthetic_data_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    registry=registry
)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class MetricsCollector:
    """Centralized metrics collection service."""
    
    def __init__(self):
        self.start_time = time.time()
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background metric collection tasks."""
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._collect_application_metrics())
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics periodically."""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_usage.set(memory.used)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_usage.set(disk.percent)
                
                # Log if resources are high
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                if memory.percent > 80:
                    logger.warning(f"High memory usage: {memory.percent}%")
                if disk.percent > 80:
                    logger.warning(f"High disk usage: {disk.percent}%")
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            
            await asyncio.sleep(10)  # Collect every 10 seconds
    
    async def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        while True:
            try:
                # Collect from Redis
                active_generations = redis_client.get("active_generations") or 0
                active_requests.set(int(active_generations))
                
                # Calculate uptime
                uptime = time.time() - self.start_time
                redis_client.set("app_uptime", uptime)
                
            except Exception as e:
                logger.error(f"Error collecting application metrics: {e}")
            
            await asyncio.sleep(5)
    
    @contextmanager
    def track_request(self, method: str, endpoint: str):
        """Context manager to track request metrics."""
        start_time = time.time()
        active_requests.inc()
        
        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            error_count.labels(error_type=type(e).__name__, component="api").inc()
            raise
        finally:
            duration = time.time() - start_time
            request_count.labels(method=method, endpoint=endpoint, status=status).inc()
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            active_requests.dec()
    
    def track_generation(
        self,
        domain: str,
        record_count: int,
        success: bool,
        duration: float
    ):
        """Track synthetic data generation metrics."""
        status = "success" if success else "failure"
        generation_count.labels(domain=domain, status=status).inc()
        
        # Bucket record count for histogram
        if record_count <= 100:
            bucket = "0-100"
        elif record_count <= 1000:
            bucket = "100-1000"
        elif record_count <= 10000:
            bucket = "1000-10000"
        else:
            bucket = "10000+"
        
        generation_duration.labels(
            domain=domain,
            record_count_bucket=bucket
        ).observe(duration)
        
        # Store in Redis for trending
        redis_client.hincrby(f"generation_stats:{domain}", status, 1)
        redis_client.hincrbyfloat(f"generation_times:{domain}", "total", duration)
        redis_client.hincrby(f"generation_times:{domain}", "count", 1)
    
    def track_privacy_budget(self, domain: str, epsilon_used: float):
        """Track privacy budget consumption."""
        current = float(redis_client.hget("privacy_budget", domain) or 0)
        new_total = current + epsilon_used
        redis_client.hset("privacy_budget", domain, new_total)
        privacy_budget_used.labels(domain=domain).set(new_total)
    
    def track_compliance_violation(
        self,
        framework: str,
        severity: str,
        details: Dict[str, Any]
    ):
        """Track compliance violations."""
        compliance_violations.labels(framework=framework, severity=severity).inc()
        
        # Store violation details
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "framework": framework,
            "severity": severity,
            "details": details
        }
        redis_client.lpush("compliance_violations", str(violation))
        redis_client.ltrim("compliance_violations", 0, 1000)  # Keep last 1000
    
    def track_cache_access(self, cache_type: str, hit: bool):
        """Track cache hit/miss rates."""
        if hit:
            cache_hits.labels(cache_type=cache_type).inc()
        else:
            cache_misses.labels(cache_type=cache_type).inc()
    
    def track_database_query(self, query_type: str, duration: float):
        """Track database query performance."""
        db_query_duration.labels(query_type=query_type).observe(duration)


class HealthCheckService:
    """Comprehensive health check service."""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.register("database", self._check_database)
        self.register("redis", self._check_redis)
        self.register("disk_space", self._check_disk_space)
        self.register("memory", self._check_memory)
        self.register("api_keys", self._check_api_keys)
    
    def register(self, name: str, check_func: Callable):
        """Register a health check."""
        self.checks[name] = check_func
    
    async def _check_database(self) -> HealthCheck:
        """Check database connectivity."""
        try:
            # Check database connection
            from sqlalchemy import create_engine, text
            engine = create_engine("postgresql://localhost/synthetic_data")
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database is accessible",
                details={"connected": True},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_redis(self) -> HealthCheck:
        """Check Redis connectivity."""
        try:
            redis_client.ping()
            info = redis_client.info()
            
            return HealthCheck(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis is accessible",
                details={
                    "connected": True,
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients")
                },
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        disk = psutil.disk_usage('/')
        status = HealthStatus.HEALTHY
        
        if disk.percent > 90:
            status = HealthStatus.UNHEALTHY
        elif disk.percent > 80:
            status = HealthStatus.DEGRADED
        
        return HealthCheck(
            name="disk_space",
            status=status,
            message=f"Disk usage: {disk.percent}%",
            details={
                "percent_used": disk.percent,
                "free_bytes": disk.free,
                "total_bytes": disk.total
            },
            timestamp=datetime.utcnow()
        )
    
    async def _check_memory(self) -> HealthCheck:
        """Check memory usage."""
        memory = psutil.virtual_memory()
        status = HealthStatus.HEALTHY
        
        if memory.percent > 90:
            status = HealthStatus.UNHEALTHY
        elif memory.percent > 80:
            status = HealthStatus.DEGRADED
        
        return HealthCheck(
            name="memory",
            status=status,
            message=f"Memory usage: {memory.percent}%",
            details={
                "percent_used": memory.percent,
                "available_bytes": memory.available,
                "total_bytes": memory.total
            },
            timestamp=datetime.utcnow()
        )
    
    async def _check_api_keys(self) -> HealthCheck:
        """Check API key validity."""
        try:
            # Check if OpenAI API key is set
            import os
            has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
            
            if not has_openai_key:
                return HealthCheck(
                    name="api_keys",
                    status=HealthStatus.DEGRADED,
                    message="OpenAI API key not configured",
                    details={"openai_configured": False},
                    timestamp=datetime.utcnow()
                )
            
            return HealthCheck(
                name="api_keys",
                status=HealthStatus.HEALTHY,
                message="API keys configured",
                details={"openai_configured": True},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            return HealthCheck(
                name="api_keys",
                status=HealthStatus.UNHEALTHY,
                message=f"API key check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.utcnow()
            )
    
    async def check_health(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[name] = {
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                    "timestamp": result.timestamp.isoformat()
                }
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f"Check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }


class DistributedTracing:
    """Distributed tracing for request tracking."""
    
    @staticmethod
    def trace_operation(operation_name: str):
        """Decorator for tracing operations."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(operation_name) as span:
                    # Add span attributes
                    span.set_attribute("operation.name", operation_name)
                    span.set_attribute("operation.start_time", datetime.utcnow().isoformat())
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("operation.status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("operation.status", "error")
                        span.set_attribute("operation.error", str(e))
                        span.record_exception(e)
                        raise
                    finally:
                        span.set_attribute("operation.end_time", datetime.utcnow().isoformat())
            
            return wrapper
        return decorator
    
    @staticmethod
    def get_trace_id() -> Optional[str]:
        """Get current trace ID."""
        span = trace.get_current_span()
        if span and span.is_recording():
            return format(span.get_span_context().trace_id, '032x')
        return None


class AlertingService:
    """Service for sending alerts based on metrics."""
    
    def __init__(self):
        self.alert_rules = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alerting rules."""
        self.add_rule(
            name="high_error_rate",
            condition=lambda: self._check_error_rate() > 0.05,
            message="Error rate exceeds 5%",
            severity="critical"
        )
        
        self.add_rule(
            name="high_cpu_usage",
            condition=lambda: psutil.cpu_percent() > 90,
            message="CPU usage exceeds 90%",
            severity="warning"
        )
        
        self.add_rule(
            name="low_disk_space",
            condition=lambda: psutil.disk_usage('/').percent > 90,
            message="Disk usage exceeds 90%",
            severity="critical"
        )
    
    def add_rule(
        self,
        name: str,
        condition: Callable,
        message: str,
        severity: str = "warning"
    ):
        """Add alerting rule."""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "message": message,
            "severity": severity
        })
    
    def _check_error_rate(self) -> float:
        """Calculate current error rate."""
        # Get counts from Redis
        total_requests = int(redis_client.get("total_requests") or 1)
        total_errors = int(redis_client.get("total_errors") or 0)
        return total_errors / total_requests if total_requests > 0 else 0
    
    async def check_alerts(self):
        """Check all alert conditions."""
        alerts = []
        
        for rule in self.alert_rules:
            try:
                if rule["condition"]():
                    alert = {
                        "name": rule["name"],
                        "message": rule["message"],
                        "severity": rule["severity"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    alerts.append(alert)
                    
                    # Log alert
                    logger.warning(f"ALERT: {rule['message']} (severity: {rule['severity']})")
                    
                    # Store in Redis
                    redis_client.lpush("alerts", str(alert))
                    redis_client.ltrim("alerts", 0, 100)  # Keep last 100 alerts
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
        
        return alerts


# Global instances
metrics_collector = MetricsCollector()
health_service = HealthCheckService()
alerting_service = AlertingService()


def get_metrics() -> bytes:
    """Generate Prometheus metrics."""
    return generate_latest(registry)