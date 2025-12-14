#!/usr/bin/env python3
"""
Node Health Reporter Agent
===========================

Lightweight agent that runs on each cluster node to report health metrics
to the centralized cluster health monitor.

Features:
- Self-monitoring of local resources
- Heartbeat reporting
- Service status checking
- Automatic metric collection
- Memory synchronization with cluster
- Failover detection and recovery

Deploy one instance on each node:
- mac-studio (orchestrator)
- macbook-air (coordinator)
- macpro51 (builder) - this node
- completeu-server (inference)
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('node-reporter')


class NodeHealthReporter:
    """
    Health reporter agent for individual cluster nodes.

    Collects and reports:
    - CPU, memory, disk, load metrics
    - Network status and latency
    - Running services (SSH, Ollama, Docker, etc.)
    - Task capacity and current load
    - Uptime and availability
    """

    def __init__(self, report_interval: int = 30):
        """
        Initialize node health reporter.

        Args:
            report_interval: Seconds between reports (default: 30)
        """
        self.report_interval = report_interval
        self.running = False

        # Auto-detect node identity
        self.node_id = self._detect_node_id()
        self.hostname = socket.gethostname()
        self.ip = self._get_primary_ip()

        # Capabilities based on node
        self.capabilities = self._detect_capabilities()

        # Report destination
        self.report_file = Path(f"/tmp/node_health_{self.node_id}.json")
        self.shared_report_file = _STORAGE_BASE / "databases" / f"node_health_{self.node_id}.json"

        logger.info(f"Node Health Reporter initialized: {self.node_id} ({self.hostname})")

    def _detect_node_id(self) -> str:
        """Auto-detect node ID from hostname"""
        hostname = socket.gethostname().lower()

        if "macpro" in hostname or "mac-pro" in hostname:
            return "macpro51"
        elif "studio" in hostname:
            return "mac-studio"
        elif "air" in hostname:
            return "macbook-air"
        elif "completeu" in hostname or "server" in hostname:
            return "completeu-server"
        else:
            return hostname.split('.')[0]

    def _get_primary_ip(self) -> str:
        """Get primary IP address"""
        try:
            # Create socket to determine primary interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _detect_capabilities(self) -> List[str]:
        """Detect node capabilities"""
        capabilities = []

        # Check for services
        if self._check_command("ollama"):
            capabilities.append("ollama")

        if self._check_command("docker"):
            capabilities.append("docker")

        if self._check_command("podman"):
            capabilities.append("podman")

        # OS-based capabilities
        os_name = platform.system().lower()
        if os_name == "linux":
            capabilities.extend(["compilation", "testing", "containerization"])
        elif os_name == "darwin":
            capabilities.extend(["coordination", "analysis"])

        # Node-specific
        if self.node_id == "macpro51":
            capabilities.extend(["tpu", "raid", "nvme"])
        elif self.node_id == "mac-studio":
            capabilities.extend(["orchestration", "temporal", "mlx-gpu"])
        elif self.node_id == "macbook-air":
            capabilities.extend(["research", "documentation"])
        elif self.node_id == "completeu-server":
            capabilities.extend(["inference", "model-serving", "llm-api"])

        return list(set(capabilities))

    def _check_command(self, command: str) -> bool:
        """Check if command exists"""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=1
            )
            return True
        except:
            return False

    async def collect_metrics(self) -> Dict:
        """
        Collect comprehensive health metrics.

        Returns:
            Dictionary of health metrics
        """
        metrics = {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "ip": self.ip,
            "timestamp": datetime.now().isoformat(),
            "capabilities": self.capabilities
        }

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            metrics["cpu"] = {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else 0
            }

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics["memory"] = {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent
            }

            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics["disk"] = {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent": disk.percent
            }

            # Load average
            load = psutil.getloadavg()
            metrics["load"] = {
                "1min": load[0],
                "5min": load[1],
                "15min": load[2]
            }

            # Network metrics
            network = psutil.net_io_counters()
            metrics["network"] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }

            # Uptime
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            metrics["uptime_seconds"] = int(uptime_seconds)

            # Service checks
            metrics["services"] = await self._check_services()

            # Process count
            metrics["process_count"] = len(psutil.pids())

            # Task capacity estimate (based on available resources)
            available_capacity = self._estimate_task_capacity(cpu_percent, memory.percent)
            metrics["task_capacity"] = {
                "current_tasks": 0,  # TODO: Integrate with task queue
                "max_capacity": 10,
                "available_capacity": available_capacity
            }

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    def _estimate_task_capacity(self, cpu_percent: float, memory_percent: float) -> int:
        """
        Estimate available task capacity based on current resource usage.

        Args:
            cpu_percent: Current CPU usage percentage
            memory_percent: Current memory usage percentage

        Returns:
            Estimated number of tasks that can be accepted
        """
        # Conservative estimate based on resource availability
        cpu_capacity = max(0, int((100 - cpu_percent) / 10))
        memory_capacity = max(0, int((100 - memory_percent) / 10))

        return min(cpu_capacity, memory_capacity, 10)

    async def _check_services(self) -> Dict:
        """Check status of important services"""
        services = {}

        # SSH
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "sshd"],
                capture_output=True,
                text=True,
                timeout=2
            )
            services["ssh"] = result.stdout.strip() == "active"
        except:
            services["ssh"] = False

        # Ollama (if available)
        if "ollama" in self.capabilities:
            try:
                result = subprocess.run(
                    ["curl", "-s", "-m", "1", "http://localhost:11434/api/tags"],
                    capture_output=True,
                    timeout=2
                )
                services["ollama"] = result.returncode == 0
            except:
                services["ollama"] = False

        # Docker/Podman
        if "docker" in self.capabilities:
            try:
                result = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    timeout=2
                )
                services["docker"] = result.returncode == 0
            except:
                services["docker"] = False

        if "podman" in self.capabilities:
            try:
                result = subprocess.run(
                    ["podman", "ps"],
                    capture_output=True,
                    timeout=2
                )
                services["podman"] = result.returncode == 0
            except:
                services["podman"] = False

        return services

    async def report_health(self, metrics: Dict):
        """
        Report health metrics to central monitor.

        Args:
            metrics: Health metrics to report
        """
        try:
            # Write to local temp file
            with open(self.report_file, 'w') as f:
                json.dump(metrics, f, indent=2)

            # Write to shared location if available
            if self.shared_report_file.parent.exists():
                with open(self.shared_report_file, 'w') as f:
                    json.dump(metrics, f, indent=2)

            logger.debug(f"Health report written: {metrics['timestamp']}")

            # TODO: Also send via HTTP/gRPC to central monitor
            # For now, file-based reporting for simplicity

        except Exception as e:
            logger.error(f"Failed to report health: {e}")

    async def sync_to_cluster_memory(self, metrics: Dict):
        """
        Sync health metrics to cluster shared memory.

        Uses enhanced-memory-mcp for persistent storage.
        """
        try:
            # Import enhanced memory client
            sys.path.insert(0, str(_STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"))
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            # Store in episodic memory
            memory = EnhancedMemoryServer()

            await memory.add_episode(
                event_type="node_health_report",
                episode_data={
                    "node_id": self.node_id,
                    "cpu_percent": metrics["cpu"]["percent"],
                    "memory_percent": metrics["memory"]["percent"],
                    "load_1min": metrics["load"]["1min"],
                    "disk_percent": metrics["disk"]["percent"],
                    "uptime": metrics["uptime_seconds"]
                },
                significance_score=0.3,  # Regular health reports have low significance
                tags=["health", "monitoring", self.node_id]
            )

            logger.debug(f"Synced health to cluster memory")

        except Exception as e:
            logger.debug(f"Could not sync to cluster memory: {e}")

    async def run_report_cycle(self):
        """Run a single health report cycle"""
        try:
            # Collect metrics
            metrics = await self.collect_metrics()

            # Report to central monitor
            await self.report_health(metrics)

            # Sync to cluster memory
            await self.sync_to_cluster_memory(metrics)

            logger.info(
                f"Health report: CPU {metrics['cpu']['percent']:.1f}%, "
                f"Mem {metrics['memory']['percent']:.1f}%, "
                f"Load {metrics['load']['1min']:.2f}"
            )

        except Exception as e:
            logger.error(f"Error in report cycle: {e}", exc_info=True)

    async def run(self):
        """Main reporting loop"""
        logger.info(f"Node Health Reporter starting on {self.node_id}...")
        self.running = True

        while self.running:
            try:
                await self.run_report_cycle()

                # Sleep until next report
                await asyncio.sleep(self.report_interval)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in reporting loop: {e}", exc_info=True)
                await asyncio.sleep(self.report_interval)

        logger.info("Node Health Reporter stopped")

    def stop(self):
        """Stop the reporter"""
        self.running = False


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Node Health Reporter")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Report interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )

    args = parser.parse_args()

    reporter = NodeHealthReporter(report_interval=args.interval)

    try:
        asyncio.run(reporter.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        reporter.stop()


if __name__ == "__main__":
    main()
