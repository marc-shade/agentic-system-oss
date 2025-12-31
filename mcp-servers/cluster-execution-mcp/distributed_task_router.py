#!/usr/bin/env python3
"""
Distributed Task Router - Runs on every cluster node

Automatically routes tasks to the best available node based on:
- Task requirements (OS, arch, capabilities)
- Node current load
- Node specialties
- Priority to keep active node free

Usage:
    # On any node - route a task
    router = DistributedTaskRouter()
    task_id = router.submit_task({
        "type": "compile",
        "language": "c++",
        "requires_os": "linux",
        "source": "/path/to/code"
    })

    # Task automatically routes to best node (likely macpro51 for Linux builds)
    result = router.wait_for_result(task_id)
"""

import json
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import uuid
import sqlite3

# Dynamic IP resolution cache
_ip_cache: Dict[str, tuple] = {}  # hostname -> (ip, timestamp)
_IP_CACHE_TTL = 300  # 5 minutes

def get_local_lan_ip() -> Optional[str]:
    """Get this machine's actual LAN IP (not Docker/loopback)."""
    # Method 1: Use ip route to find the IP used to reach the LAN gateway
    try:
        result = subprocess.run(
            ["ip", "route", "get", "192.168.1.1"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # Parse: "192.168.1.1 via ... src 192.168.1.X ..."
            match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Method 2: Connect to external address (doesn't send data, just determines route)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        # Basic validation (can't call _is_valid_cluster_ip due to ordering)
        if ip and not ip.startswith("127.") and not ip.startswith("172."):
            return ip
    except:
        pass

    return None


def _is_valid_cluster_ip(ip: str) -> bool:
    """Check if IP is valid for cluster communication (not loopback/docker/link-local)."""
    if not ip:
        return False
    # Reject loopback
    if ip.startswith("127."):
        return False
    # Reject Docker/container bridge IPs (172.16.0.0/12 = 172.16-31.x.x)
    if ip.startswith("172."):
        second_octet = int(ip.split('.')[1])
        if 16 <= second_octet <= 31:
            return False
    # Reject link-local
    if ip.startswith("169.254."):
        return False
    # Reject other internal ranges sometimes used by containers
    if ip.startswith("10.") and ip.startswith("10.0."):  # podman default
        return False
    return True


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Dynamically resolve hostname to IP using multiple methods.
    Supports mDNS (.local), DNS, and fallback methods.
    Results are cached for performance.
    """
    now = time.time()

    # Check cache first
    if hostname in _ip_cache:
        cached_ip, cached_time = _ip_cache[hostname]
        if now - cached_time < _IP_CACHE_TTL:
            return cached_ip

    ip = None

    # Method 1: Try socket.gethostbyname (works for DNS and some mDNS)
    try:
        ip = socket.gethostbyname(hostname)
        if _is_valid_cluster_ip(ip):
            _ip_cache[hostname] = (ip, now)
            return ip
    except socket.gaierror:
        pass

    # Method 2: Try avahi-resolve for .local addresses (Linux mDNS)
    if hostname.endswith(".local"):
        try:
            result = subprocess.run(
                ["avahi-resolve", "-n", hostname],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    ip = parts[1]
                    _ip_cache[hostname] = (ip, now)
                    return ip
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Method 3: Try getent hosts (system resolver)
    try:
        result = subprocess.run(
            ["getent", "hosts", hostname],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip().split()[0]
            _ip_cache[hostname] = (ip, now)
            return ip
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Method 4: Try ping -c 1 to resolve (last resort)
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", hostname],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            # Parse IP from ping output
            match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', result.stdout)
            if match:
                ip = match.group(1)
                _ip_cache[hostname] = (ip, now)
                return ip
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def verify_ssh_connectivity(ip: str, timeout: int = 3, retries: int = 2) -> bool:
    """Verify SSH connection actually works (not just port open).

    Uses actual SSH command execution because some IPs may have port 22 open
    but SSH commands timeout (e.g., WiFi interface vs Ethernet on same host).

    Includes retry logic for transient network issues.
    """
    for attempt in range(retries):
        try:
            # Actually test SSH command execution, not just port availability
            # Note: Don't use BatchMode as SSH agent forwarding may be needed
            result = subprocess.run(
                ["ssh", "-o", f"ConnectTimeout={timeout}",
                 "-o", "StrictHostKeyChecking=no", f"marc@{ip}", "exit"],
                capture_output=True,
                timeout=timeout + 2
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass
        # Brief pause before retry
        if attempt < retries - 1:
            time.sleep(0.5)
    return False


def get_node_ip(node_id: str, is_local: bool = False, verify_ssh: bool = False) -> Optional[str]:
    """Get current IP for a node, using dynamic resolution.

    Args:
        node_id: The node identifier
        is_local: If True, this is the local node - use interface IP instead of hostname
        verify_ssh: If True, verify SSH connectivity before returning IP

    Strategy:
        When verify_ssh=True, prefer fallback/Ethernet IP over mDNS/WiFi for stability.
        Multi-homed hosts often have flaky WiFi but stable Ethernet.
    """
    if node_id not in CLUSTER_NODES:
        return None

    # For local node, get the actual LAN interface IP (avoids Docker/mDNS issues)
    if is_local:
        local_ip = get_local_lan_ip()
        if local_ip:
            return local_ip

    node = CLUSTER_NODES[node_id]
    hostname = node.get("hostname")
    fallback_ip = node.get("ip")

    # With SSH verification, prefer stable fallback IP (usually Ethernet)
    # over mDNS-resolved IP (often WiFi, can be flaky)
    if verify_ssh and fallback_ip:
        if verify_ssh_connectivity(fallback_ip):
            return fallback_ip
        # Fallback failed, try mDNS-resolved IP
        if hostname:
            ip = resolve_hostname(hostname)
            if ip and ip != fallback_ip and verify_ssh_connectivity(ip):
                return ip
        return None

    # Without SSH verification, prefer dynamic resolution
    if hostname:
        ip = resolve_hostname(hostname)
        if ip:
            return ip

    # Fallback to static IP
    return fallback_ip


# Cluster node registry - hostnames are authoritative, IPs are fallback hints
CLUSTER_NODES = {
    "macpro51": {
        "ip": "192.168.1.27",  # Fallback - confirmed working IP
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
        "capabilities": ["docker", "podman", "raid", "nvme", "compilation", "testing"],
        "specialties": ["compilation", "testing", "containerization", "benchmarking"],
        "max_tasks": 10,
        "priority": 3  # Lower = higher priority for offloading
    },
    "mac-studio": {
        "ip": "192.168.1.16",  # Fallback - prefer hostname resolution
        "hostname": "Marcs-Mac-Studio.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["orchestration", "coordination", "temporal", "mlx-gpu", "arduino"],
        "specialties": ["orchestration", "coordination", "monitoring", "temporal-workflows"],
        "max_tasks": 5,
        "priority": 1  # Keep this free - orchestrator
    },
    "macbook-air": {
        "ip": "192.168.1.76",  # Fallback - confirmed working IP
        "hostname": "Marcs-MacBook-Air.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["research", "documentation", "analysis"],
        "specialties": ["research", "documentation", "analysis", "mobile-operations"],
        "max_tasks": 3,
        "priority": 2
    },
    "completeu-server": {
        "ip": "192.168.1.186",  # Fallback - prefer hostname resolution
        "hostname": "completeu-server.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["ollama", "inference", "model-serving", "llm-api"],
        "specialties": ["ollama-inference", "model-serving", "api-endpoints"],
        "max_tasks": 8,
        "priority": 2
    },
    "macmini": {
        "ip": "192.168.1.2",  # small-inference node
        "hostname": "macmini.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["inference", "lightweight-tasks", "edge-computing"],
        "specialties": ["small-inference", "lightweight-models", "edge-tasks"],
        "max_tasks": 4,
        "priority": 2
    },
    "bpi-sentinel": {
        "ip": "192.168.1.234",  # sentinel/watchdog node
        "hostname": "bpi-sentinel.local",
        "os": "linux",
        "arch": "arm64",
        "capabilities": ["monitoring", "alerting", "watchdog", "health-checks"],
        "specialties": ["sentinel", "cluster-monitoring", "health-watchdog"],
        "max_tasks": 2,
        "priority": 4  # Low priority - dedicated to monitoring
    }
}

@dataclass
class Task:
    """Task definition for cluster execution"""
    task_id: str
    task_type: str
    command: Optional[str] = None
    script: Optional[str] = None
    requires_os: Optional[str] = None
    requires_arch: Optional[str] = None
    requires_capabilities: Optional[List[str]] = None
    priority: int = 5
    metadata: Optional[Dict[str, Any]] = None
    submitted_from: Optional[str] = None
    submitted_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class DistributedTaskRouter:
    """Routes tasks across cluster nodes automatically"""

    def __init__(self):
        self.local_node_id = self._detect_local_node()
        self.db_path = self._get_db_path()
        self._init_database()

    def _detect_local_node(self) -> str:
        """Detect which node we're running on - returns CLUSTER_NODES key"""
        hostname = socket.gethostname().lower()

        # Check against CLUSTER_NODES keys (the actual node identifiers)
        for node_id, node_info in CLUSTER_NODES.items():
            # Direct match on node_id
            if node_id in hostname:
                return node_id
            # Match on configured hostname (normalize for comparison)
            config_host = node_info.get("hostname", "").lower()
            # Handle variations: "Marcs-Mac-Studio.local" -> "macsstudio"
            normalized_config = config_host.replace(".local", "").replace("-", "").replace("marcs", "")
            normalized_host = hostname.replace("-", "").replace("marcs", "")
            if normalized_config and normalized_config in normalized_host:
                return node_id

        # Fallback: detect by IP address
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            for node_id, node_info in CLUSTER_NODES.items():
                if node_info.get("ip") == local_ip:
                    return node_id
        except:
            pass

        # Final fallback based on OS - use CLUSTER_NODES keys, not role names
        if os.path.exists("/Users"):
            return "mac-studio"  # Default macOS node (orchestrator)
        else:
            return "macpro51"  # Default Linux node (builder)

    def _get_db_path(self) -> Path:
        """Get path to task queue database"""
        # Use AGENTIC_SYSTEM_PATH or fall back to home directory
        agentic_path = os.environ.get("AGENTIC_SYSTEM_PATH")
        if agentic_path:
            base = Path(agentic_path)
        else:
            base = Path.home() / "agentic-system"

        db_dir = base / "databases" / "cluster"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "task_queue.db"

    def _init_database(self):
        """Initialize task queue database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_queue (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                command TEXT,
                script TEXT,
                requires_os TEXT,
                requires_arch TEXT,
                requires_capabilities TEXT,
                priority INTEGER DEFAULT 5,
                metadata TEXT,
                submitted_from TEXT,
                submitted_at REAL,
                assigned_to TEXT,
                assigned_at REAL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                completed_at REAL,
                error TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON task_queue(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assigned_to ON task_queue(assigned_to)
        """)

        conn.commit()
        conn.close()

    def submit_task(self, task_def: Dict[str, Any]) -> str:
        """
        Submit a task for execution

        Task automatically routes to best available node based on requirements
        """
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            task_type=task_def.get("type", "generic"),
            command=task_def.get("command"),
            script=task_def.get("script"),
            requires_os=task_def.get("requires_os"),
            requires_arch=task_def.get("requires_arch"),
            requires_capabilities=task_def.get("requires_capabilities"),
            priority=task_def.get("priority", 5),
            metadata=task_def.get("metadata"),
            submitted_from=self.local_node_id,
            submitted_at=time.time()
        )

        # Find best node for this task
        target_node = self._route_task(task)

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_queue (
                task_id, task_type, command, script,
                requires_os, requires_arch, requires_capabilities,
                priority, metadata, submitted_from, submitted_at,
                assigned_to, assigned_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.task_type,
            task.command,
            task.script,
            task.requires_os,
            task.requires_arch,
            json.dumps(task.requires_capabilities) if task.requires_capabilities else None,
            task.priority,
            json.dumps(task.metadata) if task.metadata else None,
            task.submitted_from,
            task.submitted_at,
            target_node,
            time.time(),
            "assigned"
        ))

        conn.commit()
        conn.close()

        # Execute on target node
        if target_node == self.local_node_id:
            # Execute locally
            self._execute_local(task)
        else:
            # Execute remotely
            self._execute_remote(task, target_node)

        return task_id

    def _route_task(self, task: Task) -> str:
        """
        Determine best node for task execution

        Routing priority:
        1. Match OS requirement
        2. Match architecture
        3. Match capabilities
        4. Prefer specialized nodes
        5. Prefer less loaded nodes
        6. Avoid active node (aggressive offloading)
        """
        candidates = []

        for node_id, node_info in CLUSTER_NODES.items():
            # Filter by OS requirement
            if task.requires_os and node_info["os"] != task.requires_os:
                continue

            # Filter by architecture
            if task.requires_arch and node_info["arch"] != task.requires_arch:
                continue

            # Filter by capabilities
            if task.requires_capabilities:
                node_caps = set(node_info["capabilities"])
                required_caps = set(task.requires_capabilities)
                if not required_caps.issubset(node_caps):
                    continue

            # Calculate match score
            score = 0

            # Prefer specialized nodes
            if task.task_type in node_info["specialties"]:
                score += 100

            # Prefer higher priority (lower number)
            score += (5 - node_info["priority"]) * 20

            # Heavily penalize local node (aggressive offloading)
            if node_id == self.local_node_id:
                score -= 1000

            # Get current load (future: check actual load)
            # For now, simulate with fixed preference

            candidates.append((node_id, score))

        if not candidates:
            # No suitable nodes, run locally
            return self.local_node_id

        # Select node with highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _execute_local(self, task: Task):
        """Execute task on local node"""
        try:
            if task.command:
                result = subprocess.run(
                    task.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None
            elif task.script:
                # Write script to temp file and execute
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(task.script)
                    script_path = f.name

                os.chmod(script_path, 0o755)
                result = subprocess.run(
                    [script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None
                os.unlink(script_path)
            else:
                output = "No command or script provided"
                error = None

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'completed', result = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (output, error, time.time(), task.task_id))
            conn.commit()
            conn.close()

        except Exception as e:
            # Update with error
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (str(e), time.time(), task.task_id))
            conn.commit()
            conn.close()

    def _execute_remote(self, task: Task, target_node: str):
        """Execute task on remote node via SSH"""
        node_info = CLUSTER_NODES[target_node]

        # Dynamically resolve IP
        node_ip = get_node_ip(target_node)
        if not node_ip:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (f"Cannot resolve IP for node: {target_node}", time.time(), task.task_id))
            conn.commit()
            conn.close()
            return

        # Build remote execution command
        if task.command:
            remote_cmd = f"ssh -o ConnectTimeout=5 marc@{node_ip} '{task.command}'"
        elif task.script:
            # Transfer script and execute
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(task.script)
                local_script = f.name

            remote_script = f"/tmp/task_{task.task_id}.sh"

            # SCP script to remote node
            subprocess.run(
                f"scp -o ConnectTimeout=5 {local_script} marc@{node_ip}:{remote_script}",
                shell=True,
                capture_output=True
            )

            remote_cmd = f"ssh -o ConnectTimeout=5 marc@{node_ip} 'chmod +x {remote_script} && {remote_script} && rm {remote_script}'"
            os.unlink(local_script)
        else:
            # No command, mark as failed
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = 'No command or script', completed_at = ?
                WHERE task_id = ?
            """, (time.time(), task.task_id))
            conn.commit()
            conn.close()
            return

        try:
            # Execute remotely
            result = subprocess.run(
                remote_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout
            error = result.stderr if result.returncode != 0 else None

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'completed', result = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (output, error, time.time(), task.task_id))
            conn.commit()
            conn.close()

        except Exception as e:
            # Update with error
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (str(e), time.time(), task.task_id))
            conn.commit()
            conn.close()

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM task_queue WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def wait_for_result(self, task_id: str, timeout: int = 300) -> Optional[Dict]:
        """Wait for task to complete and return result"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)

            if not status:
                return None

            if status["status"] in ["completed", "failed"]:
                return status

            time.sleep(0.5)

        return None  # Timeout

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all cluster nodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count tasks by node
        cursor.execute("""
            SELECT assigned_to, status, COUNT(*) as count
            FROM task_queue
            GROUP BY assigned_to, status
        """)

        node_stats = {}
        for row in cursor.fetchall():
            node_id, status, count = row
            if node_id not in node_stats:
                node_stats[node_id] = {"total": 0, "by_status": {}}
            node_stats[node_id]["total"] += count
            node_stats[node_id]["by_status"][status] = count

        conn.close()

        return {
            "local_node": self.local_node_id,
            "cluster_nodes": CLUSTER_NODES,
            "task_distribution": node_stats
        }


