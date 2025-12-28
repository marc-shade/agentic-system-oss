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
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
import sqlite3

# Ensure module path includes this directory
_this_dir = Path(__file__).parent.resolve()
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

# Import node metrics for real-time load-aware routing
try:
    from node_metrics import NodeMetrics
    METRICS_AVAILABLE = True
except ImportError as e:
    METRICS_AVAILABLE = False
    _import_error = str(e)

# Import circuit breaker for failover
try:
    from circuit_breaker import get_node_circuit_registry, NodeCircuitBreakerRegistry
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

# Import Task DAG for dependency management
try:
    from task_dag import TaskDAG, TaskStatus as DAGStatus, CycleDetectedError, TaskNotFoundError
    DAG_AVAILABLE = True
except ImportError:
    DAG_AVAILABLE = False

# Cluster node registry - use hostnames for DNS resolution
CLUSTER_NODES = {
    "macpro51": {
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
        "capabilities": ["docker", "podman", "raid", "nvme", "compilation", "testing", "gpu", "tpu", "edge-tpu", "visual-inference"],
        "specialties": ["compilation", "testing", "containerization", "benchmarking", "visual-inference"],
        "services": {
            "tpu-api": {"port": 5201, "protocol": "http", "endpoints": ["/classify", "/detect", "/embed", "/status"]}
        },
        "max_tasks": 10,
        "priority": 3  # Lower = higher priority for offloading
    },
    "mac-studio": {
        "hostname": "Marcs-Mac-Studio.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["orchestration", "coordination", "temporal"],
        "specialties": ["orchestration", "coordination", "monitoring"],
        "max_tasks": 5,
        "priority": 1  # Keep this free - orchestrator
    },
    "macbook-air": {
        "hostname": "Marcs-MacBook-Air.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["research", "documentation", "analysis"],
        "specialties": ["research", "documentation", "analysis"],
        "max_tasks": 3,
        "priority": 2
    }
}


