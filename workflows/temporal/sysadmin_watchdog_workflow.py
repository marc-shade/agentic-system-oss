#!/usr/bin/env python3
"""
SysAdmin Watchdog Workflow
Persistent background monitoring for all services

Features:
- Monitors services every 60 seconds
- Non-intrusive - never interrupts development
- Triggers auto-recovery when issues detected
- Development mode awareness - pauses during active changes
- Arduino Surface LED integration for visual status

STATUS: Production Ready
"""

import asyncio
import logging
import json
import os
import subprocess
from datetime import timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service definitions matching verify_kutiraai_dashboard.sh exactly
MONITORED_SERVICES = {
    # 1. KutiraAI Backend Services
    "kutiraai": {
        "frontend_dashboard": {"port": 3100, "health": "/", "critical": False},
        "agentic_framework": {"port": 4100, "health": "/api/v1/health", "critical": False},
        "api_server": {"port": 3002, "health": "/api/health", "critical": False},
        "port_manager": {"port": 4102, "health": "/health", "critical": False},
        "n8n_workflows": {"port": 5678, "health": "/healthz", "critical": False},
        "autokitteh": {"port": 9980, "health": "/", "critical": False},
    },
    # 2. Voice Mode Services
    "voice": {
        "whisper_stt": {"port": 2022, "health": "/health", "critical": True},
        "kokoro_tts": {"port": 8880, "health": "/health", "critical": True},
        "voice_broker_main": {"port": 9091, "health": "/health", "critical": False},
        "voice_broker_admin": {"port": 9092, "health": "/health", "critical": False},
        "voice_cache": {"port": 9093, "health": "/health", "critical": False},
        "voice_feedback": {"port": 9050, "health": "/health", "critical": False},
        "livekit_server": {"port": 7880, "health": "/", "critical": False},
    },
    # 3. Core Workflow Services
    "workflow": {
        "temporal": {"check": "process", "pattern": "temporal server", "critical": True},
    },
    # 4. Ember (Tamagotchi) System
    "ember": {
        "ember_mcp": {"check": "process", "pattern": "ember-mcp", "critical": False},
    },
    # 5. Core MCP Servers
    "mcp": {
        "enhanced_memory": {"check": "process", "pattern": "enhanced-memory", "critical": True},
        "agent_runtime": {"check": "process", "pattern": "agent-runtime-mcp", "critical": True},
        "sequential_thinking": {"check": "process", "pattern": "sequential-thinking", "critical": False},
        "voice_mode": {"check": "process", "pattern": "voicemode", "critical": True},
        "chrome_devtools": {"check": "process", "pattern": "chrome-devtools", "critical": False},
    },
    # 6. Database Services
    "database": {
        "postgresql": {"port": 5432, "health": None, "critical": False, "check": "tcp"},
    },
    # 7. Hardware
    "hardware": {
        "arduino_surface": {"host": "macpro51", "port": 8200, "health": "/status", "critical": False},
    }
}

# Development mode detection paths
DEV_WATCH_PATHS = [
    "/Volumes/FILES/code/kutiraai",
    "/Volumes/SSDRAID0/agentic-system/mcp-servers",
    "/Users/marc/.claude",
]

@dataclass
class ServiceStatus:
    name: str
    category: str
    healthy: bool
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    last_check: Optional[str] = None

@dataclass
class SystemHealthReport:
    timestamp: str
    overall_status: str  # "healthy", "degraded", "critical"
    services_checked: int
    services_healthy: int
    services_degraded: List[str]
    services_critical: List[str]
    dev_mode_active: bool
    arduino_notified: bool


@activity.defn
async def check_http_service(name: str, port: int, health_path: str) -> ServiceStatus:
    """Check HTTP service health endpoint"""
    import aiohttp
    import time

    url = f"http://localhost:{port}{health_path}"
    start = time.time()

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                elapsed = (time.time() - start) * 1000
                if response.status == 200:
                    return ServiceStatus(
                        name=name,
                        category="http",
                        healthy=True,
                        response_time_ms=elapsed
                    )
                else:
                    return ServiceStatus(
                        name=name,
                        category="http",
                        healthy=False,
                        error=f"HTTP {response.status}"
                    )
    except Exception as e:
        return ServiceStatus(
            name=name,
            category="http",
            healthy=False,
            error=str(e)[:100]
        )