def main():
    """CLI interface for task router"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: distributed_task_router.py <command>")
        print("\nCommands:")
        print("  submit <command>    - Submit a command for execution")
        print("  status <task_id>    - Get task status")
        print("  cluster-status      - Show cluster status")
        sys.exit(1)

    router = DistributedTaskRouter()
    command = sys.argv[1]

    if command == "submit":
        if len(sys.argv) < 3:
            print("Usage: distributed_task_router.py submit <command>")
            sys.exit(1)

        task_cmd = " ".join(sys.argv[2:])
        task_id = router.submit_task({"type": "shell", "command": task_cmd})
        print(f"Task submitted: {task_id}")
        print("Waiting for result...")

        result = router.wait_for_result(task_id)
        if result:
            print(f"\nStatus: {result['status']}")
            print(f"Executed on: {result['assigned_to']}")
            if result['result']:
                print(f"Output:\n{result['result']}")
            if result['error']:
                print(f"Error:\n{result['error']}")
        else:
            print("Timeout waiting for result")

    elif command == "status":
        if len(sys.argv) < 3:
            print("Usage: distributed_task_router.py status <task_id>")
            sys.exit(1)

        task_id = sys.argv[2]
        status = router.get_task_status(task_id)
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(f"Task not found: {task_id}")

    elif command == "cluster-status":
        status = router.get_cluster_status()
        print(json.dumps(status, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
