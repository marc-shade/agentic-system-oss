#!/usr/bin/env python3
"""
Distributed Task Router - Cluster-aware task routing and execution.

Routes tasks to optimal cluster nodes based on requirements, load, and capabilities.
Includes security-hardened SSH execution without shell injection vulnerabilities.
"""

import json
import os
import re
import shlex
import socket
import sqlite3
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .config import (
    config,
    logger,
    CLUSTER_NODES,
    ClusterNode,
    TaskStatus,
    get_node,
    get_available_nodes,
    get_db_path,
    validate_node_id,
    validate_command,
    validate_ip,
    should_offload_command,
)


# =============================================================================
# IP Resolution Cache
# =============================================================================

_ip_cache: Dict[str, Tuple[str, float]] = {}  # hostname -> (ip, timestamp)


def clear_ip_cache() -> None:
    """Clear the IP resolution cache."""
    _ip_cache.clear()
    logger.debug("IP cache cleared")


def get_local_lan_ip() -> Optional[str]:
    """Get this machine's actual LAN IP (not Docker/loopback)."""
    # Method 1: Use ip route to find the IP used to reach the LAN gateway
    try:
        result = subprocess.run(
            ["ip", "route", "get", config.gateway_ip],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                ip = match.group(1)
                if validate_ip(ip):
                    return ip
    except subprocess.TimeoutExpired:
        logger.debug("Timeout getting local IP via ip route")
    except FileNotFoundError:
        logger.debug("ip command not found")
    except OSError as e:
        logger.debug(f"OS error getting local IP: {e}")

    # Method 2: Connect to external address (doesn't send data)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect((config.dns_server, 80))
        ip = s.getsockname()[0]
        s.close()
        if validate_ip(ip):
            return ip
    except socket.error as e:
        logger.debug(f"Socket error getting local IP: {e}")
    except OSError as e:
        logger.debug(f"OS error getting local IP: {e}")

    return None


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve hostname to IP using multiple methods.

    Supports mDNS (.local), DNS, and fallback methods.
    Results are cached for performance.
    """
    now = time.time()

    # Check cache first
    if hostname in _ip_cache:
        cached_ip, cached_time = _ip_cache[hostname]
        if now - cached_time < config.ip_cache_ttl:
            return cached_ip

    ip = None

    # Method 1: socket.gethostbyname (DNS and some mDNS)
    try:
        ip = socket.gethostbyname(hostname)
        if validate_ip(ip):
            _ip_cache[hostname] = (ip, now)
            logger.debug(f"Resolved {hostname} to {ip} via DNS")
            return ip
    except socket.gaierror:
        pass

    # Method 2: avahi-resolve for .local addresses (Linux mDNS)
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
                    if validate_ip(ip):
                        _ip_cache[hostname] = (ip, now)
                        logger.debug(f"Resolved {hostname} to {ip} via avahi")
                        return ip
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout resolving {hostname} via avahi")
        except FileNotFoundError:
            logger.debug("avahi-resolve not found")
        except OSError as e:
            logger.debug(f"OS error in avahi resolution: {e}")

    # Method 3: getent hosts (system resolver)
    try:
        result = subprocess.run(
            ["getent", "hosts", hostname],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip().split()[0]
            if validate_ip(ip):
                _ip_cache[hostname] = (ip, now)
                logger.debug(f"Resolved {hostname} to {ip} via getent")
                return ip
    except subprocess.TimeoutExpired:
        logger.debug(f"Timeout resolving {hostname} via getent")
    except FileNotFoundError:
        logger.debug("getent not found")
    except OSError as e:
        logger.debug(f"OS error in getent resolution: {e}")

    # Method 4: ping -c 1 to resolve (last resort)
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", hostname],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', result.stdout)
            if match:
                ip = match.group(1)
                if validate_ip(ip):
                    _ip_cache[hostname] = (ip, now)
                    logger.debug(f"Resolved {hostname} to {ip} via ping")
                    return ip
    except subprocess.TimeoutExpired:
        logger.debug(f"Timeout resolving {hostname} via ping")
    except FileNotFoundError:
        logger.debug("ping not found")
    except OSError as e:
        logger.debug(f"OS error in ping resolution: {e}")

    logger.warning(f"Failed to resolve hostname: {hostname}")
    return None


def verify_ssh_connectivity(
    ip: str,
    timeout: Optional[int] = None,
    retries: Optional[int] = None
) -> bool:
    """
    Verify SSH connection works (not just port open).

    Uses actual SSH command execution because some IPs may have port 22 open
    but SSH commands timeout (e.g., WiFi interface vs Ethernet on same host).
    """
    timeout = timeout or config.ssh_timeout
    retries = retries or config.ssh_retries

    for attempt in range(retries):
        try:
            # SECURITY: Using list arguments, not shell=True
            result = subprocess.run(
                [
                    "ssh",
                    "-o", f"ConnectTimeout={timeout}",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes",
                    f"{config.ssh_user}@{ip}",
                    "exit"
                ],
                capture_output=True,
                timeout=timeout + 2
            )
            if result.returncode == 0:
                logger.debug(f"SSH connectivity verified for {ip}")
                return True
        except subprocess.TimeoutExpired:
            logger.debug(f"SSH timeout for {ip} (attempt {attempt + 1}/{retries})")
        except OSError as e:
            logger.debug(f"SSH error for {ip}: {e}")

        if attempt < retries - 1:
            time.sleep(0.5)

    logger.warning(f"SSH connectivity failed for {ip} after {retries} attempts")
    return False


def get_node_ip(
    node_id: str,
    is_local: bool = False,
    verify_ssh: bool = False
) -> Optional[str]:
    """
    Get current IP for a node using dynamic resolution.

    Args:
        node_id: The node identifier
        is_local: If True, use interface IP instead of hostname resolution
        verify_ssh: If True, verify SSH connectivity before returning
    """
    node = get_node(node_id)
    if not node:
        logger.error(f"Unknown node: {node_id}")
        return None

    # For local node, get the actual LAN interface IP
    if is_local:
        local_ip = get_local_lan_ip()
        if local_ip:
            return local_ip

    hostname = node.hostname
    fallback_ip = node.fallback_ip

    # With SSH verification, prefer stable fallback IP
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

    return fallback_ip


# =============================================================================
# Task Definition
# =============================================================================

@dataclass
class Task:
    """Task definition for cluster execution."""
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# =============================================================================
# Distributed Task Router
# =============================================================================

class DistributedTaskRouter:
    """Routes tasks across cluster nodes automatically."""

    def __init__(self):
        self.local_node_id = self._detect_local_node()
        self.db_path = get_db_path()
        self._init_database()
        logger.info(f"Task router initialized on node: {self.local_node_id}")

    def _detect_local_node(self) -> str:
        """Detect which node we're running on."""
        hostname = socket.gethostname().lower()

        # Try to detect node from hostname
        # Configure your hostname to match node IDs (e.g., builder, orchestrator, researcher, inference)
        for node_id in CLUSTER_NODES.keys():
            if node_id in hostname:
                return node_id

        # Check if it's a macOS system by path
        if os.path.exists("/Users"):
            local_ip = get_local_lan_ip()
            if local_ip:
                # Match against known IPs
                for node_id, node in CLUSTER_NODES.items():
                    if node.fallback_ip == local_ip:
                        return node_id
            return "orchestrator"  # Default macOS node

        return "builder"  # Default Linux node

    def _init_database(self) -> None:
        """Initialize task queue database."""
        try:
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
            logger.debug(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def submit_task(self, task_def: Dict[str, Any]) -> str:
        """
        Submit a task for execution.

        Task automatically routes to best available node based on requirements.
        """
        task_id = str(uuid.uuid4())

        # Validate command if present
        command = task_def.get("command")
        if command:
            valid, error = validate_command(command)
            if not valid:
                raise ValueError(f"Invalid command: {error}")

        task = Task(
            task_id=task_id,
            task_type=task_def.get("type", "generic"),
            command=command,
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
        logger.info(f"Task {task_id} routed to {target_node}")

        # Store in database
        self._store_task(task, target_node)

        # Execute on target node
        if target_node == self.local_node_id:
            self._execute_local(task)
        else:
            self._execute_remote(task, target_node)

        return task_id

    def _store_task(self, task: Task, target_node: str) -> None:
        """Store task in database."""
        try:
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
                TaskStatus.ASSIGNED.value
            ))

            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to store task: {e}")
            raise

    def _route_task(self, task: Task) -> str:
        """
        Determine best node for task execution.

        Routing priority:
        1. Match OS requirement
        2. Match architecture
        3. Match capabilities
        4. Prefer specialized nodes
        5. Prefer less loaded nodes
        6. Avoid active node (aggressive offloading)
        """
        candidates: List[Tuple[str, int]] = []

        for node_id, node in CLUSTER_NODES.items():
            # Check if node matches requirements
            if not node.matches_requirements(
                task.requires_os,
                task.requires_arch,
                task.requires_capabilities
            ):
                continue

            # Calculate match score
            score = 0

            # Prefer specialized nodes
            if task.task_type in node.specialties:
                score += 100

            # Prefer higher priority (lower number = higher priority)
            score += (5 - node.priority) * 20

            # Heavily penalize local node (aggressive offloading)
            if node_id == self.local_node_id:
                score -= 1000

            candidates.append((node_id, score))

        if not candidates:
            logger.warning(f"No suitable nodes for task, running locally")
            return self.local_node_id

        # Select node with highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _execute_local(self, task: Task) -> None:
        """Execute task on local node."""
        try:
            if task.command:
                # SECURITY: Parse command into list to avoid shell injection
                # For complex shell commands, we still use shell=True but validate first
                if any(c in task.command for c in ['|', '&&', '||', ';', '`', '$(']):
                    # Complex command with shell operators - validate and use shell
                    result = subprocess.run(
                        task.command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=config.command_timeout
                    )
                else:
                    # Simple command - parse and execute without shell
                    cmd_parts = shlex.split(task.command)
                    result = subprocess.run(
                        cmd_parts,
                        capture_output=True,
                        text=True,
                        timeout=config.command_timeout
                    )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None

            elif task.script:
                # Write script to temp file and execute
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.sh',
                    delete=False
                ) as f:
                    f.write(task.script)
                    script_path = f.name

                try:
                    os.chmod(script_path, 0o755)
                    result = subprocess.run(
                        [script_path],
                        capture_output=True,
                        text=True,
                        timeout=config.command_timeout
                    )
                    output = result.stdout
                    error = result.stderr if result.returncode != 0 else None
                finally:
                    os.unlink(script_path)
            else:
                output = "No command or script provided"
                error = None

            self._update_task_result(
                task.task_id,
                TaskStatus.COMPLETED,
                output,
                error
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Task {task.task_id} timed out")
            self._update_task_result(
                task.task_id,
                TaskStatus.TIMEOUT,
                None,
                f"Command timed out after {config.command_timeout}s"
            )
        except subprocess.SubprocessError as e:
            logger.error(f"Task {task.task_id} subprocess error: {e}")
            self._update_task_result(task.task_id, TaskStatus.FAILED, None, str(e))
        except OSError as e:
            logger.error(f"Task {task.task_id} OS error: {e}")
            self._update_task_result(task.task_id, TaskStatus.FAILED, None, str(e))

    def _execute_remote(self, task: Task, target_node: str) -> None:
        """Execute task on remote node via SSH."""
        node = get_node(target_node)
        if not node:
            self._update_task_result(
                task.task_id,
                TaskStatus.FAILED,
                None,
                f"Unknown target node: {target_node}"
            )
            return

        # Dynamically resolve IP
        node_ip = get_node_ip(target_node)
        if not node_ip:
            self._update_task_result(
                task.task_id,
                TaskStatus.FAILED,
                None,
                f"Cannot resolve IP for node: {target_node}"
            )
            return

        ssh_target = f"{config.ssh_user}@{node_ip}"

        try:
            if task.command:
                # SECURITY: Using list arguments for SSH command
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", f"ConnectTimeout={config.ssh_connect_timeout}",
                        "-o", "StrictHostKeyChecking=accept-new",
                        "-o", "BatchMode=yes",
                        ssh_target,
                        task.command
                    ],
                    capture_output=True,
                    text=True,
                    timeout=config.command_timeout
                )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None

            elif task.script:
                # Transfer script and execute
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.sh',
                    delete=False
                ) as f:
                    f.write(task.script)
                    local_script = f.name

                remote_script = f"/tmp/task_{task.task_id}.sh"

                try:
                    # SCP script to remote node - SECURITY: list arguments
                    scp_result = subprocess.run(
                        [
                            "scp",
                            "-o", f"ConnectTimeout={config.ssh_connect_timeout}",
                            "-o", "StrictHostKeyChecking=accept-new",
                            "-o", "BatchMode=yes",
                            local_script,
                            f"{ssh_target}:{remote_script}"
                        ],
                        capture_output=True,
                        timeout=60
                    )

                    if scp_result.returncode != 0:
                        raise OSError(f"SCP failed: {scp_result.stderr.decode()}")

                    # Execute remote script - SECURITY: list arguments
                    result = subprocess.run(
                        [
                            "ssh",
                            "-o", f"ConnectTimeout={config.ssh_connect_timeout}",
                            "-o", "StrictHostKeyChecking=accept-new",
                            "-o", "BatchMode=yes",
                            ssh_target,
                            f"chmod +x {remote_script} && {remote_script} && rm {remote_script}"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=config.command_timeout
                    )
                    output = result.stdout
                    error = result.stderr if result.returncode != 0 else None

                finally:
                    os.unlink(local_script)
            else:
                self._update_task_result(
                    task.task_id,
                    TaskStatus.FAILED,
                    None,
                    "No command or script provided"
                )
                return

            self._update_task_result(
                task.task_id,
                TaskStatus.COMPLETED,
                output,
                error
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Remote task {task.task_id} timed out")
            self._update_task_result(
                task.task_id,
                TaskStatus.TIMEOUT,
                None,
                f"Remote command timed out after {config.command_timeout}s"
            )
        except subprocess.SubprocessError as e:
            logger.error(f"Remote task {task.task_id} error: {e}")
            self._update_task_result(task.task_id, TaskStatus.FAILED, None, str(e))
        except OSError as e:
            logger.error(f"Remote task {task.task_id} OS error: {e}")
            self._update_task_result(task.task_id, TaskStatus.FAILED, None, str(e))

    def _update_task_result(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[str],
        error: Optional[str]
    ) -> None:
        """Update task result in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = ?, result = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (status.value, result, error, time.time(), task_id))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to update task result: {e}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return dict(zip(columns, row))
        except sqlite3.Error as e:
            logger.error(f"Failed to get task status: {e}")
            return None

    def wait_for_result(
        self,
        task_id: str,
        timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for task to complete and return result."""
        timeout = timeout or config.command_timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)

            if not status:
                return None

            if status["status"] in [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.TIMEOUT.value
            ]:
                return status

            time.sleep(0.5)

        return None  # Timeout

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all cluster nodes."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT assigned_to, status, COUNT(*) as count
                FROM task_queue
                GROUP BY assigned_to, status
            """)

            node_stats: Dict[str, Dict[str, Any]] = {}
            for row in cursor.fetchall():
                node_id, status, count = row
                if node_id not in node_stats:
                    node_stats[node_id] = {"total": 0, "by_status": {}}
                node_stats[node_id]["total"] += count
                node_stats[node_id]["by_status"][status] = count

            conn.close()

            return {
                "local_node": self.local_node_id,
                "cluster_nodes": {
                    node_id: {
                        "hostname": node.hostname,
                        "os": node.os,
                        "arch": node.arch,
                        "capabilities": node.capabilities
                    }
                    for node_id, node in CLUSTER_NODES.items()
                },
                "task_distribution": node_stats
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get cluster status: {e}")
            return {"error": str(e)}


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI interface for task router."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: cluster-router <command>")
        print("\nCommands:")
        print("  submit <command>    - Submit a command for execution")
        print("  status <task_id>    - Get task status")
        print("  cluster-status      - Show cluster status")
        sys.exit(1)

    router = DistributedTaskRouter()
    command = sys.argv[1]

    if command == "submit":
        if len(sys.argv) < 3:
            print("Usage: cluster-router submit <command>")
            sys.exit(1)

        task_cmd = " ".join(sys.argv[2:])
        try:
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
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif command == "status":
        if len(sys.argv) < 3:
            print("Usage: cluster-router status <task_id>")
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