def resolve_node_ip(node_id: str) -> str:
    """Resolve node IP from hostname via DNS"""
    if node_id not in CLUSTER_NODES:
        raise ValueError(f"Unknown node: {node_id}")

    hostname = CLUSTER_NODES[node_id]["hostname"]
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        # Fallback: try without .local suffix
        try:
            base_hostname = hostname.replace(".local", "")
            ip = socket.gethostbyname(base_hostname)
            return ip
        except socket.gaierror:
            raise RuntimeError(f"Cannot resolve hostname {hostname} for node {node_id}")

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

        # Initialize real-time load metrics if available
        if METRICS_AVAILABLE:
            self.metrics = NodeMetrics()
            # Start background collection for local metrics
            self.metrics.start_background_collection(interval=10.0)
        else:
            self.metrics = None

        # Initialize circuit breaker registry for failover
        if CIRCUIT_BREAKER_AVAILABLE:
            self.circuit_breakers = get_node_circuit_registry()
        else:
            self.circuit_breakers = None

        # Initialize task DAG for dependency management
        if DAG_AVAILABLE:
            self.dag = TaskDAG()
        else:
            self.dag = None

    def _detect_local_node(self) -> str:
        """Detect which node we're running on"""
        hostname = socket.gethostname().lower()
        # On macOS, also check LocalHostName for accurate detection
        try:
            result = subprocess.run(["scutil", "--get", "LocalHostName"],
                capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                hostname = f"{hostname} {result.stdout.strip().lower()}"
        except:
            pass

        # Check against known nodes
        if "macpro51" in hostname:
            return "macpro51"
        elif "macbook" in hostname or "air" in hostname:
            return "macbook-air"
        elif "studio" in hostname:
            return "mac-studio"
        elif "mac" in hostname and os.path.exists("/Users/marc"):
            # Check if it's MacBook Air by IP
            try:
                result = subprocess.run(
                    ["hostname", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "192.168.1.76" in result.stdout:
                    return "macbook-air"
            except:
                pass
            return "mac-studio"  # Default macOS node
        else:
            return "macpro51"  # Default Linux node

    def _get_db_path(self) -> Path:
        """Get path to task queue database"""
        if self.local_node_id == "macpro51":
            base = Path("/home/marc/agentic-system")
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

        Task automatically routes to best available node based on requirements.
        Supports dependency management via `depends_on` parameter.

        Args:
            task_def: Task definition with keys:
                - type: Task type (generic, compile, test, etc.)
                - command: Shell command to execute
                - script: Multi-line script to execute
                - requires_os: Required OS (linux, macos)
                - requires_arch: Required architecture (x86_64, arm64)
                - requires_capabilities: List of required capabilities
                - priority: 1-10, lower is higher priority
                - depends_on: List of task IDs this task depends on
                - force_node: Force execution on specific node
                - timeout: Execution timeout in seconds

        Returns:
            task_id of created task

        Raises:
            ValueError: If force_node is invalid or cycle detected
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

        # Handle dependencies via DAG
        # Register ALL tasks in DAG so they can serve as dependency targets
        depends_on = task_def.get("depends_on", [])
        has_pending_deps = False

        if self.dag:
            try:
                # Register task in DAG (with or without dependencies)
                # This enables tasks to be found as valid dependency targets
                self.dag.add_task(
                    name=task_def.get("name", task.task_type),
                    task_type=task.task_type,
                    command=task.command,
                    script=task.script,
                    depends_on=depends_on,
                    requires_os=task.requires_os,
                    requires_arch=task.requires_arch,
                    requires_capabilities=task.requires_capabilities,
                    priority=task.priority,
                    metadata=task.metadata,
                    task_id=task_id
                )

                # Check if task has pending dependencies
                if depends_on:
                    dag_task = self.dag.get_task(task_id)
                    if dag_task and dag_task.status != DAGStatus.READY:
                        has_pending_deps = True

            except CycleDetectedError as e:
                raise ValueError(f"Dependency cycle detected: {e}")
            except TaskNotFoundError as e:
                raise ValueError(f"Dependency not found: {e}")

        # Handle force_node - bypass routing if explicitly specified
        force_node = task_def.get("force_node")
        if force_node:
            if force_node not in CLUSTER_NODES:
                raise ValueError(f"Unknown force_node: {force_node}. Available: {list(CLUSTER_NODES.keys())}")
            target_node = force_node
        else:
            # Find best node for this task
            target_node = self._route_task(task)

        # Determine initial status
        initial_status = "pending_deps" if has_pending_deps else "assigned"

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
            initial_status
        ))

        conn.commit()
        conn.close()

        # If task has pending dependencies, don't execute yet
        if has_pending_deps:
            return task_id

        # Get timeout from task_def (default 60 seconds)
        timeout = task_def.get("timeout", 60)

        # Execute on target node
        if target_node == self.local_node_id:
            # Execute locally
            self._execute_local(task, timeout=timeout)
        else:
            # Execute remotely
            self._execute_remote(task, target_node, timeout=timeout)

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
            # Circuit breaker check - skip nodes with open circuits
            if self.circuit_breakers and not self.circuit_breakers.can_route_to(node_id):
                continue

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

            # Real-time load-based scoring (if metrics available)
            if self.metrics:
                load_score = self.metrics.get_load_score(node_id)
                # Convert 0.0-1.0 load to penalty: 0.0=idle (no penalty), 1.0=overloaded (-200)
                load_penalty = int(load_score * 200)
                score -= load_penalty

                # Check if node is healthy
                if not self.metrics.is_healthy(node_id):
                    score -= 500  # Heavy penalty for unhealthy nodes

            candidates.append((node_id, score))

        if not candidates:
            # No suitable nodes, run locally
            return self.local_node_id

        # Select node with highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _execute_local(self, task: Task, timeout: int = 60):
        """Execute task on local node"""
        try:
            if task.command:
                result = subprocess.run(
                    task.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
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
                    timeout=timeout
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

            if error:
                # Task failed
                cursor.execute("""
                    UPDATE task_queue
                    SET status = 'failed', result = ?, error = ?, completed_at = ?
                    WHERE task_id = ?
                """, (output, error, time.time(), task.task_id))

                # Notify DAG of failure (blocks dependents)
                if self.dag:
                    self.dag.mark_failed(task.task_id, error)
            else:
                # Task completed successfully
                cursor.execute("""
                    UPDATE task_queue
                    SET status = 'completed', result = ?, completed_at = ?
                    WHERE task_id = ?
                """, (output, time.time(), task.task_id))

                # Notify DAG of completion (may release dependents)
                if self.dag:
                    self.dag.mark_completed(task.task_id, output)
                    # Process any tasks that are now ready
                    self._process_ready_tasks()

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

            # Notify DAG of failure
            if self.dag:
                self.dag.mark_failed(task.task_id, str(e))

    def _execute_remote(self, task: Task, target_node: str, timeout: int = 300):
        """Execute task on remote node via SSH"""
        node_info = CLUSTER_NODES[target_node]

        # Resolve IP from hostname via DNS
        try:
            node_ip = resolve_node_ip(target_node)
        except (ValueError, RuntimeError) as e:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (str(e), time.time(), task.task_id))
            conn.commit()
            conn.close()

            # Record DNS failure with circuit breaker
            if self.circuit_breakers:
                self.circuit_breakers.record_failure(target_node, f"DNS resolution failed: {e}")
            return

        # SSH options for non-interactive execution
        ssh_opts = "-o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no -o LogLevel=ERROR"

        # Build remote execution command
        if task.command:
            # Escape single quotes in command
            escaped_cmd = task.command.replace("'", "'\"'\"'")
            remote_cmd = f"ssh {ssh_opts} marc@{node_ip} '{escaped_cmd}'"
        elif task.script:
            # Transfer script and execute
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(task.script)
                local_script = f.name

            remote_script = f"/tmp/task_{task.task_id}.sh"

            # SCP script to remote node (using DNS-resolved IP)
            scp_opts = "-o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no"
            subprocess.run(
                f"scp {scp_opts} {local_script} marc@{node_ip}:{remote_script}",
                shell=True,
                capture_output=True
            )

            remote_cmd = f"ssh {ssh_opts} marc@{node_ip} 'chmod +x {remote_script} && {remote_script} && rm {remote_script}'"
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
            # Execute remotely with configurable timeout
            result = subprocess.run(
                remote_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = result.stdout
            error = result.stderr if result.returncode != 0 else None

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if error:
                # Task failed
                cursor.execute("""
                    UPDATE task_queue
                    SET status = 'failed', result = ?, error = ?, completed_at = ?
                    WHERE task_id = ?
                """, (output, error, time.time(), task.task_id))

                # Notify DAG of failure
                if self.dag:
                    self.dag.mark_failed(task.task_id, error)

                # Record failure with circuit breaker
                if self.circuit_breakers:
                    self.circuit_breakers.record_failure(target_node, error)
            else:
                # Task completed successfully
                cursor.execute("""
                    UPDATE task_queue
                    SET status = 'completed', result = ?, completed_at = ?
                    WHERE task_id = ?
                """, (output, time.time(), task.task_id))

                # Notify DAG of completion
                if self.dag:
                    self.dag.mark_completed(task.task_id, output)
                    self._process_ready_tasks()

                # Record success with circuit breaker
                if self.circuit_breakers:
                    self.circuit_breakers.record_success(target_node)

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

            # Record failure with circuit breaker
            if self.circuit_breakers:
                self.circuit_breakers.record_failure(target_node, str(e))

            # Notify DAG of failure
            if self.dag:
                self.dag.mark_failed(task.task_id, str(e))

    def _process_ready_tasks(self):
        """
        Process tasks that have become ready after dependency completion.

        This is called when a task completes to check if any dependent tasks
        can now be executed.
        """
        if not self.dag:
            return

        # Get all ready tasks from DAG
        ready_tasks = self.dag.get_ready_tasks()

        for dag_task in ready_tasks:
            # Check if this task is in our pending_deps queue
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT task_id, task_type, command, script,
                       requires_os, requires_arch, requires_capabilities,
                       priority, metadata, submitted_from, assigned_to
                FROM task_queue
                WHERE task_id = ? AND status = 'pending_deps'
            """, (dag_task.task_id,))

            row = cursor.fetchone()

            if row:
                # Task found, update status and execute
                task = Task(
                    task_id=row[0],
                    task_type=row[1],
                    command=row[2],
                    script=row[3],
                    requires_os=row[4],
                    requires_arch=row[5],
                    requires_capabilities=json.loads(row[6]) if row[6] else None,
                    priority=row[7],
                    metadata=json.loads(row[8]) if row[8] else None,
                    submitted_from=row[9],
                    submitted_at=time.time()
                )
                target_node = row[10]

                # Update status to assigned
                cursor.execute("""
                    UPDATE task_queue SET status = 'assigned' WHERE task_id = ?
                """, (task.task_id,))
                conn.commit()
                conn.close()

                # Mark as running in DAG
                self.dag.mark_running(task.task_id)

                # Execute the task
                if target_node == self.local_node_id:
                    self._execute_local(task)
                else:
                    self._execute_remote(task, target_node)
            else:
                conn.close()

    def get_dag_status(self) -> Optional[Dict[str, Any]]:
        """Get status of the task DAG"""
        if not self.dag:
            return None
        return self.dag.get_dag_status()

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
        """Get status of all cluster nodes including real-time metrics"""
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

        # Add real-time metrics if available
        node_metrics = {}
        if self.metrics:
            cluster_metrics = self.metrics.get_cluster_metrics()
            for node_id, metric in cluster_metrics.items():
                node_metrics[node_id] = {
                    "cpu_percent": metric.cpu_percent,
                    "memory_percent": metric.memory_percent,
                    "load_avg_1m": metric.load_avg_1m,
                    "active_tasks": metric.active_tasks,
                    "is_healthy": metric.is_healthy,
                    "health_reason": metric.health_reason,
                    "load_score": self.metrics.get_load_score(node_id),
                    "stale": time.time() - metric.timestamp > 60
                }

        return {
            "local_node": self.local_node_id,
            "cluster_nodes": CLUSTER_NODES,
            "task_distribution": node_stats,
            "real_time_metrics": node_metrics,
            "metrics_available": METRICS_AVAILABLE
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

        print(f"\n=== Cluster Status (from {status['local_node']}) ===\n")

        # Display real-time metrics if available
        if status.get("metrics_available") and status.get("real_time_metrics"):
            print("Real-Time Node Metrics:")
            print("-" * 70)
            for node_id in sorted(status["real_time_metrics"].keys()):
                m = status["real_time_metrics"][node_id]
                health = "OK" if m["is_healthy"] else m["health_reason"]
                stale_mark = " (stale)" if m.get("stale") else ""
                print(f"  {node_id:15} CPU={m['cpu_percent']:5.1f}%  "
                      f"Mem={m['memory_percent']:5.1f}%  "
                      f"Load={m['load_avg_1m']:5.2f}  "
                      f"Tasks={m['active_tasks']}  "
                      f"Score={m['load_score']:.2f}  "
                      f"[{health}]{stale_mark}")
            print()
        else:
            print("Real-time metrics: Not available (enable node_metrics module)")
            print()

        # Display task distribution
        if status.get("task_distribution"):
            print("Task Distribution:")
            print("-" * 40)
            for node_id, stats in status["task_distribution"].items():
                print(f"  {node_id}: {stats['total']} tasks ({stats['by_status']})")
            print()

        # Display cluster nodes
        print("Registered Nodes:")
        print("-" * 40)
        for node_id, info in status["cluster_nodes"].items():
            print(f"  {node_id}: {info['os']}/{info['arch']} - {', '.join(info['specialties'][:3])}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
