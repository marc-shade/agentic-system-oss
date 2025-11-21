#!/usr/bin/env python3
"""
Cluster Telemetry Collector - Real-Time Environmental Awareness

Provides granular, real-time metrics about ALL nodes that ANY agent can query.

All controllers/agents call this to get:
- Real-time system metrics (CPU, memory, disk, network)
- Process information
- Resource availability
- Service health
- Hardware capabilities
- Current load and capacity

Single API that returns complete cluster environmental awareness.
"""

import json
import time
import psutil
import subprocess
import socket
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from cluster_state_manager import ClusterStateManager, NodeStatus


@dataclass
class ProcessInfo:
    """Individual process information"""
    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_mb: float
    status: str
    create_time: float


@dataclass
class DiskInfo:
    """Disk usage information"""
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


@dataclass
class NetworkInfo:
    """Network interface information"""
    interface: str
    ip_address: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


@dataclass
class ServiceInfo:
    """Service/daemon status"""
    service_name: str
    status: str  # active, inactive, failed
    pid: Optional[int]
    uptime_seconds: Optional[float]


@dataclass
class NodeTelemetry:
    """Complete real-time telemetry for a node"""
    # Identity
    node_id: str
    hostname: str
    ip_address: str
    timestamp: float

    # System metrics
    cpu_percent: float
    cpu_count: int
    cpu_freq_mhz: float
    load_1m: float
    load_5m: float
    load_15m: float

    # Memory
    memory_total_gb: float
    memory_available_gb: float
    memory_used_gb: float
    memory_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float

    # Disk
    disks: List[DiskInfo]

    # Network
    network_interfaces: List[NetworkInfo]

    # Processes (top N by CPU/memory)
    top_processes_cpu: List[ProcessInfo]
    top_processes_memory: List[ProcessInfo]
    total_processes: int

    # Services
    services: List[ServiceInfo]

    # Capabilities
    os_type: str
    architecture: str
    python_version: str
    has_docker: bool
    has_podman: bool
    has_gpu: bool
    gpu_info: Optional[str]

    # Availability
    available_cpu_percent: float  # 100 - cpu_percent
    available_memory_gb: float
    is_overloaded: bool
    can_accept_work: bool