@activity.defn
async def check_process_service(name: str, process_pattern: str) -> ServiceStatus:
    """Check if a process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_pattern],
            capture_output=True,
            timeout=5
        )
        healthy = result.returncode == 0
        return ServiceStatus(
            name=name,
            category="process",
            healthy=healthy,
            error=None if healthy else "Process not found"
        )
    except Exception as e:
        return ServiceStatus(
            name=name,
            category="process",
            healthy=False,
            error=str(e)[:100]
        )


@activity.defn
async def check_tcp_service(name: str, host: str, port: int) -> ServiceStatus:
    """Check if TCP port is accepting connections"""
    import socket
    import time

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        elapsed = (time.time() - start) * 1000
        sock.close()

        if result == 0:
            return ServiceStatus(
                name=name,
                category="tcp",
                healthy=True,
                response_time_ms=elapsed
            )
        else:
            return ServiceStatus(
                name=name,
                category="tcp",
                healthy=False,
                error=f"Connection refused (code {result})"
            )
    except Exception as e:
        return ServiceStatus(
            name=name,
            category="tcp",
            healthy=False,
            error=str(e)[:100]
        )


@activity.defn
async def check_remote_http_service(name: str, host: str, port: int, health_path: str) -> ServiceStatus:
    """Check HTTP service on a remote host"""
    import aiohttp
    import time

    url = f"http://{host}:{port}{health_path}"
    start = time.time()

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                elapsed = (time.time() - start) * 1000
                if response.status == 200:
                    return ServiceStatus(
                        name=name,
                        category="remote_http",
                        healthy=True,
                        response_time_ms=elapsed
                    )
                else:
                    return ServiceStatus(
                        name=name,
                        category="remote_http",
                        healthy=False,
                        error=f"HTTP {response.status}"
                    )
    except Exception as e:
        return ServiceStatus(
            name=name,
            category="remote_http",
            healthy=False,
            error=str(e)[:100]
        )


@activity.defn
async def check_dev_mode_active() -> bool:
    """Check if development mode is active (recent file changes)"""
    import time

    threshold_seconds = 30  # Files changed in last 30 seconds = dev mode
    current_time = time.time()

    for path in DEV_WATCH_PATHS:
        if not os.path.exists(path):
            continue
        try:
            # Check for recently modified files
            result = subprocess.run(
                ["find", path, "-type", "f", "-mtime", "-30s", "-name", "*.py", "-o", "-name", "*.js", "-o", "-name", "*.ts"],
                capture_output=True,
                timeout=10
            )
            if result.stdout.strip():
                return True
        except:
            pass

    return False


@activity.defn
async def update_arduino_status(status: str, services_down: List[str]) -> bool:
    """Update Arduino Surface LED based on system status"""
    try:
        import aiohttp

        # Map status to LED colors
        led_colors = {
            "healthy": {"r": 0, "g": 255, "b": 0},      # Green
            "degraded": {"r": 255, "g": 165, "b": 0},   # Orange
            "critical": {"r": 255, "g": 0, "b": 0},     # Red
            "dev_mode": {"r": 0, "g": 0, "b": 255},     # Blue
        }

        color = led_colors.get(status, led_colors["degraded"])

        # Try remote Arduino (macpro51), then local fallbacks
        urls = [
            "http://macpro51:8200/led",
            "http://localhost:8200/led",
            "http://192.168.1.27:8200/led"
        ]

        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for url in urls:
                try:
                    async with session.post(url, json=color) as response:
                        if response.status == 200:
                            return True
                except:
                    continue

        return False
    except Exception as e:
        logger.warning(f"Arduino update failed: {e}")
        return False


@activity.defn
async def send_notification(message: str, level: str = "info") -> bool:
    """Send notification via voice or log"""
    try:
        # Log the notification
        log_func = getattr(logger, level, logger.info)
        log_func(f"[SysAdmin] {message}")

        # For critical issues, try voice notification
        if level in ["warning", "error", "critical"]:
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        "http://localhost:8880/synthesize",
                        json={"text": message, "voice": "default"}
                    ) as response:
                        pass
            except:
                pass

        return True
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False


@activity.defn
async def trigger_auto_recovery(service_name: str, category: str) -> bool:
    """Signal auto-recovery workflow to handle failed service"""
    try:
        # Write recovery request to file for auto-recovery workflow to pick up
        recovery_file = "/tmp/sysadmin_recovery_queue.json"

        requests = []
        if os.path.exists(recovery_file):
            with open(recovery_file, 'r') as f:
                requests = json.load(f)

        # Avoid duplicates
        existing = [r for r in requests if r.get('service') == service_name]
        if not existing:
            requests.append({
                "service": service_name,
                "category": category,
                "requested_at": asyncio.get_event_loop().time()
            })

            with open(recovery_file, 'w') as f:
                json.dump(requests, f)

        return True
    except Exception as e:
        logger.error(f"Failed to trigger recovery: {e}")
        return False


@workflow.defn
class SysAdminWatchdogWorkflow:
    """
    Persistent watchdog workflow that monitors all services.
    Runs continuously, checking every 60 seconds.
    Non-intrusive - pauses during active development.
    """

    def __init__(self):
        self.running = True
        self.last_report: Optional[SystemHealthReport] = None
        self.consecutive_failures: Dict[str, int] = {}

    @workflow.run
    async def run(self, check_interval_seconds: int = 60) -> str:
        """Main watchdog loop"""

        while self.running:
            # Check if dev mode is active
            dev_mode = await workflow.execute_activity(
                check_dev_mode_active,
                start_to_close_timeout=timedelta(seconds=10)
            )

            if dev_mode:
                # In dev mode - just update Arduino to blue and wait
                await workflow.execute_activity(
                    update_arduino_status,
                    args=["dev_mode", []],
                    start_to_close_timeout=timedelta(seconds=5)
                )
                await asyncio.sleep(check_interval_seconds)
                continue

            # Perform health checks
            all_statuses: List[ServiceStatus] = []

            for category, services in MONITORED_SERVICES.items():
                for name, config in services.items():
                    check_type = config.get("check", "http")
                    host = config.get("host", "localhost")

                    if check_type == "tcp" and "port" in config:
                        # TCP port check (e.g., PostgreSQL)
                        status = await workflow.execute_activity(
                            check_tcp_service,
                            args=[name, host, config["port"]],
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RetryPolicy(maximum_attempts=1)
                        )
                    elif host != "localhost" and "port" in config:
                        # Remote HTTP service (e.g., Arduino on macpro51)
                        status = await workflow.execute_activity(
                            check_remote_http_service,
                            args=[name, host, config["port"], config.get("health", "/health")],
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RetryPolicy(maximum_attempts=1)
                        )
                    elif check_type == "http" and "port" in config:
                        # Local HTTP service
                        status = await workflow.execute_activity(
                            check_http_service,
                            args=[name, config["port"], config.get("health", "/health")],
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RetryPolicy(maximum_attempts=1)
                        )
                    elif check_type == "process":
                        pattern = config.get("pattern", name)
                        status = await workflow.execute_activity(
                            check_process_service,
                            args=[name, pattern],
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=RetryPolicy(maximum_attempts=1)
                        )
                    elif check_type == "mcp":
                        # MCP servers are checked differently - skip for now
                        continue
                    else:
                        continue

                    status.category = category
                    all_statuses.append(status)

            # Analyze results
            healthy_services = [s for s in all_statuses if s.healthy]
            unhealthy_services = [s for s in all_statuses if not s.healthy]

            critical_down = [
                s.name for s in unhealthy_services
                if MONITORED_SERVICES.get(s.category, {}).get(s.name, {}).get("critical", False)
            ]

            # Determine overall status
            if critical_down:
                overall_status = "critical"
            elif unhealthy_services:
                overall_status = "degraded"
            else:
                overall_status = "healthy"

            # Update Arduino LED
            arduino_updated = await workflow.execute_activity(
                update_arduino_status,
                args=[overall_status, [s.name for s in unhealthy_services]],
                start_to_close_timeout=timedelta(seconds=5)
            )

            # Handle failures - trigger recovery after 2 consecutive failures
            for status in unhealthy_services:
                self.consecutive_failures[status.name] = self.consecutive_failures.get(status.name, 0) + 1

                if self.consecutive_failures[status.name] == 2:
                    # Notify about issue
                    await workflow.execute_activity(
                        send_notification,
                        args=[f"Service {status.name} is down. Attempting auto-recovery.", "warning"],
                        start_to_close_timeout=timedelta(seconds=10)
                    )

                    # Trigger recovery
                    await workflow.execute_activity(
                        trigger_auto_recovery,
                        args=[status.name, status.category],
                        start_to_close_timeout=timedelta(seconds=5)
                    )

            # Clear failure counts for healthy services
            for status in healthy_services:
                if status.name in self.consecutive_failures:
                    # Service recovered
                    if self.consecutive_failures[status.name] >= 2:
                        await workflow.execute_activity(
                            send_notification,
                            args=[f"Service {status.name} has recovered.", "info"],
                            start_to_close_timeout=timedelta(seconds=10)
                        )
                    del self.consecutive_failures[status.name]

            # Store report
            from datetime import datetime
            self.last_report = SystemHealthReport(
                timestamp=datetime.utcnow().isoformat(),
                overall_status=overall_status,
                services_checked=len(all_statuses),
                services_healthy=len(healthy_services),
                services_degraded=[s.name for s in unhealthy_services if s.name not in critical_down],
                services_critical=critical_down,
                dev_mode_active=False,
                arduino_notified=arduino_updated
            )

            # Log summary (only if issues)
            if unhealthy_services:
                logger.info(f"[Watchdog] Status: {overall_status} | Down: {[s.name for s in unhealthy_services]}")

            # Wait for next check
            await asyncio.sleep(check_interval_seconds)

        return "Watchdog stopped"

    @workflow.signal
    async def stop(self):
        """Signal to stop the watchdog"""
        self.running = False

    @workflow.query
    def get_last_report(self) -> Optional[dict]:
        """Query for the last health report"""
        if self.last_report:
            return {
                "timestamp": self.last_report.timestamp,
                "overall_status": self.last_report.overall_status,
                "services_checked": self.last_report.services_checked,
                "services_healthy": self.last_report.services_healthy,
                "services_degraded": self.last_report.services_degraded,
                "services_critical": self.last_report.services_critical,
                "dev_mode_active": self.last_report.dev_mode_active
            }
        return None


# Activities list for worker registration
watchdog_activities = [
    check_http_service,
    check_process_service,
    check_tcp_service,
    check_remote_http_service,
    check_dev_mode_active,
    update_arduino_status,
    send_notification,
    trigger_auto_recovery,
]