class ClusterTelemetryCollector:
    """
    Real-time environmental awareness for entire cluster

    Any agent on any node can call this to get complete cluster state.
    Provides granular metrics about all systems in real-time.
    """

    def __init__(self):
        self.csm = ClusterStateManager()
        self.cache_ttl = 5  # Cache telemetry for 5 seconds
        self._local_cache = {}
        self._remote_cache = {}

    def collect_local_telemetry(self) -> NodeTelemetry:
        """Collect complete telemetry for local node"""

        # Check cache
        if "local" in self._local_cache:
            cached_time, cached_data = self._local_cache["local"]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        load_1m, load_5m, load_15m = psutil.getloadavg()

        # Memory metrics
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk metrics
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append(DiskInfo(
                    path=part.mountpoint,
                    total_gb=usage.total / (1024**3),
                    used_gb=usage.used / (1024**3),
                    free_gb=usage.free / (1024**3),
                    percent_used=usage.percent
                ))
            except PermissionError:
                continue

        # Network metrics
        net_io = psutil.net_io_counters(pernic=True)
        net_addrs = psutil.net_if_addrs()
        network_interfaces = []

        for iface, addrs in net_addrs.items():
            if iface in net_io:
                io = net_io[iface]
                # Get IP address
                ip = None
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        break

                if ip:
                    network_interfaces.append(NetworkInfo(
                        interface=iface,
                        ip_address=ip,
                        bytes_sent=io.bytes_sent,
                        bytes_recv=io.bytes_recv,
                        packets_sent=io.packets_sent,
                        packets_recv=io.packets_recv
                    ))

        # Process metrics
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'status', 'create_time']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    cmdline=' '.join(info['cmdline']) if info['cmdline'] else '',
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_mb=info['memory_info'].rss / (1024**2),
                    status=info['status'],
                    create_time=info['create_time']
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Top processes
        top_cpu = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)[:10]
        top_mem = sorted(processes, key=lambda p: p.memory_mb, reverse=True)[:10]

        # Service status
        services = self._get_service_status()

        # Capabilities
        import platform
        os_type = "linux" if platform.system().lower() == "linux" else "darwin"
        architecture = platform.machine()
        python_version = platform.python_version()

        has_docker = self._check_command("docker")
        has_podman = self._check_command("podman")
        has_gpu, gpu_info = self._check_gpu()

        # Get node info from cluster state
        nodes = self.csm.get_nodes()
        local_node = None
        hostname = socket.gethostname()
        for node in nodes:
            if node.hostname == hostname:
                local_node = node
                break

        node_id = local_node.node_id if local_node else hostname
        primary_ip = self._get_primary_ip()

        # Availability
        available_cpu_percent = 100 - cpu_percent
        available_memory_gb = mem.available / (1024**3)
        is_overloaded = cpu_percent > 80 or mem.percent > 85
        can_accept_work = cpu_percent < 70 and mem.percent < 80

        telemetry = NodeTelemetry(
            node_id=node_id,
            hostname=hostname,
            ip_address=primary_ip,
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            cpu_freq_mhz=cpu_freq.current if cpu_freq else 0,
            load_1m=load_1m,
            load_5m=load_5m,
            load_15m=load_15m,
            memory_total_gb=mem.total / (1024**3),
            memory_available_gb=mem.available / (1024**3),
            memory_used_gb=mem.used / (1024**3),
            memory_percent=mem.percent,
            swap_total_gb=swap.total / (1024**3),
            swap_used_gb=swap.used / (1024**3),
            swap_percent=swap.percent,
            disks=disks,
            network_interfaces=network_interfaces,
            top_processes_cpu=top_cpu,
            top_processes_memory=top_mem,
            total_processes=len(processes),
            services=services,
            os_type=os_type,
            architecture=architecture,
            python_version=python_version,
            has_docker=has_docker,
            has_podman=has_podman,
            has_gpu=has_gpu,
            gpu_info=gpu_info,
            available_cpu_percent=available_cpu_percent,
            available_memory_gb=available_memory_gb,
            is_overloaded=is_overloaded,
            can_accept_work=can_accept_work
        )

        # Cache
        self._local_cache["local"] = (time.time(), telemetry)

        return telemetry

    def collect_remote_telemetry(self, node_id: str, ip_address: str) -> Optional[NodeTelemetry]:
        """Collect telemetry from remote node via SSH"""

        # Check cache
        cache_key = f"{node_id}_{ip_address}"
        if cache_key in self._remote_cache:
            cached_time, cached_data = self._remote_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data

        try:
            # Copy this script to remote and execute
            script_path = Path(__file__).absolute()

            cmd = f"""ssh -o ConnectTimeout=3 marc@{ip_address} 'python3 - <<EOF
import sys
sys.path.insert(0, "{script_path.parent}")
from cluster_telemetry_collector import ClusterTelemetryCollector
import json

collector = ClusterTelemetryCollector()
telemetry = collector.collect_local_telemetry()

# Convert to dict
result = {{
    "node_id": telemetry.node_id,
    "hostname": telemetry.hostname,
    "ip_address": telemetry.ip_address,
    "timestamp": telemetry.timestamp,
    "cpu_percent": telemetry.cpu_percent,
    "cpu_count": telemetry.cpu_count,
    "cpu_freq_mhz": telemetry.cpu_freq_mhz,
    "load_1m": telemetry.load_1m,
    "load_5m": telemetry.load_5m,
    "load_15m": telemetry.load_15m,
    "memory_total_gb": telemetry.memory_total_gb,
    "memory_available_gb": telemetry.memory_available_gb,
    "memory_used_gb": telemetry.memory_used_gb,
    "memory_percent": telemetry.memory_percent,
    "swap_total_gb": telemetry.swap_total_gb,
    "swap_used_gb": telemetry.swap_used_gb,
    "swap_percent": telemetry.swap_percent,
    "total_processes": telemetry.total_processes,
    "os_type": telemetry.os_type,
    "architecture": telemetry.architecture,
    "python_version": telemetry.python_version,
    "has_docker": telemetry.has_docker,
    "has_podman": telemetry.has_podman,
    "has_gpu": telemetry.has_gpu,
    "gpu_info": telemetry.gpu_info,
    "available_cpu_percent": telemetry.available_cpu_percent,
    "available_memory_gb": telemetry.available_memory_gb,
    "is_overloaded": telemetry.is_overloaded,
    "can_accept_work": telemetry.can_accept_work
}}

print(json.dumps(result))
EOF
'"""

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout.strip())

                # Create NodeTelemetry from JSON (simplified, no nested objects)
                telemetry = NodeTelemetry(
                    node_id=data["node_id"],
                    hostname=data["hostname"],
                    ip_address=data["ip_address"],
                    timestamp=data["timestamp"],
                    cpu_percent=data["cpu_percent"],
                    cpu_count=data["cpu_count"],
                    cpu_freq_mhz=data["cpu_freq_mhz"],
                    load_1m=data["load_1m"],
                    load_5m=data["load_5m"],
                    load_15m=data["load_15m"],
                    memory_total_gb=data["memory_total_gb"],
                    memory_available_gb=data["memory_available_gb"],
                    memory_used_gb=data["memory_used_gb"],
                    memory_percent=data["memory_percent"],
                    swap_total_gb=data["swap_total_gb"],
                    swap_used_gb=data["swap_used_gb"],
                    swap_percent=data["swap_percent"],
                    disks=[],  # Simplified for remote
                    network_interfaces=[],  # Simplified for remote
                    top_processes_cpu=[],  # Simplified for remote
                    top_processes_memory=[],  # Simplified for remote
                    total_processes=data["total_processes"],
                    services=[],  # Simplified for remote
                    os_type=data["os_type"],
                    architecture=data["architecture"],
                    python_version=data["python_version"],
                    has_docker=data["has_docker"],
                    has_podman=data["has_podman"],
                    has_gpu=data["has_gpu"],
                    gpu_info=data["gpu_info"],
                    available_cpu_percent=data["available_cpu_percent"],
                    available_memory_gb=data["available_memory_gb"],
                    is_overloaded=data["is_overloaded"],
                    can_accept_work=data["can_accept_work"]
                )

                # Cache
                self._remote_cache[cache_key] = (time.time(), telemetry)

                return telemetry
            else:
                return None

        except Exception as e:
            print(f"Error collecting remote telemetry from {node_id}: {e}")
            return None

    def get_cluster_telemetry(self) -> Dict[str, NodeTelemetry]:
        """
        Get complete real-time telemetry for entire cluster

        Returns:
            Dict mapping node_id -> NodeTelemetry
        """
        telemetry = {}

        # Get local telemetry
        local = self.collect_local_telemetry()
        telemetry[local.node_id] = local

        # Get all nodes from cluster state
        nodes = self.csm.get_nodes(status=NodeStatus.ONLINE)

        # Get remote telemetry
        for node in nodes:
            if node.hostname != local.hostname:
                remote = self.collect_remote_telemetry(node.node_id, node.ip_address)
                if remote:
                    telemetry[node.node_id] = remote

        return telemetry

    def get_best_node_for_work(self, require_os: str = None,
                               require_arch: str = None,
                               require_capability: str = None) -> Optional[NodeTelemetry]:
        """
        Find best node for accepting work based on current load

        Args:
            require_os: Required OS (linux, darwin)
            require_arch: Required architecture (x86_64, arm64)
            require_capability: Required capability (docker, gpu, etc.)

        Returns:
            NodeTelemetry for best node, or None if no suitable node
        """
        telemetry = self.get_cluster_telemetry()

        # Filter candidates
        candidates = []
        for node in telemetry.values():
            # Check if can accept work
            if not node.can_accept_work:
                continue

            # Check OS requirement
            if require_os and node.os_type != require_os:
                continue

            # Check architecture requirement
            if require_arch and node.architecture != require_arch:
                continue

            # Check capability requirement
            if require_capability:
                if require_capability == "docker" and not node.has_docker:
                    continue
                if require_capability == "podman" and not node.has_podman:
                    continue
                if require_capability == "gpu" and not node.has_gpu:
                    continue

            candidates.append(node)

        if not candidates:
            return None

        # Score nodes (lower is better)
        def score_node(node: NodeTelemetry) -> float:
            cpu_score = node.cpu_percent / 100.0
            mem_score = node.memory_percent / 100.0
            load_score = node.load_1m / (node.cpu_count * 2)  # Normalize load

            return cpu_score * 0.5 + mem_score * 0.3 + load_score * 0.2

        # Return best candidate
        best = min(candidates, key=score_node)
        return best

    def _get_service_status(self) -> List[ServiceInfo]:
        """Get status of key services"""
        services = []

        # Check for systemd (Linux)
        if self._check_command("systemctl"):
            service_names = [
                "cluster-self-x.service",
                "builder-node-api.service"
            ]

            for svc in service_names:
                try:
                    result = subprocess.run(
                        f"systemctl --user is-active {svc}",
                        shell=True, capture_output=True, text=True, timeout=2
                    )
                    status = result.stdout.strip()

                    # Get PID if active
                    pid = None
                    if status == "active":
                        pid_result = subprocess.run(
                            f"systemctl --user show -p MainPID {svc}",
                            shell=True, capture_output=True, text=True, timeout=2
                        )
                        if pid_result.returncode == 0:
                            pid_str = pid_result.stdout.strip().split("=")[1]
                            pid = int(pid_str) if pid_str != "0" else None

                    services.append(ServiceInfo(
                        service_name=svc,
                        status=status,
                        pid=pid,
                        uptime_seconds=None
                    ))
                except Exception:
                    continue

        # Check for launchd (macOS)
        elif self._check_command("launchctl"):
            service_names = [
                "com.agentic.cluster-self-x"
            ]

            for svc in service_names:
                try:
                    result = subprocess.run(
                        f"launchctl list | grep {svc}",
                        shell=True, capture_output=True, text=True, timeout=2
                    )

                    if result.returncode == 0:
                        parts = result.stdout.strip().split()
                        if len(parts) >= 1:
                            pid = int(parts[0]) if parts[0] != "-" else None
                            services.append(ServiceInfo(
                                service_name=svc,
                                status="active" if pid else "inactive",
                                pid=pid,
                                uptime_seconds=None
                            ))
                except Exception:
                    continue

        return services

    def _check_command(self, cmd: str) -> bool:
        """Check if command is available"""
        try:
            result = subprocess.run(
                f"which {cmd}",
                shell=True, capture_output=True, timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_gpu(self) -> tuple[bool, Optional[str]]:
        """Check for GPU availability"""
        # Check nvidia-smi
        if self._check_command("nvidia-smi"):
            try:
                result = subprocess.run(
                    "nvidia-smi --query-gpu=name --format=csv,noheader",
                    shell=True, capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    return True, result.stdout.strip()
            except Exception:
                pass

        # Check AMD GPU
        if self._check_command("rocm-smi"):
            return True, "AMD GPU (ROCm)"

        return False, None

    def _get_primary_ip(self) -> str:
        """Get primary IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


# Convenience functions for agents to use

def get_cluster_awareness() -> Dict[str, NodeTelemetry]:
    """
    Get complete real-time environmental awareness of entire cluster

    Call this from any agent to know about all systems.
    """
    collector = ClusterTelemetryCollector()
    return collector.get_cluster_telemetry()


def get_best_execution_node(require_os: str = None,
                            require_arch: str = None,
                            require_capability: str = None) -> Optional[NodeTelemetry]:
    """
    Find best node for executing work right now

    Call this before submitting tasks.
    """
    collector = ClusterTelemetryCollector()
    return collector.get_best_node_for_work(require_os, require_arch, require_capability)


if __name__ == "__main__":
    # Test telemetry collection
    collector = ClusterTelemetryCollector()

    print("=== Local Telemetry ===")
    local = collector.collect_local_telemetry()
    print(f"Node: {local.node_id}")
    print(f"CPU: {local.cpu_percent:.1f}% ({local.cpu_count} cores)")
    print(f"Memory: {local.memory_percent:.1f}% ({local.memory_used_gb:.1f}/{local.memory_total_gb:.1f} GB)")
    print(f"Load: {local.load_1m:.2f}, {local.load_5m:.2f}, {local.load_15m:.2f}")
    print(f"Can accept work: {local.can_accept_work}")
    print(f"Capabilities: docker={local.has_docker}, podman={local.has_podman}, gpu={local.has_gpu}")

    print("\n=== Cluster Telemetry ===")
    cluster = collector.get_cluster_telemetry()
    for node_id, telemetry in cluster.items():
        print(f"\n{node_id}:")
        print(f"  CPU: {telemetry.cpu_percent:.1f}%")
        print(f"  Memory: {telemetry.memory_percent:.1f}%")
        print(f"  Load: {telemetry.load_1m:.2f}")
        print(f"  Available: {telemetry.can_accept_work}")

    print("\n=== Best Node for Work ===")
    best = collector.get_best_node_for_work()
    if best:
        print(f"Best node: {best.node_id}")
        print(f"  CPU: {best.cpu_percent:.1f}%")
        print(f"  Available CPU: {best.available_cpu_percent:.1f}%")
        print(f"  Available Memory: {best.available_memory_gb:.1f} GB")
